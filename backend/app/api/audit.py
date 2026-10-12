"""Audit trail endpoints.

Requires admin role to view full mutation audit history.
"""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends, Query

from app.core.database import list_audit_logs
from app.core.security import require_role
from app.models.schemas import User

router = APIRouter(prefix="/api/audit", tags=["Audit Logs"])


@router.get("/logs", response_model=List[Dict[str, Any]])
def get_audit_trail(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_role("admin"))
) -> List[Dict[str, Any]]:
    """Retrieve immutable audit logs (admin only)."""
    return list_audit_logs(limit=limit, offset=offset)
