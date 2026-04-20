from __future__ import annotations

import argparse
import json

from agent_runner.config import load_client, load_executor_policy
from agent_runner.console import print_banner, print_executor_observation, print_report
from agent_runner.constants import (
    DEFAULT_MAX_ITERATIONS,
    DEFAULT_MODEL,
    DEFAULT_REASONING_EFFORT,
    FINAL_STATUSES,
    MATRIX_PATH,
    ROOT_DIR,
    STATE_PATH,
    STOP_STATUSES,
    COMMON_AGENT_PATH,
)
from agent_runner.executor import LocalExecutor
from agent_runner.matrix import build_step_context, get_stage_steps_in_order, load_yaml, resolve_stage_id, should_run_step
from agent_runner.models import StepContext
from agent_runner.planner import build_planner_prompt, compose_report, run_planner_turn
from agent_runner.state import mark_in_progress, render_status_doc, update_state_for_step
from agent_runner.utils import load_json, sanitize_observation, write_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the execution matrix through a planner + local executor loop."
    )
    parser.add_argument(
        "--stage",
        default=None,
        help="Stage id to execute. If omitted, the first unfinished stage is used.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"OpenAI model to use. Default: {DEFAULT_MODEL}",
    )
    parser.add_argument(
        "--reasoning-effort",
        default=DEFAULT_REASONING_EFFORT,
        help=(
            "Reasoning effort passed to chat.completions.create. "
            f"Default: {DEFAULT_REASONING_EFFORT}"
        ),
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=DEFAULT_MAX_ITERATIONS,
        help=f"Maximum planner iterations per step. Default: {DEFAULT_MAX_ITERATIONS}",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print stage, step, planner, and executor context without calling the API.",
    )
    return parser.parse_args()


def run_step_with_executor(
    client,
    executor: LocalExecutor,
    context: StepContext,
    state: dict[str, object],
    executor_policy: dict[str, object],
    model: str,
    reasoning_effort: str,
    max_iterations: int,
) -> dict[str, object]:
    observations: list[dict[str, object]] = []
    files_changed: list[str] = []
    commands_run: list[str] = []

    for iteration in range(1, max_iterations + 1):
        prompt = build_planner_prompt(
            context=context,
            state=state,
            executor_policy=executor_policy,
            observations=observations,
            files_changed=files_changed,
            commands_run=commands_run,
            iteration=iteration,
            max_iterations=max_iterations,
        )
        planner_response = run_planner_turn(client, model, reasoning_effort, prompt)
        print(f"planner status: {planner_response['status']}")
        print(f"planner summary: {planner_response['summary']}")

        if planner_response["status"] in FINAL_STATUSES:
            return compose_report(context, planner_response, files_changed, commands_run)

        for index, action in enumerate(planner_response["actions"], start=1):
            print(f"action {index}: {json.dumps(action, ensure_ascii=False)}")
            observation = executor.execute(context, action)
            observations.append(sanitize_observation(observation))
            files_changed.extend(observation.get("changed_paths", []))
            commands_run.extend(observation.get("commands_run", []))
            print_executor_observation(observation)

    return {
        "agent": context.agent_id,
        "stage": context.stage_id,
        "step": context.step_id,
        "status": "failed",
        "summary": f"Planner exceeded the iteration limit ({max_iterations}) for this step.",
        "files_changed": files_changed,
        "commands_run": commands_run,
        "completed_criteria": [],
        "remaining_criteria": [],
        "blockers": [f"Planner exceeded the iteration limit ({max_iterations}) for this step."],
    }


def print_step_context(context: StepContext, executor_policy: dict[str, object]) -> None:
    print_banner(f"{context.step_id} -> {context.agent_id}")
    print(f"stage file: {context.stage_file.relative_to(ROOT_DIR)}")
    print(f"planner file: {context.planner_file.relative_to(ROOT_DIR)}")
    print(f"executor file: {context.executor_file.relative_to(ROOT_DIR)}")
    print("documents:")
    for path in [
        context.planner_file,
        context.executor_file,
        COMMON_AGENT_PATH,
        context.agent_file,
        context.stage_file,
        *context.required_documents,
    ]:
        print(f"  - {path.relative_to(ROOT_DIR)}")

    role_policy = executor_policy.get("agents", {}).get(context.agent_id, {})
    print("executor writable paths:")
    for item in role_policy.get("writable_paths", []):
        print(f"  - {item}")


def run_stage(
    stage_override: str | None,
    model: str,
    reasoning_effort: str,
    max_iterations: int,
    dry_run: bool,
) -> int:
    matrix = load_yaml(MATRIX_PATH)
    state = load_json(STATE_PATH)
    executor_policy = load_executor_policy()
    stage_id = resolve_stage_id(matrix, state, stage_override)
    stage_steps = get_stage_steps_in_order(matrix, stage_id)
    executor = LocalExecutor(ROOT_DIR, executor_policy)

    print_banner(f"Stage {stage_id}")
    print(f"matrix: {MATRIX_PATH}")
    print(f"state: {STATE_PATH}")
    print(f"planner: {matrix.get('execution', {}).get('planner', 'planner-agent')}")
    print(f"executor: {matrix.get('execution', {}).get('executor', 'executor-agent')}")
    print(f"model: {model}")
    print(f"dry_run: {dry_run}")

    client = None if dry_run else load_client()
    any_step_ran = False

    for step_id in stage_steps:
        step_state = state["stages"][stage_id]["steps"][step_id]
        if not should_run_step(step_state):
            print(f"skip {step_id}: status is {step_state['status']}")
            continue

        any_step_ran = True
        context = build_step_context(matrix, stage_id, step_id)
        print_step_context(context, executor_policy)

        if dry_run:
            continue

        mark_in_progress(state, context)
        write_json(STATE_PATH, state)
        render_status_doc()

        report = run_step_with_executor(
            client=client,
            executor=executor,
            context=context,
            state=state,
            executor_policy=executor_policy,
            model=model,
            reasoning_effort=reasoning_effort,
            max_iterations=max_iterations,
        )
        update_state_for_step(state, context, report)
        write_json(STATE_PATH, state)
        render_status_doc()
        print_report(report)

        if report["status"] in STOP_STATUSES:
            print_banner("Execution stopped")
            print(f"Step {step_id} finished with status {report['status']}")
            return 1

        stage_state = state["stages"][stage_id]
        if stage_state["status"] == "completed" and matrix["execution"]["stop_after_stage_completion"]:
            print_banner("Stage completed")
            print(f"Stage {stage_id} is completed and matrix requests stop.")
            return 0

    if not any_step_ran:
        print("No runnable steps found for the selected stage.")
    return 0


def main() -> None:
    args = parse_args()
    raise SystemExit(
        run_stage(
            stage_override=args.stage,
            model=args.model,
            reasoning_effort=args.reasoning_effort,
            max_iterations=args.max_iterations,
            dry_run=args.dry_run,
        )
    )
