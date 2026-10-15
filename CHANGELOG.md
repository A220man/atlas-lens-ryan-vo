# Changelog

## 1.1.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## [1.3.0] - 2026-10-15

### Fixed
- **Honest empirical metrics**: `EvaluationEngine.run_benchmark` observations now embed the measured DAG healing rate instead of a hardcoded "100%" claim, so the report never asserts a benchmark number not observed for the run. Observation assembly was extracted into a pure, unit-tested helper (`_build_observations`).
- **Benchmark table accuracy**: README "Measured Benchmark Results" corrected from the previously claimed `42.5% – 50.0%` context-token-savings range to the deterministic baseline actually reproduced by the suite (`35.38%`).

### Added
- Dedicated `backend/tests/test_eval_engine.py` unit tests asserting observations are data-driven, including a synthetic non-100% healing case.

### Tests
- Backend: 42 tests pass (38 prior + 4 new). Frontend: 8 tests pass; typecheck and production build succeed.

## [1.2.0] - 2026-10-15

### Added
- Configurable `filter_tags` parameter in the Prompt Hygiene engine: users can now specify custom tag names (e.g. `think`, `thought`, `scratchpad`) to extract and strip from reasoning traces, instead of only the hardcoded defaults. Patterns are compiled and cached per tag set for performance.
- Frontend `HygieneWorkbench` now exposes a "Custom Filter Tags" input field for operator-defined tag configuration.
- Backend tests covering selective tag extraction, extended tag names, empty filter sets, and risk scoring with non-default tags.

### Fixed
- Eliminated React `key` prop warning in `McpHeaderManager` server `<select>` by guarding option rendering against entries lacking a valid `id` and providing a disabled placeholder option.

## [1.1.0] - 2026-10-15

### Fixed
- Corrected Chat DAG orphan repair timestamp sort: nodes without timestamps no longer sort first and become the canonical root; genuine root nodes with explicit timestamps are now preserved as the root during structural healing.
- Fixed imitation risk score double-counting: properly closed and tags are no longer also counted as unclosed, producing accurate imitation risk scores (e.g. 0.65 for one closed tag instead of 0.80).

### Added
- Regression tests for DAG root preservation over timestep-less orphans and for imitation risk no double-counting.

## [1.0.0] - 2026-10-12

Partial code published for continued development. Known issues: STATUS.md.

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

### Added
- Initial release of Atlas Lens: AI/ML developer observability and prompt hygiene workbench.
- Chat DAG integrity engine with cycle detection, orphan repair, and tree linearization to resolve frontend deadlocks.
- Reasoning tag isolation engine detecting and stripping `think` blocks to prevent pathological model self-imitation and prompt bloat.
- User-scoped MCP server headers proxy enabling multi-tenant credential isolation without leaking keys across sessions.
- Multi-provider LLM gateway supporting OpenAI-compatible, Ollama, Anthropic, and Gemini APIs with offline deterministic fallback.
- Empirical evaluation benchmark suite measuring token savings, tag imitation suppression, and structural healing fidelity.
- Production OIDC authentication through Keycloak with PKCE verification and local-only demo mode guard.
- React 18 + TypeScript + Vite frontend dashboard featuring DAG visualization, prompt hygiene workbench, and evaluation charts.
- Docker compose configuration, multi-stage Dockerfiles, and GitHub Actions CI workflow.