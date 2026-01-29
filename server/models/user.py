"""User model for BijutsuBase authentication."""
from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTableUUID
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from database.config import Base


class User(SQLAlchemyBaseUserTableUUID, Base):
    """
    User model for authentication.
    
    Inherits from SQLAlchemyBaseUserTableUUID which provides:
    - id: UUID primary key
    - email: unique email address
    - hashed_password: password hash
    - is_active: whether the user is active
    - is_superuser: whether the user has admin privileges
    - is_verified: whether the user's email is verified
    
    Additional fields:
    - username: unique display name for the user
    - avatar: sha256 hash of the user's avatar image (references a file in the system)
    """
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    avatar: Mapped[str | None] = mapped_column(String(64), nullable=True)
