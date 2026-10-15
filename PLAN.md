# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

eval-metric-honesty

## Roadmap

### core-backend-foundation — FastAPI Core Architecture, OIDC Auth with Keycloak, and Parameterized SQLite Store

Status: done

Acceptance:
- Backend starts with health endpoint at /api/health
- Enforces JWT bearer authentication and role-based access control (viewer, operator, admin)
- Refuses demo mode in production
- Persists records transactionally in SQLite with audit logging

Implementation: `backend/app/main.py`, `backend/app/core/config.py`, `backend/app/core/security.py`, `backend/app/core/database.py`, `backend/app/models/schemas.py`, `backend/app/api/auth.py`

Tests: `backend/tests/test_auth_and_security.py`

### chat-dag-integrity — Chat Tree DAG Integrity Validation and Structural Repair Engine

Status: done

Acceptance:
- Validates chat message tree for parent-child relationship integrity
- Detects and rejects or heals cycles in conversation graphs
- Repairs orphan messages and synchronizes flat message lists with tree history
- Linearizes active dialogue trajectories safely to prevent frontend deadlocks

Implementation: `backend/app/services/chat_dag.py`, `backend/app/api/chats.py`

Tests: `backend/tests/test_chat_dag.py`

### prompt-hygiene-reasoning — Reasoning Tag Isolation and Prompt Reinjection Suppression Engine

Status: done

Acceptance:
- Parses think and thought reasoning blocks from assistant outputs
- Provides model-level toggle to suppress reasoning reinjection in history
- Calculates token overhead savings and evaluates imitation risk score
- Provides deterministic sanitization without needing external LLM credentials

Implementation: `backend/app/services/prompt_hygiene.py`, `backend/app/api/hygiene.py`

Tests: `backend/tests/test_prompt_hygiene.py`

### mcp-user-headers — Per-User Scoped MCP Headers and Tool Proxy Gateway

Status: done

Acceptance:
- Allows users to register custom authentication headers for global MCP tool servers
- Enforces strict per-user header isolation so user credentials never leak across sessions
- Redacts sensitive authorization headers from audit logs
- Dispatches and simulates tool execution through proxy gateway

Implementation: `backend/app/services/mcp_proxy.py`, `backend/app/api/mcp.py`

Tests: `backend/tests/test_mcp_proxy.py`

### multi-provider-gateway-eval — Configurable LLM Adapters and Empirical Evaluation Suite

Status: done

Acceptance:
- Configurable adapters for OpenAI-compatible/Ollama, Anthropic, and Gemini with offline fallback
- Executes reproducible benchmark comparing raw vs sanitized reasoning reinjection
- Calculates prompt inflation ratios and structural healing accuracy metrics
- Provides reproducible evaluation endpoint

Implementation: `backend/app/services/llm_adapters.py`, `backend/app/services/eval_engine.py`, `backend/app/api/evaluations.py`

Tests: `backend/tests/test_llm_adapters.py`, `backend/tests/test_api_workflows.py`

### frontend-workbench-ui — React + TypeScript Domain Dashboard and Interactive Workbench

Status: done

Acceptance:
- Visual DAG tree rendering with orphan detection and repair trigger
- Interactive prompt hygiene workbench with diff view and token metric comparison
- User MCP header credential manager and simulator
- Reproducible evaluation run visualization with empirical metrics
- Full test coverage for user-visible interactions

Implementation: `frontend/src/App.tsx`, `frontend/src/api.ts`, `frontend/src/types.ts`, `frontend/src/context/AuthContext.tsx`, `frontend/src/components/ChatTreeVisualizer.tsx`, `frontend/src/components/HygieneWorkbench.tsx`, `frontend/src/components/McpHeaderManager.tsx`, `frontend/src/components/EvaluationDashboard.tsx`, `frontend/src/components/AuditLogView.tsx`, `frontend/src/components/Navbar.tsx`

Tests: `frontend/src/test/App.test.tsx`, `frontend/src/test/HygieneWorkbench.test.tsx`, `frontend/src/test/ChatTreeVisualizer.test.tsx`

### custom-filter-tags — Configurable Filter Tags for Prompt Hygiene Engine

Status: done

Acceptance:
- PromptHygieneRequest.filter_tags is honored by the engine, not ignored
- Engine builds regex patterns dynamically from the tag list and caches them per tag set
- Users can specify custom tag names (e.g. scratchpad) in addition to think/thought
- Empty filter_tags results in no extraction (no-op passthrough)
- Frontend HygieneWorkbench exposes a comma-separated input for operator-defined tags
- Risk scoring only counts tags within the configured filter set

Implementation: `backend/app/services/prompt_hygiene.py`, `backend/app/api/hygiene.py`, `frontend/src/components/HygieneWorkbench.tsx`, `frontend/src/api.ts`

Tests: `backend/tests/test_prompt_hygiene.py`

### eval-metric-honesty — Data-driven Empirical Evaluation Observations and Benchmark Accuracy

Status: done

Acceptance:
- Evaluation observations embed measured metrics rather than hardcoded constants
- DAG healing observation report reflects the computed healing_pct instead of an assumed 100%
- README benchmark table reports only values reproduced by the suite

Implementation: `backend/app/services/eval_engine.py`, `README.md`

Tests: `backend/tests/test_eval_engine.py`

