# Authentication Module — Enterprise AI Engineering Platform

> **Status:** Specification v1.0
> **Stack:** FastAPI · SQLModel · PostgreSQL (Neon) · JWT · Clerk · Argon2

---

## 1. Folder Structure

```
apps/api/
└── app/
    ├── auth/
    │   ├── __init__.py
    │   ├── router.py
    │   ├── deps.py
    │   ├── middleware.py
    │   ├── schemas/
    │   │   ├── __init__.py
    │   │   ├── request.py
    │   │   └── response.py
    │   ├── service/
    │   │   ├── __init__.py
    │   │   ├── authentication.py
    │   │   ├── authorization.py
    │   │   ├── password.py
    │   │   ├── token.py
    │   │   ├── session.py
    │   │   ├── verification.py
    │   │   └── oauth.py
    │   ├── clerk/
    │   │   ├── __init__.py
    │   │   ├── client.py
    │   │   └── webhooks.py
    │   └── tests/
    │       ├── __init__.py
    │       ├── conftest.py
    │       ├── test_authentication.py
    │       ├── test_authorization.py
    │       ├── test_oauth.py
    │       ├── test_tokens.py
    │       └── test_clerk.py
    ├── models/
    │   ├── __init__.py
    │   ├── user.py
    │   ├── session.py
    │   ├── refresh_token.py
    │   ├── role.py
    │   ├── permission.py
    │   └── audit_log.py
    ├── db/
    │   ├── __init__.py
    │   ├── session.py
    │   └── base.py
    └── core/
        ├── __init__.py
        ├── config.py
        ├── security.py
        └── exceptions.py
```

---

## 2. Database Schema

### 2.1 Entity-Relationship Overview

```
users 1───* sessions
users 1───* refresh_tokens
users 1───* audit_logs
users *───* roles
roles *───* permissions
```

### 2.2 Physical Schema

