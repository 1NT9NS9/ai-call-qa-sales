# Common Agent Rules

## Purpose

These rules apply to every agent launched through the execution matrix.

## Shared Execution Rules

- Execute exactly one stage per coordinator run.
- Do not start the next stage automatically unless `auto_advance_stage` is explicitly set to `true` in `.agents/execution-matrix.yaml`.
- Use `.agents/execution-state.json` as the single execution state source.
- Update only the state fields owned by the current task.
- Stop and report if the current task is blocked.

## Context Loading Rules

- Load only the documents explicitly listed for the current role.
- Load only the current stage file from `docs/stages/`.
- Load additional documents only if the role file explicitly allows them.
- Do not load unrelated stage files.

## Reporting Format

Return a structured completion report with:

- `agent`
- `stage`
- `step`
- `status`
- `files_changed`
- `commands_run`
- `completed_criteria`
- `remaining_criteria`
- `blockers`

## Repository Safety Rules

- Do not change files outside the role write scope.
- Do not start the next execution step.
- Do not mark a step as `completed` unless its acceptance condition is satisfied.
- Do not rewrite or relax the current stage criteria.
