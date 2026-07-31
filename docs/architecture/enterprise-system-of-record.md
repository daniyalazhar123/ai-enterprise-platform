# Enterprise System of Record — Complete Specification

> **Document ID:** AEP-SOR-002
> **Version:** 1.0
> **Status:** Approved for design. Awaiting implementation approval.
> **Owner:** Principal Enterprise Software Architect
> **Classification:** Internal — Enterprise Architecture Specification

---

## 1. Charter

The System of Record (SoR) is the authoritative, transactional core of the platform. Every durable fact — which books exist, what each published edition says, who authored and approved it, what citations ground an answer, who asked what, when — lives in PostgreSQL. Every other store (Qdrant, Redis, tsvector) is a **projection, cache, or queue** and is reconstructible from the SoR.

> **SoR axiom:** If it isn't in PostgreSQL, it isn't real. If it's lost anywhere else, rebuild from PostgreSQL.

## 2. High-Level Diagram

```
                        ┌───────────────────────────────┐
                        │      ENTERPRISE SoR CORE      │
                        │       PostgreSQL (16+)        │
                        │  Book Registry   (books)      │
                        │  Versioning      (versions)   │
                        │  Publishing      (workflow)   │
                        │  Revisions       (immutable)  │
                        │  Structure       (units/chaps)│
                        │  Chunks + Hashes (content)    │
                        │  Change Detection (deltas)    │
                        │  Citations       (grounding)  │
                        │  Conversations   (messages)   │
                        │  Audit/Workflow  (events)     │
                        │  Jobs            (indexing)   │
                        │  Backup/Retention (lifecycle) │
                        └──────────────┬────────────────┘
                                       │  (authoritative reads/writes)
             ┌─────────────────────────┼─────────────────────────┐
             ▼                         ▼                         ▼
   ┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
   │  Qdrant         │       │  Redis          │       │  tsvector (FTS) │
   │  DERIVED        │       │  CACHE + QUEUE  │       │  DERIVED (pg)   │
   │  vector index   │       │  (never SoR)    │       │  lexical index  │
   └─────────────────┘       └─────────────────┘       └─────────────────┘
         │                          │                          │
         └────────── ALL REBUILDABLE FROM THE SoR ────────────┘
```

**Reading principle for AI:** every AI agent queries the SoR first (content, citations, version, permissions). Derived stores are acceleration only. If Qdrant disagrees with the SoR, the SoR wins.

## 3. Book Registry

### 3.1 Entity

```
book
├─ id            (uuid7)
├─ slug          (unique, url-safe: "cybersecurity")
├─ title         (display: "Enterprise Cybersecurity")
├─ description
├─ status        (draft | active | deprecated | archived)
├─ default_locale
├─ model_routing (JSONB: primary, fallback, temperature, max_tokens, citation_mode)
├─ features      (JSONB: chat, tutor, quiz, interview, mcp flags)
├─ config        (JSONB: prompt overrides, top_k, difficulty ladders, glossary refs)
├─ created_at / updated_at
└─ audit trail   (book.* events)
```

### 3.2 Invariants
1. `slug` is unique → every route, vector filter, and permission derives from it.
2. A book must exist before content, versions, or permissions reference it (FK enforcement).
3. Registry mutations are low-frequency and audited; reads cached in Redis, invalidated on change.

### 3.3 Responsibilities
- Onboarding a new book = `INSERT book` + ingest content + run index job.
- Provides the scope key for RBAC (`book:{slug}:read`) and for all derived-index filters.

## 4. Versioning

### 4.1 Entity

```
book_version
├─ id
├─ book_id           (FK)
├─ semver            (major.minor.patch[+prerelease]) — unique per book
├─ codename          (optional)
├─ status            (draft | published | superseded | archived)
├─ release_notes     (text)
├─ published_at / created_at
└─ metadata          (JSONB: contributors, license, revisions)
```

### 4.2 Rules
1. **SemVer, per book.** Breaking restructure = major; additive chapters = minor; corrections = patch.
2. **One published version per book at a time**, plus unlimited drafts/archived.
3. **Version is the anchor of truth.** Every `content_revision` and `citation` carries `version_id`. Old answers keep citing old editions (non-negotiable for Banking/Law/Healthcare).
4. **Version-aware retrieval:** RAG and MCP accept `version_id` to query exactly that edition.

