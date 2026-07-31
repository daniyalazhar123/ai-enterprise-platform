# MCP (Model Context Protocol) Architecture — Enterprise Specification

> **Document ID:** AEP-MCP-007
> **Version:** 1.0
> **Status:** Approved for design. Awaiting implementation approval.
> **Owner:** Principal Enterprise Software Architect
> **Classification:** Internal — Enterprise Architecture Specification

---

## 1. Purpose

Define the Model Context Protocol (MCP) server surface that exposes the platform's books to external LLMs and IDEs (Claude, Copilot, cursor-style tools, custom agents). MCP is a **second protocol surface** over the same gateway, domain layer, and SoR — it is a new interface, never a new store.

## 2. Positioning

```
            ┌────────────────────────────────────────────┐
            │              PLATFORM CORE                 │
            │  Gateway (REST /api) ── MCP Gateway (/mcp) │
            │         Domain Layer (content, search,     │
            │          citations, agents)                │
            │         SoR (PostgreSQL) + derived stores  │
            └────────────────────────────────────────────┘
                      ▲                    ▲
               REST clients          MCP clients (LLMs/IDEs)
```

**Design rule:** every MCP tool is a thin projection of an existing domain service. Tools never contain business logic; they only bind protocol params to service calls under RBAC.

## 3. Protocol & Transport

| Aspect | Spec |
|---|---|
| Protocol | Model Context Protocol (JSON-RPC 2.0) |
| Transport (remote) | Streamable HTTP / SSE |
| Transport (local) | stdio for local IDE agents |
| Discovery | standard `initialize` + `tools/list` |
| Auth | OAuth2 / API-token bound to platform RBAC (see §7) |

## 4. Tool Catalog

| Tool | Inputs | Outputs | Backing service |
|---|---|---|---|
| `books.list` | — | registered books + status | content.registry |
| `books.info` | slug | book config (routing, features) | content.registry |
| `books.search` | slug, query, version_id?, top_k? | cited results (chunk, anchor, score) | search.hybrid |
| `books.retrieve` | slug, path or unit_id, version_id? | unit content + revision metadata | content.units |
| `books.chat` | slug, message, history? | grounded answer + citations | ai.chat |
| `books.cite` | slug, answer_hash | full citation set for a turn | citations.resolve |
| `books.publish_info` | slug | published version + date + tree | content.versions |

Each tool returns structured data (JSON schema), book-scoped, with citations as first-class structured fields.

## 5. Tool Contract

```
tool "books.search" {
  inputs  { slug: string, query: string, version_id?: string, top_k?: int }
  rbac    book:{slug}:read
  side-effects  none (read-only)
  returns { results: [{ chunk_id, unit_path, text, score, citation }] }
}
```

### 5.1 Rules
1. **Read-only by default.** Mutating tools (`books.publish_info` is a view; there are no write tools in v1) require `content:manage` and audit.
2. **Scoped result sets** — every result filtered by `book_id` (+ `version_id`).
3. **Citations mandatory** for any content-bearing tool output.
4. **Idempotent** — no tool has non-idempotent side effects in v1.

## 6. Reasoning with the Platform via MCP

External LLMs use the tools to:

1. Discover available books (`books.list`, `books.info`).
2. Ground answers in authoritative content (`books.search`, `books.retrieve`).
3. Produce cited responses (`books.cite` with `answer_hash`).
4. Preserve version truth by passing `version_id` through.

The platform never trusts the external model's claims; the SoR's citation records are the audit trail.

## 7. Authentication & Authorization

### 7.1 Identity
- MCP clients authenticate via OAuth2 bearer token or short-lived API key.
- Tokens resolve to a platform user + session; every call audited with `actor_id`.

### 7.2 Authorization (RBAC)
- Each tool declares its required scope (e.g., `book:{slug}:read`).
- Gateway enforces scope before dispatch; book scoping is mandatory — a caller can only touch books it is granted.
- Rate limits: per client + per book (shared Redis).

### 7.3 Threat controls
- Prompt-injection hardening: tool outputs delimited as data.
- Token budget per MCP client.
- Full audit of tool invocations (request_id, client, user, book, tool, latency).

## 8. Deployment

- MCP server runs as its own process (`mcp` container image) behind the ingress at `/mcp`.
- Shares config and SoR connection with the API; independent horizontal scaling.
- stdio transport enabled only for local/dev containers, never exposed externally.

See `docker-kubernetes-architecture.md` for image topology.

## 9. Observability

| Metric | Where |
|---|---|
| tool calls by type/client | audit + metrics |
| citations returned per call | telemetry |
| latency per tool | metrics |
| auth failures / rate-limit hits | security audit |

## 10. Versioning & Compatibility

- Tool schemas are versioned; breaking schema changes add a new tool version, deprecating the old over a grace period.
- `version_id` semantics match the SoR: exact edition pinning.
- Feature flags per book (`features.mcp`) control tool availability.

## 11. Acceptance Checks

| Check | Pass criteria |
|---|---|
| Contract compliance | `tools/list` + each tool conforms to schema |
| Book scoping | unauthorized book access denied (403) |
| Citation completeness | every content tool returns resolvable citations |
| Read-only default | no mutation without `content:manage` + audit |
| AuthN | tokenless calls rejected (401) |
| Isolation | MCP process failure never affects REST API |
