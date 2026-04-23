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


CREATE_CALL_PAYLOAD = {
    "external_call_id": "ext-call-stage4-t10",
    "source_type": "api",
    "metadata": {"campaign": "stage4", "channel": "sales"},
}
STANDARD_TRANSCRIPT_SEGMENTS = [
    {
        "speaker": "customer",
        "text": "The pricing feels expensive and our finance team needs a plan.",
        "start_ms": 0,
        "end_ms": 1200,
        "sequence_no": 1,
    },
    {
        "speaker": "agent",
        "text": "I can send ROI framing and a mutual action plan today.",
        "start_ms": 1200,
        "end_ms": 2600,
        "sequence_no": 2,
    },
]
TOO_SHORT_TRANSCRIPT_SEGMENTS = [
    {
        "speaker": "customer",
        "text": "Need price.",
        "start_ms": 0,
        "end_ms": 400,
        "sequence_no": 1,
    }
]
VALID_ANALYSIS_RESULT = {
    "summary": "Customer raised pricing concerns and requested a follow-up plan.",
    "score": 8.0,
    "score_breakdown": [
        {
            "criterion": "Discovery",
            "score": 4.0,
            "max_score": 5.0,
            "reason": "The rep uncovered pricing friction.",
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
            "evidence_segment_ids": [1],
        }
    ],
    "next_best_action": "Send a mutual action plan with ROI framing.",
    "coach_feedback": "Tie pricing to rollout value more explicitly.",
    "used_knowledge": [
        {
            "document_id": 3,
            "chunk_id": 7,
            "reason": "Pricing objection guidance improved the recommendation.",
        }
    ],
    "confidence": 0.11,
    "needs_review": False,
    "review_reasons": [],
}
LOW_CONFIDENCE_ANALYSIS_RESULT = {
    **VALID_ANALYSIS_RESULT,
    "used_knowledge": [],
    "risks": [
        {
            "text": "Budget approval may delay the deal.",
            "severity": "medium",
            "evidence_segment_ids": [],
        }
    ],
}
SCHEMA_INVALID_ANALYSIS_RESULT = {
    **VALID_ANALYSIS_RESULT,
    "summary": 123,
}
INVALID_JSON_RESPONSE = '{"summary":'


class _FakeBoundModel:
    def __init__(self, responses) -> None:
        self._responses = list(responses)
        self._index = 0
        self.invocations: list[object] = []

    def invoke(self, payload):
        self.invocations.append(payload)
        response_text = self._responses[self._index]
        if self._index < len(self._responses) - 1:
            self._index += 1
        return SimpleNamespace(content=response_text)


class _FakeChatModel:
    def __init__(self, responses) -> None:
        self.bound_tools = None
        self.bound_model = _FakeBoundModel(responses)

    def bind_tools(self, tools):
        self.bound_tools = list(tools)
        return self.bound_model


