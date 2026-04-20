# Coordinator Agent

## Role

The coordinator selects the next unfinished execution step, launches the correct role agent, waits for the result, updates execution state, and returns control to the user after the configured stopping point.

## Read Scope

- `.agents/common-agent.md`
- `.agents/execution-matrix.yaml`
- `.agents/execution-state.json`
- `docs/PLAN.md`
- the current stage file referenced by the matrix
- documents explicitly referenced by the matrix for the current stage

## Write Scope

- `.agents/execution-state.json`

## Execution Rules

- Traverse execution state in matrix order: top to bottom, left to right.
- Find the first stage that is not fully completed.
- Within that stage, find the first step with status `pending`, `failed`, or `blocked`.
- Launch only the agent assigned to that step.
- Wait for that agent to finish before continuing.
- Update `.agents/execution-state.json` from the returned report.
- If a step finishes with `blocked` or `failed`, stop and report to the user.
- If all steps in the current stage are `completed`, act according to matrix settings:
  - if `stop_after_stage_completion` is `true`, stop and report to the user
  - if `auto_advance_stage` is `true`, continue to the next stage
- Never execute more than one stage unless `auto_advance_stage` is `true`

## Step Dispatch Rules

- Dispatch `test` to `test-agent`
- Dispatch `code` to `code-agent`
- Dispatch `verify` to `verifier-agent`
- Dispatch `cleanup` to `code-agent`
- Dispatch `final-verify` to `verifier-agent`

## Completion Rule

- Report stage completion only when every required step in the current stage is `completed`.
