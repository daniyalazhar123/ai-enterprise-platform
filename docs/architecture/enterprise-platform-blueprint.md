# Enterprise Platform Blueprint — Enterprise AI Book Platform

> **Document ID:** AEP-BP-001
> **Version:** 1.0
> **Status:** Approved for design. Awaiting implementation approval.
> **Owner:** Principal Enterprise Software Architect
> **Classification:** Internal — Enterprise Architecture Specification

---

## 1. Purpose

This blueprint defines the target enterprise architecture for the AI Enterprise Book Platform: a single platform that operates **many books** (Enterprise AI Engineering, Banking & Finance, Cybersecurity, Robotics, and future titles) on **one architecture, one System of Record, and one set of AI services**. It is the top-level specification that all other documents in `docs/architecture/` elaborate.

## 2. Guiding Principles

| # | Principle | Meaning |
|---|---|---|
| P1 | **PostgreSQL is the only System of Record** | All durable facts live in PostgreSQL. Qdrant, Redis, and derived artifacts are projections. |
| P2 | **Derived stores are rebuildable** | Any vector index, cache, or queue can be reconstructed from the SoR without data loss. |
| P3 | **Book = data, not code** | A new book requires content + registry config, never an edit under `apps/` or `packages/`. |
| P4 | **Determinism** | Same content in → byte-identical chunks, hashes, embeddings, and point IDs out. |
| P5 | **Version truth** | Every citation and answer is pinned to a published edition; history is immutable. |
| P6 | **Fail-soft search** | Lexical search on the SoR answers even when the vector store is down. |
| P7 | **Composability** | Capabilities are bounded modules with explicit interfaces, microservice-ready but delivered as a modular monolith first. |
| P8 | **Observability by default** | Every AI call, job, and publish is auditable, metered, and cost-tracked. |

## 3. Strategic Goals

1. **G1 — One platform, many books.** Multi-book support with zero per-book code.
2. **G2 — Enterprise-grade SoR.** Durable, immutable, versioned, compliant content backbone.
3. **G3 — Grounded AI.** Every answer cites a published, resolvable source.
4. **G4 — Reproducible intelligence.** Embeddings and indexes rebuild identically.
5. **G5 — Operational maturity.** Docker now, Kubernetes ready, CI/CD, DR, observability.
6. **G6 — Extensible surface.** HTTP API + MCP server for external LLM/IDE consumption.

## 4. Non-Goals (Out of Scope)

- A public SaaS marketplace in v1.
- Multi-tenant organization data isolation beyond book-scoped RBAC.
- Custom fine-tuned foundation models in v1 (all embeddings/LLMs are third-party managed).
- Real-time collaborative authoring (revisions are append-only, not live).

## 5. Logical Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         PRESENTATION LAYER                          │
│   apps/web (Next.js 15)          apps/book (Docusaurus sites)       │
└───────────────────────────────┬──────────────────────────────────────┘
                                │ HTTPS
┌───────────────────────────────▼──────────────────────────────────────┐
│                          GATEWAY LAYER                              │
│        FastAPI Gateway (REST /api)      MCP Gateway (tools)         │
│        auth ── rate-limit ── RBAC ── audit ── routing               │
└───────────────┬─────────────────────────────────┬────────────────────┘
                │                                 │
┌───────────────▼────────────────┐   ┌────────────▼────────────────────┐
│        DOMAIN LAYER            │   │         AI LAYER                │
│  Content Service               │   │  Agent Runtime (chat/tutor/    │
│  Registry/Version/Publish      │   │   quiz/interview)              │
│  Citation Service              │   │  RAG Pipeline (hybrid)         │
│  RBAC / Identity               │   │  Guardrails / Citations        │
└───────────────┬────────────────┘   └────────────┬────────────────────┘
                │                                  │
