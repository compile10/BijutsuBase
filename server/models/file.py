"""File model for BijutsuBase."""
from __future__ import annotations

import enum
import os
from datetime import datetime
from typing import TYPE_CHECKING, Optional


if TYPE_CHECKING:
    from models.tag import Tag

from sqlalchemy import String, Integer, DateTime, Boolean, func, event, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from database.config import Base


class Rating(str, enum.Enum):
    """Rating enum for file content rating."""
    SAFE = "safe"
    SENSITIVE = "sensitive"
    QUESTIONABLE = "questionable"
    EXPLICIT = "explicit"


class File(Base):
    """File model for file storage and metadata."""
    
    __tablename__ = "files"
    
    sha256_hash: Mapped[str] = mapped_column(
        String(64),
        primary_key=True
    )
    md5_hash: Mapped[str] = mapped_column(
        String(32),
        nullable=False
    )
    file_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    file_ext: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )
    file_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    width: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )
    height: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )
    rating: Mapped[Rating] = mapped_column(
        SQLEnum(Rating),
        nullable=False,
        default=Rating.EXPLICIT,
        server_default=Rating.EXPLICIT.name  # Err on the side of caution
    )
    date_added: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    source: Mapped[Optional[str]] = mapped_column(
        String(2048),
        nullable=True
    )

    ai_generated: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false"
    )
    
    # Relationship to tags through junction table
    tags: Mapped[list["Tag"]] = relationship(
        secondary="file_tags",
        back_populates="files"
    )
    
    def __repr__(self) -> str:
        """String representation of File."""
        return f"<File(sha256_hash={self.sha256_hash[:8]}..., filename={self.original_filename})>"


@event.listens_for(File, "before_insert")
def _generate_thumbnail_before_insert(mapper, connection, target: File) -> None:
    """
    Generate and save thumbnail before inserting File record.
    
    Only generates thumbnails for image and video files.
    Raises exception if thumbnail generation fails.
    """
    from utils.file_storage import generate_file_path
    from utils.thumbnail_gen import generate_thumbnail, generate_video_thumbnail
    
    # Get file path
    file_path = generate_file_path(target.sha256_hash, target.file_ext)
    
    # Generate thumbnail based on file type
    try:
        if target.file_type.startswith("image/"):
            thumbnail_content = generate_thumbnail(file_path)
        elif target.file_type.startswith("video/"):
            thumbnail_content = generate_video_thumbnail(file_path)
        else:
            return  # Should not reach here due to check above, but just in case
    except Exception as e:
        raise RuntimeError(f"Failed to generate thumbnail: {str(e)}") from e
    
    # Generate thumbnail path (always WebP format)
    thumbnail_path = generate_file_path(target.sha256_hash, "webp", thumb=True)
    
    # Create parent directories if they don't exist
    thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write thumbnail to disk
    thumbnail_path.write_bytes(thumbnail_content)


@event.listens_for(File, "after_delete")
def _delete_file_after_delete(mapper, connection, target: File) -> None:
    """
    Delete file from disk after deleting File record.
    """
    try:
        from utils.file_storage import delete_thumbnail_from_disk, delete_file_from_disk

        delete_file_from_disk(target)
        delete_thumbnail_from_disk(target)
    except (ValueError, OSError):
        # Silently handle errors (file might not exist, etc.)
        pass

