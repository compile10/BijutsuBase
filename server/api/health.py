"""Health check router for BijutsuBase API."""
from datetime import datetime
from time import timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database.config import get_db


router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check endpoint to verify the API and database are running."""
    # Execute a simple query to check database connectivity
    result = await db.execute(text("SELECT 1 as health_check"))
    db_healthy = result.scalar() == 1
    
    return {
        "status": "healthy" if db_healthy else "unhealthy",
        "message": "BijutsuBase is running",
        "database": "connected" if db_healthy else "disconnected",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

