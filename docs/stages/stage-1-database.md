# Stage 1. Database

## Objective

Define the domain model and persistence layer.

## In Scope

- create all core models
- add migrations
- implement `CallSession` creation
- persist lifecycle status
- persist analysis review fields

## Required Deliverables

- database schema
- migration files
- basic `CallSession` create flow

## Exit Criteria

Stage 1 is complete only when all of the following are true:

- all core entities required by [../CONTRACTS.md](../CONTRACTS.md) are represented in the persistence layer
- migration files exist and are sufficient to create the current schema
- a `CallSession` can be created through the application flow
- `CallSession.processing_status` is stored in the database
- analysis review fields are stored separately from lifecycle status

## Readiness For Stage 2

Work may proceed to Stage 2 only when:

- the domain model is stable enough to attach uploaded audio and transcript data
- persistence for `CallSession` is working end to end
- no STT, RAG, or analysis behavior has been introduced

## Stage Constraints

- do not implement STT, RAG, or analysis yet
