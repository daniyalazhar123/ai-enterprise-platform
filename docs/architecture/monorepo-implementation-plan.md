# Monorepo Implementation Plan — Enterprise AI Engineering Platform

> **Stack:** pnpm · TurboRepo · Next.js 15 · Docusaurus · FastAPI · Docker · Kubernetes · Kafka · GitHub Actions

---

## 1. Directory Structure

```
ai-enterprises/
│
├── .github/
│   └── workflows/
│       ├── ci.yml                          # PR checks: lint, typecheck, test, build
│       ├── cd.yml                          # Main branch: build, tag, push images
│       ├── deploy-staging.yml              # Manual / auto-deploy to staging
│       ├── deploy-production.yml           # Manual approval gate to production
│       ├── docs-publish.yml                # Docusaurus build + deploy
│       ├── dependency-review.yml           # Security scan on PR dependencies
│       └── cleanup.yml                     # Prune old artifacts and images
│
├── .gitignore
├── .npmrc                                  # pnpm config: strict, hoist=false
├── .prettierrc                             # Shared formatter config
├── .eslintrc.js                            # Root ESLint config
├── .env.example                            # All env vars documented
├── .dockerignore                           # Global dockerignore
│
├── package.json                            # Root workspace package.json
├── pnpm-workspace.yaml                     # Workspace definition
├── turbo.json                              # TurboRepo pipeline
├── tsconfig.base.json                      # Shared TypeScript base config
│
├── apps/
│   ├── web/                                # Next.js 15 frontend
│   │   ├── .env.example
│   │   ├── .env.local                      # Local dev (gitignored)
│   │   ├── .eslintrc.js
│   │   ├── next.config.ts
│   │   ├── tailwind.config.ts
│   │   ├── postcss.config.js
│   │   ├── tsconfig.json
│   │   ├── package.json
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx
│   │   │   ├── globals.css
│   │   │   ├── (auth)/
│   │   │   │   ├── login/
│   │   │   │   └── register/
│   │   │   ├── (dashboard)/
│   │   │   │   ├── page.tsx
│   │   │   │   └── settings/
│   │   │   └── api/
│   │   │       └── auth/
│   │   ├── components/
│   │   │   ├── ui/                         # Shared UI primitives
│   │   │   └── layout/                     # Navigation, sidebar, header
│   │   ├── hooks/
│   │   ├── lib/                            # API client, utilities
│   │   ├── public/
│   │   └── styles/
│   │
│   ├── api/                                # FastAPI backend
│   │   ├── .env.example
│   │   ├── .dockerignore
│   │   ├── Dockerfile
│   │   ├── package.json                    # Only for workspace dependency tracking
│   │   ├── pyproject.toml
│   │   ├── requirements.txt
│   │   ├── alembic.ini
│   │   ├── main.py
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── core/
│   │   │   ├── db/
│   │   │   ├── models/
│   │   │   ├── api/
│   │   │   ├── auth/
│   │   │   ├── ai/
│   │   │   └── tasks/
│   │   ├── alembic/
│   │   │   ├── env.py
│   │   │   └── versions/
│   │   └── tests/
│   │       ├── conftest.py
│   │       ├── auth/
│   │       ├── ai/
│   │       └── api/
│   │
│   └── book/                               # Docusaurus documentation
│       ├── .env.example
│       ├── package.json
│       ├── docusaurus.config.ts
│       ├── sidebars.ts
│       ├── tsconfig.json
│       ├── src/
│       │   ├── pages/
│       │   │   └── index.tsx
│       │   ├── components/
│       │   └── css/
│       ├── docs/
│       │   ├── architecture/
│       │   ├── api/
│       │   ├── guides/
│       │   └── deployment/
│       ├── blog/
│       └── static/
│
├── packages/
│   ├── shared/                             # Shared TypeScript types, constants, utils
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   ├── src/
│   │   │   ├── index.ts
│   │   │   ├── types/
│   │   │   │   ├── index.ts
│   │   │   │   ├── user.ts
│   │   │   │   ├── conversation.ts
│   │   │   │   ├── document.ts
│   │   │   │   ├── quiz.ts
│   │   │   │   └── api.ts
│   │   │   ├── constants/
│   │   │   │   ├── index.ts
│   │   │   │   ├── roles.ts
│   │   │   │   └── permissions.ts
│   │   │   └── utils/
│   │   │       ├── index.ts
│   │   │       ├── validation.ts
│   │   │       └── formatting.ts
│   │   └── __tests__/
│   │
│   ├── ui/                                 # Shared React component library
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   ├── tailwind.config.ts
│   │   ├── postcss.config.js
│   │   ├── src/
│   │   │   ├── index.ts
│   │   │   ├── components/
│   │   │   │   ├── Button.tsx
│   │   │   │   ├── Card.tsx
│   │   │   │   ├── Input.tsx
│   │   │   │   ├── Modal.tsx
│   │   │   │   ├── Select.tsx
│   │   │   │   └── Spinner.tsx
│   │   │   ├── hooks/
│   │   │   │   ├── useDebounce.ts
│   │   │   │   └── useMediaQuery.ts
│   │   │   └── styles/
│   │   │       └── index.css
│   │   └── __tests__/
│   │
│   ├── config/                             # Shared configuration (eslint, tsconfig, prettier)
│   │   ├── package.json
│   │   ├── eslint/
│   │   │   ├── base.js
│   │   │   ├── next.js
│   │   │   └── react.js
│   │   ├── tsconfig/
│   │   │   ├── base.json
│   │   │   ├── nextjs.json
│   │   │   └── react-library.json
│   │   └── prettier/
│   │       └── index.js
│   │
│   ├── auth/                               # Auth logic shared across apps
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   ├── src/
│   │   │   ├── index.ts
│   │   │   ├── client.ts                   # Clerk frontend client
│   │   │   ├── middleware.ts               # Next.js middleware helpers
│   │   │   ├── session.ts                  # Session management
│   │   │   └── permissions.ts             # Permission evaluation
│   │   └── __tests__/
│   │
│   ├── prompts/                            # Prompt templates and management
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   ├── src/
│   │   │   ├── index.ts
│   │   │   ├── templates/
│   │   │   │   ├── system.ts
│   │   │   │   ├── rag.ts
│   │   │   │   └── quiz.ts
│   │   │   └── compiler.ts
│   │   └── __tests__/
│   │
│   ├── rag/                                # RAG client library
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   ├── src/
│   │   │   ├── index.ts
│   │   │   ├── client.ts                   # Qdrant / hybrid search client
│   │   │   ├── chunking.ts                 # Chunking algorithms
│   │   │   └── rerank.ts                   # Cohere re-ranker
│   │   └── __tests__/
│   │
│   └── agents/                             # AI agent definitions
│       ├── package.json
│       ├── tsconfig.json
│       ├── src/
│       │   ├── index.ts
│       │   ├── chat.ts
│       │   ├── rag.ts
│       │   └── tools/
│       │       ├── index.ts
│       │       ├── calculator.ts
│       │       └── web-search.ts
│       └── __tests__/
│
├── docker/
│   ├── .dockerignore
│   ├── docker-compose.yml                  # Local dev orchestration
│   ├── docker-compose.prod.yml             # Production-like local stack
│   ├── Dockerfile.api                      # FastAPI multi-stage build
│   ├── Dockerfile.web                      # Next.js multi-stage build
│   ├── Dockerfile.book                     # Docusaurus static build
│   ├── nginx/
│   │   ├── nginx.conf                      # Reverse proxy config
│   │   ├── nginx.dev.conf                  # Dev proxy config
│   │   └── templates/
│   │       └── default.conf.template
│   └── init/
│       ├── postgres/
│       │   └── init.sql                    # DB initialization
│       └── kafka/
│           └── init.sh                     # Kafka topic creation
│
├── k8s/
│   ├── base/
│   │   ├── kustomization.yaml
│   │   ├── namespace.yaml
│   │   ├── configmap.yaml
│   │   ├── secrets.yaml                    # Sealed secrets / External Secrets Operator
│   │   ├── api-deployment.yaml
│   │   ├── api-hpa.yaml
│   │   ├── api-service.yaml
│   │   ├── web-deployment.yaml
│   │   ├── web-hpa.yaml
│   │   ├── web-service.yaml
│   │   ├── ingress.yaml
│   │   ├── postgres.yaml                   # Neon operator or cloud: reference only
│   │   ├── redis.yaml
│   │   ├── qdrant.yaml
│   │   └── kafka.yaml                      # Strimzi operator or cloud: reference only
│   │
│   ├── overlays/
│   │   ├── staging/
│   │   │   ├── kustomization.yaml
│   │   │   ├── configmap-patch.yaml
│   │   │   ├── replica-patch.yaml
│   │   │   └── ingress-patch.yaml
│   │   └── production/
│   │       ├── kustomization.yaml
│   │       ├── configmap-patch.yaml
│   │       ├── replica-patch.yaml
│   │       ├── hpa-patch.yaml
│   │       ├── ingress-patch.yaml
│   │       ├── pod-disruption-budget.yaml
│   │       ├── network-policy.yaml
│   │       └── pdb.yaml
│   │
│   └── helm/                               # Helm charts (supplementary)
│       ├── api/
│       │   ├── Chart.yaml
│       │   ├── values.yaml
│       │   ├── values.staging.yaml
│       │   ├── values.production.yaml
│       │   └── templates/
│       │       ├── _helpers.tpl
│       │       ├── deployment.yaml
│       │       ├── hpa.yaml
│       │       ├── service.yaml
│       │       ├── serviceaccount.yaml
│       │       ├── configmap.yaml
│       │       ├── sealedsecret.yaml
│       │       ├── pdb.yaml
│       │       └── servicemonitor.yaml
│       └── web/
│           ├── Chart.yaml
│           ├── values.yaml
│           ├── values.staging.yaml
│           ├── values.production.yaml
│           └── templates/
│               ├── _helpers.tpl
│               ├── deployment.yaml
│               ├── hpa.yaml
│               ├── service.yaml
│               ├── configmap.yaml
│               └── servicemonitor.yaml
│
├── scripts/
│   ├── dev.sh                              # Start full dev environment
│   ├── build.sh                            # Build all artifacts
│   ├── test.sh                             # Run all tests
│   ├── lint.sh                             # Run all linters
│   ├── clean.sh                            # Clean all artifacts
│   ├── seed.sh                             # Seed database
│   ├── migrate.sh                          # Run Alembic migrations
│   ├── docker-build.sh                     # Build all Docker images
│   ├── docker-push.sh                      # Push images to registry
│   ├── deploy.sh                           # Deploy to environment
│   ├── k8s-apply.sh                        # Apply Kustomize overlays
│   ├── helm-install.sh                     # Install Helm charts
│   ├── kafka-topics.sh                     # Create Kafka topics
│   └── gen-env.sh                          # Generate .env from template
│
├── docs/
│   ├── .gitkeep
│   ├── api/
│   │   └── README.md
│   ├── architecture/
│   │   ├── auth-module.md
│   │   ├── database-architecture.md
│   │   └── ai-architecture.md
│   └── guides/
│       ├── local-development.md
│       ├── deployment.md
│       └── contributing.md
│
└── README.md
```

