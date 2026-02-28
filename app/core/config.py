from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application runtime settings loaded from environment variables."""

    app_name: str = "Code Radar AI"
    debug: bool = Field(default=True, alias="DEBUG")
    host: str = "0.0.0.0"
    port: int = 8000

    database_url: str = Field(alias="DATABASE_URL")
    redis_url: str = Field(alias="REDIS_URL")
    ollama_url: str = Field(default="http://localhost:11434", alias="OLLAMA_URL")
    ollama_model: str = Field(default="llama3:8b", alias="OLLAMA_MODEL")
    max_llm_concurrency: int = Field(default=4, alias="MAX_LLM_CONCURRENCY")
    ollama_timeout_seconds: float = Field(default=30.0, alias="OLLAMA_TIMEOUT_SECONDS")
    ollama_retries: int = Field(default=3, alias="OLLAMA_RETRIES")

    semgrep_bin: str = Field(default="semgrep", alias="SEMGREP_BIN")
    semgrep_config: str = Field(default="semgrep_rules/default.yml", alias="SEMGREP_CONFIG")

    upload_dir: Path = Field(default=Path("uploads"), alias="UPLOAD_DIR")
    extraction_dir: Path = Field(default=Path("data"), alias="EXTRACTION_DIR")
    log_dir: Path = Field(default=Path("logs"), alias="LOG_DIR")
    log_file: str = Field(default="app.log", alias="LOG_FILE")
    redis_ttl_seconds: int = Field(default=86400, alias="REDIS_TTL_SECONDS")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.extraction_dir.mkdir(parents=True, exist_ok=True)
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    return settings
