"""Tag serializers for BijutsuBase API."""
from pydantic import BaseModel


class TagResponse(BaseModel):
    """Response model for Tag objects."""
    
    name: str
    category: str
    count: int

    class Config:
        from_attributes = True