---

## 2. Workspace Configuration

### 2.1 pnpm Workspace

```
packages:
  - "apps/*"
  - "packages/*"
```

### 2.2 Dependency Graph

```
                    ┌─────────────────────────────────────────────────┐
                    │                  Root                           │
                    │  eslint, prettier, typescript, turbo, husky     │
                    └─────────────────────────────────────────────────┘
                                      │
            ┌─────────────────────────┼─────────────────────────┐
            │                         │                         │
            ▼                         ▼                         ▼
     ┌───────────┐            ┌──────────────┐          ┌──────────────┐
     │           │            │              │          │              │
     │ apps/web  │            │  apps/api    │          │  apps/book   │
     │ (Next.js) │            │  (FastAPI)   │          │ (Docusaurus) │
     │           │            │              │          │              │
     └─────┬─────┘            └──────────────┘          └──────────────┘
           │
           │  ┌────────────────────────────────────────────────────┐
           │  │                    Packages                        │
           │  │                                                    │
           ├──→  @ai-enterprises/shared   (types, constants, utils)│
           ├──→  @ai-enterprises/ui       (React components)       │
           ├──→  @ai-enterprises/auth     (Clerk, middleware)      │
           ├──→  @ai-enterprises/prompts  (prompt templates)       │
           ├──→  @ai-enterprises/rag      (search client)          │
           └──→  @ai-enterprises/agents   (agent definitions)      │
                                                    │              │
           ┌────────────────────────────────────────┘              │
           │                                                       │
           ▼                                                       │
     ┌───────────┐                                                 │
     │           │                                                 │
     │ packages/ │  ← All packages depend on config                │
     │ config    │                                                 │
     │ (dev only)│                                                 │
     └───────────┘                                                 │
                                                                    │
           ┌───────────────────────────────────────────────────────┘
           │
           ▼
     ┌───────────┐
     │           │
     │  apps/web │  Also depends on: apps/api (via fetch/axios)
     │           │
     └───────────┘
```

### 2.3 Package Scope Naming

| Package | npm Scope | Path |
|---|---|---|
| Shared types | `@ai-enterprises/shared` | `packages/shared` |
| UI components | `@ai-enterprises/ui` | `packages/ui` |
| Auth library | `@ai-enterprises/auth` | `packages/auth` |
| Prompt templates | `@ai-enterprises/prompts` | `packages/prompts` |
| RAG client | `@ai-enterprises/rag` | `packages/rag` |
| Agent definitions | `@ai-enterprises/agents` | `packages/agents` |
| Shared config | `@ai-enterprises/config` | `packages/config` |

