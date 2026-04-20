# Architecture

## Purpose

The project implements one backend-centered `post-call MVP` for the flow:

`audio -> speech-to-text -> RAG -> analysis -> scorecard -> next best action -> API / webhook export`

`app-api` is the single orchestrator and source of truth for pipeline state.

## Scope

- One service: `apps/app-api`
- One runtime flow in one process
- One outbound channel: `webhook`
- No UI, queues, workers, or microservices

## Technology Base

- `FastAPI` for API and orchestration
- `PostgreSQL` for primary storage
- `pgvector` for embeddings and retrieval
- One `STTAdapter` for transcription
- `LangChain` for analysis with structured output
- `Docker Compose` for local startup

Provider boundaries and integration contracts are defined in [INTEGRATIONS.md](INTEGRATIONS.md).
Lifecycle rules and object contracts are defined in [CONTRACTS.md](CONTRACTS.md).

## Core Flow

1. `POST /calls` creates `CallSession` with status `created`.
2. `POST /calls/{call_id}/audio` stores audio, runs STT, saves `TranscriptSegment`, and moves the call to `transcribed`.
3. `POST /knowledge/import` imports KB documents, chunks them, and stores embeddings in `pgvector`.
4. `POST /calls/{call_id}/analyze` retrieves KB context, runs `AnalysisService`, validates structured output, and stores `CallAnalysis`.
5. `ExportService` sends the result to a configured `webhook` and stores `DeliveryEvent`.
6. `GET /calls/{call_id}` returns current status and analysis result.

## Application Layers

- `api/` exposes REST endpoints.
- `application/` contains use cases, services, and orchestration.
- `domain/` contains entities, interfaces, and lifecycle rules.
- `infrastructure/` contains DB access, storage, and logging.
- `adapters/` isolates STT, embeddings, LLM, and webhook integrations.
- `resources/` stores prompts, schemas, and rubric outside service code.

Repository ownership and directory mapping are defined in [STRUCTURE.md](STRUCTURE.md).

Core objects and analysis contracts are defined in [CONTRACTS.md](CONTRACTS.md).
Detailed stage execution criteria are defined in [stages/README.md](stages/README.md).

## Architectural Constraints

- Only the `post-call` scenario is in scope.
- External services must stay behind adapter interfaces.
- Call lifecycle state and analysis review state must remain separate.
- No second STT provider, vector store, or export channel in the MVP.

Security controls for these constraints are defined in [SECURITY.md](SECURITY.md).
Scaling boundaries for these constraints are defined in [SCALING.md](SCALING.md).
