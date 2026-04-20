# AI Call QA & Sales Coach MVP Plan

## Goal

Build one working `post-call MVP` for this scenario:

`audio -> speech-to-text -> RAG -> analysis -> scorecard -> next best action -> API / webhook export`

The MVP is one complete `vertical slice` that can be launched, tested, and demonstrated end to end.

## Document Map

- System architecture: [ARCHITECTURE.md](ARCHITECTURE.md)
- Core contracts: [CONTRACTS.md](CONTRACTS.md)
- External integrations and interface contracts: [INTEGRATIONS.md](INTEGRATIONS.md)
- Security baseline: [SECURITY.md](SECURITY.md)
- Scaling boundary and post-MVP evolution: [SCALING.md](SCALING.md)
- Repository layout: [STRUCTURE.md](STRUCTURE.md)
- Stage completion criteria: [stages/README.md](stages/README.md)

## Stages

Stages are strict and sequential. No stage may be skipped. Detailed completion criteria are defined in the corresponding stage documents.

### Stage 0. Setup

- focus: project bootstrap and local runtime
- details: [Stage 0. Setup](stages/stage-0-setup.md)

### Stage 1. Database

- focus: domain model and persistence
- details: [Stage 1. Database](stages/stage-1-database.md)

### Stage 2. Transcription

- focus: audio upload, storage, and STT
- details: [Stage 2. Transcription](stages/stage-2-transcription.md)

### Stage 3. RAG

- focus: knowledge import, embeddings, and retrieval
- details: [Stage 3. RAG](stages/stage-3-rag.md)

### Stage 4. Analysis

- focus: structured analysis and review routing
- details: [Stage 4. Analysis](stages/stage-4-analysis.md)

### Stage 5. Export

- focus: API exposure, logging, and webhook delivery
- details: [Stage 5. Export](stages/stage-5-export.md)

## Global Rules

- only the `post-call` scenario is in scope
- no UI
- no realtime copilot
- no microservices
- no queue and no separate worker before the happy path works in one process
- no second vector store
- no second STT provider
- no second outbound channel
- no `Dify` or `LiveKit` integration
- no multi-tenant support, billing, auth, or advanced monitoring in the MVP
- external services must stay behind adapter interfaces
- prompts, schemas, and templates must remain outside service logic where applicable
- orchestration logic must remain inside `app-api`
- call lifecycle state and analysis review state must remain separate

Implementation details for these rules are defined in:

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [CONTRACTS.md](CONTRACTS.md)
- [INTEGRATIONS.md](INTEGRATIONS.md)
- [SECURITY.md](SECURITY.md)
- [SCALING.md](SCALING.md)

## MVP Acceptance

The MVP is ready when the following end-to-end scenario works:

1. `Docker Compose` is up.
2. `CallSession` is created.
3. A recording is uploaded.
4. A transcript is obtained through STT.
5. Relevant KB context is retrieved through `pgvector`.
6. Analysis is produced through `LangChain` and the approved tool API.
7. `summary`, `score`, `score_breakdown`, `objections`, `risks`, and `next_best_action` are visible.
8. Valid structured JSON is returned.
9. `confidence` and `needs_review` are visible.
10. The result is available through the API and can be delivered through the `webhook`.
11. Logs show the pipeline progression step by step.
