# Authentication Module — Implementation Plan

> **Status:** Implementation v1.0  
> **Stack:** FastAPI · SQLModel · Python 3.13+ · PostgreSQL (Neon) · JWT (RS256) · Clerk · Argon2id  
> **Base Spec:** `docs/architecture/auth-module.md`  
> **DB Spec:** `docs/architecture/database-architecture.md`

---

## 1. Exact Folder Structure

```
apps/api/
└── app/
    ├── __init__.py
    │
    ├── main.py                              # FastAPI app factory, middleware registration
    │
    ├── core/
    │   ├── __init__.py
    │   ├── config.py                        # Pydantic Settings: 60+ env vars
    │   ├── security.py                      # JWKS loader, RSA key pair, Argon2 context
    │   ├── exceptions.py                    # AppException, error_code registry
    │   ├── logging.py                       # structlog config, request_id injection
    │   └── cache.py                         # Redis client, cache decorators
    │
    ├── db/
    │   ├── __init__.py
    │   ├── base.py                          # SQLModel declarative base, TimestampMixin
    │   ├── session.py                       # async engine, sessionmaker, get_session dependency
    │   └── migrations/
    │       ├── env.py                       # Alembic async env, target_metadata
    │       ├── alembic.ini                  # DB URL from Settings, template
    │       └── versions/
    │           ├── 0001_create_users_table.py
    │           ├── 0002_create_roles_and_permissions.py
    │           ├── 0003_create_session_table.py
    │           ├── 0004_create_refresh_tokens.py
    │           ├── 0005_create_audit_logs_partitioned.py
    │           ├── 0006_create_verification_tokens.py
    │           ├── 0007_create_password_history.py
    │           ├── 0008_seed_system_roles.py
    │           └── 0009_seed_system_permissions.py
    │
    ├── models/
    │   ├── __init__.py
    │   ├── user.py                          # User SQLModel
    │   ├── session.py                       # Session SQLModel
    │   ├── refresh_token.py                 # RefreshToken SQLModel
    │   ├── role.py                          # Role + UserRoleLink SQLModel
    │   ├── permission.py                    # Permission + RolePermissionLink SQLModel
    │   ├── audit_log.py                     # AuditLog SQLModel
    │   ├── verification_token.py            # VerificationToken, PasswordResetToken
    │   └── password_history.py              # PasswordHistory SQLModel
    │
    ├── auth/
    │   ├── __init__.py
    │   ├── router.py                        # APIRouter(prefix="/api/v1/auth")
    │   ├── deps.py                          # get_current_user, get_valid_session,
    │   │                                    # require_permission, require_role
    │   ├── middleware.py                    # AuthContextMiddleware
    │   ├── rate_limit.py                    # TokenBucketRateLimiter
    │   ├── audit.py                         # AuditLogger
    │   ├── schemas/
    │   │   ├── __init__.py
    │   │   └── models.py                    # 20+ Pydantic request/response models
    │   ├── service/
    │   │   ├── __init__.py
    │   │   ├── authentication.py            # register, login, logout
    │   │   ├── authorization.py             # RBAC evaluation engine
    │   │   ├── password.py                  # Argon2 hashing, policy validation
    │   │   ├── token.py                     # JWT create/verify, refresh rotation
    │   │   ├── session.py                   # session CRUD, limits, sliding window
    │   │   ├── verification.py              # email verify, password reset tokens
    │   │   └── oauth.py                     # Google, GitHub OAuth flows
    │   └── clerk/
    │       ├── __init__.py
    │       ├── client.py                    # Clerk SDK wrapper, session verification
    │       └── webhooks.py                  # Svix verification, event dispatcher
    │
    ├── api/
    │   └── v1/
    │       ├── __init__.py
    │       ├── router.py                    # includes auth.router
    │       ├── auth.py                      # endpoint handler functions
    │       └── admin.py                     # admin CRUD endpoints
    │
    ├── tasks/
    │   ├── __init__.py
    │   ├── session_cleanup.py               # hourly: delete expired sessions
    │   ├── audit_archive.py                 # daily: partition archive
    │   └── email.py                         # SendGrid / SMTP email sender
    │
    └── tests/
        ├── __init__.py
        ├── conftest.py                      # async fixtures, test DB, HTTP client
        ├── auth/
        │   ├── test_authentication.py       # 12 test functions
        │   ├── test_authorization.py        # 10 test functions
        │   ├── test_oauth.py                # 6 test functions
        │   ├── test_tokens.py               # 8 test functions
        │   ├── test_clerk.py                # 6 test functions
        │   └── test_rate_limit.py           # 4 test functions
        ├── models/
        │   ├── test_user.py                 # 4 test functions
        │   └── test_session.py              # 4 test functions
        ├── security/
        │   ├── test_timing.py               # 2 test functions
        │   ├── test_enumeration.py           # 3 test functions
        │   └── test_injection.py            # 3 test functions
        └── e2e/
            ├── test_happy_path.py           # 3 test functions
            ├── test_oauth_flow.py           # 2 test functions
            └── test_theft_scenario.py       # 2 test functions
```

### 1.1 File Count Summary

| Directory | Files | Lines (estimate) |
|---|---|---|
| `core/` | 5 | 650 |
| `db/` | 4 + 9 migrations | 720 |
| `models/` | 8 | 480 |
| `auth/schemas/` | 2 | 320 |
| `auth/service/` | 7 | 1,200 |
| `auth/clerk/` | 3 | 350 |
| `auth/` (root) | 5 | 600 |
| `api/v1/` | 3 | 450 |
| `tasks/` | 3 | 300 |
| `tests/` | 14 | 2,400 |
| **Total** | **56 files** | **~7,500 lines** |

---

## 2. SQLModel Models

### 2.1 Base Mixins

| Mixin | Fields | Used By |
|---|---|---|
| `TimestampMixin` | `created_at: datetime`, `updated_at: datetime` | All models |
| `SoftDeleteMixin` | `deleted_at: Optional[datetime]` | User |
| `UUIDPrimaryKeyMixin` | `id: uuid.UUID` (default=uuid7) | All models |

### 2.2 User

| Field | SQLModel Type | SQL Type | Constraints |
|---|---|---|---|
| `id` | `uuid.UUID` | `UUID` | PK, default `uuid7()` |
| `email` | `str` | `VARCHAR(320)` | NOT NULL, UNIQUE index (partial: WHERE deleted_at IS NULL) |
| `password_hash` | `Optional[str]` | `TEXT` | NULLABLE |
| `display_name` | `str` | `VARCHAR(255)` | NOT NULL |
| `avatar_url` | `Optional[str]` | `TEXT` | NULLABLE |
| `is_verified` | `bool` | `BOOLEAN` | NOT NULL, DEFAULT FALSE |
| `is_active` | `bool` | `BOOLEAN` | NOT NULL, DEFAULT TRUE |
| `is_superuser` | `bool` | `BOOLEAN` | NOT NULL, DEFAULT FALSE |
| `locale` | `str` | `VARCHAR(10)` | NOT NULL, DEFAULT 'en' |
| `clerk_id` | `Optional[str]` | `VARCHAR(255)` | UNIQUE index (partial), NULLABLE |
| `last_login_at` | `Optional[datetime]` | `TIMESTAMPTZ` | NULLABLE |
| `failed_login_attempts` | `int` | `SMALLINT` | NOT NULL, DEFAULT 0 |
| `locked_until` | `Optional[datetime]` | `TIMESTAMPTZ` | NULLABLE |
| `created_at` | `datetime` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() |
| `updated_at` | `datetime` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() |
| `deleted_at` | `Optional[datetime]` | `TIMESTAMPTZ` | NULLABLE |

**Relationships:**
- `sessions: List[Session]` — back_populates user
- `refresh_tokens: List[RefreshToken]` — back_populates user
- `roles: List[Role]` — many-to-many via UserRoleLink
- `audit_logs: List[AuditLog]` — back_populates user

**Validators (SQLModel @field_validator):**
- `email` → strip, lowercase, regex `^[^@]+@[^@]+\.[^@]+$`
- `display_name` → strip, min 2 chars, max 255

**Table kwargs:**
- `table_name = "users"`

### 2.3 Session

| Field | SQLModel Type | SQL Type | Constraints |
|---|---|---|---|
| `id` | `uuid.UUID` | `UUID` | PK |
| `user_id` | `uuid.UUID` | `UUID` | FK → users.id, NOT NULL |
| `token_hash` | `str` | `TEXT` | NOT NULL, UNIQUE |
| `ip_address` | `str` | `INET` | NOT NULL |
| `user_agent` | `str` | `TEXT` | NOT NULL |
| `device_info` | `dict` | `JSONB` | NOT NULL, DEFAULT {} |
| `is_active` | `bool` | `BOOLEAN` | NOT NULL, DEFAULT TRUE |
| `expires_at` | `datetime` | `TIMESTAMPTZ` | NOT NULL |
| `last_used_at` | `datetime` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() |
| `created_at` | `datetime` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() |

**Relationships:**
- `user: User` — back_populates sessions
- `refresh_tokens: List[RefreshToken]` — back_populates session

**Indexes:** `(user_id)` where is_active, `(token_hash)` unique, `(expires_at)` where is_active

### 2.4 RefreshToken

| Field | SQLModel Type | SQL Type | Constraints |
|---|---|---|---|
| `id` | `uuid.UUID` | `UUID` | PK |
| `user_id` | `uuid.UUID` | `UUID` | FK → users.id, NOT NULL |
| `session_id` | `uuid.UUID` | `UUID` | FK → sessions.id, NOT NULL |
| `token_hash` | `str` | `TEXT` | NOT NULL, UNIQUE |
| `family` | `str` | `VARCHAR(64)` | NOT NULL |
| `metadata` | `dict` | `JSONB` | NOT NULL, DEFAULT {} |
| `expires_at` | `datetime` | `TIMESTAMPTZ` | NOT NULL |
| `revoked_at` | `Optional[datetime]` | `TIMESTAMPTZ` | NULLABLE |
| `created_at` | `datetime` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() |

**Relationships:**
- `user: User` — back_populates refresh_tokens
- `session: Session` — back_populates refresh_tokens

**Indexes:** `(user_id)` where revoked IS NULL, `(session_id)` where revoked IS NULL, `(token_hash)` unique, `(family)` btree

### 2.5 Role

| Field | SQLModel Type | SQL Type | Constraints |
|---|---|---|---|
| `id` | `uuid.UUID` | `UUID` | PK |
| `name` | `str` | `VARCHAR(100)` | NOT NULL, UNIQUE |
| `description` | `Optional[str]` | `TEXT` | NULLABLE |
| `is_system` | `bool` | `BOOLEAN` | NOT NULL, DEFAULT FALSE |
| `created_at` | `datetime` | `TIMESTAMPTZ` | NOT NULL |
| `updated_at` | `datetime` | `TIMESTAMPTZ` | NOT NULL |

**Relationships:**
- `users: List[User]` — many-to-many via UserRoleLink
- `permissions: List[Permission]` — many-to-many via RolePermissionLink

### 2.6 UserRoleLink (Junction)

| Field | Type | Constraints |
|---|---|---|
| `user_id` | `uuid.UUID` | FK → users.id, PK composite |
| `role_id` | `uuid.UUID` | FK → roles.id, PK composite |

