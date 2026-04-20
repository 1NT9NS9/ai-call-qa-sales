# Stage 0. Setup

## Objective

Establish a runnable local project skeleton for the MVP.

## In Scope

- initialize `FastAPI`
- add `Dockerfile`
- add `docker-compose.yml`
- connect `PostgreSQL`
- enable `pgvector`
- define `.env.example`
- add `/health`
- add mounted audio storage volume

## Required Deliverables

- backend container definition
- database container definition
- health endpoint
- local startup instructions

## Exit Criteria

Stage 0 is complete only when all of the following are true:

- `docker compose up` starts the backend and database without manual fixes
- the backend process starts successfully
- the database process starts successfully
- `GET /health` returns a successful response
- mounted audio storage is configured and available to the backend
- `.env.example` contains the required local configuration keys

## Readiness For Stage 1

Work may proceed to Stage 1 only when:

- the repository skeleton is stable
- API bootstrap and database bootstrap are operational
- no business-domain behavior beyond bootstrap support has been introduced

## Stage Constraints

- do not implement business logic beyond bootstrap needs
- do not add external integrations
