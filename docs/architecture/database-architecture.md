# Database Architecture — Enterprise Specification

> **Document ID:** AEP-DBA-004
> **Version:** 1.0
> **Status:** Approved for design. Awaiting implementation approval.
> **Owner:** Principal Enterprise Software Architect
> **Classification:** Internal — Enterprise Architecture Specification

---

## 1. Purpose

Define the PostgreSQL database architecture for the platform as the **only System of Record**. This document supersedes the earlier implementation blueprint of the same name and aligns schema with the SoR specification (`enterprise-system-of-record.md`) and multi-book model (`multi-book-architecture.md`).

## 2. Conventions

| Element | Convention | Example |
|---|---|---|
| Tables | `snake_case`, plural | `users`, `content_revisions` |
| Columns | `snake_case`, singular | `display_name`, `published_at` |
| Primary Keys | `id` UUIDv7 | `id` |
| Foreign Keys | `{referenced_table}_id` | `unit_id`, `version_id` |
| Join Tables | `{table_a}_{table_b}` | `user_roles`, `role_permissions` |
| Indexes | `idx_{table}_{column}` | `idx_content_revisions_unit_id` |
| Unique Constraints | `uq_{table}_{column}` | `uq_books_slug` |
| Check Constraints | `ck_{table}_{column}_{rule}` | `ck_content_units_kind` |
| Timestamps | `TIMESTAMPTZ`, UTC | `created_at` |

**ID policy:** UUIDv7 (time-ordered) for all PKs. **No sequences** except where a human-visible ordinal is needed (e.g., `rev_no`).

## 3. Logical Schema (Core SoR)

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

## 4. Domain Tables

### 4.1 `books` — Book Registry

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | uuid7 |
| slug | text UNIQUE NOT NULL | `cybersecurity` |
| title | text NOT NULL | display name |
| description | text | |
| status | enum | draft/active/deprecated/archived |
| default_locale | text | `en` |
| model_routing | JSONB | primary/fallback/temperature/max_tokens/citation_mode |
| features | JSONB | chat/tutor/quiz/interview/mcp |
| config | JSONB | top_k, rerank, glossary refs |
| created_at / updated_at | timestamptz | |

### 4.2 `book_versions`

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| book_id | UUID FK → books | ON DELETE RESTRICT |
| semver | text | unique per book `uq_book_versions_book_semver` |
| codename | text nullable | |
| status | enum | draft/published/superseded/archived |
| release_notes | text | |
| metadata | JSONB | contributors, license |
| published_at / created_at | timestamptz | |

**Constraint:** at most one `published` version per book (partial unique index).

### 4.3 `content_units` — the content tree

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| book_id | UUID FK → books | |
| parent_id | UUID FK → content_units, nullable | tree hierarchy |
| kind | enum | part/chapter/section/subsection/exercise/glossary/appendix |
| path | text | tree path `/03/03-2` |
| slug | text | unique per book |
| order | int | sort within parent |
| title | text | |
| created_at / updated_at | timestamptz | |

**Constraints:** single root per book; `uq_content_units_book_slug`; `uq_content_units_book_path`.

### 4.4 `content_revisions` — immutable revisions

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| unit_id | UUID FK → content_units | |
| version_id | UUID FK → book_versions | |
| rev_no | int | 1,2,3… per (unit, version) |
| author_id / reviewer_id / publisher_id | UUID FK → users, nullable | |
| status | enum | draft/in_review/approved/published/archived |
| content_hash | text NOT NULL | sha256 of canonical content |
| source_format | enum | markdown/mdx/plaintext/pdf-extracted |
| body | text | authoritative text |
| title / subtitle | text | |
| language_code | text | |
| metadata | JSONB | |
| created_at / updated_at / published_at | timestamptz | |

**Constraints:** `uq_content_revisions_unit_hash` unique (unit_id, content_hash); `uq_content_revisions_unit_rev` unique (unit_id, rev_no).

### 4.5 `content_chunks` — deterministic chunks

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | stable, deterministic (hash-derived) |
| revision_id | UUID FK → content_revisions | |
| unit_id / book_id / version_id | UUID FK | denormalized for filter speed |
| chunk_index | int | order within revision |
| chunk_hash | text | sha256 of canonical chunk |
| text | text | chunk content (indexed by GIN tsvector) |
| token_count | int | |
| canonicalizer_version / chunker_version | text | pipeline provenance |
| created_at | timestamptz | |

**Constraint:** `uq_content_chunks_revision_index` unique (revision_id, chunk_index).

### 4.6 `citations`

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| book_id / version_id / unit_id / revision_id / chunk_id | UUID FK | all required |
| source_text | text | exact cited snippet |
| anchor | text | unit path + chunk index + char range |
| answer_hash | text | sha256(question+answer) |
| confidence | float | |
| conversation_id | UUID FK nullable | the producing turn |
| created_at | timestamptz | |

**Constraint:** citations never cascade-delete on content archival (redaction instead).

### 4.7 `embedding_jobs`

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| scope | enum | book/version/unit/chunk-range/reindex_all |
| book_id / version_id / unit_id | UUID FK nullable | |
| chunker_version / canonicalizer_version / embedding_model | text | |
| status | enum | pending/running/completed/failed/retried/cancelled |
| attempt / max_attempts | int | |
| started_at / finished_at / heartbeat_at | timestamptz | |
| error | text | |
| stats | JSONB | processed/skipped/failed/elapsed |

