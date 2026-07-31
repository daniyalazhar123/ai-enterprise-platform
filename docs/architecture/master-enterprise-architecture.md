# Master Enterprise Architecture — Enterprise Specification

> **Document ID:** AEP-MEA-010
> **Version:** 2.0
> **Status:** Approved for design. Awaiting implementation approval.
> **Owner:** Principal Enterprise Software Architect
> **Classification:** Internal — Enterprise Architecture Specification

---

## 1. Purpose

This is the **master architecture document** for the AI Enterprise Book Platform. It consolidates the complete platform architecture into a single reference: System of Record, multi-book model, AI runtime, deployment, MCP, citation engine, AI Tutor, AI Developer, versioning, publishing workflow, and the future roadmap. It is the authoritative entry point; detailed specifications live in the companion documents referenced throughout.

## 2. Document Index

| # | Document | ID | Scope |
|---|---|---|---|
| 1 | `enterprise-platform-blueprint.md` | AEP-BP-001 | Vision, principles, stack, roadmap, ADR summary |
| 2 | `system-of-record.md` | AEP-SOR-M | Database SoR, book hierarchy, chunking, embeddings, indexing, hybrid search, citations, registry, content pipeline |
| 3 | `enterprise-system-of-record.md` | AEP-SOR-002 | Full SoR lifecycle: publishing, revisions, recovery, DR, backup |
| 4 | `multi-book-architecture.md` | AEP-MBA-003 | Book-as-data model, registry, routing, onboarding |
| 5 | `database-architecture.md` | AEP-DBA-004 | PostgreSQL schema, indexes, partitioning, migrations, replication |
| 6 | `ai-architecture.md` | AEP-AIA-005 | Agent runtime, model routing, tools, memory, guardrails, cost |
| 7 | `rag-search-architecture.md` | AEP-RSA-006 | Hybrid retrieval, chunking, embeddings, RRF, rerank, citations |
| 8 | `mcp-architecture.md` | AEP-MCP-007 | MCP protocol surface, tools, auth, deployment |
| 9 | `docker-kubernetes-architecture.md` | AEP-DKR-008 | Images, compose, K8s manifests, rollout, observability |
| 10 | `security-rbac-architecture.md` | AEP-SEC-009 | AuthN/AuthZ, RBAC scopes, audit, secrets, threat model |
| 11 | `master-enterprise-architecture.md` | AEP-MEA-010 | This document |
| 12 | `phase-0-implementation-checklist.md` | AEP-P0C-000 | Gate G0 file-by-file execution plan |
| 13 | `implementation-roadmap.md` | AEP-ROD-011 | Phase 0–5 deliverables and milestones |

**Reading order:** 11 (this doc) → 13 → 12 → 2 → 1 → 5 → 7 → 6 → 8 → 9 → 10.

---

## 3. Complete Enterprise Platform Architecture

### 3.1 Vision

One platform, many books. Every book — Enterprise AI Engineering, Banking & Finance, Cybersecurity, Robotics, and future titles — runs on the **same architecture, the same System of Record, the same AI services**, and is added as **data, not code**.

### 3.2 Guiding principles

1. **PostgreSQL is the only System of Record**; Qdrant/Redis are derived projections.
2. **Derived stores are rebuildable** from the SoR without data loss.
3. **Book = data, not code** — zero per-book changes under `apps/`/`packages/`.
4. **Determinism** — identical input + pipeline → identical chunks, hashes, embeddings, point IDs.
5. **Version truth** — every citation/answer pinned to a published edition.
6. **Fail-soft search** — the SoR lexical leg answers when vector stores are down.
7. **Observability by default** — every AI call, job, and publish is audited and metered.

### 3.3 Logical architecture

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
│  Registry/Version/Publish      │   │   quiz/interview/developer)    │
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

### 3.4 Bounded contexts

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

---

## 4. System of Record

The SoR is the authoritative, transactional core. See `system-of-record.md` (design) and `enterprise-system-of-record.md` (lifecycle).

- **PostgreSQL owns:** books, versions, revisions, units, chunks, citations, conversations, users, permissions, audit events, jobs.
- **Qdrant owns:** derived vectors only (point_id = `content_chunk.id`, rebuildable).
- **Redis owns:** cache + queues only (flush-safe).
- **Rule:** commit to PostgreSQL before any derived-store write; the SoR always wins on disagreement.

---

## 5. Multi-Book Architecture

- A book is `content/books/{slug}/` + one registry row (`books`). No per-book code.
- Per-book config (`book.config`/`model_routing`) drives routing, prompts, top_k, citation mode, features.
- Logical isolation by `book_id` FK everywhere; physical isolation (partitions, collections) is a tuning decision.
- RBAC scopes `book:{slug}:{read|write|review|publish|manage}`.
- Full spec: `multi-book-architecture.md`.

---

## 6. AI Architecture

### 6.1 Agents