```ascii
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  users                          roles                                  │
│  ──────────────────────         ─────────────────────                  │
│  id            UUID PK          id            UUID PK                  │
│  email         VARCHAR(320) UQ   name          VARCHAR(100) UQ         │
│  password_hash TEXT             description   TEXT                      │
│  display_name  VARCHAR(255)     is_system     BOOLEAN                  │
│  avatar_url    TEXT             created_at    TIMESTAMPTZ               │
│  is_verified   BOOLEAN          updated_at    TIMESTAMPTZ               │
│  is_active     BOOLEAN                                                 │
│  is_superuser  BOOLEAN          user_roles                             │
│  locale        VARCHAR(10)      ─────────────────────                  │
│  clerk_id      VARCHAR(255) UQ  user_id       UUID FK users            │
│  last_login_at TIMESTAMPTZ      role_id       UUID FK roles            │
│  created_at    TIMESTAMPTZ                                             │
│  updated_at    TIMESTAMPTZ      permissions                            │
│  deleted_at    TIMESTAMPTZ      ─────────────────────                  │
│                                 id            UUID PK                  │
│  sessions                       resource      VARCHAR(255)             │
│  ─────────────────────          action        VARCHAR(100)             │
│  id            UUID PK          description   TEXT                      │
│  user_id       UUID FK users    is_system     BOOLEAN                  │
│  token_hash    TEXT UQ          created_at    TIMESTAMPTZ               │
│  ip_address    INET                                                     │
│  user_agent    TEXT             role_permissions                        │
│  device_info   JSONB            ─────────────────────                  │
│  is_active     BOOLEAN          role_id       UUID FK roles            │
│  expires_at    TIMESTAMPTZ      permission_id UUID FK permissions      │
│  created_at    TIMESTAMPTZ                                             │
│  last_used_at  TIMESTAMPTZ     audit_logs                              │
│                                 ─────────────────────                  │
│  refresh_tokens                  id            UUID PK                  │
│  ─────────────────────          user_id       UUID FK users            │
│  id            UUID PK          session_id    UUID FK sessions         │
│  user_id       UUID FK users    event_type    VARCHAR(50)              │
│  session_id    UUID FK sessions  resource      VARCHAR(255)             │
│  token_hash    TEXT UQ          resource_id   VARCHAR(255)             │
│  family        VARCHAR(64)      action        VARCHAR(100)             │
│  metadata      JSONB            actor_ip      INET                     │
│  expires_at    TIMESTAMPTZ      actor_ua      TEXT                     │
│  revoked_at    TIMESTAMPTZ      metadata      JSONB                    │
│  created_at    TIMESTAMPTZ      created_at    TIMESTAMPTZ              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.3 Indexes

| Table | Index | Columns | Type |
|---|---|---|---|
| users | idx_users_email | email | UNIQUE |
| users | idx_users_clerk_id | clerk_id | UNIQUE |
| users | idx_users_active | is_active, deleted_at | Partial |
| sessions | idx_sessions_user | user_id | BTREE |
| sessions | idx_sessions_token | token_hash | UNIQUE |
| sessions | idx_sessions_expires | expires_at | BTREE |
| refresh_tokens | idx_rt_user | user_id | BTREE |
| refresh_tokens | idx_rt_token | token_hash | UNIQUE |
| refresh_tokens | idx_rt_family | family | BTREE |
| refresh_tokens | idx_rt_revoked | revoked_at | Partial |
| audit_logs | idx_audit_user | user_id | BTREE |
| audit_logs | idx_audit_event | event_type, created_at | BTREE |
| audit_logs | idx_audit_resource | resource, resource_id | BTREE |
| permissions | idx_perm_resource_action | resource, action | UNIQUE |

### 2.4 Partitioning Strategy

`audit_logs` — Range-partitioned by `created_at` (monthly).

---

## 3. SQLModel Models

| Model | Table | Key Relationships |
|---|---|---|
| User | `users` | Has many Sessions, RefreshTokens, AuditLogs; many-to-many Roles |
| Session | `sessions` | Belongs to User; has many RefreshTokens |
| RefreshToken | `refresh_tokens` | Belongs to User and Session |
| Role | `roles` | Many-to-many Users and Permissions |
| Permission | `permissions` | Many-to-many Roles |
| AuditLog | `audit_logs` | Belongs to User and Session |

---

## 4. Users Table

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | UUID | PK, default gen_random_uuid() | Primary identifier |
| email | VARCHAR(320) | NOT NULL, UNIQUE | Verified email address |
| password_hash | TEXT | NULLABLE | Argon2 hash; NULL for OAuth-only accounts |
| display_name | VARCHAR(255) | NOT NULL | Public-facing name |
| avatar_url | TEXT | NULLABLE | Profile image URL |
| is_verified | BOOLEAN | NOT NULL, DEFAULT FALSE | Email verified flag |
| is_active | BOOLEAN | NOT NULL, DEFAULT TRUE | Account active flag |
| is_superuser | BOOLEAN | NOT NULL, DEFAULT FALSE | Bypasses all permission checks |
| locale | VARCHAR(10) | NOT NULL, DEFAULT 'en' | IETF language tag |
| clerk_id | VARCHAR(255) | UNIQUE, NULLABLE | Clerk user ID for hybrid auth |
| last_login_at | TIMESTAMPTZ | NULLABLE | Most recent authentication |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Row creation timestamp |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Row update timestamp |
| deleted_at | TIMESTAMPTZ | NULLABLE | Soft-delete timestamp |

### 4.1 Soft Delete Rule

All queries MUST include `WHERE deleted_at IS NULL` via a default SQLModel scope. Hard deletes are FORBIDDEN.

---

## 5. Sessions Table

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | UUID | PK, default gen_random_uuid() | Primary identifier |
| user_id | UUID | FK → users.id, NOT NULL | Owning user |
| token_hash | TEXT | NOT NULL, UNIQUE | SHA-256 of opaque session token |
| ip_address | INET | NOT NULL | Client IP at creation |
| user_agent | TEXT | NOT NULL | Client User-Agent string |
| device_info | JSONB | NOT NULL, DEFAULT '{}' | Device fingerprint metadata |
| is_active | BOOLEAN | NOT NULL, DEFAULT TRUE | Session revocation flag |
| expires_at | TIMESTAMPTZ | NOT NULL | Absolute expiration (24h default) |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Row creation timestamp |
| last_used_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Most recent request timestamp |

### 5.1 Session Limits

Maximum **10 active sessions per user**. Creating the 11th session revokes the oldest inactive session.

---

## 6. Refresh Tokens

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | UUID | PK, default gen_random_uuid() | Primary identifier |
| user_id | UUID | FK → users.id, NOT NULL | Token owner |
| session_id | UUID | FK → sessions.id, NOT NULL | Parent session |
| token_hash | TEXT | NOT NULL, UNIQUE | SHA-256 of opaque refresh token |
| family | VARCHAR(64) | NOT NULL | Token family for rotation detection |
| metadata | JSONB | NOT NULL, DEFAULT '{}' | Extensible metadata payload |
| expires_at | TIMESTAMPTZ | NOT NULL | Absolute expiration (7 days default) |
| revoked_at | TIMESTAMPTZ | NULLABLE | Timestamp of revocation |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Row creation timestamp |

### 6.1 Token Family Reuse Detection

When a refresh token from a revoked family is presented, ALL tokens in that family and ALL associated sessions are immediately revoked. This detects token theft.

---

## 7. Roles

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | UUID | PK, default gen_random_uuid() | Primary identifier |
| name | VARCHAR(100) | NOT NULL, UNIQUE | Role identifier (e.g., `admin`, `editor`, `viewer`) |
| description | TEXT | NULLABLE | Human-readable description |
| is_system | BOOLEAN | NOT NULL, DEFAULT FALSE | Protects system roles from deletion |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Row creation timestamp |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Row update timestamp |

### 7.1 System Roles

| Role | Description |
|---|---|
| `superadmin` | Full system access, is_system=TRUE |
| `admin` | Administrative operations |
| `editor` | Content creation and modification |
| `viewer` | Read-only access |

### 7.2 Junction Table — user_roles

| Column | Type | Constraints |
|---|---|---|
| user_id | UUID | FK → users.id, NOT NULL, PK composite |
| role_id | UUID | FK → roles.id, NOT NULL, PK composite |

---

## 8. Permissions

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | UUID | PK, default gen_random_uuid() | Primary identifier |
| resource | VARCHAR(255) | NOT NULL | Resource pattern (e.g., `users`, `projects:*`) |
| action | VARCHAR(100) | NOT NULL | Action (e.g., `create`, `read`, `update`, `delete`, `manage`) |
| description | TEXT | NULLABLE | Human-readable description |
| is_system | BOOLEAN | NOT NULL, DEFAULT FALSE | Protects system permissions from deletion |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Row creation timestamp |

### 8.1 Naming Convention

```
<resource>:<action>
```

| Example | Meaning |
|---|---|
| `users:read` | Read any user profile |
| `users:write` | Modify any user profile |
| `projects:create` | Create new projects |
| `projects:*:delete` | Delete any project |
| `workspace:manage` | Full workspace administration |

### 8.2 Junction Table — role_permissions

| Column | Type | Constraints |
|---|---|---|
| role_id | UUID | FK → roles.id, NOT NULL, PK composite |
| permission_id | UUID | FK → permissions.id, NOT NULL, PK composite |

### 8.3 Permission Evaluation

1. If `user.is_superuser` is TRUE → GRANT
2. Collect all permissions from all assigned roles
3. If requested `resource:action` matches an explicit permission → GRANT
4. If any assigned role lacks `resource:action` explicitly → DENY
5. Default: DENY

---

## 9. Audit Logs

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | UUID | PK, default gen_random_uuid() | Primary identifier |
| user_id | UUID | FK → users.id, NOT NULL | Acting user |
| session_id | UUID | FK → sessions.id, NULLABLE | Session context |
| event_type | VARCHAR(50) | NOT NULL | Event classification |
| resource | VARCHAR(255) | NOT NULL | Affected resource type |
| resource_id | VARCHAR(255) | NULLABLE | Affected resource identifier |
| action | VARCHAR(100) | NOT NULL | Action performed |
| actor_ip | INET | NOT NULL | Request origin IP |
| actor_ua | TEXT | NOT NULL | Request User-Agent |
| metadata | JSONB | NOT NULL, DEFAULT '{}' | Event-specific payload |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Event timestamp |

### 9.1 Event Types

| Event Type | Trigger |
|---|---|
| `auth.login` | Successful authentication |
| `auth.login.failed` | Failed login attempt |
| `auth.logout` | Explicit logout |
| `auth.refresh` | Token rotation |
| `auth.token.revoked` | Token theft detected |
| `user.created` | Account registration |
| `user.updated` | Profile modification |
| `user.deleted` | Account soft-delete |
| `user.verified` | Email verification |
| `user.password.reset` | Password reset |
| `user.password.changed` | Password change |
| `role.assigned` | Role granted to user |
| `role.revoked` | Role removed from user |
| `permission.denied` | Authorization failure |
| `oauth.linked` | OAuth provider linked |
| `oauth.unlinked` | OAuth provider unlinked |
| `clerk.webhook` | Clerk webhook received |
| `session.revoked` | Admin session revocation |
| `session.expired` | Automatic session cleanup |

### 9.2 Retention Policy

- Active audit logs: 90 days in primary table
- Archived audit logs: 1 year in partitioned archive
- Compressed cold storage: 7 years (Parquet in S3/Blob)

---

## 10. JWT Strategy

### 10.1 Token Specification

| Field | Access Token | Refresh Token |
|---|---|---|
| Format | JWT (signed) | Opaque (32-byte random) |
| Storage | Client memory only | `httpOnly` secure cookie + DB hash |
| Lifetime | 15 minutes | 7 days |
| Algorithm | RS256 (asymmetric) | N/A |
| Rotation | N/A | On every refresh |
| Reuse Detection | N/A | Token family tracking |

### 10.2 Access Token Claims

```json
{
  "sub": "uuid-of-user",
  "sid": "uuid-of-session",
  "email": "user@example.com",
  "name": "Display Name",
  "roles": ["admin", "editor"],
  "permissions": ["users:read", "projects:write"],
  "iat": 1700000000,
  "exp": 1700000900,
  "iss": "https://auth.ai-enterprises.com",
  "aud": "ai-enterprises-api",
  "jti": "unique-token-id",
  "type": "access"
}
```

### 10.3 Key Management

| Key | Rotation | Storage |
|---|---|---|
| RS256 Private Key | Every 30 days | Hardware Security Module (HSM) or encrypted env |
| RS256 Public Key | Published with JWKS | `.well-known/jwks.json` endpoint |

### 10.4 JWKS Endpoint

`GET /.well-known/jwks.json` — Serves current and previous public keys with `kid` header matching JWT `kid`.

---

## 11. Refresh Token Strategy

### 11.1 Flow

1. Client presents refresh token (opaque, `httpOnly` cookie)
2. Server hashes token with SHA-256
3. Server looks up hash in `refresh_tokens` table
4. Server validates `expires_at > now()` and `revoked_at IS NULL`
5. Server issues new access token (15 min) and new refresh token (rotated)
6. New refresh token shares the same `family` value
7. Previous refresh token is marked `revoked_at = now()`

### 11.2 Theft Detection

If a revoked refresh token is presented (family reuse):
1. All tokens sharing `family` are immediately revoked
2. All sessions associated with those tokens are deactivated
3. `audit_logs` records `auth.token.revoked` with theft flag
4. User is forced to re-authenticate on all devices

---

## 12. Password Hashing

### 12.1 Policy

| Parameter | Value |
|---|---|
| Algorithm | Argon2id |
| Memory Cost | 64 MB |
| Time Cost | 3 iterations |
| Parallelism | 4 threads |
| Salt Length | 16 bytes |
| Hash Length | 32 bytes |
| Encoding | PHC string format |

### 12.2 PHC Format

```
$argon2id$v=19$m=65536,t=3,p=4$<base64-salt>$<base64-hash>
```

### 12.3 Password Validation Rules

| Rule | Value |
|---|---|
| Minimum Length | 12 characters |
| Maximum Length | 128 characters |
| Character Classes | At least 3 of: uppercase, lowercase, digits, special |
| Common Password Check | Against 10k+ common password list |
| Pwned Password Check | k-anonymity query to Have I Been Pwned API |
| Maximum Age | 90 days (enforced for sensitive roles) |
| History | No reuse of last 5 passwords |
| Rate Limit | 5 attempts per 15 minutes per IP |

---

## 13. Argon2 Configuration

### 13.1 Production Tuning

| Environment | Memory | Time | Parallelism |
|---|---|---|---|
| Development | 19 MiB | 2 | 1 |
| Staging | 64 MiB | 3 | 4 |
| Production | 64 MiB | 3 | 4 |
| High-Security | 128 MiB | 4 | 8 |

### 13.2 Verification Cost Constant

Verification time MUST NOT exceed 1 second on production hardware. If Argon2 parameters cause >1s verification, reduce `time` cost first, then `memory`.

---

## 14. Clerk Integration

### 14.1 Architecture

Clerk operates as an **optional identity provider** in hybrid mode:
- Users MAY register via Clerk (Google, GitHub, email magic link)
- Users MAY register via native platform auth (email + password)
- Both paths converge into the same `users` table
- Clerk users have `clerk_id` populated; native users have `password_hash` populated
- A user MAY link both: `clerk_id` + `password_hash` both non-null

### 14.2 Webhook Events

| Clerk Event | Platform Action |
|---|---|
| `user.created` | Upsert local user record |
| `user.updated` | Sync profile fields (name, avatar, locale) |
| `user.deleted` | Soft-delete local user |
| `session.created` | Create local session record |
| `session.revoked` | Revoke local session record |
| `email.verified` | Mark `is_verified = TRUE` |

### 14.3 Webhook Verification

Every Clerk webhook MUST be verified using `svix` signature verification before processing.

### 14.4 Boundary

When Clerk is the sole identity provider, the following endpoints are DISABLED:
- `POST /auth/register`
- `POST /auth/forgot-password`
- `POST /auth/reset-password`

The `password_hash` column remains NULL for Clerk-only users.

---

## 15. Google Login

### 15.1 Flow

1. Client redirects to `GET /auth/oauth/google`
2. Server generates state parameter (anti-CSRF, stored in session cache)
3. Server redirects to Google OAuth 2.0 authorize URL
4. Google redirects to `GET /auth/oauth/google/callback?code=...&state=...`
5. Server validates state parameter
6. Server exchanges authorization code for tokens
7. Server fetches user profile from Google
8. Server looks up or creates user by email
9. If Clerk is enabled, server upserts Clerk user
10. Server creates local session and issues tokens
11. Client is redirected to frontend with session cookie

### 15.2 Requested Scopes

```
openid, email, profile
```

---

## 16. GitHub Login

### 16.1 Flow

Identical to Google login flow with `GET /auth/oauth/github` and `GET /auth/oauth/github/callback`.

### 16.2 Requested Scopes

```
read:user, user:email
```

### 16.3 Email Privacy

GitHub may not expose primary email. If email is private, the platform fetches the email list from the GitHub API and selects the primary verified email.

---

## 17. Email Verification

### 17.1 Token Specification

| Field | Value |
|---|---|
| Format | cryptographically random 32-byte token |
| Encoding | URL-safe base64 |
| Storage | SHA-256 hash in database |
| Lifetime | 24 hours |
| Purpose | Email ownership verification |

### 17.2 Flow

1. User registers → `is_verified = FALSE`
2. Server generates verification token, stores hash in DB
3. Server sends email with `https://platform.com/auth/verify?token=<token>`
4. Client clicks link → `GET /auth/verify?token=<token>`
5. Server hashes token, looks up in DB
6. Server sets `is_verified = TRUE`
7. Server invalidates the verification token
8. User is redirected to login with `?verified=true`

