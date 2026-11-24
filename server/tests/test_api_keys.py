"""Tests for API key generation, hashing, authentication, and FastAPI dependencies."""
import os
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import mock

import httpx
from fastapi import Depends, FastAPI
from fastapi.security import HTTPAuthorizationCredentials

os.environ.setdefault("JWT_SECRET", "test-jwt-secret-for-unit-tests-only")

from auth.api_keys import (
    API_KEY_DISPLAY_PREFIX_LEN,
    API_KEY_PREFIX,
    authenticate_api_key,
    extract_api_key,
    generate_api_key,
    hash_api_key,
)
from auth.users import (
    _current_cookie_user_optional,
    current_active_user,
    current_superuser,
)
from api.api_keys import router as api_keys_router
from database.config import get_db
from models.api_key import ApiKey


def make_fake_db(row):
    """Build a mock AsyncSession returning `row` from execute(...).first()."""
    result = mock.MagicMock()
    result.first.return_value = row

    db = mock.AsyncMock()
    db.execute.return_value = result
    return db


class ApiKeyHelperTests(unittest.TestCase):
    def test_generate_api_key_format_and_hash(self) -> None:
        raw_key, key_prefix, key_hash = generate_api_key()

        self.assertTrue(raw_key.startswith(API_KEY_PREFIX))
        self.assertEqual(key_prefix, raw_key[:API_KEY_DISPLAY_PREFIX_LEN])
        self.assertEqual(len(key_hash), 64)
        self.assertEqual(key_hash, hash_api_key(raw_key))

        other_raw, _, other_hash = generate_api_key()
        self.assertNotEqual(raw_key, other_raw)
        self.assertNotEqual(key_hash, other_hash)

    def test_extract_api_key_from_bearer_credentials(self) -> None:
        bearer = HTTPAuthorizationCredentials(scheme="Bearer", credentials="  bb_from_bearer  ")
        blank = HTTPAuthorizationCredentials(scheme="Bearer", credentials="   ")
        self.assertEqual(extract_api_key(bearer), "bb_from_bearer")
        self.assertIsNone(extract_api_key(blank))
        self.assertIsNone(extract_api_key(None))


class AuthenticateApiKeyTests(unittest.IsolatedAsyncioTestCase):
    async def test_valid_key_authenticates_and_updates_last_used(self) -> None:
        raw_key, _, key_hash = generate_api_key()
        user = SimpleNamespace(id=uuid.uuid4(), is_active=True, is_superuser=False)
        api_key = SimpleNamespace(
            id=uuid.uuid4(),
            key_hash=key_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            last_used_at=None,
        )
        db = make_fake_db((api_key, user))

        authenticated, error = await authenticate_api_key(raw_key, db)

        self.assertIs(authenticated, user)
        self.assertIsNone(error)
        self.assertEqual(db.execute.await_count, 2)  # select + last_used_at update
        db.commit.assert_awaited_once()

    async def test_recent_last_used_skips_write(self) -> None:
        raw_key, _, key_hash = generate_api_key()
        user = SimpleNamespace(id=uuid.uuid4(), is_active=True, is_superuser=False)
        api_key = SimpleNamespace(
            id=uuid.uuid4(),
            key_hash=key_hash,
            expires_at=None,
            last_used_at=datetime.now(timezone.utc) - timedelta(seconds=10),
        )
        db = make_fake_db((api_key, user))

        authenticated, error = await authenticate_api_key(raw_key, db)

        self.assertIs(authenticated, user)
        self.assertIsNone(error)
        self.assertEqual(db.execute.await_count, 1)  # select only
        db.commit.assert_not_awaited()

    async def test_rejects_missing_expired_and_inactive(self) -> None:
        raw_key, _, key_hash = generate_api_key()
        now = datetime.now(timezone.utc)

        cases = {
            "not found": (None, "Invalid API key"),
            "expired": (
                (
                    SimpleNamespace(
                        id=uuid.uuid4(),
                        key_hash=key_hash,
                        expires_at=now - timedelta(seconds=1),
                        last_used_at=None,
                    ),
                    SimpleNamespace(id=uuid.uuid4(), is_active=True),
                ),
                "API key has expired",
            ),
            "inactive user": (
                (
                    SimpleNamespace(
                        id=uuid.uuid4(),
                        key_hash=key_hash,
                        expires_at=None,
                        last_used_at=None,
                    ),
                    SimpleNamespace(id=uuid.uuid4(), is_active=False),
                ),
                "User account is inactive",
            ),
        }

        for label, (row, expected_error) in cases.items():
            with self.subTest(label):
                db = make_fake_db(row)
                authenticated, error = await authenticate_api_key(raw_key, db)
                self.assertIsNone(authenticated)
                self.assertEqual(error, expected_error)
                db.commit.assert_not_awaited()