class Stage4RetryAndReviewRoutingTests(unittest.TestCase):
    def _run_analysis(
        self,
        *,
        transcript_segments,
        responses,
    ):
        TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)
        temp_root = TEST_TMP_ROOT / f"stage4-t10-{uuid.uuid4().hex}"
        temp_root.mkdir(parents=True, exist_ok=True)

        try:
            with temporary_postgres_database("stage4_t10") as database_url:
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
                                    for segment in transcript_segments
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

                        fake_chat_model = _FakeChatModel(responses)
                        analysis_service = analysis_service_module.build_analysis_service(
                            session_factory=app.state.session_factory,
                            rag_service=app.state.rag_service,
                            chat_model=fake_chat_model,
                        )

                        error = None
                        result = None
                        try:
                            result = analysis_service.analyze(call_id=call_id)
                        except Exception as exc:  # pragma: no cover - asserted by callers
                            error = exc

                        with app.state.session_factory() as session:
                            persisted_analysis = session.get(
                                persistence_models.CallAnalysis,
                                call_id,
                            )
                            persisted_call = session.get(
                                persistence_models.CallSession,
                                call_id,
                            )

                return (
                    result,
                    error,
                    persisted_analysis,
                    persisted_call,
                    persistence_models,
                    fake_chat_model,
                    analysis_service_module,
                )
        finally:
            clear_src_modules()
            shutil.rmtree(temp_root, ignore_errors=True)

    def test_stage4_invalid_json_retries_once_then_persists_valid_analysis(self) -> None:
        (
            result,
            error,
            persisted_analysis,
            persisted_call,
            persistence_models,
            fake_chat_model,
            _analysis_service_module,
        ) = self._run_analysis(
            transcript_segments=STANDARD_TRANSCRIPT_SEGMENTS,
            responses=[
                INVALID_JSON_RESPONSE,
                json.dumps(VALID_ANALYSIS_RESULT),
            ],
        )

        self.assertIsNone(error)
        self.assertEqual(
            len(fake_chat_model.bound_model.invocations),
            2,
            "expected invalid JSON to trigger exactly one retry before success",
        )
        self.assertIsNotNone(
            persisted_analysis,
            "expected the retry-success path to persist a CallAnalysis record",
        )
        self.assertFalse(
            persisted_analysis.review_required,
            "expected the retry-success path not to route the result into review",
        )
        self.assertEqual(
            persisted_call.processing_status,
            persistence_models.CallProcessingStatus.ANALYZED,
            "expected the retry-success path to end in analyzed",
        )
        self.assertEqual(
            persisted_analysis.result_json,
            result,
            "expected the persisted analysis payload to match the returned payload after retry success",
        )

    def test_stage4_schema_invalid_json_retries_once_then_persists_valid_analysis(
        self,
    ) -> None:
        (
            result,
            error,
            persisted_analysis,
            persisted_call,
            persistence_models,
            fake_chat_model,
            _analysis_service_module,
        ) = self._run_analysis(
            transcript_segments=STANDARD_TRANSCRIPT_SEGMENTS,
            responses=[
                json.dumps(SCHEMA_INVALID_ANALYSIS_RESULT),
                json.dumps(VALID_ANALYSIS_RESULT),
            ],
        )

        self.assertIsNone(error)
        self.assertEqual(
            len(fake_chat_model.bound_model.invocations),
            2,
            "expected schema-invalid JSON to trigger exactly one retry before success",
        )
        self.assertIsNotNone(persisted_analysis)
        self.assertFalse(persisted_analysis.review_required)
        self.assertEqual(
            persisted_call.processing_status,
            persistence_models.CallProcessingStatus.ANALYZED,
            "expected the schema-invalid retry-success path to end in analyzed",
        )
        self.assertEqual(
            persisted_analysis.result_json,
            result,
            "expected the persisted analysis payload to match the returned payload after schema-invalid retry success",
        )

    def test_stage4_repeated_invalid_json_routes_to_review_after_retry_budget(self) -> None:
        (
            result,
            error,
            persisted_analysis,
            _persisted_call,
            _persistence_models,
            fake_chat_model,
            _analysis_service_module,
        ) = self._run_analysis(
            transcript_segments=STANDARD_TRANSCRIPT_SEGMENTS,
            responses=[
                INVALID_JSON_RESPONSE,
                INVALID_JSON_RESPONSE,
                json.dumps(VALID_ANALYSIS_RESULT),
            ],
        )

        self.assertIsNone(error)
        self.assertEqual(
            len(fake_chat_model.bound_model.invocations),
            2,
            "expected repeated invalid JSON not to retry a second time for the same case",
        )
        self.assertEqual(
            result,
            {
                "needs_review": True,
                "review_reasons": [
                    "analysis output remained invalid after retry",
                    "Analysis output is invalid JSON.",
                ],
            },
            "expected repeated invalid JSON to persist review-required state after the retry budget is exhausted",
        )
        self.assertTrue(persisted_analysis.review_required)
        self.assertEqual(
            persisted_analysis.review_reasons,
            result["review_reasons"],
        )

    def test_stage4_repeated_schema_invalid_output_routes_to_review_after_retry_budget(
        self,
    ) -> None:
        (
            result,
            error,
            persisted_analysis,
            _persisted_call,
            _persistence_models,
            fake_chat_model,
            _analysis_service_module,
        ) = self._run_analysis(
            transcript_segments=STANDARD_TRANSCRIPT_SEGMENTS,
            responses=[
                json.dumps(SCHEMA_INVALID_ANALYSIS_RESULT),
                json.dumps(SCHEMA_INVALID_ANALYSIS_RESULT),
                json.dumps(VALID_ANALYSIS_RESULT),
            ],
        )

        self.assertIsNone(error)
        self.assertEqual(
            len(fake_chat_model.bound_model.invocations),
            2,
            "expected repeated schema-invalid output not to retry a second time for the same case",
        )
        self.assertEqual(
            result,
            {
                "needs_review": True,
                "review_reasons": [
                    "analysis output remained invalid after retry",
                    "Analysis output failed schema validation: $.summary must be a string",
                ],
            },
            "expected repeated schema-invalid output to persist review-required state after the retry budget is exhausted",
        )
        self.assertTrue(persisted_analysis.review_required)
        self.assertEqual(
            persisted_analysis.review_reasons,
            result["review_reasons"],
        )

    def test_stage4_low_confidence_output_persists_review_required_state(self) -> None:
        (
            result,
            error,
            persisted_analysis,
            persisted_call,
            persistence_models,
            fake_chat_model,
            _analysis_service_module,
        ) = self._run_analysis(
            transcript_segments=STANDARD_TRANSCRIPT_SEGMENTS,
            responses=[json.dumps(LOW_CONFIDENCE_ANALYSIS_RESULT)],
        )

        self.assertIsNone(error)
        self.assertEqual(
            len(fake_chat_model.bound_model.invocations),
            1,
            "expected the low-confidence case to complete without retrying valid output",
        )
        self.assertTrue(result["needs_review"])
        self.assertEqual(
            result["review_reasons"],
            ["confidence below 0.70 threshold"],
        )
        self.assertTrue(persisted_analysis.review_required)
        self.assertEqual(
            persisted_analysis.review_reasons,
            ["confidence below 0.70 threshold"],
        )
        self.assertEqual(
            persisted_call.processing_status,
            persistence_models.CallProcessingStatus.ANALYZED,
            "expected low-confidence output to persist review-required state without changing lifecycle status",
        )

    def test_stage4_too_short_transcript_follows_the_hard_fail_rule(self) -> None:
        (
            _result,
            error,
            persisted_analysis,
            persisted_call,
            persistence_models,
            fake_chat_model,
            analysis_service_module,
        ) = self._run_analysis(
            transcript_segments=TOO_SHORT_TRANSCRIPT_SEGMENTS,
            responses=[json.dumps(LOW_CONFIDENCE_ANALYSIS_RESULT)],
        )

        self.assertIsInstance(error, RuntimeError)
        self.assertEqual(str(error), analysis_service_module.TRANSCRIPT_TOO_SHORT_ERROR)
        self.assertEqual(
            len(fake_chat_model.bound_model.invocations),
            0,
            "expected the hard-fail transcript branch not to invoke the analysis model",
        )
        self.assertIsNone(
            persisted_analysis,
            "expected the hard-fail transcript branch not to persist review-required state",
        )
        self.assertEqual(
            persisted_call.processing_status,
            persistence_models.CallProcessingStatus.FAILED,
            "expected the too-short transcript case to move the call lifecycle to failed",
        )
