# Multi-Tenant Agentic RAG Platform

Embeddable, multi-tenant RAG-as-a-widget — one script a company drops into their site, backed by a shared agentic RAG service with per-tenant data isolation, content-type-aware ingestion, and cost/latency-optimized retrieval.

## Why this exists

Not "RAG for any company" as a pitch — it's a platform that proves three specific engineering claims:
1. **Multi-tenant isolation** — one shared backend, provably no cross-tenant data leakage, enforced and load-tested, not just assumed.
2. **Content-type-aware retrieval** — a single ingestion pipeline that adapts chunking to what it's actually parsing (tables vs. prose vs. code vs. conversation), rather than one strategy applied everywhere.
3. **Cost/latency optimization** — prompt caching, semantic caching, and embedding caching, instrumented and benchmarked, not just implemented.

## Target tenants (v1)

| Tenant | Corpus | Primary content types | Latency target |
|---|---|---|---|
| Finance | SEC 10-K/10-Q filings | Table, Prose | Relaxed (3-4s) |
| Dev docs | GitHub issues + repo docs | Code, Conversation, Prose | Moderate (~2s) |
| Support | Support ticket dataset | Conversation (short) | Strict (<1s) |

## Stack

- **Backend**: Python, FastAPI, LangGraph (agent orchestration), Postgres + pgvector (vector store + metadata), Redis (caching + queues), Celery/RQ (async ingestion)
- **Embed widget**: TypeScript, minimal bundle (no heavy framework), injected script + scoped-token auth
- **Admin dashboard**: React + TypeScript — tenant onboarding, config, usage/cost visibility
- **Eval**: golden Q&A sets per tenant, regression run in CI (ported from an earlier RAG eval harness)
- **Load testing**: Locust

## Tenant isolation model

Shared Postgres/pgvector instance, every chunk tagged with `tenant_id` at write time, all retrieval queries filtered by `tenant_id` before ranking. Isolation is proven, not assumed: a dedicated leak-test suite runs adversarial cross-tenant queries in CI and asserts zero leakage.

## Caching strategy (three distinct layers — don't conflate them)

- **Prompt caching**: caches the static prefix of LLM calls (system prompts, tool schemas, per-tenant static config) — cuts input token cost and time-to-first-token. Requires static content first, dynamic content (retrieved chunks, user query) last in every prompt template.
- **Semantic cache**: skips retrieval + generation entirely on near-duplicate queries.
- **Embedding cache**: skips re-embedding identical chunks during ingestion.

## Folder structure

