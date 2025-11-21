"""Tag serializers for BijutsuBase API."""
from pydantic import BaseModel


class TagResponse(BaseModel):
    """Response model for Tag objects."""
    
    name: str
    category: str
    count: int

    class Config:
        from_attributes = True


class TagAssociateRequest(BaseModel):
    """Request model for associating a tag with a file."""
    
    file_sha256: str
    tag_name: str
    category: str


class TagDissociateRequest(BaseModel):
    """Request model for dissociating a tag from a file."""
    
    file_sha256: str
    tag_name: str


class BulkTagAssociateRequest(BaseModel):
    """Request model for associating a tag with multiple files."""
    file_hashes: list[str]
    tag_name: str
    category: str


class BulkTagDissociateRequest(BaseModel):
    """Request model for dissociating a tag from multiple files."""
    file_hashes: list[str]
    tag_name: str
