# Phase 0 — Stabilize: Implementation Checklist (File-by-File)

> **Document ID:** AEP-P0C-000
> **Version:** 1.0
> **Status:** Checklist only. **No source files modified. No code written.**
> **Gate:** G0 exit = API boots, Alembic linear, missing schemas/config added, workspaces enabled, `build/test/typecheck` green.
> **Owner:** Principal Enterprise Software Architect

---

## 1. Purpose

This is the **only** authoritative execution plan for Phase 0 (Gate G0 of `implementation-roadmap.md` §2). It is deliberately file-by-file: exact paths, exact changes, dependencies, effort, risk, and rollback. It contains **zero implementation** — the code will be written only after this checklist is approved.

## 2. Scope

**In scope (G0):**
- Make `apps/api` importable and bootable.
- Add missing config keys and AI response schemas.
- Align agent/service method contracts with the routers.
- Linearize the Alembic migration graph (single head).
- Re-enable pnpm workspaces and make the monorepo `build/test/typecheck` green.

**Out of scope (deferred to later gates):**
- SoR content tables (G1), deterministic indexing (G2), frontend token transport/SSE proxy (G3), MCP (G4), Docker/K8s/CI (G5).
- All architecture decisions in the approved spec set (AEP-*).

## 3. Objectives

| # | Objective | Success measure |
|---|---|---|
| O1 | Make the API importable and bootable | `uvicorn main:app` starts; `/health` returns 200 |
| O2 | Add all missing config keys and AI response schemas | `import apps.api.app.main` clean; no `ImportError`/`AttributeError` |
| O3 | Align agent/service contracts with the routers | All AI endpoints resolve their handlers; no 500 on import or route resolution |
| O4 | Fix the tool-result bug in chat | `zip(tool_calls, [])` removed; tool results bound to call ids |
| O5 | Linearize the Alembic migration graph | `alembic heads` → single head; `upgrade head` succeeds on fresh DB |
| O6 | Re-enable monorepo workspaces | root `"workspaces": ["apps/*", "packages/*"]`; `apps/web` resolves `@ai-enterprises/auth` |
| O7 | Green monorepo verification | `npm run build` / `typecheck` / `lint` pass; `pytest` passes |
| O8 | No scope creep | Only tasks T1–T16 executed; no G1+ features |

## 4. Environment Prerequisites (before any edit)

| # | Action | Notes |
|---|---|---|
| E1 | Create Python venv: `python -m venv .venv` (or `.venv\Scripts\activate`) | System Python is 3.14.3; project requires `>=3.13` (compatible). |
| E2 | Install API deps: `pip install -e ".[dev]"` from `apps/api` | Current env lacks `joserfc`, `svix`, etc. |
| E3 | Install JS deps after workspaces enabled (T13): `npm install` at repo root | No lockfile or `node_modules` present today. |
| E4 | Baseline snapshot for rollback | Repo is **not** a git repo. Recommend `git init` + baseline commit, or a `docs/` + `_phase0_snapshot/` backup of all files listed in §7. |
| E5 | Prepare `.env` from `.env.example` + generate JWT keypair into `.secrets/` | `crypto.initialize()` auto-writes `.secrets/` (removed in G5). |

---

## 5. Task Map (ID → File → Action)

| Task | File | Action |
|---|---|---|
| T1 | `apps/api/app/core/deps.py` | CREATE |
| T2 | `apps/api/app/core/auth.py` | CREATE |
| T3 | `apps/api/app/core/config.py` | MODIFY |
| T4 | `apps/api/app/ai/schemas/models.py` | MODIFY |
| T5 | `apps/api/app/ai/rag/pipeline.py` | MODIFY |
| T6 | `apps/api/app/ai/agents/chat_agent.py` | MODIFY |
| T7 | `apps/api/app/ai/agents/tutor_agent.py` | MODIFY |
| T8 | `apps/api/app/ai/agents/quiz_agent.py` | MODIFY |
| T9 | `apps/api/app/ai/agents/interview_agent.py` | MODIFY |
| T10 | `apps/api/app/ai/memory/conversation_memory.py` | MODIFY |
| T11 | `apps/api/alembic/versions/0010_merge_heads.py` | CREATE (new migration) |
| T12 | `apps/api/app/db/session.py` | MODIFY (decision item) |
| T13 | `package.json` (root) | MODIFY |
| T14 | Workspace install + monorepo build/typecheck | RUN |
| T15 | `apps/api/tests/**` | VERIFY (adjust only if contract aligns) |
| T16 | Lint (ruff) + boot smoke + exit checks | RUN |

