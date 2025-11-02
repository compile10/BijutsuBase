"""File model for BijutsuBase."""
from __future__ import annotations

import os
from datetime import datetime
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from models.tag import Tag

from sqlalchemy import String, Integer, DateTime, func, event
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from database.config import Base


class File(Base):
    """File model for file storage and metadata."""
    
    __tablename__ = "files"
    
    # Non-persistent attribute for temporary file content storage
    _temp_file_content: Optional[bytes] = None
    
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
    date_added: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    # Relationship to tags through junction table
    tags: Mapped[list["Tag"]] = relationship(
        secondary="file_tags",
        back_populates="files"
    )
    
    def set_temp_file_content(self, content: bytes) -> None:
        """
        Store file content temporarily before insertion.
        
        This content will be saved to disk before inserting the File record.
        
        Args:
            content: File content as bytes
        """
        self._temp_file_content = content
    
    def __repr__(self) -> str:
        """String representation of File."""
        return f"<File(sha256_hash={self.sha256_hash[:8]}..., filename={self.original_filename})>"


# SQLAlchemy event listeners for automatic file handling
@event.listens_for(File, "before_insert")
def _save_file_before_insert(mapper, connection, target: File) -> None:
    """
    Save file to disk before inserting File record.
    
    Raises ValueError if no file content has been associated.
    """
    if target._temp_file_content is None:
        raise ValueError("No file content has been associated. Call set_temp_file_content() before inserting.")
    
    from utils.file_storage import save_file_to_disk
    save_file_to_disk(target, target._temp_file_content)
    # Clear temporary content after saving
    target._temp_file_content = None


@event.listens_for(File, "after_delete")
def _delete_file_after_delete(mapper, connection, target: File) -> None:
    """
    Delete file from disk after deleting File record.
    """
    from utils.file_storage import delete_file_from_disk
    try:
        delete_file_from_disk(target)
    except (ValueError, OSError):
        # Silently handle errors (file might not exist, etc.)
        pass

