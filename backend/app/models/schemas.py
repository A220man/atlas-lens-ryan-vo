"""Pydantic models and schemas for Atlas Lens.

Defines schemas for chat DAG trees, prompt hygiene analysis,
scoped MCP headers, evaluations, and role-based authentication.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


RoleType = Literal["viewer", "operator", "admin"]


class User(BaseModel):
    """Authenticated user context."""
    id: str
    email: str
    role: RoleType = "viewer"
    is_demo: bool = False


class TokenResponse(BaseModel):
    """Bearer token response envelope."""
    access_token: str
    token_type: str = "bearer"
    role: RoleType
    expires_in: int
    user_id: str
    email: str


class ChatMessage(BaseModel):
    """Individual node in the chat message graph."""
    id: str
    parentId: Optional[str] = None
    childrenIds: List[str] = Field(default_factory=list)
    role: Literal["user", "assistant", "system", "tool"] = "user"
    content: str = ""
    timestamp: Optional[float] = None
    model: Optional[str] = None
    thinking_content: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


class ChatGraphPayload(BaseModel):
    """Full chat structure matching standard Open WebUI / conversational exports."""
    id: Optional[str] = None
    title: str = "Untitled Session"
    history: Optional[Dict[str, Any]] = None
    messages: Optional[List[Dict[str, Any]]] = None
    tags: List[str] = Field(default_factory=list)
    created_at: Optional[float] = None
    updated_at: Optional[float] = None


class ChatValidationReport(BaseModel):
    """Diagnostics and integrity report for a chat DAG."""
    is_valid: bool
    total_messages: int
    cycles_detected: bool
    orphan_messages: List[str] = Field(default_factory=list)
    missing_children_links: int = 0
    out_of_sync_count: int = 0
    repaired: bool = False
    details: List[str] = Field(default_factory=list)


class ChatRecord(BaseModel):
    """Stored chat entity representation."""
    id: str
    title: str
    user_id: str
    total_messages: int
    is_repaired: bool
    created_at: str
    updated_at: str
    validation_summary: ChatValidationReport


class PromptMessage(BaseModel):
    """Message item for prompt reconstruction."""
    role: Literal["user", "assistant", "system", "tool"]
    content: str
    reasoning: Optional[str] = None


class PromptHygieneRequest(BaseModel):
    """Request to inspect and sanitize prompt history."""
    model_config = {"protected_namespaces": ()}
    model_id: str = "default"
    reinject_reasoning: bool = False
    messages: List[PromptMessage]
    filter_tags: List[str] = Field(default_factory=lambda: ["think", "thought"])


class SanitizedMessage(BaseModel):
    """Sanitized prompt message with reasoning extracted or stripped."""
    role: str
    content: str
    stripped_reasoning: Optional[str] = None


class PromptHygieneResponse(BaseModel):
    """Sanitization results, token reduction estimates, and imitation risk score."""
    model_config = {"protected_namespaces": ()}
    model_id: str
    reinject_reasoning: bool
    original_estimated_tokens: int
    sanitized_estimated_tokens: int
    token_savings_pct: float
    contains_think_tags: bool
    imitation_risk_score: float = Field(
        ...,
        description="Probability (0.0 to 1.0) that prompt will induce model to hallucinate or imitate tags"
    )
    sanitized_messages: List[SanitizedMessage]


class McpServerCreate(BaseModel):
    """Global MCP tool server registration."""
    name: str
    url: str
    description: str = ""
    global_headers: Dict[str, str] = Field(default_factory=dict)


class McpServerResponse(BaseModel):
    """Registered MCP tool server."""
    id: str
    name: str
    url: str
    description: str
    global_header_keys: List[str]
    created_at: str


class UserMcpHeaderCreate(BaseModel):
    """User-scoped authorization header configuration."""
    header_key: str
    header_value: str


class UserMcpHeaderResponse(BaseModel):
    """Metadata for a user's scoped MCP header with redacted value."""
    id: str
    server_id: str
    user_id: str
    header_key: str
    header_value_masked: str
    created_at: str


class McpToolExecuteRequest(BaseModel):
    """Proxy invocation of a tool on a registered MCP server."""
    server_id: str
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class McpToolExecuteResponse(BaseModel):
    """Result of an MCP tool dispatch."""
    server_id: str
    tool_name: str
    status: Literal["success", "mocked_fallback", "error"]
    result: Any
    injected_header_keys: List[str]
    execution_time_ms: float


class EvaluationBenchmarkRequest(BaseModel):
    """Request to run reproducible empirical evaluation suite."""
    sample_count: int = Field(default=20, ge=5, le=100)
    include_repetition_test: bool = True


class EvaluationMetricSummary(BaseModel):
    """Detailed summary of empirical evaluation measurements."""
    run_id: str
    timestamp: str
    dataset_name: str
    sample_count: int
    mean_token_savings_pct: float
    imitation_suppression_pct: float
    dag_healing_success_pct: float
    mean_repair_latency_ms: float
    observations: List[str]


class AuditLogEntry(BaseModel):
    """Immutable audit trail record."""
    id: str
    timestamp: str
    user_id: str
    action: str
    resource_type: str
    resource_id: str
    details: Dict[str, Any]
