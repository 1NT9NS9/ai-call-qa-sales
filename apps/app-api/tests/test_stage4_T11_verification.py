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


APPROVED_TOOL_NAMES = ["retrieve_context", "get_call_metadata"]
CREATE_CALL_PAYLOAD = {
    "external_call_id": "ext-call-stage4-t11",
    "source_type": "api",
    "metadata": {"campaign": "stage4", "channel": "sales"},
}
FIXED_TRANSCRIPT_SEGMENTS = [
    {
        "speaker": "customer",
        "text": "The pricing feels expensive and our finance team needs a clear plan.",
        "start_ms": 0,
        "end_ms": 1200,
        "sequence_no": 1,
    },
    {
        "speaker": "agent",
        "text": "I can send ROI proof, approval guidance, and a mutual action plan today.",
        "start_ms": 1200,
        "end_ms": 2600,
        "sequence_no": 2,
    },
]
DETERMINISTIC_ANALYSIS_RESULT = {
    "summary": "Customer raised pricing and finance approval concerns.",
    "score": 8.6,
    "score_breakdown": [
        {
            "criterion": "Discovery",
            "score": 4.2,
            "max_score": 5.0,
            "reason": "The rep uncovered the main blocker and next step.",
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
            "text": "Finance approval may delay the deal.",
            "severity": "medium",
            "evidence_segment_ids": [1],
        }
    ],
    "next_best_action": "Send ROI proof and a mutual action plan.",
    "coach_feedback": "Keep connecting value to approval urgency and rollout timing.",
    "used_knowledge": [
        {
            "document_id": 3,
            "chunk_id": 7,
            "reason": "Pricing objection guidance supported the recommendation.",
        }
    ],
    "confidence": 0.99,
    "needs_review": False,
    "review_reasons": [],
}


class _DeterministicBoundModel:
    def __init__(self, response_text: str) -> None:
        self._response_text = response_text
        self.invocations: list[object] = []

    def invoke(self, payload):
        self.invocations.append(payload)
        return SimpleNamespace(content=self._response_text)


class _DeterministicFakeChatModel:
    def __init__(self, response_text: str) -> None:
        self._response_text = response_text
        self.bound_tools_history: list[list[object]] = []
        self.bound_model = _DeterministicBoundModel(response_text)

    def bind_tools(self, tools):
        bound_tools = list(tools)
        self.bound_tools_history.append(bound_tools)
        return self.bound_model


def _tool_name(tool: object) -> str | None:
    if isinstance(tool, dict):
        if "name" in tool:
            return str(tool["name"])
        if "function" in tool and isinstance(tool["function"], dict):
            return str(tool["function"].get("name"))

    for attr_name in ("name", "tool_name", "__name__"):
        value = getattr(tool, attr_name, None)
        if isinstance(value, str) and value:
            return value

    if hasattr(tool, "func"):
        func = getattr(tool, "func")
        for attr_name in ("name", "tool_name", "__name__"):
            value = getattr(func, attr_name, None)
            if isinstance(value, str) and value:
                return value

    return None


class Stage4RepeatabilityVerificationTests(unittest.TestCase):
    def test_stage4_fixed_input_is_repeatable_across_two_runs(self) -> None:
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
                    analysis_service_module = importlib.import_module(
                        "src.application.analysis_service"
                    )
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

                        fake_chat_model = _DeterministicFakeChatModel(
                            json.dumps(DETERMINISTIC_ANALYSIS_RESULT)
                        )
                        analysis_service = analysis_service_module.build_analysis_service(
                            session_factory=app.state.session_factory,
                            rag_service=app.state.rag_service,
                            chat_model=fake_chat_model,
                        )

                        invoked_tool_names_by_run: list[list[str]] = []
                        original_invoke_tool = analysis_service.invoke_tool

                        def run_once():
                            run_tool_names: list[str] = []

                            def recording_invoke_tool(tool_name: str, **kwargs):
                                run_tool_names.append(tool_name)
                                return original_invoke_tool(tool_name, **kwargs)

                            analysis_service.invoke_tool = recording_invoke_tool
                            result_payload = analysis_service.analyze(call_id=call_id)
                            invoked_tool_names_by_run.append(run_tool_names)
                            return result_payload

                        first_result = run_once()
                        second_result = run_once()

                        with app.state.session_factory() as session:
                            persisted_analysis = session.get(
                                persistence_models.CallAnalysis,
                                call_id,
                            )
                            persisted_call = session.get(
                                persistence_models.CallSession,
                                call_id,
                            )

                self.assertEqual(
                    set(first_result),
                    set(second_result),
                    "expected both repeatability runs to produce the same schema shape",
                )
                self.assertEqual(
                    [_tool_name(tool) for tool in fake_chat_model.bound_tools_history[0]],
                    APPROVED_TOOL_NAMES,
                    "expected the first run to bind only the approved tools",
                )
                self.assertEqual(
                    [_tool_name(tool) for tool in fake_chat_model.bound_tools_history[1]],
                    APPROVED_TOOL_NAMES,
                    "expected the second run to bind only the approved tools",
                )
                self.assertEqual(
                    invoked_tool_names_by_run[0],
                    APPROVED_TOOL_NAMES,
                    "expected the first run to invoke the approved tools in the same bounded order",
                )
                self.assertEqual(
                    invoked_tool_names_by_run[1],
                    APPROVED_TOOL_NAMES,
                    "expected the second run to invoke the approved tools in the same bounded order",
                )
                self.assertEqual(
                    first_result["needs_review"],
                    second_result["needs_review"],
                    "expected both runs to produce the same review decision",
                )
                self.assertEqual(
                    first_result["score"],
                    second_result["score"],
                    "expected both runs to produce the same normalized score",
                )
                self.assertEqual(
                    first_result["confidence"],
                    second_result["confidence"],
                    "expected both runs to produce the same confidence",
                )
                self.assertEqual(
                    len(fake_chat_model.bound_model.invocations),
                    2,
                    "expected the deterministic repeatability check to invoke the model exactly twice",
                )
                self.assertIsNotNone(
                    persisted_analysis,
                    "expected the repeated happy-path runs to keep a persisted CallAnalysis record",
                )
                self.assertEqual(
                    persisted_analysis.result_json,
                    second_result,
                    "expected the persisted analysis payload to match the latest repeatable run",
                )
                self.assertEqual(
                    persisted_call.processing_status,
                    persistence_models.CallProcessingStatus.ANALYZED,
                    "expected repeated happy-path runs to keep the call lifecycle in analyzed",
                )
        finally:
            clear_src_modules()
            shutil.rmtree(temp_root, ignore_errors=True)
