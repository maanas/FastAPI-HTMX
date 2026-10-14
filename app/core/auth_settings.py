from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Absolute, so the settings load from any working directory
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

# Values that must never sign a token: the old built-in default and the
# placeholder in .env.example.
FORBIDDEN_AUTH_SECRETS = {"my_default_secret_key", "change-me-auth-secret"}

MIN_AUTH_SECRET_LENGTH = 32

GENERATE_HINT = 'python -c "import secrets; print(secrets.token_urlsafe(48))"'


def validate_auth_secret(value: str | None) -> str:
    """Return the stripped secret, or raise RuntimeError without echoing the value."""
    stripped = (value or "").strip()
    if (
        not stripped
        or stripped in FORBIDDEN_AUTH_SECRETS
        or len(stripped) < MIN_AUTH_SECRET_LENGTH
    ):
        raise RuntimeError(
            "AUTH_SECRET is missing, empty, a placeholder or shorter than "
            f"{MIN_AUTH_SECRET_LENGTH} characters. Set a long random value in "
            f".env, for example: {GENERATE_HINT}"
        )
    return stripped


class AuthSettings(BaseSettings):
    auth_secret: str | None = Field(default=None, validation_alias="AUTH_SECRET")

    model_config = SettingsConfigDict(
        env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore"
    )


def get_auth_secret() -> str:
    return validate_auth_secret(AuthSettings().auth_secret)
