from __future__ import annotations

from agent_runner.utils import truncate_text


def print_banner(title: str) -> None:
    print(f"\n=== {title} ===")


def print_executor_observation(observation: dict[str, object]) -> None:
    print(f"executor ok: {observation.get('ok', False)}")
    if observation.get("path"):
        print(f"path: {observation['path']}")
    if observation.get("command"):
        print(f"command: {observation['command']}")
    if observation.get("entries"):
        print("entries:")
        for item in observation["entries"]:
            print(f"  - {item}")
    if observation.get("content"):
        print("content:")
        print(truncate_text(observation["content"], 800))
    if observation.get("stdout"):
        print("stdout:")
        print(truncate_text(observation["stdout"], 800))
    if observation.get("stderr"):
        print("stderr:")
        print(truncate_text(observation["stderr"], 800))
    if observation.get("error"):
        print("error:")
        print(truncate_text(observation["error"], 800))


def print_report(report: dict[str, object]) -> None:
    print(f"status: {report['status']}")
    print(f"agent: {report['agent']}")
    print(f"stage: {report['stage']}")
    print(f"step: {report['step']}")
    print(f"summary: {report['summary']}")
    print("files_changed:")
    for item in report["files_changed"] or ["-"]:
        print(f"  - {item}")
    print("commands_run:")
    for item in report["commands_run"] or ["-"]:
        print(f"  - {item}")
    print("completed_criteria:")
    for item in report["completed_criteria"] or ["-"]:
        print(f"  - {item}")
    print("remaining_criteria:")
    for item in report["remaining_criteria"] or ["-"]:
        print(f"  - {item}")
    print("blockers:")
    for item in report["blockers"] or ["-"]:
        print(f"  - {item}")