## 5. Publishing Workflow

### 5.1 State machine

```
                 ┌─────────┐
      create     │ DRAFT   │◄────────────── amend (new revision)
      ─────────► └────┬────┘
                      │ submit (author)
                      ▼
                 ┌────────────┐
                 │ IN REVIEW  │◄────────── reject → back to DRAFT
                 └────┬───────┘
                      │ approve (reviewer)
                      ▼
                 ┌────────────┐
                 │ APPROVED   │
                 └────┬───────┘
                      │ publish (publisher)   → transactional
                      ▼
                 ┌────────────┐     supersede (next version)
                 │ PUBLISHED  │──────────────────────────────► ARCHIVED
                 └────┬───────┘
                      │ deprecate
                      ▼
                   ARCHIVED
```

### 5.2 Transition permissions (RBAC resources)

| Transition | Required permission |
|---|---|
| create/submit | `content:write` (scoped `book:{slug}:write`) |
| review/reject/approve | `content:review` |
| publish | `content:publish` |
| amend | `content:write` (creates new revision, never edits) |
| deprecate/archive | `content:manage` |

### 5.3 Publish semantics (transactional)

1. Begin transaction.
2. Mark revision `published`; record `published_at`.
3. Advance/close target `book_version.status → published`.
4. Write workflow + audit events.
5. Commit.
6. **After commit:** enqueue `embedding_job` for affected units → derived index updates asynchronously.

**Index lag is designed-in and safe:** clients querying by published-version filter never see partial index state; the SoR is correct the moment the transaction commits.

## 6. Revisions (Immutability)

### 6.1 Entity

```
content_revision
├─ id
├─ unit_id        (FK → content_unit)
├─ version_id     (FK → book_version)
├─ rev_no         (1,2,3… per unit-version)
├─ author_id / reviewer_id / publisher_id
├─ status         (draft|in_review|approved|published|archived)
├─ content_hash   (sha256 of canonical content) — UNIQUE per (unit_id, hash)
├─ source_format  (markdown | mdx | plaintext | pdf-extracted)
├─ body           (text) — the authoritative text
├─ title / subtitle
├─ language_code
├─ metadata       (JSONB)
└─ created_at / updated_at / published_at
```

### 6.2 Immutability rules
1. **Append-only.** Editing = creating `rev_no+1`. Existing rows never mutate.
2. **`content_hash` dedupe:** identical text → identical hash → no-op edits detected, reindex skipped.
3. **Copy-on-write:** only the changed unit forks; unchanged units keep their revision + chunk rows.
4. **Deletion is prohibited** for published revisions; only `archived` status.

## 7. Chapters & Sections (Content Structure)

### 7.1 Entity

```
content_unit                     content_unit
├─ id                            ├─ id
├─ book_id   (FK)                ├─ parent_id  (FK, self)   → hierarchy
├─ kind      (part|chapter|       ├─ kind
│            section|subsection|  ├─ path      (tree path, e.g. /03/03-2)
│            exercise|glossary|   ├─ slug      (unique per book)
│            appendix)            ├─ order     (sort within parent)
└─ ...                           └─ title
```

### 7.2 Invariants
1. **Single tree per book** (`parent_id` + `path` + `order`), enforced by FK + path uniqueness.
2. Chapters/sections are **containers**; a `content_revision` belongs to a unit and represents its text at a version.
3. Tree is stable across revisions; revisions change *text*, the tree changes *shape* — both versioned, both in the SoR.
4. URL/slug mapping (`/b/{book}/v/{semver}/docs/{path}`) is derived from the tree, so Docusaurus and the API share one structure.

## 8. Metadata Model

Metadata is **structured data in the SoR**, not buried in vector payloads:

| Class | Where it lives | Example |
|---|---|---|
| Structural | `content_unit`, `book_version` | order, path, kind, semver |
| Content | `content_revision` | title, language, source_format, license |
| Provenance | `content_revision` | author, reviewer, timestamps, content_hash |
| Indexing | `content_chunk` | chunk_hash, token_count, model_used |
| Derivation | Qdrant payload (mirror) | book_id, version_id, unit_id, chunk_id, revision_id |
| Runtime | `book.config` | model routing, citation_mode, top_k |
| Observability | audit + job tables | who/when/what changed, job status |

**Golden rule:** vector payload metadata is a **denormalized mirror** for filter speed; the authoritative copy is always a SoR column/row. Payloads are rewritten on reindex, never hand-edited.

## 9. Content Hashing

### 9.1 Purpose
Make the pipeline deterministic and change detection trivial.

### 9.2 Hash hierarchy

```
source file (raw bytes) ──canonicalize──▶ canonical text (normalized)
    │
    ▼
content_hash = sha256(canonical_text)         [revision-level]
    │
    ▼
chunk i: chunk_hash_i = sha256(canonical_chunk_i)   [chunk-level]
    │
    ▼
point_id = content_chunk.id  (stable, hash-derived)  [Qdrant point]
```

### 9.3 Canonicalization rules (must be reproducible)
- Fixed line endings (LF), fixed encoding (UTF-8), strip BOM, normalize whitespace per chunker, consistent heading markers.
- Canonicalization version recorded; if the rule set changes, hashes change deliberately → **full reindex** (versioned as `canonicalizer_version`).

### 9.4 Guarantees
- Same source + same pipeline version → **identical hashes, chunks, embeddings, and point IDs**.
- Enables idempotent upserts, no-op detection, and verifiable rebuilds.

## 10. Change Detection

### 10.1 Triggers
- **Push:** authoring pipeline (ingest job, git webhook, admin upload) computes hashes and compares against latest revision.
- **Poll:** scheduled integrity job rescans source content for `content_hash` drift.

### 10.2 Comparison logic (pure)

```
for each unit:
    new_hash = sha256(canonical(source))
    latest   = latest published revision for (unit, version)
    if new_hash == latest.content_hash:
        → UNCHANGED   (skip; keep chunks/citations intact)
    elif a draft/approved revision with same hash exists:
        → NOOP_NEW    (reuse existing revision — dedupe)
    else:
        → CHANGED     (create rev_no+1, enqueue reindex of unit only)
```

### 10.3 Change-scoped indexing
Only changed units enqueue jobs → incremental, cheap, auditable (`change_delta` per job). Unchanged chunks are never re-embedded.

## 11. Background Indexing

### 11.1 Entity

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

### 11.2 Execution pipeline (worker)

```
┌──────────────┐   ┌───────────────────────┐   ┌────────────────┐
│ Job queue    │   │ Worker (arq/celery)   │   │ Derived stores │
│ (Redis list) │──▶│ 1. load units (SoR)   │──▶│ Qdrant (upsert)│
│              │   │ 2. canonicalize+chunk │   │ tsvector (SoR) │
│              │   │ 3. embed (Cohere)     │   │ cache (Redis)  │
│              │   │ 4. record vectors? no │   └────────────────┘
│              │   └────────┬──────────────┘        ▲
└──────────────┘            │ idempotent replay     │
                            └── point_id = chunk_id (stable) ──┘
```

### 11.3 Idempotency & retry
- Upsert, never insert; point IDs are stable chunk IDs.
- Failure: `failed` + `error`; retry with backoff (`attempt++`, max 5); poisoned jobs escalate to alert.
- **Rebuild on demand:** `reindex_all` job per (book, model) — delete collection filter + replay from SoR.

### 11.4 Verification (drift check)
Scheduled reconciliation compares Qdrant point set vs. `content_chunk` rows per (book, version, model): missing/stale points re-upserted; orphans deleted. Report to audit + metrics.

## 12. Citation Engine

### 12.1 Purpose
Every grounded answer is traceable to a specific published text anchor — the SoR's trust product.

### 12.2 Entity

```
citation
├─ id
├─ book_id / version_id / unit_id / revision_id / chunk_id  (all FK)
├─ source_text      (the exact snippet cited)
├─ anchor           (unit path + chunk index + optional char range)
├─ answer_hash      (sha256 of question+answer)  → link citation to a turn
├─ confidence / score
├─ created_at
└─ conversation_id (nullable — the turn that produced it)
```

