from fastapi import FastAPI
from datetime import datetime

app = FastAPI(
    title="BijutsuBase API",
    description="API for managing anime-style art in cloud storage",
    version="0.1.0"
)


@app.get("/health")
async def health_check():
    """Health check endpoint to verify the API is running."""
    return {
        "status": "healthy",
        "message": "BijutsuBase is running",
        "timestamp": datetime.utcnow().isoformat()
    }
