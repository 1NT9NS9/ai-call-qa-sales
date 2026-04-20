# Integrations Specification

## Purpose

This document defines the external integration boundaries for the MVP and the internal interfaces that isolate them from core application logic.

## Scope

The MVP includes the following integration categories:

- STT provider
- embedding provider
- LLM provider
- outbound webhook target
- PostgreSQL with `pgvector`

The MVP does not include:

- a second provider for the same responsibility
- inbound third-party event connectors
- queue or worker integrations
- realtime integrations

The end-to-end runtime flow is defined in [ARCHITECTURE.md](ARCHITECTURE.md).
Data contracts used by these integrations are defined in [CONTRACTS.md](CONTRACTS.md).

## Integration Principles

- Every external service shall be accessed through an adapter interface.
- Domain and application logic shall depend on internal contracts, not provider SDKs.
- Only one provider shall exist for each responsibility in the MVP.
- Integration-specific request and response normalization shall happen inside adapters.

## Integration Map

### STT

- Purpose: convert uploaded audio into transcript segments.
- Internal boundary: `STTAdapter`
- Input: stored audio file path
- Output: ordered `TranscriptSegment[]`
- Ownership: `adapters/stt/`

### Embeddings

- Purpose: generate vectors for knowledge-base chunks.
- Internal boundary: `EmbeddingService`
- Input: chunk text collection
- Output: vector collection
- Ownership: `adapters/embeddings/`

### LLM And Analysis

- Purpose: generate structured post-call analysis.
- Internal boundary: analysis adapter behind `AnalysisService`
- Input: transcript, call metadata, and retrieved knowledge context
- Output: structured analysis payload
- Ownership: `adapters/llm/`

Tool restrictions for the analysis layer are defined in [CONTRACTS.md](CONTRACTS.md).

### Webhook Delivery

- Purpose: deliver the final analysis result outside the system.
- Internal boundary: webhook delivery adapter behind `ExportService`
- Input: normalized analysis payload
- Output: `DeliveryEvent`
- Ownership: `adapters/delivery/`

### Database

- Purpose: persist application state, transcript data, analysis data, delivery data, and vectors.
- Internal boundary: repositories and infrastructure DB layer
- Technology: `PostgreSQL` with `pgvector`
- Ownership: `infrastructure/db/`

## Required Integration Contracts

- `STTAdapter.transcribe(file_path) -> TranscriptSegment[]`
- `EmbeddingService.embed(texts) -> vector[]`
- `RAGService.index(documents) -> void`
- `RAGService.search(query, top_k) -> KnowledgeChunk[]`
- `AnalysisService.analyze(call_id) -> CallAnalysis`
- `ExportService.deliver(call_id) -> DeliveryEvent`

## Connector Constraints

- STT integration shall remain behind `STTAdapter`.
- Embedding generation shall store vectors in `pgvector` only.
- Analysis integration shall remain deterministic around the fixed happy path.
- Webhook delivery shall remain the only outbound export channel.
- Provider-specific logic shall not leak into `domain/` or `application/`.

Security requirements for these integrations are defined in [SECURITY.md](SECURITY.md).
Scaling boundaries for integration changes are defined in [SCALING.md](SCALING.md).
