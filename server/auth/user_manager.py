"""User manager for FastAPI Users."""
import uuid
import logging
from typing import Optional

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, UUIDIDMixin
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from database.config import get_db
from models.user import User
from auth.config import RESET_PASSWORD_TOKEN_SECRET, VERIFICATION_TOKEN_SECRET

logger = logging.getLogger(__name__)


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    """User manager handling user lifecycle events."""
    
    reset_password_token_secret = RESET_PASSWORD_TOKEN_SECRET
    verification_token_secret = VERIFICATION_TOKEN_SECRET

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        """Called after a user registers."""
        logger.info("User %s has registered.", user.id)

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        """Called after a user requests password reset."""
        # SECURITY: Never log the token - it would allow account takeover
        logger.info("Password reset requested for user %s.", user.id)

    async def on_after_request_verify(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        """Called after a user requests email verification."""
        # SECURITY: Never log the token - it would allow account takeover
        logger.info("Email verification requested for user %s.", user.id)


async def get_user_db(session: AsyncSession = Depends(get_db)):
    """Get the SQLAlchemy user database adapter."""
    yield SQLAlchemyUserDatabase(session, User)


async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    """Get the user manager instance."""
    yield UserManager(user_db)