### 17.3 Resend

- Rate limit: 1 resend per 60 seconds
- Max: 5 resends per 24 hours

---

## 18. Forgot Password

### 18.1 Flow

1. User submits email via `POST /auth/forgot-password`
2. Server checks if user exists with that email (always returns 200 to prevent enumeration)
3. If user exists and has `password_hash` non-null, server generates reset token
4. Server stores SHA-256 hash of token with 1-hour expiration
5. Server sends email with `https://platform.com/auth/reset?token=<token>`
6. Link points to frontend reset page

### 18.2 Rate Limiting

- 1 request per 60 seconds per email
- 5 requests per 24 hours per email
- 10 requests per 15 minutes per IP

---

## 19. Reset Password

### 19.1 Flow

1. User navigates to frontend reset page with token in URL
2. User submits new password via `POST /auth/reset-password`
3. Server validates token (hash match + not expired + not used)
4. Server validates password against policy (12+ chars, 3 of 4 classes, not pwned)
5. Server hashes new password with Argon2id
6. Server updates `users.password_hash`
7. Server invalidates the reset token
8. Server revokes ALL sessions for the user except current one
9. Server revokes ALL refresh tokens for the user
10. Server records `user.password.reset` in audit logs
11. Server sends confirmation email
12. Client redirects to login with `?password-reset=true`

### 19.2 Password History

The last 5 password hashes are stored in a separate `password_history` table. The new password hash is validated against the historical hashes before update.

---

## 20. Protected Routes

### 20.1 Frontend Protection

| Route | Auth Required | Additional Check |
|---|---|---|
| `/dashboard/*` | Yes | User must have `session.is_active` |
| `/admin/*` | Yes | User must have role `admin` or `superadmin` |
| `/settings` | Yes | Owner-only |
| `/settings/team` | Yes | `workspace:manage` permission |
| `/api/*` (client) | Yes | Valid JWT in Authorization header |

### 20.2 Backend Protection

| Strategy | Scope | Mechanism |
|---|---|---|
| JWT validation | All authenticated routes | FastAPI dependency |
| Session validation | All authenticated routes | Check session exists and is active |
| Permission check | Authorized routes | FastAPI dependency evaluating resource:action |
| Role check | Admin routes | FastAPI dependency evaluating role membership |
| Rate limiting | Auth endpoints | Token bucket per IP/user |
| IP allowlist | Admin endpoints | Configurable CIDR ranges |

### 20.3 Frontend Middleware

