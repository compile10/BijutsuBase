"""Authentication configuration for BijutsuBase."""
import os


def _get_required_secret(name: str) -> str:
    """Get a required secret from environment, failing loudly if not set."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Required environment variable {name} is not set. "
            "Please set it to a secure random value (e.g., 32+ character random string)."
        )
    return value


# JWT Configuration - secrets are required, no defaults
JWT_SECRET = _get_required_secret("JWT_SECRET")
JWT_LIFETIME_SECONDS = int(os.getenv("JWT_LIFETIME_SECONDS", "3600"))

# Password reset and verification secrets
# These default to JWT_SECRET if not explicitly set, but JWT_SECRET is required
RESET_PASSWORD_TOKEN_SECRET = os.getenv("RESET_PASSWORD_TOKEN_SECRET") or JWT_SECRET
VERIFICATION_TOKEN_SECRET = os.getenv("VERIFICATION_TOKEN_SECRET") or JWT_SECRET
