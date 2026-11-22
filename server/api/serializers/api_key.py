"""API key serializers for BijutsuBase API."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CreateApiKeyRequest(BaseModel):
    """Request model for creating a new API key on the current account."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Human-readable label for the API key",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Optional timezone-aware expiration timestamp in the future",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        """Strip whitespace and ensure the key name is not blank."""
        stripped = value.strip()
        if not stripped:
            raise ValueError("API key name must not be blank")
        return stripped

    @field_validator("expires_at")
    @classmethod
    def validate_expires_at(cls, value: datetime | None) -> datetime | None:
        """Ensure expires_at is timezone-aware and in the future."""
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("expires_at must include timezone information")
        if value <= datetime.now(timezone.utc):
            raise ValueError("expires_at must be in the future")
        return value


class ApiKeyResponse(BaseModel):
    """Public metadata for an API key (never includes the secret or hash)."""

    id: uuid.UUID
    name: str
    key_prefix: str
    created_at: datetime
    last_used_at: datetime | None = None
    expires_at: datetime | None = None
    revoked_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class CreateApiKeyResponse(ApiKeyResponse):
    """Response returned once when an API key is created, including the raw secret."""

    api_key: str


class ApiKeyListResponse(BaseModel):
    """Paginated list of API keys belonging to the current account."""

    items: list[ApiKeyResponse]
    total: int
    page: int
    page_size: int
