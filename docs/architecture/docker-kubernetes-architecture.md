# Docker & Kubernetes Architecture — Enterprise Specification

> **Document ID:** AEP-DKR-008
> **Version:** 1.0
> **Status:** Approved for design. Awaiting implementation approval.
> **Owner:** Principal Enterprise Software Architect
> **Classification:** Internal — Enterprise Architecture Specification

---

## 1. Purpose

Define the containerization and orchestration strategy: one image per process, a `docker compose` dev stack, and Kubernetes as a **future-ready deployment target** (authored and CI-tested now, applied when load demands). Container images must be reproducible and identical across dev, CI, and prod.

## 2. Strategy Principles

1. **Docker is mandatory.** Every environment (dev, CI, staging, prod) runs the same images.
2. **Kubernetes is future-ready, not day-1.** Start with compose; K8s manifests are authored and tested in CI from day 1.
3. **One process per image** (`api`, `worker`, `web`, `mcp`, `nginx`) — clear scaling and failure boundaries.
4. **SoR-derived behavior:** containers are stateless; durable state lives only in PostgreSQL/Qdrant/Redis.
5. **K8s is a deployment target, never a design constraint** on the domain.

## 3. Image Topology

```
                    ┌─────────────────────────────┐
  ingress ──TLS──▶  │  nginx (reverse proxy)      │
                    │  /api ─▶ api   (FastAPI)    │
                    │  /web ─▶ web   (Next.js)    │
                    │  /docs─▶ docs  (Docusaurus) │
                    │  /mcp ─▶ mcp   (MCP server) │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
                 api pods      web pods      docs pods
                 (HPA)                       (static)
                    │
                    └── workers (indexing) ── consume Redis queue
                                   │
   PostgreSQL ◀─────────────── all services (SoR)
   Qdrant  ◀────────── derived index (api/workers)
   Redis   ◀────────── cache + queues (api/workers/web)
```

### 3.1 Images

| Image | Base | Runs | Scale strategy |
|---|---|---|---|
| `api` | python:3.13-slim | FastAPI app | HPA by CPU/RPS |
| `worker` | python:3.13-slim | job consumers (arq/celery) | HPA by queue depth |
| `web` | node:22-alpine | Next.js standalone server | HPA by RPS |
| `docs` | nginx:alpine | static Docusaurus export | static, CDN |
| `mcp` | python:3.13-slim | MCP protocol server | HPA by connections |
| `nginx` | nginx:alpine | ingress/reverse proxy | 2+ replicas |

## 4. Dockerfile Conventions

- **Multi-stage builds:** build deps in one stage, copy only runtime artifacts.
- **Non-root user** in all runtime images.
- **Pin base images** to digest or exact tag; SBOM generated in CI.
- **Healthcheck** per service (`/health` endpoint).
- **No secrets in images**; secrets injected via env from Vault/KMS at runtime.
- `.dockerignore` excludes docs, tests, secrets, node_modules.

## 5. Docker Compose (Dev Stack)

```
services:
  postgres  (SoR, volume persisted)
  qdrant    (derived vector store)
  redis     (cache + queues)
  api       (uvicorn --reload)
  worker    (job consumers)
  web       (next dev)
  mcp       (mcp server, stdio local only)
  nginx     (dev proxy)
```

- Named volumes for PostgreSQL data only (Qdrant/Redis are rebuildable, but persisted for dev speed).
- `init` service runs migrations before api/worker start.
- Parity: same env var names as prod; secret refs via `.env` (local) vs Vault (prod).

## 6. Kubernetes Target (Kustomize)

### 6.1 Layout

```
k8s/
├─ base/
│  ├─ namespace.yaml
│  ├─ api-deploy.yaml / api-svc.yaml / api-hpa.yaml
│  ├─ worker-deploy.yaml
│  ├─ web-deploy.yaml / web-svc.yaml
│  ├─ mcp-deploy.yaml / mcp-svc.yaml
│  ├─ nginx-ingress.yaml
│  ├─ migration-job.yaml
│  └─ kustomization.yaml
└─ overlays/
   ├─ dev/   (compose parity, small replicas)
   ├─ staging/ (2 replicas, staging secrets)
   └─ prod/  (HPA, resources, prod secrets via Vault/KMS)
```

### 6.2 Key resources

| Resource | Purpose |
|---|---|
| `Namespace` | platform isolation |
| `Deployment` + `Service` | per process |
| `HorizontalPodAutoscaler` | api/worker/web/mcp |
| `Job` (migration) | run Alembic head before rollout |
| `Ingress` (nginx) | TLS, path routing |
| `Secret`/`ExternalSecret` | env from Vault/KMS |
| `PodDisruptionBudget` | availability during drains |
| `ResourceQuota` / `LimitRange` | cost control |
| `NetworkPolicy` | service-to-service allowlist |

### 6.3 Rollout procedure (CI)
1. Build + scan + push images (digest-pinned).
2. Apply manifests to staging; run migration `Job`.
3. Smoke tests (health, search, citations).
4. Rollout prod: migration `Job` → canary → full rollout with PDB.
5. Verify metrics; rollback = revert manifest revision (state remains safe in SoR).

## 7. Configuration & Secrets

| Item | Dev | Prod |
|---|---|---|
| Config | `.env` (compose) | `ConfigMap` (non-secret) |
| Secrets | `.env` local | Vault/KMS via External Secrets, injected as env/mount |
| Rotation | manual | automated + audit |

**Rule:** never bake secrets into images or repo; the config loader's current auto-write to `.secrets/` is removed in Phase 0/5.

## 8. Observability Stack

- **Logs:** stdout structured JSON → collector.
- **Metrics:** Prometheus endpoints per service; dashboards (API latency, queue depth, model cost, citation coverage).
- **Traces:** OpenTelemetry across api→worker→SoR.
- **Alerts:** P95 latency, migration failures, queue backlog, model budget, DR verification failure.

## 9. Scaling Semantics

| Component | Trigger | Notes |
|---|---|---|
| api | CPU > 70% / RPS | stateless; scale freely |
| worker | queue depth | concurrency bounded by embedding API limits |
| web | CPU / RPS | Next.js standalone |
| mcp | connections | session-affinity not required (stateless) |
| nginx | CPU | 2+ always |

Stateful stores (PostgreSQL, Qdrant, Redis) scale **vertically / via managed services**, not by replica count.

## 10. Failure & Recovery Semantics

| Failure | Behavior |
|---|---|
| Pod crash | restart (stateless); state safe in SoR |
| Queue backlog | scale workers; alerts at threshold |
| Migration failure | rollout halted; app serves previous schema-safe version |
| Region loss | DR: restore Postgres + reindex derived stores (see SoR §15) |
| Image scan fail | CI blocks promotion |

## 11. Acceptance Checks

| Check | Pass criteria |
|---|---|
| Image reproducibility | same commit → identical image digest |
| Compose parity | dev compose uses same config keys as prod |
| Statelessness | kill all api pods → no data loss |
| Migration safety | `alembic upgrade head` Job succeeds before rollout |
| K8s dry-run | manifests pass `kubectl kustomize --load-restrictor` + CI lint |
| Secret hygiene | no secrets in images/repo; `scan` gate green |