---

## 3. Packages

### 3.1 Package Inventory

| # | Package | Type | Language | Build Tool | Publishes |
|---|---|---|---|---|---|
| 1 | `@ai-enterprises/shared` | Library | TypeScript | tsc | npm (internal) |
| 2 | `@ai-enterprises/ui` | Library (React) | TypeScript + CSS | tsc + PostCSS | npm (internal) |
| 3 | `@ai-enterprises/auth` | Library | TypeScript | tsc | npm (internal) |
| 4 | `@ai-enterprises/prompts` | Library | TypeScript | tsc | npm (internal) |
| 5 | `@ai-enterprises/rag` | Library | TypeScript | tsc | npm (internal) |
| 6 | `@ai-enterprises/agents` | Library | TypeScript | tsc | npm (internal) |
| 7 | `@ai-enterprises/config` | Dev only | JavaScript | — | — |

### 3.2 Package Dependency Matrix

```
                    ┌────────┬──────┬──────┬────────┬────────┬────────┬────────┐
                    │ config │shared│  ui  │ auth   │prompts │  rag   │ agents │
┌───────────────────┼────────┼──────┼──────┼────────┼────────┼────────┼────────┤
│ config            │   —    │  —   │  —   │   —    │   —    │   —    │   —    │
│ shared            │   ✓    │  —   │  —   │   —    │   —    │   —    │   —    │
│ ui                │   ✓    │  ✓   │  —   │   —    │   —    │   —    │   —    │
│ auth              │   ✓    │  ✓   │  —   │   —    │   —    │   —    │   —    │
│ prompts           │   ✓    │  ✓   │  —   │   —    │   —    │   —    │   —    │
│ rag               │   ✓    │  ✓   │  —   │   —    │   —    │   —    │   —    │
│ agents            │   ✓    │  ✓   │  —   │   ✓    │   ✓    │   ✓    │   —    │
│ apps/web          │   ✓    │  ✓   │  ✓   │   ✓    │   —    │   —    │   —    │
│ apps/api          │   —    │  —   │  —   │   —    │   ✓    │   ✓    │   ✓    │
│ apps/book         │   —    │  —   │  —   │   —    │   —    │   —    │   —    │
└───────────────────┴────────┴──────┴──────┴────────┴────────┴────────┴────────┘
```

### 3.3 Package Build Configuration

| Package | `main` | `module` | `types` | `files` |
|---|---|---|---|---|
| shared | `dist/index.js` | `dist/index.mjs` | `dist/index.d.ts` | `dist` |
| ui | `dist/index.js` | `dist/index.mjs` | `dist/index.d.ts` | `dist` |
| auth | `dist/index.js` | `dist/index.mjs` | `dist/index.d.ts` | `dist` |
| prompts | `dist/index.js` | `dist/index.mjs` | `dist/index.d.ts` | `dist` |
| rag | `dist/index.js` | `dist/index.mjs` | `dist/index.d.ts` | `dist` |
| agents | `dist/index.js` | `dist/index.mjs` | `dist/index.d.ts` | `dist` |

---

## 4. Apps

### 4.1 apps/web — Next.js 15

| Property | Value |
|---|---|
| Framework | Next.js 15 (App Router) |
| Port (dev) | 3000 |
| Port (prod) | 3000 |
| Build output | `.next/` |
| Docker base | `node:22-alpine` |
| Dependencies | `@ai-enterprises/shared`, `@ai-enterprises/ui`, `@ai-enterprises/auth` |
| Environment | `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_CLERK_KEY`, `AUTH_SECRET` |

### 4.2 apps/api — FastAPI

| Property | Value |
|---|---|
| Framework | FastAPI + Uvicorn |
| Port (dev) | 8000 |
| Port (prod) | 8000 |
| ASGI workers | 4 (prod) |
| Build output | `dist/` (Python package) |
| Docker base | `python:3.12-slim` |
| Dependencies | `@ai-enterprises/prompts`, `@ai-enterprises/rag`, `@ai-enterprises/agents` (type stubs) |
| Environment | `DATABASE_URL`, `REDIS_URL`, `QDRANT_URL`, `OPENAI_API_KEY`, `CLERK_SECRET_KEY` |

### 4.3 apps/book — Docusaurus

| Property | Value |
|---|---|
| Framework | Docusaurus 3 |
| Port (dev) | 3001 |
| Build output | `build/` (static HTML) |
| Docker base | `nginx:alpine` (serves static) |
| CI trigger | Changes to `apps/book/` or `docs/` |

---

## 5. Infrastructure

### 5.1 Service Inventory

| Service | Technology | Managed / Self-hosted | Criticality |
|---|---|---|---|
| PostgreSQL | Neon (PostgreSQL 16) | Managed | Tier 0 |
| Redis | Upstash / ElastiCache | Managed | Tier 0 |
| Qdrant | Qdrant Cloud | Managed | Tier 1 |
| Kafka | Confluent Cloud / MSK | Managed | Tier 1 |
| Object Storage | S3 / Cloudflare R2 | Managed | Tier 0 |
| Container Registry | ECR / GHCR | Managed | Tier 0 |
| Kubernetes | EKS / GKE | Managed | Tier 0 |
| CDN | CloudFront | Managed | Tier 1 |

### 5.2 Resource Requirements

| Service | CPU | Memory | Storage | Replicas |
|---|---|---|---|---|
| api | 2 cores | 4 GB | — | 2–6 (HPA) |
| web | 1 core | 2 GB | — | 2–4 (HPA) |
| book | 0.5 core | 512 MB | — | 2 |
| Redis | — | 2 GB | 5 GB | 1 (primary) + 1 (replica) |
| Qdrant | 4 cores | 8 GB | 50 GB SSD | 2 (sharded) |
| Kafka | 4 cores | 16 GB | 500 GB | 3 brokers |
| PostgreSQL | 4 cores | 16 GB | 100 GB SSD | 1 primary + 2 replicas |

### 5.3 Network Architecture

```
Internet
    │
    ▼
┌──────────────┐
│  CDN         │  CloudFront (static) + Cloudflare (DNS)
│  + WAF       │  Rate limiting, DDoS protection
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Load        │  ALB / Nginx Ingress Controller
│  Balancer    │  TLS termination, path routing
└──────┬───────┘
       │
       ├──────────────────┐
       ▼                  ▼
┌──────────────┐   ┌──────────────┐
│  apps/web    │   │  apps/api    │
│  (Next.js)   │   │  (FastAPI)   │
│  service:3000│   │  service:8000│
└──────────────┘   └──────┬───────┘
                          │
                          ├────────────────────────────┐
                          ▼                            ▼
                   ┌──────────────┐            ┌──────────────┐
                   │  Internal    │            │  Kafka       │
                   │  Services    │            │  (async)     │
                   │  PG, Redis,  │            │              │
                   │  Qdrant      │            │  → Workers   │
                   └──────────────┘            └──────────────┘
```

