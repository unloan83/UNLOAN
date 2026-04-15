import os


class Config:
    SECRET_KEY = os.getenv("UNLOAN_SECRET_KEY", "change-me-in-production")
    ADMIN_USERNAME = os.getenv("UNLOAN_ADMIN_USER", "admin")
    ADMIN_PASSWORD_HASH = os.getenv(
        "UNLOAN_ADMIN_PASSWORD_HASH",
        "pbkdf2:sha256:260000$demo$demo"  # placeholder hash; set via env
    )
    TOKEN_MAX_AGE_SECONDS = int(os.getenv("UNLOAN_TOKEN_MAX_AGE_SECONDS", "3600"))
    STORAGE_PATH = os.getenv("UNLOAN_STORAGE_PATH", "data/plans.json")
    FIREBASE_ENABLED = os.getenv("UNLOAN_FIREBASE_ENABLED", "false").lower() == "true"
