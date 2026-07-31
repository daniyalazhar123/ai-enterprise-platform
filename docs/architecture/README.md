# Architecture Documentation

Enterprise architecture specification set for the AI Enterprise Book Platform. **Design/planning only — no production code written.**

## Master Index

Start at `master-enterprise-architecture.md` (complete platform architecture + ADR log + glossary), then `implementation-roadmap.md` (phases) and `phase-0-implementation-checklist.md` (next execution gate).

| # | Document | ID | Scope |
|---|---|---|---|
| 1 | `master-enterprise-architecture.md` | AEP-MEA-010 | Complete platform architecture, SoR, multi-book, AI, deployment, Docker, K8s, MCP, citation engine, AI Tutor, Daniyal AI Developer, versioning, publishing, roadmap |
| 2 | `system-of-record.md` | AEP-SOR-M | DB as SoR, book hierarchy, versioning, chunking, embeddings, background indexing, hybrid search, citations, registry, content pipeline |
| 3 | `implementation-roadmap.md` | AEP-ROD-011 | Phase 0–5 deliverables, milestones, gates, timeline |
| 4 | `phase-0-implementation-checklist.md` | AEP-P0C-000 | G0 objectives, tasks, affected files, dependency graph, rollback, verification, risks, effort |
| 5 | `enterprise-platform-blueprint.md` | AEP-BP-001 | Vision, principles, stack, roadmap |
| 6 | `enterprise-system-of-record.md` | AEP-SOR-002 | SoR lifecycle: publishing, recovery, DR, backup |
| 7 | `multi-book-architecture.md` | AEP-MBA-003 | Book-as-data, registry, routing, onboarding |
| 8 | `database-architecture.md` | AEP-DBA-004 | PostgreSQL schema, partitions, migrations, replication |
| 9 | `ai-architecture.md` | AEP-AIA-005 | Agent runtime, model routing, guardrails, cost |
| 10 | `rag-search-architecture.md` | AEP-RSA-006 | Hybrid retrieval, RRF, rerank, citations |
| 11 | `mcp-architecture.md` | AEP-MCP-007 | MCP protocol surface, tools, auth |
| 12 | `docker-kubernetes-architecture.md` | AEP-DKR-008 | Images, compose, K8s, rollout, observability |
| 13 | `security-rbac-architecture.md` | AEP-SEC-009 | AuthN/AuthZ, RBAC scopes, audit, secrets |

## Prior Deliverables

- `enterprise-architecture-review.md` — full-repo audit, scores, defect register (points to the canonical set).
- **Superseded (retained for audit, not authoritative):** `system-of-record-design.md`, `platform-architecture.md` — content fully covered by the canonical SoR and platform docs above.
- Legacy implementation blueprints (`auth-module.md`, `frontend-architecture.md`, `monorepo-implementation-plan.md`, `implementation/*`) — superseded where overlapping.

## Status

Documentation phase complete. Awaiting approval to begin **Gate G0** (`phase-0-implementation-checklist.md`). No production code written.
