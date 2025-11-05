## AGENTS.MD

This document orients AI agents and contributors to work effectively in the BijutsuBase codebase.

- **Project**: BijutsuBase — anime fanart online storage system (images/videos) with upload, tagging, and multi-device access.
- **Backend stack**: FastAPI, async SQLAlchemy, Alembic, PostgreSQL, Uvicorn, Astral `uv` for Python env/deps.
- **Frontend**: SvelteKit (Svelte 5), Tailwind CSS, Icons via `unplugin-icons`.
- **Proxy/deploy**: Nginx as reverse proxy; Docker Compose orchestrates all services.

### Project overview

- **Goal**: Provide an API and clients to upload and manage media (fanart images/videos), associate tags, and access across devices.
- **Current state**:
  - API service with FastAPI (`server/main.py`), DB connectivity, and health check.
  - Async SQLAlchemy configured via `DATABASE_URL` (`server/database/config.py`).
  - Alembic initial migration for `files`, `tags`, and `file_tags` (includes `rating`, `source`, `ai_generated`).
  - File upload endpoint streams to disk, validates MIME with `python-magic`, computes MD5/SHA256, extracts dimensions (PIL/OpenCV), and persists.
  - Automatic Danbooru metadata enrichment on upload (rating/source/tags) via `tagging/danbooru/*` with in-process caching.
  - Thumbnail generation (images and animated WebP for videos) on `before_insert`; disk cleanup on `after_delete`.
  - File search by tags (`/api/files/search`) returning thumbnail URLs.
  - Media serving under `/media/original/...` and `/media/thumb/...` (proxied by Nginx).
  - SvelteKit web client with upload modal and tag-based search UI.
- **Planned/expected** (not yet implemented):
  - Auth flows (signup/login, token issuance), full tag management endpoints, and object storage integration.

### Repository layout (high level)

- `server/`: FastAPI app, models, DB config, Alembic config, Dockerfile.
- `server/main.py`: FastAPI app entry with lifespan and router registration.
- `server/database/config.py`: async engine/session, `Base`, DI helper `get_db`.
- `server/models/`: SQLAlchemy models (`file.py`, `tag.py`).
- `server/api/`: API routers (`health.py`, `files.py`, `media.py`).
- `server/api/serializers/`: Pydantic serializers (e.g., `file.py`).
- `server/utils/`: Utilities (`file_storage.py`, `file_info.py`, `thumbnail_gen.py`).
- `server/tagging/`: Danbooru integration (`danbooru_client.py`, enrichment helpers).
- `server/alembic/`: migrations config and versions.
- `clients/bijutsubase-web/`: SvelteKit web client (SSR build for Docker).
- `nginx/nginx.conf`: reverse proxy for API (`/api`), media (`/media`) and web (all other routes).
- `docker-compose.yml`: Orchestrates `postgres`, `api`, `web`, and `nginx`.
- `scripts/`: Helper scripts (e.g., `upload.py` test uploader).

### Runtime and dependencies

- **Python**: pyproject declares `>=3.13`. Docker image uses Python 3.12. Prefer aligning to one version; if running locally, use 3.13.
- **Dependency manager**: Astral `uv`. Use `uv sync` and `uv run`.
- **Key libraries**:
  - Backend: `fastapi`, `uvicorn[standard]`, `sqlalchemy[asyncio]`, `psycopg[binary]`, `alembic`, `pillow`, `python-magic`, `opencv-python`, `httpx`, `pydantic`.
  - ML (present in deps, future use): `huggingface-hub`, `onnxruntime`, `numpy`.
- **Frontend**: `@sveltejs/kit`, `svelte@5`, `tailwindcss`, `virtua` (virtual list), `unplugin-icons`.

### Environment variables

- **DATABASE_URL**: Postgres connection URL. Examples:
  - Local host: `postgresql+psycopg://postgres:postgres@localhost:5432/bijutsubase`
  - In Docker: `postgresql+psycopg://postgres:postgres@postgres:5432/bijutsubase`
- Optional (Docker compose provides): `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`.
- In dev, SQLAlchemy engine uses `echo=True`; ensure it is `False` in production.

### Build and run

#### Local without Docker (API only)

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

- Health check: `curl http://localhost:8000/api/health`

#### Local with Docker Compose (API + Web + Proxy)

```bash
# Build and start services (postgres, api, web, nginx)
docker compose up --build

# Follow logs
docker compose logs -f api

# Stop
docker compose down
```

- Access via Nginx at `http://localhost:8000`
  - API proxied at `/api` (e.g., `/api/health`)
  - Media proxied at `/media`
  - Web app (SvelteKit SSR) serves all other routes

### Database and migrations (Alembic)

- Generate a new migration after model changes:

```bash
cd server
uv run alembic revision -m "describe change" --autogenerate
uv run alembic upgrade head
```

- Alembic uses the sync URL derived from `DATABASE_URL` via `get_sync_database_url()`.

### Current database schema

- **files**: sha256_hash (PK), md5_hash, file_size, original_filename, file_ext, file_type, width, height, rating enum, date_added, source, ai_generated
- **tags**: id (PK), name unique, category enum, count, created_at
- **file_tags**: file_sha256_hash (FK), tag_id (FK), created_at, with helpful indexes

### Code style guidelines