Next.js middleware checks:
1. `__session` cookie presence
2. Token expiration (client-side decoding, no signature verification)
3. Route-level role/permission requirements
4. Redirect to `/login` with `?redirect=<original_path>` on failure

---

## 21. Role-Based Access Control (RBAC)

### 21.1 Evaluation Model

```
USER → ROLES → PERMISSIONS → RESOURCE:ACTION
```

### 21.2 Dependency Injection

```python
# Pseudocode dependency signatures:

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User
async def get_valid_session(user: User = Depends(get_current_user)) -> Session
async def require_permission(
    resource: str,
    action: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_valid_session),
) -> None
async def require_role(
    role_name: str,
    user: User = Depends(get_current_user),
) -> None
```

### 21.3 Permission Hierarchy

```
manage > write > create > read
```

- `manage` implies all lower actions
- `write` implies `create` and `read`
- `create` implies `read`

### 21.4 Resource Patterns

| Pattern | Matches |
|---|---|
| `users:*` | All user resources |
| `projects:new-project-id` | Specific project |
| `projects:*` | All projects |
| `*:read` | Read on any resource |

### 21.5 Deny Priority

Explicit denies override grants. A deny rule on `users:delete` blocks delete even if `manage` is granted.

---

## 22. Security Best Practices

### 22.1 Authentication

| Practice | Implementation |
|---|---|
| Password hashing | Argon2id with memory-hard parameters |
| Token storage | Opaque refresh tokens, DB-hashed; JWT in memory only |
| Session binding | Access token linked to session ID |
| Token rotation | Every refresh rotates the refresh token |
| Theft detection | Token family reuse = mass revocation |
| Rate limiting | Tiered: per-IP, per-user, per-endpoint |
| Account lockout | 10 failed attempts = 15 min lockout |
| Concurrent session limit | Max 10 active sessions per user |

### 22.2 Transport Security

| Practice | Implementation |
|---|---|
| TLS | TLS 1.3 minimum, HSTS header |
| Cookie flags | `__Host-` prefix, `Secure`, `HttpOnly`, `SameSite=Strict` |
| CORS | Origin whitelist, credentials allowed only for known origins |
| CSP | Strict Content-Security-Policy header |

### 22.3 API Security

| Practice | Implementation |
|---|---|
| CSRF | State parameter in OAuth, `SameSite=Strict` cookies |
| Rate limiting | Token bucket per-IP (100 req/min), per-user (500 req/min) |
| Input validation | Pydantic strict mode, max length constraints |
| SQL injection | SQLModel parameterized queries only |
| No sensitive leaks | Error responses never expose internal state |
| Audit logging | All auth events logged with actor, resource, metadata |

### 22.4 Data Protection

| Practice | Implementation |
|---|---|
| Password storage | Argon2id, never logged or returned |
| Token storage | SHA-256 hash in DB, never plaintext |
| PII minimization | Only essential claims in JWT |
| Soft delete | `deleted_at` instead of row removal |
| Encryption at rest | PostgreSQL TDE or disk-level encryption |
| Encryption in transit | TLS 1.3 |

### 22.5 Operational Security

| Practice | Implementation |
|---|---|
| Key rotation | JWT signing keys every 30 days |
| Secret rotation | All secrets every 90 days |
| Dependency scanning | Weekly `pip audit` and `npm audit` |
| Penetration testing | Quarterly |
| Incident response | Automated session revocation endpoint |

---

## 23. API Endpoints

### 23.1 Public Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/auth/register` | Create account |
| POST | `/api/v1/auth/login` | Authenticate with email + password |
| POST | `/api/v1/auth/refresh` | Rotate tokens |
| POST | `/api/v1/auth/logout` | Terminate session |
| GET | `/api/v1/auth/verify` | Verify email (query token) |
| POST | `/api/v1/auth/resend-verification` | Resend verification email |
| POST | `/api/v1/auth/forgot-password` | Request password reset |
| POST | `/api/v1/auth/reset-password` | Execute password reset |
| GET | `/api/v1/auth/oauth/google` | Initiate Google OAuth |
| GET | `/api/v1/auth/oauth/google/callback` | Google OAuth callback |
| GET | `/api/v1/auth/oauth/github` | Initiate GitHub OAuth |
| GET | `/api/v1/auth/oauth/github/callback` | GitHub OAuth callback |
| GET | `/.well-known/jwks.json` | Public JWKS endpoint |
| POST | `/api/v1/auth/clerk/webhook` | Clerk webhook receiver |

### 23.2 Protected Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/auth/me` | Get current user profile |
| PATCH | `/api/v1/auth/me` | Update current user profile |
| GET | `/api/v1/auth/sessions` | List active sessions |
| DELETE | `/api/v1/auth/sessions/{session_id}` | Revoke specific session |
| DELETE | `/api/v1/auth/sessions` | Revoke all other sessions |

### 23.3 Admin Endpoints

| Method | Path | Permission Required |
|---|---|---|
| GET | `/api/v1/admin/users` | `users:read` |
| GET | `/api/v1/admin/users/{user_id}` | `users:read` |
| PATCH | `/api/v1/admin/users/{user_id}` | `users:write` |
| DELETE | `/api/v1/admin/users/{user_id}` | `users:delete` |
| POST | `/api/v1/admin/users/{user_id}/roles` | `users:write` |
| DELETE | `/api/v1/admin/users/{user_id}/roles/{role_id}` | `users:write` |
| GET | `/api/v1/admin/roles` | `roles:read` |
| POST | `/api/v1/admin/roles` | `roles:create` |
| PATCH | `/api/v1/admin/roles/{role_id}` | `roles:write` |
| DELETE | `/api/v1/admin/roles/{role_id}` | `roles:delete` |
| GET | `/api/v1/admin/permissions` | `permissions:read` |
| POST | `/api/v1/admin/permissions` | `permissions:create` |
| PATCH | `/api/v1/admin/permissions/{permission_id}` | `permissions:write` |
| DELETE | `/api/v1/admin/permissions/{permission_id}` | `permissions:delete` |
| GET | `/api/v1/admin/audit-logs` | `audit:read` |

---

## 24. API Contracts

### 24.1 POST /api/v1/auth/register

```
Request:
  Content-Type: application/json

  {
    "email": "user@example.com",
    "password": "SecureP@ss123!",
    "display_name": "John Doe",
    "locale": "en"
  }

Response 201:
  Set-Cookie: __Host-refresh_token=<opaque>; Path=/api/v1/auth; HttpOnly; Secure; SameSite=Strict; Max-Age=604800

  {
    "status": "success",
    "data": {
      "user": { ... user response ... },
      "access_token": "eyJhbGciOiJSUzI1NiIs...",
      "expires_in": 900
    }
  }

Response 409:
  {
    "status": "error",
    "error": {
      "code": "EMAIL_ALREADY_EXISTS",
      "message": "An account with this email already exists."
    }
  }

Response 422:
  {
    "status": "error",
    "error": {
      "code": "VALIDATION_ERROR",
      "message": "Password must be at least 12 characters.",
      "details": [
        { "field": "password", "message": "String should have at least 12 characters" }
      ]
    }
  }
```

### 24.2 POST /api/v1/auth/login

