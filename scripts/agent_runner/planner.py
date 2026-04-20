from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from agent_runner.constants import (
    COMMON_AGENT_PATH,
    FINAL_STATUSES,
    MAX_ACTIONS_PER_TURN,
    PLANNER_RESPONSE_KEYS,
    PLANNER_STATUSES,
    REPORT_KEYS,
    RUNTIME_INTEGRATION_NOTES,
)
from agent_runner.models import StepContext
from agent_runner.utils import unique_preserve_order


def build_planner_prompt(
    context: StepContext,
    state: dict[str, Any],
    executor_policy: dict[str, Any],
    observations: list[dict[str, Any]],
    files_changed: list[str],
    commands_run: list[str],
    iteration: int,
    max_iterations: int,
) -> str:
    current_stage_state = state["stages"][context.stage_id]
    current_step_state = current_stage_state["steps"][context.step_id]
    documents = [
        ("planner-agent", context.planner_file.read_text(encoding="utf-8")),
        ("executor-agent", context.executor_file.read_text(encoding="utf-8")),
        ("common-agent", COMMON_AGENT_PATH.read_text(encoding="utf-8")),
        (context.agent_id, context.agent_file.read_text(encoding="utf-8")),
        ("stage-file", context.stage_file.read_text(encoding="utf-8")),
    ]
    for path in context.required_documents:
        documents.append((path.as_posix(), path.read_text(encoding="utf-8")))

    role_policy = executor_policy.get("agents", {}).get(context.agent_id, {})
    prompt_parts = [
        "You are the planner for one execution-matrix step in a local repository.",
        f"Planner id: {context.planner_id}",
        f"Executor id: {context.executor_id}",
        f"Current stage: {context.stage_id} ({context.stage_name})",
        f"Current step: {context.step_id}",
        f"Assigned role agent: {context.agent_id}",
        f"Planner iteration: {iteration}/{max_iterations}",
        "",
        "Return only valid JSON with this schema:",
        json.dumps(
            {
                "status": "in_progress | completed | blocked | failed",
                "summary": "short factual summary",
                "actions": [
                    {
                        "type": "list_files | read_file | run_command | write_file | replace_text",
                        "path": "relative/path",
                        "command": "for run_command only",
                        "workdir": "relative/workdir",
                        "timeout_ms": 10000,
                        "content": "full file content for write_file",
                        "old_text": "exact old text for replace_text",
                        "new_text": "exact new text for replace_text",
                        "count": 1,
                    }
                ],
                "completed_criteria": ["criterion"],
                "remaining_criteria": ["criterion"],
                "blockers": ["blocker"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        "",
        "Rules for this response:",
        f"- Use at most {MAX_ACTIONS_PER_TURN} actions in one response.",
        "- If status is `in_progress`, provide at least one action.",
        "- If status is terminal, provide no actions.",
        "- Do not invent file changes or command results. Use executor observations only.",
        "- Stay within the writable paths allowed for the current role.",
        "",
        "Runtime integration notes:",
        RUNTIME_INTEGRATION_NOTES,
        "",
        "Executor policy for the current role:",
        json.dumps(role_policy, ensure_ascii=False, indent=2),
        "",
        "Current execution state snapshot:",
        json.dumps(
            {
                "active_stage": state.get("active_stage"),
                "stage_state": current_stage_state,
                "current_step_state": current_step_state,
                "files_changed_so_far": files_changed,
                "commands_run_so_far": commands_run,
            },
            ensure_ascii=False,
            indent=2,
        ),
        "",
        "Executor observations from earlier iterations:",
        json.dumps(observations, ensure_ascii=False, indent=2),
        "",
        "Loaded documents:",
    ]

    for label, content in documents:
        prompt_parts.append(f"--- BEGIN {label} ---")
        prompt_parts.append(content)
        prompt_parts.append(f"--- END {label} ---")

    return "\n".join(prompt_parts)


def extract_json(text: str) -> dict[str, Any]:
    payload = text.strip()
    if payload.startswith("```"):
        payload = payload.split("\n", 1)[1]
        payload = payload.rsplit("```", 1)[0].strip()
    return json.loads(payload)


def extract_planner_response(text: str) -> dict[str, Any]:
    data = extract_json(text)
    missing = PLANNER_RESPONSE_KEYS - data.keys()
    if missing:
        raise ValueError(f"Planner response is missing keys: {sorted(missing)}")
    status = data["status"]
    if status not in PLANNER_STATUSES:
        raise ValueError(f"Unsupported planner status: {status}")
    if not isinstance(data["actions"], list):
        raise ValueError("Planner response field `actions` must be a list.")
    if status == "in_progress" and not data["actions"]:
        raise ValueError("Planner returned `in_progress` without any actions.")
    if status in FINAL_STATUSES and data["actions"]:
        raise ValueError("Planner returned terminal status with actions.")
    if len(data["actions"]) > MAX_ACTIONS_PER_TURN:
        raise ValueError("Planner requested too many actions in one response.")
    return data


def run_planner_turn(
    client: OpenAI,
    model: str,
    reasoning_effort: str,
    prompt: str,
) -> dict[str, Any]:
    request: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }
    if reasoning_effort:
        request["reasoning_effort"] = reasoning_effort

    response = client.chat.completions.create(**request)
    content = response.choices[0].message.content or ""
    return extract_planner_response(content)


def compose_report(
    context: StepContext,
    planner_response: dict[str, Any],
    files_changed: list[str],
    commands_run: list[str],
) -> dict[str, Any]:
    report = {
        "agent": context.agent_id,
        "stage": context.stage_id,
        "step": context.step_id,
        "status": planner_response["status"],
        "summary": planner_response["summary"],
        "files_changed": unique_preserve_order(files_changed),
        "commands_run": unique_preserve_order(commands_run),
        "completed_criteria": planner_response["completed_criteria"],
        "remaining_criteria": planner_response["remaining_criteria"],
        "blockers": planner_response["blockers"],
    }
    missing = REPORT_KEYS - report.keys()
    if missing:
        raise ValueError(f"Final report is missing keys: {sorted(missing)}")
    return report