- **General**
  - Prefer clear, descriptive names: functions as verbs; variables as meaningful nouns.
  - Add explicit type hints on public APIs and function signatures.
  - Use early returns; avoid deep nesting beyond 2–3 levels.
  - Avoid try/except unless handling a known exceptional case; never swallow errors.
  - Keep comments minimal and only for non-obvious rationale, invariants, and caveats.
  - Match existing formatting; prefer multi-line over dense one-liners.

- **FastAPI**
  - Group endpoints by feature in routers; use DI for DB sessions: `Depends(get_db)`.
  - Validate request/response payloads with Pydantic models under `server/api/serializers/`.
  - Use appropriate status codes and structured error responses.
  - Routers are registered in `main.py`; `/media` router is mounted without `/api` prefix for file serving.

- **SQLAlchemy (async)**
  - Use the provided `AsyncSession` via `get_db()`; avoid creating ad-hoc engines/sessions.
  - Keep queries in repository/service layers where possible.
  - Commit only when a unit of work is complete.
  - `File` model uses SQLAlchemy event listeners (`before_insert` thumbnail generation; `after_delete` disk cleanup).

- **Migrations**
  - Never edit historical migrations; add new ones via `--autogenerate` and review diffs.

### Testing instructions

- There is no formal test suite yet. For now:
  - **Smoke**: `GET /api/health` → `healthy`, `database: connected`.
  - **DB**: `uv run alembic upgrade head` populates `files`, `tags`, `file_tags` with new columns.
  - **Upload**: `PUT /api/files/upload` with an image/video; confirm thumbnail created and Danbooru enrichment (when MD5 matches a Danbooru post).
  - **Search**: `GET /api/files/search?tags=...` returns `thumbnail_url` objects; spot check `/media/thumb/...` loads.
  - **Fetch/Delete**: `GET /api/files/{sha256}` and `DELETE /api/files/{sha256}` behave as expected.
  - Consider adding `pytest` and `httpx[async]` for API tests; prefer fixture-managed databases and transaction rollbacks.

Example quick checks:

```bash
curl -s http://localhost:8000/api/health | jq
psql "postgresql://postgres:postgres@localhost:5432/postgres" -c "\l"  # list DBs
curl -X PUT -F "file=@test.jpg" http://localhost:8000/api/files/upload | jq
curl -s "http://localhost:8000/api/files/search?tags=artist_name" | jq
```

### Security considerations

- **Authentication & passwords**
  - Store only hashed passwords (e.g., Argon2id or bcrypt via `passlib`). Never plaintext.
  - Use access tokens (e.g., JWT) with short lifetimes; rotate secrets.

- **Uploads**
  - Enforce strict content-type and size limits; verify file signatures with `python-magic`.
  - Store media in hash-based directory structure (`media/<original|thumb>/<first_two>/<next_two>/<hash>.<ext>`).
  - Sanitize metadata; reject executable content; validate only image/video MIME types.
  - Thumbnails are generated on ingest; originals and thumbnails are deleted on record deletion.

- **API and proxy hardening**
  - Apply CORS restrictions; rate limit auth/upload endpoints.
  - Use parameterized queries via SQLAlchemy ORM; never raw string SQL.
  - Disable SQLAlchemy `echo` in production; avoid leaking credentials in logs.
  - Nginx enforces `client_max_body_size 10240M`; tune as needed for your environment.

- **Secrets & config**
  - Load secrets from environment/secret manager; avoid committing secrets.
  - Separate dev/prod configs; distinct databases and credentials.

### Common tasks for agents

- **Add a new model**
  1) Create/modify SQLAlchemy model under `server/models/` using `Base`.
  2) Generate migration: `uv run alembic revision -m "add <model>" --autogenerate`.
  3) Upgrade DB: `uv run alembic upgrade head`.

- **Add a new API route**
  1) Create a router module (e.g., `server/api/tags.py`).
  2) Define request/response schemas (e.g., `server/api/serializers/tag.py`).
  3) Inject DB with `Depends(get_db)` and keep DB operations in a service layer.
  4) Include router in `main.py` with appropriate prefix.

- **Work with the DB (async)**
  - Use the injected `AsyncSession`:

```python
from fastapi import Depends, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.config import get_db
from models.file import File

router = APIRouter(prefix="/files", tags=["files"])

@router.get("/")
async def list_files(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(File))
    return result.scalars().all()
```

### API quick reference

- `GET /api/health` — API readiness and DB connectivity.
- `PUT /api/files/upload` — Upload image/video; validates type; computes hashes; extracts dimensions; persists; auto-enriches from Danbooru.
- `GET /api/files/search?tags=<space+separated+tags>` — Search files containing ALL tags; returns thumbnails.
- `GET /api/files/{sha256}` — Fetch file details including tags and computed URLs.
- `DELETE /api/files/{sha256}` — Delete file and associations; disk cleanup occurs.
- `GET /media/original/...` — Serve original media.
- `GET /media/thumb/...` — Serve generated WebP thumbnails.

### Notes for future work

- Align Python versions (Docker image vs. `pyproject.toml`).
- Add test suite (pytest, coverage) and CI.
- Implement auth, tag management endpoints, and object storage integration.

---

If something in this document drifts from the code, prefer the code and update this file accordingly.

