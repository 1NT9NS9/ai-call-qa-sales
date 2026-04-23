import importlib
import json
import shutil
import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import patch

from alembic import command
from alembic.config import Config
from conftest import (
    ALEMBIC_INI_PATH,
    TEST_TMP_ROOT,
    clear_src_modules,
    temporary_postgres_database,
)
from fastapi.testclient import TestClient
from sqlalchemy import insert

from src.application.analysis_service import AnalysisService
from src.application.analysis_tools import (
    AnalysisToolAPI,
    build_analysis_tool_api,
    build_langchain_tools,
)


APPROVED_TOOL_NAMES = ["retrieve_context", "get_call_metadata"]
CREATE_CALL_PAYLOAD = {
    "external_call_id": "ext-call-stage4-t11",
    "source_type": "api",
    "metadata": {"campaign": "stage4", "channel": "sales"},
}
FIXED_TRANSCRIPT_SEGMENTS = [
    {
        "speaker": "customer",
        "text": "The pricing feels expensive and our budget approval is slow.",
        "start_ms": 0,
        "end_ms": 1200,
        "sequence_no": 1,
    },
    {
        "speaker": "agent",
        "text": "We can map the value to your rollout plan and help with internal approval.",
        "start_ms": 1200,
        "end_ms": 2600,
        "sequence_no": 2,
    },
    {
        "speaker": "customer",
        "text": "If you can send next steps and a mutual action plan, I can review it with finance.",
        "start_ms": 2600,
        "end_ms": 4100,
        "sequence_no": 3,
    },
]
DETERMINISTIC_ANALYSIS_RESULT = {
    "summary": "Customer raised pricing concerns and asked for approval help plus next steps.",
    "score": 8.7,
    "score_breakdown": [
        {
            "criterion": "Discovery",
            "score": 4.5,
            "max_score": 5.0,
            "reason": "The rep uncovered pricing and approval blockers clearly.",
        }
    ],
    "objections": [
        {
            "text": "Pricing feels expensive.",
            "handled": True,
            "evidence_segment_ids": [1],
        }
    ],
    "risks": [
        {
            "text": "Budget approval may delay the deal.",
            "severity": "medium",
            "evidence_segment_ids": [1, 3],
        }
    ],
    "next_best_action": "Send a mutual action plan with ROI framing and approval next steps.",
    "coach_feedback": "Tie pricing to rollout value and confirm the finance process earlier.",
    "used_knowledge": [
        {
            "document_id": 3,
            "chunk_id": 7,
            "reason": "Pricing objection guidance improved the response.",
        }
    ],
    "confidence": 0.25,
    "needs_review": False,
    "review_reasons": [],
}
EXPECTED_COMPUTED_CONFIDENCE = 1.0


class _RecordingToolAPI:
    def __init__(self, inner: AnalysisToolAPI) -> None:
        self._inner = inner
        self.invocations: list[str] = []

    def definitions(self):
        return self._inner.definitions()

    def invoke(self, tool_name: str, **kwargs):
        self.invocations.append(tool_name)
        return self._inner.invoke(tool_name, **kwargs)


class _FakeBoundModel:
    def __init__(self, response_text: str) -> None:
        self._response_text = response_text
        self.invocations: list[object] = []

    def invoke(self, payload):
        self.invocations.append(payload)
        return SimpleNamespace(content=self._response_text)


class _DeterministicFakeChatModel:
    def __init__(self, response_text: str) -> None:
        self._response_text = response_text
        self.bind_history: list[list[object]] = []
        self.bound_models: list[_FakeBoundModel] = []

    def bind_tools(self, tools):
        self.bind_history.append(list(tools))
        bound_model = _FakeBoundModel(self._response_text)
        self.bound_models.append(bound_model)
        return bound_model


def _tool_name(tool: object) -> str | None:
    for attr_name in ("name", "tool_name", "__name__"):
        value = getattr(tool, attr_name, None)
        if isinstance(value, str) and value:
            return value

    if hasattr(tool, "func"):
        return _tool_name(getattr(tool, "func"))

    return None


def _json_shape(value):
    if isinstance(value, dict):
        return {
            key: _json_shape(value[key])
            for key in sorted(value)
        }
    if isinstance(value, list):
        if not value:
            return []
        return [_json_shape(value[0])]
    return type(value).__name__


