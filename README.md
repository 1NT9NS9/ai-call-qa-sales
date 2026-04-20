# AI Call QA & Sales Coach MVP

Repository scaffold aligned with `docs/STRUCTURE.md`.

## Quick start

Create a local `.env` file from `.env.example` before starting the stack.

```bash
docker compose up --build
```

Published ports are bound to `127.0.0.1` for local-only access.

Health check:

- `GET http://127.0.0.1:8000/health`

## Local utility scripts

- `apps/app-api/api_start.py` is a direct OpenAI smoke script without proxy.
- `apps/app-api/api_proxy.py` is a local OpenAI proxy smoke script for manual API checks.
- `python scripts/render_execution_status.py` renders `docs/EXECUTION-STATUS.md` from `.agents/execution-state.json`.
