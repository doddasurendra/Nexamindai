"""Application configuration loaded from environment variables only."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "NexaMind AI"
    environment: str = "development"
    debug: bool = False
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60 * 24 * 7
    jwt_algorithm: str = "HS256"

    # Database: defaults to SQLite for local development; use PostgreSQL in production.
    database_url: str = "sqlite+aiosqlite:///./data/nexamind.db"
    auto_create_tables: bool = True

    # OpenRouter (server-side only)
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_app_name: str = "NexaMind AI"
    openrouter_app_url: str = "http://localhost:5173"
    default_model: str = "openai/gpt-4o-mini"
    fallback_models: str = "openai/gpt-4o-mini,google/gemini-2.0-flash-001"
    request_timeout_seconds: float = 60.0
    max_retries: int = 3
    max_context_tokens: int = 12000

    # Search / research
    search_provider: str = "tavily"
    tavily_api_key: str = ""
    search_max_results: int = 6

    # Ollama (local model inference)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # Media / generation
    image_generation_model: str = "google/gemini-2.5-flash-image"
    video_generation_provider: str = "replicate"
    replicate_api_token: str = ""
    video_model: str = "minimax/video-01"

    # Storage
    storage_dir: Path = Path("./data/storage")
    max_upload_mb: int = 25
    allowed_upload_types: str = "pdf,docx,txt,csv,xlsx,png,jpg,jpeg,webp,gif,mp4,webm"

    # Security
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    rate_limit_per_minute: int = 120
    auth_rate_limit_per_minute: int = 20
    max_url_bytes: int = 2_000_000
    url_fetch_timeout_seconds: float = 15.0
    allow_private_urls: bool = False

    # Google Sign-In (OAuth 2.0 / OpenID Connect)
    google_client_id: str = ""  # Google OAuth Web Client ID for GIS sign-in
    google_client_secret: str = ""  # Server-side only; used for authorization-code flows

    # Firebase: primary database when configured; otherwise SQLite/PostgreSQL
    # ============================================================
    firebase_project_id: str = ""  # Firebase project ID, e.g. "nexamind-ai"
    firebase_credentials_path: str = ""  # path to service-account JSON key
    firebase_bucket: str = ""  # optional Cloud Storage bucket, defaults to default bucket

    # Embeddings: "local" (offline deterministic) or "openrouter"
    embedding_provider: str = "local"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 384

    @property
    def firebase_enabled(self) -> bool:
        return bool(self.firebase_project_id and self.firebase_credentials_path)

    @property
    def fallback_model_list(self) -> list[str]:
        return [m.strip() for m in self.fallback_models.split(",") if m.strip()]

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allowed_upload_extensions(self) -> set[str]:
        return {e.strip().lower() for e in self.allowed_upload_types.split(",") if e.strip()}

    @property
    def openrouter_configured(self) -> bool:
        return bool(self.openrouter_api_key)

    @property
    def search_configured(self) -> bool:
        return self.search_provider == "tavily" and bool(self.tavily_api_key)

    @property
    def ollama_configured(self) -> bool:
        return bool(self.ollama_base_url)

    def ensure_directories(self) -> None:
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        if self.database_url.startswith("sqlite"):
            Path("./data").mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
