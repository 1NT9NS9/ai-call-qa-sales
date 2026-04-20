from __future__ import annotations

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
AGENTS_DIR = ROOT_DIR / ".agents"
MATRIX_PATH = AGENTS_DIR / "execution-matrix.yaml"
STATE_PATH = AGENTS_DIR / "execution-state.json"
COMMON_AGENT_PATH = AGENTS_DIR / "common-agent.md"
PLANNER_AGENT_PATH = AGENTS_DIR / "planner-agent.md"
EXECUTOR_AGENT_PATH = AGENTS_DIR / "executor-agent.md"
LEGACY_COORDINATOR_AGENT_PATH = AGENTS_DIR / "coordinator-agent.md"
EXECUTOR_POLICY_PATH = AGENTS_DIR / "executor-policy.json"
EXECUTION_STATUS_OUTPUT_PATH = ROOT_DIR / "docs" / "EXECUTION-STATUS.md"
STEP_ORDER = ["test", "code", "verify", "cleanup", "final-verify"]
STATUS_ICON = {
    "pending": "P",
    "in_progress": "WIP",
    "completed": "OK",
    "blocked": "BLOCK",
    "failed": "FAIL",
}
DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-5.3-codex"
DEFAULT_REASONING_EFFORT = "high"
DEFAULT_MAX_ITERATIONS = 8
MAX_ACTIONS_PER_TURN = 5
PLANNER_STATUSES = {"in_progress", "completed", "blocked", "failed"}
FINAL_STATUSES = {"completed", "blocked", "failed"}
STOP_STATUSES = {"blocked", "failed"}
REPORT_KEYS = {
    "agent",
    "stage",
    "step",
    "status",
    "summary",
    "files_changed",
    "commands_run",
    "completed_criteria",
    "remaining_criteria",
    "blockers",
}
PLANNER_RESPONSE_KEYS = {
    "status",
    "summary",
    "actions",
    "completed_criteria",
    "remaining_criteria",
    "blockers",
}
ACTION_TYPES = {"list_files", "read_file", "run_command", "write_file", "replace_text"}
COMMAND_DENYLIST = (
    "git reset --hard",
    "git checkout --",
    "rm -rf",
    "remove-item",
    "del /",
    "rmdir /s",
    "format ",
    "shutdown",
    "restart-computer",
    "stop-computer",
)
DEFAULT_EXECUTOR_POLICY = {
    "version": 1,
    "agents": {
        "test-agent": {
            "writable_paths": [
                "apps/app-api/tests",
                "data/demo",
            ]
        },
        "code-agent": {
            "writable_paths": [
                "apps/app-api/src",
                "apps/app-api/alembic",
                "apps/app-api/Dockerfile",
                "apps/app-api/requirements.txt",
                "apps/app-api/alembic.ini",
                "docker-compose.yml",
                ".env.example",
                "README.md",
                "storage/audio",
                "data/demo",
            ]
        },
        "verifier-agent": {"writable_paths": []},
    },
}
RUNTIME_INTEGRATION_NOTES = """
Runtime integration note:
- You are operating through a planner + local executor loop.
- If the loaded role documents conflict with this runtime note, follow this runtime note.
- Intermediate planner responses must follow the planner JSON schema requested by the runner.
- The runner composes the final execution-state report from your terminal status plus real executor evidence.
- Do not claim a file was changed or a command passed unless executor observations show it.
""".strip()
