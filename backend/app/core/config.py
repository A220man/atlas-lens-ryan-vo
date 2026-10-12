"""Application configuration and environment settings.

Enforces operator-driven settings, role policies, and startup validation
to prevent insecure demo execution in production environments.
"""

import os
from typing import Literal, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Core environment
    app_name: str = "Atlas Lens"
    app_version: str = "1.0.0"
    app_env: Literal["production", "development", "test"] = "development"
    debug: bool = False
    demo_mode: bool = True
    host: str = "127.0.0.1"
    port: int = 8000

    # Persistence
    database_url: str = "sqlite:///./atlas_lens.db"

    # Security & Tokens
    secret_key: str = "test-insecure-secret-key-replace-in-production-minimum-32"
    token_algorithm: str = "HS256"
    access_token_expire_minutes: int = 120

    # OIDC Configuration (Keycloak / Enterprise IdP)
    oidc_enabled: bool = False
    oidc_issuer_url: str = "http://127.0.0.1:8080/realms/atlas-lens"
    oidc_client_id: str = "atlas-lens-client"
    oidc_client_secret: Optional[str] = None
    oidc_audience: str = "atlas-lens-client"

    # LLM Gateway non-secret operator settings
    llm_api_key: Optional[str] = None
    llm_provider: Literal["openai-compatible", "anthropic", "gemini", "ollama"] = "ollama"
    llm_model: str = "llama3.1"
    llm_base_url: str = "http://127.0.0.1:11434"
    llm_request_timeout: float = 30.0

    @field_validator("demo_mode")
    @classmethod
    def validate_demo_mode_safety(cls, demo_mode_val: bool, info) -> bool:
        env = info.data.get("app_env", "development")
        if env == "production" and demo_mode_val:
            raise ValueError(
                "CRITICAL SECURITY VIOLATION: DEMO_MODE cannot be enabled in production environment. "
                "Set DEMO_MODE=false and configure OIDC_ENABLED=true."
            )
        return demo_mode_val


def get_settings() -> Settings:
    """Retrieve application settings instance."""
    return Settings()
