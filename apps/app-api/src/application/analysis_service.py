from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from src.application.analysis_tools import AnalysisToolAPI, build_analysis_tool_api
from src.infrastructure.persistence.models import TranscriptSegment
from src.services.rag import RAGService


@dataclass(frozen=True)
class AnalysisAssets:
    prompt: str
    rubric: str
    schema: dict[str, Any]


@dataclass(frozen=True)
class AnalysisSchemaContractSource:
    contract_path: Path
    fence_label: str


def _default_resources_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "resources" / "analysis"


def _load_schema_source(
    schema_manifest_path: Path,
) -> AnalysisSchemaContractSource:
    schema_manifest = json.loads(
        schema_manifest_path.read_text(encoding="utf-8")
    )
    source_config = schema_manifest["analysis_schema_contract_source"]
    return AnalysisSchemaContractSource(
        contract_path=(
            schema_manifest_path.parent / source_config["contract_path"]
        ).resolve(),
        fence_label=source_config["fence_label"],
    )


def load_analysis_schema_from_contracts(
    resources_dir: Path | None = None,
) -> dict[str, Any]:
    active_resources_dir = resources_dir or _default_resources_dir()
    schema_manifest_path = active_resources_dir / "analysis_schema.json"
    schema_source = _load_schema_source(schema_manifest_path)
    contract_text = schema_source.contract_path.read_text(encoding="utf-8")
    schema_match = re.search(
        rf"```{re.escape(schema_source.fence_label)}\r?\n(.*?)\r?\n```",
        contract_text,
        re.DOTALL,
    )
    if schema_match is None:
        raise RuntimeError(
            "Stage 4 analysis schema block was not found in docs/CONTRACTS.md."
        )

    return json.loads(schema_match.group(1))


class AnalysisService:
    def __init__(
        self,
        resources_dir: Path | None = None,
        tool_api: AnalysisToolAPI | None = None,
        session_factory: sessionmaker[Session] | None = None,
    ) -> None:
        self._resources_dir = resources_dir or _default_resources_dir()
        self._tool_api = tool_api
        self._session_factory = session_factory

    def load_assets(self) -> AnalysisAssets:
        prompt_path = self._resources_dir / "analysis_prompt.md"
        rubric_path = self._resources_dir / "analysis_rubric.md"
        return AnalysisAssets(
            prompt=prompt_path.read_text(encoding="utf-8"),
            rubric=rubric_path.read_text(encoding="utf-8"),
            schema=load_analysis_schema_from_contracts(self._resources_dir),
        )

    def tool_definitions(self) -> list[dict[str, Any]]:
        if self._tool_api is None:
            return []

        return [
            {
                "name": definition.name,
                "description": definition.description,
                "parameters": definition.parameters,
            }
            for definition in self._tool_api.definitions()
        ]

    def invoke_tool(self, tool_name: str, **kwargs: Any) -> Any:
        if self._tool_api is None:
            raise RuntimeError("Analysis tool API is not configured.")

        return self._tool_api.invoke(tool_name, **kwargs)

    def build_prompt_context(
        self,
        call_id: int,
        context_limit: int = 5,
    ) -> dict[str, Any]:
        if self._tool_api is None or self._session_factory is None:
            raise RuntimeError(
                "Analysis prompt-context assembly requires tool_api and session_factory."
            )

        transcript = self._load_transcript(call_id=call_id)
        return {
            "call_id": call_id,
            "transcript": transcript,
            "retrieved_context": self.invoke_tool(
                "retrieve_context",
                call_id=call_id,
                limit=context_limit,
            ),
            "call_metadata": self.invoke_tool(
                "get_call_metadata",
                call_id=call_id,
            ),
        }

    def _load_transcript(self, call_id: int) -> list[dict[str, Any]]:
        with self._session_factory() as session:
            segments = list(
                session.scalars(
                    select(TranscriptSegment)
                    .where(TranscriptSegment.call_id == call_id)
                    .order_by(TranscriptSegment.sequence_no, TranscriptSegment.id)
                )
            )

        return [
            {
                "segment_id": segment.id,
                "speaker": segment.speaker,
                "text": segment.text,
                "start_ms": segment.start_ms,
                "end_ms": segment.end_ms,
                "sequence_no": segment.sequence_no,
            }
            for segment in segments
        ]


def build_analysis_service(
    resources_dir: Path | None = None,
    session_factory: sessionmaker[Session] | None = None,
    rag_service: RAGService | None = None,
) -> AnalysisService:
    tool_api = None
    if session_factory is not None or rag_service is not None:
        if session_factory is None or rag_service is None:
            raise ValueError(
                "session_factory and rag_service must be provided together."
            )
        tool_api = build_analysis_tool_api(
            session_factory=session_factory,
            rag_service=rag_service,
        )

    return AnalysisService(
        resources_dir=resources_dir,
        tool_api=tool_api,
        session_factory=session_factory,
    )
