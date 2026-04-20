from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from agent_runner.constants import ACTION_TYPES, COMMAND_DENYLIST
from agent_runner.models import StepContext
from agent_runner.utils import truncate_text


class LocalExecutor:
    def __init__(self, root_dir: Path, policy: dict[str, Any]) -> None:
        self.root_dir = root_dir.resolve()
        self.policy = policy

    def execute(self, context: StepContext, action: dict[str, Any]) -> dict[str, Any]:
        action_type = action.get("type")
        base = {
            "type": action_type,
            "ok": False,
            "changed_paths": [],
            "commands_run": [],
        }
        if action_type not in ACTION_TYPES:
            base["error"] = f"Unsupported action type: {action_type}"
            return base

        try:
            if action_type == "list_files":
                return self._list_files(action)
            if action_type == "read_file":
                return self._read_file(action)
            if action_type == "run_command":
                return self._run_command(action)
            if action_type == "write_file":
                return self._write_file(context, action)
            if action_type == "replace_text":
                return self._replace_text(context, action)
        except Exception as exc:
            base["error"] = str(exc)
            return base

        base["error"] = f"Unhandled action type: {action_type}"
        return base

    def _resolve_path(self, raw_path: str, allow_missing: bool = False) -> Path:
        candidate = Path(raw_path)
        resolved = candidate.resolve() if candidate.is_absolute() else (self.root_dir / candidate).resolve()
        try:
            resolved.relative_to(self.root_dir)
        except ValueError as exc:
            raise ValueError(f"Path is outside the workspace: {raw_path}") from exc

        if not allow_missing and not resolved.exists():
            raise FileNotFoundError(f"Path does not exist: {raw_path}")
        return resolved

    def _ensure_writable(self, context: StepContext, resolved_path: Path) -> None:
        agent_policy = self.policy.get("agents", {}).get(context.agent_id, {})
        writable_paths = agent_policy.get("writable_paths", [])
        for raw_allowed in writable_paths:
            allowed = self._resolve_path(raw_allowed, allow_missing=True)
            if resolved_path == allowed or allowed in resolved_path.parents:
                return
        raise PermissionError(
            f"Path is not writable for {context.agent_id}: {resolved_path.relative_to(self.root_dir)}"
        )

    def _list_files(self, action: dict[str, Any]) -> dict[str, Any]:
        target = self._resolve_path(str(action.get("path", ".")))
        recursive = bool(action.get("recursive", False))
        limit = int(action.get("limit", 100))

        if target.is_file():
            entries = [str(target.relative_to(self.root_dir)).replace("\\", "/")]
        else:
            iterator = target.rglob("*") if recursive else target.iterdir()
            entries = [
                str(path.relative_to(self.root_dir)).replace("\\", "/")
                for path in iterator
                if path != target
            ]
            entries.sort()
            entries = entries[:limit]

        return {
            "type": "list_files",
            "ok": True,
            "path": str(target.relative_to(self.root_dir)).replace("\\", "/"),
            "entries": entries,
            "changed_paths": [],
            "commands_run": [],
        }

    def _read_file(self, action: dict[str, Any]) -> dict[str, Any]:
        target = self._resolve_path(str(action["path"]))
        content = target.read_text(encoding="utf-8")
        start_line = max(1, int(action.get("start_line", 1)))
        lines = content.splitlines()
        end_line = int(action.get("end_line", len(lines) if lines else 1))
        selected = "\n".join(lines[start_line - 1 : end_line])

        return {
            "type": "read_file",
            "ok": True,
            "path": str(target.relative_to(self.root_dir)).replace("\\", "/"),
            "start_line": start_line,
            "end_line": end_line,
            "content": selected,
            "changed_paths": [],
            "commands_run": [],
        }

    def _run_command(self, action: dict[str, Any]) -> dict[str, Any]:
        command = str(action["command"]).strip()
        lower_command = command.lower()
        if any(token in lower_command for token in COMMAND_DENYLIST):
            raise PermissionError(f"Command is blocked by executor policy: {command}")

        workdir = self._resolve_path(str(action.get("workdir", ".")))
        if not workdir.is_dir():
            raise NotADirectoryError(f"Workdir is not a directory: {workdir}")

        timeout_ms = int(action.get("timeout_ms", 30000))
        try:
            completed = subprocess.run(
                ["powershell", "-NoProfile", "-Command", command],
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=timeout_ms / 1000,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return {
                "type": "run_command",
                "ok": False,
                "command": command,
                "workdir": str(workdir.relative_to(self.root_dir)).replace("\\", "/"),
                "error": f"Command timed out after {timeout_ms} ms",
                "stdout": truncate_text(exc.stdout or ""),
                "stderr": truncate_text(exc.stderr or ""),
                "changed_paths": [],
                "commands_run": [command],
            }

        return {
            "type": "run_command",
            "ok": completed.returncode == 0,
            "command": command,
            "workdir": str(workdir.relative_to(self.root_dir)).replace("\\", "/"),
            "returncode": completed.returncode,
            "stdout": truncate_text(completed.stdout),
            "stderr": truncate_text(completed.stderr),
            "changed_paths": [],
            "commands_run": [command],
        }

    def _write_file(self, context: StepContext, action: dict[str, Any]) -> dict[str, Any]:
        target = self._resolve_path(str(action["path"]), allow_missing=True)
        self._ensure_writable(context, target)
        content = str(action["content"])
        previous = target.read_text(encoding="utf-8") if target.exists() else None
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        changed = previous != content

        return {
            "type": "write_file",
            "ok": True,
            "path": str(target.relative_to(self.root_dir)).replace("\\", "/"),
            "change": "unchanged" if not changed else "created" if previous is None else "updated",
            "changed_paths": [] if not changed else [str(target.relative_to(self.root_dir)).replace("\\", "/")],
            "commands_run": [],
        }

    def _replace_text(self, context: StepContext, action: dict[str, Any]) -> dict[str, Any]:
        target = self._resolve_path(str(action["path"]))
        self._ensure_writable(context, target)
        old_text = str(action["old_text"])
        new_text = str(action["new_text"])
        count = int(action.get("count", 1))
        content = target.read_text(encoding="utf-8")
        replacements = content.count(old_text)
        if replacements == 0:
            raise ValueError(f"Old text was not found in {target.relative_to(self.root_dir)}")

        if count <= 0:
            updated = content.replace(old_text, new_text)
            applied = replacements
        else:
            updated = content.replace(old_text, new_text, count)
            applied = min(count, replacements)

        target.write_text(updated, encoding="utf-8")
        return {
            "type": "replace_text",
            "ok": True,
            "path": str(target.relative_to(self.root_dir)).replace("\\", "/"),
            "replacements": applied,
            "changed_paths": [str(target.relative_to(self.root_dir)).replace("\\", "/")],
            "commands_run": [],
        }
