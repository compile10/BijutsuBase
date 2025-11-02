"""File model for BijutsuBase."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from models.tag import Tag

from sqlalchemy import String, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.config import Base


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
    
    def __repr__(self) -> str:
        """String representation of File."""
        return f"<File(sha256_hash={self.sha256_hash[:8]}..., filename={self.original_filename})>"

