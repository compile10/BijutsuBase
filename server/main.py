import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from sqlalchemy import text


from database.config import engine
from api.health import router as health_router
from api.files import router as files_router
from api.upload import router as upload_router
from api.media import router as media_router
from api.tags import router as tags_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan context manager for FastAPI application.

    Handles startup and shutdown events for the database connection and ML models.
    """
    # Startup: verify database connection
    logger.info("Verifying database connection...")
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
    logger.info("Database connection verified successfully")

    # Startup: Initialize ONNX model (downloads if needed)
    logger.info("Initializing ONNX model...")
    from ml.config import onnx_model, sess_options
    onnx_model.initialize(sess_options=sess_options)
    logger.info("ONNX model initialized successfully")

    yield

    # Shutdown: dispose of the engine
    logger.info("Shutting down application...")
    await engine.dispose()
    logger.info("Database engine disposed successfully")


app = FastAPI(
    title="BijutsuBase API",
    description="API for managing anime-style art in cloud storage",
    version="0.1.0",
    lifespan=lifespan
)

logger.info("FastAPI application created")

# Register API routers
logger.info("Registering API routers")
app.include_router(health_router, prefix="/api")
app.include_router(files_router, prefix="/api")
app.include_router(upload_router, prefix="/api")
app.include_router(tags_router, prefix="/api")

# Register media serving router (no /api prefix)
app.include_router(media_router, prefix="/media")
logger.info("All routers registered successfully")
