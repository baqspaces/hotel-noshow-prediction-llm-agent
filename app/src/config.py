from pathlib import Path

try:
    from functools import lru_cache
    from pydantic import Field
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ModuleNotFoundError as exc:  # pragma: no cover - startup guidance
    missing = exc.name
    raise ModuleNotFoundError(
        f"Missing dependency '{missing}'. From visa/app, run: py -m pip install -r requirements.txt"
    ) from exc


APP_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = APP_DIR.parent / "noshow.db"


class Settings(BaseSettings):
    app_name: str = "Hotel No-Show Prediction AI Insights Assistant"
    environment: str = Field(default="development", alias="APP_ENV")
    database_url: str = Field(
        default=f"sqlite:///{DEFAULT_DB_PATH.as_posix()}",
        alias="DATABASE_URL",
    )
    jwt_secret: str = Field(default="change-me-for-production", alias="JWT_SECRET")
    jwt_issuer: str = "visa-noshow-demo"
    access_token_minutes: int = 60
    demo_username: str = Field(default="manager", alias="DEMO_USERNAME")
    demo_password: str = Field(default="password123", alias="DEMO_PASSWORD")
    cache_ttl_seconds: int = 300
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_org_id: str | None = Field(default=None, alias="OPENAI_ORG_ID")
    openai_project_id: str | None = Field(default=None, alias="OPENAI_PROJECT_ID")
    openai_model: str = Field(default="gpt-5-mini", alias="OPENAI_MODEL")
    openai_timeout_seconds: float = Field(default=20.0, alias="OPENAI_TIMEOUT_SECONDS")

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
