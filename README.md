# BijutsuBase

BijutsuBase is a modern, self-hosted web application for organizing and storing large collections of anime-style art. It features booru-style tagging, search capabilities, and a high-performance UI.

## Features

*   **Media Organization**: Store and manage large collections of images and videos.
*   **Smart Tagging**:
    *   **Danbooru Integration**: Automatically identifies files by hash and fetches metadata (tags, ratings, source) directly from Danbooru.
    *   **AI Auto-Tagging**: Fallback on-device tagging using an ONNX model (e.g., WD 1.4 Tagger) for files not found online. Includes frame-sampling support for video files.
*   **Advanced Search**: Filter your collection by tags, rating (Safe, Questionable, Explicit), and other metadata.
*   **High-Performance UI**: Built with Svelte 5 and SvelteKit.
*   **Modern Backend**: Async Python backend using FastAPI and SQLAlchemy for robust performance.

## Tech Stack

### Backend (`/server`)
*   **Language**: Python 3.13+
*   **Framework**: FastAPI
*   **Database**: PostgreSQL (Async via SQLAlchemy + asyncpg/psycopg)
*   **ML/AI**: ONNX Runtime, OpenCV (for video processing)
*   **Package Management**: uv

### Frontend (`/clients/bijutsubase-web`)
*   **Framework**: Svelte 5 + SvelteKit
*   **Styling**: Tailwind CSS
*   **Language**: TypeScript
*   **Build Tool**: Vite

### Infrastructure
*   **Containerization**: Docker & Docker Compose
*   **Reverse Proxy**: Nginx

## Getting Started

### Option 1: Docker/Podman Compose (Recommended)

The easiest way to run BijutsuBase is using Docker Compose or Podman Compose.

1.  Clone the repository.
2.  Run the following command in the project root (change it to podman if needed):
    ```bash
    docker-compose up -d --build
    ```
3.  Access the application at `http://localhost:8000`.


The services included are:
*   `web`: SvelteKit frontend (internal port 3000)
*   `api`: FastAPI backend (internal port 8000)
*   `postgres`: Database
*   `nginx`: Reverse proxy exposing the app on host port 8000

### Option 2: Manual Setup

If you prefer running services locally for development:

#### Prerequisites
*   Python 3.13+ (and `uv` installed)
*   Node.js 20+
*   PostgreSQL 16+ running locally

#### 1. Database Setup
Ensure you have a PostgreSQL database running.
*   Default config expects: `postgresql://postgres:postgres@localhost:5432/bijutsubase`
*   If your credentials differ, export the `DATABASE_URL` environment variable.

#### 2. Backend Setup
```bash
cd server

# Install dependencies
uv sync

# Run database migrations
uv run alembic upgrade head

# Start the server
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

#### 3. Frontend Setup
```bash
cd clients/bijutsubase-web

# Install dependencies
npm install

# Start the development server
npm run dev
```

The frontend usually runs on `http://localhost:5173` in dev mode. You may need to configure the API URL if running separately from Nginx.

## Project Structure

*   `clients/bijutsubase-web/`: SvelteKit frontend application.
*   `server/`: Python backend application.
    *   `api/`: API routes and endpoints.
    *   `database/`: Database models and configuration.
    *   `ml/`: Machine learning configuration and models.
    *   `sources/`: External data source integrations (Danbooru, ONNX).
*   `nginx/`: Nginx configuration for the reverse proxy.
*   `docker-compose.yml`: Service orchestration.

