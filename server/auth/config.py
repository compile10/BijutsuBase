"""Authentication configuration for BijutsuBase."""
import os

# JWT Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "CHANGE_ME_IN_PRODUCTION")
JWT_LIFETIME_SECONDS = int(os.getenv("JWT_LIFETIME_SECONDS", "3600"))

# Password reset and verification secrets
RESET_PASSWORD_TOKEN_SECRET = os.getenv("RESET_PASSWORD_TOKEN_SECRET", JWT_SECRET)
VERIFICATION_TOKEN_SECRET = os.getenv("VERIFICATION_TOKEN_SECRET", JWT_SECRET)
