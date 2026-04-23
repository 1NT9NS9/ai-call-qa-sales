import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
README_PATH = REPO_ROOT / "README.md"


class Stage5UsageDocumentationTests(unittest.TestCase):
    def test_readme_documents_stage5_api_result_retrieval_webhook_export_and_observability(
        self,
    ) -> None:
        readme_text = README_PATH.read_text(encoding="utf-8")

        self.assertIn(
            "GET /calls/{call_id}",
            readme_text,
            "expected Stage 5 usage docs to describe how to retrieve the result through the API",
        )
        self.assertIn(
            "result",
            readme_text,
            "expected Stage 5 usage docs to mention the final result in the call response",
        )
        self.assertIn(
            "WEBHOOK_TARGET_URL",
            readme_text,
            "expected Stage 5 usage docs to describe how to configure the webhook happy path",
        )
        self.assertIn(
            "POST /calls/{call_id}/export",
            readme_text,
            "expected Stage 5 usage docs to describe how to trigger webhook export",
        )
        self.assertTrue(
            "DeliveryEvent" in readme_text or "delivery_events" in readme_text,
            "expected Stage 5 usage docs to say where delivery status can be reviewed",
        )
        self.assertTrue(
            "app.pipeline" in readme_text
            or "pipeline.started" in readme_text
            or "webhook.delivery_result" in readme_text,
            "expected Stage 5 usage docs to say where pipeline logs can be observed",
        )
