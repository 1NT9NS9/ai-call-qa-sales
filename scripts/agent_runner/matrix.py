from __future__ import annotations

from pathlib import Path
from typing import Any

from agent_runner.config import executor_file_path, planner_file_path
from agent_runner.constants import ROOT_DIR
from agent_runner.models import StepContext
from agent_runner.utils import parse_key_value, parse_scalar


def load_yaml(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = {
        "version": None,
        "execution": {},
        "steps": [],
        "stages": [],
    }
    section: str | None = None
    stage_subsection: str | None = None
    current_step: dict[str, Any] | None = None
    current_stage: dict[str, Any] | None = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()

        if indent == 0:
            stage_subsection = None
            current_step = None
            if line.startswith("version:"):
                _, value = parse_key_value(line)
                data["version"] = value
            elif line == "execution:":
                section = "execution"
            elif line == "steps:":
                section = "steps"
            elif line == "stages:":
                section = "stages"
            continue

        if section == "execution" and indent == 2:
            key, value = parse_key_value(line)
            data["execution"][key] = value
            continue

        if section == "steps":
            if indent == 2 and line.startswith("- "):
                key, value = parse_key_value(line[2:])
                current_step = {key: value}
                data["steps"].append(current_step)
                continue
            if indent == 4 and current_step is not None:
                key, value = parse_key_value(line)
                current_step[key] = value
                continue

        if section == "stages":
            if indent == 2 and line.startswith("- "):
                key, value = parse_key_value(line[2:])
                current_stage = {
                    key: value,
                    "required_documents": [],
                    "steps": {},
                }
                data["stages"].append(current_stage)
                stage_subsection = None
                continue

            if indent == 4 and current_stage is not None:
                if line == "required_documents:":
                    stage_subsection = "required_documents"
                    continue
                if line == "steps:":
                    stage_subsection = "steps"
                    continue
                key, value = parse_key_value(line)
                current_stage[key] = value
                stage_subsection = None
                continue

            if indent == 6 and current_stage is not None and stage_subsection == "required_documents":
                if line.startswith("- "):
                    current_stage["required_documents"].append(parse_scalar(line[2:]))
                continue

            if indent == 6 and current_stage is not None and stage_subsection == "steps":
                key, value = parse_key_value(line)
                current_stage["steps"][key] = value
                continue

    return data


def resolve_stage_id(matrix: dict[str, Any], state: dict[str, Any], stage_override: str | None) -> str:
    if stage_override:
        return stage_override

    for stage in matrix["stages"]:
        stage_id = stage["id"]
        if state["stages"][stage_id].get("status") != "completed":
            return stage_id
    raise SystemExit("All stages are already completed.")


def build_step_context(matrix: dict[str, Any], stage_id: str, step_id: str) -> StepContext:
    stages = {stage["id"]: stage for stage in matrix["stages"]}
    stage = stages.get(stage_id)
    if not stage:
        raise SystemExit(f"Unknown stage id: {stage_id}")

    steps = {step["id"]: step["agent"] for step in matrix["steps"]}
    agent_id = steps.get(step_id)
    if not agent_id:
        raise SystemExit(f"Unknown step id: {step_id}")

    planner_id, planner_path = planner_file_path(matrix)
    executor_id, executor_path = executor_file_path(matrix)
    stage_step_matrix = stage["steps"]
    required_step_ids = [
        current_step_id
        for current_step_id, mode in stage_step_matrix.items()
        if mode == "required"
    ]
    return StepContext(
        stage_id=stage_id,
        stage_name=stage["name"],
        stage_file=ROOT_DIR / stage["file"],
        step_id=step_id,
        agent_id=agent_id,
        agent_file=ROOT_DIR / ".agents" / f"{agent_id}.md",
        planner_id=planner_id,
        planner_file=planner_path,
        executor_id=executor_id,
        executor_file=executor_path,
        required_documents=[ROOT_DIR / value for value in stage.get("required_documents", [])],
        required_step_ids=required_step_ids,
    )


def get_stage_steps_in_order(matrix: dict[str, Any], stage_id: str) -> list[str]:
    stage = next(stage for stage in matrix["stages"] if stage["id"] == stage_id)
    stage_step_matrix = stage["steps"]
    ordered = []
    for step in matrix["steps"]:
        step_id = step["id"]
        if step_id in stage_step_matrix:
            ordered.append(step_id)
    return ordered


def should_run_step(step_state: dict[str, Any]) -> bool:
    return step_state.get("status", "pending") in {"pending", "failed", "blocked"}
