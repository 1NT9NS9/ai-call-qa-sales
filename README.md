# AI Call QA & Sales Coach MVP

Repository scaffold aligned with `docs/STRUCTURE.md`.

## Quick start

Create a local `.env` file from `.env.example` before starting the stack.

If you use a local OpenAI-compatible proxy, set `OPENAI_BASE_URL` in `.env`.
Example:

```env
OPENAI_BASE_URL=http://127.0.0.1:8317/v1
```

```bash
docker compose up --build
```

Published ports are bound to `127.0.0.1` for local-only access.

Health check:

- `GET http://127.0.0.1:8000/health`

## Agent Runner

Dry run without API calls:

```bash
python scripts/agent_runner/run_stage_agents.py --dry-run
```

Real run:

```bash
python scripts/agent_runner/run_stage_agents.py
```

The real run requires:

- `OPENAI_API_KEY` in `.env`
- optional `OPENAI_BASE_URL` in `.env` if you use a proxy
- write access to the local workspace
- working local tools for commands the executor will run

## Before Pushing To Git

Check these points before publishing the repository:

- `.env` is not committed
- no real secrets are left in example files or docs
- `storage/audio/`, `data/demo/`, and local cache folders are not staged
- `python scripts/agent_runner/run_stage_agents.py --dry-run` passes
- `docker compose config` passes
- optional: `docker compose up --build` and `GET /health` pass locally

## Local utility scripts

- `scripts/api_start.py` is a direct OpenAI smoke script without proxy.
- `scripts/api_proxy.py` is a local OpenAI proxy smoke script for manual API checks.
- `python scripts/agent_runner/run_stage_agents.py --dry-run` prints the current planner/executor execution path for the first unfinished stage.