class Stage4RepeatabilityTests(unittest.TestCase):
    def test_stage4_fixed_input_is_repeatable_with_deterministic_fake_model(self) -> None:
        TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)
        temp_root = TEST_TMP_ROOT / f"stage4-t11-{uuid.uuid4().hex}"
        temp_root.mkdir(parents=True, exist_ok=True)

        try:
            with temporary_postgres_database("stage4_t11") as database_url:
                env_values = {
                    "APP_ENV": "test",
                    "APP_HOST": "127.0.0.1",
                    "APP_PORT": "8000",
                    "DATABASE_URL": database_url,
                    "STORAGE_AUDIO_DIR": str(temp_root / "audio"),
                }

                with patch.dict("os.environ", env_values, clear=True):
                    alembic_config = Config(str(ALEMBIC_INI_PATH))
                    command.upgrade(alembic_config, "head")

                    clear_src_modules()
                    main_module = importlib.import_module("src.main")
                    persistence_models = importlib.import_module(
                        "src.infrastructure.persistence.models"
                    )
                    app = main_module.create_app()

                    with TestClient(app) as client:
                        import_response = client.post("/knowledge/import")
                        embed_response = client.post("/knowledge/embed")
                        create_call_response = client.post(
                            "/calls",
                            json=CREATE_CALL_PAYLOAD,
                        )
                        self.assertEqual(import_response.status_code, 201)
                        self.assertEqual(embed_response.status_code, 200)
                        self.assertEqual(create_call_response.status_code, 201)

                        call_id = create_call_response.json()["id"]
                        with app.state.session_factory() as session:
                            session.execute(
                                insert(persistence_models.TranscriptSegment),
                                [
                                    {"call_id": call_id, **segment}
                                    for segment in FIXED_TRANSCRIPT_SEGMENTS
                                ],
                            )
                            call_session = session.get(
                                persistence_models.CallSession,
                                call_id,
                            )
                            call_session.processing_status = (
                                persistence_models.CallProcessingStatus.TRANSCRIBED
                            )
                            session.commit()

                        recording_tool_api = _RecordingToolAPI(
                            build_analysis_tool_api(
                                session_factory=app.state.session_factory,
                                rag_service=app.state.rag_service,
                            )
                        )
                        fake_chat_model = _DeterministicFakeChatModel(
                            json.dumps(DETERMINISTIC_ANALYSIS_RESULT)
                        )
                        analysis_service = AnalysisService(
                            tool_api=recording_tool_api,
                            session_factory=app.state.session_factory,
                            chat_model=fake_chat_model,
                            langchain_tools=build_langchain_tools(
                                session_factory=app.state.session_factory,
                                rag_service=app.state.rag_service,
                            ),
                        )

                        first_invocation_index = len(recording_tool_api.invocations)
                        first_result = analysis_service.analyze(call_id=call_id)
                        first_run_tools = recording_tool_api.invocations[
                            first_invocation_index:
                        ]

                        second_invocation_index = len(recording_tool_api.invocations)
                        second_result = analysis_service.analyze(call_id=call_id)
                        second_run_tools = recording_tool_api.invocations[
                            second_invocation_index:
                        ]

                        with app.state.session_factory() as session:
                            persisted_analysis = session.get(
                                persistence_models.CallAnalysis,
                                call_id,
                            )
                            persisted_call = session.get(
                                persistence_models.CallSession,
                                call_id,
                            )

                schema = analysis_service.load_assets().schema
                first_errors = analysis_service._validate_schema_instance(
                    instance=first_result,
                    schema=schema,
                )
                second_errors = analysis_service._validate_schema_instance(
                    instance=second_result,
                    schema=schema,
                )

                self.assertEqual(first_errors, [])
                self.assertEqual(second_errors, [])
                self.assertEqual(
                    _json_shape(first_result),
                    _json_shape(second_result),
                    "expected both repeatability runs to produce the same schema shape",
                )
                self.assertEqual(
                    first_run_tools,
                    APPROVED_TOOL_NAMES,
                    "expected the first repeatability run to use only the approved tools",
                )
                self.assertEqual(
                    second_run_tools,
                    APPROVED_TOOL_NAMES,
                    "expected the second repeatability run to use only the approved tools",
                )
                self.assertEqual(
                    [_tool_name(tools[0]) for tools in fake_chat_model.bind_history],
                    ["retrieve_context", "retrieve_context"],
                    "expected both repeatability runs to bind the approved tools",
                )
                self.assertEqual(
                    [
                        [_tool_name(tool) for tool in tools]
                        for tools in fake_chat_model.bind_history
                    ],
                    [APPROVED_TOOL_NAMES, APPROVED_TOOL_NAMES],
                    "expected both repeatability runs to bind the same approved-tool set",
                )
                self.assertEqual(
                    first_result["needs_review"],
                    second_result["needs_review"],
                    "expected both repeatability runs to produce the same review decision",
                )
                self.assertEqual(
                    float(first_result["score"]),
                    float(second_result["score"]),
                    "expected both repeatability runs to produce the same normalized score",
                )
                self.assertEqual(
                    first_result["confidence"],
                    second_result["confidence"],
                    "expected both repeatability runs to produce the same confidence",
                )
                self.assertEqual(
                    first_result["confidence"],
                    EXPECTED_COMPUTED_CONFIDENCE,
                    "expected the deterministic repeatability run to keep the service-owned confidence stable",
                )
                self.assertEqual(
                    first_result,
                    second_result,
                    "expected deterministic repeatability to return the same analysis payload twice",
                )
                self.assertIsNotNone(
                    persisted_analysis,
                    "expected the repeated run to leave a persisted CallAnalysis record",
                )
                self.assertEqual(
                    persisted_analysis.result_json,
                    second_result,
                    "expected persisted analysis state to match the last repeatability run result",
                )
                self.assertEqual(
                    persisted_analysis.confidence,
                    EXPECTED_COMPUTED_CONFIDENCE,
                    "expected persisted confidence to remain stable across repeatability runs",
                )
                self.assertEqual(
                    persisted_call.processing_status,
                    persistence_models.CallProcessingStatus.ANALYZED,
                    "expected repeated deterministic runs to keep the call lifecycle in analyzed",
                )
                self.assertEqual(
                    [len(bound_model.invocations) for bound_model in fake_chat_model.bound_models],
                    [1, 1],
                    "expected each repeatability run to invoke its bound model exactly once",
                )
        finally:
            clear_src_modules()
            shutil.rmtree(temp_root, ignore_errors=True)
