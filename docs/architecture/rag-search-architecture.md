# RAG & Search Architecture — Enterprise Specification

> **Document ID:** AEP-RSA-006
> **Version:** 1.0
> **Status:** Approved for design. Awaiting implementation approval.
> **Owner:** Principal Enterprise Software Architect
> **Classification:** Internal — Enterprise Architecture Specification

---

## 1. Purpose

Define the retrieval-augmented generation (RAG) pipeline and hybrid search system: deterministic chunking, embeddings, semantic + lexical retrieval, fusion, reranking, and citation assembly. Search is **SoR-first**: the lexical leg runs on PostgreSQL and remains functional when derived stores fail.

## 2. Pipeline Overview

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

## 3. Ingestion & Chunking (Deterministic)

### 3.1 Chain

```
source (markdown/mdx/pdf) ──canonicalize──▶ canonical text
   ──chunk──▶ chunks (heading-aware, size/token capped)
   ──hash──▶ chunk_hash = sha256(canonical_chunk)
   ──persist──▶ content_chunks (SoR) with chunk_index, token_count
   ──embed──▶ vectors → Qdrant (point_id = content_chunk.id)
```

### 3.2 Chunking rules
- **Heading-aware:** do not split across `##`/`###` boundaries.
- **Token cap:** max ~512 tokens, with overlap window for recall.
- **Stable boundaries:** chunk_index determined by canonical text ordering; identical text → identical chunks.
- **Provenance recorded:** `chunker_version`, `canonicalizer_version`, `embedding_model` on every chunk.

### 3.3 Embedding determinism
- Embedding call is a pure function of (text, model, version).
- Same content + same pipeline version → identical vectors and point IDs.
- Unchanged chunks are **never re-embedded** (hash dedupe).

## 4. Retrieval

### 4.1 Semantic leg (Qdrant, derived)

```
filter: { book_id, version_id?, unit_id? }  (authoritative values from SoR)
distance: cosine
top: top_k (book.config, default 8) × multiplier
```

### 4.2 Lexical leg (PostgreSQL tsvector, SoR)

```
websearch_to_tsquery(locale, query)
  → rank via ts_rank_cd over content_chunks GIN index
  → filter same (book_id, version_id?)
  → top: top_k × multiplier
```

**Why lexical on the SoR:** never depends on derived store; excels at domain terms (acronyms, codes); exact-phrase queries; keeps search alive when Qdrant is down.

### 4.3 Version-aware filtering
- If request pins `version_id`, both legs filter to that edition.
- Published-by-default: unpinned queries resolve to the current published version per book.

### 4.4 Config keys (canonical)
Single source of truth for RAG settings is `apps/api/app/core/config.py`. Keys and roles:

| Key | Value | Role |
|---|---|---|
| `RAG_MAX_CONTEXT_CHUNKS` | 5 | Context window size consumed by `ai/rag/pipeline.py` |
| `RAG_SCORE_THRESHOLD` | 0.65 | Minimum accepted retrieval score |
| `RAG_RRF_K` | 60 | RRF fusion constant (§5) |
| `RAG_HYBRID_ALPHA` | 0.5 | Semantic/lexical blend (reserved) |
| `RAG_TOP_K` | 5 | Reserved default candidate count (not read by the pipeline) |

> **Do not add parallel keys.** If a new tunable is needed, extend this table first, then add the key. `RAG_TOP_K` and `RAG_MAX_CONTEXT_CHUNKS` serve distinct roles and must not be conflated.


## 5. Fusion (RRF)

```
score(d) = Σ_leg 1/(k + rank_leg(d)),  k = 60
normalize to [0,1] per result set
```

- RRF requires no parameter fitting; robust to heterogeneous score scales.
- Deduplicate by `chunk_id` across legs.
- Fusion runs on the API worker; result set ≤ 20 candidates before rerank.

## 6. Reranking

- Cohere rerank over fused candidates (top 10–20).
- Result cached in Redis keyed by `query_hash = sha256(canonical_query + version_id + top_k)`, TTL tied to content updates.
- Rerank failure → fall back to RRF-only ordering (degraded, functional).

## 7. Citation Assembly

```
top results (chunk_id, score)
  → load content_chunk rows (SoR) + linked unit/revision metadata
  → build citation records (book_id, version_id, unit_id, revision_id, chunk_id, anchor, source_text)
  → persist citations (SoR) bound to answer_hash + conversation_id
  → return citations in agent response
```

- Citations are version-pinned and **immutable in effect**: re-publishing never rewrites historical citations.
- `strict` citation mode enforces a minimum citation count per answer.

## 8. Query Rewrite

- Optional LLM step that expands/refines the user query per book template (cached, deterministic where possible).
- Template and language derived from `book.config`/`default_locale`.
- Skip rewrite for exact-phrase queries.

## 9. Failure Semantics (Search)

| Failure | Behavior | Degraded service |
|---|---|---|
| Qdrant down | semantic leg skipped (flagged) | lexical-only answers |
| Rerank down | RRF-only ordering | yes |
| Redis down | no cache; direct calls | yes |
| Embedding API down | ingest blocked; search still lexical | yes |
| Both Qdrant + Rerank down | lexical-only, RRF-only | yes |

**Guarantee:** search never 500s due to derived-store failure; it degrades to SoR-only retrieval.

## 10. Cache Design (Redis)

| Cache | Key | TTL |
|---|---|---|
| Query rewrite | `qr:{book}:{query_hash}` | 24h |
| Rerank results | `rr:{book}:{query_hash}` | tied to content revision |
| Registry/config reads | `cfg:{slug}` | until invalidation |
| Lexical tokenization | none (pg native) | — |

## 11. Indexing Job Lifecycle

```
publish/change → enqueue embedding_job(scope)
  → worker: load units from SoR → canonicalize → chunk → hash
  → upsert content_chunks (SoR) → embed → upsert Qdrant points
  → update job stats → reconciliation check
  → invalidate search caches
```

Reindex determinism test: run the pipeline twice → identical chunk rows + point IDs.

## 12. Search API Surface (REST)

| Endpoint | Purpose |
|---|---|
| `GET /api/v1/books/{slug}/search?q=&version_id=&top_k=` | hybrid search, cited results |
| `POST /api/v1/ai/chat` (stream) | RAG-grounded chat with citations |
| `GET /api/v1/books/{slug}/citations/{answer_hash}` | retrieve citations for a turn |

(Full contracts finalized at implementation gate; MCP equivalents in `mcp-architecture.md`.)

## 13. Acceptance Checks

| Check | Pass criteria |
|---|---|
| Determinism | reindex twice → identical chunk rows + point IDs |
| Reproducible rebuild | delete Qdrant collection → reindex → identical search results |
| Fail-soft | kill Qdrant → search still returns grounded lexical results |
| Version truth | v1-pinned query never returns v2 chunks |
| Grounding | returned results map 1:1 to resolvable citations |
| Cost | embedding/rerank calls deduped and metered |
