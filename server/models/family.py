"""Family models for BijutsuBase."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import String, DateTime, ForeignKey, func, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.config import Base

if TYPE_CHECKING:
    from models.file import File


class FileFamily(Base):
    """Family model grouping a parent file with its children."""
    
    __tablename__ = "file_families"
    
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4
    )
    parent_sha256_hash: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("files.sha256_hash", ondelete="CASCADE"),
        unique=True,  # A file can only be parent of one family
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    parent: Mapped["File"] = relationship(
        "File",
        back_populates="family_as_parent",
        foreign_keys=[parent_sha256_hash]
    )
    children: Mapped[List["File"]] = relationship(
        "File",
        back_populates="family_as_child",
        foreign_keys="File.parent_family_id"
    )
    
    def __repr__(self) -> str:
        """String representation of FileFamily."""
        return f"<FileFamily(id={self.id}, parent_hash={self.parent_sha256_hash[:8]}...)>"