```
Request:
  Content-Type: application/json

  {
    "email": "user@example.com",
    "password": "SecureP@ss123!",
    "device_info": {
      "platform": "Windows",
      "browser": "Chrome 120",
      "timezone": "America/New_York"
    }
  }

Response 200:
  Set-Cookie: __Host-refresh_token=<opaque>; Path=/api/v1/auth; HttpOnly; Secure; SameSite=Strict; Max-Age=604800

  {
    "status": "success",
    "data": {
      "user": { ... user response ... },
      "access_token": "eyJhbGciOiJSUzI1NiIs...",
      "expires_in": 900
    }
  }

Response 401:
  {
    "status": "error",
    "error": {
      "code": "INVALID_CREDENTIALS",
      "message": "Invalid email or password."
    }
  }

Response 423:
  {
    "status": "error",
    "error": {
      "code": "ACCOUNT_LOCKED",
      "message": "Account temporarily locked due to too many failed attempts. Try again in 15 minutes.",
      "retry_after_seconds": 900
    }
  }

Response 403:
  {
    "status": "error",
    "error": {
      "code": "EMAIL_NOT_VERIFIED",
      "message": "Please verify your email before logging in."
    }
  }
```

### 24.3 POST /api/v1/auth/refresh

```
Request:
  Cookie: __Host-refresh_token=<opaque>

  (No body)

Response 200:
  Set-Cookie: __Host-refresh_token=<new_opaque>; Path=/api/v1/auth; HttpOnly; Secure; SameSite=Strict; Max-Age=604800

  {
    "status": "success",
    "data": {
      "access_token": "eyJhbGciOiJSUzI1NiIs...",
      "expires_in": 900
    }
  }

Response 401:
  {
    "status": "error",
    "error": {
      "code": "TOKEN_EXPIRED",
      "message": "Refresh token has expired. Please log in again."
    }
  }

Response 401 (theft detected):
  Set-Cookie: __Host-refresh_token=; Path=/api/v1/auth; HttpOnly; Secure; SameSite=Strict; Max-Age=0

  {
    "status": "error",
    "error": {
      "code": "TOKEN_THEFT_DETECTED",
      "message": "Session has been revoked due to potential token theft. All devices have been signed out."
    }
  }
```

### 24.4 POST /api/v1/auth/logout

```
Request:
  Authorization: Bearer <access_token>
  Cookie: __Host-refresh_token=<opaque>

  (No body)

Response 200:
  Set-Cookie: __Host-refresh_token=; Path=/api/v1/auth; HttpOnly; Secure; SameSite=Strict; Max-Age=0

  {
    "status": "success",
    "data": {
      "message": "Successfully logged out."
    }
  }
```

### 24.5 POST /api/v1/auth/forgot-password

```
Request:
  Content-Type: application/json

  {
    "email": "user@example.com"
  }

Response 200:
  {
    "status": "success",
    "data": {
      "message": "If an account exists with this email, a password reset link has been sent."
    }
  }
```

### 24.6 POST /api/v1/auth/reset-password

```
Request:
  Content-Type: application/json

  {
    "token": "abc123def456...",
    "password": "NewSecureP@ss456!"
  }

Response 200:
  {
    "status": "success",
    "data": {
      "message": "Password has been reset. Please log in with your new password."
    }
  }

Response 400:
  {
    "status": "error",
    "error": {
      "code": "INVALID_RESET_TOKEN",
      "message": "Reset token is invalid or has expired."
    }
  }
```

---

## 25. Request Schemas

| Schema | Endpoint | Fields |
|---|---|---|
| RegisterRequest | POST /auth/register | email, password, display_name, locale (optional) |
| LoginRequest | POST /auth/login | email, password, device_info (optional) |
| RefreshRequest | POST /auth/refresh | (cookie only) |
| LogoutRequest | POST /auth/logout | (cookie + header) |
| ForgotPasswordRequest | POST /auth/forgot-password | email |
| ResetPasswordRequest | POST /auth/reset-password | token, password |
| ResendVerificationRequest | POST /auth/resend-verification | email |
| UpdateProfileRequest | PATCH /auth/me | display_name, avatar_url, locale (all optional) |
| RevokeSessionRequest | DELETE /auth/sessions/{id} | (path param) |

---

## 26. Response Schemas

| Schema | Fields |
|---|---|
| AuthResponse | user (UserResponse), access_token, expires_in |
| UserResponse | id, email, display_name, avatar_url, is_verified, roles, locale, created_at |
| SessionResponse | id, ip_address, user_agent, device_info, is_active, created_at, last_used_at, expires_at |
| AuditLogResponse | id, event_type, resource, resource_id, action, actor_ip, metadata, created_at |
| ErrorResponse | status, error (code, message, details[], retry_after_seconds) |
| PaginatedResponse | status, data (items[], total, page, page_size, pages) |

---

## 27. Error Responses

### 27.1 Error Code Catalog

| HTTP Status | Code | Description |
|---|---|---|
| 400 | `VALIDATION_ERROR` | Request body failed validation |
| 400 | `INVALID_RESET_TOKEN` | Password reset token expired or invalid |
| 400 | `INVALID_VERIFICATION_TOKEN` | Email verification token expired or invalid |
| 401 | `INVALID_CREDENTIALS` | Email or password is incorrect |
| 401 | `INVALID_TOKEN` | JWT is malformed, expired, or invalid signature |
| 401 | `TOKEN_EXPIRED` | Refresh token has expired |
| 401 | `TOKEN_THEFT_DETECTED` | Token reuse detected, all sessions revoked |
| 401 | `SESSION_REVOKED` | Session has been explicitly revoked |
| 403 | `EMAIL_NOT_VERIFIED` | Email verification required |
| 403 | `ACCOUNT_INACTIVE` | Account has been deactivated |
| 403 | `FORBIDDEN` | Insufficient permissions |
| 409 | `EMAIL_ALREADY_EXISTS` | Registration email conflict |
| 423 | `ACCOUNT_LOCKED` | Temporary lockout due to failed attempts |
| 429 | `RATE_LIMIT_EXCEEDED` | Too many requests |
| 500 | `INTERNAL_ERROR` | Unexpected server error |

### 27.2 Error Response Envelope

```json
{
  "status": "error",
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable description.",
    "details": [
      {
        "field": "password",
        "message": "Field-level validation message."
      }
    ],
    "retry_after_seconds": 900
  },
  "request_id": "req_abc123"
}
```

---

## 28. Validation Rules

### 28.1 Email

| Rule | Value |
|---|---|
| Format | RFC 5321 (standard email regex) |
| Max Length | 320 characters |
| Normalization | Lowercased before storage |
| Disposable domains | Blocked (100+ known disposable email domains) |
| Role-based emails | Blocked (admin@, info@, support@, etc.) |

### 28.2 Password

| Rule | Value |
|---|---|
| Min Length | 12 |
| Max Length | 128 |
| Uppercase | At least 1 (if class selected) |
| Lowercase | At least 1 (if class selected) |
| Digit | At least 1 (if class selected) |
| Special | At least 1 (if class selected) |
| Required classes | At least 3 of 4 |
| Common password | Rejected (10k+ list) |
| Pwned | Rejected (HIBP k-anonymity) |
| Reuse | No match with last 5 passwords |
| Unicode | Allowed (NFKC normalized) |
| Whitespace | Leading/trailing stripped |

### 28.3 Display Name

| Rule | Value |
|---|---|
| Min Length | 2 |
| Max Length | 255 |
| Allowed characters | Unicode letters, digits, spaces, hyphens, apostrophes |
| Profanity | Checked against profanity filter |

### 28.4 Locale

| Rule | Value |
|---|---|
| Format | IETF BCP 47 (e.g., `en-US`, `ur-PK`, `ar-SA`) |
| Supported | Restricted to platform-supported locales |

### 28.5 Device Info

