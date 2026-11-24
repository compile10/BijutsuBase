"""API key generation, hashing, and authentication helpers."""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.api_key import ApiKey
from models.user import User

API_KEY_PREFIX = "bb_"
API_KEY_DISPLAY_PREFIX_LEN = 12
LAST_USED_UPDATE_INTERVAL = timedelta(minutes=1)

bearer_scheme = HTTPBearer(auto_error=False)


def hash_api_key(raw_key: str) -> str:
    """Return the hex-encoded SHA-256 hash of a raw API key."""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def generate_api_key() -> tuple[str, str, str]:
    """Generate a new API key and return (raw_key, key_prefix, key_hash)."""
    raw_key = f"{API_KEY_PREFIX}{secrets.token_urlsafe(32)}"
    return raw_key, raw_key[:API_KEY_DISPLAY_PREFIX_LEN], hash_api_key(raw_key)


def extract_api_key(
    bearer_credentials: HTTPAuthorizationCredentials | None,
) -> str | None:
    """Extract a raw API key from an Authorization: Bearer header."""
    if bearer_credentials is None:
        return None

    token = bearer_credentials.credentials.strip()
    return token or None


async def authenticate_api_key(
    raw_key: str,
    db: AsyncSession,
) -> tuple[User | None, str | None]:
    """Validate a raw API key and return (user, error_reason)."""
    key_hash = hash_api_key(raw_key)
    result = await db.execute(
        select(ApiKey, User)
        .join(User, ApiKey.user_id == User.id)
        .where(ApiKey.key_hash == key_hash)
    )
    row = result.first()
    if row is None:
        return None, "Invalid API key"

    api_key, user = row
    now = datetime.now(timezone.utc)

    if api_key.expires_at is not None and api_key.expires_at <= now:
        return None, "API key has expired"
    if not user.is_active:
        return None, "User account is inactive"

    # Throttle last_used_at writes so bursts (e.g. thumbnail grids) avoid write churn
    if (
        api_key.last_used_at is None
        or (now - api_key.last_used_at) >= LAST_USED_UPDATE_INTERVAL
    ):
        await db.execute(
            update(ApiKey)
            .where(ApiKey.id == api_key.id)
            .values(last_used_at=now)
        )
        await db.commit()

    return user, None
