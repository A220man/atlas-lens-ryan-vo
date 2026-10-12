"""Pytest configuration and test fixtures.

Provides test client with in-memory database and scoped auth credentials.
"""

import os
from typing import AsyncGenerator, Dict, Generator
import pytest
from fastapi.testclient import TestClient
import httpx

# Ensure test environment variables before imports
os.environ["APP_ENV"] = "test"
os.environ["DEMO_MODE"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key-at-least-32-characters-long"
os.environ["LLM_API_KEY"] = ""

from app.core.config import Settings, get_settings
from app.core.database import init_database
from app.core.security import create_demo_token
from app.main import create_app
from app.models.schemas import User


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Provide test configuration."""
    return Settings(
        app_env="test",
        demo_mode=True,
        database_url="sqlite:///:memory:",
        secret_key="test-secret-key-at-least-32-characters-long",
        token_algorithm="HS256",
        llm_api_key="",
        llm_provider="ollama",
    )


@pytest.fixture(scope="function")
def app(test_settings: Settings):
    """Create test application instance with fresh database."""
    init_database(test_settings)
    application = create_app(test_settings)
    return application


@pytest.fixture(scope="function")
def client(app) -> Generator[TestClient, None, None]:
    """Synchronous test client."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def viewer_token(test_settings: Settings) -> str:
    """Generate demo JWT with viewer role."""
    user = User(id="viewer-1", email="viewer@atlas-lens.test", role="viewer", is_demo=True)
    return create_demo_token(user, test_settings)


@pytest.fixture
def operator_token(test_settings: Settings) -> str:
    """Generate demo JWT with operator role."""
    user = User(id="operator-1", email="operator@atlas-lens.test", role="operator", is_demo=True)
    return create_demo_token(user, test_settings)


@pytest.fixture
def admin_token(test_settings: Settings) -> str:
    """Generate demo JWT with admin role."""
    user = User(id="admin-1", email="admin@atlas-lens.test", role="admin", is_demo=True)
    return create_demo_token(user, test_settings)


@pytest.fixture
def viewer_headers(viewer_token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {viewer_token}"}


@pytest.fixture
def operator_headers(operator_token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {operator_token}"}


@pytest.fixture
def admin_headers(admin_token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {admin_token}"}
