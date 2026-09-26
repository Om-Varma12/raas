# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
A Multi-Tenant Agentic RAG Platform providing a "RAG-as-a-widget" service. The platform emphasizes provable multi-tenant isolation, content-type-aware ingestion (tables, prose, code, conversations), and cost/latency optimization through multi-layer caching (prompt, semantic, and embedding).

## Documentation Map
- `docs/PRD.md`: Product requirements and high-level feature set.
- `docs/SCHEMA.md`: Qdrant collection schema and payload definitions.
- `docs/TECHNICALS.md`: Specific technical decisions (e.g., Jina embedding model, task types).

## High-Level Architecture
The system is split into three main components:
1. **Backend (Python/FastAPI)**: 
   - **Ingestion Pipeline**: Parsers $\rightarrow$ Content-type Detection $\rightarrow$ Chunkers $\rightarrow$ Embedder $\rightarrow$ Vector Store.
   - **Agentic Retrieval**: A LangGraph-based state machine (Router $\rightarrow$ Decomposer $\rightarrow$ Retrieval $\rightarrow$ Verifier).
   - **Storage**: Postgres/pgvector for tenant metadata and vector storage.
   - **Caching**: Three layers: Prompt caching (static-first ordering), Semantic cache (query similarity), and Embedding cache (content-hash).
2. **Embed Widget (TypeScript)**: A minimal JS bundle injected into host sites for chat interaction.
3. **Admin Dashboard (React/TS)**: For tenant onboarding and configuration.

## Development Commands
### Backend
- **Install Dependencies**: `pip install -r backend/requirements.txt`
- **Run Backend**: `cd backend && uvicorn main:app --reload`
- **Run Ingestion**: `python backend/fetchers/fetch_devdocs.py` (for dev docs)

### Infrastructure
- **Local Environment**: `docker-compose up -d` (starts Postgres, Redis, etc.)

## Key Engineering Constraints
- **Tenant Isolation**: Every retrieval query MUST be filtered by `tenant_id` before ranking.
- **Embedding Task Types**: Must explicitly distinguish between `retrieval.passage` (for ingestion) and `retrieval.query` (for user questions) to avoid recall degradation.
- **Prompt Ordering**: Static content first, dynamic content last to optimize prompt caching.
