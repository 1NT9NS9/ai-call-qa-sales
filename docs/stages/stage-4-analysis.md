# Stage 4. Analysis

## Objective

Produce valid post-call analysis in the target schema.

## In Scope

- implement `AnalysisService`
- integrate `LangChain`
- externalize prompts and rubric
- implement the minimal tool API
- enable function calling for `retrieve_context` and `get_call_metadata`
- assemble prompt context
- validate JSON schema
- compute `confidence`
- add retry and review routing

## Required Deliverables

- working analysis pipeline
- valid structured output
- guardrails and review path

The target analysis schema and tool restrictions are defined in [../CONTRACTS.md](../CONTRACTS.md).

## Exit Criteria

Stage 4 is complete only when all of the following are true:

- `AnalysisService` runs against a real transcript and retrieved KB context
- prompts, rubric, and schema are stored outside service code
- the analysis layer uses only the approved tools: `retrieve_context` and `get_call_metadata`
- analysis output conforms to the target structured schema
- `confidence` is computed and stored
- invalid JSON triggers one retry
- repeated invalid output or low confidence routes the result into review mode
- a valid analysis result is persisted as `CallAnalysis`

## Readiness For Stage 5

Work may proceed to Stage 5 only when:

- the happy-path analysis flow is deterministic enough for API exposure
- the target analysis schema is stable
- review routing is implemented for invalid or weak outputs

## Stage Constraints

- do not add extra tools
- keep analysis deterministic around the fixed happy path
