from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from sqlalchemy import text


from database.config import engine
from api.health import router as health_router
from api.files import router as files_router
from api.media import router as media_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan context manager for FastAPI application.
    
    Handles startup and shutdown events for the database connection and ML models.
    """
    # Startup: verify database connection
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
    
    # Startup: Initialize ONNX model (downloads if needed)
    print("Initializing ONNX model...")
    from ml.config import onnx_model, sess_options
    onnx_model.initialize(sess_options=sess_options)
    print(f"ONNX model initialized successfully")
    
    yield
    
    # Shutdown: dispose of the engine
    await engine.dispose()


app = FastAPI(
    title="BijutsuBase API",
    description="API for managing anime-style art in cloud storage",
    version="0.1.0",
    lifespan=lifespan
)

# Register API routers
app.include_router(health_router, prefix="/api")
app.include_router(files_router, prefix="/api")

# Register media serving router (no /api prefix)
app.include_router(media_router, prefix="/media")
