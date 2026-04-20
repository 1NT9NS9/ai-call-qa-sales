from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StepContext:
    stage_id: str
    stage_name: str
    stage_file: Path
    step_id: str
    agent_id: str
    agent_file: Path
    planner_id: str
    planner_file: Path
    executor_id: str
    executor_file: Path
    required_documents: list[Path]
    required_step_ids: list[str]
