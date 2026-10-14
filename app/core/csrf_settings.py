from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Absolute, so the settings load from any working directory
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class CsrfSettings(BaseSettings):
    secret_key: str = Field(validation_alias="CSRF_SECRET_KEY")
    cookie_samesite: Literal["lax", "strict", "none"] = Field(
        validation_alias="COOKIE_SAMESITE"
    )
    cookie_secure: bool = Field(validation_alias="COOKIE_SECURE")

    model_config = SettingsConfigDict(
        env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore"
    )


crsf_settings = CsrfSettings()