### 12.3 Lifetime
- Citations are **created at answer time, stored forever**, tied to the `revision_id` true at that moment.
- If v2 publishes, historical answers keep citing v1 → **version-stable truth**.
- Citations are queryable and exportable (API, MCP, PDF/report).

### 12.4 Grounding policy (per-book `book.config.citation_mode`)

| Mode | Rule |
|---|---|
| `strict` (Law/Banking/Healthcare) | answer rejected/flagged unless ≥ N citations from active book |
| `standard` (technical books) | citations required; low-score spans flagged |
| `lax` | citations best-effort, marked "unverified" |

## 13. Hybrid Search (SoR-first)

### 13.1 Pipeline

```
Query
 ├─1. Book context resolution  (book_id + optional version_id from request/RBAC)
 ├─2. Query rewrite (LLM, cached; template per book)
 ├─3a. Semantic: Qdrant (derived) — filter [book_id, version_id?, unit_id?]
 ├─3b. Lexical:  PostgreSQL tsvector (SoR) — GIN over content_chunk.text
 ├─4. RRF fusion (k=60) + score normalization
 ├─5. Re-rank: Cohere re-ranker (cache in Redis per query-hash)
 ├─6. Citation assembly: map top results → content_chunk rows → citation records
 └─7. Return grounded, cited, book-scoped results
```

### 13.2 Why lexical runs on the SoR
- Never depends on the derived store.
- Boosts recall for domain terms with ranking math PostgreSQL already provides.
- Answers exact-phrase queries the vector index misses.

### 13.3 Failure semantics
- Qdrant down → semantic leg fails soft (flag), lexical still answers; hybrid stays functional.
- Qdrant rebuilt → identical results after reindex because points derive from the SoR.

## 14. Recovery Strategy

| Failure | Recovery | RTO/RPO target |
|---|---|---|
| Qdrant collection corrupt | `reindex_all(book, model)` from SoR | minutes (auto) |
| Redis flushed | cold cache + queue rebuild; no data loss | immediate |
| tsvector index rebuild | `REINDEX` from SoR | minutes |
| Single transaction failure | rollback; job retry | immediate |
| Postgres instance loss | PITR + replication failover | RPO ≤ 5 min, RTO ≤ 15 min |
| Region loss | replicated region + restore from backup | RPO ≤ 15 min, RTO ≤ 1 h |

**Rebuild playbooks**
- **Vector rebuild:** delete collection filter by (book, model) → enqueue `reindex_all` → verify via reconciliation → warm cache.
- **Chunk rebuild:** re-canonicalize from `content_revision.body` (never from Qdrant) → regenerate `content_chunk` rows (deterministic) → reindex.
- **Citation rebuild:** citations are SoR rows — they survive everything; no rebuild.

## 15. Disaster Recovery

### 15.1 Pillars
1. **PostgreSQL first:** continuous WAL archiving + full backups to cold storage; managed offering with automated failover.
2. **Restore-to-any-point:** PITR window ≥ 30 days (compliance-dependent).
3. **Replication:** primary + async read replica (different AZ); promote on failure.
4. **Derived-store DR is a rebuild, not a restore:** Qdrant/Redis carry no DR burden because the SoR is authoritative.

### 15.2 Runbook (abbreviated)
1. Promote standby (or restore backup + PITR).
2. Validate integrity (row counts, FK checks, `content_hash` spot-check vs source).
3. Restore secrets from secret store (never disk).
4. Replay `embedding_job`s left `pending/running`.
5. Trigger `reindex_all` + reconciliation verification.
6. Cut traffic via DNS/ingress; verify health + sample citation lookups.

### 15.3 DR testing
Quarterly restore drill to staging + reconciliation + golden citation-query set; measure RTO/RPO; report.

## 16. Data Lifecycle

### 16.1 Retention tiers

| Tier | Data | Retention |
|---|---|---|
| Hot | published content, chunks, citations, active versions | indefinite (SoR) |
| Warm | conversations (post-export), in_review/approved revisions | 90 days – 2 years |
| Cold/Archived | archived revisions, old versions | 7 years (compliance) |
| Expunge | deleted users' PII per policy | on deletion (GDPR-style) |

