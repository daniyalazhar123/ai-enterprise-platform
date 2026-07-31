# Multi-Book Architecture — Enterprise Specification

> **Document ID:** AEP-MBA-003
> **Version:** 1.0
> **Status:** Approved for design. Awaiting implementation approval.
> **Owner:** Principal Enterprise Software Architect
> **Classification:** Internal — Enterprise Architecture Specification

---

## 1. Purpose

Define the architecture by which the platform operates **any number of books** on a single codebase, a single System of Record, and a single set of AI services. The core design decision: **a book is data, not code.**

## 2. Core Design Principle

> Adding a book must never require a change under `apps/` or `packages/`.

A new book = content files + one registry row + an indexing job. Nothing else.

## 3. Book Content Layout

```
content/books/
├─ cybersecurity/
│  ├─ book.yaml            # registry config (slug, title, routing, citation_mode)
│  └─ chapters/
│     ├─ 01-introduction.md
│     ├─ 02-threat-modeling.md
│     └─ 03-security-architecture.md
├─ banking-finance/        # same layout, same pipeline
│  ├─ book.yaml
│  └─ chapters/
├─ robotics/               # ditto
└─ ... (every future book)
```

### 3.1 book.yaml (authoritative input)

```
slug: cybersecurity
title: Enterprise Cybersecurity
status: active
default_locale: en
model_routing:
  primary: gpt-4o
  fallback: gemini-2.5-pro
  temperature: 0.3
  max_tokens: 4096
  citation_mode: standard
features:
  chat: true
  tutor: true
  quiz: true
  interview: true
  mcp: true
config:
  top_k: 8
  rerank: true
  glossary_refs: [...]
```

`book.yaml` is canonicalized and loaded into the `book` registry row in PostgreSQL. The SoR is authoritative at runtime; `book.yaml` is the authoring input.

## 4. Book Registry (SoR)

Every book has exactly one registry row (`books` table). The registry is the **single source of truth** for:

- Identity and routing (slug, model config, citation mode).
- Feature enablement flags.
- Lifecycle status (draft / active / deprecated / archived).
- RBAC scope naming (`book:{slug}:read`).

See `enterprise-system-of-record.md` §3 for the full entity spec.

## 5. Runtime Resolution

```
request (book=cybersecurity, v=2.1.0)
   │
   ├─ resolve book_id via book registry (slug unique)
   ├─ resolve version_id via book_versions (semver)
   ├─ load model_routing + citation_mode from book.config
   ├─ enforce RBAC scope book:{slug}:*
   └─ route to shared agent service (prompts/top_k per config)
```

**No request is ever book-agnostic.** Every API/MCP/search call is scoped to a book, and the scope is derived from the registry, not from code paths.

## 6. Feature Matrix (applies to every book)

| Feature | Driven by | Per-book override |
|---|---|---|
| AI Chat | `features.chat` | prompts, temperature |
| AI Tutor | `features.tutor` | difficulty ladder |
| Quiz engine | `features.quiz` | question templates |
| Interview | `features.interview` | role ladders |
| MCP tools | `features.mcp` | citation strictness |
| Search | always | top_k, rerank on/off |
| Docusaurus site | always | book.yaml + tree |

Each feature reads configuration from `book.config`/`book.model_routing` at request time. The agent code itself is shared.

## 7. Multi-Book Data Isolation

### 7.1 Logical isolation via foreign keys
Every content/search/citation row carries `book_id`. All queries are filtered by `book_id` (+ `version_id` when pinned). There is **no cross-book access** without explicit RBAC.

### 7.2 Physical isolation (scale path)
| Concern | Strategy |
|---|---|
| Tables | Shared tables, `book_id` column + indexes (v1) |
| Partitions | Optional LIST-partition by book when a single book exceeds warm-tier size |
| Qdrant | One collection per (book, model), filter-scoped; collections are derived |
| Caches | Redis keys namespaced `book:{slug}:*` |
| Docusaurus sites | Built per book from the SoR tree |

Physical isolation is a **tuning decision**, never a correctness one — logical `book_id` isolation is always correct.

## 8. Versioned Content per Book

Each book independently maintains its version line:

```
book: cybersecurity            book: banking-finance
  v1.0.0 (published)             v1.2.0 (published)
  v1.1.0 (published)             v2.0.0 (draft)
  v2.0.0 (draft)
```

- One published version per book at a time (enforced).
- Citations are pinned to `(book_id, version_id, revision_id)` — v1 answers never silently float to v2.
- RAG/MCP accept an explicit `version_id` to query exactly that edition.

## 9. Onboarding a New Book (Runbook)

1. Author `content/books/{slug}/book.yaml` + chapter files.
2. Push → ingest job canonicalizes and creates the registry row (or admin UI does the same).
3. Run a book-scoped `embedding_job` to populate derived vectors.
4. Verify: search, chat, citations, Docusaurus site, RBAC scoping all work with no code changes.
5. Set `status: active`.

**Acceptance:** a second/third book requires **zero** changes under `apps/` or `packages/`.

## 10. Per-Book Config Governing AI Behavior

| Config | Purpose | Default |
|---|---|---|
| `model_routing.primary/fallback` | Model selection + failover | primary/fallback per book |
| `model_routing.temperature` | Creativity control | 0.3 |
| `model_routing.max_tokens` | Output cap | 4096 |
| `model_routing.citation_mode` | Grounding strictness | standard |
| `config.top_k` | Retrieval breadth | 8 |
| `config.rerank` | Enable Cohere rerank | true |
| `features.*` | Feature enablement | all true |

All values live in the SoR (`book` registry) and are hot-read via Redis cache (invalidated on update).

## 11. Diagrams

### 11.1 Book → Content → Service mapping

```
book registry (books) ──┬── content_versions (per book)
                        ├── content_units (per book tree)
                        ├── content_revisions (per unit-version)
                        ├── content_chunks (per revision)
                        ├── citations (per (book, version, revision))
                        └── scopes for RBAC (book:{slug}:*)

shared services ── one copy, parameterized by book_id/config
```

### 11.2 Two books, one platform

```
            ┌─────────────────────────────────────────────┐
            │              SHARED SERVICES                │
            │  content | search | ai | jobs | gateway     │
            └──────┬──────────────────────┬───────────────┘
                   │ book_id=cybersecurity │ book_id=banking-finance
                   ▼                       ▼
            ┌─────────────┐         ┌─────────────┐
            │ v1.1.0 pub   │         │ v1.2.0 pub   │
            │ v2.0.0 draft │         │ v2.0.0 draft │
            └─────────────┘         └─────────────┘
                 │                        │
                 └───── SoR (shared tables, book_id-scoped) ────┘
```

## 12. Constraints & Acceptance Checks

| Constraint | Acceptance check |
|---|---|
| Zero code per book | Add second book with zero `apps/`/`packages/` changes |
| Version isolation | v1 answer cites v1; v2 publish changes nothing retroactively |
| RBAC scoping | Users without `book:{slug}:read` cannot retrieve that book's content |
| Feature parity | Every feature works for every enabled book automatically |
| Derived-store scoping | Qdrant/Redis keys always namespaced by book |
