## AGENTS.MD

This document orients AI agents and contributors to work effectively in the BijutsuBase codebase.

- **Project**: BijutsuBase — anime fanart online storage system (images/videos) with upload, tagging, and multi-device access.
- **Backend stack**: FastAPI, async SQLAlchemy, Alembic, PostgreSQL, Uvicorn, Astral `uv` for Python env/deps.
- **Deploy/dev**: Docker Compose for local services; health check at `/health`.

### Project overview

- **Goal**: Provide an API and clients to upload and manage media (fanart images/videos), associate tags, and access across devices.
- **Current state**:
  - API service scaffolded with FastAPI (`server/main.py`), DB connectivity, and health check.
  - Async SQLAlchemy configured with a Postgres URL via `DATABASE_URL` (`server/database/config.py`).
  - Alembic set up with an initial `users` table migration.
  - Docker Compose orchestrates `postgres` and `api` services.
- **Planned/expected** (not yet implemented):
  - Auth flows (signup/login, token issuance), media upload endpoints, tag management, and object storage integration.

### Repository layout (high level)

- `server/`: FastAPI app, models, DB config, Alembic config, Dockerfile.
- `server/main.py`: FastAPI app entry with lifespan and `/health`.
- `server/database/config.py`: async engine/session, `Base`, DI helper `get_db`.
- `server/models/`: SQLAlchemy models (e.g., `user.py`).
- `server/alembic/`: migrations config and versions.
- `docker-compose.yml`: `postgres` + `api` services for local dev.
- `clients/`: placeholder for frontend/clients (not configured here).

### Runtime and dependencies

- **Python**: pyproject currently declares `>=3.13`. The Docker image uses Python 3.12. Prefer aligning to one version; if running locally, use 3.13.
- **Dependency manager**: Astral `uv`. Use `uv sync` and `uv run`.
- **Key libraries**:
  - `fastapi`, `uvicorn[standard]`
  - `sqlalchemy[asyncio]`, `psycopg[binary]`
  - `alembic`

### Environment variables

- **DATABASE_URL**: Postgres connection URL. Examples:
  - Local host: `postgresql+psycopg://postgres:postgres@localhost:5432/bijutsubase`
  - In Docker: `postgresql+psycopg://postgres:postgres@postgres:5432/bijutsubase`
- Optional (Docker compose provides): `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`.
- In dev, SQLAlchemy engine uses `echo=True`; ensure it is `False` in production.

### Build and run

#### Local without Docker

```bash
# From repo root
cd server

# Install dependencies (creates/uses .venv)
uv sync

# Ensure Postgres is running locally and DATABASE_URL is set as needed
export DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/bijutsubase"

# Run migrations
uv run alembic upgrade head

# Start the API (reload enabled)
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

- Health check: `curl http://localhost:8000/health`

#### Local with Docker Compose

```bash
# Build and start services
docker compose up --build

# Follow logs
docker compose logs -f api

# Stop
docker compose down
```

- API: `http://localhost:8000` (health at `/health`).

### Database and migrations (Alembic)

- Generate a new migration after model changes:

```bash
cd server
uv run alembic revision -m "describe change" --autogenerate
uv run alembic upgrade head
```

- Alembic uses the sync URL derived from `DATABASE_URL` via `get_sync_database_url()`.

### Code style guidelines

- **General**
  - Prefer clear, descriptive names: functions as verbs; variables as meaningful nouns.
  - Add explicit type hints on public APIs and function signatures.
  - Use early returns; avoid deep nesting beyond 2–3 levels.
  - Avoid try/except unless handling a known exceptional case; never swallow errors.
  - Keep comments minimal and only for non-obvious rationale, invariants, and caveats.
  - Match existing formatting; prefer multi-line over dense one-liners.

- **FastAPI**
  - Group endpoints by feature in routers; use dependency injection for DB sessions: `Depends(get_db)`.
  - Validate request/response payloads with Pydantic models (add to `server/schemas/` when created).
  - Use appropriate status codes and structured error responses.

- **SQLAlchemy (async)**
  - Use the provided `AsyncSession` via `get_db()`; avoid creating ad-hoc engines/sessions.
  - Keep queries in repository/service layers; avoid mixing heavy DB logic inside route handlers.
  - Commit only in service layer when a unit of work is complete.

- **Migrations**
  - Never edit historical migrations; add new ones via `--autogenerate` and review diffs.

### Testing instructions

- There is no formal test suite yet. For now:
  - **Smoke**: `GET /health` should return status `healthy` with `database: connected`.
  - **DB**: Run `uv run alembic upgrade head` in a clean DB and ensure the `users` table exists.
  - Consider adding `pytest` and `httpx[async]` for API tests; prefer fixture-managed databases and transaction rollbacks.

Example quick checks:

```bash
curl -s http://localhost:8000/health | jq
psql "postgresql://postgres:postgres@localhost:5432/postgres" -c "\l"  # list DBs
```

### Security considerations

- **Authentication & passwords**
  - Store only hashed passwords (e.g., Argon2id or bcrypt via `passlib`). Never plaintext.
  - Use access tokens (e.g., JWT) with short lifetimes; rotate secrets.

- **Uploads**
  - Enforce strict content-type and size limits; verify file signatures (magic numbers).
  - Store media in object storage (e.g., S3/compatible) with presigned URLs; never trust client filenames.
  - Sanitize metadata; reject executable content.

- **API hardening**
  - Apply CORS restrictions; rate limit auth and upload endpoints.
  - Use parameterized queries via SQLAlchemy ORM; never raw string SQL.
  - Disable SQLAlchemy `echo` in production; avoid leaking credentials in logs.

- **Secrets & config**
  - Load secrets from environment/secret manager; avoid committing secrets.
  - Separate dev/prod configs; distinct databases and credentials.

### Common tasks for agents

- **Add a new model**
  1) Create/modify SQLAlchemy model under `server/models/` using `Base`.
  2) Generate migration: `uv run alembic revision -m "add <model>" --autogenerate`.
  3) Upgrade DB: `uv run alembic upgrade head`.

- **Add a new API route**
  1) Create a router module (e.g., `server/routers/media.py`).
  2) Define request/response schemas (e.g., `server/schemas/media.py`).
  3) Inject DB with `Depends(get_db)` and keep DB operations in a service layer.
  4) Include router in `main.py` with a versioned prefix (e.g., `/api/v1`).

- **Work with the DB (async)**
  - Use the injected `AsyncSession`:

```python
from fastapi import Depends, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.config import get_db
from models.user import User

router = APIRouter()

@router.get("/users")
async def list_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    return result.scalars().all()
```

### API quick reference

- `GET /health` — returns service readiness and DB connectivity.

### Notes for future work

- Align Python versions (Docker image vs. `pyproject.toml`).
- Introduce schemas, routers, and services directories to structure features.
- Add test suite (pytest, coverage) and CI.
- Implement auth, media upload endpoints, tag management, and storage integration.

---

If something in this document drifts from the code, prefer the code and update this file accordingly.

