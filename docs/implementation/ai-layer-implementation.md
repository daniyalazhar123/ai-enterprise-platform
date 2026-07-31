# AI Layer — Implementation Plan

> **Status:** Implementation v1.0  
> **Stack:** OpenAI Agents SDK · FastAPI · Python 3.13+ · Gemini · Grok · OpenRouter · Cohere · Qdrant · pgvector · PostgreSQL (Neon)  
> **Base Spec:** `docs/architecture/ai-architecture.md`

---

## 1. Folder Structure

```
apps/api/
└── app/
    ├── ai/
    │   ├── __init__.py
    │   ├── gateway.py                        # AI Gateway: validate, rate limit, cost track
    │   ├── router.py                         # LLM Router: model selection, fallback chain
    │   ├── deps.py                           # DI: get_ai_gateway, get_llm_router, get_rag_pipeline
    │   │
    │   ├── agent/                            # OpenAI Agents SDK orchestration
    │   │   ├── __init__.py
    │   │   ├── runner.py                     # AgentRunner factory, config builder, lifecycle
    │   │   ├── chat_agent.py                 # ChatAgent: instructions, tool registration
    │   │   ├── rag_agent.py                  # RagAgent: RAG instructions, search tool
    │   │   ├── tools/                        # Tool implementations
    │   │   │   ├── __init__.py
    │   │   │   ├── rag_search.py             # Hybrid search tool
    │   │   │   ├── web_search.py             # Live web search tool
    │   │   │   ├── calculator.py             # Math evaluation tool
    │   │   │   ├── generate_quiz.py          # Quiz generation tool
    │   │   │   ├── save_note.py              # Note persistence tool
    │   │   │   └── translate.py              # Language translation tool
    │   │   └── guardrails.py                 # Input/output guardrail functions
    │   │
    │   ├── memory/                           # Conversation memory management
    │   │   ├── __init__.py
    │   │   ├── manager.py                    # MemoryManager: load, window, persist
    │   │   ├── strategies.py                 # Windowing strategies: sliding, token-aware, summary
    │   │   └── summarizer.py                 # Conversation summarization
    │   │
    │   ├── rag/                              # RAG pipeline
    │   │   ├── __init__.py
    │   │   ├── pipeline.py                   # RAGPipeline: orchestrate full search
    │   │   ├── query_rewrite.py              # QueryRewriter: expansion, HyDE, decomposition
    │   │   ├── search/                       # Search implementations
    │   │   │   ├── __init__.py
    │   │   │   ├── semantic.py               # Qdrant ANN search
    │   │   │   ├── keyword.py                # PostgreSQL full-text search (tsvector)
    │   │   │   ├── hybrid.py                 # RRF fusion
    │   │   │   └── reranker.py               # Cohere re-ranker
    │   │   └── context.py                    # ContextAssembler: format chunks for LLM
    │   │
    │   ├── embeddings/                       # Embedding pipeline
    │   │   ├── __init__.py
    │   │   ├── pipeline.py                   # EmbeddingPipeline: extract → chunk → embed → store
    │   │   ├── chunking.py                   # ChunkingEngine: recursive, semantic, heading-based
    │   │   ├── embedder.py                   # Embedder: Cohere + OpenAI clients
    │   │   └── cache.py                      # Embedding cache (Redis)
    │   │
    │   ├── streaming/                        # Streaming support
    │   │   ├── __init__.py
    │   │   ├── sse.py                        # SSE event formatter + generator
    │   │   ├── websocket.py                  # WebSocket handler
    │   │   └── events.py                     # StreamEvent types
    │   │
    │   ├── rate_limit/                       # Rate limiting
    │   │   ├── __init__.py
    │   │   ├── limiter.py                    # TokenBucketRateLimiter
    │   │   └── tiers.py                      # User tier definitions
    │   │
    │   ├── security/                         # AI-specific security
    │   │   ├── __init__.py
    │   │   ├── pii_filter.py                 # PII detection + redaction
    │   │   ├── prompt_injection.py           # Injection pattern detection
    │   │   └── content_policy.py             # Content policy enforcement
    │   │
    │   ├── observability/                    # AI observability
    │   │   ├── __init__.py
    │   │   ├── tracing.py                    # OpenTelemetry span setup
    │   │   ├── metrics.py                    # Prometheus metric definitions
    │   │   ├── logging.py                    # Structured logging
    │   │   └── cost_tracker.py               # CostTracker: per-request cost accumulation
    │   │
    │   └── tests/
    │       ├── __init__.py
    │       ├── conftest.py
    │       ├── test_gateway.py
    │       ├── test_router.py
    │       ├── test_chat_agent.py
    │       ├── test_rag_agent.py
    │       ├── test_rag_pipeline.py
    │       ├── test_embedding_pipeline.py
    │       ├── test_hybrid_search.py
    │       ├── test_reranker.py
    │       ├── test_memory.py
    │       ├── test_streaming.py
    │       ├── test_rate_limit.py
    │       └── test_security.py
    │
    ├── models/
    │   ├── __init__.py
    │   ├── conversation.py                   # Conversation SQLModel
    │   ├── message.py                        # Message SQLModel
    │   ├── document.py                       # Document SQLModel
    │   ├── document_chunk.py                 # DocumentChunk SQLModel
    │   └── user.py                           # User SQLModel (reference for relationships)
    │
    ├── api/
    │   └── v1/
    │       ├── __init__.py
    │       ├── chat.py                        # POST /chat, GET /chat/{id}
    │       └── documents.py                   # POST /documents, GET /documents
    │
    └── tasks/
        ├── __init__.py
        └── embed_document.py                  # Background: chunk → embed → index
```

### 1.1 File Count Summary

| Directory | Files | Lines (estimate) |
|---|---|---|
| `ai/` (root) | 3 | 350 |
| `ai/agent/` | 10 | 1,500 |
| `ai/memory/` | 3 | 400 |
| `ai/rag/` | 7 | 1,200 |
| `ai/embeddings/` | 4 | 800 |
| `ai/streaming/` | 3 | 300 |
| `ai/rate_limit/` | 2 | 200 |
| `ai/security/` | 3 | 350 |
| `ai/observability/` | 4 | 400 |
| `ai/tests/` | 14 | 2,800 |
| **Total** | **53 files** | **~8,300 lines** |

---

## 2. AI Gateway

### 2.1 Gateway Interface

```
Class: AIGateway
Init: gateway = AIGateway(config: GatewayConfig, rate_limiter, cost_tracker, tracer)

GatewayConfig:
  max_input_tokens: int = 128_000
  max_output_tokens: int = 16_384
  stream_default: bool = True
  timeout_ms: int = 120_000
  retry_count: int = 2
  cost_tracking_enabled: bool = True

Methods:
  async process(
    user_id: UUID,
    conversation_id: UUID,
    message: str,
    request_type: str,           # "chat" | "rag" | "code" | "vision"
    stream: bool,
    preferred_model: str | None,
    ip_address: str,
    user_agent: str,
  ) -> GatewayResult:
      1. Validate input (token count, content policy)
      2. Check rate limits (user tier, IP, endpoint)
      3. Route to LLM Router → (model, provider, api_key_ref)
      4. Load conversation memory → history + windowed context
      5. If request_type == "rag":
           Run RAG pipeline → search results → inject into context
      6. Create AgentRunner → run agent → stream/gather response
      7. Track cost: call cost_tracker.record(usage, model, provider)
      8. Insert audit log (event_type='ai.chat')
      9. Return GatewayResult(response, usage, cost, trace_id)
```

### 2.2 Gateway Validation

```
Input Validation — executed before any LLM call:

  1. Total input characters → estimate tokens (≈ chars / 4)
     If estimated tokens > max_input_tokens:
       Return 400 error: "Input exceeds maximum token limit"
       
  2. Check for empty/whitespace-only messages
     If empty:
       Return 400 error: "Message cannot be empty"
       
  3. Check content policy (see 22.3)
     If blocked category detected:
       Return 400 error: "Content violates usage policy"
       
  4. Check user tier token limits
     If user tier.max_tokens_per_request < estimated_tokens:
       Return 429 error: "Request exceeds your plan's token limit"
```

### 2.3 Gateway Response

```
GatewayResult:
  response: str | StreamEvent  # Full text or AsyncGenerator[StreamEvent]
  usage: TokenUsage(input_tokens, output_tokens)
  cost: Decimal
  model: str
  provider: str
  trace_id: str
  finish_reason: str  # "stop" | "length" | "tool_calls" | "error"

TokenUsage:
  input_tokens: int
  output_tokens: int
  total_tokens: int

Error Cases:
  RATE_LIMITED       → raise RateLimitExceededException
  INPUT_TOO_LARGE    → raise BadRequestException
  CONTENT_POLICY     → raise BadRequestException
  AI_UNAVAILABLE     → raise ServiceUnavailableException
  PROVIDER_ERROR     → raise UpstreamServiceException
```

---

## 3. LLM Router

### 3.1 Router Interface

```
Class: LLMRouter
Init: router = LLMRouter(config: RouterConfig)

RouterConfig:
  models: list[ModelConfig]
  default_model: str = "gpt-4o"
  fallback_order: list[str]
  timeout_per_provider: int = 60

ModelConfig:
  name: str              # "gpt-4o" | "gemini-2.5-pro" | "grok-3"
  provider: str          # "openai" | "google" | "xai" | "openrouter"
  capabilities: list[str]     # "text" | "vision" | "tool_use" | "streaming" | "code"
  context_window: int         # 128000 | 1000000 | 131072
  cost_per_1m_input: Decimal
  cost_per_1m_output: Decimal
  fallback_group: str   # "primary" | "secondary" | "fallback"
  api_key_ref: str      # Vault key reference

Methods:
  async select(
    request_type: str,       # "chat" | "rag" | "code" | "vision"
    estimated_tokens: int,
    preferred_model: str | None,
    user_tier: str,          # "free" | "basic" | "premium"
    capabilities_required: list[str],
  ) -> SelectedModel:
      1. If preferred_model specified AND user tier has access:
         Return preferred_model
      2. If estimated_tokens > 100_000:
         Select gemini-2.5-pro (1M context)
      3. If request_type == "vision":
         Select gpt-4o or gemini-2.5-pro
      4. If request_type == "code":
         Select gpt-4o or grok-3
      5. If request_type == "rag":
         Select gpt-4o (tool calling compatible)
      6. Default:
         Select gpt-4o-mini (lowest latency, lowest cost)
      7. Apply tier overrides:
         free → gpt-4o-mini only
         basic → gpt-4o or lower
         premium → any model
         enterprise → any model + reserved capacity

  async get_fallback_model(
    failed_model: str,
    previously_tried: list[str],
  ) -> SelectedModel:
      # Walk the fallback order, skip tried models
      # Fallback chain: gpt-4o → gemini-2.5-pro → grok-3 → openrouter/gpt-4o-mini

SelectedModel:
  name: str
  provider: str
  api_key: str          # Resolved from Vault
  endpoint: str         # Provider API endpoint
  supports_stream: bool
  context_window: int
```

### 3.2 Provider Clients

| Provider | Client Library | Authentication |
|---|---|---|
| OpenAI | `openai` Python SDK | API key from `OPENAI_API_KEY` |
| Google (Gemini) | `google-generativeai` | API key from `GOOGLE_API_KEY` |
| xAI (Grok) | `openai` SDK (compatible) | API key from `GROK_API_KEY`, base_url = `https://api.x.ai/v1` |
| OpenRouter | `openai` SDK (compatible) | API key from `OPENROUTER_API_KEY`, base_url = `https://openrouter.ai/api/v1` |

### 3.3 Fallback Execution

```
async def execute_with_fallback(
    agent_config: AgentConfig,
    input: str,
    history: list,
    router: LLMRouter,
    stream: bool,
) -> RunnerResult:

    tried_providers: list[str] = []
    last_error: Exception | None = None

    for attempt in range(1 + router.config.retry_count):
        try:
            if attempt == 0:
                model = await router.select(...)
            else:
                model = await router.get_fallback_model(
                    failed_model=model.name,
                    previously_tried=tried_providers,
                )

            tried_providers.append(model.name)

            # Create provider-specific client
            client = create_provider_client(model.provider, model.api_key, model.endpoint)

            # Configure agent with this model
            agent_config.model = model.name
            agent_config.client = client

            # Run
            result = await run_agent(agent_config, input, history, stream)
            return result

        except (RateLimitError, InternalServerError, Timeout) as e:
            last_error = e
            tried_providers.append(model.name)
            logger.warning("Provider failed", provider=model.provider, error=str(e))
            continue

    # All attempts exhausted
    raise AIUnavailableException(
        message="All AI providers are currently unavailable",
        details={"tried": tried_providers, "last_error": str(last_error)},
    )
```

