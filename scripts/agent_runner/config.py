from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from agent_runner.constants import (
    DEFAULT_BASE_URL,
    DEFAULT_EXECUTOR_POLICY,
    EXECUTOR_AGENT_PATH,
    EXECUTOR_POLICY_PATH,
    LEGACY_COORDINATOR_AGENT_PATH,
    ROOT_DIR,
)
from agent_runner.utils import load_json


def load_client() -> OpenAI:
    load_dotenv(ROOT_DIR / ".env")
    api_key = load_env_required("OPENAI_API_KEY")
    base_url = load_env_optional("OPENAI_BASE_URL") or DEFAULT_BASE_URL
    return OpenAI(api_key=api_key, base_url=base_url)


def load_env_required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"{name} is not set in the root .env file.")
    return value


def load_env_optional(name: str) -> str:
    return os.getenv(name, "").strip()


def load_executor_policy() -> dict[str, Any]:
    if EXECUTOR_POLICY_PATH.exists():
        return load_json(EXECUTOR_POLICY_PATH)
    return DEFAULT_EXECUTOR_POLICY


def planner_file_path(matrix: dict[str, Any]) -> tuple[str, Path]:
    planner_id = str(matrix.get("execution", {}).get("planner", "planner-agent"))
    candidate = ROOT_DIR / ".agents" / f"{planner_id}.md"
    if candidate.exists():
        return planner_id, candidate

    if planner_id == "planner-agent" and LEGACY_COORDINATOR_AGENT_PATH.exists():
        return planner_id, LEGACY_COORDINATOR_AGENT_PATH

    return planner_id, candidate


def executor_file_path(matrix: dict[str, Any]) -> tuple[str, Path]:
    executor_id = str(matrix.get("execution", {}).get("executor", "executor-agent"))
    candidate = ROOT_DIR / ".agents" / f"{executor_id}.md"
    if candidate.exists():
        return executor_id, candidate
    if executor_id == "executor-agent" and EXECUTOR_AGENT_PATH.exists():
        return executor_id, EXECUTOR_AGENT_PATH
    return executor_id, candidate