| Rule | Value |
|---|---|
| Max object depth | 3 levels |
| Max keys | 10 |
| Max string length per value | 255 |

---

## 29. Sequence Diagrams

### 29.1 Registration and Login Flow

```
Client                  FastAPI                       PostgreSQL              Email Service
  │                        │                             │                        │
  │── POST /auth/register ──│                             │                        │
  │   {email, password,     │                             │                        │
  │    display_name}        │                             │                        │
  │                        │── Check email uniqueness ────│                        │
  │                        │←── OK ──────────────────────│                        │
  │                        │                             │                        │
  │                        │── Argon2 hash password       │                        │
  │                        │── INSERT user ───────────────│                        │
  │                        │←── user record ─────────────│                        │
  │                        │                             │                        │
  │                        │── Generate verification token│                        │
  │                        │── Store token hash ──────────│                        │
  │                        │── Send verification email ───│───────────────────────│
  │                        │                             │                        │
  │                        │── INSERT session ────────────│                        │
  │                        │── INSERT refresh_token ──────│                        │
  │                        │── INSERT audit_log ──────────│                        │
  │                        │                             │                        │
  │←── 201 + Set-Cookie ────│                             │                        │
  │    {access_token, user} │                             │                        │
```

### 29.2 Authenticated Request Flow

```
Client                  FastAPI                       PostgreSQL
  │                        │                             │
  │── GET /api/v1/me ──────│                             │
  │   Authorization:       │                             │
  │   Bearer <JWT>         │                             │
  │                        │                             │
  │                        │── Verify JWT signature       │
  │                        │   (RS256, jwks cache)       │
  │                        │                             │
  │                        │── Decode JWT → sub, sid     │
  │                        │                             │
  │                        │── SELECT session by sid ────│
  │                        │←── session record ──────────│
  │                        │                             │
  │                        │── Validate session active   │
  │                        │   & not expired             │
  │                        │                             │
  │                        │── UPDATE last_used_at ──────│
  │                        │                             │
  │                        │── Load user + roles +       │
  │                        │   permissions               │
  │                        │                             │
  │                        │── Evaluate permission       │
  │                        │   (user:read)               │
  │                        │                             │
  │                        │── INSERT audit_log          │
  │                        │                             │
  │←── 200 + user data ────│                             │
```

### 29.3 Token Rotation and Refresh

```
Client                  FastAPI                       PostgreSQL
  │                        │                             │
  │── POST /auth/refresh ───│                             │
  │   Cookie: __Host-      │                             │
  │   refresh_token=<rt>   │                             │
  │                        │                             │
  │                        │── SHA-256(refresh_token)    │
  │                        │                             │
  │                        │── SELECT rt by token_hash ──│
  │                        │←── refresh_token record ───│
  │                        │                             │
  │                        │── IF revoked_at IS NOT NULL │
  │                        │   → THEFT DETECTED          │
  │                        │   → Revoke ALL in family    │
  │                        │   → Revoke ALL sessions     │
  │                        │   → Return 401 + clear      │
  │                        │     cookie                  │
  │                        │                             │
  │                        │── Validate expires_at       │
  │                        │                             │
  │                        │── Generate new access token  │
  │                        │── Generate new refresh token │
  │                        │   (same family)             │
  │                        │                             │
  │                        │── INSERT new refresh_token ─│
  │                        │── UPDATE old: revoked_at ───│
  │                        │                             │
  │                        │── UPDATE session             │
  │                        │   last_used_at              │
  │                        │                             │
  │                        │── INSERT audit_log          │
  │                        │                             │
  │←── 200 + Set-Cookie ───│                             │
  │    {new_access_token}  │                             │
```

### 29.4 OAuth (Google/GitHub) Flow

```
Client               FastAPI                    OAuth Provider          PostgreSQL
  │                     │                            │                     │
  │── GET /auth/oauth/  │                            │                     │
  │    google           │                            │                     │
  │                     │── Generate state + store    │                     │
  │                     │── PKCE code_verifier +     │                     │
  │                     │   code_challenge           │                     │
  │                     │                            │                     │
  │←── 302 Redirect ────│                            │                     │
  │    to Google Auth   │                            │                     │
  │     URL             │                            │                     │
  │                     │                            │                     │
  │── (Browser          │                            │                     │
  │    redirects to     │                            │                     │
  │    Google) ─────────┼────────────────────────────│                     │
  │                     │                            │                     │
  │                     │←── Authorization Code ─────│                     │
  │                     │    + state                 │                     │
  │                     │                            │                     │
  │── GET /auth/oauth/  │                            │                     │
  │    google/callback  │                            │                     │
  │    ?code=&state=    │                            │                     │
  │                     │                            │                     │
  │                     │── Validate state           │                     │
  │                     │── Exchange code for tokens ─│                     │
  │                     │←── ID token, access token ─│                     │
  │                     │                            │                     │
  │                     │── Fetch user info from     │                     │
  │                     │    Google API              │                     │
  │                     │                            │                     │
  │                     │── Lookup user by email ────│                     │
  │                     │←── user or NULL ───────────│                     │
  │                     │                            │                     │
  │                     │── If new: INSERT user ─────│                     │
  │                     │── If Clerk: upsert Clerk   │                     │
  │                     │                            │                     │
  │                     │── INSERT session ──────────│                     │
  │                     │── INSERT refresh_token ────│                     │
  │                     │                            │                     │
  │←── 302 Redirect ────│                            │                     │
  │    to frontend      │                            │                     │
  │    Set-Cookie:      │                            │                     │
  │    __Host-          │                            │                     │
  │    refresh_token    │                            │                     │
```

### 29.5 Logout Flow

```
Client                  FastAPI                       PostgreSQL
  │                        │                             │
  │── POST /auth/logout ────│                             │
  │   Authorization:        │                             │
  │   Bearer <access_token> │                             │
  │   Cookie: __Host-       │                             │
  │   refresh_token=<rt>    │                             │
  │                        │                             │
  │                        │── Verify JWT                │
  │                        │── Extract session_id from   │
  │                        │   JWT claims                │
  │                        │                             │
  │                        │── SHA-256(refresh_token)    │
  │                        │── Lookup refresh_token ─────│
  │                        │                             │
  │                        │── UPDATE session:            │
  │                        │   is_active = FALSE ────────│
  │                        │                             │
  │                        │── UPDATE refresh_token:      │
  │                        │   revoked_at = now() ───────│
  │                        │                             │
  │                        │── INSERT audit_log          │
  │                        │   (auth.logout)             │
  │                        │                             │
  │←── 200 + Clear-Cookie ─│                             │
```

---

## 30. Authentication Flow

### 30.1 Standard Email/Password

```
Step 1:  Client sends POST /auth/login with email + password
Step 2:  Server rate-checks IP and email (max 5 attempts/15 min)
Step 3:  Server looks up user by email (404 → 401, generic message)
Step 4:  Server verifies password_hash with Argon2id (fail → increment counter)
Step 5:  Server checks is_verified (false → 403)
Step 6:  Server checks is_active (false → 403)
Step 7:  Server checks account lockout (locked → 423)
Step 8:  Server generates opaque session token (32 bytes)
Step 9:  Server hashes session token with SHA-256
Step 10: Server stores session record in PostgreSQL
Step 11: Server generates opaque refresh token (32 bytes)
Step 12: Server hashes refresh token with SHA-256
Step 13: Server stores refresh token with family identifier
Step 14: Server generates JWT access token (RS256, 15 min expiry)
Step 15: Server sets __Host-refresh_token cookie (httpOnly, Secure, SameSite=Strict)
Step 16: Server resets failed attempt counter
Step 17: Server logs audit event (auth.login)
Step 18: Server updates last_login_at
Step 19: Client receives access_token in body, refresh_token in cookie
Step 20: Client stores access_token in memory (never localStorage)
Step 21: Client attaches Authorization: Bearer <token> to all requests
```