**Table kwargs:** `table_name = "user_roles"`

### 2.7 Permission

| Field | SQLModel Type | SQL Type | Constraints |
|---|---|---|---|
| `id` | `uuid.UUID` | `UUID` | PK |
| `resource` | `str` | `VARCHAR(255)` | NOT NULL |
| `action` | `str` | `VARCHAR(100)` | NOT NULL |
| `description` | `Optional[str]` | `TEXT` | NULLABLE |
| `is_system` | `bool` | `BOOLEAN` | NOT NULL, DEFAULT FALSE |
| `created_at` | `datetime` | `TIMESTAMPTZ` | NOT NULL |

**Index:** UNIQUE `(resource, action)`

### 2.8 RolePermissionLink (Junction)

| Field | Type | Constraints |
|---|---|---|
| `role_id` | `uuid.UUID` | FK → roles.id, PK composite |
| `permission_id` | `uuid.UUID` | FK → permissions.id, PK composite |

**Table kwargs:** `table_name = "role_permissions"`

### 2.9 AuditLog

| Field | SQLModel Type | SQL Type | Constraints |
|---|---|---|---|
| `id` | `uuid.UUID` | `UUID` | PK |
| `user_id` | `uuid.UUID` | `UUID` | FK → users.id, NOT NULL |
| `session_id` | `Optional[uuid.UUID]` | `UUID` | FK → sessions.id, NULLABLE |
| `event_type` | `str` | `VARCHAR(50)` | NOT NULL |
| `resource` | `str` | `VARCHAR(255)` | NOT NULL |
| `resource_id` | `Optional[str]` | `VARCHAR(255)` | NULLABLE |
| `action` | `str` | `VARCHAR(100)` | NOT NULL |
| `actor_ip` | `str` | `INET` | NOT NULL |
| `actor_ua` | `str` | `TEXT` | NOT NULL |
| `metadata` | `dict` | `JSONB` | NOT NULL, DEFAULT {} |
| `created_at` | `datetime` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() |

**Partitioning:** Range by `created_at` monthly. Child tables: `audit_logs_2026_07`, etc.

### 2.10 VerificationToken

| Field | Type | Constraints |
|---|---|---|
| `id` | `uuid.UUID` | PK |
| `user_id` | `uuid.UUID` | FK → users.id, NOT NULL |
| `token_hash` | `str` | NOT NULL, UNIQUE |
| `purpose` | `str` | NOT NULL — `email_verification`, `password_reset` |
| `expires_at` | `datetime` | NOT NULL |
| `used_at` | `Optional[datetime]` | NULLABLE |
| `created_at` | `datetime` | NOT NULL |

### 2.11 PasswordHistory

| Field | Type | Constraints |
|---|---|---|
| `id` | `uuid.UUID` | PK |
| `user_id` | `uuid.UUID` | FK → users.id, NOT NULL |
| `password_hash` | `str` | NOT NULL |
| `created_at` | `datetime` | NOT NULL |

---

## 3. Alembic Migrations

### 3.1 Migration Sequence

| # | Migration | Dependencies | Operation |
|---|---|---|---|
| 0001 | `create_users_table` | — | CREATE TABLE users, indexes, CHECK constraints |
| 0002 | `create_roles_and_permissions` | 0001 | CREATE roles, permissions, user_roles, role_permissions |
| 0003 | `create_session_table` | 0001 | CREATE sessions table, indexes |
| 0004 | `create_refresh_tokens` | 0001, 0003 | CREATE refresh_tokens, indexes |
| 0005 | `create_audit_logs_partitioned` | 0001, 0003 | CREATE audit_logs parent + partitions, indexes |
| 0006 | `create_verification_tokens` | 0001 | CREATE verification_tokens table |
| 0007 | `create_password_history` | 0001 | CREATE password_history table |
| 0008 | `seed_system_roles` | 0002 | INSERT superadmin, admin, editor, viewer |
| 0009 | `seed_system_permissions` | 0002 | INSERT base permissions, assign to roles |

### 3.2 Migration 0001 — users

```
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_uuidv7;

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    email           VARCHAR(320) NOT NULL,
    password_hash   TEXT,
    display_name    VARCHAR(255) NOT NULL,
    avatar_url      TEXT,
    is_verified     BOOLEAN NOT NULL DEFAULT FALSE,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    is_superuser    BOOLEAN NOT NULL DEFAULT FALSE,
    locale          VARCHAR(10) NOT NULL DEFAULT 'en',
    clerk_id        VARCHAR(255),
    last_login_at   TIMESTAMPTZ,
    failed_login_attempts SMALLINT NOT NULL DEFAULT 0,
    locked_until    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ
);

CREATE UNIQUE INDEX idx_users_email ON users(email) WHERE deleted_at IS NULL;
CREATE UNIQUE INDEX idx_users_clerk_id ON users(clerk_id) WHERE clerk_id IS NOT NULL AND deleted_at IS NULL;
CREATE INDEX idx_users_active ON users(is_active, deleted_at);
CREATE INDEX idx_users_locked ON users(locked_until) WHERE locked_until IS NOT NULL;

ALTER TABLE users ADD CONSTRAINT ck_users_display_name_length CHECK (length(display_name) >= 2);
```

### 3.3 Migration 0002 — roles + permissions

```
CREATE TABLE roles (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    name        VARCHAR(100) NOT NULL,
    description TEXT,
    is_system   BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX idx_roles_name ON roles(name);

CREATE TABLE permissions (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    resource    VARCHAR(255) NOT NULL,
    action      VARCHAR(100) NOT NULL,
    description TEXT,
    is_system   BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX idx_permissions_resource_action ON permissions(resource, action);

CREATE TABLE user_roles (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE RESTRICT,
    PRIMARY KEY (user_id, role_id)
);

CREATE TABLE role_permissions (
    role_id       UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE RESTRICT,
    PRIMARY KEY (role_id, permission_id)
);
```

### 3.4 Migration 0003 — sessions

```
CREATE TABLE sessions (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash    TEXT NOT NULL,
    ip_address    INET NOT NULL,
    user_agent    TEXT NOT NULL,
    device_info   JSONB NOT NULL DEFAULT '{}',
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    expires_at    TIMESTAMPTZ NOT NULL,
    last_used_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX idx_sessions_token_hash ON sessions(token_hash);
CREATE INDEX idx_sessions_user_id ON sessions(user_id) WHERE is_active = TRUE;
CREATE INDEX idx_sessions_expires ON sessions(expires_at) WHERE is_active = TRUE;
ALTER TABLE sessions ADD CONSTRAINT ck_sessions_expires_future CHECK (expires_at > created_at);
```

### 3.5 Migration 0004 — refresh_tokens

```
CREATE TABLE refresh_tokens (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id  UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    token_hash  TEXT NOT NULL,
    family      VARCHAR(64) NOT NULL,
    metadata    JSONB NOT NULL DEFAULT '{}',
    expires_at  TIMESTAMPTZ NOT NULL,
    revoked_at  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX idx_rt_token_hash ON refresh_tokens(token_hash);
CREATE INDEX idx_rt_user_id ON refresh_tokens(user_id) WHERE revoked_at IS NULL;
CREATE INDEX idx_rt_session_id ON refresh_tokens(session_id) WHERE revoked_at IS NULL;
CREATE INDEX idx_rt_family ON refresh_tokens(family);
ALTER TABLE refresh_tokens ADD CONSTRAINT ck_rt_expires_future CHECK (expires_at > created_at);
```

### 3.6 Migration 0005 — audit_logs (partitioned)

```
CREATE TABLE audit_logs (
    id          UUID NOT NULL DEFAULT uuid_generate_v7(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE SET NULL,
    session_id  UUID REFERENCES sessions(id) ON DELETE SET NULL,
    event_type  VARCHAR(50) NOT NULL,
    resource    VARCHAR(255) NOT NULL,
    resource_id VARCHAR(255),
    action      VARCHAR(100) NOT NULL,
    actor_ip    INET NOT NULL,
    actor_ua    TEXT NOT NULL,
    metadata    JSONB NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

CREATE TABLE audit_logs_2026_07 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-07-01') TO ('2026-08-01');
CREATE TABLE audit_logs_default PARTITION OF audit_logs DEFAULT;

CREATE INDEX idx_audit_created ON audit_logs(created_at DESC);
CREATE INDEX idx_audit_user ON audit_logs(user_id, created_at DESC);
CREATE INDEX idx_audit_event ON audit_logs(event_type, created_at DESC);
CREATE INDEX idx_audit_resource ON audit_logs(resource, resource_id);
```

### 3.7 Migration 0006 — verification_tokens

```
CREATE TABLE verification_tokens (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  TEXT NOT NULL,
    purpose     VARCHAR(50) NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL,
    used_at     TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX idx_vt_token_hash ON verification_tokens(token_hash);
CREATE INDEX idx_vt_user_purpose ON verification_tokens(user_id, purpose);
ALTER TABLE verification_tokens ADD CONSTRAINT ck_vt_purpose CHECK (purpose IN ('email_verification', 'password_reset'));
```

### 3.8 Migration 0007 — password_history

```
CREATE TABLE password_history (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    user_id        UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    password_hash  TEXT NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_pwd_history_user ON password_history(user_id, created_at DESC);
```

### 3.9 Migration 0008 — seed system roles

```
INSERT INTO roles (name, description, is_system) VALUES
    ('superadmin', 'Full system access', TRUE),
    ('admin', 'Administrative operations', TRUE),
    ('editor', 'Content creation and modification', TRUE),
    ('viewer', 'Read-only access', TRUE);
```

### 3.10 Migration 0009 — seed system permissions

```
-- Permissions
INSERT INTO permissions (resource, action, is_system) VALUES
    ('users', '*', TRUE),
    ('roles', '*', TRUE),
    ('permissions', '*', TRUE),
    ('audit', 'read', TRUE);

-- Superadmin gets all
INSERT INTO role_permissions (role_id, permission_id)
    SELECT r.id, p.id FROM roles r, permissions p WHERE r.name = 'superadmin';

-- Admin gets users:*
INSERT INTO role_permissions (role_id, permission_id)
    SELECT r.id, p.id FROM roles r, permissions p
    WHERE r.name = 'admin' AND p.resource = 'users';
```

---

## 4. JWT Implementation

### 4.1 Key Generation (on first startup)

