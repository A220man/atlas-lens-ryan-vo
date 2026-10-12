"""Tests for authentication, authorization, role hierarchy, and demo mode refusal."""

from datetime import datetime, timedelta, timezone
import jwt
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.models.schemas import User


def test_unauthenticated_request_rejected(client: TestClient):
    """Ensure data endpoints reject unauthenticated requests with 401."""
    resp = client.get("/api/chats")
    assert resp.status_code == 401
    assert "Missing Bearer" in resp.json()["detail"]


def test_role_viewer_denied_operator_action(client: TestClient, viewer_headers):
    """Ensure viewers cannot trigger mutation or repair actions (403 Forbidden)."""
    resp = client.post("/api/chats/import", json={"title": "Test Chat"}, headers=viewer_headers)
    assert resp.status_code == 403
    assert "Insufficient permissions" in resp.json()["detail"]


def test_role_operator_denied_admin_action(client: TestClient, operator_headers):
    """Ensure operators cannot access admin-only endpoints like audit logs or server registration."""
    resp = client.get("/api/audit/logs", headers=operator_headers)
    assert resp.status_code == 403
    assert "Insufficient permissions" in resp.json()["detail"]


def test_admin_allowed_admin_action(client: TestClient, admin_headers):
    """Ensure admins can query audit logs."""
    resp = client.get("/api/audit/logs", headers=admin_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_demo_mode_refused_in_production():
    """Ensure settings validation raises an error if DEMO_MODE is true in production."""
    with pytest.raises(ValueError, match="CRITICAL SECURITY VIOLATION"):
        Settings(
            app_env="production",
            demo_mode=True,
            secret_key="some-production-secret-key-at-least-32-chars",
        )


def test_demo_login_endpoint(client: TestClient):
    """Verify demo login endpoint returns valid JWT token and profile."""
    resp = client.post("/api/auth/demo-login", json={"role": "operator", "email": "dev@atlas-lens.local"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["role"] == "operator"

    # Call /api/auth/me using returned token
    auth_header = {"Authorization": f"Bearer {data['access_token']}"}
    me_resp = client.get("/api/auth/me", headers=auth_header)
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["role"] == "operator"
    assert me_data["is_demo"] is True


def test_expired_token_rejected(client: TestClient, test_settings: Settings):
    """Ensure expired tokens are rejected with 401."""
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    payload = {
        "sub": "user-expired",
        "email": "expired@atlas-lens.test",
        "role": "viewer",
        "is_demo": True,
        "aud": test_settings.oidc_audience,
        "exp": int(past.timestamp()),
        "iat": int((past - timedelta(minutes=10)).timestamp()),
    }
    expired_token = jwt.encode(payload, test_settings.secret_key, algorithm=test_settings.token_algorithm)
    resp = client.get("/api/chats", headers={"Authorization": f"Bearer {expired_token}"})
    assert resp.status_code == 401
    assert "expired" in resp.json()["detail"].lower()


def test_invalid_token_rejected(client: TestClient):
    """Ensure tokens with invalid signatures are rejected."""
    resp = client.get("/api/chats", headers={"Authorization": "Bearer invalid.token.payload"})
    assert resp.status_code == 401


def test_logout_endpoint(client: TestClient, viewer_headers):
    """Ensure logout endpoint acknowledges session closure."""
    resp = client.post("/api/auth/logout", headers=viewer_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "logged_out"