### 5.4 Kafka Topics

| Topic | Partitions | Retention | Messages | Producers | Consumers |
|---|---|---|---|---|---|
| `ai.embeddings.queue` | 4 | 7 days | Document indexing | API (doc upload) | Embedding workers |
| `ai.audit.logs` | 3 | 30 days | Structured audit events | API, workers | Audit archiver |
| `ai.conversation.analyze` | 2 | 3 days | Conversation metadata | API | Analytics worker |
| `ai.model.metrics` | 2 | 7 days | LLM latency/cost data | AI Gateway | Cost tracker |
| `system.health` | 1 | 1 day | Health check pings | All services | Health aggregator |

---

## 6. Development Scripts

### 6.1 Script Inventory

| Script | Command | Description |
|---|---|---|
| `dev.sh` | `pnpm dev` | Start all dev servers concurrently |
| `build.sh` | `pnpm build` | Build all packages and apps |
| `test.sh` | `pnpm test` | Run all tests across workspace |
| `lint.sh` | `pnpm lint` | Run ESLint, Prettier, mypy, ruff |
| `clean.sh` | `pnpm clean` | Clean all build artifacts |
| `seed.sh` | `pnpm seed` | Seed database with test data |
| `migrate.sh` | `pnpm migrate` | Run Alembic migrations |
| `docker-build.sh` | `docker buildx bake` | Build all Docker images |
| `docker-push.sh` | `docker push` | Push images to registry |
| `deploy.sh` | `pnpm exec turbo deploy` | Deploy to target environment |
| `k8s-apply.sh` | `kustomize build \| kubectl apply` | Apply Kubernetes manifests |
| `helm-install.sh` | `helm install` | Install Helm charts |
| `kafka-topics.sh` | `kafka-topics --create` | Create Kafka topics |
| `gen-env.sh` | `node scripts/gen-env.mjs` | Generate .env from template |

### 6.2 Workspace Scripts (package.json)

```jsonc
{
  "scripts": {
    "dev": "turbo run dev --parallel",
    "dev:web": "turbo run dev --filter=@ai-enterprises/web",
    "dev:api": "turbo run dev --filter=@ai-enterprises/api",
    "dev:book": "turbo run dev --filter=@ai-enterprises/book",
    "build": "turbo run build",
    "build:web": "turbo run build --filter=@ai-enterprises/web",
    "build:api": "turbo run build --filter=@ai-enterprises/api",
    "build:book": "turbo run build --filter=@ai-enterprises/book",
    "build:packages": "turbo run build --filter=./packages/*",
    "test": "turbo run test --parallel",
    "test:web": "turbo run test --filter=@ai-enterprises/web",
    "test:api": "cd apps/api && poetry run pytest",
    "lint": "turbo run lint --parallel",
    "lint:fix": "turbo run lint:fix --parallel",
    "format": "prettier --write .",
    "format:check": "prettier --check .",
    "clean": "turbo run clean && rm -rf node_modules",
    "typecheck": "turbo run typecheck --parallel",
    "migrate": "cd apps/api && alembic upgrade head",
    "migrate:rollback": "cd apps/api && alembic downgrade -1",
    "seed": "cd apps/api && python -m scripts.seed",
    "docker:build": "bash scripts/docker-build.sh",
    "docker:push": "bash scripts/docker-push.sh",
    "deploy": "bash scripts/deploy.sh",
    "gen-env": "node scripts/gen-env.mjs",
    "outdated": "pnpm outdated -r"
  }
}
```

---

## 7. Build Flow

### 7.1 Turbo Pipeline

```jsonc
{
  "$schema": "https://turbo.build/schema.json",
  "globalDependencies": ["tsconfig.base.json", ".env.example"],
  "pipeline": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": ["dist/**", ".next/**", "build/**"],
      "env": [
        "NEXT_PUBLIC_API_URL",
        "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY",
        "DATABASE_URL",
        "REDIS_URL",
        "QDRANT_URL"
      ]
    },
    "dev": {
      "cache": false,
      "persistent": true
    },
    "test": {
      "dependsOn": ["build"],
      "inputs": ["src/**/*.ts", "src/**/*.tsx", "__tests__/**"]
    },
    "lint": {
      "outputs": []
    },
    "typecheck": {
      "dependsOn": ["^build"],
      "outputs": []
    },
    "clean": {
      "cache": false
    }
  }
}
```

### 7.2 Build Order

```
Phase 1: Packages (parallel)
  ┌──────────────────────────────────────────┐
  │  packages/config   → build (no deps)     │
  │  packages/shared   → build (dep: config) │
  │  packages/ui       → build (dep: shared) │
  │  packages/auth     → build (dep: shared) │
  │  packages/prompts  → build (dep: shared) │
  │  packages/rag      → build (dep: shared) │
  │  packages/agents   → build (dep: shared,  │
  │                      auth, prompts, rag)  │
  └──────────────────────────────────────────┘
                      │
Phase 2: Apps (parallel, after packages)
  ┌──────────────────────────────────────────┐
  │  apps/web    → build (dep: all packages) │
  │  apps/api    → build (dep: prompts, rag, │
  │                          agents)         │
  │  apps/book   → build (no workspace deps) │
  └──────────────────────────────────────────┘
                      │
Phase 3: Docker (serial or parallel-batched)
  ┌──────────────────────────────────────────┐
  │  docker build -t api:tag                 │
  │  docker build -t web:tag                 │
  │  docker build -t book:tag                │
  └──────────────────────────────────────────┘
                      │
Phase 4: Push (serial, after all images built)
  ┌──────────────────────────────────────────┐
  │  docker push api:tag                     │
  │  docker push web:tag                     │
  │  docker push book:tag                    │
  └──────────────────────────────────────────┘
```

### 7.3 Caching Strategy

| Artifact | Cache Storage | TTL | Invalidation |
|---|---|---|---|
| Turbo cache (local) | `.turbo/` | Per run | Input file hash change |
| Turbo cache (remote) | S3 / Vercel Remote Caching | 7 days | Branch mismatch |
| pnpm store | `~/.local/share/pnpm/store` | Indefinite | Lockfile change |
| Docker layers | Local Docker cache | Indefinite | Dockerfile or context change |
| Next.js build cache | `.next/cache` | Per build | Source change |
| pip cache | `~/.cache/pip` | Indefinite | requirements.txt change |

---

## 8. Test Flow

### 8.1 Test Configuration