## 5. Identity & RBAC Tables

Existing auth schema (`users`, `sessions`, `refresh_tokens`, `roles`, `permissions`, `user_roles`, `role_permissions`, `audit_logs`) is retained as the identity foundation. Extend with:

- **`book_permissions`** — scope strings `book:{slug}:{action}`.
- **`user_book_roles`** — join of users to book-scoped roles.
- **`permission_scopes`** — validation registry of valid scope patterns.

RBAC behavior is specified in `security-rbac-architecture.md`.

## 6. Conversations & Feature SoR

| Table | Purpose |
|---|---|
| `conversations` | durable chat/interview sessions, `book_id` scoped |
| `messages` | turns (role, content, tool_calls, latency, model) |
| `quiz_results` | quiz submissions and scores |
| `learning_progress` | per-user per-book progress |
| `bookmarks` | user bookmarks |

These move AI state out of Redis-only TTL into the SoR (Phase 3+).

## 7. Indexing Strategy

| Index | Table | Purpose |
|---|---|---|
| `idx_books_slug` (unique) | books | registry lookup |
| `idx_book_versions_book` | book_versions | version list per book |
| `uq_book_versions_book_semver` (unique) | book_versions | semver enforcement |
| `idx_content_units_book_path` (unique) | content_units | tree integrity |
| `idx_content_revisions_unit` | content_revisions | revision list per unit |
| `uq_content_revisions_unit_hash` (unique) | content_revisions | hash dedupe |
| `idx_content_chunks_revision` | content_chunks | chunk list per revision |
| GIN `chunks_tsv` | content_chunks | lexical search (derived tsvector) |
| `idx_citations_answer_hash` | citations | citation→turn lookup |
| `idx_jobs_status` | embedding_jobs | worker polling |
| `idx_audit_created_at` | audit_logs | retention pruning |

## 8. Full-Text Search on the SoR

- `content_chunks.text` carries a generated `tsvector` column (`en` default; per-book language via `book.default_locale`).
- GIN index enables the **lexical leg** of hybrid search without any derived store.
- Query-time use: `websearch_to_tsquery` for user queries; rank via `ts_rank_cd`.

See `rag-search-architecture.md` §for fusion.

## 9. Partitioning & Scale

| Table | Partition key | Rollover |
|---|---|---|
| `content_revisions` | RANGE (created_at) | monthly (hot), archive quarterly |
| `content_chunks` | RANGE (created_at) | monthly |
| `citations` | RANGE (created_at) | quarterly |
| `audit_logs` | RANGE (created_at) | monthly, prune per retention |
| `messages` | RANGE (created_at) | monthly |

Optional LIST partitioning by `book_id` when a single book exceeds warm-tier size. **Partitions are never correctness concerns** — indexes and queries are partition-agnostic.

## 10. Migration Strategy

1. **Alembic is the only DDL authority.** Remove `SQLModel.metadata.create_all` from startup (`db/session.py`); schema is migration-managed.
2. **Repair the migration graph first (Phase 0):** current `0004`–`0009` heads branch inconsistently (conflicting `down_revision`s). Linearize via a squash/base revision so `alembic upgrade head` is deterministic.
3. **Convention:** one migration per schema feature; migrations are additive; destructive changes require a documented two-step (deploy-compatible) migration.
4. **Baseline:** after Phase 0 repair, regenerate a clean baseline migration reflecting the actual SoR schema.

## 11. Replication & High Availability

```
primary (writer, AZ-A)
   ├── async read replica (AZ-B)  → hot reads (search, catalog, chat history)
   └── WAL archive → cold storage (PITR window ≥ 30 days)
```

- **Promotion:** on primary failure, promote replica (RPO ≤ 5 min async; tune for compliance).
- **Read routing:** API routes write-path to primary, read-path to replica with short read-your-writes tolerance via session stickiness or 1s grace.
- **Managed option:** Neon/RDS managed service for automated failover + branching for CI.

## 12. Backup & PITR

| Item | Spec |
|---|---|
| Full backup | daily, encrypted, geo-redundant cold storage |
| WAL archiving | continuous |
| PITR window | ≥ 30 days (compliance-adjusted) |
| Verification | monthly restore drill + reconciliation |
| Retention | daily ×30, weekly ×12, monthly ×7, annual ×7 |

Full backup/lifecycle details: `enterprise-system-of-record.md` §16–17.

## 13. Performance Targets

| Query class | Target |
|---|---|
| Registry lookup (slug→book) | cached; < 10 ms p99 miss |
| Version list per book | < 50 ms p99 |
| Chunk list per revision | < 50 ms p99 |
| Hybrid search (per book, fused) | < 500 ms p99 (excl. model calls) |
| Citation lookup by answer_hash | < 25 ms p99 |
| Worker job claim | < 100 ms p99 |

## 14. Acceptance Checks

| Check | Pass criteria |
|---|---|
| Migration determinism | Fresh DB: `alembic upgrade head` → same schema as CI |
| No DDL drift | Schema diff between migration and ORM metadata = empty |
| SoR-only writes | No code writes Qdrant/Redis without a preceding SoR commit |
| Hash reproducibility | Reindex twice → identical chunk rows |
| PITR restore | Restore to arbitrary point succeeds in drill |
| Read/write routing | No data loss on replica promotion within RPO |
