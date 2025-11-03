"""Tag models for BijutsuBase."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.file import File

from sqlalchemy import String, Integer, DateTime, ForeignKey, Index, func, Enum as SQLEnum, update, event
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
    count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0"
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
        return f"<Tag(id={self.id}, name={self.name}, category={self.category.value}, count={self.count})>"


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


@event.listens_for(FileTag, "after_insert")
def _increment_tag_count(mapper, connection, target: FileTag) -> None:
    """Increment tag count when a FileTag is created."""
    stmt = update(Tag).where(Tag.id == target.tag_id).values(count=Tag.count + 1)
    connection.execute(stmt)


@event.listens_for(FileTag, "after_delete")
def _decrement_tag_count(mapper, connection, target: FileTag) -> None:
    """Decrement tag count when a FileTag is deleted."""
    stmt = update(Tag).where(Tag.id == target.tag_id).values(count=func.greatest(0, Tag.count - 1))
    connection.execute(stmt)