### 30.2 Hybrid Clerk Flow

```
Step 1:  Clerk handles primary authentication (Google, GitHub, magic link)
Step 2:  Clerk issues its own session token
Step 3:  Client sends Clerk session token to POST /api/v1/auth/clerk/sync
Step 4:  Server verifies Clerk session via Clerk API/SDK (getUser)
Step 5:  Server looks up or creates local user by clerk_id
Step 6:  Server creates local session and refresh token (same as standard flow)
Step 7:  Server issues platform JWT (short-lived, for internal API consumption)
Step 8:  Client uses platform JWT for all subsequent API calls
```

---

## 31. Logout Flow

```
Step 1:  Client sends POST /auth/logout with access_token + refresh_token cookie
Step 2:  Server validates access token (signature, expiry, session binding)
Step 3:  Server extracts session_id from JWT claims (sid)
Step 4:  Server looks up refresh token by hash from cookie
Step 5:  Server sets session.is_active = FALSE
Step 6:  Server sets refresh_token.revoked_at = now()
Step 7:  Server clears __Host-refresh_token cookie (Max-Age=0)
Step 8:  Server logs audit event (auth.logout)
Step 9:  Server responds 200
Step 10: Client clears access_token from memory
Step 11: Client redirects to login page
```

### 31.1 Global Logout

```
DELETE /api/v1/auth/sessions
Authorization: Bearer <access_token>

→ Revokes ALL sessions for the user except the current one.
→ Revokes ALL associated refresh tokens.
→ Returns 200 with count of revoked sessions.
```

---

## 32. Token Rotation

### 32.1 Rotation Policy

| Token | Rotation Trigger | Mechanism |
|---|---|---|
| Access token | Every 15 minutes | Client calls POST /auth/refresh |
| Refresh token | Every use | Old token revoked, new token issued (same family) |
| Session token | Not rotated | Remains until explicit revocation or expiration |
| JWT signing key | Every 30 days | New key pair generated; JWKS updated; old key still valid for 24h |

### 32.2 Rotation Chain

```
refresh_token_v1 (family: abc123)
  ├── Used at T+5min → revoked
  ├── refresh_token_v2 (family: abc123)
  │     ├── Used at T+10min → revoked
  │     └── refresh_token_v3 (family: abc123)
  │           └── ... continues until expiry or logout
  │
  └── If v1 reused after revocation → THEFT DETECTED
        → Family abc123: ALL revoked
        → Session: ALL deactivated
```

---

## 33. Token Expiration

### 33.1 Lifetime Table

| Token Type | Lifetime | Renewal | Post-Expiry |
|---|---|---|---|
| Access Token (JWT) | 15 minutes | Automatic via refresh | Forbidden, 401 |
| Refresh Token | 7 days | Rotated on use | Forced re-login |
| Session | 7 days (sliding) | Extended on active use | Cleanup job deletes |
| Email Verification | 24 hours | Manual resend (max 5) | New token required |
| Password Reset | 1 hour | Manual resend (max 3) | New token required |
| OAuth State | 10 minutes | N/A | New OAuth flow required |

### 33.2 Session Sliding Window

Each authenticated request extends `sessions.expires_at` by 24 hours from the current time, capped at 7 days from creation.

### 33.3 Cleanup Jobs

| Job | Schedule | Action |
|---|---|---|
| Expired session cleanup | Every hour | DELETE expired sessions |
| Orphaned token cleanup | Every hour | DELETE refresh_tokens with expired sessions |
| Audit log archive | Daily at 00:00 UTC | MOVE records >90 days to partitioned archive |
| Soft-delete purge | Weekly | DELETE users with deleted_at >90 days |

---

## 34. Middleware

### 34.1 Backend Middleware Stack

```
Request
  │
  ├── 1. Rate Limiting Middleware
  │     Token bucket per IP (100 req/min)
  │     Token bucket per user (500 req/min, if authenticated)
  │     → 429 if exceeded
  │
  ├── 2. Request ID Middleware
  │     Generates or propagates X-Request-ID header
  │     Attached to all logs and audit records
  │
  ├── 3. CORS Middleware
  │     Validates Origin against allowlist
  │     Sets Access-Control-* headers
  │
  ├── 4. Security Headers Middleware
  │     Strict-Transport-Security: max-age=63072000
  │     Content-Security-Policy: default-src 'self'
  │     X-Content-Type-Options: nosniff
  │     X-Frame-Options: DENY
  │     Referrer-Policy: strict-origin-when-cross-origin
  │
  └── 5. Authentication Middleware
        Attempts to extract JWT from Authorization header
        Attempts to extract refresh_token from cookie
        Does NOT block unauthenticated requests
        Sets request.state.user = User | None
        Sets request.state.session = Session | None
```

### 34.2 Route-Level Middleware (FastAPI Dependencies)

```
Public Routes:
  No dependencies

Authenticated Routes:
  Depends(get_current_user)
  → Validates JWT
  → Loads session
  → Validates session active
  → Returns User + Session

Authorized Routes:
  Depends(get_current_user)
  Depends(require_permission("resource:action"))
  → All of the above
  → Evaluates RBAC
  → Returns User + Session

Admin Routes:
  Depends(get_current_user)
  Depends(require_role("admin"))
  → All of the above
  → Checks role
  → Returns User + Session
```

### 34.3 Frontend Middleware

```typescript
// Next.js middleware.ts — Pseudocode behavior

// 1. Define route protection map
const protectedRoutes = [
  { pattern: '/dashboard/:path*', roles: ['*'] },
  { pattern: '/admin/:path*', roles: ['admin', 'superadmin'] },
  { pattern: '/settings/:path*', roles: ['*'] },
]

// 2. Define auth routes (never protected)
const authRoutes = ['/login', '/register', '/forgot-password',
                    '/reset-password', '/verify']

// 3. For each request:
//    a. Read __Host-refresh_token cookie
//    b. Decode JWT from in-memory store (if available in header)
//    c. If route is protected and no valid session:
//       → Redirect to /login?redirect=<path>
//    d. If route is auth route and valid session exists:
//       → Redirect to /dashboard
//    e. If route requires specific role and user lacks it:
//       → Redirect to /403
```

---

## 35. Dependency Injection

### 35.1 FastAPI Dependency Graph

```python
# Dependency hierarchy:

# Level 0: No auth
Router Dependency: None

# Level 1: Current user
get_current_user
  ├── Extracts Authorization: Bearer <token>
  ├── Decodes JWT (RS256, validates signature, exp, iss, aud)
  ├── Loads User from DB by sub (UUID)
  ├── Validates is_active and deleted_at IS NULL
  └── Returns User model

# Level 2: Valid session
get_valid_session
  └── Depends on: get_current_user
  ├── Extracts session_id from JWT sid claim
  ├── Loads Session from DB
  ├── Validates is_active = TRUE
  ├── Validates expires_at > now()
  ├── Updates last_used_at
  └── Returns Session model

# Level 3: Permission check
require_permission(resource: str, action: str)
  └── Depends on: get_current_user, get_valid_session
  ├── If user.is_superuser → GRANT
  ├── Loads all user roles + permissions
  ├── Evaluates resource:action against permissions
  ├── Hits cache if available
  ├── Logs audit event on DENY
  └── Raises 403 on failure

# Level 4: Role check
require_role(role_name: str)
  └── Depends on: get_current_user
  ├── Checks if user has role
  ├── Logs audit event on DENY
  └── Raises 403 on failure
```