┌───────────────▼──────────────────────────────────▼───────────────────┐
│                          INFRASTRUCTURE LAYER                        │
│   PostgreSQL 16+ (SoR)     Qdrant (derived)     Redis (cache/queue) │
│   Object storage (backups)  Vault/KMS (secrets)  Observability stack │
└───────────────────────────────────────────────────────────────────────┘
```

## 6. Technology Stack

| Layer | Technology | Role |
|---|---|---|
| Backend | FastAPI + SQLModel, Python 3.13+ | API + domain logic |
| SoR | PostgreSQL 16+ | all durable state |
| Vector (derived) | Qdrant | semantic retrieval |
| Cache/Queue | Redis | cache, rate-limit, queues |
| Embeddings / Rerank | Cohere v3 | deterministic embeddings + rerank |
| Frontend | Next.js 15 + Tailwind | web app |
| Docs sites | Docusaurus 3 | per-book documentation |
| Background jobs | APScheduler / arq | scheduling + workers |
| Container | Docker | build + runtime images |
| Orchestration | Kubernetes (Kustomize) | future-ready, not day-1 |
| CI/CD | GitHub Actions | build, test, deploy |
| Secret management | Vault / KMS | secrets, never on disk |

## 7. Bounded Contexts (Modules)

```
modules/
├─ identity      → users, sessions, refresh tokens, roles, permissions
├─ content       → books, versions, revisions, units, chunks
├─ publishing    → workflow state machine, audit events
├─ search        → hybrid retrieval, reranking, version filters
├─ ai            → agents, prompts, citations, cost logging
├─ jobs          → indexing jobs, queues, retries
└─ gateway       → REST + MCP surfaces, rate limiting
```

Each context owns its tables, exposes an internal API, and publishes domain events after SoR commit. This is the seam for future service extraction (microservice readiness).

## 8. Deployment Topology (Target)

```
Browser/IDE ─▶ nginx (TLS ingress)
                  ├─ /api  ─▶ api pods   (FastAPI, stateless, HPA)
                  ├─ /web  ─▶ web pods   (Next.js)
                  ├─ /docs ─▶ docs pods  (Docusaurus static)
                  └─ /mcp  ─▶ mcp pods   (MCP protocol server)

workers (indexing) ── consume jobs from Redis queue
postgres (primary + read replica + WAL → cold storage)
qdrant (derived, rebuildable)
redis (cache + queues, ephemeral)
cohere (external embedding/rerank API)
```

## 9. Delivery Roadmap (Approval-Gated)

| Phase | Deliverable | Exit Gate |
|---|---|---|
| **Phase 0 — Stabilize** | API boots; Alembic graph linear; missing schemas/config added; workspaces enabled; build/test/typecheck green | Runbook demo |
| **Phase 1 — SoR content core** | Books, versions, revisions, units, chunks tables; deterministic chunking; Postgres-backed docs | SoR test suite |
| **Phase 2 — Reproducible indexing/search** | Background jobs, hashing, hybrid search, citation engine | Rebuild reproducibility test |
| **Phase 3 — Frontend & streaming** | Token transport, SSE proxy, route guards | E2E happy-path |
| **Phase 4 — Book platform + MCP** | Multi-book data model, MCP server | MCP contract tests |
| **Phase 5 — Delivery & hardening** | Docker images, K8s manifests, CI/CD, DR drills | DR acceptance |

Each gate requires written approval before the next phase begins.

## 10. Architecture Decision Records (ADR) Summary

| ADR | Decision | Rationale |
|---|---|---|
| ADR-001 | PostgreSQL = only SoR | ACID, tsvector, PITR, single backup target |
| ADR-002 | Qdrant = derived only | Fully rebuildable from SoR; never authoritative |
| ADR-003 | Redis = cache/queue only | Flush-safe; no durable facts |
| ADR-004 | Deterministic chunk IDs | Idempotent upserts, reproducible rebuilds |
| ADR-005 | Version-pinned citations | Trust/compliance for law/banking/health |
| ADR-006 | Modular monolith first | Simple deploys, mechanical service extraction |
| ADR-007 | Docker now, K8s future | Cost-efficient, K8s as deployment target |
| ADR-008 | MCP as second protocol surface | External LLMs/IDEs consume books without new UI |

## 11. Acceptance Criteria (Platform Level)

1. Kill Qdrant + Redis in staging → platform still serves grounded content (degraded, correct).
2. Reindex twice → byte-identical chunks and point IDs; reconciliation diff = 0.
3. Add a second book → zero code changes under `apps/` or `packages/`.
4. Answer citing v1 remains verifiable after v2 publishes.
5. Every AI call is metered and audited (cost + event).
6. Restore drill meets RTO/RPO targets (see DR section).

## 12. Document Map

| Document | Scope |
|---|---|
| `enterprise-system-of-record.md` | Complete SoR specification |
| `multi-book-architecture.md` | Book-as-data model, registry, routing |
| `database-architecture.md` | PostgreSQL schema, partitions, indexes, migrations |
| `ai-architecture.md` | Agent runtime, model routing, memory, cost |
| `rag-search-architecture.md` | Hybrid retrieval, citations, failure semantics |
| `mcp-architecture.md` | MCP protocol surface and tools |
| `docker-kubernetes-architecture.md` | Container + orchestration strategy |
| `security-rbac-architecture.md` | AuthN/AuthZ, RBAC, audit, secrets |
| `master-enterprise-architecture.md` | Master index, ADR log, glossary, phase gates |
