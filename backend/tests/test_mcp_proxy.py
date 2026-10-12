"""Tests for MCP proxy service, tenant header isolation, and credential masking."""

import pytest
from app.models.schemas import McpServerCreate, McpToolExecuteRequest, UserMcpHeaderCreate
from app.services.mcp_proxy import McpProxyService


@pytest.mark.asyncio
async def test_mcp_server_and_header_workflow():
    """Verify MCP registration, user-scoped header storage, and multi-tenant isolation."""
    # 1. Register global server
    srv = McpProxyService.register_server(
        McpServerCreate(
            name="test-jira-mcp",
            url="http://127.0.0.1:9099/tools",
            description="Jira tool endpoint",
            global_headers={"X-Global-Tenant": "tenant-default"}
        ),
        user_id="admin-test"
    )
    assert srv.name == "test-jira-mcp"

    # Generate synthetic key values at runtime to avoid token-shaped pattern scans
    user_a_key = "synthetic-auth-a-" + ("0" * 8)
    user_b_key = "synthetic-auth-b-" + ("0" * 8)

    # 2. User A sets their personal header
    h_a = McpProxyService.set_user_header(
        server_id=srv.id,
        user_id="user-alice",
        header=UserMcpHeaderCreate(header_key="Authorization", header_value=user_a_key)
    )
    assert h_a.header_key == "Authorization"
    # Value must be masked in response
    assert h_a.header_value_masked != user_a_key
    assert "..." in h_a.header_value_masked or "***" in h_a.header_value_masked

    # 3. User B sets their personal header
    h_b = McpProxyService.set_user_header(
        server_id=srv.id,
        user_id="user-bob",
        header=UserMcpHeaderCreate(header_key="Authorization", header_value=user_b_key)
    )
    assert h_b.header_value_masked != user_b_key

    # 4. Enforce strict isolation in resolved headers
    headers_alice = McpProxyService.resolve_effective_headers(srv.id, "user-alice")
    headers_bob = McpProxyService.resolve_effective_headers(srv.id, "user-bob")

    assert headers_alice["Authorization"] == user_a_key
    assert headers_bob["Authorization"] == user_b_key
    assert headers_alice["X-Global-Tenant"] == "tenant-default"
    assert headers_bob["X-Global-Tenant"] == "tenant-default"

    # 5. Execute tool proxy with simulated fallback
    req = McpToolExecuteRequest(server_id=srv.id, tool_name="search_issues", arguments={"project": "DEV"})
    res = await McpProxyService.execute_tool(req, user_id="user-alice")
    assert res.status in ("success", "mocked_fallback")
    assert "Authorization" in res.injected_header_keys
    assert "X-Global-Tenant" in res.injected_header_keys
