"""Authentication backend configuration."""
import os

from fastapi_users.authentication import AuthenticationBackend, CookieTransport, JWTStrategy

from auth.config import JWT_SECRET, JWT_LIFETIME_SECONDS


# Cookie transport for JWT tokens
# HttpOnly cookie prevents JavaScript access (XSS protection)
# SameSite=Lax provides CSRF protection for most cases
# COOKIE_SECURE=false allows cookies over HTTP (for non-browser clients like scripts)
cookie_secure = os.getenv("COOKIE_SECURE", "true").lower() in ("true", "1", "yes")
cookie_transport = CookieTransport(
    cookie_max_age=JWT_LIFETIME_SECONDS,
    cookie_secure=cookie_secure,
)


def get_jwt_strategy() -> JWTStrategy:
    """Get the JWT strategy for authentication."""
    return JWTStrategy(secret=JWT_SECRET, lifetime_seconds=JWT_LIFETIME_SECONDS)


# Authentication backend combining transport and strategy
auth_backend = AuthenticationBackend(
    name="cookie",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)