```
rag-platform/
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   │   ├── auth.py             # Issues short-lived, tenant-scoped tokens for widget sessions
│   │   │   ├── ingest.py           # Endpoints to trigger/monitor document ingestion per tenant
│   │   │   ├── query.py            # Main chat/query endpoint, invokes the LangGraph agent graph
│   │   │   └── admin.py            # Tenant CRUD, config, usage stats for the admin dashboard
│   │   ├── agents/
│   │   │   ├── router_agent.py     # Classifies query: single-hop / multi-hop / needs-structured-data
│   │   │   ├── decomposer_agent.py # Breaks multi-hop queries into sub-queries
│   │   │   ├── retrieval_agent.py  # Executes tenant-scoped hybrid retrieval for a (sub-)query
│   │   │   ├── verifier_agent.py   # Checks the draft answer is grounded in retrieved chunks
│   │   │   └── graph.py            # Wires all agents into the LangGraph state machine
│   │   ├── retrieval/
│   │   │   ├── hybrid_search.py    # Combines dense (vector) + sparse (BM25) retrieval
│   │   │   ├── reranker.py         # Cross-encoder reranking of retrieved candidates
│   │   │   └── vector_store.py     # pgvector query/insert wrapper, tenant_id-filtered
│   │   ├── ingestion/
│   │   │   ├── parsers/
│   │   │   │   ├── pdf.py          # Parses SEC filings; separates table elements from prose
│   │   │   │   ├── github.py       # Pulls + parses GitHub issues and markdown docs
│   │   │   │   └── tickets.py      # Parses support ticket dataset into Q&A pairs
│   │   │   ├── content_type.py     # Detects content type (table/prose/code/conversation) per element
│   │   │   ├── chunkers/
│   │   │   │   ├── table_chunker.py        # Row-atomic chunking, no mid-row splits
│   │   │   │   ├── prose_chunker.py        # Structural/section-boundary chunking with overlap
│   │   │   │   ├── code_chunker.py         # Function/class-atomic chunking (tree-sitter)
│   │   │   │   └── conversation_chunker.py # Ticket/issue-thread-atomic chunking
│   │   │   ├── chunker_registry.py # Routes each parsed element to the right chunker by content type
│   │   │   ├── embedder.py         # Batched embedding generation, checks embedding cache first
│   │   │   └── pipeline.py         # Orchestrates parse → detect → chunk → embed → store
│   │   ├── caching/
│   │   │   ├── semantic_cache.py   # Query-embedding similarity cache, skips retrieval+generation
│   │   │   ├── embedding_cache.py  # Content-hash cache, skips re-embedding identical chunks
│   │   │   └── prompt_cache.py     # Builds prompts with static-first ordering, sets cache_control breakpoints
│   │   ├── core/
│   │   │   ├── config.py           # App settings, environment config
│   │   │   ├── security.py         # Verifies tenant-scoped tokens on incoming requests
│   │   │   ├── tenancy.py          # Tenant context object, isolation helper functions
│   │   │   └── logging.py          # Structured logging, cache-hit/cost/latency instrumentation
│   │   ├── db/
│   │   │   ├── models.py           # SQLAlchemy models: tenants, documents, chunks, acl
│   │   │   ├── session.py          # DB session/connection management
│   │   │   └── migrations/         # Alembic migration scripts
│   │   ├── workers/
│   │   │   └── ingestion_worker.py # Celery/RQ task definitions for async ingestion
│   │   ├── eval/
│   │   │   ├── golden_sets/
│   │   │   │   ├── finance.jsonl       # Golden Q&A pairs for the finance tenant
│   │   │   │   ├── devdocs.jsonl       # Golden Q&A pairs for the dev docs tenant
│   │   │   │   └── support.jsonl       # Golden Q&A pairs for the support tenant
│   │   │   ├── metrics.py          # recall@k, groundedness, latency, cost-per-query calculations
│   │   │   └── run_eval.py         # Runs golden sets against the pipeline, outputs a report
│   │   └── main.py                 # FastAPI app entrypoint
│   ├── tests/
│   │   ├── test_isolation.py       # Adversarial cross-tenant leak tests
│   │   └── ...                     # Unit tests mirroring app/ structure
│   ├── pyproject.toml
│   └── Dockerfile
│
├── embed-widget/
│   ├── src/
│   │   ├── widget.ts               # Entry point injected into the host page
│   │   ├── auth.ts                 # Exchanges a public tenant key for a scoped session token
│   │   ├── api-client.ts           # Wraps calls to the backend query/ingest endpoints
│   │   └── ui/                     # Minimal chat bubble UI, no heavy framework
│   └── vite.config.ts              # Bundles widget to a single small JS file
│
├── admin-dashboard/
│   └── src/                        # Tenant onboarding, config, usage/cost dashboard (React/TS)
│
├── infra/
│   ├── docker-compose.yml          # Local dev: backend, Postgres, Redis
│   └── locustfile.py               # Load test: concurrent multi-tenant query traffic
│
└── README.md                       # This file
```

## Data sources

- **Finance**: SEC EDGAR full-text search / bulk data API — public 10-K/10-Q filings, no auth required.
- **Dev docs**: GitHub REST API — issues + markdown docs from a chosen public repo.
- **Support**: Public support-ticket dataset (e.g. Bitext customer-support dataset on Hugging Face).

## Build order

1. Ingestion pipeline (parsers + content-type detection + chunkers) for all 3 tenants
2. Hybrid retrieval + reranking, tenant-scoped
3. LangGraph agent graph (router → decomposer → retrieval → verifier)
4. Eval harness wired in from the start
5. Caching layers (prompt, semantic, embedding)
6. Isolation leak-test suite
7. Embed widget + admin dashboard
8. Load test, publish numbers