---

## 4. Chat Agent

### 4.1 Agent Definition

```
Agent: ChatAgent
Model: gpt-4o (default, overridable by LLM Router)
Instructions Template — compiled per request from:

  Components:
    1. Base Role Definition:
       "You are an AI learning assistant for the Enterprise AI Engineering Platform.
        You help users learn software engineering, AI, cloud, and system design
        concepts through conversation, exercises, and quizzes."

    2. Behavioral Rules:
       - "Answer in the user's preferred language: {user.locale}"
       - "Use markdown for code blocks, LaTeX for math equations."
       - "Cite sources when referencing documents or external content."
       - "If you don't know something, say so. Never fabricate answers."
       - "Keep responses concise and focused. Ask clarifying questions when needed."
       - "Adapt difficulty to the user's proficiency level: {user.proficiency}"

    3. RAG Context Injection (if RAG pipeline executed):
       "<context>
        [Source: {document_title} (page {page})]
        {chunk_text}
        [/Source]
        </context>"

    4. Conversation Window (from Memory Manager):
       "{formatted_history}"

    5. Tools Available:
       - rag_search: Search user documents for relevant information
       - web_search: Search the web for current information
       - calculator: Evaluate mathematical expressions
       - generate_quiz: Create a quiz from conversation content
       - save_note: Save a note to the user's notebook
       - translate: Translate text to the user's language

Tools Registered:
  rag_search_tool    → ToolDef(name="rag_search", args={query, top_k}, handler=rag_pipeline.search)
  web_search_tool    → ToolDef(name="web_search", args={query}, handler=web_search_client.search)
  calculator_tool    → ToolDef(name="calculator", args={expression}, handler=eval_math_expression)
  generate_quiz_tool → ToolDef(name="generate_quiz", args={topic, num_questions}, handler=quiz_generator)
  save_note_tool     → ToolDef(name="save_note", args={title, content, tags}, handler=note_service.create)
  translate_tool     → ToolDef(name="translate", args={text, target_language}, handler=translation_service)

Agent Configuration:
  model: str                    # From LLM Router
  instructions: str             # Compiled system prompt
  tools: list[ToolDef]          # Registered tools
  tool_choice: "auto"           # "auto" | "required" | "none"
  parallel_tool_calls: True
  max_turns: 20
  guardrails: [input_guard, output_guard]
```

### 4.2 Agent Runner

```
Class: AgentRunner
Init: runner = AgentRunner(config: RunnerConfig)

RunnerConfig:
  openai_api_key: str
  default_model: str
  max_tokens: int = 16_384
  temperature: float = 0.7
  top_p: float = 1.0
  presence_penalty: float = 0.0
  frequency_penalty: float = 0.0

Methods:
  async run(
    agent: Agent,
    input: str,
    history: list[Message],
    stream: bool = False,
  ) -> RunnerResult | AsyncGenerator[StreamEvent]:
      config = RunConfig(
          model=agent.model,
          instructions=agent.instructions,
          history=history,
          tools=agent.tools,
          tool_choice=agent.tool_choice,
          parallel_tool_calls=agent.parallel_tool_calls,
          max_turns=agent.max_turns,
          stream=stream,
          trace_metadata={
              "user_id": str(user_id),
              "conversation_id": str(conversation_id),
              "session_id": str(session_id),
          },
      )

      if stream:
          return Runner.streamed_run(agent, input, config)
      else:
          result = await Runner.run(agent, input, config)
          return RunnerResult(
              response=result.final_output,
              usage=result.usage,
              tool_calls=result.tool_calls,
              finish_reason=result.finish_reason,
          )

  async run_stream(
    agent: Agent,
    input: str,
    history: list[Message],
  ) -> AsyncGenerator[StreamEvent]:
      stream = Runner.streamed_run(agent, input, RunConfig(stream=True, ...))
      async for event in stream:
          yield convert_to_stream_event(event)
```

### 4.3 Guardrails

```
Input Guard — runs before agent processes user message:

  async def input_guard(user_message: str) -> GuardrailResult:
      1. Check prompt_injection_detector(message)
         If injection_score > 0.85:
           Return DENY("Message contains prompt injection attempt")
      2. Check pii_filter.contains_blocked_pii(message)
         If blocked PII detected:
           Return DENY("Message contains blocked personally identifiable information")
      3. Check content_policy.violates_policy(message)
         If policy_violation:
           Return DENY("Message violates content policy")
      4. Return ALLOW

Output Guard — runs after agent generates response:

  async def output_guard(agent_response: str) -> GuardrailResult:
      1. Check pii_filter.contains_sensitive_data(agent_response)
         If sensitive data detected:
           REDACT (PII redacted, response continues)
      2. Check prompt_leakage_detector(agent_response)
         If system prompt leakage detected:
           Return DENY("Response contains system instructions")
      3. Check content_policy.violates_policy(agent_response)
         If policy_violation:
           Return DENY("Response violates content policy")
      4. Return ALLOW
```

---

## 5. RAG Agent

### 5.1 Agent Definition

```
Agent: RagAgent
Extends: ChatAgent (inherits tools + guardrails)

Specialized Instructions:
  "You are a document-aware AI assistant. Your primary role is to answer questions
   using the user's uploaded documents. Follow these rules:

   1. ALWAYS use the rag_search tool before answering document-related questions.
   2. Cite the source document name and page number for each fact you use.
   3. If rag_search returns no results, state: 'I could not find information about
      this in your documents.'
   4. If the user asks about general knowledge, you may answer without searching.
   5. Never fabricate document content or citations.
   6. When citing, use this format: [Source: Document Title, Page N]
   7. For code-related questions from documents, include the file name and line range."

Tools Registration:
  rag_search_tool → MANDATORY (always available)
  web_search_tool → OPTIONAL (user-tier dependent)
  calculator_tool → OPTIONAL (available to all)
  generate_quiz_tool → OPTIONAL (available on request)
  save_note_tool → OPTIONAL (available on request)
  translate_tool → OPTIONAL (available on request)

Default Tool Choice: rag_search_tool is called automatically on any document-related query.
```

---

## 6. RAG Pipeline

### 6.1 Pipeline Interface

```
Class: RAGPipeline
Init: pipeline = RAGPipeline(
    semantic_search: SemanticSearch,
    keyword_search: KeywordSearch,
    reranker: RerankerClient,
    context_assembler: ContextAssembler,
    query_rewriter: QueryRewriter,
    config: RAGConfig,
)

RAGConfig:
  semantic_top_k: int = 50
  keyword_top_k: int = 50
  rrf_k: int = 60
  rerank_top_n: int = 5
  context_max_tokens: int = 25_000
  min_chunk_length: int = 50
  enable_query_rewrite: bool = True
  enable_hyde: bool = False

Methods:
  async search(
    user_id: UUID,
    query: str,
    conversation_id: UUID | None,
    filters: dict | None,      # Optional: document_id, file_type, date range
  ) -> RAGResult:
      1. Query Rewriting (if enabled):
           variants = await query_rewriter.rewrite(query)
           queries = [query] + variants
      2. For each query variant:
           a. Semantic search → Qdrant ANN
           b. Keyword search → PostgreSQL tsvector
      3. RRF Fusion: combine all result sets
      4. Re-rank: Cohere reranker on top 20
      5. Context Assembly: format top 5 for LLM
      6. Return RAGResult(chunks, context_prompt, metadata)

RAGResult:
  chunks: list[RAGChunk]
  context_prompt: str          # Formatted context for LLM injection
  metadata: RAGMetadata

RAGChunk:
  chunk_id: UUID
  document_id: UUID
  document_title: str
  chunk_text: str
  page_number: int | None
  section_heading: str | None
  relevance_score: float
  source: "semantic" | "keyword" | "reranked"

RAGMetadata:
  total_chunks_found: int
  chunks_used: int
  query_variants: list[str]
  search_latency_ms: int
  rerank_latency_ms: int
  total_latency_ms: int
```

### 6.2 Query Rewriting

```
Class: QueryRewriter
Init: rewriter = QueryRewriter(llm_client: OpenAI, config: RewriteConfig)

RewriteConfig:
  num_expansions: int = 3
  enable_decomposition: bool = True
  enable_hyde: bool = False
  language_normalization: bool = True

Methods:
  async rewrite(original_query: str) -> list[str]:
      variants: list[str] = [original_query]

      # 1. Query Expansion — generate paraphrases
      if True:
          expansions = await llm_client.chat.completions.create(
              model="gpt-4o-mini",
              messages=[
                  {"role": "system", "content":
                   "Generate {num_expansions} concise search queries that capture different
                    aspects of this question. Return one per line, no numbering."},
                  {"role": "user", "content": original_query},
              ],
              max_tokens=200,
          )
          expansions_text = expansions.choices[0].message.content
          for line in expansions_text.strip().split("\n"):
              line = line.strip().strip("-\"")
              if line and len(line) > 10:
                  variants.append(line)

      # 2. Query Decomposition — split multi-part questions
      if config.enable_decomposition and is_multi_part(original_query):
          parts = await llm_client.chat.completions.create(
              model="gpt-4o-mini",
              messages=[
                  {"role": "system", "content":
                   "Split this question into individual sub-questions. Return one per line."},
                  {"role": "user", "content": original_query},
              ],
          )
          for part in parts.choices[0].message.content.strip().split("\n"):
              part = part.strip()
              if part and len(part) > 10 and part not in variants:
                  variants.append(part)

      return variants[:5]  # Max 5 variants
```

### 6.3 Semantic Search (Qdrant)

```
Class: SemanticSearch
Init: search = SemanticSearch(qdrant_client, collection_name, embedder)

Methods:
  async search(
    query: str,
    user_id: UUID,
    top_k: int = 50,
    filters: dict | None = None,
  ) -> list[SearchResult]:
      1. Embed query:
           query_vector = await embedder.embed_query(query)
           
      2. Build Qdrant filter:
           filter = Filter(
               must=[
                   FieldCondition(key="user_id", match=MatchValue(value=str(user_id))),
               ]
           )
           if filters:
               for key, value in filters.items():
                   filter.must.append(FieldCondition(key=key, match=MatchValue(value=value)))
           
      3. Execute search:
           results = qdrant_client.search(
               collection_name=collection_name,
               query_vector=query_vector,
               query_filter=filter,
               limit=top_k,
               with_payload=["document_id", "chunk_text", "chunk_index",
                             "page_number", "section_heading", "file_type", "file_name"],
               score_threshold=0.5,
           )
           
      4. Return [SearchResult(
              chunk_id=point.id,
              score=point.score,
              text=point.payload["chunk_text"],
              metadata=point.payload,
          ) for point in results]

SearchResult:
  chunk_id: UUID
  score: float
  text: str
  metadata: dict
  search_type: "semantic"
```

### 6.4 Keyword Search (PostgreSQL tsvector)

```
Class: KeywordSearch
Init: search = KeywordSearch(db_session_factory)

Methods:
  async search(
    query: str,
    user_id: UUID,
    top_k: int = 50,
  ) -> list[SearchResult]:
      1. Parse query to tsquery:
           tsquery = plainto_tsquery("english", query)
           
      2. Execute full-text search:
           SELECT
               dc.id, dc.chunk_text, dc.chunk_index,
               dc.page_number, dc.section_heading,
               d.title, d.file_type, d.file_name,
               ts_rank_cd(dc.search_vector, :tsquery) AS rank
           FROM document_chunks dc
           JOIN documents d ON d.id = dc.document_id
           WHERE d.user_id = :user_id
             AND dc.deleted_at IS NULL
             AND d.deleted_at IS NULL
             AND dc.search_vector @@ :tsquery
           ORDER BY rank DESC
           LIMIT :top_k
           
      3. Return [SearchResult(
              chunk_id=row.id,
              score=row.rank,
              text=row.chunk_text,
              metadata={document_id, chunk_index, page_number, section_heading,
                        file_type, file_name, title},
          ) for row in results]
```

### 6.5 RRF Fusion

```
Function: rrf_fusion(
    semantic_results: list[SearchResult],
    keyword_results: list[SearchResult],
    k: int = 60,
    top_k: int = 20,
) -> list[FusedResult]:

    1. Build rank map:
         ranks: dict[str, list[int]] = {}
         for i, r in enumerate(semantic_results):
             ranks[r.chunk_id] = [i + 1, None]
         for i, r in enumerate(keyword_results):
             if r.chunk_id in ranks:
                 ranks[r.chunk_id][1] = i + 1
             else:
                 ranks[r.chunk_id] = [None, i + 1]
                 
    2. Compute RRF scores:
         fused: list[FusedResult] = []
         for chunk_id, (sem_rank, kw_rank) in ranks.items():
             score = 0.0
             if sem_rank is not None:
                 score += 1.0 / (k + sem_rank)
             if kw_rank is not None:
                 score += 1.0 / (k + kw_rank)
             fused.append(FusedResult(
                 chunk_id=chunk_id,
                 rrf_score=score,
                 semantic_rank=sem_rank,
                 keyword_rank=kw_rank,
             ))
             
    3. Sort by rrf_score descending:
         fused.sort(key=lambda x: x.rrf_score, reverse=True)
         
    4. Return top_k

FusedResult:
  chunk_id: UUID
  rrf_score: float
  semantic_rank: int | None
  keyword_rank: int | None
  text: str             # Populated from original results
  metadata: dict
```

