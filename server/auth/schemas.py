"""Pydantic schemas for user authentication."""
import uuid
from typing import Optional
from fastapi_users import schemas


class UserRead(schemas.BaseUser[uuid.UUID]):
    """Schema for reading user data."""
    username: str
    avatar: str | None = None


class UserCreate(schemas.BaseUserCreate):
    """Schema for creating a new user."""
    username: str


class UserUpdate(schemas.BaseUserUpdate):
    """Schema for updating user data."""
    username: Optional[str] = None
    avatar: Optional[str] = None
