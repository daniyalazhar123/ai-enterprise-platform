# Implementation Roadmap — Phase 0 to Phase 5

> **Document ID:** AEP-ROD-011
> **Version:** 1.0
> **Status:** Approved for planning. Awaiting implementation approval.
> **Owner:** Principal Enterprise Software Architect
> **Classification:** Internal — Enterprise Architecture Specification
> **Governed by:** `master-enterprise-architecture.md` · `system-of-record.md` · `phase-0-implementation-checklist.md`

---

## 1. Purpose

Sequenced implementation plan from the non-bootable baseline to a delivered, hardened platform. Every phase ends at an **approval gate**; no phase begins without written approval. Phases are deliverable- and milestone-driven.

## 2. Phase Overview

| Phase | Name | Theme | Gate |
|---|---|---|---|
| 0 | Stabilize | Make the repo bootable and verified | G0 |
| 1 | SoR Content Core | Durable content system of record | G1 |
| 2 | Reproducible Indexing & Search | Deterministic pipeline + hybrid search + citations | G2 |
| 3 | Frontend & Streaming | Token transport, SSE, guards, UX | G3 |
| 4 | Book Platform & MCP | Multi-book data model + MCP server | G4 |
| 5 | Delivery & Hardening | Docker, K8s, CI/CD, DR, observability | G5 |

```
G0 ──▶ G1 ──▶ G2 ──▶ G3 ──▶ G4 ──▶ G5
boot    SoR     index   frontend  MCP    deliver
```

---

## 3. Phase 0 — Stabilize

**Goal:** make the API bootable, migrations linear, schemas/config complete, and the monorepo `build/test/typecheck` green.

**Executed per:** `phase-0-implementation-checklist.md` (16 tasks, file-by-file).

### Deliverables
- `apps/api/app/core/deps.py`, `apps/api/app/core/auth.py` (created).
- Missing config key `RAG_MAX_CONTEXT_CHUNKS` + 5 AI response schemas (added).
- Agent/service contracts aligned with routers; `zip(tool_calls, [])` bug fixed.
- `0010_merge_heads.py` Alembic merge → single migration head.
- Root `package.json` workspaces enabled.

### Milestones
| # | Milestone | Evidence |
|---|---|---|
| M0.1 | API boots | `/health` → 200 |
| M0.2 | Migration linear | `alembic heads` = 1 |
| M0.3 | Tests green | `pytest` passes |
| M0.4 | Monorepo green | `build`/`typecheck`/`lint` pass |

### Gate G0 exit
Verification checklist V1–V13 (in `phase-0-implementation-checklist.md` §10) all green.

---

## 4. Phase 1 — SoR Content Core

**Goal:** materialize the durable content System of Record in PostgreSQL: books, versions, revisions, units, chunks; deterministic chunking; Postgres-backed document services.

### Deliverables
- Migrations: `books`, `book_versions`, `content_units`, `content_revisions`, `content_chunks` (+ indexes, unique constraints, partial published-version index).
- `books` registry read/write services (book-as-data).
- Deterministic canonicalizer + heading-aware chunker (`canonicalizer_version` recorded).
- `content_hash` / `chunk_hash` dedupe (no-op detection).
- Postgres-backed document ingest replacing the in-memory `_DOCUMENTS_STORE`.
- Remove `SQLModel.metadata.create_all` from startup (ADR: Alembic is the only DDL authority).

### Milestones
| # | Milestone | Evidence |
|---|---|---|
| M1.1 | Schema migrated | `alembic upgrade head` → SoR tables present |
| M1.2 | Registry operational | add/list/update a book via API/service |
| M1.3 | Deterministic chunking | same source → identical hashes (unit test) |
| M1.4 | Ingest end-to-end | upload → units → revisions → chunks persisted |

### Gate G1 exit
SoR test suite green; reproducibility unit test passes; `create_all` removed; reviewed before indexing work.

---

## 5. Phase 2 — Reproducible Indexing & Search

**Goal:** background indexing jobs, hybrid search on the SoR, citation engine.

### Deliverables
- `embedding_jobs` table + worker loop (arq/celery) with retry/backoff and `reindex_all`.
- Embedding determinism: Cohere embed keyed by `content_chunk.id`; upsert-only Qdrant.
- Hybrid search: Qdrant + PG tsvector + RRF (k=60) + Cohere rerank (Redis-cached).
- Citation engine: create/resolve/export; version-pinned citations; per-book `citation_mode`.
- Reconciliation/drift check job (SoR chunks vs Qdrant points).
- Query rewrite with per-book templates.

### Milestones
| # | Milestone | Evidence |
|---|---|---|
| M2.1 | Indexing worker | publish → job → points upserted |
| M2.2 | Determinism | reindex twice → identical point IDs (test) |
| M2.3 | Hybrid search | Qdrant-down → lexical-only answers still served |
| M2.4 | Citations | every answer maps to resolvable chunk citations |