| Step | Action | Output |
|---|---|---|
| 1 | Generate RSA-2048 key pair | Private key (PKCS#8 PEM), Public key (SPKI PEM) |
| 2 | Compute `kid` (Key ID) | SHA-256 fingerprint of public key, first 16 hex chars |
| 3 | Store private key | Encrypted at rest via `cryptography` Fernet + `JWT_PRIVATE_KEY_ENCRYPTION_KEY` env var |
| 4 | Store public key | Plaintext alongside private key (for JWKS) |
| 5 | Register in JWKS cache | `{keys: [{kty, kid, n, e, alg: "RS256", use: "sig"}]}` |
| 6 | Persist to DB | JWK record table or config store |

### 4.2 Key Rotation (every 30 days)

```
Step 1:  Generate new key pair (new_kid)
Step 2:  Add new public key to JWKS (both old and new served)
Step 3:  Sign new JWTs with new private key
Step 4:  Keep old private key for 24h (verify tokens signed before rotation)
Step 5:  After 24h, remove old key from JWKS
Step 6:  Archive old private key (encrypted, 90-day retention)
```

### 4.3 JWT Creation

| Parameter | Value |
|---|---|
| Algorithm | `RS256` |
| Header | `{"alg": "RS256", "typ": "JWT", "kid": "<current_kid>"}` |
| Claims | `sub`, `sid`, `email`, `name`, `roles[]`, `permissions[]`, `iat`, `exp`, `iss`, `aud`, `jti`, `type` |
| `iss` | `https://auth.ai-enterprises.com` |
| `aud` | `ai-enterprises-api` |
| `type` | `access` |
| Expiry | 15 minutes from `iat` |
| `jti` | uuid7 (for revocation tracking) |

### 4.4 JWT Verification

```
Step 1:  Decode header → extract kid
Step 2:  Load JWKS cache → find key by kid (cache miss → fetch /.well-known/jwks.json → cache 1h)
Step 3:  Decode and verify signature using cryptography library RS256 verification
Step 4:  Validate exp > now() (buffer: 30s clock skew tolerance)
Step 5:  Validate iss == expected issuer
Step 6:  Validate aud == expected audience
Step 7:  Validate type == 'access'
Step 8:  Check jti against revocation list (Redis SET, TTL = token expiry)
```

### 4.5 JWKS Endpoint

`GET /.well-known/jwks.json`

```
Response 200:
  {
    "keys": [
      {
        "kty": "RSA",
        "kid": "a1b2c3d4e5f6g7h8",
        "n": "<base64url-encoded-modulus>",
        "e": "AQAB",
        "alg": "RS256",
        "use": "sig"
      }
    ]
  }
```

---

## 5. Refresh Token Implementation

### 5.1 Token Generation

```
Step 1:  Generate 32 cryptographically random bytes (secrets.token_bytes(32))
Step 2:  Encode as URL-safe base64 (without padding) → opaque refresh token string
Step 3:  Compute SHA-256(token_string) → token_hash
Step 4:  Generate family string: uuid7() (one per refresh token chain)
Step 5:  Store {user_id, session_id, token_hash, family, expires_at} in refresh_tokens table
Step 6:  Set cookie: __Host-refresh_token=<token_string>; Path=/api/v1/auth; HttpOnly; Secure; SameSite=Strict; Max-Age=604800
Step 7:  Return token_string to caller (for cookie only; never in response body)
```

### 5.2 Token Validation

```
Step 1:  Extract token_string from __Host-refresh_token cookie
Step 2:  Compute SHA-256(token_string) → token_hash
Step 3:  SELECT from refresh_tokens WHERE token_hash = :hash
Step 4:  If not found → 401 TOKEN_EXPIRED
Step 5:  If revoked_at IS NOT NULL → THEFT DETECTED (see 5.4)
Step 6:  If expires_at < now() → 401 TOKEN_EXPIRED
Step 7:  Load associated session (sessions.id = session_id)
Step 8:  If session.is_active = FALSE → 401 SESSION_REVOKED
Step 9:  Load associated user (users.id = user_id)
Step 10: If user.deleted_at IS NOT NULL → 401 ACCOUNT_INACTIVE
```

### 5.3 Token Rotation

```
Step 1:  Validate current token (see 5.2)
Step 2:  Generate new refresh token (see 5.1) — same family value
Step 3:  Generate new access token (15 min)
Step 4:  In transaction:
           INSERT new refresh_token
           UPDATE old refresh_token SET revoked_at = now()
           UPDATE sessions SET last_used_at = now()
Step 5:  Set new cookie (replaces old)
Step 6:  Return {access_token, expires_in}
Step 7:  INSERT audit_log (event_type='auth.refresh', resource='session', resource_id=session_id)
```

### 5.4 Theft Detection

```
Trigger: Valid token_hash found but revoked_at IS NOT NULL

Step 1:  SELECT all tokens WHERE family = :family
Step 2:  UPDATE refresh_tokens SET revoked_at = now() WHERE family = :family AND revoked_at IS NULL
Step 3:  Collect all session_ids from affected tokens
Step 4:  UPDATE sessions SET is_active = FALSE WHERE id IN (:session_ids)
Step 5:  Clear cookie: __Host-refresh_token=; Path=/api/v1/auth; Max-Age=0
Step 6:  INSERT audit_log (event_type='auth.token.revoked', action='family_reuse_detected')
Step 7:  Return 401 TOKEN_THEFT_DETECTED
```

---

## 6. Argon2 Password Hashing

### 6.1 Library Integration

| Library | Version | Purpose |
|---|---|---|
| `argon2-cffi` | 23.1+ | Argon2id hash/verify |

### 6.2 Hash Function

```
Input: plaintext_password (str)
Output: PHC string

Operation:
  1. Validate password against policy (see 6.4)
  2. argon2.PasswordHasher(
       time_cost=3,
       memory_cost=65536,    # 64 MB
       parallelism=4,
       hash_len=32,
       salt_len=16,
       type=argon2.Type.ID
     ).hash(plaintext_password)
  3. Return PHC string

Example output:
  $argon2id$v=19$m=65536,t=3,p=4$c29tZXNhbHQ$dGhlc3VwZXJzZWNyZXRoYXNo
```

### 6.3 Verify Function

```
Input: plaintext_password (str), stored_hash (PHC string)
Output: bool

Operation:
  1. argon2.PasswordHasher().verify(stored_hash, plaintext_password)
  2. If verification passes:
       a. Check if hash needs rehashing (parameters upgraded)
       b. If rehash needed: compute new hash, update user record
  3. Return True/False
  4. On argon2.exceptions.VerifyMismatchError → return False
  5. On argon2.exceptions.InvalidHashError → log warning, return False
  6. On argon2.exceptions.VerificationError → log error, return False
```

### 6.4 Password Policy Validator

```
Input: plaintext_password (str)
Output: ValidationResult(passes: bool, errors: list[str])

Rules evaluated in order:
  1. length(plaintext_password) >= 12 → else: "at least 12 characters"
  2. length(plaintext_password) <= 128 → else: "at most 128 characters"
  3. Count character classes:
       - uppercase: any(c.isupper()) for c in password
       - lowercase: any(c.islower()) for c in password
       - digit: any(c.isdigit()) for c in password
       - special: any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?~") for c in password
     At least 3 classes present → else: "at least 3 of 4 character classes"
  4. Common password check:
       Load 10k common passwords list (embedded resource)
       if password.lower() in common_passwords → reject
  5. Have I Been Pwned check (k-anonymity):
       sha1 = hashlib.sha1(password.encode()).hexdigest().upper()
       prefix = sha1[:5]
       response = GET https://api.pwnedpasswords.com/range/{prefix}
       if sha1[5:] in response.text → reject (password has been pwned)
       (timeout: 2s, fail open: log warning but allow)
  6. Return result
```

### 6.5 Password History Check

```
Input: user_id (UUID), new_hash (PHC string)
Output: bool — True if not reused

Operation:
  1. SELECT password_hash FROM password_history WHERE user_id = :id ORDER BY created_at DESC LIMIT 5
  2. For each historical hash:
       Attempt argon2.verify(historical_hash, plaintext_password)
       If any match → return False (password reused)
  3. Return True

On password change:
  1. INSERT new hash into password_history
  2. DELETE FROM password_history WHERE user_id = :id AND id NOT IN (SELECT id FROM password_history WHERE user_id = :id ORDER BY created_at DESC LIMIT 5)
```

---

## 7. Clerk Authentication

### 7.1 Clerk SDK Client

| Parameter | Value |
|---|---|
| SDK | `clerk-backend` (Python) |
| Initialization | `clerk.Client(secret_key=settings.CLERK_SECRET_KEY)` |
| Caching | SDK-managed JWKS cache (auto-refresh) |

### 7.2 Session Verification

```
Input: clerk_session_token (str) — from Authorization header or cookie
Output: clerk.User | None

Operation:
  1. clerk_client.users.get_user(session_token=clerk_session_token)
  2. If session invalid/expired → return None
  3. If valid → return clerk.User object
```

### 7.3 Clerk Sync Endpoint

```
POST /api/v1/auth/clerk/sync
Cookie: __session=<clerk_session_token>

Operation:
  1. Extract clerk_session_token from __session cookie
  2. Verify with Clerk SDK
  3. Extract clerk_id, email, display_name, avatar_url from clerk.User
  4. Look up local user by clerk_id
  5. If not found: look up by email → link clerk_id, or create new user
  6. Create local session + refresh token (same as standard login)
  7. Issue platform JWT
  8. Set __Host-refresh_token cookie
  9. Return {access_token, expires_in, user}
```

### 7.4 Webhook Verification

```
POST /api/v1/auth/clerk/webhook
Headers: svix-id, svix-timestamp, svix-signature

Operation:
  1. Extract svix headers from request
  2. svix.Webhook.verify(payload. body, headers, settings.CLERK_WEBHOOK_SECRET)
  3. If verification fails → return 400 INVALID_WEBHOOK_SIGNATURE
  4. Parse event type from payload (event.type)
  5. Dispatch to event handler (see 7.5)
  6. Return 200
```

### 7.5 Webhook Event Handlers

| Event | Handler Logic |
|---|---|
| `user.created` | Attempt to find user by email → if exists, link clerk_id; if not, create new user with clerk_id, password_hash=NULL, is_verified=True |
| `user.updated` | Find user by clerk_id → update display_name, avatar_url, locale |
| `user.deleted` | Find user by clerk_id → set deleted_at=now(), is_active=FALSE, clerk_id=CONCAT('deleted-', clerk_id) |
| `session.created` | Find user by clerk_id → create local session (same as login) |
| `session.revoked` | Find user by clerk_id → revoke all local sessions |
| `email.verified` | Find user by clerk_id → set is_verified=TRUE |

---

## 8. Google OAuth

### 8.1 Configuration

| Parameter | Value |
|---|---|
| Endpoint | `https://accounts.google.com/o/oauth2/v2/auth` |
| Token URL | `https://oauth2.googleapis.com/token` |
| Userinfo URL | `https://www.googleapis.com/oauth2/v2/userinfo` |
| Scopes | `openid email profile` |
| Client ID | `settings.GOOGLE_CLIENT_ID` |
| Client Secret | `settings.GOOGLE_CLIENT_SECRET` (encrypted) |
| Redirect URI | `{API_URL}/api/v1/auth/oauth/google/callback` |

### 8.2 Initiate Flow

```
GET /api/v1/auth/oauth/google
Query: redirect (optional — post-auth redirect URL)

Operation:
  1. Generate state = secrets.token_urlsafe(32)
  2. Generate code_verifier = secrets.token_urlsafe(64)
  3. Generate code_challenge = SHA256(code_verifier) → base64url
  4. Store {state, code_verifier, redirect} in Redis (TTL: 10 min)
  5. Construct authorize URL:
       https://accounts.google.com/o/oauth2/v2/auth?
         client_id={client_id}&
         redirect_uri={redirect_uri}&
         response_type=code&
         scope=openid+email+profile&
         state={state}&
         code_challenge={code_challenge}&
         code_challenge_method=S256&
         access_type=offline
  6. Return 302 redirect to authorize URL
```

### 8.3 Callback

```
GET /api/v1/auth/oauth/google/callback
Query: code, state, error (optional)

Operation:
  1. If error present → redirect to frontend /login?error=oauth_denied
  2. Validate state from Redis → retrieve stored code_verifier
  3. Exchange code for tokens:
       POST https://oauth2.googleapis.com/token
       Body: code, client_id, client_secret, redirect_uri, code_verifier, grant_type=authorization_code
       Response: {access_token, id_token, expires_in}
  4. Decode id_token (verify signature, validate iss, aud, exp)
  5. Fetch userinfo if needed:
       GET https://www.googleapis.com/oauth2/v2/userinfo
       Header: Authorization: Bearer {access_token}
       Response: {id, email, name, picture, locale, verified_email}
  6. Look up user by email:
       - Found: update display_name, avatar_url, last_login_at
       - Not found: CREATE user with password_hash=NULL, is_verified=verified_email
  7. If Clerk enabled: upsert Clerk user via Clerk API
  8. Create local session + refresh token
  9. Set __Host-refresh_token cookie
  10. If Clerk enabled: set __session cookie (Clerk session)
  11. Redirect to frontend (redirect from state, or default /dashboard)
  12. INSERT audit_log (event_type='oauth.linked', resource='oauth', resource_id='google')
```

---

## 9. GitHub OAuth

### 9.1 Configuration

| Parameter | Value |
|---|---|
| Authorize URL | `https://github.com/login/oauth/authorize` |
| Token URL | `https://github.com/login/oauth/access_token` |
| User API URL | `https://api.github.com/user` |
| Emails API URL | `https://api.github.com/user/emails` |
| Scopes | `read:user user:email` |
| Client ID | `settings.GITHUB_CLIENT_ID` |
| Client Secret | `settings.GITHUB_CLIENT_SECRET` |
| Redirect URI | `{API_URL}/api/v1/auth/oauth/github/callback` |

### 9.2 Email Resolution

```
If user/:email field is null or not primary verified:
  1. GET https://api.github.com/user/emails
     Header: Authorization: Bearer {access_token}
  2. Filter: verified == true AND primary == true
  3. Use first matching email (or first verified email if none primary)
```

---

## 10. Email Verification

### 10.1 Token Generation

```
Input: user_id (UUID), purpose = 'email_verification'
Output: token_string (str), stored in verification_tokens

Operation:
  1. token_bytes = secrets.token_bytes(32)
  2. token_string = urlsafe_b64encode(token_bytes).rstrip('=')
  3. token_hash = SHA256(token_string.encode()).hexdigest()
  4. Store: INSERT verification_tokens(user_id, token_hash, purpose, expires_at=now()+24h)
  5. Return token_string
```

### 10.2 Verification Endpoint

```
GET /api/v1/auth/verify?token=<token_string>

Operation:
  1. token_hash = SHA256(token_string.encode()).hexdigest()
  2. SELECT FROM verification_tokens WHERE token_hash = :hash AND purpose = 'email_verification'
  3. If not found → 400 INVALID_VERIFICATION_TOKEN
  4. If used_at IS NOT NULL → 400 INVALID_VERIFICATION_TOKEN (token already used)
  5. If expires_at < now() → 400 INVALID_VERIFICATION_TOKEN (token expired)
  6. BEGIN TRANSACTION:
       UPDATE verification_tokens SET used_at = now() WHERE id = :id
       UPDATE users SET is_verified = TRUE WHERE id = :user_id
       INSERT audit_log (event_type='user.verified')
  7. Return 200 {message: "Email verified"}
```

### 10.3 Resend Verification

```
POST /api/v1/auth/resend-verification
Body: {email: str}

Operation:
  1. Rate limit check: 1 per 60s, max 5 per 24h (Redis key: resend:{email})
  2. Find user by email (silently return 200 if not found — enumeration protection)
  3. If user.is_verified → return 200 (idempotent)
  4. Invalidate previous verification tokens for this user+purpose
  5. Generate new token → store hash
  6. Send email with verification link
  7. Return 200 {message: "If account exists, verification email sent"}
```

---

## 11. Forgot Password

```
POST /api/v1/auth/forgot-password
Body: {email: str}

Operation:
  1. Rate limit check: 1 per 60s per email, 5 per 24h per email
  2. Find user by email (silently return 200 if not found)
  3. If user.password_hash IS NULL (Clerk-only account) → return 200 (silent no-op)
  4. Invalidate previous password_reset tokens for this user
  5. Generate reset token (same as verification token, purpose='password_reset', TTL=1h)
  6. Store token hash + user_id + expires_at in verification_tokens
  7. Send email:
       To: user.email
       Subject: "Reset your password"
       Body: "Click here to reset: https://app.ai-enterprises.com/auth/reset?token={token}"
  8. Return 200 {message: "If an account exists, a reset link has been sent"}
```

---

## 12. Password Reset

```
POST /api/v1/auth/reset-password
Body: {token: str, password: str}

Operation:
  1. token_hash = SHA256(token.encode()).hexdigest()
  2. SELECT FROM verification_tokens WHERE token_hash = :hash AND purpose = 'password_reset'
  3. If not found → 400 INVALID_RESET_TOKEN
  4. If used_at IS NOT NULL → 400 INVALID_RESET_TOKEN
  5. If expires_at < now() → 400 INVALID_RESET_TOKEN
  6. Load user by user_id from token record
  7. Validate new password against policy (see 6.4)
  8. Check password history (see 6.5)
  9. new_hash = argon2.hash(password)
  10. BEGIN TRANSACTION:
        UPDATE verification_tokens SET used_at = now()
        UPDATE users SET password_hash = :new_hash
        INSERT INTO password_history (user_id, password_hash) VALUES (:user_id, :new_hash)
        UPDATE sessions SET is_active = FALSE WHERE user_id = :user_id AND is_active = TRUE
        (exclude current session if identifiable)
        UPDATE refresh_tokens SET revoked_at = now() WHERE user_id = :user_id AND revoked_at IS NULL
        INSERT audit_log (event_type='user.password.reset')
  11. Send confirmation email
  12. Return 200 {message: "Password has been reset"}
```

---

## 13. Session Management

### 13.1 Session Creation

```
Input: user_id (UUID), ip_address (str), user_agent (str), device_info (dict)
Output: Session object

Operation:
  1. Count active sessions for user:
       SELECT COUNT(*) FROM sessions WHERE user_id = :id AND is_active = TRUE
  2. If count >= 10:
       SELECT id FROM sessions WHERE user_id = :id AND is_active = TRUE ORDER BY last_used_at ASC LIMIT 1
       UPDATE sessions SET is_active = FALSE WHERE id = :oldest_id
  3. session_token = secrets.token_bytes(32)
  4. token_hash = SHA256(session_token).hexdigest()
  5. INSERT sessions(user_id, token_hash, ip_address, user_agent, device_info, expires_at=now()+7d)
  6. Return Session object
```

### 13.2 Session Sliding Window

```
On every authenticated request (via get_valid_session dependency):
  If session.last_used_at < now() - 1h:
    new_expires_at = min(now() + 24h, session.created_at + 7d)
    UPDATE sessions SET last_used_at = now(), expires_at = :new_expires_at WHERE id = :id
```

### 13.3 Session Revocation

```
DELETE /api/v1/auth/sessions/{session_id}
Authorization: Bearer <access_token>

Operation:
  1. get_current_user → user
  2. SELECT FROM sessions WHERE id = :session_id AND user_id = :user.id
  3. If not found → 404
  4. BEGIN TRANSACTION:
       UPDATE sessions SET is_active = FALSE WHERE id = :session_id
       UPDATE refresh_tokens SET revoked_at = now() WHERE session_id = :session_id AND revoked_at IS NULL
       INSERT audit_log (event_type='session.revoked')
  5. Return 200
```

### 13.4 Global Logout (all other sessions)

```
DELETE /api/v1/auth/sessions
Authorization: Bearer <access_token>

Operation:
  1. get_current_user + get_valid_session → user, current_session
  2. BEGIN TRANSACTION:
       UPDATE sessions SET is_active = FALSE WHERE user_id = :user.id AND id != :current_session.id
       UPDATE refresh_tokens SET revoked_at = now()
         WHERE user_id = :user.id AND session_id != :current_session.id AND revoked_at IS NULL
  3. revoked_count = SQL rowcount
  4. INSERT audit_log (event_type='session.revoked', metadata={count: revoked_count})
  5. Return 200 {revoked_count}
```

### 13.5 Cleanup Task (hourly)

```
Operation:
  1. DELETE FROM sessions WHERE expires_at < now()
  2. DELETE FROM refresh_tokens WHERE expires_at < now()
  3. (These cascade to nothing — no FK retention issues)
```

---

## 14. RBAC

### 14.1 Permission Evaluation Engine

```
Input:
  - user: User (with roles loaded)
  - required_resource: str
  - required_action: str

Evaluation:
  1. If user.is_superuser → GRANT
  2. Load user roles: SELECT r.*, p.resource, p.action
       FROM user_roles ur
       JOIN roles r ON r.id = ur.role_id
       JOIN role_permissions rp ON rp.role_id = r.id
       JOIN permissions p ON p.id = rp.permission_id
       WHERE ur.user_id = :user.id
  3. For each permission on each role:
       resource_pattern = compile_pattern(p.resource)
       action_hierarchy = expand_action(p.action)
       If match(required_resource, resource_pattern) AND required_action in action_hierarchy:
         → GRANT
  4. If no match → DENY

Pattern matching rules:
  - "users:*" → matches users:anything
  - "*" → matches any resource
  - "projects:new-project-id" → exact match

Action hierarchy expansion:
  - "manage" → ["manage", "create", "read", "update", "delete"]
  - "write" → ["write", "create", "read", "update"]
  - "create" → ["create", "read"]
  - "read" → ["read"]
  - "delete" → ["delete"]
  - "*" → ["*", "create", "read", "update", "delete", "manage"]
```

### 14.2 Role Assignment

```
POST /api/v1/admin/users/{user_id}/roles
Body: {role_ids: [UUID]}

Authorization: require_permission("users:write")

Operation:
  1. Validate all role_ids exist
  2. BEGIN TRANSACTION:
       DELETE FROM user_roles WHERE user_id = :user_id
       INSERT INTO user_roles (user_id, role_id) VALUES (:user_id, :rid) for each role_id
       INSERT audit_log (event_type='role.assigned', metadata={roles: role_ids})
  3. Invalidate permission cache for user (Redis: DEL perms:{user_id}; DEL roles:{user_id})
  4. Return 200
```

---

## 15. Dependency Injection

### 15.1 FastAPI Dependencies

```
get_db_session() → AsyncSession
  Scope: request
  Creates async session from engine, yields, closes on completion

get_jwks() → JWKS
  Scope: application
  Lazy-loaded, refreshes every hour from DB / file

get_current_user(
  token: str = Depends(oauth2_scheme),
  db: AsyncSession = Depends(get_db_session),
  jwks: JWKS = Depends(get_jwks),
  request: Request = None,
) -> User
  Scope: request
  Raises: 401 INVALID_TOKEN, 401 INVALID_CREDENTIALS

get_valid_session(
  user: User = Depends(get_current_user),
  db: AsyncSession = Depends(get_db_session),
) -> Session
  Scope: request
  Raises: 401 SESSION_REVOKED, 401 TOKEN_EXPIRED
  Side effect: updates session.last_used_at (sliding window)

require_permission(resource: str, action: str) -> Callable
  Returns a dependency: (user, session) = Depends(get_current_user), Depends(get_valid_session)
  Raises: 403 FORBIDDEN
  Side effect: logs audit event on DENY

require_role(role_name: str) -> Callable
  Returns a dependency: user = Depends(get_current_user)
  Raises: 403 FORBIDDEN
```

### 15.2 Dependency Chain

```
Public endpoint:          (no deps)
Protected endpoint:       Depends(get_valid_session)
Permission endpoint:      Depends(get_valid_session), Depends(require_permission("resource", "action"))
Admin endpoint:           Depends(get_valid_session), Depends(require_role("admin"))
Superadmin endpoint:      Depends(get_valid_session), Depends(require_role("superadmin"))
```

### 15.3 OAuth2 Scheme

```
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False
)

Extracts: Authorization: Bearer <token>
Returns: token string or None (for optional auth)
```

---

## 16. Middleware

### 16.1 Middleware Stack (order matters)

```
Request Pipeline:

  1. RequestIDMiddleware
       Action:     Generate/propagate X-Request-ID
       Header:     X-Request-ID (uuid7)
       Logging:    Injected into structlog context
       
  2. CORSMiddleware
       Allow:      settings.CORS_ORIGINS (parsed from env)
       Methods:    GET, POST, PUT, PATCH, DELETE, OPTIONS
       Headers:    Authorization, Content-Type, X-Request-ID
       Credentials: True
       Max-Age:    600
       
  3. SecurityHeadersMiddleware
       HSTS:               max-age=63072000; includeSubDomains
       CSP:                default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'
       X-Content-Type-Options: nosniff
       X-Frame-Options:    DENY
       Referrer-Policy:    strict-origin-when-cross-origin
       Permissions-Policy: camera=(), microphone=(), geolocation=()
       
  4. RateLimitMiddleware
       IP-based:   100 req/min (token bucket, Redis)
       User-based: 500 req/min (token bucket, Redis; only if authenticated)
       Auth endpoints: 20 req/min (login, register, forgot-password, reset-password)
       
  5. AuthContextMiddleware
       Reads:      Authorization header, __Host-refresh_token cookie
       Sets:       request.state.user (User | None)
                   request.state.session (Session | None)
       Does NOT:   Block unauthenticated requests (routing-level deps do that)
       
  6. AuditMiddleware
       Post-response:  Logs request summary (method, path, status, duration, user_id)
       Not:            Audit log insertion (that's done explicitly in services)
```

### 16.2 Next.js Frontend Middleware

```
Location: apps/web/middleware.ts
Matcher: /dashboard/:path*, /admin/:path*, /settings/:path*, /login, /register

Route Protection Map:
  public:     /login, /register, /forgot-password, /reset-password, /verify, /api/auth/*
  protected:  /dashboard/* (auth required)
  admin:      /admin/* (auth + role: admin|superadmin)
  settings:   /settings/* (auth required)

Logic:
  1. Read __Host-refresh_token cookie
  2. If route is public and cookie exists → redirect to /dashboard
  3. If route is protected and cookie is missing → redirect to /login?redirect={path}
  4. If route is admin: decode JWT from in-memory store (no signature verify, just check roles claim)
  5. If roles claim missing admin/superadmin → redirect to /403
```

---

## 17. API Endpoints

### 17.1 Router Registration

```
router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

Register:
  POST   /register           → auth.register        (public, rate-limited)
  POST   /login              → auth.login           (public, rate-limited)
  POST   /refresh            → auth.refresh         (public, cookie)
  POST   /logout             → auth.logout          (authenticated)
  GET    /verify             → auth.verify_email    (public, token query param)
  POST   /resend-verification → auth.resend_verify  (public, rate-limited)
  POST   /forgot-password    → auth.forgot_password  (public, rate-limited)
  POST   /reset-password     → auth.reset_password   (public, rate-limited)
  GET    /oauth/google       → auth.oauth_google     (public)
  GET    /oauth/google/callback → auth.oauth_google_callback (public)
  GET    /oauth/github       → auth.oauth_github     (public)
  GET    /oauth/github/callback → auth.oauth_github_callback (public)
  POST   /clerk/webhook      → auth.clerk_webhook    (public, svix-verified)
  POST   /clerk/sync         → auth.clerk_sync       (public)
  GET    /me                 → auth.me               (authenticated)
  PATCH  /me                 → auth.update_me        (authenticated)
  GET    /sessions           → auth.list_sessions    (authenticated)
  DELETE /sessions/{id}      → auth.revoke_session   (authenticated)
  DELETE /sessions           → auth.revoke_all_other_sessions (authenticated)

Admin router: /api/v1/admin
  GET    /users              → admin.list_users      (permission: users:read)
  GET    /users/{id}         → admin.get_user        (permission: users:read)
  PATCH  /users/{id}         → admin.update_user     (permission: users:write)
  DELETE /users/{id}         → admin.delete_user     (permission: users:delete)
  POST   /users/{id}/roles   → admin.set_user_roles  (permission: users:write)
  GET    /roles              → admin.list_roles      (permission: roles:read)
  POST   /roles              → admin.create_role     (permission: roles:create)
  PATCH  /roles/{id}         → admin.update_role     (permission: roles:write)
  DELETE /roles/{id}         → admin.delete_role     (permission: roles:delete)
  GET    /permissions        → admin.list_permissions (permission: permissions:read)
  POST   /permissions        → admin.create_permission (permission: permissions:create)
  DELETE /permissions/{id}   → admin.delete_permission (permission: permissions:delete)
  GET    /audit-logs         → admin.list_audit_logs  (permission: audit:read)

Public no-prefix:
  GET    /.well-known/jwks.json → public.jwks
```

---

## 18. Request/Response Schemas

### 18.1 Request Schemas (Pydantic v2)

| Schema | Fields | Validators |
|---|---|---|
| `RegisterRequest` | `email: EmailStr`, `password: str`, `display_name: str`, `locale: str = "en"` | email → strip+lower; password → validate_policy; display_name → strip, min 2 |
| `LoginRequest` | `email: EmailStr`, `password: str`, `device_info: dict = {}` | email → strip+lower; device_info → max_depth=3, max_keys=10 |
| `ForgotPasswordRequest` | `email: EmailStr` | email → strip+lower |
| `ResetPasswordRequest` | `token: str`, `password: str` | password → validate_policy |
| `ResendVerificationRequest` | `email: EmailStr` | email → strip+lower |
| `UpdateProfileRequest` | `display_name: Optional[str]`, `avatar_url: Optional[HttpUrl]`, `locale: Optional[str]` | at least one field required |
| `SetUserRolesRequest` | `role_ids: list[uuid.UUID]` | min 1, max 10 |
| `CreateRoleRequest` | `name: str`, `description: Optional[str]` | name → alphanumeric + underscore, max 100 |
| `UpdateRoleRequest` | `name: Optional[str]`, `description: Optional[str]` | — |
| `CreatePermissionRequest` | `resource: str`, `action: str`, `description: Optional[str]` | resource → alphanumeric+colon+asterisk, max 255 |
| `PaginatedQuery` | `page: int = 1`, `page_size: int = 20`, `sort_by: Optional[str]`, `sort_order: Literal["asc", "desc"] = "desc"` | page >= 1, page_size 1-100 |

### 18.2 Response Schemas

| Schema | Fields |
|---|---|
| `AuthResponse` | `status: str = "success"`, `data: AuthData` |
| `AuthData` | `user: UserResponse`, `access_token: str`, `expires_in: int` |
| `UserResponse` | `id: UUID`, `email: str`, `display_name: str`, `avatar_url: Optional[str]`, `is_verified: bool`, `roles: list[str]`, `locale: str`, `created_at: datetime` |
| `SessionResponse` | `id: UUID`, `ip_address: str`, `user_agent: str`, `device_info: dict`, `is_active: bool`, `created_at: datetime`, `last_used_at: datetime`, `expires_at: datetime` |
| `AuditLogResponse` | `id: UUID`, `event_type: str`, `resource: str`, `resource_id: Optional[str]`, `action: str`, `actor_ip: str`, `metadata: dict`, `created_at: datetime` |
| `MessageResponse` | `status: str = "success"`, `data: MessageData` |
| `MessageData` | `message: str` |
| `PaginatedResponse` | `status: str = "success"`, `data: PaginatedData` |
| `PaginatedData` | `items: list`, `total: int`, `page: int`, `page_size: int`, `pages: int` |
| `ErrorResponse` | `status: str = "error"`, `error: ErrorDetail`, `request_id: Optional[str]` |
| `ErrorDetail` | `code: str`, `message: str`, `details: Optional[list[FieldError]]`, `retry_after_seconds: Optional[int]` |
| `FieldError` | `field: str`, `message: str` |

### 18.3 JSON Response Envelope

```
Success:    {status, data}
Error:      {status, error: {code, message, details?, retry_after_seconds?}, request_id?}
List:       {status, data: {items[], total, page, page_size, pages}}
```

---

## 19. Exception Handling

### 19.1 Exception Hierarchy

```
BaseException
  └── AppException (400-499)
        ├── BadRequestException (400)
        │     └── ValidationException (400)
        │     └── InvalidResetToken (400)
        │     └── InvalidVerificationToken (400)
        ├── UnauthorizedException (401)
        │     └── InvalidCredentialsException (401)
        │     └── InvalidTokenException (401)
        │     └── TokenExpiredException (401)
        │     └── TokenTheftDetectedException (401)
        │     └── SessionRevokedException (401)
        ├── ForbiddenException (403)
        │     └── EmailNotVerifiedException (403)
        │     └── AccountInactiveException (403)
        │     └── InsufficientPermissionsException (403)
        ├── NotFoundException (404)
        ├── ConflictException (409)
        │     └── EmailAlreadyExistsException (409)
        └── LockedException (423)
              └── AccountLockedException (423)
  └── RateLimitExceededException (429)
```

### 19.2 Exception Handler Registration

```python
# Registered in main.py: app.add_exception_handler(...)

@app.exception_handler(AppException)
async def app_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "retry_after_seconds": exc.retry_after_seconds,
            },
            "request_id": request.state.request_id,
        },
    )

@app.exception_handler(PydanticValidationError)
async def validation_handler(request, exc):
    details = [{"field": e["loc"][-1], "message": e["msg"]} for e in exc.errors()]
    return JSONResponse(
        status_code=422,
        content={
            "status": "error",
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": details,
            },
        },
    )

@app.exception_handler(Exception)
async def unhandled_handler(request, exc):
    # Log full traceback, return sanitized 500
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
            },
        },
    )
```

### 19.3 Error Response Examples

```
422 VALIDATION_ERROR:
  {
    "status": "error",
    "error": {
      "code": "VALIDATION_ERROR",
      "message": "Request validation failed",
      "details": [
        {"field": "password", "message": "String should have at least 12 characters"}
      ]
    },
    "request_id": "0194f2a0-..."
  }

401 INVALID_CREDENTIALS:
  {
    "status": "error",
    "error": {
      "code": "INVALID_CREDENTIALS",
      "message": "Invalid email or password."
    },
    "request_id": "0194f2a0-..."
  }

423 ACCOUNT_LOCKED:
  {
    "status": "error",
    "error": {
      "code": "ACCOUNT_LOCKED",
      "message": "Account temporarily locked. Try again in 15 minutes.",
      "retry_after_seconds": 900
    },
    "request_id": "0194f2a0-..."
  }

429 RATE_LIMIT_EXCEEDED:
  {
    "status": "error",
    "error": {
      "code": "RATE_LIMIT_EXCEEDED",
      "message": "Too many requests. Please try again later.",
      "retry_after_seconds": 60
    },
    "request_id": "0194f2a0-..."
  }
```

---

## 20. Validation

### 20.1 Email Validation

```
Format: RFC 5321 simplified regex: ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$
Normalization: .lower().strip()
Max length: 320 characters after normalization
Disposable blocklist: 100+ domains (loaded from embedded resource)
  Examples: mailinator.com, tempmail.com, 10minutemail.com, guerrillamail.com
Role-based blocklist: admin@, info@, support@, sales@, contact@, webmaster@, postmaster@, abuse@, root@, noreply@, dev@, test@
```

### 20.2 Password Validation

```
Rules (evaluated in order, fail on first violation):
  1. len >= 12 → "at least 12 characters"
  2. len <= 128 → "at most 128 characters"
  3. Count class matches:
       [any(c.isupper() for c in pw),
        any(c.islower() for c in pw),
        any(c.isdigit() for c in pw),
        any(c in SPECIAL_CHARS for c in pw)]
     sum >= 3 → else: "at least 3 of: uppercase, lowercase, digit, special character"
  4. pw.lower() not in COMMON_PASSWORDS (10k list) → else: "password is too common"
  5. HIBP check (k-anonymity): SHA1 prefix → check range API → else: "password has been exposed in a data breach"
  6. Unicode: NFKC normalize before hashing
  7. Whitespace: strip leading/trailing (internal whitespace allowed)
```

### 20.3 Display Name Validation

```
Min length: 2 characters (trimmed)
Max length: 255 characters
Allowed pattern: Unicode letters, digits, spaces, hyphens, apostrophes
  Regex: ^[\p{L}\p{N}\s\-']+$
Profanity check: against embedded blocklist (case-insensitive, substring match)
```

### 20.4 Locale Validation

```
Format: IETF BCP 47 (language[-region])
  Regex: ^[a-z]{2,3}(-[A-Z]{2})?$
Supported: restricted to ['en', 'en-US', 'ur', 'ur-PK', 'ar', 'ar-SA', 'es', 'fr', 'de', 'zh-CN', 'ja', 'ko'] (expandable)
```

### 20.5 Device Info Validation

```
Type: dict (JSONB storage)
Max depth: 3 levels
Max keys: 10
Max string value length: 255 characters
Allowed key pattern: ^[a-zA-Z_][a-zA-Z0-9_]*$
PII fields blocked: The following keys are stripped if present: ['latitude', 'longitude', 'gps', 'coordinates', 'ip']
```

---

## 21. Security Headers

### 21.1 Backend Response Headers

```
All responses (via SecurityHeadersMiddleware):

  Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
  Content-Security-Policy:
    default-src 'self';
    script-src 'self';
    style-src 'self' 'unsafe-inline';
    img-src 'self' data: https:;
    font-src 'self';
    connect-src 'self' https://api.ai-enterprises.com;
    frame-ancestors 'none';
    form-action 'self'
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  X-XSS-Protection: 0  (deprecated, but CSP handles it)
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy:
    camera=(),
    microphone=(),
    geolocation=(),
    interest-cohort=()
  Cross-Origin-Embedder-Policy: require-corp
  Cross-Origin-Opener-Policy: same-origin
  Cross-Origin-Resource-Policy: same-origin
```

### 21.2 Cookie Configuration

```
Refresh token cookie:
  Name:             __Host-refresh_token
  Value:            opaque token string
  Path:             /api/v1/auth
  Domain:           NOT SET (hostname only — __Host- prefix requirement)
  Secure:           TRUE (HTTPS only)
  HttpOnly:         TRUE (not accessible to JavaScript)
  SameSite:         Strict
  Max-Age:          604800 (7 days)
  Priority:         High

Session cookie (Clerk):
  Name:             __session
  Set by:           Clerk (frontend SDK)
  Secure:           TRUE
  HttpOnly:         TRUE
  SameSite:         Lax

Access token cookie (NOT USED — in-memory only):
  Access tokens are NEVER stored in cookies.
  Transmitted via Authorization: Bearer header only.
  Stored client-side in memory (closure variable, Zustand store).
```

---

## 22. Cookie Strategy

### 22.1 Cookie Namespacing

```
Prefix:  __Host- (requires Secure + no Domain + Path=/)

Cookies:
  __Host-refresh_token     → refresh token (httpOnly, Secure, SameSite=Strict)
  __Host-clerk_session     → Clerk session (httpOnly, Secure, SameSite=Lax) [if Clerk enabled]
```

### 22.2 Cookie Lifecycle

```
Registration/Login:
  Set:   __Host-refresh_token=<opaque>; Path=/api/v1/auth; Secure; HttpOnly; SameSite=Strict; Max-Age=604800

Token Refresh:
  Set:   __Host-refresh_token=<new_opaque>; ... ; Max-Age=604800  (replaces old)

Logout:
  Set:   __Host-refresh_token=; Path=/api/v1/auth; Max-Age=0  (immediate expiry)

Theft Detection:
  Set:   __Host-refresh_token=; Path=/api/v1/auth; Max-Age=0  (clear all)
```

### 22.3 CSRF Protection

```
CSRF is handled via SameSite=Strict cookie attribute on all auth cookies.
No additional CSRF token is needed for auth endpoints because:

  1. __Host-refresh_token is SameSite=Strict → never sent on cross-site requests
  2. OAuth flows use state + PKCE parameters (anti-CSRF)
  3. Non-auth state-changing endpoints use access_tokens in Authorization headers
     (not cookies), which are immune to CSRF

If non-cookie state-changing endpoints are needed for browser clients:
  CSRF token = SHA256(random || secret) stored in session, returned via custom header
```

---

## 23. Rate Limiting

### 23.1 Token Bucket Algorithm

```
Class: TokenBucketRateLimiter
Storage: Redis (sorted sets for sliding window)

Per-bucket configuration:
  key:      ratelimit:{scope}:{identifier}:{endpoint_group}
  capacity: max burst allowed
  refill:   tokens per minute

Check function:
  async def check(key: str, capacity: int, refill: int, window_s: int = 60) -> RateLimitResult:
      now = time.time()
      window_start = now - window_s

      # Atomic Redis script (Lua):
      #   1. ZREMRANGEBYSCORE key 0 window_start   (remove old entries)
      #   2. ZCARD key                               (count current)
      #   3. IF count >= capacity → RETURN 0 (deny)
      #   4. ZADD key now member:{random}
      #   5. EXPIRE key window_s * 2
      #   6. RETURN capacity - count - 1 (remaining)

      result = redis.eval(script, keys=[key], args=[window_start, now, capacity])

      return RateLimitResult(
          allowed=result > 0,
          remaining=result if result > 0 else 0,
          reset_at=window_start + window_s,
      )
```

### 23.2 Bucket Definitions

| Bucket | Key Pattern | Capacity | Refill | Scope |
|---|---|---|---|---|
| IP global | `rl:ip:{ip}:global` | 100 | 100/min | Per IP, all endpoints |
| User global | `rl:user:{user_id}:global` | 500 | 500/min | Per authenticated user |
| Auth IP | `rl:ip:{ip}:auth` | 20 | 20/min | Per IP on auth endpoints |
| Login user | `rl:login:{email}` | 5 | 5/15min | Per email on POST /login |
| Register IP | `rl:ip:{ip}:register` | 3 | 3/15min | Per IP on POST /register |
| Forgot IP | `rl:ip:{ip}:forgot` | 5 | 5/15min | Per IP on forgot-password |
| Forgot email | `rl:forgot:{email}` | 3 | 3/24h | Per email on forgot-password |
| Verify resend | `rl:resend:{email}` | 5 | 5/24h | Per email on resend-verification |

### 23.3 Response Headers

```
When rate limited (429):
  RateLimit-Limit: 20
  RateLimit-Remaining: 0
  RateLimit-Reset: 1700000100
  Retry-After: 45
```

---

## 24. Audit Logging

### 24.1 AuditLogger Service

```
Class: AuditLogger
Dependencies: AsyncSession (db)

Methods:
  async def log(
      self,
      event_type: str,
      user_id: UUID,
      session_id: UUID | None,
      resource: str,
      resource_id: str | None,
      action: str,
      actor_ip: str,
      actor_ua: str,
      metadata: dict = {},
  ) -> None:

      audit = AuditLog(
          user_id=user_id,
          session_id=session_id,
          event_type=event_type,
          resource=resource,
          resource_id=resource_id,
          action=action,
          actor_ip=actor_ip,
          actor_ua=actor_ua,
          metadata=metadata,
      )
      self.db.add(audit)
      await self.db.commit()
      # Log to structured logger as well
      logger.info("audit.event", event_type=event_type, resource=resource, action=action)
```

### 24.2 Audit Event Dispatch

```
Every auth service method calls audit_logger.log() at the end:

  authentication.register    → user.created
  authentication.login      → auth.login
  authentication.login.fail → auth.login.failed (no user_id if email not found — use placeholder)
  authentication.logout     → auth.logout
  token.refresh             → auth.refresh
  token.theft_detected      → auth.token.revoked (metadata: {reason: "family_reuse"})
  verification.verify_email → user.verified
  password.forgot           → user.password.forgot
  password.reset            → user.password.reset
  password.change           → user.password.changed
  oauth.google              → oauth.linked (metadata: {provider: "google"})
  oauth.github              → oauth.linked (metadata: {provider: "github"})
  session.revoke            → session.revoked
  session.revoke_all        → session.revoked (metadata: {count: N})
  authorization.deny        → permission.denied (metadata: {required_resource, required_action})
  role.assign               → role.assigned (metadata: {roles: [...]})
  role.remove               → role.revoked (metadata: {role: role_name})
  clerk.webhook             → clerk.webhook (metadata: {event: clerk_event_type})
```

---

## 25. Unit Tests

### 25.1 Test Configuration

```
Framework: pytest + pytest-asyncio
Database: test PostgreSQL (via testcontainers or Neon branch)
HTTP Client: httpx.AsyncClient (ASGI-transport)
Fixtures: conftest.py (session-scoped engine, function-scoped session)

conftest.py fixtures:
  - event_loop: module-scoped
  - db_engine: session-scoped (creates tables, drops after)
  - db_session: function-scoped (fresh transaction, rollback after)
  - test_client: function-scoped (FastAPI test client with auth headers)
  - default_user: function-scoped (verified user, viewer role)
  - admin_user: function-scoped (admin user)
  - argo n2_mock: function-scoped (mock argon2 for speed)
  - redis_mock: function-scoped (fake Redis)
  - email_mock: function-scoped (mock email sender)
```

### 25.2 Test Files and Functions

```
test_authentication.py (12 tests):
  ✓ test_register_success — valid registration returns 201 + sets cookie
  ✓ test_register_duplicate_email — 409 EMAIL_ALREADY_EXISTS
  ✓ test_register_weak_password — 422 VALIDATION_ERROR
  ✓ test_register_disposable_email — 422 disposable domain blocked
  ✓ test_login_success — valid credentials returns 200 + cookie
  ✓ test_login_wrong_password — 401 INVALID_CREDENTIALS
  ✓ test_login_unverified_email — 403 EMAIL_NOT_VERIFIED
  ✓ test_login_locked_account — 423 ACCOUNT_LOCKED
  ✓ test_login_inactive_account — 403 ACCOUNT_INACTIVE
  ✓ test_logout_success — 200 + cookie cleared
  ✓ test_logout_invalid_token — 401 INVALID_TOKEN
  ✓ test_login_after_account_lockout_expires — succeeds after 15 min

test_authorization.py (10 tests):
  ✓ test_superuser_bypasses_permissions — superuser can access any resource
  ✓ test_viewer_cannot_write — viewer role denied on users:write
  ✓ test_admin_can_write — admin role granted on users:write
  ✓ test_permission_hierarchy_manage_implies_read — manage grants read
  ✓ test_permission_hierarchy_write_implies_read — write grants read
  ✓ test_permission_wildcard_match — users:* matches users:delete
  ✓ test_deny_priority_overrides_grant — explicit deny blocks even with manage
  ✓ test_no_role_assigned_denied — user without roles gets 403
  ✓ test_require_role_admin_missing — user without admin role gets 403
  ✓ test_require_role_admin_success — admin user passes role check

test_tokens.py (8 tests):
  ✓ test_jwt_creation_valid_claims — JWT contains correct sub, sid, roles, exp
  ✓ test_jwt_verification_valid — valid JWT passes verification
  ✓ test_jwt_expired_token — expired JWT returns 401
  ✓ test_jwt_invalid_signature — wrong key returns 401
  ✓ test_jwt_none_algorithm_rejected — alg:none attack blocked
  ✓ test_refresh_token_rotation — old token revoked, new one issued
  ✓ test_refresh_token_expired — expired refresh token returns 401
  ✓ test_refresh_token_theft_detection — revoked family reuse → mass revocation

test_oauth.py (6 tests):
  ✓ test_google_initiate — returns 302 with correct state + redirect URL
  ✓ test_google_callback_success — code exchange → user created → cookie set
  ✓ test_google_callback_invalid_state — invalid state → redirect to /login?error
  ✓ test_github_initiate — returns 302 with correct state
  ✓ test_github_callback_success — code exchange → user created → cookie set
  ✓ test_github_private_email_resolved — email from /user/emails API

test_clerk.py (6 tests):
  ✓ test_clerk_sync_new_user — first-time Clerk sync creates local user
  ✓ test_clerk_sync_existing_user — returning Clerk sync updates last_login_at
  ✓ test_clerk_webhook_user_created — webhook creates local user record
  ✓ test_clerk_webhook_user_deleted — webhook soft-deletes local user
  ✓ test_clerk_webhook_invalid_signature — bad svix sig returns 400
  ✓ test_clerk_webhook_unknown_event — unknown event silently ack'd

test_rate_limit.py (4 tests):
  ✓ test_ip_rate_limit_exceeded — 20th request from same IP in 1 min → 429
  ✓ test_user_rate_limit_exceeded — 501st request from same user → 429
  ✓ test_auth_endpoint_rate_limit — 21st /login in 1 min → 429
  ✓ test_rate_limit_headers_present — 200 response includes RateLimit-* headers

test_user.py (4 tests):
  ✓ test_user_soft_delete_sets_deleted_at — delete sets deleted_at, row remains
  ✓ test_user_soft_delete_removes_from_queries — query filters WHERE deleted_at IS NULL
  ✓ test_user_email_unique_constraint — duplicate email raises integrity error
  ✓ test_user_auth_method_constraint — password_hash OR clerk_id must be non-null

test_session.py (4 tests):
  ✓ test_session_limit_enforced — 11th session revokes oldest
  ✓ test_session_sliding_window — active request extends expires_at
  ✓ test_session_revocation — revoke sets is_active=FALSE
  ✓ test_session_cleanup — expired session deleted on cleanup
```

---

## 26. Integration Tests

### 26.1 Test Environment

```
Database: Dedicated test PostgreSQL (same Docker image, ephemeral)
Redis: Dedicated test Redis (ephemeral)
Email: Mock SMTP server (aiosmtpd or pytest-httpx)
OAuth: Mock HTTP server (respx or pytest-httpx)
Clerk: Mock HTTP server
```

### 26.2 Integration Test Cases

```
Full Registration Flow (3 tests):
  ✓ Register → receive 201 → cookie set → access token valid → email sent with verification link
  ✓ Register → verification link clicked → is_verified=TRUE → login succeeds
  ✓ Register → login before verify → 403 EMAIL_NOT_VERIFIED

Login Flow (3 tests):
  ✓ Login → receive 200 → cookie set → access token valid → permissions loaded
  ✓ Login → 5 failed attempts → account locked → 423 with retry_after
  ✓ Login after lockout expires → succeeds, counter reset

Token Lifecycle (3 tests):
  ✓ Login → use access token → refresh (rotate) → old RT revoked → new RT valid → use new RT
  ✓ Login → steal refresh token → wait → use stolen token → THEFT DETECTED → all sessions revoked
  ✓ Login → refresh after 7 days → 401 TOKEN_EXPIRED → re-login required

Password Reset (2 tests):
  ✓ Forgot password → receive email → click reset link → set new password → login with new password → old password fails
  ✓ Forgot password → reset → attempt reuse of old password → 400 validation error

OAuth Flows (2 tests):
  ✓ Google OAuth → redirect → callback → user created → session created → can access protected route
  ✓ GitHub OAuth → redirect → callback → existing user linked → login successful

RBAC (2 tests):
  ✓ Admin creates role → assigns permission → assigns to user → user accesses resource
  ✓ Role removed from user → user loses access → 403 on next request

Audit Logging (2 tests):
  ✓ Every auth action generates audit log entry with correct event_type, resource, action
  ✓ Audit logs queryable by user_id with proper pagination
```

---

## 27. E2E Tests

### 27.1 E2E Test Infrastructure

```
Framework: pytest + httpx (full ASGI app, no mocking)
Database: Fresh test PostgreSQL per test suite
External: All external APIs mocked at HTTP level (respx)
Browser: Playwright (optional — for full frontend+backend flow)
```

### 27.2 E2E Test Cases

```
Happy Path — Complete User Journey:
  1. POST /register → 201 {user, access_token}
  2. Extract __Host-refresh_token from Set-Cookie header
  3. Verify email: GET /verify?token=<from email> → 200
  4. POST /login with credentials → 200 {access_token}
  5. GET /me (Authorization: Bearer <token>) → 200 {user profile}
  6. POST /refresh (Cookie: __Host-refresh_token=<rt>) → 200 {new_access_token}
  7. GET /me (with new access token) → 200
  8. GET /sessions → 200 {sessions: [{...}]}
  9. POST /logout → 200, cookie cleared
  10. GET /me (with old access token) → 401

OAuth Flow — Google:
  1. GET /auth/oauth/google → 302 redirect to Google
  2. Extract state from Location header
  3. Simulate Google callback: GET /auth/oauth/google/callback?code=mock_code&state=<state>
  4. → 302 redirect to frontend with Set-Cookie: __Host-refresh_token
  5. Extract cookie, GET /me → 200 {user from Google}
  6. POST /logout → 200

Token Theft Scenario:
  1. POST /login → 200, capture refresh_token cookie
  2. POST /refresh → 200, cookie updated
  3. POST /refresh with original (now-stolen) refresh_token → 401 TOKEN_THEFT_DETECTED
  4. Attempt GET /me with any access token from the same login → 401 SESSION_REVOKED
```

---

## 28. Sequence Diagrams

### 28.1 Complete Registration

```
Client                  FastAPI                         PostgreSQL        Email Service
  │                        │                               │                  │
  │── POST /register ──────│                               │                  │
  │   {email, password,    │                               │                  │
  │    display_name}       │                               │                  │
  │                        │── Validate email format        │                  │
  │                        │── Validate password policy     │                  │
  │                        │── Check disposable domain     │                  │
  │                        │── Normalize email (lower)     │                  │
  │                        │                               │                  │
  │                        │── Check email uniqueness ─────│                  │
  │                        │   SELECT email FROM users     │                  │
  │                        │   WHERE email=:email          │                  │
  │                        │   AND deleted_at IS NULL      │                  │
  │                        │←── no result ────────────────│                  │
  │                        │                               │                  │
  │                        │── Argon2.hash(password)        │                  │
  │                        │   → phc_string                │                  │
  │                        │                               │                  │
  │                        │── INSERT users ───────────────│                  │
  │                        │   (email, password_hash,       │                  │
  │                        │    display_name, locale)       │                  │
  │                        │←── user_id ──────────────────│                  │
  │                        │                               │                  │
  │                        │── secrets.token_bytes(32)     │                  │
  │                        │── SHA256(token)→ token_hash    │                  │
  │                        │── INSERT verification_tokens ──│                  │
  │                        │   (user_id, token_hash,       │                  │
  │                        │    purpose=email_verification, │                  │
  │                        │    expires_at=now()+24h)       │                  │
  │                        │                               │                  │
  │                        │── Send verification email ────│─────────────────│
  │                        │   To: user.email               │                  │
  │                        │   Subject: Verify your email   │                  │
  │                        │   Body: /verify?token=...      │                  │
  │                        │                               │                  │
  │                        │── secrets.token_bytes(32)     │                  │
  │                        │── SHA256(session_token)        │                  │
  │                        │── INSERT sessions ────────────│                  │
  │                        │   (user_id, token_hash,       │                  │
  │                        │    ip, ua, device_info,       │                  │
  │                        │    expires_at=now()+7d)        │                  │
  │                        │←── session_id ───────────────│                  │
  │                        │                               │                  │
  │                        │── secrets.token_bytes(32)     │                  │
  │                        │── SHA256(refresh_token)        │                  │
  │                        │── family = uuid7()            │                  │
  │                        │── INSERT refresh_tokens ──────│                  │
  │                        │   (user_id, session_id,       │                  │
  │                        │    token_hash, family,        │                  │
  │                        │    expires_at=now()+7d)        │                  │
  │                        │                               │                  │
  │                        │── Generate JWT (RS256)         │                  │
  │                        │   sub=user_id, sid=session_id │                  │
  │                        │   roles=[viewer], email=...    │                  │
  │                        │   exp=now()+15min             │                  │
  │                        │                               │                  │
  │                        │── INSERT audit_log ───────────│                  │
  │                        │   (event_type=user.created)   │                  │
  │                        │                               │                  │
  │                        │── COMMIT transaction          │                  │
  │                        │                               │                  │
  │←── 201 ────────────────│                               │                  │
  │   Set-Cookie: __Host-  │                               │                  │
  │   refresh_token=<rt>   │                               │                  │
  │   {access_token,       │                               │                  │
  │    expires_in: 900,    │                               │                  │
  │    user: {id, email,   │                               │                  │
  │          display_name, │                               │                  │
  │          is_verified:  │                               │                  │
  │          false,        │                               │                  │
  │          roles:        │                               │                  │
  │          [viewer]}}    │                               │                  │
```

### 28.2 Authenticated Request (with RBAC)

```
Client                  FastAPI                        PostgreSQL          Redis
  │                        │                              │                  │
  │── GET /api/v1/me ──────│                              │                  │
  │   Authorization:       │                              │                  │
  │   Bearer <JWT>         │                              │                  │
  │                        │                              │                  │
  │── Extract kid from JWT header                         │                  │
  │── Check jwks cache ───────────────────────────────────│                  │
  │   Key: jwks:{kid}     │                              │                  │
  │←── CACHE HIT ─────────│                              │                  │
  │                        │                              │                  │
  │── Verify JWT signature │                              │                  │
  │   (RS256, kid-matched  │                              │                  │
  │    public key)         │                              │                  │
  │── Validate exp, iss,   │                              │                  │
  │   aud, type claims     │                              │                  │
  │                        │                              │                  │
  │── Decode claims:       │                              │                  │
  │   sub = user_id,       │                              │                  │
  │   sid = session_id     │                              │                  │
  │                        │                              │                  │
  │── Check jti revocation │                              │                  │
  │   Key: revoke:{jti}   │                              │                  │
  │←── NOT FOUND ──────────│                              │                  │
  │                        │                              │                  │
  │── SELECT user ─────────│──────────────────────────────│                  │
  │   WHERE id = :sub     │                              │                  │
  │   AND deleted_at IS NULL                              │                  │
  │←── user ──────────────│                              │                  │
  │                        │                              │                  │
  │── user.is_active?      │                              │                  │
  │   (No: → 403)          │                              │                  │
  │                        │                              │                  │
  │── SELECT session ──────│──────────────────────────────│                  │
  │   WHERE id = :sid     │                              │                  │
  │   AND is_active = TRUE│                              │                  │
  │←── session ───────────│                              │                  │
  │                        │                              │                  │
  │── session.expires_at > now()?                         │                  │
  │   (No: → 401)          │                              │                  │
  │                        │                              │                  │
  │── Session sliding window                              │                  │
  │   If last_used_at < 1h ago:                           │                  │
  │      UPDATE sessions   │                              │                  │
  │      SET last_used_at  │                              │                  │
  │      = now(),          │                              │                  │
  │      expires_at =      │                              │                  │
  │      min(now()+24h,    │                              │                  │
  │      created+7d)       │                              │                  │
  │   (fire-and-forget)    │                              │                  │
  │                        │                              │                  │
  │── Load roles + permissions                            │                  │
  │   Check cache ────────────────────────────────────────│                  │
  │   Key: perms:{user_id}│                              │                  │
  │←── CACHE MISS ────────│                              │                  │
  │                        │                              │                  │
  │── SELECT roles + perms│──────────────────────────────│                  │
  │   JOIN user_roles +   │                              │                  │
  │   role_permissions    │                              │                  │
  │←── [resource, action] │                              │                  │
  │                        │                              │                  │
  │── SET cache ─────────────────────────────────────────│                  │
  │   perms:{user_id}     │                              │                  │
  │   TTL: 300            │                              │                  │
  │                        │                              │                  │
  │── Evaluate permission: │                              │                  │
  │   required: users:read│                              │                  │
  │   user.is_superuser?  │                              │                  │
  │   → No                │                              │                  │
  │   Match perm rule?    │                              │                  │
  │   → users:read matches│                              │                  │
  │   → GRANT             │                              │                  │
  │                        │                              │                  │
  │── INSERT audit_log ────│──────────────────────────────│                  │
  │   (event_type=         │                              │                  │
  │    user.profile.read)  │                              │                  │
  │                        │                              │                  │
  │←── 200 ────────────────│                              │                  │
  │   {id, email,          │                              │                  │
  │    display_name,       │                              │                  │
  │    avatar_url,         │                              │                  │
  │    is_verified,        │                              │                  │
  │    roles: [viewer],    │                              │                  │
  │    locale: "en",       │                              │                  │
  │    created_at}         │                              │                  │
```

---

## 29. Production Checklist

### 29.1 Pre-Deployment Verification

```
□ [CONFIG]   All 40+ environment variables defined with correct values
□ [CONFIG]   CORS_ORIGINS whitelist contains only known frontend domains
□ [CONFIG]   JWT_PRIVATE_KEY exists and is encrypted
□ [CONFIG]   JWT_PRIVATE_KEY_ENCRYPTION_KEY set and rotated
□ [CONFIG]   DATABASE_URL uses SSL mode (require/verify-full)
□ [CONFIG]   REDIS_URL uses TLS
□ [CONFIG]   CLERK_SECRET_KEY and CLERK_WEBHOOK_SECRET set
□ [CONFIG]   GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET set
□ [CONFIG]   GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET set
□ [CONFIG]   SMTP credentials set for production email provider
□ [CONFIG]   COOKIE_DOMAIN left empty (__Host- prefix requires no domain)
□ [CONFIG]   CORS_ORIGINS does NOT contain wildcards
□ [CONFIG]   LOG_LEVEL set to WARNING (or INFO for initial monitoring)
□ [CONFIG]   SENTRY_DSN set

□ [DB]       Alembic migrations applied (alembic upgrade head)
□ [DB]       System roles seeded (superadmin, admin, editor, viewer)
□ [DB]       System permissions seeded
□ [DB]       Partition for current month created (audit_logs)
□ [DB]       Partition automation configured (pg_partman or cron)
□ [DB]       Unique partial indexes verified (WHERE deleted_at IS NULL)
□ [DB]       Database connection pool limits confirmed
□ [DB]       PgBouncer configured (transaction mode, 200 max connections)
□ [DB]       Neon PITR retention confirmed (7 days)

□ [JWT]      RS256 key pair generated
□ [JWT]      JWKS endpoint returns valid public keys
□ [JWT]      kid value matches between JWT header and JWKS
□ [JWT]      Key rotation process documented and tested
□ [JWT]      Clock skew buffer set to 30 seconds

□ [SECURITY] HSTS preload eligibility confirmed
□ [SECURITY] CSP policy reviewed and tightened
□ [SECURITY] TLS 1.3 enforced at load balancer
□ [SECURITY] Rate limit thresholds tuned for expected traffic
□ [SECURITY] Email service SPF/DKIM/DMARC configured
□ [SECURITY] Argon2 timing benchmarked (< 1s per verification)
□ [SECURITY] Password policy confirmed (12 chars, 3/4 classes)
□ [SECURITY] Common password list loaded (10k entries)
□ [SECURITY] Disposable email domain list loaded (100+ domains)
□ [SECURITY] Account lockout threshold confirmed (5 attempts)
□ [SECURITY] Lockout duration confirmed (15 min)

□ [CLERK]    Webhook signing secret matches Clerk dashboard
□ [CLERK]    Svix library verified for webhook validation
□ [CLERK]    Test webhook events processed in staging

□ [OAUTH]    Google OAuth consent screen configured
□ [OAUTH]    GitHub OAuth app configured
□ [OAUTH]    Redirect URIs registered in Google/GitHub dashboards
□ [OAUTH]    Test OAuth flows completed in staging

□ [EMAIL]    SMTP relay confirmed operational
□ [EMAIL]    Email templates reviewed (verification, reset, confirmation)
□ [EMAIL]    Rate limits on email sending confirmed

□ [RATE LIMIT] Token bucket parameters tuned per tier
□ [RATE LIMIT] Redis cluster sized for rate limit keys

□ [LOGGING]  Structured JSON logging verified
□ [LOGGING]  Audit log retention confirmed (90d hot + 1y warm + 7y cold)
□ [LOGGING]  Audit log partition for current month created
□ [LOGGING]  Logs shipping to central observability (SigNoz / Axiom)

□ [TASKS]    Session cleanup cron job registered (hourly)
□ [TASKS]    Audit archive cron job registered (daily)
□ [TASKS]    Soft-delete purge cron job registered (weekly)

□ [TESTS]    All unit tests passing (40+)
□ [TESTS]    All integration tests passing (15)
□ [TESTS]    All E2E tests passing (3)
□ [TESTS]    Security tests passing (timing, enumeration, JWT none)
□ [TESTS]    Performance benchmarks meet thresholds
```

### 29.2 Post-Deployment Verification

```
□ Health endpoint returns 200
□ /api/v1/auth/login returns 200 with valid credentials
□ /api/v1/auth/login returns 401 with invalid credentials
□ /api/v1/auth/register creates user and sends verification email
□ /api/v1/auth/refresh rotates tokens successfully
□ /api/v1/auth/logout clears cookie and revokes session
□ /.well-known/jwks.json returns valid JWKS
□ GET /api/v1/auth/me returns user profile with valid JWT
□ GET /api/v1/auth/me returns 401 with expired JWT
□ Admin endpoints return 403 for non-admin users
□ Rate limited endpoint returns 429 with Retry-After header
□ CORS preflight returns correct headers for known origins
□ Security headers present on all responses
```

### 29.3 Monitoring Setup

```
Alerts to configure:
  - Login failure rate > 10% in 5 min (possible brute force)
  - Token theft events > 0 (active attack)
  - Argon2 verification time > 1s (hardware issue)
  - Rate limit hit rate > 20% (legitimate users being blocked)
  - Registration rate spike > 5x normal (possible bot attack)
  - Audit log partition nearing capacity

Dashboards:
  - Auth success/failure rate (time series)
  - Token refresh vs. re-login ratio
  - Active sessions per user (distribution)
  - P95 auth endpoint latency
  - JWKS cache hit ratio
  - Rate limit bucket utilization
```

### 29.4 Incident Response

```
Scenario 1: Brute Force Attack
  Detection:  Login failure rate alert
  Response:   IP-based rate limit tightening
              CAPTCHA enforcement on /login
              Manual account lockout for targeted users

Scenario 2: Token Theft / Session Hijacking
  Detection:  Token theft event in audit log
  Response:   Mass session revocation for affected families
              Force password reset for affected users
              IP block on attacker IPs
              Incident report

Scenario 3: OAuth Provider Outage
  Detection:  Google/GitHub OAuth callback error rate spike
  Response:   Graceful degradation (disable OAuth login buttons)
              Serve error message: "Login with email/password"
              Monitor provider status page
              Re-enable after confirmed recovery

Scenario 4: Database Connection Pool Exhaustion
  Detection:  Connection wait time > 1s
  Response:   Scale up API pods
              Reduce PgBouncer pool size per pod
              Restart stalled connections
              Investigate unclosed session leaks

Scenario 5: JWT Signing Key Compromise
  Detection:  Security audit or external report
  Response:   Immediate key rotation (new kid)
              Revoke ALL sessions and refresh tokens
              Force all users to re-login
              Audit all JWTs signed with compromised key
              Incident report + post-mortem
```