| Agent | Purpose | Tools | Output |
|---|---|---|---|
| `ChatAgent` | book Q&A grounded in SoR | rag_search, citations, glossary | streamed answer + citations |
| `TutorAgent` | Socratic guided learning | rag_search, progress | steps + questions + citations |
| `QuizAgent` | generate + grade quizzes | unit_tree, quiz_gen/grade | quiz + answers + rationale |
| `InterviewAgent` | scenario interviews + eval | scenario, evaluate | session + rubric |
| `DeveloperAgent` (Daniyal AI Developer) | codebase-focused AI developer | see §12 | analysis + code + citations |

### 6.2 Model routing (per book)

```
request → resolve model_routing (book.config)
  ├─ primary available → use primary
  ├─ primary fails → fallback (audited)
  ├─ both fail → cached answer (flagged) or clear degraded error
```

### 6.3 Contracts & invariants
- Uniform agent interface: `run()` / `run_stream()`.
- Tool results bound to originating `tool_call_id` (the `zip(tool_calls, [])` bug is prohibited).
- Every model call logged to `ai_call_logs` (cost, tokens, latency).
- Full spec: `ai-architecture.md`.

---

## 7. Deployment Architecture

### 7.1 Topology

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

### 7.2 Consistency contract

| Operation | SoR | Qdrant | Redis |
|---|---|---|---|
| Publish revision | commit row + state | job enqueued | invalidate caches |
| Reindex unit | job stats | upsert points | clear query cache |
| Delete unit | tombstone + archive | delete points (async) | invalidate |
| Answer question | store message + citations | — | cache rerank |

---

## 8. Docker

- **One image per process:** `api`, `worker`, `web`, `docs`, `mcp`, `nginx`.
- Multi-stage builds, non-root user, pinned base images, healthchecks, no secrets in images.
- Dev: `docker compose` full stack (postgres, qdrant, redis, api, worker, web, mcp, nginx) with a migrations `init` service.
- Full spec: `docker-kubernetes-architecture.md`.

---

## 9. Kubernetes

- **Future-ready, not day-1:** compose first; K8s manifests authored and CI-tested from day 1 (Kustomize).
- Resources: `Deployment`+`Service` per process, `HPA` (api/worker/web/mcp), migration `Job`, `Ingress` (TLS), `PDB`, `NetworkPolicy`, `ExternalSecret` (Vault/KMS).
- Rollout: build+scan+push → staging (migration Job → smoke) → prod canary → full rollout; rollback = revert manifest revision (state safe in SoR).
- Full spec: `docker-kubernetes-architecture.md`.

---

## 10. MCP Server

- MCP is a second protocol surface over the same gateway/domain/SoR — **a new interface, never a new store**.
- Tools: `books.list`, `books.info`, `books.search`, `books.retrieve`, `books.chat`, `books.cite`, `books.publish_info`.
- Every tool book-scoped + RBAC-checked; read-only by default; citations structured.
- Deployed as its own `mcp` process behind `/mcp`; stdio only for local/dev.
- Full spec: `mcp-architecture.md`.

---

## 11. Citation Engine

- Every grounded answer maps to published text anchors: `(book_id, version_id, unit_id, revision_id, chunk_id, source_text, anchor, answer_hash)`.
- Citations created at answer time, stored forever, **version-pinned** — republishing never rewrites history.
- Per-book `citation_mode`: `strict` (Law/Banking/Health — minimum N citations), `standard` (flag low-score), `lax` (best-effort, "unverified").
- Queryable/exportable via REST + MCP. Full spec: `rag-search-architecture.md` §7 and `system-of-record.md` §10.

---

## 12. AI Tutor and Daniyal AI Developer

### 12.1 AI Tutor (`TutorAgent`)

- Socratic guided learning: never answers directly; asks guiding questions; tracks mastery.
- Driven by `book.config` difficulty ladder and `learning_progress` (SoR).
- Uses `rag_search` + unit tree + citations; per-book prompts via `prompt_manager`.
- `features.tutor` gates availability.

### 12.2 Daniyal AI Developer (`DeveloperAgent`)

An AI developer capability targeted at the platform's own **codebase corpus** (and, in the future, any connected repository).

| Aspect | Spec |
|---|---|
| Corpus | indexed code units (repo structure, files, symbols) stored in the SoR as `content`-style units under a special book slug (e.g., `developer`) |
| Tools | `code.search`, `code.retrieve`, `code.explain`, `code.refactor_suggest`, `code.test_suggest`, `code.cite` |
| Grounding | same citation engine — every code claim cites a file + line range (version-pinned to repo snapshot) |
| Safety | read-only analysis first; no auto-apply to the repo without explicit approval; all suggestions are DRAFT revisions |
| RBAC | `book:developer:read` / `book:developer:write` scopes |
| Output | analysis, suggested diffs as revisions, test recommendations, all with citations |

The Developer agent shares the agent runtime, model routing, guardrails, and cost metering of every other agent. It is enabled via a registry row, not new code.