### 6.6 Re-ranker (Cohere)

```
Class: RerankerClient
Init: reranker = RerankerClient(
    api_key: str,
    model: str = "rerank-v3.5",
    max_chunks: int = 100,
)

Methods:
  async rerank(
    query: str,
    chunks: list[RAGChunk],
    top_n: int = 5,
  ) -> list[RerankedChunk]:
      1. If len(chunks) > max_chunks:
           Truncate to max_chunks (keep highest-scored)
           
      2. Call Cohere API:
           response = cohere_client.rerank(
               model=model,
               query=query,
               documents=[c.chunk_text for c in chunks],
               top_n=top_n,
           )
           
      3. Map results back to chunks:
           reranked = []
           for r in response.results:
               original = chunks[r.index]
               reranked.append(RerankedChunk(
                   chunk_id=original.chunk_id,
                   chunk_text=original.chunk_text,
                   relevance_score=r.relevance_score,
                   metadata=original.metadata,
               ))
               
      4. Cache result: Redis, key=rerank:{hash(query)}:{hash(chunk_ids)}, TTL=5min
      5. Return reranked

RerankedChunk:
  chunk_id: UUID
  chunk_text: str
  relevance_score: float     # 0.0 - 1.0
  metadata: dict
```

### 6.7 Context Assembly

```
Class: ContextAssembler
Init: assembler = ContextAssembler(config: ContextConfig)

ContextConfig:
  max_tokens: int = 25_000
  include_page_numbers: bool = True
  include_section_headings: bool = True
  citation_format: str = "markdown"

Methods:
  async assemble(
    chunks: list[RerankedChunk],
    conversation_history: list[Message] | None,
  ) -> AssembledContext:
      1. Sort chunks by relevance_score (descending)
      2. Format each chunk:
           formatted_chunks: list[str] = []
           for chunk in chunks:
               header = f"[Source: {chunk.metadata['title']}"
               if config.include_page_numbers and chunk.metadata.get('page_number'):
                   header += f", Page {chunk.metadata['page_number']}"
               if config.include_section_headings and chunk.metadata.get('section_heading'):
                   header += f", Section: {chunk.metadata['section_heading']}"
               header += "]"
               formatted = f"{header}\n{chunk.chunk_text}\n[/Source]"
               formatted_chunks.append(formatted)
               
      3. Token budget allocation:
           budget = config.max_tokens
           history_tokens = estimate_tokens(conversation_history) if conversation_history else 0
           chunk_budget = budget - history_tokens
           used: list[str] = []
           used_tokens = 0
           for fc in formatted_chunks:
               tokens = estimate_tokens(fc)
               if used_tokens + tokens <= chunk_budget:
                   used.append(fc)
                   used_tokens += tokens
               else:
                   break
                   
      4. Build context string:
           context_xml = "<context>\n" + "\n\n".join(used) + "\n</context>"
           
      5. Return AssembledContext(
             context_string=context_xml,
             chunk_count=len(used),
             total_tokens=used_tokens,
         )

AssembledContext:
  context_string: str
  chunk_count: int
  total_tokens: int
```

---

## 7. Document Upload

### 7.1 Upload Endpoint Contract

```
POST /api/v1/documents
Content-Type: multipart/form-data
Authorization: Bearer <access_token>

Fields:
  file: File (required)               # The document to upload
  conversation_id: UUID (optional)     # Link to conversation

Response 202:
  {
    "status": "success",
    "data": {
      "document_id": "0194f2a0-...",
      "file_name": "transformer-paper.pdf",
      "file_type": "pdf",
      "file_size": 2_456_000,
      "status": "processing",
      "created_at": "2026-07-30T10:00:00Z"
    }
  }

Response 400:
  {
    "status": "error",
    "error": {
      "code": "INVALID_FILE_TYPE",
      "message": "File type .exe is not supported."
    }
  }

Response 413:
  {
    "status": "error",
    "error": {
      "code": "FILE_TOO_LARGE",
      "message": "File exceeds maximum size of 50 MB."
    }
  }

Response 409:
  {
    "status": "error",
    "error": {
      "code": "DUPLICATE_FILE",
      "message": "This file has already been uploaded."
    }
  }
```

### 7.2 Upload Handler Logic

```
async def handle_document_upload(
    user_id: UUID,
    file: UploadFile,
    conversation_id: UUID | None,
    db: AsyncSession,
    storage: ObjectStorageClient,
    task_queue: TaskQueue,
) -> DocumentResponse:

    1. Validate file:
         if file.filename.split(".")[-1].lower() not in SUPPORTED_EXTENSIONS:
             raise BadRequestException("INVALID_FILE_TYPE")
         if file.size > MAX_FILE_SIZE:  # 50 MB
             raise BadRequestException("FILE_TOO_LARGE")
             
    2. Read file bytes into memory buffer:
         content = await file.read()
         
    3. Compute SHA-256 hash:
         file_hash = hashlib.sha256(content).hexdigest()
         
    4. Check for duplicate:
         existing = db.query(Document).filter(
             Document.user_id == user_id,
             Document.content_hash == file_hash,
             Document.deleted_at.is_(None),
         ).first()
         if existing:
             raise ConflictException("DUPLICATE_FILE")
             
    5. Detect MIME type:
         mime_type = magic.from_buffer(content[:2048], mime=True)
         
    6. Upload to object store:
         storage_key = f"users/{user_id}/documents/{uuid7()}.{ext}"
         await storage.upload(
             bucket=BUCKET_DOCUMENTS,
             key=storage_key,
             body=content,
             content_type=mime_type,
         )
         
    7. Create document record:
         document = Document(
             user_id=user_id,
             conversation_id=conversation_id,
             title=file.filename.rsplit(".", 1)[0],
             file_name=file.filename,
             file_type=ext,
             file_size=file.size,
             storage_url=storage_key,
             content_hash=file_hash,
             status="processing",
         )
         db.add(document)
         await db.commit()
         await db.refresh(document)
         
    8. Enqueue background embedding task:
         await task_queue.enqueue(
             task="embed_document",
             payload={
                 "document_id": document.id,
                 "user_id": user_id,
                 "storage_url": storage_key,
                 "file_type": ext,
             },
         )
         
    9. Insert audit log:
         audit.log(event_type="document.uploaded", ...)
         
    10. Return 202 response with document_id
```

### 7.3 Supported File Types

| Extension | MIME Type | Max Size | Parser |
|---|---|---|---|
| `.pdf` | `application/pdf` | 50 MB | PyMuPDF (fitz) |
| `.docx` | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` | 25 MB | python-docx |
| `.txt` | `text/plain` | 10 MB | UTF-8 decode |
| `.md` | `text/markdown` | 10 MB | UTF-8 decode |
| `.csv` | `text/csv` | 25 MB | csv module |
| `.html` | `text/html` | 10 MB | BeautifulSoup |
| `.htm` | `text/html` | 10 MB | BeautifulSoup |
| `.py` | `text/x-python` | 5 MB | UTF-8 decode |
| `.js` | `text/javascript` | 5 MB | UTF-8 decode |
| `.ts` | `text/typescript` | 5 MB | UTF-8 decode |
| `.java` | `text/x-java` | 5 MB | UTF-8 decode |
| `.cpp` | `text/x-c++` | 5 MB | UTF-8 decode |
| `.rs` | `text/rust` | 5 MB | UTF-8 decode |
| `.go` | `text/x-go` | 5 MB | UTF-8 decode |

---

## 8. PDF Parsing

### 8.1 PDF Extractor

```
Class: PDFExtractor
Library: PyMuPDF (fitz)
Init: extractor = PDFExtractor()

Methods:
  async extract(pdf_bytes: bytes) -> ExtractionResult:
      1. Open document: fitz.open(stream=pdf_bytes, filetype="pdf")
      2. Iterate over pages:
           for page_num, page in enumerate(doc):
               text = page.get_text("text")
               if text.strip():
                   pages.append(PageContent(
                       page_number=page_num + 1,
                       text=text,
                       word_count=len(text.split()),
                   ))
      3. Extract metadata:
           metadata = {
               "title": doc.metadata.get("title", ""),
               "author": doc.metadata.get("author", ""),
               "subject": doc.metadata.get("subject", ""),
               "page_count": len(doc),
           }
      4. doc.close()
      5. Return ExtractionResult(pages, metadata, total_chars)

ExtractionResult:
  pages: list[PageContent]
  metadata: dict
  total_chars: int

PageContent:
  page_number: int
  text: str
  word_count: int

Notes:
  - Extract text layer only (ignore images)
  - If page has no extractable text (scanned PDF), raise ExtractionError
  - Detect and skip headers/footers by position analysis
  - Merge hyphenated words split across lines
```

---

## 9. Chunking

### 9.1 Chunking Engine

```
Class: ChunkingEngine
Init: engine = ChunkingEngine(config: ChunkingConfig)

ChunkingConfig:
  default_strategy: str = "recursive"
  chunk_size: int = 1000        # Characters
  chunk_overlap: int = 200      # Characters
  min_chunk_length: int = 50
  max_chunk_length: int = 2000
  respect_sentences: bool = True
  respect_paragraphs: bool = True
  tokenizer_model: str = "cl100k_base"   # tiktoken

Strategies:
  recursive:   RecursiveCharacterTextSplitter
  semantic:    Sentence boundary splitter
  heading:     Section-by-heading splitter
  token:       Token-aware splitter (512 tokens, 128 overlap)

Methods:
  async chunk(
    text: str,
    file_type: str,
    metadata: dict,
    strategy: str | None = None,
  ) -> list[Chunk]:
      1. Pre-process text:
           text = normalize_whitespace(text)
           text = unicodedata.normalize("NFKC", text)
           text = text.strip()
           
      2. Detect structure:
           structure = detect_structure(text)
           # headings, code blocks, tables, lists
           
      3. Select strategy:
           if strategy:
               selected = strategy
           elif file_type in ("py", "js", "ts", "java", "cpp", "rs", "go"):
               selected = "recursive"
           elif structure.has_headings:
               selected = "heading"
           elif structure.is_narrative:
               selected = "semantic"
           else:
               selected = "recursive"
               
      4. Apply selected strategy:
           chunks = await self._chunk_by_strategy(text, selected, structure)
           
      5. Post-process chunks:
           cleaned = []
           for chunk in chunks:
               chunk.text = chunk.text.strip()
               if len(chunk.text) < min_chunk_length:
                   continue   # Merge with previous chunk
               if len(chunk.text) > max_chunk_length:
                   sub_chunks = split_long_chunk(chunk, max_chunk_length)
                   cleaned.extend(sub_chunks)
               else:
                   cleaned.append(chunk)
                   
      6. Enrich with metadata:
           for chunk in cleaned:
               chunk.metadata["char_count"] = len(chunk.text)
               chunk.metadata["token_count"] = estimate_tokens(chunk.text)
               chunk.metadata["file_type"] = file_type
               
      7. Return cleaned

Chunk:
  index: int
  text: str
  token_count: int
  char_count: int
  metadata: dict        # page_number, section_heading, document_id
```

### 9.2 Recursive Strategy

```
Strategy: RecursiveCharacterTextSplitter

Separators in order:
  1. "\n\n" (paragraphs)
  2. "\n"   (lines)
  3. ". "   (sentences)
  4. " "    (words)
  5. ""     (characters)

Algorithm:
  def recursive_split(text: str, chunk_size: int, overlap: int):
      if len(text) <= chunk_size:
          return [Chunk(text=text)]
          
      # Try each separator in order
      for sep in separators:
          if sep in text:
              splits = text.split(sep)
              chunks = []
              current = ""
              for split in splits:
                  if len(current) + len(sep) + len(split) <= chunk_size:
                      current += sep + split if current else split
                  else:
                      if current:
                          chunks.append(Chunk(text=current))
                      current = split
              if current:
                  chunks.append(Chunk(text=current))
                  
              # Apply overlap
              return apply_overlap(chunks, overlap)
              
      # Fallback: character-level split
      return [Chunk(text=text[i:i+chunk_size]) for i in range(0, len(text), chunk_size - overlap)]
```

### 9.3 Heading-Based Strategy

```
Strategy: HeadingBasedSplitter

