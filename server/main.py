from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator

from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database.config import engine, get_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan context manager for FastAPI application.
    
    Handles startup and shutdown events for the database connection.
    """
    # Startup: verify database connection
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
    
    yield
    
    # Shutdown: dispose of the engine
    await engine.dispose()


app = FastAPI(
    title="BijutsuBase API",
    description="API for managing anime-style art in cloud storage",
    version="0.1.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check endpoint to verify the API and database are running."""
    # Execute a simple query to check database connectivity
    result = await db.execute(text("SELECT 1 as health_check"))
    db_healthy = result.scalar() == 1
    
    return {
        "status": "healthy" if db_healthy else "unhealthy",
        "message": "BijutsuBase is running",
        "database": "connected" if db_healthy else "disconnected",
        "timestamp": datetime.utcnow().isoformat()
    }