---

## 13. Versioning

- **SemVer per book** (`major.minor.patch`): breaking restructure = major; additive chapters = minor; corrections = patch.
- One published version per book at a time (enforced by partial unique index), plus unlimited drafts/archived.
- Version is the anchor of truth: revisions, chunks, and citations all carry `version_id`.
- RAG and MCP accept `version_id` to query exactly that edition.
- Full spec: `system-of-record.md` §4 and `enterprise-system-of-record.md` §3–4.

---

## 14. Publishing Workflow

```
DRAFT ──submit──▶ IN REVIEW ──approve──▶ APPROVED ──publish──▶ PUBLISHED
   ▲                │                                            │
   └──── reject ────┘                             supersede ────▶ ARCHIVED
```

- Permissions: `content:write` (create/submit), `content:review` (approve/reject), `content:publish` (publish), `content:manage` (deprecate/archive).
- Publish is transactional: mark revision published + advance version in one transaction, then enqueue `embedding_job` (async index lag is designed-in and safe).
- Full spec: `enterprise-system-of-record.md` §5.

---

## 15. Future Roadmap

> **Terminology:** *Phase N* (execution) and *Gate GN* (approval) denote the same stage, e.g. Phase 0 = Gate G0. The authoritative phase plan, milestones, and exit evidence live in `implementation-roadmap.md`; the G0 file-by-file plan is `phase-0-implementation-checklist.md`.

| Horizon | Direction |
|---|---|
| **G1–G5 execution** | SoR content core → indexing/search → frontend/streaming → book platform + MCP → delivery/hardening (see `implementation-roadmap.md`) |
| **Post-G5** | Multi-tenant org isolation (beyond book scoping); SSO federation; usage billing per tenant |
| **AI evolution** | Provider abstraction (single interface over OpenAI/OpenRouter/Gemini/Grok/Cohere); optional fine-tuned domain models; evaluator-driven prompt optimization |
| **Content** | Structured exercises/glossary taxonomies; authored quizzes; multilingual book editions |
| **Developer surface** | Daniyal AI Developer reaching GA; MCP tool marketplace; repo-corpus ingestion for arbitrary projects |
| **Scale** | LIST partitioning by book; managed Postgres (Neon/RDS) with CI branching; multi-region DR |

---

## 16. Architecture Decision Record (ADR) Log

| ADR | Status | Decision | Owner doc |
|---|---|---|---|
| ADR-001 | Approved | PostgreSQL is the only SoR | SOR |
| ADR-002 | Approved | Qdrant is derived only, rebuildable | SOR |
| ADR-003 | Approved | Redis is cache + queues only | SOR |
| ADR-004 | Approved | Deterministic chunk IDs + content hashing | SOR, DBA |
| ADR-005 | Approved | Version-pinned citations (immutable truth) | SOR, AIA |
| ADR-006 | Approved | Modular monolith first; microservice-ready | BP-001 |
| ADR-007 | Approved | Docker now; K8s future-ready | DKR-008 |
| ADR-008 | Approved | MCP as second protocol surface | MCP-007 |
| ADR-009 | Approved | Hybrid search: lexical leg on SoR tsvector | RSA-006 |
| ADR-010 | Approved | Retain existing auth module; extend with book scopes | SEC-009 |
| ADR-011 | Proposed | LIST partitioning by book when volume demands | DBA-004 |
| ADR-012 | Proposed | Managed Postgres (Neon/RDS) for failover + CI branching | DBA-004 |
| ADR-013 | Proposed | Unified LLM provider abstraction before G3 | AIA-005 |

**ADR process:** deviations require a written superseding ADR, approved, and reflected here.

---

## 17. Glossary

| Term | Definition |
|---|---|
| SoR | System of Record — authoritative PostgreSQL store |
| Derived store | Qdrant/Redis/tsvector — rebuildable projections |
| Book | Content collection with registry row, versions, config |
| Version | SemVer edition of a book (one published at a time) |
| Revision | Immutable snapshot of a unit's text at a version |
| Unit | Node in the book tree (part/chapter/section/...) |
| Chunk | Deterministic segment of canonical text |
| Citation | SoR record tying an answer to a published chunk |
| RRF | Reciprocal Rank Fusion |
| MCP | Model Context Protocol |
| PITR | Point-In-Time Recovery (WAL) |
| RPO/RTO | Recovery Point/Time Objective |
| RAG | Retrieval-Augmented Generation |
| `content_unit` | Table row — node in the book tree (`part/chapter/section/...`) |
| `chapter_id` | API shorthand — a `content_unit` whose `kind = chapter` |
| `RAG_MAX_CONTEXT_CHUNKS` | Config key for RAG context window (see `rag-search-architecture.md` §4.4) |

---

## 18. Status

**Documentation phase complete.** All architecture work is saved to `docs/architecture/`. No production code written. Implementation awaits approval, starting at Gate G0 (`phase-0-implementation-checklist.md`).