Algorithm:
  1. Detect headings via regex:
       # ^#{1,6}\s.+ (Markdown ATX)
       # ^={3,}$ preceded by text line (Markdown Setext H1)
       # ^-{3,}$ preceded by text line (Markdown Setext H2)
       # ^[A-Z][A-Z\s]+$ (all-caps lines in plain text)
       
  2. Split at each heading boundary:
       chunks = []
       current_section = {"heading": None, "text": []}
       for line in text.split("\n"):
           if is_heading(line):
               if current_section["text"]:
                   chunks.append(Chunk(
                       text="\n".join(current_section["text"]),
                       metadata={"heading": current_section["heading"]},
                   ))
               current_section = {"heading": line.strip("# ").strip(), "text": []}
           else:
               current_section["text"].append(line)
       if current_section["text"]:
           chunks.append(...)
           
  3. Merge small sections (< min_chunk_length) with next
  4. If any chunk > max_chunk_length, apply recursive split on that chunk
```

---

## 10. Embeddings

### 10.1 Embedder Interface

```
Class: Embedder
Init: embedder = Embedder(
    cohere_api_key: str,
    openai_api_key: str | None,     # Secondary
    default_model: str = "embed-multilingual-v3.0",
    batch_size: int = 96,
)

Methods:
  async embed_documents(
    texts: list[str],
    model: str | None = None,
  ) -> list[list[float]]:
      1. Validate texts (non-empty, max 2048 tokens each)
      2. Choose model: model or self.default_model
      3. If model starts with "embed-":
           # Cohere
           responses = []
           for batch in batched(texts, batch_size):
               resp = cohere_client.embed(
                   texts=batch,
                   model=model,
                   input_type="search_document",
                   truncate="END",
               )
               responses.extend(resp.embeddings)
      4. If model starts with "text-embedding-":
           # OpenAI
           responses = openai_client.embeddings.create(
               model=model,
               input=texts,
           )
           responses = [r.embedding for r in responses.data]
      5. Retry on transient failure (3 attempts, exponential backoff)
      6. Return responses

  async embed_query(
    query: str,
    model: str | None = None,
  ) -> list[float]:
      1. Same as embed_documents but with input_type="search_query" (Cohere)
      2. Single text, no batching needed
      3. Return single embedding vector

  def get_dimensions(model: str) -> int:
      return {
          "embed-multilingual-v3.0": 1024,
          "embed-english-v3.0": 1024,
          "text-embedding-3-small": 1536,
          "text-embedding-3-large": 3072,
      }.get(model, 1024)
```

### 10.2 Embedding Pipeline

```
Class: EmbeddingPipeline
Init: pipeline = EmbeddingPipeline(
    embedder: Embedder,
    chunking_engine: ChunkingEngine,
    qdrant_client: QdrantClient,
    db_session_factory: Callable,
    storage_client: ObjectStorageClient,
    cache: EmbeddingCache,
    config: EmbeddingPipelineConfig,
)

EmbeddingPipelineConfig:
  embedding_model: str = "embed-multilingual-v3.0"
  chunk_strategy: str = "recursive"
  chunk_size: int = 1000
  chunk_overlap: int = 200
  qdrant_collection: str = "ai_enterprises_embeddings_v1"
  min_chunk_length: int = 50

Methods:
  async process_document(document_id: UUID):
      1. Load document from DB:
           document = db.query(Document).get(document_id)
           
      2. Download from object store:
           content = await storage_client.download(
               bucket=BUCKET_DOCUMENTS,
               key=document.storage_url,
           )
           
      3. Extract text based on file_type:
           if document.file_type == "pdf":
               result = pdf_extractor.extract(content)
               raw_text = "\n\n".join([p.text for p in result.pages])
               page_map = {p.page_number: p.text for p in result.pages}
           elif document.file_type == "docx":
               result = docx_extractor.extract(content)
               raw_text = result.text
           else:
               raw_text = content.decode("utf-8")
               
      4. Chunk text:
           chunks = await chunking_engine.chunk(
               text=raw_text,
               file_type=document.file_type,
               metadata={"document_id": str(document_id)},
           )
           
      5. Check embedding cache (by text hash):
           uncached_chunks = []
           for chunk in chunks:
               text_hash = hashlib.sha256(chunk.text.encode()).hexdigest()
               cached = await cache.get(text_hash)
               if cached:
                   chunk.vector = cached
               else:
                   uncached_chunks.append(chunk)
                   
      6. Embed uncached chunks:
           if uncached_chunks:
               texts = [c.text for c in uncached_chunks]
               vectors = await embedder.embed_documents(texts)
               for chunk, vector in zip(uncached_chunks, vectors):
                   chunk.vector = vector
                   await cache.set(text_hash(text), vector, ttl=86400)
                   
      7. Store in Qdrant:
           points = []
           for chunk in chunks:
               payload = {
                   "document_chunk_id": str(chunk.id) if hasattr(chunk, 'id') else str(uuid7()),
                   "document_id": str(document_id),
                   "user_id": str(document.user_id),
                   "chunk_index": chunk.index,
                   "chunk_text": chunk.text[:20000],   # Qdrant payload limit
                   "file_type": document.file_type,
                   "file_name": document.file_name,
                   "token_count": chunk.token_count,
                   "char_count": chunk.char_count,
                   "embedding_model": config.embedding_model,
                   "created_at": datetime.utcnow().isoformat(),
               }
               if chunk.metadata.get("page_number"):
                   payload["page_number"] = chunk.metadata["page_number"]
               if chunk.metadata.get("section_heading"):
                   payload["section_heading"] = chunk.metadata["section_heading"][:500]
                   
               points.append(PointStruct(
                   id=str(uuid7()),
                   vector=chunk.vector,
                   payload=payload,
               ))
               
           qdrant_client.upsert(
               collection_name=config.qdrant_collection,
               points=points,
           )
           
      8. Store chunks in PostgreSQL:
           for chunk in chunks:
               db_chunk = DocumentChunk(
                   document_id=document_id,
                   chunk_index=chunk.index,
                   chunk_text=chunk.text,
                   token_count=chunk.token_count,
                   metadata={
                       "page_number": chunk.metadata.get("page_number"),
                       "section_heading": chunk.metadata.get("section_heading"),
                       "file_type": document.file_type,
                   },
               )
               db.add(db_chunk)
               
      9. Update document status:
           document.status = "ready"
           document.chunk_count = len(chunks)
           document.is_indexed = True
           document.indexed_at = datetime.utcnow()
           db.commit()
           
      10. Insert audit log:
            audit.log(event_type="document.indexed", resource="document", resource_id=document_id)
```

---

## 11. Metadata

### 11.1 Qdrant Collection Schema

```
Collection: ai_enterprises_embeddings_v1

Vector Configuration:
  size: 1024 (Cohere multilingual) or 1536 (OpenAI)
  distance: Cosine
  multivector_config: null

Payload Schema (all fields):
  ┌─────────────────────┬──────────┬───────────────┬──────────────┐
  │ Field               │ Type     │ Indexed       │ Max Length   │
  ├─────────────────────┼──────────┼───────────────┼──────────────┤
  │ document_chunk_id   │ keyword  │ YES           │ 36 (UUID)    │
  │ document_id         │ keyword  │ YES           │ 36 (UUID)    │
  │ user_id             │ keyword  │ YES           │ 36 (UUID)    │
  │ chunk_index         │ integer  │ YES (range)   │ —            │
  │ chunk_text          │ text     │ NO            │ 20,000       │
  │ file_type           │ keyword  │ YES           │ 10           │
  │ file_name           │ keyword  │ NO            │ 500          │
  │ page_number         │ integer  │ YES (range)   │ —            │
  │ section_heading     │ text     │ NO            │ 500          │
  │ token_count         │ integer  │ NO            │ —            │
  │ char_count          │ integer  │ NO            │ —            │
  │ embedding_model     │ keyword  │ NO            │ 50           │
  │ created_at          │ datetime │ YES (range)   │ —            │
  └─────────────────────┴──────────┴───────────────┴──────────────┘

HNSW Index Configuration:
  m: 16
  ef_construct: 200
  full_scan_threshold: 10000

Optimizer Configuration:
  memmap_threshold_kb: 1024
  indexing_threshold: 20000
  flush_interval_sec: 5

Write Consistency: Majority
Read Consistency: Majority
Replication Factor: 2
Shard Number: 4
```

### 11.2 Qdrant Payload Indexes

```
Payload indexes to create on collection initialization:

  PUT /collections/ai_enterprises_embeddings_v1/index
  {
    "field_name": "user_id",
    "field_type": "keyword"
  }
  
  PUT /collections/ai_enterprises_embeddings_v1/index
  {
    "field_name": "document_id",
    "field_type": "keyword"
  }
  
  PUT /collections/ai_enterprises_embeddings_v1/index
  {
    "field_name": "file_type",
    "field_type": "keyword"
  }
  
  PUT /collections/ai_enterprises_embeddings_v1/index
  {
    "field_name": "chunk_index",
    "field_type": "integer"
  }
  
  PUT /collections/ai_enterprises_embeddings_v1/index
  {
    "field_name": "page_number",
    "field_type": "integer"
  }
  
  PUT /collections/ai_enterprises_embeddings_v1/index
  {
    "field_name": "created_at",
    "field_type": "datetime"
  }
```

### 11.3 Qdrant Collection Initialization

```
async def ensure_collection_exists(qdrant_client: QdrantClient, config: QdrantConfig):
    collections = qdrant_client.get_collections().collections
    exists = any(c.name == config.collection_name for c in collections)
    
    if not exists:
        qdrant_client.create_collection(
            collection_name=config.collection_name,
            vectors_config=VectorParams(
                size=config.vector_size,
                distance=Distance.COSINE,
            ),
            hnsw_config=HnswConfig(
                m=16,
                ef_construct=200,
                full_scan_threshold=10000,
            ),
            optimizers_config=OptimizersConfigDiff(
                memmap_threshold_kb=1024,
                indexing_threshold=20000,
            ),
            replication_factor=2,
            shard_number=4,
            write_consistency_factor=1,
            on_disk_payload=True,
        )
        
        # Create payload indexes
        for field_config in PAYLOAD_INDEXES:
            qdrant_client.create_payload_index(
                collection_name=config.collection_name,
                field_name=field_config["field_name"],
                field_type=field_config["field_type"],
            )
```

---

## 12. Hybrid Search

### 12.1 Hybrid Search Service

```
Class: HybridSearchService
Init: service = HybridSearchService(
    semantic: SemanticSearch,
    keyword: KeywordSearch,
    reranker: RerankerClient,
    assembler: ContextAssembpler,
    query_rewriter: QueryRewriter,
    config: HybridSearchConfig,
)

HybridSearchConfig:
  semantic_top_k: int = 50
  keyword_top_k: int = 50
  rrf_k: int = 60
  rerank_top_n: int = 5
  context_max_tokens: int = 25_000
  enable_rewrite: bool = True

Methods:
  async search(
    user_id: UUID,
    query: str,
    filters: dict | None = None,
  ) -> RAGResult:
      1. trace_id = str(uuid7())
      2. start_time = time.monotonic()
       
      3. Query rewriting:
           if config.enable_rewrite:
               queries = await self.query_rewriter.rewrite(query)
           else:
               queries = [query]
               
      4. Execute searches in parallel for each variant:
           all_semantic = []
           all_keyword = []
           for q in queries:
               sem_task = self.semantic.search(query=q, user_id=user_id, top_k=config.semantic_top_k, filters=filters)
               kw_task = self.keyword.search(query=q, user_id=user_id, top_k=config.keyword_top_k)
               sem_results, kw_results = await asyncio.gather(sem_task, kw_task)
               all_semantic.extend(sem_results)
               all_keyword.extend(kw_results)
               
      5. Deduplicate by chunk_id:
           seen = set()
           deduped_semantic = []
           for r in all_semantic:
               if r.chunk_id not in seen:
                   seen.add(r.chunk_id)
                   deduped_semantic.append(r)
           deduped_keyword = [r for r in all_keyword if r.chunk_id not in seen] + \
                             [r for r in all_keyword if r.chunk_id in seen]
           # (keyword results deduped differently — keep all for RRF)
           
      6. RRF fusion:
           fused = rrf_fusion(deduped_semantic, all_keyword, k=config.rrf_k, top_k=20)
           
      7. Retrieve full text + metadata for fused results:
           fused_with_text = await self._enrich_fused(fused, all_semantic, all_keyword)
           
      8. Re-rank:
           reranked = await self.reranker.rerank(query, fused_with_text, top_n=config.rerank_top_n)
           
      9. Context assembly:
           context = await self.assembler.assemble(reranked, conversation_history=None)
           
      10. end_time = time.monotonic()
       
      11. Return RAGResult(
              chunks=reranked,
              context_prompt=context.context_string,
              metadata=RAGMetadata(
                  total_chunks_found=len(fused),
                  chunks_used=len(reranked),
                  query_variants=queries,
                  search_latency_ms=int((end_time - start_time) * 1000),
              ),
          )