class FastApiDependencyTests(unittest.IsolatedAsyncioTestCase):
    def _build_app(self, *, cookie_user=None, api_key_row=None) -> FastAPI:
        app = FastAPI()
        fake_db = make_fake_db(api_key_row)

        async def override_get_db():
            yield fake_db

        async def override_cookie_user():
            return cookie_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[_current_cookie_user_optional] = override_cookie_user

        @app.get("/protected")
        async def protected(user=Depends(current_active_user)):
            return {"user_id": str(user.id)}

        @app.get("/admin")
        async def admin(user=Depends(current_superuser)):
            return {"user_id": str(user.id)}

        return app

    async def test_accepts_bearer_header(self) -> None:
        raw_key, _, key_hash = generate_api_key()
        user = SimpleNamespace(id=uuid.uuid4(), is_active=True, is_superuser=False)
        api_key = SimpleNamespace(
            id=uuid.uuid4(),
            key_hash=key_hash,
            expires_at=None,
            last_used_at=datetime.now(timezone.utc),
        )
        app = self._build_app(api_key_row=(api_key, user))

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/protected",
                headers={"Authorization": f"Bearer {raw_key}"},
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"user_id": str(user.id)})

    async def test_invalid_api_key_returns_401_without_falling_back_to_cookie(self) -> None:
        cookie_user = SimpleNamespace(id=uuid.uuid4(), is_active=True, is_superuser=False)
        app = self._build_app(cookie_user=cookie_user, api_key_row=None)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/protected",
                headers={"Authorization": "Bearer bb_bogus"},
            )
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json()["detail"], "Invalid API key")

    async def test_pipes_explicit_rejection_reason_to_http_401(self) -> None:
        raw_key, _, key_hash = generate_api_key()
        user = SimpleNamespace(id=uuid.uuid4(), is_active=True, is_superuser=False)
        expired_key = SimpleNamespace(
            id=uuid.uuid4(),
            key_hash=key_hash,
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
            last_used_at=None,
        )
        app = self._build_app(api_key_row=(expired_key, user))

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/protected",
                headers={"Authorization": f"Bearer {raw_key}"},
            )
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json()["detail"], "API key has expired")

    async def test_falls_back_to_cookie_user_when_no_api_key_header(self) -> None:
        cookie_user = SimpleNamespace(id=uuid.uuid4(), is_active=True, is_superuser=False)
        app = self._build_app(cookie_user=cookie_user)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/protected")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"user_id": str(cookie_user.id)})

    async def test_unauthenticated_returns_401_and_non_superuser_returns_403(self) -> None:
        app_unauth = self._build_app(cookie_user=None)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app_unauth),
            base_url="http://test",
        ) as client:
            response = await client.get("/protected")
            self.assertEqual(response.status_code, 401)

        regular_user = SimpleNamespace(id=uuid.uuid4(), is_active=True, is_superuser=False)
        app_regular = self._build_app(cookie_user=regular_user)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app_regular),
            base_url="http://test",
        ) as client:
            response = await client.get("/admin")
            self.assertEqual(response.status_code, 403)


