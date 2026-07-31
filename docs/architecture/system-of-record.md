# System of Record — Design Specification

> **Document ID:** AEP-SOR-M
> **Version:** 1.0
> **Status:** Approved for design. Awaiting implementation approval.
> **Owner:** Principal Enterprise Software Architect
> **Classification:** Internal — Enterprise Architecture Specification
> **Companion:** `enterprise-system-of-record.md` (lifecycle: recovery, DR, backup)

---

## 1. Purpose

Define the System of Record (SoR) for the AI Enterprise Book Platform: PostgreSQL as the single source of truth for all content, plus the complete content pipeline from book registry to hybrid search. This document is the **implementation-focused design**; lifecycle concerns (DR, backups, retention) are in `enterprise-system-of-record.md`.

## 2. Database as Source of Truth

### 2.1 Axiom

> **SoR axiom:** If it isn't in PostgreSQL, it isn't real. If it's lost anywhere else, rebuild from PostgreSQL.

### 2.2 Ownership

| Store | Owns | Role |
|---|---|---|
| PostgreSQL | books, versions, revisions, units, chunks, citations, conversations, users, RBAC, audit, jobs | **authoritative** |
| Qdrant | vectors (point_id = `content_chunk.id`) | derived, rebuildable |
| Redis | caches, queues, rate-limit | cache/queue, flush-safe |
| tsvector (in PG) | lexical index over `content_chunk.text` | derived inside SoR |

### 2.3 Write discipline

1. Commit to PostgreSQL first (transaction).
2. Enqueue/emit derived-store work after commit (job or event).
3. No operation ever writes Qdrant or Redis without a preceding SoR commit.
4. On disagreement, the SoR wins; reconciliation re-derives the projection.

## 3. Book Hierarchy

```
book (registry row)
└── book_version (SemVer edition)
    └── content_unit (tree node: part/chapter/section/subsection/exercise/glossary/appendix)
        └── content_revision (immutable text snapshot at a version)
            └── content_chunk (deterministic segment of canonical text)
                └── citation (answer → published chunk anchor)
```

- **Single tree per book** (`content_units.parent_id` + `path` + `order`, FK self).
- Units are containers; revisions change *text*, the tree changes *shape* — both versioned.
- Every content row carries `book_id` (+ `version_id` where edition-specific) for scoping and filters.

## 4. Versioning

- **SemVer per book**, unique `(book_id, semver)`.
- One `published` version per book at a time (partial unique index); drafts/archived unlimited.
- Version is the **anchor of truth**: all revisions, chunks, and citations pin `version_id`.
- RAG/MCP accept `version_id` to query exactly that edition.

```
book: cybersecurity            book: banking-finance
  v1.0.0 (published)             v1.2.0 (published)
  v1.1.0 (published)             v2.0.0 (draft)
  v2.0.0 (draft)
```

## 5. Chunking

### 5.1 Chain

```
source (markdown/mdx/pdf) ──canonicalize──▶ canonical text
   ──chunk──▶ chunks (heading-aware, token-capped)
   ──hash──▶ chunk_hash = sha256(canonical_chunk)
   ──persist──▶ content_chunks (SoR) with chunk_index, token_count
   ──embed──▶ vectors → Qdrant (point_id = content_chunk.id)
```

### 5.2 Rules
- Heading-aware: never split across `##`/`###` boundaries.
- Token cap ~512, overlap window for recall; `chunk_index` stable from canonical ordering.
- `chunk_hash` records `canonicalizer_version`, `chunker_version`, `embedding_model` for provenance.
- Identical text → identical chunks → **no-op edits skip reindexing** (hash dedupe).

## 6. Embeddings

- Embedding is a **pure function** of `(text, model, version)` → deterministic vectors.
- Same content + same pipeline version → identical vectors and point IDs.
- Unchanged chunks are **never re-embedded** (hash dedupe) — this is the primary cost control.
- Model choice per book config (`model_routing`); vector dimension recorded in the collection config.

## 7. Background Indexing

### 7.1 Job model

```
embedding_job
├─ id
├─ scope     (book | version | unit | chunk-range | reindex_all)
├─ book_id / version_id / unit_id
├─ chunker_version / canonicalizer_version / embedding_model
├─ status    (pending | running | completed | failed | retried | cancelled)
├─ attempt / max_attempts
├─ started_at / finished_at / heartbeat_at
├─ error     (text)
└─ stats     (JSONB: processed, skipped, failed, elapsed)
```

### 7.2 Worker loop

```
publish/change → enqueue embedding_job(scope)
  → worker: load units from SoR → canonicalize → chunk → hash
  → upsert content_chunks (SoR) → embed → upsert Qdrant points
  → update job stats → reconciliation check → invalidate caches
```