```

### 12.2 User Isolation Filter

```
Every Qdrant search MUST include a user_id filter:

  filter_condition = Filter(
      must=[
          FieldCondition(
              key="user_id",
              match=MatchValue(value=str(user_id)),
          ),
      ]
  )

  # Optional additional filters
  if filters:
      for key, value in filters.items():
          if key == "document_id":
              filter_condition.must.append(
                  FieldCondition(key="document_id", match=MatchValue(value=str(value)))
              )
          elif key == "file_type":
              filter_condition.must.append(
                  FieldCondition(key="file_type", match=MatchValue(value=str(value)))
              )

  results = qdrant_client.search(
      collection_name=collection_name,
      query_vector=vector,
      query_filter=filter_condition,
      limit=top_k,
  )
```

---

## 13. Memory

### 13.1 Memory Manager

```
Class: MemoryManager
Init: manager = MemoryManager(db_session_factory, redis_client, config: MemoryConfig)

MemoryConfig:
  window_strategy: str = "sliding"       # "sliding" | "token_aware" | "summary" | "full"
  sliding_window_size: int = 10          # Messages
  token_aware_max_tokens: int = 32000
  summary_ttl_seconds: int = 86400       # 24h
  enable_summarization: bool = True

Methods:
  async load_history(
    conversation_id: UUID,
    user_id: UUID,
    strategy: str | None = None,
  ) -> ConversationHistory:
      1. Check Redis cache:
           cache_key = f"conv:{conversation_id}:history"
           cached = await redis.get(cache_key)
           if cached:
               return ConversationHistory.from_json(cached)
               
      2. Load from PostgreSQL:
           rows = await db.execute(
               SELECT m.id, m.role, m.content, m.metadata, m.token_count, m.created_at
               FROM messages m
               WHERE m.conversation_id = :conv_id AND m.deleted_at IS NULL
               ORDER BY m.sequence_number ASC
           )
           messages = [Message.from_db(r) for r in rows]
           
      3. Apply windowing strategy:
           strategy = strategy or config.window_strategy
           if strategy == "sliding":
               windowed = messages[-config.sliding_window_size:]
           elif strategy == "token_aware":
               windowed = token_aware_window(messages, config.token_aware_max_tokens)
           elif strategy == "summary":
               windowed = await summary_window(messages, config)
           elif strategy == "full":
               windowed = messages
               
      4. Format for OpenAI Agents SDK:
           history = []
           for msg in windowed:
               role = "user" if msg.role == "user" else "assistant"
               history.append({"role": role, "content": msg.content})
               
      5. Cache in Redis:
           await redis.set(cache_key, history.to_json(), ex=300)  # 5 min
           
      6. Return ConversationHistory(messages=history, total_count=len(messages), windowed_count=len(windowed))

  async persist_messages(
    conversation_id: UUID,
    user_id: UUID,
    new_messages: list[dict],     # [{role, content, metadata}]
  ) -> None:
      1. Get next sequence number:
           max_seq = SELECT MAX(sequence_number) FROM messages WHERE conversation_id = :conv_id
           next_seq = (max_seq or 0) + 1
           
      2. Insert messages:
           for i, msg in enumerate(new_messages):
               db_message = Message(
                   conversation_id=conversation_id,
                   user_id=user_id if msg["role"] == "user" else None,
                   role=msg["role"],
                   content=msg["content"],
                   metadata=msg.get("metadata", {}),
                   token_count=estimate_tokens(msg["content"]),
                   sequence_number=next_seq + i,
               )
               db.add(db_message)
           await db.commit()
           
      3. Update conversation metadata:
           UPDATE conversations
           SET message_count = message_count + len(new_messages),
               last_message_at = now()
           WHERE id = :conv_id
           
      4. Invalidate cache:
           await redis.delete(f"conv:{conversation_id}:history")
```

### 13.2 Windowing Strategies

```
Strategy 1: Sliding Window
  Keep the last N messages
  Input: messages (list), window_size (int = 10)
  Output: messages[-window_size:]

Strategy 2: Token-Aware Window
  Keep messages until token budget is exhausted
  Input: messages (list), max_tokens (int = 32000)
  Algorithm:
    total = 0
    windowed = []
    for msg in reversed(messages):
        tokens = msg.token_count or estimate_tokens(msg.content)
        if total + tokens > max_tokens:
            break
        windowed.insert(0, msg)
        total += tokens
    return windowed

Strategy 3: Summary + Recent
  First N messages summarized, last M messages kept verbatim
  Input: messages (list), config
  Algorithm:
    if len(messages) <= config.sliding_window_size:
        return messages
    old_messages = messages[:-config.sliding_window_size]
    recent_messages = messages[-config.sliding_window_size:]
    summary = await summarizer.summarize(old_messages)
    return [summary_message] + recent_messages
    
  Summary message format:
    {"role": "system", "content": "Previous conversation summary: {summary_text}"}
```

---

## 14. Streaming

### 14.1 SSE Event Types

```
Event: message_start
  Trigger: Agent run begins
  Payload: {"type": "message_start", "conversation_id": UUID, "trace_id": str}

Event: content_delta
  Trigger: Token-by-token generation
  Payload: {"type": "content_delta", "delta": str}

Event: content_done
  Trigger: Full text block complete
  Payload: {"type": "content_done", "content": str}

Event: tool_call_start
  Trigger: Agent initiates a tool call
  Payload: {"type": "tool_call_start", "tool": str, "tool_call_id": str, "arguments": dict}

Event: tool_call_end
  Trigger: Tool execution complete
  Payload: {"type": "tool_call_end", "tool": str, "tool_call_id": str, "result": any}

Event: message_done
  Trigger: Full agent response complete
  Payload: {
    "type": "message_done",
    "finish_reason": "stop" | "length" | "tool_calls",
    "usage": {"input_tokens": int, "output_tokens": int, "total_tokens": int}
  }

Event: error
  Trigger: Non-recoverable error during agent run
  Payload: {"type": "error", "code": str, "message": str}

Event: done
  Trigger: Stream complete (sentinel)
  Payload: {"type": "done"}
```

### 14.2 SSE Formatter

```
Class: SSEFormatter

Methods:
  format_event(event_type: str, data: dict) -> str:
      # Format: "event: {type}\ndata: {json}\n\n"
      lines = [f"event: {event_type}", f"data: {json.dumps(data)}", ""]
      return "\n".join(lines)

  async stream_generator(
    agent_runner: AgentRunner,
    agent: Agent,
    input: str,
    history: list,
  ) -> AsyncGenerator[str, None]:
      yield SSEFormatter.format_event("message_start", {
          "conversation_id": str(conversation_id),
          "trace_id": trace_id,
      })
      
      stream = await agent_runner.run_stream(agent, input, history)
      
      async for event in stream:
          if event.type == "raw_response_event":
              for delta in event.data.deltas:
                  if delta.type == "text":
                      yield SSEFormatter.format_event("content_delta", {"delta": delta.text})
          elif event.type == "tool_call":
              yield SSEFormatter.format_event("tool_call_start", {
                  "tool": event.tool.name,
                  "tool_call_id": event.tool_call_id,
                  "arguments": event.tool.arguments,
              })
          elif event.type == "tool_return":
              yield SSEFormatter.format_event("tool_call_end", {
                  "tool": event.tool.name,
                  "tool_call_id": event.tool_call_id,
                  "result": event.result,
              })
          elif event.type == "agent_end":
              yield SSEFormatter.format_event("message_done", {
                  "finish_reason": event.finish_reason,
                  "usage": {
                      "input_tokens": event.usage.input_tokens,
                      "output_tokens": event.usage.output_tokens,
                      "total_tokens": event.usage.total_tokens,
                  },
              })
          elif event.type == "error":
              yield SSEFormatter.format_event("error", {
                  "code": event.error.code,
                  "message": event.error.message,
              })
              
      yield SSEFormatter.format_event("done", {})
```

### 14.3 FastAPI Streaming Endpoint

```
POST /api/v1/chat
Authorization: Bearer <access_token>
Content-Type: application/json
Accept: text/event-stream

Response:
  Content-Type: text/event-stream
  Cache-Control: no-cache
  Connection: keep-alive
  X-Accel-Buffering: no

  event: message_start
  data: {"type":"message_start","conversation_id":"0194...","trace_id":"abc..."}
  
  event: content_delta
  data: {"type":"content_delta","delta":"Attention"}
  
  event: content_delta
  data: {"type":"content_delta","delta":" mechanisms"}
  
  event: tool_call_start
  data: {"type":"tool_call_start","tool":"rag_search","tool_call_id":"call_123","arguments":{"query":"transformer attention","top_k":5}}
  
  event: tool_call_end
  data: {"type":"tool_call_end","tool":"rag_search","tool_call_id":"call_123","result":{"chunks_found":3}}
  
  event: content_delta
  data: {"type":"content_delta","delta":" allow models to..."}
  
  event: message_done
  data: {"type":"message_done","finish_reason":"stop","usage":{"input_tokens":452,"output_tokens":183,"total_tokens":635}}
  
  event: done
  data: {"type":"done"}
```

### 14.4 WebSocket Handler

```
WS /api/v1/chat/ws?token=<access_token>

Connection:
  1. Verify access_token from query parameter
  2. Extract user_id, session_id from JWT
  3. Accept WebSocket connection
  
Message Flow (Client → Server):
  {
    "type": "chat",
    "conversation_id": "uuid",
    "message": "Explain transformer attention",
    "stream": true
  }

Message Flow (Server → Client):
  Same event types as SSE, but as JSON messages:
  {"type": "content_delta", "delta": "Attention"}
  {"type": "done"}
```

---

## 15. Conversation History

### 15.1 Conversation CRUD

```
Class: ConversationService
Init: service = ConversationService(db_session_factory, memory_manager)

Methods:
  async create(
    user_id: UUID,
    title: str | None = None,
    language: str = "en",
    model: str | None = None,
    system_prompt: str | None = None,
  ) -> Conversation:
      conversation = Conversation(
          user_id=user_id,
          title=title or "New Conversation",
          language=language,
          model=model,
          system_prompt=system_prompt,
          message_count=0,
          token_count=0,
      )
      db.add(conversation)
      await db.commit()
      await db.refresh(conversation)
      return conversation

  async get(conversation_id: UUID, user_id: UUID) -> Conversation | None:
      return await db.query(Conversation).filter(
          Conversation.id == conversation_id,
          Conversation.user_id == user_id,
          Conversation.deleted_at.is_(None),
      ).first()

  async list_by_user(
    user_id: UUID,
    page: int = 1,
    page_size: int = 20,
  ) -> PaginatedResult[Conversation]:
      query = db.query(Conversation).filter(
          Conversation.user_id == user_id,
          Conversation.deleted_at.is_(None),
      ).order_by(Conversation.last_message_at.desc().nullslast())
      return await paginate(query, page, page_size)

  async update_title(conversation_id: UUID, user_id: UUID, title: str) -> Conversation:
      conv = await self.get(conversation_id, user_id)
      if not conv:
          raise NotFoundException("Conversation not found")
      conv.title = title
      await db.commit()
      return conv

  async delete(conversation_id: UUID, user_id: UUID) -> None:
      conv = await self.get(conversation_id, user_id)
      if not conv:
          raise NotFoundException("Conversation not found")
      conv.deleted_at = datetime.utcnow()
      await db.commit()
```

### 15.2 Message Storage

```
On agent completion (response received):

  1. Save user message:
       INSERT INTO messages (
           conversation_id, user_id, role='user',
           content=user_input, sequence_number=next_seq,
           token_count=estimate_tokens(user_input),
           metadata={"model": null, "provider": null, "input_tokens": 0}
       )
       
  2. Save assistant response:
       INSERT INTO messages (
           conversation_id, user_id=NULL, role='assistant',
           content=full_response, sequence_number=next_seq+1,
           token_count=output_tokens,
           metadata={
               "model": model_name,
               "provider": provider_name,
               "input_tokens": input_tokens,
               "output_tokens": output_tokens,
               "total_tokens": total_tokens,
               "finish_reason": finish_reason,
               "tool_calls": tool_calls_used,
           }
       )
       
  3. Update conversation:
       UPDATE conversations SET
           message_count = message_count + 2,
           token_count = token_count + :total_tokens,
           last_message_at = now()
       WHERE id = :conversation_id
       
  4. Invalidate memory cache:
       REDIS DEL conv:{conversation_id}:history
