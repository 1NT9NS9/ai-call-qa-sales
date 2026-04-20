from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_key_value(line: str) -> tuple[str, Any]:
    key, raw_value = line.split(":", 1)
    return key.strip(), parse_scalar(raw_value.strip())


def parse_scalar(value: str) -> Any:
    if value == "true":
        return True
    if value == "false":
        return False
    if value.isdigit():
        return int(value)
    return value


def truncate_text(text: str, limit: int = 4000) -> str:
    if len(text) <= limit:
        return text
    omitted = len(text) - limit
    return text[:limit] + f"\n...[truncated {omitted} chars]"


def sanitize_observation(observation: dict[str, Any]) -> dict[str, Any]:
    clean = json.loads(json.dumps(observation, ensure_ascii=False))
    for key in ("content", "stdout", "stderr", "error"):
        value = clean.get(key)
        if isinstance(value, str):
            clean[key] = truncate_text(value, 2000)
    return clean


def unique_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