---

## 6. File-by-File Specification

### T1 — CREATE `apps/api/app/core/deps.py`

**Why:** `ai/router.py:33` imports `CurrentUser` from `apps.api.app.core.deps`; module does not exist (only `auth/deps.py` exists with the implementation).

**Content (contract):**
- Re-export the auth dependencies as the canonical `core.deps` surface:
  - `CurrentUser = Annotated[User, Depends(get_current_user)]`
  - `SessionDep` / `CurrentSession` (from `get_valid_session`)
  - `require_permission(resource, action)`, `require_role(role_name)`
  - `OptionalUser` = `User | None` via `Depends(get_current_user_optional)` (see T2)
- Implementation delegates to `apps.api.app.auth.deps`; **no logic duplication**.

**Dependencies:** none (imports existing `auth/deps.py`).
**Effort:** S (< 1 h).
**Risk:** low (pure re-export).

### T2 — CREATE `apps/api/app/core/auth.py`

**Why:** `ai/streaming.py:18` imports `get_current_user_optional` from `apps.api.app.core.auth`; module does not exist.

**Content (contract):**
- `async def get_current_user_optional(request) -> User | None` — returns user from `request.state.auth_context` or a valid Bearer token; `None` instead of raising when absent/invalid.
- Keep semantics identical to `auth/deps.get_current_user` but fail-soft (streaming allows anonymous).

**Dependencies:** none.
**Effort:** S.
**Risk:** low.

### T3 — MODIFY `apps/api/app/core/config.py`

**Why:** `ai/rag/pipeline.py:14` reads `settings.RAG_MAX_CONTEXT_CHUNKS`; key missing (only `RAG_TOP_K` exists).

**Change (additive):**
- Add `RAG_MAX_CONTEXT_CHUNKS: int = 5` in the `# ── RAG ──` block.
- (Verify `RAG_SCORE_THRESHOLD` already exists — yes, `0.65`.)

**Dependencies:** none.
**Effort:** S.
**Risk:** low (additive).

### T4 — MODIFY `apps/api/app/ai/schemas/models.py`

**Why:** router imports 5 schemas that do not exist, and two existing schemas conflict with runtime usage.

**Changes:**
1. Add missing response models:
   - `TutorResponse` (matches `TutorRequest` fields + answer/citations).
   - `QuizGenerateResponse` (wraps `QuizResponse` + status).
   - `QuizSubmitResponse` (wraps `QuizResult`).
   - `InterviewStartResponse` (session_id + first question).
   - `InterviewEvaluateResponse` (strengths/improvements/score/next_question/is_complete — aligns with `InterviewFeedback`).
2. Fix `StreamChunk`: currently `{token, index, finish_reason}` but `streaming.py` reads `chunk.event_type` and `chunk.model_dump_json()`. **Contract fix:** add `event_type: str` (e.g. `token|done|error`); keep `content` field.
3. Fix `SourceCitation`: pipeline constructs with `id, title, content, score, source, section, chunk_index, relevance`; schema has `id, title, section, content, relevance(float), url, page`. **Contract fix:** add `score: float`, `source: str`, `chunk_index: int`; change `relevance` to `str` (values `high|medium|low`) or align pipeline output — decide once, document in schema.
4. Verify `InterviewEvaluateRequest` fields match router usage (`conversation_id`, `question_index`, `answer`) — align existing request models.

**Dependencies:** none (blocked only if test imports fail; see T15).
**Effort:** M (1–3 h, schema alignment decisions).
**Risk:** medium — schema drift causes runtime 422s; must match router + agents + streaming exactly.

### T5 — MODIFY `apps/api/app/ai/rag/pipeline.py`

**Why:** `chat_agent.py:50` and `quiz_agent.py:21` call `rag_pipeline.search(...)`; only `retrieve/augment/generate_citations` exist.

**Change:**
- Add `async def search(query, top_k=5, filters=None) -> list[dict]` delegating to `hybrid_search.search` (keeps score-threshold filtering consistent with `retrieve`).
- Keep `retrieve` as the citation-oriented path (used by later gates).

**Dependencies:** T3 (module-level `settings` read at import).
**Effort:** S.
**Risk:** low.

