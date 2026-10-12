"""Authentication endpoints for Keycloak OIDC and development demo login.

Enforces role assignment, audit logging, and explicit logout.
"""

from typing import Dict, Literal
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.config import Settings, get_settings
from app.core.database import record_audit_log
from app.core.security import create_demo_token, get_current_user
from app.models.schemas import RoleType, TokenResponse, User

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class DemoLoginRequest(BaseModel):
    """Local demo login parameter."""
    role: RoleType = "operator"
    email: str = "developer@atlas-lens.local"


@router.get("/oidc-config")
def get_oidc_config(settings: Settings = Depends(get_settings)) -> Dict[str, str]:
    """Provide public OIDC configuration for SPA PKCE authentication."""
    return {
        "enabled": str(settings.oidc_enabled).lower(),
        "issuer_url": settings.oidc_issuer_url,
        "client_id": settings.oidc_client_id,
        "audience": settings.oidc_audience,
        "demo_mode": str(settings.demo_mode).lower(),
        "app_env": settings.app_env,
    }


@router.post("/demo-login", response_model=TokenResponse)
def demo_login(
    req: DemoLoginRequest,
    settings: Settings = Depends(get_settings)
) -> TokenResponse:
    """Create a scoped JWT token for local testing and demonstration.

    Refused if APP_ENV is production or DEMO_MODE is false.
    """
    if settings.app_env == "production" or not settings.demo_mode:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo login is disabled in production environments."
        )

    user = User(
        id=f"demo-{req.role}",
        email=req.email,
        role=req.role,
        is_demo=True
    )
    token = create_demo_token(user, settings)

    record_audit_log(
        user_id=user.id,
        action="DEMO_LOGIN",
        resource_type="auth",
        resource_id=user.id,
        details={"role": req.role, "email": req.email},
        settings=settings
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        role=req.role,
        expires_in=settings.access_token_expire_minutes * 60,
        user_id=user.id,
        email=user.email
    )


@router.get("/me", response_model=User)
def get_profile(current_user: User = Depends(get_current_user)) -> User:
    """Return authenticated user profile and active role."""
    return current_user


@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)) -> Dict[str, str]:
    """Acknowledge explicit session logout."""
    record_audit_log(
        user_id=current_user.id,
        action="LOGOUT",
        resource_type="auth",
        resource_id=current_user.id,
        details={"user_id": current_user.id}
    )
    return {"status": "logged_out", "user_id": current_user.id}