```

---

## 16. User Isolation

### 16.1 Isolation Filters

```
All data access paths enforce user isolation:

  1. Qdrant: Every search includes must filter on user_id
       filter = Filter(must=[FieldCondition(key="user_id", match=MatchValue(value=str(user_id)))])

  2. PostgreSQL: Every query includes user_id WHERE clause
       SELECT ... FROM documents WHERE user_id = :user_id AND deleted_at IS NULL

  3. Object Storage: Key prefix includes user_id
       key = f"users/{user_id}/documents/{document_id}.{ext}"

  4. Conversation history: Filtered by user_id
       SELECT ... FROM conversations WHERE user_id = :user_id AND deleted_at IS NULL

  5. Agent context: user_id injected into trace metadata
       trace_metadata = {"user_id": str(user_id), "conversation_id": str(conversation_id)}
```

### 16.2 Cross-Tenant Security

```
No cross-tenant data access is possible because:

  1. User_id is extracted from JWT (signed, verified)
  2. All queries enforce user_id filter at database level
  3. Qdrant filter is mandatory — payload index on user_id ensures performance
  4. Object storage paths are namespaced by user_id
  5. Presigned URLs expire after 1 hour
```

---

## 17. Prompt Templates

### 17.1 Template Compiler

```
Class: PromptTemplate
Init: template = PromptTemplate(name: str, template_string: str)