class ApiKeyEndpointTests(unittest.IsolatedAsyncioTestCase):
    def _build_app(self, *, user, db) -> FastAPI:
        app = FastAPI()
        app.include_router(api_keys_router, prefix="/api")

        async def override_get_db():
            yield db

        app.dependency_overrides[get_db] = override_get_db
        if user is not None:
            async def override_current_user():
                return user

            app.dependency_overrides[current_active_user] = override_current_user
        else:
            async def override_cookie_user():
                return None

            app.dependency_overrides[_current_cookie_user_optional] = override_cookie_user

        return app

    async def test_create_api_key_returns_raw_secret_and_persists_hash(self) -> None:
        user = SimpleNamespace(id=uuid.uuid4(), is_active=True)
        added_objects: list[ApiKey] = []
        created_at = datetime.now(timezone.utc)
        expires_at = created_at + timedelta(days=30)

        db = mock.AsyncMock()
        db.add = mock.MagicMock(side_effect=added_objects.append)

        async def fake_refresh(obj: ApiKey) -> None:
            if obj.id is None:
                obj.id = uuid.uuid4()
            if obj.created_at is None:
                obj.created_at = created_at

        db.refresh.side_effect = fake_refresh
        app = self._build_app(user=user, db=db)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/api-keys",
                json={"name": "  CLI key  ", "expires_at": expires_at.isoformat()},
            )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(len(added_objects), 1)
        stored = added_objects[0]
        self.assertEqual(stored.user_id, user.id)
        self.assertEqual(stored.name, "CLI key")
        self.assertTrue(payload["api_key"].startswith(API_KEY_PREFIX))
        self.assertEqual(stored.key_prefix, payload["api_key"][:API_KEY_DISPLAY_PREFIX_LEN])
        self.assertEqual(stored.key_hash, hash_api_key(payload["api_key"]))
        self.assertEqual(payload["id"], str(stored.id))
        self.assertEqual(payload["name"], "CLI key")
        self.assertEqual(payload["key_prefix"], stored.key_prefix)
        self.assertNotIn("key_hash", payload)
        self.assertNotIn("revoked_at", payload)
        db.commit.assert_awaited_once()
        db.refresh.assert_awaited_once_with(stored)

    async def test_create_api_key_rejects_invalid_inputs(self) -> None:
        user = SimpleNamespace(id=uuid.uuid4(), is_active=True)
        db = mock.AsyncMock()
        app = self._build_app(user=user, db=db)

        cases = {
            "blank name": {"name": "   "},
            "naive expires_at": {"name": "CLI", "expires_at": "2099-01-01T00:00:00"},
            "past expires_at": {
                "name": "CLI",
                "expires_at": (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat(),
            },
        }

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            for label, body in cases.items():
                with self.subTest(label):
                    response = await client.post("/api/api-keys", json=body)
                    self.assertEqual(response.status_code, 422)

        db.commit.assert_not_awaited()

    async def test_list_api_keys_returns_paginated_metadata_for_current_user(self) -> None:
        user = SimpleNamespace(id=uuid.uuid4(), is_active=True)
        now = datetime.now(timezone.utc)
        key_a = SimpleNamespace(
            id=uuid.uuid4(),
            user_id=user.id,
            name="Newest",
            key_prefix="bb_aaaaaaaaa",
            key_hash="secret-hash-a",
            created_at=now,
            last_used_at=None,
            expires_at=None,
        )
        key_b = SimpleNamespace(
            id=uuid.uuid4(),
            user_id=user.id,
            name="Older",
            key_prefix="bb_bbbbbbbbb",
            key_hash="secret-hash-b",
            created_at=now - timedelta(hours=1),
            last_used_at=now - timedelta(minutes=5),
            expires_at=now + timedelta(days=7),
        )

        count_result = mock.MagicMock()
        count_result.scalar_one.return_value = 5

        items_result = mock.MagicMock()
        items_result.scalars.return_value.all.return_value = [key_a, key_b]

        db = mock.AsyncMock()
        db.execute.side_effect = [count_result, items_result]
        app = self._build_app(user=user, db=db)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/api-keys?page=2&page_size=2")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total"], 5)
        self.assertEqual(payload["page"], 2)
        self.assertEqual(payload["page_size"], 2)
        self.assertEqual(len(payload["items"]), 2)
        self.assertEqual(payload["items"][0]["id"], str(key_a.id))
        self.assertEqual(payload["items"][0]["name"], "Newest")
        self.assertEqual(payload["items"][0]["key_prefix"], "bb_aaaaaaaaa")
        self.assertNotIn("key_hash", payload["items"][0])
        self.assertNotIn("api_key", payload["items"][0])
        self.assertNotIn("revoked_at", payload["items"][0])

        # Verify SQL queries scope to the current user and apply offset/limit
        count_stmt = db.execute.await_args_list[0].args[0]
        list_stmt = db.execute.await_args_list[1].args[0]
        self.assertIn("api_keys.user_id =", str(count_stmt))
        self.assertIn("api_keys.user_id =", str(list_stmt))
        self.assertEqual(list_stmt._limit_clause.value, 2)
        self.assertEqual(list_stmt._offset_clause.value, 2)

    async def test_list_api_keys_returns_empty_page_past_end(self) -> None:
        user = SimpleNamespace(id=uuid.uuid4(), is_active=True)
        count_result = mock.MagicMock()
        count_result.scalar_one.return_value = 2

        items_result = mock.MagicMock()
        items_result.scalars.return_value.all.return_value = []

        db = mock.AsyncMock()
        db.execute.side_effect = [count_result, items_result]
        app = self._build_app(user=user, db=db)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/api-keys?page=2&page_size=2")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total"], 2)
        self.assertEqual(payload["items"], [])

    async def test_delete_api_key_deletes_owned_key(self) -> None:
        user = SimpleNamespace(id=uuid.uuid4(), is_active=True)
        key_id = uuid.uuid4()
        api_key = SimpleNamespace(id=key_id, user_id=user.id)

        select_result = mock.MagicMock()
        select_result.scalar_one_or_none.return_value = api_key

        db = mock.AsyncMock()
        db.execute.return_value = select_result
        app = self._build_app(user=user, db=db)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.delete(f"/api/api-keys/{key_id}")

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        select_stmt = db.execute.await_args_list[0].args[0]
        self.assertIn("api_keys.user_id =", str(select_stmt))
        db.delete.assert_awaited_once_with(api_key)
        db.commit.assert_awaited_once()

    async def test_delete_api_key_returns_404_when_missing_or_not_owned(self) -> None:
        user = SimpleNamespace(id=uuid.uuid4(), is_active=True)
        key_id = uuid.uuid4()

        select_result = mock.MagicMock()
        select_result.scalar_one_or_none.return_value = None

        db = mock.AsyncMock()
        db.execute.return_value = select_result
        app = self._build_app(user=user, db=db)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.delete(f"/api/api-keys/{key_id}")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "API key not found")
        db.delete.assert_not_awaited()
        db.commit.assert_not_awaited()

    async def test_endpoints_require_authentication(self) -> None:
        db = make_fake_db(None)
        app = self._build_app(user=None, db=db)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            create_resp = await client.post("/api/api-keys", json={"name": "CLI"})
            list_resp = await client.get("/api/api-keys")
            delete_resp = await client.delete(f"/api/api-keys/{uuid.uuid4()}")

        self.assertEqual(create_resp.status_code, 401)
        self.assertEqual(list_resp.status_code, 401)
        self.assertEqual(delete_resp.status_code, 401)


if __name__ == "__main__":
    unittest.main()
