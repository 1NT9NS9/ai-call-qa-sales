from __future__ import annotations

from agent_runner.constants import EXECUTION_STATUS_OUTPUT_PATH, STATE_PATH, STATUS_ICON, STEP_ORDER
from agent_runner.models import StepContext
from agent_runner.utils import load_json


def update_state_for_step(
    state: dict[str, object],
    context: StepContext,
    report: dict[str, object],
) -> None:
    state["active_stage"] = context.stage_id
    stage_state = state["stages"][context.stage_id]
    step_state = stage_state["steps"][context.step_id]
    step_state["status"] = report["status"]
    step_state["agent"] = report["agent"]
    step_state["summary"] = report["summary"]
    step_state["files_changed"] = report["files_changed"]
    step_state["commands_run"] = report["commands_run"]
    step_state["completed_criteria"] = report["completed_criteria"]
    step_state["remaining_criteria"] = report["remaining_criteria"]
    step_state["blockers"] = report["blockers"]
    stage_state["status"] = compute_stage_status(stage_state, context.required_step_ids)


def compute_stage_status(stage_state: dict[str, object], required_step_ids: list[str]) -> str:
    statuses = [stage_state["steps"][step_id].get("status", "pending") for step_id in required_step_ids]
    if any(status == "failed" for status in statuses):
        return "failed"
    if any(status == "blocked" for status in statuses):
        return "blocked"
    if required_step_ids and all(status == "completed" for status in statuses):
        return "completed"
    if any(status in {"completed", "in_progress"} for status in statuses):
        return "in_progress"
    return "pending"


def mark_in_progress(state: dict[str, object], context: StepContext) -> None:
    state["active_stage"] = context.stage_id
    stage_state = state["stages"][context.stage_id]
    stage_state["status"] = "in_progress"
    step_state = stage_state["steps"][context.step_id]
    step_state["status"] = "in_progress"
    step_state["summary"] = ""


def render_status_doc() -> None:
    state = load_json(STATE_PATH)
    EXECUTION_STATUS_OUTPUT_PATH.write_text(render_markdown(state), encoding="utf-8")


def sort_stage_ids(stage_ids: list[str]) -> list[str]:
    return sorted(stage_ids, key=lambda value: int(value.split("-")[1]))


def render_cell(step: dict[str, object]) -> str:
    status = step.get("status", "pending")
    icon = STATUS_ICON.get(status, status)
    agent = step.get("agent", "-")
    return f"{icon} `{status}`<br>`{agent}`"


def render_table(stages: dict[str, object]) -> list[str]:
    stage_ids = sort_stage_ids(list(stages.keys()))
    headers = ["Process"] + [f"`{stage_id}`<br>{stages[stage_id]['name']}" for stage_id in stage_ids]
    divider = ["---"] * len(headers)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(divider) + " |",
    ]

    for step_id in STEP_ORDER:
        row = [f"`{step_id}`"]
        for stage_id in stage_ids:
            row.append(render_cell(stages[stage_id]["steps"][step_id]))
        lines.append("| " + " | ".join(row) + " |")

    return lines


def render_stage_details(stages: dict[str, object]) -> list[str]:
    lines = ["## Stage Details", ""]
    for stage_id in sort_stage_ids(list(stages.keys())):
        stage = stages[stage_id]
        lines.append(f"### {stage_id} - {stage['name']}")
        lines.append("")
        lines.append(f"- status: `{stage.get('status', 'pending')}`")
        for step_id in STEP_ORDER:
            step = stage["steps"][step_id]
            lines.append(
                f"- {step_id}: `{step.get('status', 'pending')}` | "
                f"agent `{step.get('agent', '-')}` | "
                f"criteria {len(step.get('completed_criteria', []))} done | "
                f"blockers {len(step.get('blockers', []))}"
            )
        lines.append("")
    return lines


def render_markdown(state: dict[str, object]) -> str:
    stages = state["stages"]
    lines = [
        "# Execution Status",
        "",
        "Generated from `.agents/execution-state.json`.",
        "",
        "## Summary",
        "",
        f"- active stage: `{state.get('active_stage', '-')}`",
        f"- stop after stage completion: `{state.get('stop_after_stage_completion', False)}`",
        f"- auto advance stage: `{state.get('auto_advance_stage', False)}`",
        "",
        "## Matrix",
        "",
        *render_table(stages),
        "",
        "Legend: `P pending`, `WIP in_progress`, `OK completed`, `BLOCK blocked`, `FAIL failed`.",
        "",
        *render_stage_details(stages),
    ]
    return "\n".join(lines).strip() + "\n"
