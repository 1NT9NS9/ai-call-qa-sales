# Scaling Notes

## Purpose

This document defines the current scaling boundary of the MVP and the expected evolution path after the happy path is stable.

Current system structure is defined in [ARCHITECTURE.md](ARCHITECTURE.md).
Repository ownership is defined in [STRUCTURE.md](STRUCTURE.md).
Integration boundaries are defined in [INTEGRATIONS.md](INTEGRATIONS.md).
Security requirements are defined in [SECURITY.md](SECURITY.md).

## Current MVP Boundary

The MVP shall remain:

- single service
- single-process for orchestration
- backend-centered
- synchronous on the happy path
- limited to one STT provider, one vector store, and one outbound channel

The MVP shall not introduce:

- queues
- separate workers
- microservices
- realtime processing
- multi-tenant isolation

## Expected Pressure Points

The first likely scaling limits are:

- long-running transcription latency
- LLM analysis latency
- webhook delivery latency or retries
- vector search growth as the knowledge base expands
- database load from transcripts, analysis payloads, and delivery events

## Post-MVP Evolution Path

If the happy path is stable and load requires it, the preferred order of evolution is:

1. isolate slow external calls behind clearer application boundaries
2. introduce asynchronous execution for transcription, analysis, or delivery
3. separate API request handling from background processing
4. add stronger observability for queue depth, latency, failure rate, and retry behavior
5. revisit storage strategy only after real bottlenecks are measured

## Non-Goals Before MVP Completion

The following shall not be added before MVP completion:

- distributed orchestration
- multiple application services for the same pipeline
- a second vector store
- a second STT provider
- a second export channel
- advanced autoscaling design

## Decision Rule

Scaling changes shall be introduced only when:

- the end-to-end happy path already works
- the bottleneck is measured, not assumed
- the change does not break the existing contract boundaries defined in [CONTRACTS.md](CONTRACTS.md)
