# Changelog

## 1.0.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-10-12

### Added
- Initial release of Atlas Lens: AI/ML developer observability and prompt hygiene workbench.
- Chat DAG integrity engine with cycle detection, orphan repair, and tree linearization to resolve frontend deadlocks.
- Reasoning tag isolation engine detecting and stripping `<think>` blocks to prevent pathological model self-imitation and prompt bloat.
- User-scoped MCP server headers proxy enabling multi-tenant credential isolation without leaking keys across sessions.
- Multi-provider LLM gateway supporting OpenAI-compatible, Ollama, Anthropic, and Gemini APIs with offline deterministic fallback.
- Empirical evaluation benchmark suite measuring token savings, tag imitation suppression, and structural healing fidelity.
- Production OIDC authentication through Keycloak with PKCE verification and local-only demo mode guard.
- React 18 + TypeScript + Vite frontend dashboard featuring DAG visualization, prompt hygiene workbench, and evaluation charts.
- Docker compose configuration, multi-stage Dockerfiles, and GitHub Actions CI workflow.
