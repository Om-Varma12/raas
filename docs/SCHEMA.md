# RAG Platform — Collection Schema

Scope: `finance` and `devdocs` tenants only. `support` intentionally excluded for now.

---

## Collections

One Qdrant collection per `tenant_id` (UUID). Content type (`finance` / `devdocs`) is **tenant config metadata in Postgres**, not part of the collection name or key — the collection schema below is identical in structure for both; only the *values* differ.

```
collection_name: tenant_{tenant_id}
```

### Vector config (per collection)

| Vector name | Type | Dims | Distance | Notes |
|---|---|---|---|---|
| `dense` | float32 | 1024 (Jina, confirm truncation setting) | Cosine | Normalize on write |
| `sparse` | sparse (BM25-style) | — | Dot | Qdrant native sparse vector, for hybrid fusion query |

### HNSW config (per collection, tunable per tenant SLA)

| Param | `finance` | `devdocs` |
|---|---|---|
| `ef_construct` | 200 | 150 |
| `ef_search` | 128 | 96 |
| Rationale | Favor recall — long filings, tolerant of slower query | Balance — code/docs need decent recall but faster iteration expected |

---

## Payload schema (shared structure, both tenants)

| Field | Type | Indexed | Applies to |
|---|---|---|---|
| `tenant_id` | keyword (UUID) | ✅ | both — redundant with collection scoping, kept for cross-collection leak-test assertions |
| `doc_id` | keyword (UUID) | ✅ | both |
| `chunk_id` | keyword (UUID) | — (point ID) | both |
| `content_hash` | keyword (sha256) | ✅ | both — skip re-embed on unchanged re-ingest |
| `source_type` | keyword | ✅ | both — enum differs per tenant, see below |
| `heading_path` | string | — | both — e.g. "Item 7 > Revenue" / "Auth > OAuth Setup" |
| `token_count` | int | — | both |
| `embedding_model_version` | keyword | — | both — track for future re-embed migrations |
| `embedding_task_type` | keyword (`retrieval.passage`) | — | both — sanity-check field, all ingested chunks should match |
| `created_at` | timestamp (ISO 8601) | — | both |

### `source_type` enum values

**`finance` tenant:**
- `filing_section` — prose chunk from a 10-K/10-Q section
- `filing_table` — extracted/flattened table content

**`devdocs` tenant:**
- `md_section` — prose chunk from markdown docs
- `code_block` — fenced code block (atomic, never split)
- `issue_thread` — GitHub issue title + body + accepted comment, as one unit

---

## Tenant-specific metadata fields

### `finance` — additional payload fields

| Field | Type | Indexed | Notes |
|---|---|---|---|
| `fiscal_period` | keyword (e.g. `"FY2023-Q4"`) | ✅ | Time-scoped filtering, pre- or post-retrieval |
| `filing_date` | timestamp | ✅ | Sort/filter by recency |
| `filing_type` | keyword (`10-K` / `10-Q`) | — | |
| `item_number` | keyword (e.g. `"Item 7"`, `"Item 1A"`) | ✅ | Section-level filtering |
| `company_ticker` | keyword | ✅ | If corpus spans multiple filers |
| `table_metadata` | object, nullable | — | Only on `filing_table` chunks — flattened row/col labels for display |

### `devdocs` — additional payload fields

| Field | Type | Indexed | Notes |
|---|---|---|---|
| `repo_name` | keyword | ✅ | Source repo, if corpus spans multiple |
| `doc_path` | string | — | Original file path, e.g. `docs/auth/oauth.md` |
| `code_language` | keyword, nullable | — | Only on `code_block` chunks (`python`, `bash`, etc.) |
| `issue_number` | int, nullable | ✅ | Only on `issue_thread` chunks |
| `issue_state` | keyword, nullable (`open`/`closed`/`resolved`) | — | Only on `issue_thread` chunks |

---

## Postgres — tenant config (not in Qdrant)

Reference only, since content type lives here, not in the collection:

```
tenants
├── tenant_id (PK, UUID)
├── name
├── content_type        -- "finance" | "devdocs"
├── qdrant_collection    -- "tenant_{tenant_id}"
├── hnsw_config          -- jsonb, per-tenant override
├── sla_latency_ms       -- target p95, informs ef_search choice
└── created_at
```

---

## Open items — decide before ingestion code is written

- [ ] Confirm Jina embedding dimension (1024 default vs. Matryoshka truncation to 512/768)
- [ ] Confirm sparse vector generation method (Qdrant built-in vs. precomputed BM25 upload)
- [ ] Decide whether `table_metadata` is stored as raw JSON or a normalized sub-schema