| App/Package | Framework | Run Command | Coverage Target |
|---|---|---|---|
| packages/shared | Vitest | `pnpm --filter shared test` | 90% |
| packages/ui | Vitest + Testing Library | `pnpm --filter ui test` | 85% |
| packages/auth | Vitest | `pnpm --filter auth test` | 90% |
| packages/prompts | Vitest | `pnpm --filter prompts test` | 95% |
| packages/rag | Vitest | `pnpm --filter rag test` | 90% |
| packages/agents | Vitest | `pnpm --filter agents test` | 85% |
| apps/web | Vitest + Playwright | `pnpm --filter web test` | 80% (unit), 90% (e2e) |
| apps/api | pytest | `cd apps/api && pytest` | 90% |
| apps/book | — | — | (no tests) |

### 8.2 Test Pyramid

```
         /\
        /  \
       / E2E \          Playwright (web) + pytest e2e (api)
      /────────\         3 critical user journeys
     /          \
    / Integration \     API integration, DB integration, AI mock tests
   /──────────────\     15 test suites
  /                \
 /   Unit Tests     \   40+ test files across all packages + apps
/────────────────────\
```

### 8.3 CI Test Order

```
Step 1:  pnpm install --frozen-lockfile
Step 2:  pnpm lint
Step 3:  pnpm typecheck
Step 4:  turbo run test --filter=./packages/*     (parallel, fast)
Step 5:  turbo run test --filter=@ai-enterprises/web  (unit)
Step 6:  cd apps/api && pytest --cov              (unit + integration)
Step 7:  pnpm exec playwright install             (e2e deps)
Step 8:  pnpm exec playwright test                (e2e, on staging deploy)
```

---

## 9. Deployment Flow

### 9.1 Environments

| Environment | URL | Kubernetes Cluster | DB | Auto-deploy |
|---|---|---|---|---|
| Local | `localhost:3000` | — | Docker PostgreSQL | Manual |
| Review | `pr-{number}.dev.ai-enterprises.com` | Staging EKS | Neon branch | PR opened |
| Staging | `staging.ai-enterprises.com` | Staging EKS | Neon staging | Main branch |
| Production | `app.ai-enterprises.com` | Production EKS | Neon production | Manual approval |

