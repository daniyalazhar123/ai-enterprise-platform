# System of Record — Design (Superseded)

> **Status:** SUPERSEDED — historical working draft. Do not use as authority.
> **Replaced by:** `system-of-record.md` (AEP-SOR-M, implementation-focused design) and `enterprise-system-of-record.md` (AEP-SOR-002, full lifecycle spec: publishing, revisions, recovery, DR, backup).

This file was the original complete SoR design. Its content is fully covered — and now versioned under canonical IDs — by the two documents above. It is retained for audit trail only.

## Pointer

- **Design:** `system-of-record.md` — axiom, book hierarchy, chunking, embeddings, indexing, hybrid search, citations, registry, content pipeline.
- **Lifecycle:** `enterprise-system-of-record.md` — publishing workflow, immutable revisions, recovery, DR, backup, consistency contract.

## Conventions

- Chunk/hash determinism, RRF (k=60), citation modes (`strict|standard|lax`) and all decision records are defined in the canonical documents.
