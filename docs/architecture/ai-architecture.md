# AI Architecture — Enterprise Specification

> **Document ID:** AEP-AIA-005
> **Version:** 1.0
> **Status:** Approved for design. Awaiting implementation approval.
> **Owner:** Principal Enterprise Software Architect
> **Classification:** Internal — Enterprise Architecture Specification

---

## 1. Purpose

Define the AI runtime: agents, model routing, tool use, memory, grounding, guardrails, and observability. This document supersedes the earlier implementation blueprint of the same name and aligns the AI layer with the SoR-first principle: **every AI agent reads from the SoR and persists its durable state there.**

## 2. Principles

1. **SoR-first:** agents read content/citations/config from PostgreSQL; Qdrant/Redis are acceleration only.
2. **Grounded output:** every answer carries version-pinned citations.
3. **Cost-controlled:** every model call is metered, cached, and budget-aware.
4. **Fail-soft:** model/router outage degrades gracefully (fallback model, cached answers, clear errors).
5. **Book-parameterized:** agents are shared code; behavior is driven by `book.config`/`book.model_routing`.

## 3. AI Layer Diagram

```
Browser / MCP client
   │
   ▼
Gateway (REST /api/v1/ai/*  or  MCP tools)
   │  auth + RBAC + rate-limit + audit
   ▼
Agent Runtime (shared)
   ├─ ChatAgent      (RAG-grounded Q&A)
   ├─ TutorAgent     (guided learning, Socratic)
   ├─ QuizAgent      (generation + evaluation)
   └─ InterviewAgent (scenario interviews, eval)
   │
   ├─ Tool Executor   (RAG search, citations, glossary, bookmark)
   ├─ Guardrails      (grounding check, PII, policy)
   ├─ Memory          (session context, SoR-persisted)
   └─ Model Router    (primary → fallback → cached)
         │
         ▼
     LLM providers (Cohere embed/rerank, OpenAI/OpenRouter, Gemini, Grok)
```

## 4. Agent Catalog

| Agent | Purpose | Tools | Output contract |
|---|---|---|---|
| `ChatAgent` | book Q&A grounded in SoR | rag_search, get_citations, get_glossary, resolve_book | streamed answer + citations |
| `TutorAgent` | Socratic guided learning | rag_search, progress, difficulty | steps + questions + citations |
| `QuizAgent` | generate + grade quizzes | unit_tree, quiz_gen, quiz_grade | quiz + answers + rationale |
| `InterviewAgent` | role/skill interviews | scenario, evaluate, score | session + evaluation + rubric |

**Contract rule:** each agent exposes a single interface: `run(messages, context) → Response` and optionally `run_stream(...) → SSE`. The router calls only these. (Current code violates this — see §9 defects.)

## 5. Model Routing

### 5.1 Configuration (per book)

```
model_routing:
  primary:   gpt-4o
  fallback:  gemini-2.5-pro
  temperature: 0.3
  max_tokens: 4096
```

### 5.2 Decision flow

```
request → resolve model_routing (book.config, cached)
   ├─ primary available? ──▶ use primary
   ├─ primary rate-limited/fails ──▶ fallback (flag in audit)
   ├─ both fail ──▶ serve cached answer (if any, flagged stale)
   └─ else ──▶ error with retry hint (never silent empty)
```

### 5.3 Determinism & caching
- Query-rewrite and rerank results cached in Redis by query hash (TTL by content update).
- Embeddings are deterministic + content-hashed → deduplicated (unchanged chunks never re-embedded).
- Streaming responses are not cached (interactive), but metadata/citations always are.

## 6. Tool Execution Model

```
Agent → tool_calls [ {name, args} ]
   ├─ validate against tool registry + RBAC scopes
   ├─ execute (bound timeout)
   ├─ collect results (each call maps to its call_id)
   └─ return enriched context to model
```

**Invariant:** every tool result is bound to its originating `tool_call_id`. (Current `zip(tool_calls, [])` bug drops results — prohibited by this spec.)

## 7. Memory

| Type | Store | Retention |
|---|---|---|
| Session context | Redis (hot) + PostgreSQL (durable) | session + post-export 90d–2y |
| Conversation history | `conversations`/`messages` (SoR) | retention policy |
| Long-term user state | `learning_progress`, `bookmarks` (SoR) | indefinite |
| Ephemeral scratch | Redis | TTL seconds–minutes |

**Rule:** Redis is hot cache only; the durable record is always PostgreSQL. On Redis flush, sessions reconstruct from the SoR.

## 8. Grounding & Citations

- Agents assemble context from `rag_search` results; each result maps to `content_chunk` → `citation`.
- **Grounding check (guardrail):** for `citation_mode=strict`, refuse/flag answers whose claims lack ≥ N in-book citations.
- Citations are version-pinned: `(book_id, version_id, revision_id, chunk_id)`. See `enterprise-system-of-record.md` §12.

## 9. Current Defects to Resolve (Phase 0/3)

| Defect | Spec fix |
|---|---|
| `ai/router.py:33` imports missing `core.deps` | create `core/deps.py` (auth + db deps) |
| `ai/streaming.py:18` imports missing `core.auth` | create `core/auth.py` (token/security helpers) |
| `settings.RAG_MAX_CONTEXT_CHUNKS` missing | add config key |
| 5 missing response schemas (`QuizGenerateResponse`, `QuizSubmitResponse`, `InterviewStartResponse`, `InterviewEvaluateResponse`, `TutorResponse`) | add to `ai/schemas/models.py` |
| Router calls `agent.run/run_stream`; agents lack them | implement uniform agent contract |
| `interview_agent` exported as class, used as service | export instance |
| `zip(tool_calls, [])` in `chat_agent.py:164` | bind results to call ids |
| `list_conversations` argument mismatch | align signature |
| `AiLogger` never called | instrument every model call |

## 10. Observability & Cost Control

| Metric | Where |
|---|---|
| per-call model, tokens, latency | `ai_call_logs` (SoR) + metrics |
| cost per (book, model, agent) | aggregation from call logs |
| citation coverage % | guardrail telemetry |
| fallback rate | router telemetry |
| queue depth / worker lag | job metrics |

**Budget controls:** per-book monthly token budget; hard cap on tokens per turn; degraded mode to fallback/lexical-only when budget exhausted.

## 11. Guardrails

1. **Grounding enforcement** (strict/standard modes).
2. **PII detection** on inputs/outputs; redaction policy.
3. **Prompt injection resistance:** tool outputs treated as data, delimited, never trusted instructions.
4. **Content policy:** per-book sensitive-topic flags.
5. **Rate limiting:** per user + per book, shared via Redis.
6. **Audit:** every AI interaction logged with request id, user, book, model, cost.

## 12. Failure Semantics

| Failure | Behavior |
|---|---|
| Primary model down | fallback model, audited |
| All models down | cached answer (flagged) or clear degraded message |
| Qdrant down | lexical-only retrieval (SoR tsvector) |
| Redis down | bypass cache; direct SoR reads; queues paused |
| Rerank down | RRF-only ordering |

## 13. Acceptance Checks

| Check | Pass criteria |
|---|---|
| Uniform agent contract | router compiles; all agents implement run/run_stream |
| SoR persistence | conversation + citations survive process restart |
| Grounded answers | strict mode: 100% of answers carry ≥ N citations |
| Cost metering | every model call appears in ai_call_logs |
| Fail-soft | simulated Qdrant/model outage degrades, never crashes |
| Tool correctness | tool results always bound to correct call |
