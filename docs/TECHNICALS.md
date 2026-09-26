# RAG Platform — Technical Decisions

Running log of what we're using, how, and why. One section per component.

---

## Embedding Model — Jina

**What:** Jina Embeddings API (`https://api.jina.ai/v1/embeddings`)

**Model:** `jina-embeddings-v4`

3.8B param, natively multimodal (text/image/PDF), 2048-dim native output, Matryoshka truncation supported down to 128 dims with minimal quality loss. Chosen deliberately over a text-only model to leave room for embedding charts/tables-as-images from filings or docs later without a re-embed migration.

**Dimension: truncated to 1024** via the `dimensions` param — matches Qdrant vector config in SCHEMA.md, avoids paying 2x storage/memory for the full 2048 without a demonstrated recall gain. Revisit via golden-set ablation (1024 vs 2048) if recall numbers say otherwise.

**Task type usage:**

| Path | Task type | Why |
|---|---|---|
| Ingestion (chunk embedding) | `retrieval.passage` | Optimizes embedding for documents meant to be *retrieved* — asymmetric retrieval setup, chunks are dense/declarative |
| Query (user question embedding) | `retrieval.query` | Optimizes embedding for the *search query* side — short, interrogative. Must match on the query side of every retrieval call |

**Critical constraint:** query and passage embeddings for the same text are *not* interchangeable — task type changes the actual output vector. Never mix task types within one collection's similarity comparisons. `embed()` function signature should require `task` as an explicit param, not a default, to prevent silent misuse:

```python
def embed(texts: list[str], task: Literal["retrieval.passage", "retrieval.query"]) -> list[list[float]]:
    ...
```

**API call reference:**

```python
import requests
import json
import os

url = "https://api.jina.ai/v1/embeddings"
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {os.getenv('JINA_API_KEY')}"
}
data = {
    "model": "jina-embeddings-v4",
    "task": "text-matching",
    "input": [
        {"text": "A beautiful sunset over the beach"},
        {"text": "Un beau coucher de soleil sur la plage"},
        {"text": "海滩上美丽的日落"},
        {"text": "浜辺に沈む美しい夕日"},
        {"image": "https://images.unsplash.com/photo-1460627390041-532a28402358?w=640&q=80&fm=jpg&fit=crop"},
        {"image": "https://images.unsplash.com/photo-1503803548695-c2a7b4a5b875?w=640&q=80&fm=jpg&fit=crop"},
        {"image": "iVBORw0KGgoAAAANSUhEUgAAABwAAAA4CAIAAABhUg/jAAAAMklEQVR4nO3MQREAMAgAoLkoFreTiSzhy4MARGe9bX99lEqlUqlUKpVKpVKpVCqVHksHaBwCA2cPf0cAAAAASUVORK5CYII="}
    ]
}

response = requests.post(url, headers=headers, data=json.dumps(data))
print(response.json())
```

**Other params used:**
- `normalized: True` — vectors normalized on the Jina side, matches Cosine distance config in Qdrant collection schema (see SCHEMA.md)


---

## Chunking Strategy — Tenant-specific

Chunking is determined by document structure and tenant type rather than using one universal splitter. Structural boundaries are preferred over blind token/character windows.

### Finance — SEC `.htm` Filings

SEC 10-K filings are structurally complex: nested tables, `<div>` elements without clean paragraph boundaries, and inline-XBRL `<ix>` tags. Do not treat these as generic HTML-to-text documents.

**1. Parse by SEC section structure first**

Parse the filing using `unstructured` or BeautifulSoup while targeting the actual SEC section structure.

10-Ks contain standardized sections such as:

- `Item 1` — Business
- `Item 1A` — Risk Factors
- `Item 7` — Management's Discussion and Analysis
- etc.

Split on these section boundaries **before** any size-based chunking. These are high-signal semantic boundaries that generic recursive chunking would otherwise ignore.

**2. Tables are separate retrieval units**

Tables must be extracted separately from surrounding prose and never merged into the same chunk.

Represent tables as either:

- Markdown-table text for embedding, or
- Structured JSON stored in Qdrant metadata.

Each table chunk should contain a pointer to its originating SEC section.

This prevents queries such as *"What was Q3 revenue?"* from retrieving a chunk containing a mixture of narrative text and fragmented table rows.

**3. Chunk size**

Within each SEC section:

- Target: **~400–600 tokens**
- Use recursive character splitting after the structural section split.
- Store the following in Qdrant payload metadata:
  - `section_name`
  - `item_number`
  - `document_id`
  - `chunk_index`

Section information should be available for filtering/boosting during retrieval rather than relying only on the embedding to capture it.

**4. Overlap**

No fixed overlap tuning yet.

When overlap is introduced:

- Preserve sentence boundaries.
- Never split in the middle of a table row.
- Prefer structurally meaningful boundaries over arbitrary character offsets.

---

### Dev Docs — `.md` Files

Markdown already contains meaningful document structure. Preserve that structure instead of flattening the document before chunking.

**1. Split on Markdown headers first**

Use a header-aware splitter such as LangChain's `MarkdownHeaderTextSplitter`, or implement equivalent logic.

Primary boundaries:

- `#`
- `##`
- `###`

Header hierarchy should be retained as metadata so a chunk knows the section it belongs to.

**2. Fenced code blocks are atomic**

Never split inside a fenced code block.

Detect triple-backtick fences (` ``` `) and treat the entire code block as one atomic chunk.

If a code block exceeds the normal chunk size, allow that chunk to run long rather than splitting a function or code example across multiple chunks.

This avoids retrieving incomplete code and makes code-focused queries more reliable.

**3. GitHub issues use a separate strategy**

GitHub issues are structurally different from documentation and should not use the same splitter.

An issue is generally:

- Title
- Body
- Comment thread

Use:

- Whole issue when it is short.
- Per-comment chunks when the issue/thread is long.

Store issue-specific metadata such as:

- `issue_number`
- `thread_position`
- `comment_author`
- `document_id`

This allows multi-hop questions such as *"What did the maintainer say after the first fix attempt?"* to be answered using the conversation sequence.

**4. Chunk size**

For Markdown documentation:

- Target: **~200–400 tokens** for prose sections.

Dev-doc queries are generally narrower and more configuration-oriented than financial queries, so smaller chunks are preferred.

---

### Design Principle

The chunker should be selected based on **document structure**, not simply file extension.

| Tenant / Document | Primary boundary | Secondary chunking | Target size |
|---|---|---|---|
| SEC 10-K | SEC `Item` sections | Recursive splitter | ~400–600 tokens |
| SEC tables | Individual table | Table-aware handling | Independent chunk |
| Dev docs | Markdown headers | Recursive splitter | ~200–400 tokens |
| Fenced code | Entire code block | No internal splitting | Atomic |
| GitHub issues | Issue / comment | Whole issue or per-comment | Short / conversational |

The general pipeline is:

**Document parsing → Structural segmentation → Special-content extraction → Size-based chunking → Metadata enrichment → Embedding**

Structural segmentation should happen **before** token/character-based chunking wherever the document format provides meaningful boundaries.