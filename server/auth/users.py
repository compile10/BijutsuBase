"""FastAPI Users instance and dependencies."""
import uuid

from fastapi_users import FastAPIUsers

from models.user import User
from auth.user_manager import get_user_manager
from auth.backend import auth_backend


# Main FastAPI Users instance
fastapi_users = FastAPIUsers[User, uuid.UUID](
    get_user_manager=get_user_manager,
    auth_backends=[auth_backend],
)

# Dependency for getting the current active user
current_active_user = fastapi_users.current_user(active=True)

# Dependency for getting the current superuser (admin)
current_superuser = fastapi_users.current_user(active=True, superuser=True)
