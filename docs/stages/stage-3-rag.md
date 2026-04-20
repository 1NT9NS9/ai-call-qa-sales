# Stage 3. RAG

## Objective

Provide relevant knowledge-base context for analysis.

## In Scope

- prepare `5-10` test documents
- implement knowledge-base import
- generate embeddings
- store vectors in `pgvector`
- implement vector search
- implement `RAGService`

## Required Deliverables

- knowledge-base import flow
- stored vectors
- retrieval flow

## Exit Criteria

Stage 3 is complete only when all of the following are true:

- the repository contains a small test knowledge base
- knowledge documents can be imported into the system
- documents are chunked into retrievable units
- embeddings are generated for the stored chunks
- vectors are stored in `pgvector`
- `RAGService` can search stored chunks
- a transcript-derived query returns relevant knowledge chunks

## Readiness For Stage 4

Work may proceed to Stage 4 only when:

- retrieval produces usable context for the happy path
- imported knowledge and vector search are stable
- no second vector store has been introduced

## Stage Constraints

- use `pgvector` only
- do not add a second vector store