### T6 — MODIFY `apps/api/app/ai/agents/chat_agent.py`

**Why:** router calls `agent.run(...)` / `agent.run_stream(...)` (do not exist); `zip(tool_calls, [])` drops tool results (line 164); `process_message` calls missing `rag_pipeline.search`.

**Changes:**
1. Add `run(message, conversation_id, use_rag)` returning a `ChatResponse`-shaped result — delegate to `process_message(stream=False)` / RAG path.
2. Add `run_stream(message, conversation_id, use_rag)` async generator yielding `StreamChunk` objects with `event_type` (aligns with T4 streaming contract).
3. **Bug fix (line 164):** replace `zip(choice.message.tool_calls, [])` with a collected `results` list (per tool call) so tool responses are actually sent back to the model.
4. Replace `rag_pipeline.search(message, top_k=3)` calls with the new T5 `search()` signature (verify kwargs).

**Dependencies:** T4 (schemas), T5 (rag_pipeline.search).
**Effort:** M.
**Risk:** medium — this is the streaming heart; must not break SSE shape.

### T7 — MODIFY `apps/api/app/ai/agents/tutor_agent.py`

**Why:** router calls `agent.tutor(topic, question, conversation_id)` returning `TutorResponse`, and `agent.tutor_stream(...)`; current `tutor()` is `(topic, message, stream=True)` returning a generator.

**Changes:**
- Rename/realign: `tutor(topic, question, conversation_id) -> TutorResponse` (non-stream path).
- Add `tutor_stream(topic, question, conversation_id)` async generator yielding `StreamChunk`.
- Keep Socratic prompt path (`prompt_manager.render("tutor_socratic", ...)`).

**Dependencies:** T4 (TutorResponse, StreamChunk).
**Effort:** S–M.
**Risk:** low–medium.

### T8 — MODIFY `apps/api/app/ai/agents/quiz_agent.py`

**Why:** router calls `agent.generate(topic, num_questions, difficulty, conversation_id)`, `agent.generate_stream(...)`, `agent.evaluate(quiz_data, answers)`; current methods are `generate_quiz(chapter_id, count, difficulty)` / `evaluate_answers(quiz, answers)`.

**Changes:**
- Add `generate(...)` → `QuizGenerateResponse` (wrap existing `generate_quiz`; map `topic→chapter_id` semantics per request).
- Add `generate_stream(...)` async generator yielding `StreamChunk`.
- Add `evaluate(quiz_data, answers)` → `QuizSubmitResponse` (wrap `evaluate_answers`).

**Dependencies:** T4 (schemas), T5 (rag_pipeline.search).
**Effort:** M.
**Risk:** medium — quiz data shape must match `QuizResponse`/`QuizResult`.

### T9 — MODIFY `apps/api/app/ai/agents/interview_agent.py`

**Why:** router calls `agent.start(conversation_id=None)` and `agent.evaluate(conversation_id, question_index, answer)`; current methods are `start_interview(topic, difficulty)` / `submit_answer(answer)`.

**Changes:**
- Add `start(conversation_id=None)` → `InterviewStartResponse` (use stored metadata topic/difficulty; validate conversation belongs to user).
- Add `evaluate(conversation_id, question_index, answer)` → `InterviewEvaluateResponse` (wrap `submit_answer`).
- Keep `interview_agent = InterviewAgent` instance export; ensure router imports the instance, not the class.

**Dependencies:** T4 (schemas).
**Effort:** S–M.
**Risk:** low–medium (metadata-key dependency).

### T10 — MODIFY `apps/api/app/ai/memory/conversation_memory.py`

**Why:** router calls `list_conversations(user_id, limit, offset)` (current method takes no args), `get_messages(conversation_id, user_id)` (missing), `delete_conversation(conversation_id, user_id)` returning `bool` (current returns None), `update_title(conversation_id, user_id, title)` (missing).

**Changes:**
1. Add `user_id, limit, offset` params to `list_conversations`; apply pagination.
2. Add `get_messages(conversation_id, user_id)` (scoped; alias of `get_history` with ownership check).
3. Return `bool` from `delete_conversation` (True if keys existed).
4. Add `update_title(conversation_id, user_id, title)`.

**Dependencies:** none.
**Effort:** S–M.
**Risk:** low — Redis-only; ownership checks are security-relevant (keep).

