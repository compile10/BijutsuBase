"""Pool models for BijutsuBase."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import String, Integer, DateTime, ForeignKey, Enum as SQLEnum, func, Index, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.config import Base

if TYPE_CHECKING:
    from models.file import File


class PoolCategory(str, enum.Enum):
    """Pool category enumeration."""
    SERIES = "series"
    COLLECTION = "collection"


class Pool(Base):
    """Pool model for grouping files."""
    
    __tablename__ = "pools"
    
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=True
    )
    category: Mapped[PoolCategory] = mapped_column(
        SQLEnum(PoolCategory),
        nullable=False,
        default=PoolCategory.SERIES,
        server_default=PoolCategory.SERIES.name
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
    
    # Relationship to pool members (files with order)
    members: Mapped[List["PoolMember"]] = relationship(
        "PoolMember",
        back_populates="pool",
        cascade="all, delete-orphan",
        order_by="PoolMember.order"
    )
    
    def __repr__(self) -> str:
        """String representation of Pool."""
        return f"<Pool(id={self.id}, name={self.name}, category={self.category.value})>"


class PoolMember(Base):
    """Association model between Pool and File with ordering."""
    
    __tablename__ = "pool_members"
    
    pool_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("pools.id", ondelete="CASCADE"),
        primary_key=True
    )
    file_sha256_hash: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("files.sha256_hash", ondelete="CASCADE"),
        primary_key=True
    )
    order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    # Relationships
    pool: Mapped["Pool"] = relationship("Pool", back_populates="members")
    file: Mapped["File"] = relationship("File", back_populates="pool_entries")
    
    __table_args__ = (
        Index("ix_pool_members_file_hash", "file_sha256_hash"),
        Index("ix_pool_members_pool_order", "pool_id", "order"),
    )
    
    def __repr__(self) -> str:
        """String representation of PoolMember."""
        return f"<PoolMember(pool_id={self.pool_id}, file_hash={self.file_sha256_hash[:8]}..., order={self.order})>"

