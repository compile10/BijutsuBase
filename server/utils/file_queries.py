"""Shared SQLAlchemy query helpers for loading File records."""
from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.interfaces import LoaderOption

from api.serializers.file import FileResponse
from models.family import FileFamily
from models.file import File as FileModel
from models.pool import PoolMember

FileRelation = Literal["tags", "pools", "family"]

FILE_RESPONSE_OPTIONS: dict[FileRelation, tuple[LoaderOption, ...]] = {
    "tags": (selectinload(FileModel.tags),),
    "pools": (selectinload(FileModel.pool_entries).selectinload(PoolMember.pool),),
    "family": (
        selectinload(FileModel.family_as_child).selectinload(FileFamily.parent),
        selectinload(FileModel.family_as_parent).selectinload(FileFamily.children),
    ),
}


def resolve_file_options(
    options: Iterable[FileRelation] | None = None,
) -> tuple[LoaderOption, ...]:
    """Return SQLAlchemy loader options for the requested relations (all if omitted or empty)."""
    selected = list(options) if options else list(FILE_RESPONSE_OPTIONS)
    unknown = [opt for opt in selected if opt not in FILE_RESPONSE_OPTIONS]
    if unknown:
        valid = ", ".join(FILE_RESPONSE_OPTIONS)
        raise ValueError(
            f"Unknown file relation option(s): {', '.join(unknown)}. Valid options: {valid}"
        )

    return tuple(
        loader
        for opt in dict.fromkeys(selected)
        for loader in FILE_RESPONSE_OPTIONS[opt]
    )


async def get_file_with_relations(
    db: AsyncSession,
    sha256: str,
    options: Iterable[FileRelation] | None = None,
) -> FileModel | None:
    """Fetch a File by SHA-256 with the requested relationships (all if options is empty/None)."""
    loader_options = resolve_file_options(options)
    result = await db.execute(
        select(FileModel)
        .options(*loader_options)
        .where(FileModel.sha256_hash == sha256)
    )
    return result.scalar_one_or_none()


async def get_file_response(
    db: AsyncSession,
    sha256: str,
    options: Iterable[FileRelation] | None = None,
) -> FileResponse:
    """Fetch a File by SHA-256 and serialize it as a FileResponse, or raise 404."""
    file_model = await get_file_with_relations(db, sha256, options=options)
    if file_model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )
    return FileResponse.model_validate(file_model)
