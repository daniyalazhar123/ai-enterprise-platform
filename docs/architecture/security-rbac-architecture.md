# Security & RBAC Architecture — Enterprise Specification

> **Document ID:** AEP-SEC-009
> **Version:** 1.0
> **Status:** Approved for design. Awaiting implementation approval.
> **Owner:** Principal Enterprise Software Architect
> **Classification:** Internal — Enterprise Architecture Specification

---

## 1. Purpose

Define authentication, authorization (RBAC), audit, and secret management for the platform. The existing auth module (JWT access/refresh rotation, Argon2id, RBAC hierarchy, audit logging) is judged enterprise-grade and is **retained as the foundation**; this spec adds book-scoped authorization, hardens the frontend token transport, and defines the threat model.

## 2. Security Principles

1. **Defense in depth:** authN → authZ → rate-limit → audit at every layer.
2. **Least privilege:** every call is scoped to the minimum book/action.
3. **Book-scoped by default:** no cross-book access without explicit grant.
4. **Secrets never on disk/repo:** injected via Vault/KMS at runtime.
5. **Fail closed:** on any ambiguity, deny + audit.
6. **Audit everything:** identity, content, publishing, AI calls.

## 3. Authentication

### 3.1 Credentials & verification
- Passwords hashed with **Argon2id** (never reversible, never stored).
- Verification flow (email, optional 2FA) before account activation.

### 3.2 Token architecture (retained)

```
access token (JWT, short-lived 15 min)
  └─ signed, carries actor_id + role claims
refresh token (opaque, rotation with reuse detection)
  └─ one-time use; rotation on every refresh
  └─ theft detection: reuse of an old token revokes the family
```

- **Rotation with reuse detection** and **theft detection** are retained from the current implementation (correct design).
- **Refresh tokens stored hashed** in PostgreSQL (`refresh_tokens`), not plaintext.

### 3.3 Frontend transport (defects to fix — Phase 3)

| Current issue | Target |
|---|---|
| Access token in `sessionStorage` (`packages/auth/src/api.ts`) | short-lived token in memory; refresh in HttpOnly cookie |
| Refresh route sends `refresh_token: ""` (`hooks.ts`) | read cookie server-side; never expose refresh token to JS |
| No `middleware.ts` | Next.js middleware guards private routes by cookie |
| `ProtectedRoute` unused | use guard on client + middleware on server |

## 4. Authorization (RBAC)

### 4.1 Role hierarchy (retained, extended)

```
SuperAdmin
   └─ Admin
        └─ Editor (per book)
             └─ Reviewer (per book)
                  └─ Reader (per book)
```

- Global roles: `SuperAdmin`, `Admin`.
- Book-scoped roles: `Reader`, `Reviewer`, `Editor`, `Publisher`, `Manager` per book.

### 4.2 Permission model

```
permission := action on resource
resource   := global | book:{slug}
action     := read | write | review | publish | manage

examples:
  book:cybersecurity:read
  book:banking-finance:review
  content:write (global editor)
```

### 4.3 Resource scopes

| Scope pattern | Meaning |
|---|---|
| `book:{slug}:read` | view content/search/chat of that book |
| `book:{slug}:write` | create/edit content (revisions) |
| `book:{slug}:review` | approve/reject submissions |
| `book:{slug}:publish` | publish versions |
| `book:{slug}:manage` | manage book config, RBAC, lifecycle |

### 4.4 Enforcement points (every layer)

1. **Gateway:** validate JWT → resolve user → check scope for route/tool.
2. **Domain:** re-check scope on sensitive operations (publish, manage).
3. **Data:** queries always filter by permitted `book_id` set (defense in depth).
4. **MCP:** per-tool scope declaration (see `mcp-architecture.md` §7).

## 5. Audit Logging

| Event class | Recorded |
|---|---|
| Identity | login, refresh, reuse-detected, 2FA, account changes |
| Publishing | submit, approve, reject, publish, archive (with reviewer/publisher) |
| Content | revision create, hash dedupe, index job events |
| AI | every model call: user, book, model, tokens, cost, latency |
| Admin | RBAC changes, config changes, secret rotation |
| MCP | tool invocation, client, result scope |

Audit rows are **append-only** in PostgreSQL (`audit_logs`), partitioned, retention-managed. Never stored only in logs.

## 6. Rate Limiting

- Shared, cross-worker via Redis (`rate_limit` buckets).
- Keys: `user`, `book`, `IP`, `model`, `MCP-client`.
- Enforcement: per-second burst + per-minute sustained; configurable per book.

## 7. Secrets Management

| Item | Spec |
|---|---|
| Storage | Vault / KMS (cloud managed) |
| Runtime injection | env from External Secrets (K8s) or compose secrets (dev) |
| Rotation | automated, audited; no downtime pattern |
| Prohibited | secrets in images, repo, `.secrets/` auto-write (remove), client bundles |

**Config loader change (Phase 0/5):** stop auto-writing JWT keys to `.secrets/`; use env/secret store.

## 8. Threat Model

| Threat | Mitigation |
|---|---|
| Token theft (XSS) | access token in memory only; refresh in HttpOnly cookie; rotation + reuse detection |
| Cross-book access | book-scoped RBAC + query filtering at all layers |
| Prompt injection via content | tool outputs delimited as data; guardrails |
| PII exposure | PII detection + redaction policy on AI I/O |
| Secret exfiltration | no secrets on disk; least-privilege service accounts |
| DDoS/abuse | rate limits, quotas, budgets per book |
| Supply chain | image digest pinning, SBOM, scan gate in CI |
| Data loss | SoR-only truth, PITR, DR drills (see SoR §14–17) |

## 9. Compliance Considerations

- **Retention:** audit + content per policy (30d–7y depending on class).
- **Right to erasure:** anonymize/expunge per lifecycle; citations redacted, never lost.
- **Encryption:** TLS in transit; encryption at rest for all stores/backups.
- **Region:** data residency options via managed Postgres placement (per customer need).

## 10. Acceptance Checks

| Check | Pass criteria |
|---|---|
| Book scoping | user without `book:{slug}:read` → 403 on REST + MCP |
| Token refresh | refresh from HttpOnly cookie; JS never sees refresh token |
| Reuse detection | replaying a rotated refresh token revokes family + alerts |
| Secrets hygiene | `gitleaks`/scan gate green; no `.secrets/` writes |
| Audit completeness | every publish + AI call appears in audit_logs |
| Rate limits | shared across pods (Redis) |
