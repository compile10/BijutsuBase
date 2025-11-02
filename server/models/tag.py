"""Tag models for BijutsuBase."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.file import File

from sqlalchemy import String, Integer, DateTime, ForeignKey, Index, func, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.config import Base


class TagCategory(str, Enum):
    """Tag category enumeration."""
    GENERAL = "General"
    ARTIST = "Artist"
    COPYRIGHT = "Copyright"
    CHARACTER = "Character"
    META = "Meta"


class Tag(Base):
    """Tag model for categorizing files."""
    
    __tablename__ = "tags"
    
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )
    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False
    )
    category: Mapped[TagCategory] = mapped_column(
        SQLEnum(TagCategory),
        nullable=False,
        default=TagCategory.GENERAL,
        server_default=TagCategory.GENERAL.name
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    # Relationship to files through junction table
    files: Mapped[list["File"]] = relationship(
        secondary="file_tags",
        back_populates="tags"
    )
    
    def __repr__(self) -> str:
        """String representation of Tag."""
        return f"<Tag(id={self.id}, name={self.name}, category={self.category.value})>"


class FileTag(Base):
    """Junction table for many-to-many relationship between Files and Tags."""
    
    __tablename__ = "file_tags"
    
    file_sha256_hash: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("files.sha256_hash"),
        primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tags.id"),
        primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    __table_args__ = (
        Index('ix_file_tags_tag_id', 'tag_id'),
        Index('ix_file_tags_file_sha256_hash', 'file_sha256_hash'),
    )
    
    def __repr__(self) -> str:
        """String representation of FileTag."""
        return f"<FileTag(file_sha256_hash={self.file_sha256_hash[:8]}..., tag_id={self.tag_id})>"