### T11 — CREATE `apps/api/alembic/versions/0010_merge_heads.py`

**Why:** migration graph has **6 heads** (`0004`,`0005`,`0006`,`0007`,`0008`,`0009`) because `0003` branches from `0001` (not `0002`), `0004/0005` list `("0001","0003")`, `0006/0007` from `0001`, `0008/0009` from `0002`. `alembic upgrade head` refuses multiple heads.

**Change (non-destructive, additive):**
- New migration: `down_revision = ("0004", "0005", "0006", "0007", "0008", "0009")`, `revision = "0010"`, empty `upgrade()`/`downgrade()` (pure merge node).
- Verify `alembic upgrade head` → single head `0010`.
- **Do not** rewrite existing `0003–0009` files (keeps rollback simple and history intact).

**Dependencies:** none (DB-level).
**Effort:** S.
**Risk:** low — additive; existing branch data unaffected. `upgrade head` determinism verified in CI.

### T12 — MODIFY `apps/api/app/db/session.py` (DECISION ITEM)

**Why:** `init_db()` runs `SQLModel.metadata.create_all` (line 39) while Alembic owns schema → dual DDL authority (ADR violation for G1).

**Decision required before coding:**
- **Option A (recommended, minimal):** keep `init_db()` for dev/test boot but gate behind `settings.DB_AUTO_CREATE_SCHEMA` (default `True` in local, `False` in prod); document that G1 removes it fully.
- **Option B:** replace `init_db()` with programmatic `alembic upgrade head`. Risk: tests rely on `create_all` via conftest (separate test engine); changing now widens G0 scope.

**Note:** `tests/conftest.py` uses its own `create_all` on `ai_enterprises_test` — untouched by this task.

**Dependencies:** none (runtime only).
**Effort:** S.
**Risk:** low; ensure no startup path breaks if Postgres is absent during import.

### T13 — MODIFY `package.json` (repo root)

**Why:** `"workspaces": []` is empty → monorepo linking disabled; `apps/web` cannot resolve `@ai-enterprises/auth`, turbo builds can't run.

**Change:**
- Set `"workspaces": ["apps/*", "packages/*"]`.

**Dependencies:** none.
**Effort:** S.
**Risk:** medium — enables install of all packages; empty/stub packages (`agents`, `config`, `prompts`, `rag`, `shared`, `ui`) must typecheck/build (see T14).

### T14 — RUN workspace install + monorepo verification

**Actions:**
1. `npm install` at root (generates lockfile + `node_modules`).
2. `npm run build` — expect `apps/web` (Next.js), `apps/book` (Docusaurus), `packages/*` to build.
3. `npm run typecheck` — fix any type errors that gate the build (targeted; full auth-transport redesign is G3).
4. `npm run lint` — fix blocking lint only; no sweeping refactors.

**Dependencies:** T13.
**Effort:** L (half day+ — depends on how broken the stub packages are).
**Risk:** high — `next lint`/typecheck may surface pre-existing errors; **scope discipline** required (no feature changes).

### T15 — VERIFY `apps/api/tests/**`

**Actions:**
- Run `pytest` in `apps/api` (needs Postgres `ai_enterprises_test` + Redis available or mocked).
- Align tests only where they encode the OLD contracts being changed (agent method names, schema shapes, `StreamChunk`/`SourceCitation` fields).
- Do **not** add new feature tests in G0 (that is G1+).

**Dependencies:** T1–T12.
**Effort:** M.
**Risk:** medium — boot-blocking imports are fixed, so collection should succeed; failing cases indicate missed contract spots.

### T16 — RUN exit verification

**Checks (G0 exit criteria):**
1. `uvicorn main:app` boots; `/health` returns `200`.
2. `alembic upgrade head` succeeds on a fresh DB (single head `0010`).
3. `pytest` green.
4. `npm run build` / `typecheck` / `lint` green.
5. AI routers import without error (`import apps.api.app.main`).

**Dependencies:** T1–T15.
**Effort:** S–M.

---

## 7. Dependency Graph

```
T13 ─▶ T14 ─▶ T16
E1/E2 ─▶ T1 ─┐
            ├─▶ T15 ─▶ T16
E3 ─▶ T13   │
T3 ─▶ T5 ─▶ T6 ─┐
T4 ─▶ T6/T7/T8/T9 ─┤
T11 ─▶ T15/T16     │
T12 ─▶ T16         ▼
              T16 (gate)
```

