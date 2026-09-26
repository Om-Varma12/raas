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
import json
import requests
import os

url = "https://api.jina.ai/v1/embeddings"
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {os.getenv('JINA_API_KEY')}"
}
data = {
    "model": "jina-embeddings-v5-omni-small",
    "task": "retrieval.query",
    "normalized": True,
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

response = requests.post(url, headers=headers, json=data)
print(response.json())
```

**Other params used:**
- `normalized: True` — vectors normalized on the Jina side, matches Cosine distance config in Qdrant collection schema (see SCHEMA.md)

**Open items:**
- [ ] Confirm v5-omni vs. text-only model — see flag above
- [ ] Confirm output embedding dimension for chosen model (affects Qdrant vector config in SCHEMA.md)
- [ ] Decide retry/rate-limit handling strategy for the embedder wrapper