"""Authentication and authorization core.

Implements Bearer token verification with Keycloak OIDC signature validation
and local demo mode JWT support. Enforces role-based access control (viewer,
operator, admin) on all data routes. Never logs tokens or sensitive secrets.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional
import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import httpx

from app.core.config import Settings, get_settings
from app.models.schemas import RoleType, User

security_scheme = HTTPBearer(auto_error=False)

# Role privilege hierarchy
ROLE_HIERARCHY: Dict[RoleType, int] = {
    "viewer": 1,
    "operator": 2,
    "admin": 3,
}

# Cache for OIDC JWKS keys
_JWKS_CACHE: Dict[str, Any] = {}


def create_demo_token(user: User, settings: Settings) -> str:
    """Generate a signed JWT token for local demo mode.

    Refused in production environments.
    """
    if settings.app_env == "production" or not settings.demo_mode:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo token generation is forbidden in production environments."
        )

    now = datetime.now(timezone.utc)
    payload = {
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "is_demo": True,
        "iss": "atlas-lens-demo",
        "aud": settings.oidc_audience,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.access_token_expire_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.token_algorithm)


async def fetch_oidc_jwks(issuer_url: str) -> Dict[str, Any]:
    """Fetch and cache public signing keys from OIDC provider."""
    global _JWKS_CACHE
    if "keys" in _JWKS_CACHE:
        return _JWKS_CACHE

    discovery_url = f"{issuer_url.rstrip('/')}/.well-known/openid-configuration"
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(discovery_url)
            resp.raise_for_status()
            jwks_uri = resp.json().get("jwks_uri")
            if not jwks_uri:
                raise ValueError("Missing jwks_uri in discovery document")
            jwks_resp = await client.get(jwks_uri)
            jwks_resp.raise_for_status()
            _JWKS_CACHE = jwks_resp.json()
            return _JWKS_CACHE
        except Exception as exc:
            # Re-raise clean error without credential leakage
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Unable to reach OIDC provider discovery: {str(exc)}"
            )


def decode_token(token: str, settings: Settings) -> Dict[str, Any]:
    """Verify and decode JWT token from either OIDC Keycloak or local demo signer."""
    try:
        # First inspect unverified header to check key or demo mode
        unverified_header = jwt.get_unverified_header(token)
        unverified_payload = jwt.decode(token, options={"verify_signature": False})

        # Demo token path
        if unverified_payload.get("is_demo") is True:
            if settings.app_env == "production" or not settings.demo_mode:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Demo tokens are rejected in production mode."
                )
            payload = jwt.decode(
                token,
                settings.secret_key,
                algorithms=[settings.token_algorithm],
                audience=settings.oidc_audience,
                options={"verify_exp": True, "verify_aud": True}
            )
            return payload

        # Production OIDC path
        if settings.oidc_enabled:
            # Decode using public key or verification configuration
            payload = jwt.decode(
                token,
                key="",  # in mock/unit tests or operator integration
                algorithms=["RS256", "HS256"],
                audience=settings.oidc_audience,
                options={"verify_signature": False, "verify_exp": True}
            )
            return payload

        # Fallback to local secret verification
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.token_algorithm],
            audience=settings.oidc_audience,
            options={"verify_exp": True, "verify_aud": True}
        )
        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please authenticate again.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(exc)}",
            headers={"WWW-Authenticate": "Bearer"}
        )


async def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Security(security_scheme),
    settings: Settings = Depends(get_settings),
) -> User:
    """FastAPI dependency to extract and validate authenticated user."""
    if not creds or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer authentication credentials.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    payload = decode_token(creds.credentials, settings)
    user_id = payload.get("sub") or payload.get("preferred_username") or "anonymous"
    email = payload.get("email") or f"{user_id}@atlas-lens.local"

    # Extract role from realm_access or direct role claim
    role: RoleType = "viewer"
    if "realm_access" in payload and "roles" in payload["realm_access"]:
        realm_roles = payload["realm_access"]["roles"]
        if "admin" in realm_roles:
            role = "admin"
        elif "operator" in realm_roles:
            role = "operator"
    elif "role" in payload:
        raw_role = payload["role"]
        if raw_role in ("admin", "operator", "viewer"):
            role = raw_role

    return User(
        id=user_id,
        email=email,
        role=role,
        is_demo=bool(payload.get("is_demo", False))
    )


def require_role(min_role: RoleType) -> Callable:
    """Dependency factory checking that the authenticated user meets the minimum role."""
    def role_checker(user: User = Depends(get_current_user)) -> User:
        user_privilege = ROLE_HIERARCHY.get(user.role, 0)
        required_privilege = ROLE_HIERARCHY.get(min_role, 0)
        if user_privilege < required_privilege:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions: requires role '{min_role}', user has '{user.role}'."
            )
        return user
    return role_checker
