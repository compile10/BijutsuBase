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
from database.config import get_db


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
            revoked_at=None,
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
            revoked_at=None,
            expires_at=None,
            last_used_at=datetime.now(timezone.utc) - timedelta(seconds=10),
        )
        db = make_fake_db((api_key, user))

        authenticated, error = await authenticate_api_key(raw_key, db)

        self.assertIs(authenticated, user)
        self.assertIsNone(error)
        self.assertEqual(db.execute.await_count, 1)  # select only
        db.commit.assert_not_awaited()

    async def test_rejects_missing_revoked_expired_and_inactive(self) -> None:
        raw_key, _, key_hash = generate_api_key()
        now = datetime.now(timezone.utc)

        cases = {
            "not found": (None, "Invalid API key"),
            "revoked": (
                (
                    SimpleNamespace(
                        id=uuid.uuid4(),
                        key_hash=key_hash,
                        revoked_at=now - timedelta(minutes=5),
                        expires_at=None,
                        last_used_at=None,
                    ),
                    SimpleNamespace(id=uuid.uuid4(), is_active=True),
                ),
                "API key has been revoked",
            ),
            "expired": (
                (
                    SimpleNamespace(
                        id=uuid.uuid4(),
                        key_hash=key_hash,
                        revoked_at=None,
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
                        revoked_at=None,
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
            revoked_at=None,
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
        revoked_key = SimpleNamespace(
            id=uuid.uuid4(),
            key_hash=key_hash,
            revoked_at=datetime.now(timezone.utc) - timedelta(minutes=1),
            expires_at=None,
            last_used_at=None,
        )
        app = self._build_app(api_key_row=(revoked_key, user))

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/protected",
                headers={"Authorization": f"Bearer {raw_key}"},
            )
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json()["detail"], "API key has been revoked")

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


if __name__ == "__main__":
    unittest.main()
