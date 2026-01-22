"""Authentication backend configuration."""
from fastapi_users.authentication import AuthenticationBackend, BearerTransport, JWTStrategy

from auth.config import JWT_SECRET, JWT_LIFETIME_SECONDS


# Bearer transport for JWT tokens
bearer_transport = BearerTransport(tokenUrl="/api/auth/jwt/login")


def get_jwt_strategy() -> JWTStrategy:
    """Get the JWT strategy for authentication."""
    return JWTStrategy(secret=JWT_SECRET, lifetime_seconds=JWT_LIFETIME_SECONDS)


# Authentication backend combining transport and strategy
auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)