Template syntax:
  {{variable_name}}       → simple variable substitution
  {{#if condition}}       → conditional block
    content
  {{/if}}
  {{#each items}}         → iteration
    {{this}}
  {{/each}}
  {{#if items}}           → check non-empty collection
    {{#each items}}
      - {{this}}
    {{/each}}
  {{else}}
    No items found.
  {{/if}}

Methods:
  compile(variables: dict) -> str:
      # Use Jinja2 or custom mustache-like parser
      # Available variables: user_id, user_locale, user_proficiency,
      #                     conversation_title, system_prompt, rag_context,
      #                     tool_descriptions, current_date
      return rendered_string

Template Registry:
  templates = {
      "chat_agent_base": PromptTemplate("chat_agent_base", "..."),
      "rag_agent_base": PromptTemplate("rag_agent_base", "..."),
      "quiz_generator": PromptTemplate("quiz_generator", "..."),
      "query_expander": PromptTemplate("query_expander", "..."),
      "conversation_summarizer": PromptTemplate("conversation_summarizer", "..."),
      "hyde_generator": PromptTemplate("hyde_generator", "..."),
  }
```

### 17.2 Template Inventory

```
Template: chat_agent_base
  You are an AI learning assistant for the Enterprise AI Engineering Platform.
  You help users learn software engineering, AI, cloud, and system design.
  
  Language: {{user_locale}}
  Proficiency Level: {{user_proficiency}}
  Current Date: {{current_date}}
  
  {{#if system_prompt}}
  Additional Instructions:
  {{system_prompt}}
  {{/if}}
  
  {{#if rag_context}}
  Relevant Document Context:
  {{rag_context}}
  {{/if}}
  
  Available Tools:
  {{#if tools}}
  {{#each tools}}
  - {{name}}: {{description}}
  {{/each}}
  {{/if}}
  
  Rules:
  - Answer in the user's language.
  - Use markdown for code blocks.
  - Cite sources when referencing documents.
  - Be concise and ask clarifying questions when needed.

Template: rag_agent_base
  You are a document-aware AI assistant.
  
  ALWAYS use the rag_search tool before answering document-related questions.
  Cite sources using: [Source: Document Title, Page N]
  
  {{#if rag_context}}
  Context from user documents:
  {{rag_context}}
  {{/if}}
  
  Rules:
  - Do NOT fabricate document content.
  - If rag_search returns nothing, state: "I could not find this in your documents."
  - General knowledge questions do not require rag_search.

Template: query_expander
  Generate {{num_expansions}} search queries that capture different aspects of this question.
  Return one per line, no numbering or bullets.
  
  Original: {{original_query}}
  
Template: conversation_summarizer
  Summarize the following conversation in 2-3 sentences.
  Focus on: topics discussed, key facts shared, decisions made, questions asked.
  
  Conversation:
  {{conversation_text}}
  
Template: quiz_generator
  Create a {{num_questions}}-question {{quiz_type}} quiz based on the following content.
  Difficulty: {{difficulty}}
  Language: {{language}}
  
  For each question, provide:
  - The question
  - {{num_options}} multiple choice options
  - The correct answer index
  - A brief explanation
  
  Content:
  {{content}}
```

---

## 18. Tool Calling

### 18.1 Tool Definition Format

```
Each tool is defined as:

ToolDef:
  name: str                     # Unique identifier
  description: str              # LLM-facing description
  parameters: dict              # JSON Schema for arguments
  handler: Callable             # Async function implementing the tool
  requires_confirmation: bool   # If True, user must approve before execution
  timeout_seconds: int          # Max execution time
  cache_ttl: int | None         # Cache TTL in seconds (None = no cache)

Registration:
  rag_search_tool = ToolDef(
      name="rag_search",
      description="Search the user's uploaded documents for information relevant to the query. Use when the user asks about their documents, uploaded content, or specific topics they've been studying.",
      parameters={
          "type": "object",
          "properties": {
              "query": {
                  "type": "string",
                  "description": "The search query. Be specific and detailed for best results."
              },
              "top_k": {
                  "type": "integer",
                  "description": "Number of results to return (1-10)",
                  "default": 5,
              },
          },
          "required": ["query"],
      },
      handler=rag_pipeline.search,
      requires_confirmation=False,
      timeout_seconds=30,
      cache_ttl=300,
  )

  calculator_tool = ToolDef(
      name="calculator",
      description="Evaluate mathematical expressions. Supports +, -, *, /, **, sqrt, sin, cos, log, etc.",
      parameters={
          "type": "object",
          "properties": {
              "expression": {
                  "type": "string",
                  "description": "The mathematical expression to evaluate."
              },
          },
          "required": ["expression"],
      },
      handler=evaluate_math,
      requires_confirmation=False,
      timeout_seconds=5,
      cache_ttl=None,
  )

  web_search_tool = ToolDef(
      name="web_search",
      description="Search the internet for current information. Use when the user asks about recent events, news, or topics not covered in their documents.",
      parameters={
          "type": "object",
          "properties": {
              "query": {
                  "type": "string",
                  "description": "The search query for the web.",
              },
              "num_results": {
                  "type": "integer",
                  "description": "Number of results (1-5)",
                  "default": 3,
              },
          },
          "required": ["query"],
      },
      handler=web_search_client.search,
      requires_confirmation=False,
      timeout_seconds=15,
      cache_ttl=600,
  )
```

### 18.2 Tool Registration to Agent

```
Agent registration process:

  def register_tools(agent: Agent, tools: list[ToolDef], user_tier: str):
      for tool_def in tools:
          # Tier-based filtering
          if tool_def.name == "web_search" and user_tier == "free":
              continue    # Free users don't get web search
              
          # Create OpenAI SDK tool definition
          openai_tool = FunctionTool(
              name=tool_def.name,
              description=tool_def.description,
              parameters=tool_def.parameters,
          )
          
          # Register handler
          agent.add_tool(openai_tool, tool_def.handler)
```

---

## 19. Agent Orchestration

### 19.1 Full Orchestration Flow

```
async def orchestrate_chat(
    user_id: UUID,
    conversation_id: UUID,
    message: str,
    stream: bool,
    preferred_model: str | None,
    ip_address: str,
    user_agent: str,
) -> GatewayResult | StreamingResponse:

    # Phase 1: Gateway validation
    gateway_result = await gateway.process(
        user_id=user_id,
        conversation_id=conversation_id,
        message=message,
        request_type="chat",      # Classified by gateway
        stream=stream,
        preferred_model=preferred_model,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    
    # Phase 2: Model selection
    model = await router.select(
        request_type="chat",
        estimated_tokens=estimate_tokens(message),
        preferred_model=preferred_model,
        user_tier=user_tier,
        capabilities_required=["text", "tool_use", "streaming"] if stream else ["text", "tool_use"],
    )
    
    # Phase 3: Load memory
    history = await memory_manager.load_history(
        conversation_id=conversation_id,
        user_id=user_id,
    )
    
    # Phase 4: RAG check (optional, based on query classification)
    rag_context = None
    if classify_needs_rag(message):
        rag_result = await rag_pipeline.search(
            user_id=user_id,
            query=message,
            conversation_id=conversation_id,
        )
        if rag_result.chunks:
            rag_context = rag_result.context_prompt
    
    # Phase 5: Compile prompt
    instructions = prompt_template.compile({
        "user_locale": user.locale,
        "user_proficiency": user.proficiency,
        "rag_context": rag_context,
        "system_prompt": conversation.system_prompt,
        "tools": tool_descriptions,
        "current_date": today,
    })
    
    # Phase 6: Configure agent
    agent = ChatAgent(
        model=model.name,
        instructions=instructions,
        tools=register_tools(chat_tools, user.tier),
        max_turns=20,
        input_guard=input_guard,
        output_guard=output_guard,
    )
    
    # Phase 7: Execute with fallback
    runner_start = time.monotonic()
    result = await execute_with_fallback(
        agent_config=agent,
        input=message,
        history=history.messages,
        router=router,
        stream=stream,
    )
    runner_duration = time.monotonic() - runner_start
    
    # Phase 8: Persist messages
    new_messages = [
        {"role": "user", "content": message, "metadata": {"input_tokens": estimate_tokens(message)}},
        {"role": "assistant", "content": result.response, "metadata": {
            "model": model.name,
            "provider": model.provider,
            "input_tokens": result.usage.input_tokens,
            "output_tokens": result.usage.output_tokens,
            "finish_reason": result.finish_reason,
        }},
    ]
    await memory_manager.persist_messages(
        conversation_id=conversation_id,
        user_id=user_id,
        new_messages=new_messages,
    )
    
    # Phase 9: Track cost
    cost = await cost_tracker.record(
        user_id=user_id,
        model=model.name,
        provider=model.provider,
        input_tokens=result.usage.input_tokens,
        output_tokens=result.usage.output_tokens,
    )
    
    # Phase 10: Return
    return GatewayResult(
        response=result.response,
        usage=result.usage,
        cost=cost,
        model=model.name,
        provider=model.provider,
        trace_id=trace_id,
        finish_reason=result.finish_reason,
    )
```

---

## 20. Error Handling

### 20.1 Error Hierarchy

```
AIException (base)
  ├── AIValidationException (400)
  │     └── InputTooLargeException
  │     └── ContentPolicyViolationException
  │     └── UnsupportedFileTypeException
  ├── AIAuthException (401)
  │     └── InvalidApiKeyException
  ├── AIRateLimitException (429)
  │     └── UserRateLimitExceededException
  │     └── TokenRateLimitExceededException
  │     └── ProviderRateLimitExceededException
  ├── AIUpstreamException (502)
  │     └── ProviderTimeoutException
  │     └── ProviderServerErrorException
  │     └── ProviderUnavailableException
  ├── AIUnavailableException (503)
  │     └── AllProvidersExhaustedException
  └── AIInternalException (500)
        └── EmbeddingFailedException
        └── ChunkingFailedException
        └── QdrantException
```

### 20.2 Retry Strategy

```
Retry configuration per operation:

  Embedding:
    max_retries: 3
    base_delay: 1.0          # seconds
    max_delay: 10.0
    backoff_factor: 2.0      # exponential
    retryable_errors: [Timeout, ServiceUnavailable, RateLimitError]
    
  LLM Call:
    max_retries: 2           # Plus provider fallback
    base_delay: 2.0
    max_delay: 30.0
    retryable_errors: [RateLimitError, InternalServerError, Timeout, APIConnectionError]
    
  Qdrant Search:
    max_retries: 2
    base_delay: 0.5
    max_delay: 5.0
    retryable_errors: [UnexpectedResponse, ServiceUnavailable]
    
  Document Parsing:
    max_retries: 1
    base_delay: 1.0
    retryable_errors: [Timeout]   # Most parse errors are non-retryable

Implementation (decorator pattern):

  @retry(
      max_retries=3,
      base_delay=1.0,
      backoff_factor=2.0,
      retryable_exceptions=[RateLimitError, Timeout],
      on_retry=log_warning,
  )
  async def embed_documents(texts):
      ...
```

### 20.3 Error Responses

```
400 Input Too Large:
  {
    "status": "error",
    "error": {
      "code": "INPUT_TOO_LARGE",
      "message": "Input exceeds maximum token limit of 128,000 tokens.",
      "details": [{"field": "message", "message": "Estimated 150,000 tokens exceeds limit of 128,000"}]
    }
  }

400 Content Policy:
  {
    "status": "error",
    "error": {
      "code": "CONTENT_POLICY_VIOLATION",
      "message": "Message violates content policy."
    }
  }

429 Rate Limited:
  {
    "status": "error",
    "error": {
      "code": "RATE_LIMIT_EXCEEDED",
      "message": "You have exceeded your rate limit. Please wait before sending another message.",
      "retry_after_seconds": 45
    }
  }

429 Provider Rate Limited:
  {
    "status": "error",
    "error": {
      "code": "PROVIDER_RATE_LIMITED",
      "message": "The AI provider is temporarily rate limited. Retrying with fallback provider.",
      "retry_after_seconds": 30
    }
  }

503 AI Unavailable:
  {
    "status": "error",
    "error": {
      "code": "AI_UNAVAILABLE",
      "message": "AI service is temporarily unavailable. Please try again later."
    }
  }
```

---

## 21. Retry Strategy

### 21.1 Retry Decorator

```
@retry decorator specification:

  Parameters:
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    backoff_factor: float = 2.0
    retryable_exceptions: tuple[Exception] = (Timeout,)
    on_retry: Callable | None = None
    
  Behavior:
    attempt = 0
    while attempt <= max_retries:
        try:
            return await func(*args, **kwargs)
        except retryable_exceptions as e:
            attempt += 1
            if attempt > max_retries:
                raise
            delay = min(base_delay * (backoff_factor ** (attempt - 1)), max_delay)
            jitter = random.uniform(0, delay * 0.1)
            if on_retry:
                on_retry(attempt, delay + jitter, e)
            await asyncio.sleep(delay + jitter)
```

### 21.2 Provider Fallback (not retry — different provider)

```
Provider fallback is NOT a retry. It's a different execution path:

  try:
      return await run_with_provider(primary_model)
  except ProviderError as e:
      logger.warning("Primary provider failed", provider=primary_model.provider, error=str(e))
      for fallback in fallback_chain:
          try:
              return await run_with_provider(fallback)
          except ProviderError as e2:
              logger.warning("Fallback provider failed", provider=fallback.provider, error=str(e2))
              continue
      raise AIUnavailableException("All providers exhausted")
```

---

## 22. Monitoring

### 22.1 Metrics

```
Prometheus metric definitions:

  Metrics:
    ai_requests_total:
      type: Counter
      labels: [provider, model, status, user_tier]
      description: "Total AI requests by provider, model, status, and user tier"
      
    ai_request_duration_seconds:
      type: Histogram
      labels: [provider, model]
      buckets: [0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
      description: "AI request latency in seconds"
      
    ai_tokens_input_total:
      type: Counter
      labels: [provider, model]
      description: "Total input tokens consumed"
      
    ai_tokens_output_total:
      type: Counter
      labels: [provider, model]
      description: "Total output tokens generated"
      
    ai_cost_total_usd:
      type: Counter
      labels: [provider, model, user_tier]
      description: "Total cost in USD"
      
    ai_rate_limit_hits_total:
      type: Counter
      labels: [user_tier, endpoint]
      description: "Total rate limit hits"
      
    ai_tool_calls_total:
      type: Counter
      labels: [tool_name, status]
      description: "Total tool calls by tool and status"
      
    ai_rag_search_duration_seconds:
      type: Histogram
      labels: [search_type]   # semantic, keyword, rerank
      buckets: [0.05, 0.1, 0.2, 0.5, 1.0, 2.0]
      description: "RAG search latency by type"
      
    ai_rerank_duration_seconds:
      type: Histogram
      buckets: [0.05, 0.1, 0.2, 0.5, 1.0]
      description: "Cohere reranker latency"
      
    ai_context_window_ratio:
      type: Gauge
      description: "Ratio of used context to max context (0.0 - 1.0)"
      
    ai_conversation_messages:
      type: Histogram
      buckets: [1, 5, 10, 20, 50, 100]
      description: "Message count per conversation"
      
    ai_embedding_duration_seconds:
      type: Histogram
      labels: [model]
      buckets: [0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
      description: "Embedding generation latency"
      
    ai_document_processing_duration_seconds:
      type: Histogram
      labels: [file_type]
      buckets: [1.0, 5.0, 10.0, 30.0, 60.0, 120.0]
      description: "Full document processing pipeline latency"
```

### 22.2 Tracing

```
OpenTelemetry spans (ai.* namespace):

  Span: ai.request
    Attributes: user_id, conversation_id, model, provider, stream, trace_id
    
  Span: ai.gateway.validate
    Parent: ai.request
    Attributes: input_tokens, content_policy_result
    Events: validation_passed, validation_failed
    
  Span: ai.router.select
    Parent: ai.request
    Attributes: request_type, estimated_tokens, user_tier, selected_model, selected_provider
    
  Span: ai.memory.load
    Parent: ai.request
    Attributes: conversation_id, message_count, total_tokens, strategy, cache_hit
    
  Span: ai.rag.search
    Parent: ai.request
    Attributes: query, variants, semantic_latency, keyword_latency, rerank_latency, chunks_found
    
  Span: ai.agent.run
    Parent: ai.request
    Attributes: agent_type, max_turns, tool_calls, finish_reason, latency
    
  Span: ai.llm.call
    Parent: ai.agent.run
    Attributes: model, provider, input_tokens, output_tokens, latency, status
    
  Span: ai.memory.persist
    Parent: ai.request
    Attributes: conversation_id, messages_count, tokens_added
    
  Span: ai.cost.track
    Parent: ai.request
    Attributes: model, provider, input_tokens, output_tokens, cost_usd
```

### 22.3 Structured Logging

```
Log format (JSON, sent to stdout):

  {
    "timestamp": "2026-07-30T10:00:00.123Z",
    "level": "INFO",
    "service": "ai-gateway",
    "trace_id": "0194f2a0-abc-def-ghi",
    "span_id": "789ghi",
    "event": "ai.request",
    "attributes": {
      "user_id": "0194f2a0-...",
      "conversation_id": "0194f2b0-...",
      "model": "gpt-4o",
      "provider": "openai",
      "input_tokens": 452,
      "output_tokens": 183,
      "duration_ms": 2340,
      "stream": true,
      "finish_reason": "stop",
      "cost_usd": 0.00235,
      "status": "success"
    }
  }
```

---

## 23. Cost Tracking

### 23.1 Cost Tracker

```
Class: CostTracker
Init: tracker = CostTracker(db_session_factory, redis_client, config: CostConfig)

CostConfig:
  enabled: bool = True
  daily_budget_per_user: dict = {
      "free": 0.50,
      "basic": 5.00,
      "premium": 50.00,
      "enterprise": 1000.00,
  }
  cost_per_token: dict = {
      "openai:gpt-4o": {"input": 0.0000025, "output": 0.00001},
      "openai:gpt-4o-mini": {"input": 0.00000015, "output": 0.0000006},
      "google:gemini-2.5-pro": {"input": 0.00000125, "output": 0.000005},
      "xai:grok-3": {"input": 0.000003, "output": 0.000015},
      "openrouter:gpt-4o-mini": {"input": 0.00000015, "output": 0.0000006},
  }

Methods:
  async calculate(
    model: str,
    provider: str,
    input_tokens: int,
    output_tokens: int,
  ) -> Decimal:
      key = f"{provider}:{model}"
      rates = config.cost_per_token.get(key)
      if not rates:
          return Decimal("0")
      cost = (input_tokens * rates["input"] + output_tokens * rates["output"])
      return Decimal(str(cost)).quantize(Decimal("0.00001"))

  async record(
    user_id: UUID,
    model: str,
    provider: str,
    input_tokens: int,
    output_tokens: int,
  ) -> Decimal:
      cost = await self.calculate(model, provider, input_tokens, output_tokens)
      
      # Update daily counter in Redis
      daily_key = f"cost:daily:{user_id}:{datetime.utcnow().strftime('%Y-%m-%d')}"
      await redis.incrbyfloat(daily_key, float(cost))
      await redis.expire(daily_key, 86400 * 2)
      
      # Historical record in PostgreSQL
      cost_record = CostRecord(
          user_id=user_id,
          model=model,
          provider=provider,
          input_tokens=input_tokens,
          output_tokens=output_tokens,
          cost_usd=cost,
      )
      db.add(cost_record)
      await db.commit()
      
      return cost

  async check_budget(
    user_id: UUID,
    user_tier: str,
  ) -> BudgetStatus:
      daily_limit = config.daily_budget_per_user.get(user_tier, 0)
      if daily_limit == 0:
          return BudgetStatus(unlimited=True)
          
      daily_key = f"cost:daily:{user_id}:{datetime.utcnow().strftime('%Y-%m-%d')}"
      current = float(await redis.get(daily_key) or 0)
      
      return BudgetStatus(
          unlimited=False,
          daily_limit=daily_limit,
          current_spend=current,
          remaining=daily_limit - current,
          exhausted=current >= daily_limit,
      )
```

### 23.2 Budget Enforcement

```
In AI Gateway, before processing:

  budget = await cost_tracker.check_budget(user_id, user_tier)
  if budget.exhausted:
      raise RateLimitExceededException(
          message="Daily AI usage budget exceeded. Upgrade your plan or wait until tomorrow.",
          retry_after_seconds=seconds_until_midnight(),
      )
```

---

## 24. Caching

### 24.1 Cache Layers

```
Layer 1: In-Memory (function-scoped LRU)
  Cache: lru_cache on pure functions
  TTL: None (function-scoped)
  Used for: token estimation, JSON schema validation
  
Layer 2: Redis (shared)
  Cache: ai_enterprises: prefix
  TTL: Varies by data type
  
Layer 3: PostgreSQL (source of truth)
  Cache: No caching — authoritative storage
  Used for: conversation history, document metadata
```

### 24.2 Redis Cache Keys

```
Cache Key Patterns:

  Embedding Cache:
    Key:   embed:{sha256(text)}
    Value: list[float] (serialized)
    TTL:   86400 (24h)
    Usage: Skip re-embedding identical text
    
  Rerank Cache:
    Key:   rerank:{sha256(query)}:{sha256(joined_chunk_ids)}
    Value: list[RerankedChunk] (serialized)
    TTL:   300 (5 min)
    Usage: Avoid re-reranking identical queries
    
  Conversation History:
    Key:   conv:{conversation_id}:history
    Value: ConversationHistory (JSON)
    TTL:   300 (5 min)
    Usage: Fast load of recent conversation context
    
  Search Results (temporary):
    Key:   search:{sha256(query)}:{user_id}:{filters_hash}
    Value: RAGResult (serialized)
    TTL:   60 (1 min)
    Usage: Avoid duplicate searches within same interaction
    
  Model Availability:
    Key:   model:availability:{model_name}
    Value: {available: bool, latency_p50: int}
    TTL:   30 (30 sec)
    Usage: Quick check before routing
    
  Provider Rate Limit Status:
    Key:   provider:ratelimit:{provider_name}
    Value: {remaining: int, reset_at: timestamp}
    TTL:   Until reset
    Usage: Prefer providers with available capacity
```

### 24.3 Cache Invalidation

```
Invalidation Events:

  Document Upload:
    - Clear search results cache for user
    - Clear embedding cache for text (on re-embed)
    
  Document Delete:
    - Clear all caches for user
    - Delete Qdrant points for document
    
  New Message:
    - Clear conv:{id}:history
    - Clear search results for conversation
    
  User Role Change:
    - (No AI cache impact — role changes affect auth, not AI)
```

---

## 25. Testing

### 25.1 Test Configuration

```
Framework: pytest + pytest-asyncio
HTTP: httpx.AsyncClient (ASGI transport)
Database: test PostgreSQL (testcontainers)
Vector: test Qdrant (testcontainers or in-memory)
Redis: fakeredis (in-memory)
LLM: All calls mocked with respx or pytest-httpx
Embeddings: All calls mocked (return fixed-size random vectors)
Cohere: All calls mocked (return deterministic scores)
Object Store: In-memory mock
```

### 25.2 Test Fixtures (conftest.py)

```
Module-scoped:
  db_engine: Creates test PostgreSQL, runs Alembic migrations
  qdrant_client: Creates test Qdrant collection
  redis_client: fakeredis instance
  
Function-scoped:
  db_session: Fresh session, rollback after test
  test_client: FastAPI test client
  auth_headers: Valid JWT + cookie for authenticated requests
  
  mock_llm_router: Returns fixed model selection, no real API call
  mock_embedder: Returns fixed-size random vectors
  mock_reranker: Returns deterministic scores
  mock_web_search: Returns canned results
  mock_email_sender: Captures email to in-memory list
```

### 25.3 Test Files and Functions

```
test_gateway.py (8 tests):
  ✓ test_gateway_validates_input_length — rejects >128k tokens
  ✓ test_gateway_validates_content_policy — rejects policy-violating content
  ✓ test_gateway_enforces_rate_limit — returns 429 after threshold
  ✓ test_gateway_injects_user_context — user_id present in trace metadata
  ✓ test_gateway_records_cost — cost_tracker.record called after process
  ✓ test_gateway_streaming_mode — returns StreamingResponse when stream=True
  ✓ test_gateway_non_streaming_mode — returns full response when stream=False
  ✓ test_gateway_fallback_on_provider_error — falls back to next provider

test_router.py (6 tests):
  ✓ test_router_selects_preferred_model — returns user-preferred model if tier allows
  ✓ test_router_selects_long_context_model — >100k tokens → gemini-2.5-pro
  ✓ test_router_selects_vision_model — vision request → gpt-4o or gemini
  ✓ test_router_enforces_tier_limits — free tier only gets gpt-4o-mini
  ✓ test_router_fallback_chain — failed primary → fallback → fallback → 503
  ✓ test_router_fallback_exhaustion — all providers failed → AIUnavailableException

test_chat_agent.py (6 tests):
  ✓ test_chat_agent_compiles_instructions — system prompt includes language, proficiency, tools
  ✓ test_chat_agent_registers_tools — all tier-appropriate tools registered
  ✓ test_chat_agent_rag_context_injection — context appears in instructions when RAG run
  ✓ test_chat_agent_max_turns — agent stops after max_turns tool calls
  ✓ test_chat_agent_guardrails_input — input guard rejects injection attempts
  ✓ test_chat_agent_guardrails_output — output guard redacts PII

test_rag_agent.py (4 tests):
  ✓ test_rag_agent_searches_on_document_query — rag_search called for document-related query
  ✓ test_rag_agent_cites_sources — response includes [Source: ...] citations
  ✓ test_rag_agent_no_fabrication — returns "not found" when rag_search empty
  ✓ test_rag_agent_general_knowledge — answers without search for non-document query

test_rag_pipeline.py (8 tests):
  ✓ test_rag_pipeline_full_flow — query rewrite → semantic → keyword → RRF → rerank → context
  ✓ test_rag_pipeline_semantic_search — returns results from Qdrant
  ✓ test_rag_pipeline_keyword_search — returns results from PostgreSQL tsvector
  ✓ test_rag_pipeline_rrf_fusion — combines and ranks results from both sources
  ✓ test_rag_pipeline_reranker — Cohere reranker returns re-scored top 5
  ✓ test_rag_pipeline_context_assembly — formats chunks with source attribution, respects token budget
  ✓ test_rag_pipeline_empty_results — returns empty context when no results found
  ✓ test_rag_pipeline_user_isolation — Qdrant filter includes user_id

test_embedding_pipeline.py (6 tests):
  ✓ test_embed_document_full_flow — pdf → extract → chunk → embed → qdrant upsert → pg store
  ✓ test_embedding_pipeline_chunking_recursive — splits text at paragraph, sentence, word boundaries
  ✓ test_embedding_pipeline_chunking_heading — splits at heading boundaries
  ✓ test_embedding_pipeline_cache_hit — cached text skipped, Qdrant receives only uncached
  ✓ test_embedding_pipeline_qdrant_payload — Qdrant points contain correct metadata fields
  ✓ test_embedding_pipeline_document_status — document.status updated to "ready" after completion

test_hybrid_search.py (4 tests):
  ✓ test_hybrid_search_rrf_scoring — documents appearing in both results rank higher
  ✓ test_hybrid_search_deduplication — duplicate chunk_ids removed before RRF
  ✓ test_hybrid_search_empty_query — returns empty results for empty query
  ✓ test_hybrid_search_filters_applied — document_id filter correctly limits results

test_reranker.py (3 tests):
  ✓ test_reranker_returns_top_n — exactly top_n results returned
  ✓ test_reranker_scores_decreasing — results sorted by relevance_score descending
  ✓ test_reranker_caching — identical call returns cached result

test_memory.py (4 tests):
  ✓ test_memory_loads_conversation_history — returns messages in correct order
  ✓ test_memory_sliding_window — returns last N messages
  ✓ test_memory_token_aware_window — respects token budget
  ✓ test_memory_persists_new_messages — user + assistant messages saved with correct sequence

test_streaming.py (3 tests):
  ✓ test_sse_event_format — each event follows "event:{type}\ndata:{json}\n\n" format
  ✓ test_sse_message_done — stream ends with message_done + done events
  ✓ test_sse_tool_call_events — tool_call_start and tool_call_end events emitted during tool use

test_rate_limit.py (4 tests):
  ✓ test_ip_rate_limit — 100 req/min per IP
  ✓ test_user_rate_limit — 500 req/min per authenticated user
  ✓ test_auth_endpoint_rate_limit — 20 req/min on auth endpoints
  ✓ test_rate_limit_headers — RateLimit-* and Retry-After headers present

test_security.py (4 tests):
  ✓ test_prompt_injection_detection — known injection patterns blocked
  ✓ test_pii_redaction_in_response — emails, phone numbers redacted from agent output
  ✓ test_user_isolation_cross_tenant — user A cannot search user B's documents
  ✓ test_presigned_url_expiration — expired URL returns 403
```

### 25.4 Integration Tests

```
test_full_chat_flow.py (3 tests):
  ✓ Complete chat: create conversation → send message → receive response → verify DB has user + assistant messages
  ✓ Chat with RAG: create conversation → upload document → wait for indexing → send document question → verify citation in response
  ✓ Chat streaming: create conversation → send message with stream=true → collect SSE events → verify message_done received

test_full_rag_flow.py (2 tests):
  ✓ Upload PDF → wait for embedding pipeline → search for content → verify chunks returned
  ✓ Upload DOCX → search before indexing complete → verify "not indexed" status response

test_cost_tracking.py (2 tests):
  ✓ Budget enforcement: free user with daily budget exceeded → request blocked
  ✓ Cost accumulation: multiple requests → daily total correctly incremented
```

---

## 26. API Contracts

### 26.1 Chat Endpoints

```
POST /api/v1/chat
  Description: Send a message to the AI assistant. Creates conversation if conversation_id is null.
  
  Headers:
    Authorization: Bearer <access_token>
    Content-Type: application/json
    Accept: text/event-stream | application/json
  
  Request Body:
    {
      "conversation_id": "UUID | null",        # null = create new conversation
      "message": "Explain transformer attention",
      "stream": true,                           # true = SSE, false = JSON response
      "preferred_model": "gpt-4o | null",       # optional model override
      "attachments": [                          # optional file references
        {"type": "document", "id": "UUID"}
      ]
    }
  
  Response (stream=false):
    200:
      {
        "status": "success",
        "data": {
          "conversation_id": "0194f2a0-...",
          "response": "Attention mechanisms allow transformers to...",
          "usage": {
            "input_tokens": 452,
            "output_tokens": 183,
            "total_tokens": 635
          },
          "model": "gpt-4o",
          "provider": "openai",
          "finish_reason": "stop",
          "tool_calls": [
            {"tool": "rag_search", "status": "success", "duration_ms": 234}
          ],
          "trace_id": "abc123def456"
        }
      }
  
  Response (stream=true):
    200:
      Content-Type: text/event-stream
      Transfer-Encoding: chunked
      (see 14.3 for event format)
  
  Errors:
    400: INPUT_TOO_LARGE, CONTENT_POLICY_VIOLATION
    401: INVALID_TOKEN
    429: RATE_LIMIT_EXCEEDED
    503: AI_UNAVAILABLE

GET /api/v1/chat/{conversation_id}
  Description: Get conversation history.
  
  Headers:
    Authorization: Bearer <access_token>
  
  Response:
    200:
      {
        "status": "success",
        "data": {
          "id": "0194f2a0-...",
          "title": "Learning Transformers",
          "language": "en",
          "model": "gpt-4o",
          "message_count": 12,
          "token_count": 4520,
          "created_at": "2026-07-30T10:00:00Z",
          "last_message_at": "2026-07-30T10:15:00Z"
        }
      }

GET /api/v1/chat/{conversation_id}/messages
  Query: page, page_size, before (message_id for cursor pagination)
  
  Headers:
    Authorization: Bearer <access_token>
  
  Response:
    200:
      {
        "status": "success",
        "data": {
          "items": [
            {
              "id": "0194f2a0-...",
              "role": "user",
              "content": "Explain transformer attention",
              "token_count": 12,
              "created_at": "2026-07-30T10:00:00Z",
              "metadata": {}
            },
            {
              "id": "0194f2a1-...",
              "role": "assistant",
              "content": "Attention mechanisms allow...",
              "token_count": 183,
              "created_at": "2026-07-30T10:00:05Z",
              "metadata": {
                "model": "gpt-4o",
                "input_tokens": 452,
                "output_tokens": 183,
                "finish_reason": "stop"
              }
            }
          ],
          "total": 12,
          "page": 1,
          "page_size": 20,
          "pages": 1
        }
      }

GET /api/v1/chat
  Query: page, page_size
  
  Headers:
    Authorization: Bearer <access_token>
  
  Response:
    200:
      {
        "status": "success",
        "data": {
          "items": [
            {
              "id": "0194f2a0-...",
              "title": "Learning Transformers",
              "message_count": 12,
              "last_message_at": "2026-07-30T10:15:00Z"
            }
          ],
          "total": 25,
          "page": 1,
          "page_size": 20,
          "pages": 2
        }
      }

PATCH /api/v1/chat/{conversation_id}
  Description: Update conversation title.
  
  Request Body:
    { "title": "New Title" }
  
  Response: 200 with updated conversation

DELETE /api/v1/chat/{conversation_id}
  Response: 204 No Content
```

### 26.2 Document Endpoints

```
POST /api/v1/documents
  Description: Upload a document for AI indexing.
  
  Headers:
    Authorization: Bearer <access_token>
    Content-Type: multipart/form-data
  
  Body:
    file: File (required)
    conversation_id: UUID (optional)
  
  Response:
    202:
      {
        "status": "success",
        "data": {
          "document_id": "0194f2a0-...",
          "file_name": "transformer-paper.pdf",
          "file_type": "pdf",
          "file_size": 2456000,
          "status": "processing",
          "created_at": "2026-07-30T10:00:00Z"
        }
      }
  
  Errors:
    400: INVALID_FILE_TYPE, FILE_TOO_LARGE
    409: DUPLICATE_FILE

GET /api/v1/documents
  Query: page, page_size, file_type (optional filter), status (optional filter)
  
  Headers:
    Authorization: Bearer <access_token>
  
  Response:
    200:
      {
        "status": "success",
        "data": {
          "items": [
            {
              "id": "0194f2a0-...",
              "file_name": "transformer-paper.pdf",
              "file_type": "pdf",
              "file_size": 2456000,
              "chunk_count": 24,
              "status": "ready",
              "created_at": "2026-07-30T10:00:00Z",
              "indexed_at": "2026-07-30T10:01:30Z"
            }
          ],
          "total": 5,
          "page": 1,
          "page_size": 20,
          "pages": 1
        }
      }

GET /api/v1/documents/{document_id}
  Response: 200 with single document detail (includes file_name, file_type, file_size, chunk_count, status, created_at, indexed_at)

DELETE /api/v1/documents/{document_id}
  Description: Soft-delete document and remove from vector store.
  Response: 204 No Content
  Side effects:
    - Qdrant: Delete all points where document_id matches
    - PostgreSQL: Set deleted_at on document + document_chunks
    - Clear all related caches for this user
```

### 26.3 WebSocket Endpoint

```
WS /api/v1/chat/ws?token=<access_token>
  
  Connection:
    1. Server validates JWT from query parameter
    2. Server accepts WebSocket
  
  Client → Server Messages:
    {
      "type": "chat",
      "conversation_id": "UUID | null",
      "message": "Explain transformer attention",
      "preferred_model": "gpt-4o | null",
      "attachments": []
    }
    
    {
      "type": "cancel",         # Cancel in-progress streaming
      "conversation_id": "UUID"
    }
    
    {
      "type": "ping"            # Keepalive
    }
  
  Server → Client Messages:
    {"type": "message_start", "conversation_id": "UUID", "trace_id": "str"}
    {"type": "content_delta", "delta": "Attention"}
    {"type": "tool_call_start", "tool": "rag_search", "tool_call_id": "call_123", "arguments": {"query": "..."}}
    {"type": "tool_call_end", "tool": "rag_search", "tool_call_id": "call_123", "result": {"chunks_found": 3}}
    {"type": "message_done", "finish_reason": "stop", "usage": {"input_tokens": 452, "output_tokens": 183}}
    {"type": "error", "code": "RATE_LIMITED", "message": "..."}
    {"type": "pong"}
    {"type": "done"}
  
  Close:
    - Client closes connection
    - Server closes on idle > 5 minutes
    - Server closes on authentication failure
```