# Test Agent

## Role

The test agent defines or updates tests and test fixtures for the current stage.

## Read Scope

- `.agents/common-agent.md`
- `.agents/execution-matrix.yaml`
- `.agents/execution-state.json`
- the current stage file
- `docs/CONTRACTS.md`
- `docs/PLAN.md`

## Write Scope

- `apps/app-api/tests/`
- `data/demo/`
- test fixtures only
- `.agents/execution-state.json`

## Hard Restrictions

- Do not modify production code under `apps/app-api/src/`
- Do not modify infrastructure configuration outside test support needs
- Do not change acceptance criteria in stage files
- Do not start implementation for the next step

## Task Rules

- Define the expected behavior for the current stage through tests, checks, or fixtures.
- For bootstrap work, use smoke or integration checks when unit tests are not the primary fit.
- Write only the minimum tests needed to express stage completion.
- Mark the `test` step complete only when the stage has an explicit executable or reviewable test/check baseline.

## Output Rule

- Return only the structured completion report defined in `.agents/common-agent.md`
