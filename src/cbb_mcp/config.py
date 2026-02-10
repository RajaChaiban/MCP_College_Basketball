"""Application configuration via environment variables."""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "CBB_", "env_file": ".env", "extra": "ignore"}

    # Transport
    transport: Literal["stdio", "streamable-http"] = "stdio"
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    server_api_key: str = Field(default="", repr=False)

    # Cache
    cache_dir: str = ".cache"
    cache_enabled: bool = True

    # Rate limits (requests per second)
    espn_rate_limit: int = Field(default=10, ge=1, le=100)
    ncaa_rate_limit: int = Field(default=5, ge=1, le=100)

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # Future paid sources (repr=False hides from logs/repr)
    sportsdataio_key: str = Field(default="", repr=False)
    kenpom_user: str = Field(default="", repr=False)
    kenpom_pass: str = Field(default="", repr=False)


settings = Settings()