**Ordering rule:** boot-safe path first — `T1,T2,T3,T4` → `T5..T10` → `T11,T12` → verify with `T15,T16`; monorepo `T13,T14` runs in parallel.

---

## 8. Rollback Strategy

> **Repo is not under git today.** Baseline must be captured in **E4** before edits.

| Tier | Rollback action |
|---|---|
| **Whole phase** | Restore E4 snapshot / baseline git commit of all listed files; delete new files (`core/deps.py`, `core/auth.py`, `0010_merge_heads.py`). |
| **Per task (additive)** | Revert single file to baseline; new files deleted. |
| **T11 migration** | Safe: delete `0010_merge_heads.py` → returns to pre-merge multi-head state; no data touched (empty upgrade). |
| **T3 config** | Remove added key. |
| **T13 workspaces** | Restore `"workspaces": []`. |
| **DB state** | G0 changes no schema (T11 is empty); existing dev DBs unaffected unless `alembic upgrade head` runs — reversible via `alembic downgrade 0010` (no-op). |

**Invariant:** no task destroys data; all migrations are additive or no-op; all code changes are reversible file edits.

---

## 9. Risk Register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | No VCS baseline | High | High | E4 git init + snapshot before edits |
| R2 | Python 3.14 wheel gaps (asyncpg/cryptography) | Med | Med | Pin latest; fallback Python 3.13 venv |
| R3 | Schema drift (StreamChunk/SourceCitation) causes runtime 422s | Med | Med | T4 contract table reviewed against routers+agents+streaming |
| R4 | Stub packages break `turbo build/typecheck` | High | Med | Scope discipline; fix only gate-blocking errors (T14) |
| R5 | Streaming contract mismatch (frontend EventSource GET vs POST SSE) | Known | Med | Deferred to G3 — note in T4/T6 comments, not fixed in G0 |
| R6 | Tests encode old contracts | Med | Med | T15 aligns tests, no new tests |
| R7 | `create_all` vs Alembic divergence persists | Known | Low | T12 decision; removed fully in G1 |

---

## 10. Verification Checklist

Gate G0 is **not** passed until every check below is green.

| # | Check | Command / evidence | Related tasks |
|---|---|---|---|
| V1 | API imports clean | `python -c "import apps.api.app.main"` — no `ImportError` | T1–T4 |
| V2 | API boots | `uvicorn main:app` → `/health` returns 200 | T1–T5 |
| V3 | AI routers resolve | all `/api/v1/ai/*` routes registered (no 500 on load) | T4–T10 |
| V4 | Streaming contract | SSE endpoints produce `StreamChunk` events with `event_type` | T4, T6 |
| V5 | Tool-call bug fixed | `chat_agent.py` has no `zip(tool_calls, [])` | T6 |
| V6 | Single migration head | `alembic heads` → exactly one (0010) | T11 |
| V7 | Fresh-DB migration | `alembic upgrade head` succeeds on empty database | T11 |
| V8 | Workspaces enabled | root `package.json` `"workspaces"` non-empty; `@ai-enterprises/auth` resolvable | T13 |
| V9 | API tests green | `pytest` (requires `ai_enterprises_test` + Redis) | T15 |
| V10 | Monorepo build | `npm run build` passes | T14 |
| V11 | Typecheck | `npm run typecheck` passes | T14 |
| V12 | Lint | `ruff check .` in `apps/api` and `npm run lint` pass | T16 |
| V13 | No scope creep | diff contains only files listed in §5/§6 (Task Map) | all |

**Definition of done (G0 exit):** V1–V13 all green, reviewed against O1–O8, then documented before G1 begins.

---

## 11. Effort Summary

| Effort | Tasks |
|---|---|
| S (< 1 h) | T1, T2, T3, T5, T11, T12, T13, T16 |
| M (1–3 h) | T4, T6, T7, T8, T9, T10, T15 |
| L (half day+) | T14 |
| Total | **~2–3 focused days** including verification |

---

## 12. Stop Statement

This document is a **plan only**. No source files have been modified and no code has been written. Execution begins only after:
1. This checklist is approved, and
2. The E1–E5 prerequisites (venv, deps, baseline snapshot) are confirmed.

Next gate after G0 completes and is reviewed: **G1 — SoR content core** (per `implementation-roadmap.md` §4).
