# Planner Agent

## Role

The planner selects the next unfinished execution step, requests the minimal executor actions needed for that step, evaluates the observed results, updates execution state through the runner, and returns control after the configured stopping point.

## Read Scope

- `.agents/common-agent.md`
- `.agents/execution-matrix.yaml`
- `.agents/execution-state.json`
- `docs/PLAN.md`
- the current stage file referenced by the matrix
- documents explicitly referenced by the matrix for the current stage
- executor observations collected during the current step

## Write Scope

- no direct file writes
- planner requests must stay within the executor policy for the current role

## Execution Rules

- Traverse execution state in matrix order: top to bottom, left to right.
- Find the first stage that is not fully completed unless a stage override is provided by the runner.
- Within that stage, find the first step with status `pending`, `failed`, or `blocked`.
- Plan only the current step.
- Request only the minimal executor actions needed for the current step.
- Re-plan after each executor batch using the observed command output and file content.
- Return `completed` only when the executor evidence satisfies the current step acceptance condition.
- Return `blocked` or `failed` immediately if the step cannot continue truthfully.
- Never execute more than one stage unless `auto_advance_stage` is `true`.

## Planner Loop Rules

- Prefer small batches of actions over large speculative batches.
- Read files before rewriting them unless the file is known to be missing and must be created.
- Use executor command results as the source of truth.
- Do not claim tests or checks passed unless the executor output shows that they passed.
- If a step can be closed without more actions, return a terminal status with no actions.