- **Upsert, never insert** (point_id = stable chunk ID) → idempotent replay.
- Retry with backoff (max 5), poisoned jobs escalate to alert.
- `reindex_all(book, model)` = delete collection filter + replay from SoR.
- **Verification (drift check):** scheduled reconciliation compares Qdrant points vs `content_chunk` rows; missing/stale re-upserted, orphans deleted.

## 8. Hybrid Search

### 8.1 Pipeline

```
Query
 ├─1. Book context resolution  (book_id + optional version_id)
 ├─2. Query rewrite (LLM, cached; template per book)
 ├─3a. Semantic: Qdrant (derived) — filter [book_id, version_id?, unit_id?]
 ├─3b. Lexical:  PostgreSQL tsvector (SoR) — GIN over content_chunk.text
 ├─4. RRF fusion (k=60) + score normalization
 ├─5. Re-rank: Cohere re-ranker (cache in Redis per query-hash)
 ├─6. Citation assembly: top results → content_chunk rows → citations
 └─7. Return grounded, cited, book-scoped results
```

### 8.2 Why lexical runs on the SoR
- Never depends on the derived store.
- Boosts recall for domain terms (acronyms, codes) and exact-phrase queries.
- Keeps search functional when Qdrant is down (fail-soft).

### 8.3 Failure semantics

| Failure | Behavior |
|---|---|
| Qdrant down | semantic leg skipped (flagged) → lexical-only answers |
| Rerank down | RRF-only ordering |
| Both down | lexical-only, RRF-only — still answers |

## 9. Citation Engine

- Citation rows pin: `(book_id, version_id, unit_id, revision_id, chunk_id, source_text, anchor, answer_hash, confidence)`.
- Created at answer time, stored forever, **version-pinned** — republishing never rewrites history.
- `citation_mode` per book: `strict` (min N citations), `standard` (flag low-score), `lax` (best-effort "unverified").
- Queryable/exportable via REST + MCP.

## 10. Book Registry

```
book
├─ id            (uuid7)
├─ slug          (unique, url-safe)
├─ title / description
├─ status        (draft | active | deprecated | archived)
├─ default_locale
├─ model_routing (JSONB: primary, fallback, temperature, max_tokens, citation_mode)
├─ features      (JSONB: chat, tutor, quiz, interview, mcp, developer flags)
├─ config        (JSONB: top_k, rerank, difficulty ladders, glossary refs)
├─ created_at / updated_at
└─ audit trail   (book.* events)
```

- Onboarding a new book = `INSERT book` + ingest content + run index job.
- Provides the scope key for RBAC (`book:{slug}:{action}`) and all derived-index filters.

## 11. Content Pipeline

```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  INGEST      │──▶│  CANONICALIZE │──▶│  CHUNK + HASH│──▶│  PERSIST     │
│ book.yaml +  │   │ normalizer    │   │ heading-aware│   │ content_units│
│ chapter files│   │ (versioned)   │   │ sha256       │   │ content_rev  │
└──────────────┘   └──────────────┘   └──────────────┘   │ content_chunk│
                                                        └──────┬───────┘
                                                               ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  SERVE       │◀──│  CITE        │◀──│  SEARCH      │◀──│  EMBED       │
│ agents/MCP   │   │ answer→chunk │   │ hybrid (RRF) │   │ Cohere →     │
│ citations    │   │ version-pin  │   │ + rerank     │   │ Qdrant upsert│
└──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘
```

### 11.1 Trigger paths
- **Push:** authoring pipeline (ingest job, git webhook, admin upload) computes hashes, compares to latest revision.
- **Poll:** scheduled integrity job rescans source for `content_hash` drift.

### 11.2 Change detection (pure)

```
for each unit:
    new_hash = sha256(canonical(source))
    latest   = latest published revision for (unit, version)
    if new_hash == latest.content_hash:   → UNCHANGED (skip)
    elif revision with same hash exists:  → NOOP_NEW (dedupe/reuse)
    else:                                 → CHANGED (rev_no+1, reindex unit only)
```

## 12. Acceptance Checks

| Check | Pass criteria |
|---|---|
| Postgres only SoR | Kill Qdrant+Redis in staging → still serves grounded content |
| Reproducibility | Reindex twice → byte-identical chunks + point IDs; diff = 0 |
| Multi-book | Add second book → zero code changes |
| Version truth | Answer citing v1 verifiable after v2 publishes |
| Grounding | `strict` mode: every answer has ≥ N citations |
| Fail-soft | Qdrant down → lexical-only search answers |
