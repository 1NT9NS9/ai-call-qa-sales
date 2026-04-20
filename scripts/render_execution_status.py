from __future__ import annotations

import json
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT_DIR / ".agents" / "execution-state.json"
OUTPUT_PATH = ROOT_DIR / "docs" / "EXECUTION-STATUS.md"
STEP_ORDER = ["test", "code", "verify", "cleanup", "final-verify"]
STATUS_ICON = {
    "pending": "P",
    "in_progress": "WIP",
    "completed": "OK",
    "blocked": "BLOCK",
    "failed": "FAIL",
}


def load_state() -> dict:
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def sort_stage_ids(stage_ids: list[str]) -> list[str]:
    return sorted(stage_ids, key=lambda value: int(value.split("-")[1]))


def render_cell(step: dict) -> str:
    status = step.get("status", "pending")
    icon = STATUS_ICON.get(status, status)
    agent = step.get("agent", "-")
    return f"{icon} `{status}`<br>`{agent}`"


def render_table(stages: dict) -> list[str]:
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


def render_stage_details(stages: dict) -> list[str]:
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


def render_markdown(state: dict) -> str:
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


def main() -> None:
    state = load_state()
    OUTPUT_PATH.write_text(render_markdown(state), encoding="utf-8")
    print(f"Rendered {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