### 35.2 Cache Strategy

| Cache | Key | TTL | Invalidation |
|---|---|---|---|
| JWKS public keys | `jwks:{kid}` | 1 hour | On key rotation webhook |
| User permissions | `perms:{user_id}` | 5 minutes | On role assignment change |
| User roles | `roles:{user_id}` | 5 minutes | On role assignment change |
| Rate limit counters | `ratelimit:{ip}:{endpoint}` | Sliding window | Automatic expiry |
| Account lockout | `lockout:{email}` | 15 minutes | Automatic expiry |

---

## 36. Testing Strategy

### 36.1 Test Pyramid

```
         /\
        /  \
       / E2E \          → 3 critical flows (login, refresh, RBAC)
      /────────\
     /          \
    / Integration \     → 15 service-level tests (token rotation, OAuth,
   /──────────────\        password reset, session management, audit)
  /                \
 /   Unit Tests     \   → 40+ tests (password hashing, validation rules,
/────────────────────\      permission evaluation, token serialization)
```

### 36.2 Unit Tests

| Category | Test Cases |
|---|---|
| Password | Hash verification, policy validation, common password rejection, pwned check mock |
| Token | JWT encode/decode, claim validation, signature verification, kid matching |
| Permission | CRUD hierarchy, wildcard matching, deny priority, superuser bypass |
| Validation | Email format, password rules, display name sanitization, locale validation |
| Rate Limiting | Token bucket algorithm, counter increment, window sliding, overflow |

### 36.3 Integration Tests

| Category | Test Cases |
|---|---|
| Registration | Full flow, duplicate email, weak password, email verification trigger |
| Login | Valid credentials, wrong password, unverified email, locked account |
| Token Refresh | Valid rotation, expired token, stolen token (family reuse), concurrent refresh |
| OAuth | Google callback, GitHub callback, state validation, PKCE verification |
| Password Reset | Request flow, token expiration, reuse prevention, session revocation |
| Session Management | Create list revoke, session limit enforcement, inactivity expiration |
| RBAC | Role assignment, permission grant/deny, admin override, cascading role removal |
| Clerk Integration | Webhook signature, user sync, session sync, webhook retry |
| Audit Logging | Event creation, proper metadata, retention enforcement |

### 36.4 E2E Tests

| Test | Description |
|---|---|
| Happy path login | Register → verify → login → access protected resource → refresh → logout |
| Full OAuth flow | Google OAuth → callback → create user → access resource → revoke session |
| Token theft scenario | Login → steal refresh token → use it → get revoked → re-authenticate |

### 36.5 Security Tests

| Test | Description |
|---|---|
| Timing attack | Password comparison timing must be constant (Argon2 is constant-time) |
| Enumeration | Forgot-password, register, login must not reveal user existence |
| JWT none attack | Algorithm must be pinned to RS256; `alg: none` MUST be rejected |
| SQL injection | All inputs parameterized via SQLModel |
| XSS | All user inputs sanitized on output |
| CSRF | OAuth state parameter + SameSite cookie validation |
| Brute force | Rate limiting + account lockout verified under load |

### 36.6 Test Fixtures

| Fixture | Scope | Description |
|---|---|---|
| `test_db` | Session | Fresh PostgreSQL database with Alembic migrations |
| `test_client` | Function | FastAPI TestClient with auth headers |
| `default_user` | Function | Pre-created verified user with viewer role |
| `admin_user` | Function | Pre-created admin user |
| `oauth_mock` | Function | Mocked Google/GitHub OAuth responses |
| `clerk_mock` | Function | Mocked Clerk API responses |
| `jwks_mock` | Function | Test RSA key pair |

### 36.7 Performance Tests

| Test | Target | Threshold |
|---|---|---|
| Login RPS | 1000 concurrent users | P95 < 500ms |
| Token refresh RPS | 1000 concurrent users | P95 < 200ms |
| Permission evaluation | 1000 evaluations/second | Cache hit < 5ms, miss < 50ms |
| Argon2 verification | Single operation | < 1 second |

---

## 37. Production Folder Structure

```
apps/api/
└── app/
    ├── __init__.py
    ├── main.py                          # FastAPI app factory
    ├── core/
    │   ├── __init__.py
    │   ├── config.py                    # Pydantic Settings, env loading
    │   ├── security.py                  # Argon2, JWT helpers
    │   ├── exceptions.py                # Custom exception classes
    │   ├── logging.py                   # Structured logging config
    │   ├── cache.py                     # Redis/ValKey client
    │   └── metrics.py                   # Prometheus metrics
    ├── db/
    │   ├── __init__.py
    │   ├── base.py                      # SQLModel declarative base
    │   ├── session.py                   # Async session factory
    │   └── migrations/                  # Alembic migration files
    │       ├── versions/
    │       ├── env.py
    │       └── alembic.ini
    ├── models/
    │   ├── __init__.py
    │   ├── user.py
    │   ├── session.py
    │   ├── refresh_token.py
    │   ├── role.py
    │   ├── permission.py
    │   ├── audit_log.py
    │   └── password_history.py
    ├── auth/
    │   ├── __init__.py
    │   ├── router.py                    # All auth route registrations
    │   ├── deps.py                      # DI: get_current_user, require_permission, etc.
    │   ├── middleware.py                # Auth middleware functions
    │   ├── schemas/
    │   │   ├── __init__.py
    │   │   ├── request.py               # Pydantic request models
    │   │   └── response.py              # Pydantic response models
    │   ├── service/
    │   │   ├── __init__.py
    │   │   ├── authentication.py        # Login, register, verify
    │   │   ├── authorization.py         # RBAC evaluation
    │   │   ├── password.py              # Argon2 hash/verify, policy
    │   │   ├── token.py                 # JWT create/verify, refresh rotation
    │   │   ├── session.py               # CRUD, limits, sliding expiration
    │   │   ├── verification.py          # Email verify tokens
    │   │   └── oauth.py                 # Google/GitHub OAuth flows
    │   ├── clerk/
    │   │   ├── __init__.py
    │   │   ├── client.py                # Clerk SDK wrapper
    │   │   └── webhooks.py              # Svix verification, event handlers
    │   └── rate_limit.py                # Token bucket implementation
    ├── api/
    │   └── v1/
    │       ├── __init__.py
    │       ├── auth.py                  # Auth endpoint implementations
    │       └── admin.py                 # Admin endpoint implementations
    ├── tasks/                           # Background task handlers
    │   ├── __init__.py
    │   ├── session_cleanup.py
    │   ├── audit_archive.py
    │   └── email.py
    └── tests/
        ├── __init__.py
        ├── conftest.py                  # Fixtures, test DB setup
        ├── auth/
        │   ├── test_authentication.py
        │   ├── test_authorization.py
        │   ├── test_oauth.py
        │   ├── test_tokens.py
        │   ├── test_clerk.py
        │   └── test_rate_limit.py
        ├── models/
        │   ├── test_user.py
        │   └── test_session.py
        ├── security/
        │   ├── test_timing.py
        │   ├── test_enumeration.py
        │   └── test_injection.py
        └── e2e/
            ├── test_happy_path.py
            ├── test_oauth_flow.py
            └── test_theft_scenario.py
```