### 9.2 Deployment Pipeline

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  Feature Branch                                                        │
│      │                                                                  │
│      ▼                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │  CI Pipeline (GitHub Actions)                                │       │
│  │                                                              │       │
│  │  1. pnpm install --frozen-lockfile                          │       │
│  │  2. pnpm lint                                                │       │
│  │  3. pnpm typecheck                                           │       │
│  │  4. pnpm exec turbo run build --filter=./packages/*          │       │
│  │  5. pnpm exec turbo run test --filter=./packages/*           │       │
│  │  6. apps/api: pytest                                         │       │
│  │  7. apps/web: vitest                                         │       │
│  │  8. Security: dependency review, codeQL                      │       │
│  │                                                              │       │
│  │  (All checks must pass before merge)                         │       │
│  └─────────────────────────────────────────────────────────────┘       │
│                                                                         │
│  Merge to main                                                          │
│      │                                                                  │
│      ▼                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │  CD Pipeline (GitHub Actions)                                │       │
│  │                                                              │       │
│  │  1. pnpm install --frozen-lockfile                          │       │
│  │  2. pnpm build                                               │       │
│  │  3. Build Docker images (bake)                               │       │
│  │     - api:{sha}                                              │       │
│  │     - web:{sha}                                              │       │
│  │     - book:{sha}                                             │       │
│  │  4. Tag images                                               │       │
│  │     - latest, {semver}                                       │       │
│  │  5. Push to ECR / GHCR                                      │       │
│  │  6. Run DB migrations (alembic upgrade head)                 │       │
│  │  7. Deploy to staging                                        │       │
│  │     - kustomize build | kubectl apply -f -                  │       │
│  │  8. Smoke tests (helm test / playwright)                     │       │
│  │                                                              │       │
│  └─────────────────────────────────────────────────────────────┘       │
│                                                                         │
│  Approval Gate (Production)                                             │
│      │                                                                  │
│      ▼                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │  Production Deployment (manual trigger)                      │       │
│  │                                                              │       │
│  │  1. GitHub Environment approval (required)                   │       │
│  │  2. Promote staging tag to production tag                    │       │
│  │     - api:staging-{sha} → api:production                     │       │
│  │  3. Deploy to production (rolling update)                    │       │
│  │     - helm upgrade --values values.production.yaml           │       │
│  │  4. Health check (readiness probe, 5 min timeout)            │       │
│  │  5. Run DB migrations (alembic upgrade head)                 │       │
│  │  6. Smoke tests (production endpoint checks)                 │       │
│  │  7. Rollback on failure (helm rollback)                     │       │
│  │                                                              │       │
│  └─────────────────────────────────────────────────────────────┘       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 9.3 Rollback Strategy

| Scenario | Action | Time |
|---|---|---|
| Deployment fails health check | Automatic rollback to previous release | < 2 min |
| Migration breaks read path | `alembic downgrade -1`, rollback app | < 5 min |
| Migration breaks write path | Feature flag toggle, rollback at convenience | < 1 min |
| Config error detected | `kubectl rollout undo deployment/api` | < 30s |
| Infrastructure failure | Restore from backup, redeploy last stable | < 30 min |

---

## 10. Environment Variables

### 10.1 Variable Inventory

| Variable | Scope | Required | Secret | Source |
|---|---|---|---|---|
| `NODE_ENV` | all apps | Yes | No | Inferred |
| `NEXT_PUBLIC_API_URL` | web | Yes | No | ConfigMap |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | web | Yes | No | ConfigMap |
| `NEXT_PUBLIC_APP_URL` | web | Yes | No | ConfigMap |
| `NEXT_PUBLIC_POSTHOG_KEY` | web | No | No | ConfigMap |
| `AUTH_SECRET` | api | Yes | Yes | Secret Store |
| `DATABASE_URL` | api | Yes | Yes | Secret Store |
| `DATABASE_POOL_MIN` | api | No | No | ConfigMap |
| `DATABASE_POOL_MAX` | api | No | No | ConfigMap |
| `REDIS_URL` | api | Yes | Yes | Secret Store |
| `REDIS_PREFIX` | api | No | No | ConfigMap |
| `QDRANT_URL` | api | Yes | Yes | Secret Store |
| `QDRANT_API_KEY` | api | Yes | Yes | Secret Store |
| `QDRANT_COLLECTION` | api | No | No | ConfigMap |
| `OPENAI_API_KEY` | api | Yes | Yes | Secret Store |
| `OPENAI_ORGANIZATION` | api | No | Yes | Secret Store |
| `GOOGLE_API_KEY` | api | No | Yes | Secret Store |
| `GROK_API_KEY` | api | No | Yes | Secret Store |
| `OPENROUTER_API_KEY` | api | No | Yes | Secret Store |
| `COHERE_API_KEY` | api | Yes | Yes | Secret Store |
| `CLERK_SECRET_KEY` | api | Yes | Yes | Secret Store |
| `CLERK_WEBHOOK_SECRET` | api | Yes | Yes | Secret Store |
| `KAFKA_BROKERS` | api | No | Yes | Secret Store |
| `KAFKA_CLIENT_ID` | api | No | No | ConfigMap |
| `S3_ENDPOINT` | api | Yes | Yes | Secret Store |
| `S3_REGION` | api | No | No | ConfigMap |
| `S3_BUCKET_DOCUMENTS` | api | No | No | ConfigMap |
| `S3_BUCKET_AUDIO` | api | No | No | ConfigMap |
| `S3_ACCESS_KEY_ID` | api | Yes | Yes | Secret Store |
| `S3_SECRET_ACCESS_KEY` | api | Yes | Yes | Secret Store |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | all | No | No | ConfigMap |
| `OTEL_SERVICE_NAME` | all | No | No | ConfigMap |
| `SENTRY_DSN` | all | No | Yes | Secret Store |
| `LOG_LEVEL` | all | No | No | ConfigMap |

### 10.2 Environment-Specific Overrides

| Variable | Local | Staging | Production |
|---|---|---|---|
| `DATABASE_URL` | `postgres://localhost:5432/ai-enterprises` | Neon staging URL | Neon production URL |
| `REDIS_URL` | `redis://localhost:6379` | Upstash staging | Upstash production |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant cloud staging | Qdrant cloud production |
| `KAFKA_BROKERS` | `localhost:9092` | Confluent staging | Confluent production |
| `S3_ENDPOINT` | `http://localhost:9000` (MinIO) | S3 staging | S3 production |
| `LOG_LEVEL` | `DEBUG` | `INFO` | `WARNING` |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | `https://staging.api.ai-enterprises.com` | `https://api.ai-enterprises.com` |

### 10.3 .env File Loading Order

```
Root .env                        → Git ignored, local overrides
apps/web/.env.local              → Git ignored, Next.js specific
apps/web/.env.production         → Git tracked, production defaults
apps/api/.env                    → Git ignored, FastAPI specific
k8s/base/configmap.yaml          → Git tracked, Kubernetes non-secret
k8s/base/secrets.yaml            → SealedSecret, Git tracked encrypted
External Secrets Operator        → Syncs from AWS Secrets Manager / Vault
```

---

## 11. Secrets

### 11.1 Secret Inventory

| Secret Name | Provider | Rotation | Access |
|---|---|---|---|
| `DATABASE_URL` | AWS Secrets Manager | 90 days | API service account |
| `REDIS_URL` | AWS Secrets Manager | 90 days | API service account |
| `QDRANT_API_KEY` | AWS Secrets Manager | 90 days | API service account |
| `OPENAI_API_KEY` | AWS Secrets Manager | 90 days | API, embedding worker |
| `GOOGLE_API_KEY` | AWS Secrets Manager | 90 days | API |
| `GROK_API_KEY` | AWS Secrets Manager | 90 days | API |
| `OPENROUTER_API_KEY` | AWS Secrets Manager | 90 days | API |
| `COHERE_API_KEY` | AWS Secrets Manager | 90 days | API, embedding worker |
| `CLERK_SECRET_KEY` | AWS Secrets Manager | 90 days | API, web |
| `CLERK_WEBHOOK_SECRET` | AWS Secrets Manager | 90 days | API |
| `AUTH_SECRET` | AWS Secrets Manager | 90 days | API, web |
| `S3_ACCESS_KEY_ID` | AWS Secrets Manager | 90 days | API, embedding worker |
| `S3_SECRET_ACCESS_KEY` | AWS Secrets Manager | 90 days | API, embedding worker |
| `KAFKA_API_KEY` | AWS Secrets Manager | 90 days | API |
| `KAFKA_API_SECRET` | AWS Secrets Manager | 90 days | API |
| `SENTRY_DSN` | AWS Secrets Manager | Per project | API, web |
| `SLACK_WEBHOOK_URL` | AWS Secrets Manager | Per incident | Deployment pipeline |
| `DOCKER_REGISTRY_PASSWORD` | GitHub Secrets | Per rotation | CI/CD |

### 11.2 Secret Management Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                    Secret Management Pipeline                        │
│                                                                      │
│  Developer                                                           │
│      │                                                               │
│      ▼                                                               │
│  ┌──────────────────────┐                                            │
│  │  kubeseal            │  Encrypt secret to SealedSecret            │
│  │  < raw-secret.yaml   │                                            │
│  │  --cert pub-cert.pem │                                            │
│  └─────────┬────────────┘                                            │
│            │                                                         │
│            ▼                                                         │
│  ┌──────────────────────┐                                            │
│  │  SealedSecret        │  Committed to Git (encrypted)              │
│  │  k8s/base/           │                                            │
│  │  secrets.yaml        │                                            │
│  └─────────┬────────────┘                                            │
│            │                                                         │
│            ▼                                                         │
│  ┌──────────────────────┐                                            │
│  │  External Secrets    │  Development / Staging: fetch from Vault   │
│  │  Operator            │  Production: fetch from AWS Secrets Mgr   │
│  └─────────┬────────────┘                                            │
│            │                                                         │
│            ▼                                                         │
│  ┌──────────────────────┐                                            │
│  │  Kubernetes Secret   │  Mounted as env vars or volumes            │
│  │  (in-cluster)        │  Never logged, never in git (unencrypted)  │
│  └──────────────────────┘                                            │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 11.3 Secret Access Control

| Role | Can Read Secrets | Can Create/Update Secrets |
|---|---|---|
| Developer (local) | .env.local only | No |
| CI/CD pipeline | Deployment secrets (GitHub Secrets) | No |
| External Secrets Operator | Full access (via IAM role) | No |
| Platform engineering | All secrets (via Vault) | Yes |
| Production deployment | Production secrets only | No |

---

## 12. Docker Structure

### 12.1 Dockerfile Strategy

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Multi-Stage Build Strategy                          │
│                                                                         │
│  Stage 1: Install & Build (base: node:22-alpine / python:3.12-slim)     │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │  - Install system dependencies (build-essential, curl, git)  │      │
│  │  - Install pnpm                                              │      │
│  │  - pnpm install --frozen-lockfile                            │      │
│  │  - Copy packages + app source                                │      │
│  │  - pnpm build                                                │      │
│  └──────────────────────────────────────────────────────────────┘      │
│                                                                         │
│  Stage 2: Production (base: node:22-alpine / python:3.12-slim)         │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │  - Copy only built artifacts from Stage 1                    │      │
│  │  - Copy production node_modules (pruned)                     │      │
│  │  - Install runtime system dependencies (ca-certificates)     │      │
│  │  - Set user to non-root (node / appuser)                     │      │
│  │  - Set WORKDIR, EXPOSE, ENTRYPOINT, CMD                      │      │
│  │  - HEALTHCHECK instruction                                   │      │
│  └──────────────────────────────────────────────────────────────┘      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 12.2 Dockerfiles

| Dockerfile | Base Image | Stages | Entry Point |
|---|---|---|---|
| `Dockerfile.api` | `python:3.12-slim` | Builder, Production | `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4` |
| `Dockerfile.web` | `node:22-alpine` | Dependencies, Builder, Runner | `node server.js` (standalone output) |
| `Dockerfile.book` | `node:22-alpine` (build), `nginx:alpine` (serve) | Builder, Nginx | `nginx -g daemon off;` |

### 12.3 Docker Compose Topology (Local)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      docker-compose.yml Topology                        │
│                                                                         │
│  Services:                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                 │
│  │  nginx       │  │  web         │  │  api         │                  │
│  │  port: 80    │──│  port: 3000  │  │  port: 8000  │                  │
│  │  (reverse    │  │  (Next.js)   │  │  (FastAPI)   │                  │
│  │   proxy)     │  └──────────────┘  └──────┬───────┘                  │
│  └──────────────┘                           │                          │
│                                              │                          │
│                    ┌─────────────────────────┼──────────────┐          │
│                    │                         │              │          │
│                    ▼                         ▼              ▼          │
│           ┌──────────────┐          ┌──────────────┐ ┌──────────────┐ │
│           │  postgres    │          │  redis       │ │  qdrant      │ │
│           │  port: 5432  │          │  port: 6379  │ │  port: 6333  │ │
│           │  Neon compat │          └──────────────┘ └──────────────┘ │
│           └──────────────┘                                            │
│  ┌──────────────┐  ┌──────────────┐                                   │
│  │  kafka       │  │  minio       │                                   │
│  │  port: 9092  │  │  port: 9000  │                                   │
│  │  (+ KRaft)   │  │  (S3 compat) │                                   │
│  └──────────────┘  └──────────────┘                                   │
│                                                                         │
│  Networks:                                                              │
│    frontend: web, nginx                                                 │
│    backend:  api, postgres, redis, qdrant, kafka, minio                │
│                                                                         │
│  Volumes:                                                               │
│    postgres_data, redis_data, qdrant_data, kafka_data, minio_data      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 13. Helm Structure

### 13.1 Chart Organization

```
k8s/helm/
├── api/
│   ├── Chart.yaml                  # api: appVersion: 0.1.0
│   ├── values.yaml                 # Default values (dev)
│   ├── values.staging.yaml         # Staging overrides
│   ├── values.production.yaml      # Production overrides
│   └── templates/
│       ├── _helpers.tpl            # Template helpers: labels, selectors, names
│       ├── deployment.yaml         # Deployment spec
│       ├── hpa.yaml                # HorizontalPodAutoscaler
│       ├── service.yaml            # ClusterIP service
│       ├── serviceaccount.yaml     # ServiceAccount + IAM annotations
│       ├── configmap.yaml          # Non-sensitive env vars
│       ├── sealedsecret.yaml       # SealedSecret (encrypted in git)
│       ├── pdb.yaml                # PodDisruptionBudget (min 2 available)
│       └── servicemonitor.yaml     # Prometheus ServiceMonitor
│
└── web/
    ├── Chart.yaml                  # web: appVersion: 0.1.0
    ├── values.yaml
    ├── values.staging.yaml
    ├── values.production.yaml
    └── templates/
        ├── _helpers.tpl
        ├── deployment.yaml
        ├── hpa.yaml
        ├── service.yaml
        ├── configmap.yaml
        └── servicemonitor.yaml
```

### 13.2 Helm Values Structure

```yaml
# values.yaml structure (pseudocode)

global:
  environment: production
  region: us-east-1

image:
  repository: ghcr.io/ai-enterprises/api
  tag: latest
  pullPolicy: Always

replicaCount: 2
revisionHistoryLimit: 3

containerPort: 8000

resources:
  requests:
    cpu: 500m
    memory: 512Mi
  limits:
    cpu: 2
    memory: 4Gi

hpa:
  enabled: true
  minReplicas: 2
  maxReplicas: 6
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80

probes:
  liveness:
    path: /health
    initialDelaySeconds: 30
    periodSeconds: 10
  readiness:
    path: /ready
    initialDelaySeconds: 15
    periodSeconds: 5
  startup:
    path: /startup
    initialDelaySeconds: 5
    periodSeconds: 5
    failureThreshold: 30

service:
  port: 80
  targetPort: 8000
  type: ClusterIP

ingress:
  enabled: true
  className: nginx
  host: app.ai-enterprises.com
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/enable-cors: "true"

configmap:
  data:
    LOG_LEVEL: WARNING
    REDIS_PREFIX: ai-enterprises
    QDRANT_COLLECTION: ai_enterprises_embeddings_v1
    S3_REGION: us-east-1
    S3_BUCKET_DOCUMENTS: ai-enterprises-documents
    S3_BUCKET_AUDIO: ai-enterprises-audio

sealedSecrets:
  DATABASE_URL: AgAA... (encrypted)
  REDIS_URL: AgBB... (encrypted)
  OPENAI_API_KEY: AgCC... (encrypted)

podDisruptionBudget:
  minAvailable: 2

serviceMonitor:
  enabled: true
  interval: 30s
  scrapeTimeout: 10s

nodeSelector:
  type: general-purpose

tolerations: []

affinity:
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        podAffinityTerm:
          labelSelector:
            matchLabels:
              app: api
          topologyKey: kubernetes.io/hostname
```

---

## 14. CI/CD Structure

### 14.1 CI Pipeline — `ci.yml`

```
Trigger: pull_request (opened, synchronize, reopened)

Concurrency: ${{ github.workflow }}-${{ github.ref }}

Environment: github-actions

Jobs:
  1. lint:
      runs-on: ubuntu-latest
      steps:
        - Checkout
        - Setup pnpm (corepack enable, pnpm install)
        - pnpm lint
        - pnpm format:check

  2. typecheck:
      runs-on: ubuntu-latest
      steps:
        - Checkout
        - Setup pnpm
        - pnpm typecheck

  3. test-packages:
      runs-on: ubuntu-latest
      needs: [lint, typecheck]
      steps:
        - Checkout
        - Setup pnpm
        - turbo run test --filter=./packages/*
        - Upload coverage reports

  4. test-api:
      runs-on: ubuntu-latest
      needs: [lint, typecheck]
      services:
        postgres: postgres:16-alpine
        redis: redis:7-alpine
      steps:
        - Checkout
        - Setup Python 3.12 + Poetry
        - cd apps/api && poetry install
        - cd apps/api && pytest --cov --cov-report=xml
        - Upload coverage to Codecov

  5. test-web:
      runs-on: ubuntu-latest
      needs: [lint, typecheck]
      steps:
        - Checkout
        - Setup pnpm
        - turbo run test --filter=@ai-enterprises/web

  6. build:
      runs-on: ubuntu-latest
      needs: [test-packages, test-api, test-web]
      steps:
        - Checkout
        - Setup pnpm
        - pnpm build
        - Upload built artifacts (actions/upload-artifact)

  7. dependency-review:
      runs-on: ubuntu-latest
      steps:
        - Checkout
        - Dependency Review Action (fail on critical/high)
```

### 14.2 CD Pipeline — `cd.yml`

```
Trigger: push (branches: [main])

Concurrency: ${{ github.workflow }}-${{ github.ref }}

Environment: staging

Jobs:
  1. build-images:
      runs-on: ubuntu-latest
      permissions:
        contents: read
        packages: write
      outputs:
        tags: ${{ steps.meta.outputs.tags }}
      steps:
        - Checkout
        - Docker metadata action (tags: {sha}, latest, {semver})
        - Setup Docker Buildx
        - Login to GHCR
        - Build and push api: docker build -f docker/Dockerfile.api
        - Build and push web: docker build -f docker/Dockerfile.web
        - Build and push book: docker build -f docker/Dockerfile.book

  2. deploy-staging:
      runs-on: ubuntu-latest
      needs: [build-images]
      environment: staging
      steps:
        - Checkout
        - Setup kubectl + kustomize
        - kustomize build k8s/overlays/staging | kubectl apply -f -
        - kubectl rollout status deployment/api -n ai-enterprises
        - kubectl rollout status deployment/web -n ai-enterprises
        - Run smoke tests (curl health endpoints)

  3. migrate-staging:
      runs-on: ubuntu-latest
      needs: [deploy-staging]
      steps:
        - kubectl run alembic-job --image=ghcr.io/ai-enterprises/api:{sha}
        - alembic upgrade head
        - kubectl delete pod alembic-job

  4. smoke-test-staging:
      runs-on: ubuntu-latest
      needs: [migrate-staging]
      steps:
        - Run playwright tests against staging URL
        - Run API contract tests
        - Report results to GitHub commit status
```

### 14.3 Production Deployment — `deploy-production.yml`

```
Trigger: workflow_dispatch (manual)

Environment: production
  Required reviewers: [platform-engineering-team]
  Wait timer: 15 minutes
  Deployment branches: main

Jobs:
  1. validate:
      runs-on: ubuntu-latest
      steps:
        - Checkout
        - Validate git tag matches semver
        - Validate staging deployment health
        - Validate migrations have been applied on staging

  2. promote-images:
      runs-on: ubuntu-latest
      needs: [validate]
      steps:
        - Pull staging images
        - Tag as production: {v0.1.0}
        - Push to production registry

  3. deploy-production:
      runs-on: ubuntu-latest
      needs: [promote-images]
      environment: production
      steps:
        - Checkout
        - Setup Helm
        - helm upgrade --install ai-enterprises-api ./k8s/helm/api \
            --values ./k8s/helm/api/values.production.yaml \
            --set image.tag={v0.1.0} \
            --namespace ai-enterprises --wait --timeout 10m
        - helm upgrade --install ai-enterprises-web ./k8s/helm/web \
            --values ./k8s/helm/web/values.production.yaml \
            --set image.tag={v0.1.0} \
            --namespace ai-enterprises --wait --timeout 10m
        - kubectl rollout status deployment/api -n ai-enterprises
        - kubectl rollout status deployment/web -n ai-enterprises

  4. migrate-production:
      runs-on: ubuntu-latest
      needs: [deploy-production]
      steps:
        - kubectl run alembic-job-prod --image=ghcr.io/ai-enterprises/api:{v0.1.0}
        - alembic upgrade head
        - kubectl delete pod alembic-job-prod

  5. verify-production:
      runs-on: ubuntu-latest
      needs: [migrate-production]
      steps:
        - Verify /health endpoint returns 200
        - Verify /api/v1/ endpoint returns valid response
        - Verify static assets load via CDN
        - Run critical path health checks
        - Post Slack notification with deployment summary

  6. rollback-on-failure:
      if: failure()
      runs-on: ubuntu-latest
      needs: [deploy-production, migrate-production, verify-production]
      steps:
        - helm rollback ai-enterprises-api -n ai-enterprises
        - helm rollback ai-enterprises-web -n ai-enterprises
        - alembic downgrade -1
        - Post Slack notification: deployment rolled back
```

### 14.4 Docs Publishing — `docs-publish.yml`

```
Trigger:
  push:
    branches: [main]
    paths: [apps/book/**, docs/**]

Jobs:
  1. build-and-deploy:
      runs-on: ubuntu-latest
      steps:
        - Checkout
        - Setup pnpm
        - pnpm install --frozen-lockfile
        - pnpm build --filter=@ai-enterprises/book
        - Deploy to Cloudflare Pages / GitHub Pages / S3 + CloudFront
        - Invalidate CDN cache
```

### 14.5 Cleanup — `cleanup.yml`

```
Trigger:
  schedule:
    - cron: '0 4 * * 0'  # Weekly Sunday 4 AM

Jobs:
  1. cleanup-artifacts:
      runs-on: ubuntu-latest
      steps:
        - Delete old GitHub Packages (>= 90 days, no tag)
        - Delete old workflow runs (>= 90 days)
        - Prune old cache entries

  2. cleanup-k8s:
      runs-on: ubuntu-latest
      steps:
        - Delete completed pods older than 7 days
        - Delete orphaned PVCs
        - Prune unused container images from node
```

### 14.6 CI/CD Secrets (GitHub Actions)

| Secret Name | Used By | Source |
|---|---|---|
| `GHCR_TOKEN` | build-images | GitHub Token (auto) |
| `KUBE_CONFIG_STAGING` | deploy-staging | Base64-encoded kubeconfig |
| `KUBE_CONFIG_PRODUCTION` | deploy-production | Base64-encoded kubeconfig |
| `SLACK_WEBHOOK_URL` | deploys | Slack Incoming Webhook |
| `DOCKER_REGISTRY` | build-images | `ghcr.io` |
| `SENTRY_AUTH_TOKEN` | builds | Sentry org auth token |
| `TURBO_TOKEN` | builds | Vercel Remote Cache token |
| `TURBO_TEAM` | builds | Vercel Remote Cache team |

### 14.7 Branch Protection Rules

| Branch | Rule |
|---|---|
| `main` | Require PR with 1 approval, all CI checks pass, no merge commit (squash only) |
| `staging` | Push-only from `main`, auto-deploy enabled |
| `production` | Push protected, deploy via workflow dispatch only |
| `release/*` | Require PR with 2 approvals, all CI checks pass, signed commits |