### 16.2 Stages

```
create ─▶ active ─▶ archived ─▶ (retention expiry) ─▶ expunge/anonymize
                              │
                              └── backup/export snapshot before expiry
```

- **Archival:** rows move to archived partitions/cold schema; vector points for archived revisions removed after grace period.
- **Expungement:** hard-delete or anonymize per policy; citations to expunged content are **redacted, not deleted** (audit integrity).
- **Tombstones:** deleted books/units leave tombstone rows so citations remain resolvable.

### 16.3 Partitioning for scale
`content_revision`, `content_chunk`, `citations`, `audit_logs` partition by RANGE (`created_at`) or LIST (book) with monthly/quarterly rollover.

## 17. Backup Strategy

### 17.1 What is backed up

| Component | Method | Frequency | Restore target |
|---|---|---|---|
| PostgreSQL | Full + WAL/PITR | daily full, continuous WAL | any point in time |
| Qdrant | Snapshots (optional, convenience) | nightly | bypass rebuild; rebuild still available |
| Redis | None required (cache) | — | rebuilt |
| Secrets | Vault/KMS | managed | — |
| Source content | Git + object storage | on commit | source-of-truth input |

### 17.2 Rules
1. **Backup the SoR; never trust derived-store backups as a data source.** Qdrant snapshots shorten RTO but are validated against the SoR.
2. **Verification:** monthly restore drill to staging + reconciliation report.
3. **Retention:** daily × 30, weekly × 12, monthly × 7, annual × 7 (align with compliance).
4. **Encryption at rest and in transit** for all backups.

### 17.3 Topology

```
 Postgres ──▶ WAL archive ──▶ cold storage (encrypted, versioned, geo-redundant)
     │            │
     ├── daily full backup ──▶ cold storage
     └── read replica ──▶ (async, different AZ) ──▶ failover promotion

 Qdrant ──▶ nightly snapshot ──▶ object storage (validated, optional)
 content ──▶ git history + object storage mirror
 secrets ──▶ Vault/KMS (encrypted, versioned)
```

## 18. SoR ↔ Derived-Store Consistency Contract

| Operation | SoR (authoritative) | Qdrant (derived) | Redis (cache/queue) |
|---|---|---|---|
| Publish revision | commit row + version state | job enqueued | invalidate related caches |
| Reindex unit | update job stats | upsert points | clear query cache |
| Delete unit | tombstone + archive | delete points (async) | invalidate |
| Answer a question | store message + citations | — | cache re-ranker |
| Rebuild index | unchanged | replay from SoR | warm |

**Invariant:** no operation ever writes Qdrant or Redis without first committing to PostgreSQL.

## 19. Consolidated Entity Map

```
books ─┬─ book_versions ──────┬─ content_units ── content_revisions ── content_chunks
       │                      │        │                 │                 │
       ├─ book_config         │        ▼                 ▼                 ▼
       │                      │   (tree, FK self)    content_hash      chunk_hash
       ├─ permissions (RBAC)  │                                        + point_id
       │                      └───────────────┬────────────────────────┘
       └─ audit_logs / workflow_events        ▼
                                       citations (grounding)
users ── sessions ── refresh_tokens ── roles ── permissions
                                          └── user_roles / role_permissions
conversations ── messages ── (referenced by) citations
embedding_jobs ── (scope → books/versions/units)
user_settings / bookmarks / learning_progress / quiz_results (feature SoR)
```

## 20. Acceptance Checks

| Constraint | Acceptance check |
|---|---|
| Postgres only SoR | Kill Qdrant+Redis in staging; platform still serves grounded content (degraded, correct) |
| Reproducibility | Reindex twice → byte-identical chunks and point IDs; reconciliation diff = 0 |
| Multi-book | Add second book = content + registry row; zero changes in `apps/` or `packages/` |
| Version truth | Answer citing v1 remains verifiable after v2 publishes |
| Grounding | Every answer in `strict` mode carries ≥ N resolvable citations |
| Recovery | Restore drill completes within RTO/RPO targets |
