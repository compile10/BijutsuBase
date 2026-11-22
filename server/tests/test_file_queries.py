"""Unit tests for shared File query helpers."""
from __future__ import annotations

import unittest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from models.family import FileFamily
from models.file import File as FileModel, ProcessingStatus, Rating, TagSource
from models.pool import Pool, PoolCategory, PoolMember
from models.tag import Tag, TagCategory
from utils.file_queries import (
    FILE_RESPONSE_OPTIONS,
    get_file_response,
    get_file_with_relations,
    resolve_file_options,
)


def _make_file(sha256: str, *, filename: str = "art.png") -> FileModel:
    return FileModel(
        sha256_hash=sha256,
        md5_hash="0" * 32,
        file_size=1234,
        original_filename=filename,
        file_ext="png",
        file_type="image/png",
        width=800,
        height=600,
        rating=Rating.SAFE,
        date_added=datetime(2026, 1, 1, tzinfo=timezone.utc),
        source="https://example.com/art",
        ai_generated=False,
        tag_source=TagSource.DANBOORU,
        processing_status=ProcessingStatus.COMPLETED,
        processing_error=None,
    )


class FileQueriesTests(unittest.IsolatedAsyncioTestCase):
    async def test_get_file_with_relations_defaults_to_all_options(self) -> None:
        expected = _make_file("a" * 64)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expected

        db = AsyncMock()
        db.execute.return_value = mock_result

        actual = await get_file_with_relations(db, "a" * 64)

        self.assertIs(actual, expected)
        db.execute.assert_awaited_once()
        stmt = db.execute.await_args.args[0]
        self.assertEqual(len(stmt._with_options), len(resolve_file_options()))

    async def test_get_file_with_relations_empty_options_loads_all(self) -> None:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db = AsyncMock()
        db.execute.return_value = mock_result

        await get_file_with_relations(db, "a" * 64, options=[])

        stmt = db.execute.await_args.args[0]
        self.assertEqual(len(stmt._with_options), len(resolve_file_options()))

    async def test_get_file_with_relations_subset_of_options(self) -> None:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db = AsyncMock()
        db.execute.return_value = mock_result

        await get_file_with_relations(db, "a" * 64, options=("tags", "family", "tags"))

        stmt = db.execute.await_args.args[0]
        expected_count = len(FILE_RESPONSE_OPTIONS["tags"]) + len(FILE_RESPONSE_OPTIONS["family"])
        self.assertEqual(len(stmt._with_options), expected_count)

    def test_resolve_file_options_rejects_unknown_option(self) -> None:
        with self.assertRaises(ValueError):
            resolve_file_options(["tags", "bogus"])  # type: ignore[list-item]

    async def test_get_file_response_raises_404_when_missing(self) -> None:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        db = AsyncMock()
        db.execute.return_value = mock_result

        with self.assertRaises(HTTPException) as ctx:
            await get_file_response(db, "b" * 64)

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.detail, "File not found")

    async def test_get_file_response_serializes_tags_pools_and_family(self) -> None:
        parent = _make_file("1" * 64, filename="parent.png")
        child = _make_file("2" * 64, filename="child.png")

        tag = Tag(name="1girl", category=TagCategory.GENERAL, count=5)
        pool_id = uuid.uuid4()
        pool = Pool(id=pool_id, name="Favorites", category=PoolCategory.COLLECTION)
        member = PoolMember(pool_id=pool_id, file_sha256_hash=parent.sha256_hash, order=1, pool=pool)
        family_id = uuid.uuid4()
        family = FileFamily(id=family_id, parent_sha256_hash=parent.sha256_hash)
        family.children = [child]

        parent.tags = [tag]
        parent.pool_entries = [member]
        parent.family_as_child = None
        parent.family_as_parent = family

        with patch("utils.file_queries.get_file_with_relations", new=AsyncMock(return_value=parent)):
            response = await get_file_response(AsyncMock(), parent.sha256_hash)

        self.assertEqual(response.sha256_hash, parent.sha256_hash)
        self.assertEqual([t.name for t in response.tags], ["1girl"])
        self.assertEqual([(p.id, p.name) for p in response.pools], [(pool_id, "Favorites")])
        self.assertEqual(response.family_id, str(family_id))
        self.assertIsNone(response.parent)
        self.assertEqual([c.sha256_hash for c in response.children], [child.sha256_hash])


if __name__ == "__main__":
    unittest.main()