### Gate G2 exit
Rebuild reproducibility test; fail-soft search demo (Qdrant killed); citation coverage metrics.

---

## 6. Phase 3 — Frontend & Streaming

**Goal:** fix token transport, streaming proxy, and route guards; align frontend with the booted API.

### Deliverables
- Access token in memory only; refresh via HttpOnly cookie (replace `sessionStorage` in `packages/auth/src/api.ts`; fix `refresh_token: ""` in `hooks.ts`).
- Next.js `middleware.ts` guard; `ProtectedRoute` used consistently.
- SSE proxy for streaming endpoints (POST SSE → browser-compatible stream; resolve EventSource GET mismatch).
- AI pages (chat/tutor/quiz/interview/search/documents) wired to working API.

### Milestones
| # | Milestone | Evidence |
|---|---|---|
| M3.1 | Refresh flow fixed | no empty `refresh_token`; rotation works |
| M3.2 | Guards active | unauthenticated → redirect |
| M3.3 | Streaming UX | chat/tutor/quiz stream live with token events |
| M3.4 | E2E happy path | login → chat → citations rendered |

### Gate G3 exit
E2E happy-path automated test; frontend auth defects closed (per `security-rbac-architecture.md` §3.3).

---

## 7. Phase 4 — Book Platform & MCP

**Goal:** operationalize multi-book as data, expose the MCP server, onboard a second book as proof.

### Deliverables
- Multi-book data model fully exercised: registry-driven routing, features, RBAC book scopes, per-book collections/config.
- MCP server: `books.list/info/search/retrieve/chat/cite/publish_info` behind the gateway with RBAC + audit (per `mcp-architecture.md`).
- Second book onboarding runbook executed (zero code changes).
- Admin endpoints for registry + publishing workflow.

### Milestones
| # | Milestone | Evidence |
|---|---|---|
| M4.1 | MCP contract tests | `tools/list` + each tool passes |
| M4.2 | Second book live | banking-finance serves search/chat/citations |
| M4.3 | RBAC scoping | cross-book access denied (403) |
| M4.4 | Publish workflow | DRAFT→PUBLISHED end-to-end via admin |

### Gate G4 exit
MCP contract suite green; second-book onboarding without code changes demonstrated.

---

## 8. Phase 5 — Delivery & Hardening

**Goal:** production delivery: Docker images, Kubernetes manifests, CI/CD, DR, observability, secret management.

### Deliverables
- Docker images: `api`, `worker`, `web`, `docs`, `mcp`, `nginx` (multi-stage, non-root, pinned, healthchecked).
- `docker compose` dev stack with migrations `init` service.
- K8s manifests (Kustomize): base + dev/staging/prod overlays; HPA, PDB, NetworkPolicy, ExternalSecret, migration `Job`.
- CI/CD: GitHub Actions (build → scan/SBOM → staging → smoke → prod canary), `kubectl kustomize` dry-run gate.
- Observability: Prometheus metrics, OpenTelemetry traces, structured JSON logs, dashboards + alerts.
- Secrets: Vault/KMS integration; remove `.secrets/` auto-write from config loader.
- DR: PITR + backups, quarterly restore drills, reconciliation/reindex runbooks.

### Milestones
| # | Milestone | Evidence |
|---|---|---|
| M5.1 | Images build | `docker build` green for all images; scan clean |
| M5.2 | Compose parity | dev stack runs full platform |
| M5.3 | K8s dry-run | `kubectl kustomize` + CI lint pass |
| M5.4 | CI/CD pipeline | commit → prod deploy (canary) works |
| M5.5 | DR drill | restore within RTO/RPO; reconciliation diff = 0 |
| M5.6 | Observability live | cost, latency, queue, citation metrics alerting |

### Gate G5 exit
DR acceptance; secret hygiene scan green; production rollout smoke passed.

---

## 9. Cross-Cutting Guards (all phases)

1. **Approval gates** — no phase begins without written approval of the prior gate's exit evidence.
2. **Scope discipline** — no feature work outside the current phase's deliverables.
3. **SoR invariant** — every durable write commits to PostgreSQL first.
4. **No secrets in repo/images** — enforced from G0 (`gitleaks`/scan from G5).
5. **VCS baseline** — `git init` + baseline commit required before Phase 0 execution.
6. **Documentation parity** — each phase updates `docs/architecture/` where design changes.

## 10. Timeline Estimate

| Phase | Estimate |
|---|---|
| 0 — Stabilize | ~2–3 focused days |
| 1 — SoR Content Core | ~1–2 weeks |
| 2 — Indexing & Search | ~1–2 weeks |
| 3 — Frontend & Streaming | ~1 week |
| 4 — Book Platform & MCP | ~1–2 weeks |
| 5 — Delivery & Hardening | ~2–3 weeks |
| **Total** | **~7–12 weeks** (sequential; parallel tracks where independent) |

## 11. Status

**Planning complete. No production code written.** Awaiting approval to begin Phase 0 per `phase-0-implementation-checklist.md`.
