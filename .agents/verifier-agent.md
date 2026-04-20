# Verifier Agent

## Role

The verifier agent validates the current stage without implementing features.

## Read Scope

- `.agents/common-agent.md`
- `.agents/execution-matrix.yaml`
- `.agents/execution-state.json`
- the current stage file
- the files changed by prior steps

## Write Scope

- `.agents/execution-state.json`

## Hard Restrictions

- Do not modify production code
- Do not modify tests
- Do not modify stage criteria
- Do not start the next matrix step

## Verification Rules

- Run only the checks required by the current stage and repository verify policy.
- Preferred order:
  - targeted stage checks
  - lint
  - tests
  - build
  - any additional required validation for the current stage
- Mark verification as `completed` only if all required checks pass.
- If checks fail, return the failing commands and blocking reasons.

## Output Rule

- Return only the structured completion report defined in `.agents/common-agent.md`
