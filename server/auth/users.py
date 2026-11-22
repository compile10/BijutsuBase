"""FastAPI Users instance and dependencies."""
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from fastapi_users import FastAPIUsers
from sqlalchemy.ext.asyncio import AsyncSession

from auth.api_keys import (
    authenticate_api_key,
    bearer_scheme,
    extract_api_key,
)
from auth.backend import auth_backend
from auth.user_manager import get_user_manager
from database.config import get_db
from models.user import User


# Main FastAPI Users instance
fastapi_users = FastAPIUsers[User, uuid.UUID](
    get_user_manager=get_user_manager,
    auth_backends=[auth_backend],
)

_current_cookie_user_optional = fastapi_users.current_user(active=True, optional=True)


async def current_active_user(
    bearer_credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    cookie_user: User | None = Depends(_current_cookie_user_optional),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Authenticate via Authorization: Bearer API key or session cookie."""
    raw_key = extract_api_key(bearer_credentials)
    if raw_key is not None:
        user, error = await authenticate_api_key(raw_key, db)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=error or "Invalid API key",
            )
        return user

    if cookie_user is not None:
        return cookie_user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized",
    )


async def current_superuser(
    user: User = Depends(current_active_user),
) -> User:
    """Require an authenticated active superuser."""
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )
    return user
