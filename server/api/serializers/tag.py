"""Tag serializers for BijutsuBase API."""
from pydantic import BaseModel, computed_field, Field


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


class TagBrowseResponse(BaseModel):
    """Response model for browsing tags with an example thumbnail."""
    
    name: str
    count: int
    example_thumbnail: str | None = Field(exclude=True)  # sha256_hash of latest file (internal only)
    
    @computed_field
    @property
    def thumbnail_url(self) -> str | None:
        """
        Generate thumbnail URL using the file's hash.
        Returns None if example_thumbnail is None.
        """
        if self.example_thumbnail is None:
            return None
        
        from utils.file_storage import generate_file_path
        
        # Thumbnails are always WebP format
        thumbnail_path = generate_file_path(self.example_thumbnail, "webp", thumb=True)
        
        return "/" + str(thumbnail_path).replace("\\", "/")
    
    class Config:
        from_attributes = True
