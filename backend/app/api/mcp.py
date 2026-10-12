"""MCP server registration and user-scoped header endpoints.

Addresses Issue #19313.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import require_role
from app.models.schemas import (
    McpServerCreate,
    McpServerResponse,
    McpToolExecuteRequest,
    McpToolExecuteResponse,
    User,
    UserMcpHeaderCreate,
    UserMcpHeaderResponse,
)
from app.services.mcp_proxy import McpProxyService

router = APIRouter(prefix="/api/mcp", tags=["MCP Tool Headers"])


@router.get("/servers", response_model=List[McpServerResponse])
def list_mcp_servers(
    current_user: User = Depends(require_role("viewer"))
) -> List[McpServerResponse]:
    """List globally registered MCP tool servers."""
    return McpProxyService.list_servers()


@router.post("/servers", response_model=McpServerResponse)
def register_mcp_server(
    server: McpServerCreate,
    current_user: User = Depends(require_role("admin"))
) -> McpServerResponse:
    """Register a global MCP tool server (admin role required)."""
    try:
        return McpProxyService.register_server(server, current_user.id)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/servers/{server_id}/headers", response_model=List[UserMcpHeaderResponse])
def get_user_headers(
    server_id: str,
    current_user: User = Depends(require_role("viewer"))
) -> List[UserMcpHeaderResponse]:
    """Retrieve calling user's scoped headers for specified MCP server."""
    return McpProxyService.get_user_headers(server_id, current_user.id)


@router.post("/servers/{server_id}/headers", response_model=UserMcpHeaderResponse)
def set_user_header(
    server_id: str,
    header: UserMcpHeaderCreate,
    current_user: User = Depends(require_role("operator"))
) -> UserMcpHeaderResponse:
    """Set personal credentials / headers for an MCP server (strictly isolated per user)."""
    try:
        return McpProxyService.set_user_header(server_id, current_user.id, header)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/execute", response_model=McpToolExecuteResponse)
async def execute_mcp_tool(
    request: McpToolExecuteRequest,
    current_user: User = Depends(require_role("operator"))
) -> McpToolExecuteResponse:
    """Proxy tool dispatch injecting user-scoped headers with credential isolation."""
    try:
        return await McpProxyService.execute_tool(request, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
