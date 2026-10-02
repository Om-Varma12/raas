import json
import logging
from typing import List, Dict, Any
from backend.app.eval import metrics
from backend.app.retrieval.engine import RetrievalEngine
from backend.app.ingestion.embedder import JinaEmbedder
from backend.app.retrieval.vector_store import RetrievalVectorStore
from backend.app.retrieval.reranker import CrossEncoderReranker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EvalRunner:
    """
    Runs ablation experiments across different retrieval strategies.
    """
    def __init__(self, engine: RetrievalEngine):
        self.engine = engine

    def run_golden_set(self, file_path: str, mode: str = "hybrid") -> Dict[str, Any]:
        """
        Evaluates the retriever against a specific golden set.
        Mode can be: 'dense', 'sparse', 'hybrid', 'reranked'.
        """
        results = []
        with open(file_path, 'r') as f:
            for line in f:
                item = json.loads(line)
                query = item["query"]
                tenant_id = item["tenant_id"]
                relevant_ids = item["relevant_chunk_ids"]

                # Modify retrieval based on mode for ablation
                if mode == "dense":
                    # Bypass hybrid search in vector store manually if needed,
                    # but for this framework we wrap the engine's behavior
                    retrieved = self.engine.vector_store.search_dense(tenant_id, self.engine.embedder.embed([query], task="retrieval.query")[0])
                elif mode == "sparse":
                    retrieved = self.engine.vector_store.search_sparse(tenant_id, query)
                elif mode == "hybrid":
                    # Hybrid without reranking
                    query_vec = self.engine.embedder.embed([query], task="retrieval.query")[0]
                    retrieved = self.engine.vector_store.search_hybrid(tenant_id, query, query_vec)
                else: # reranked
                    retrieved = self.engine.retrieve(tenant_id, query)

                retrieved_ids = [c.get("chunk_id", "") for c in retrieved]

                results.append({
                    "query": query,
                    "recall_5": metrics.calculate_recall_at_k(relevant_ids, retrieved_ids, 5),
                    "mrr": metrics.calculate_mrr(relevant_ids, retrieved_ids),
                    "type": item.get("type", "unknown")
                })

        # Aggregate Metrics
        avg_recall = sum(r["recall_5"] for r in results) / len(results)
        avg_mrr = sum(r["mrr"] for r in results) / len(results)

        # Slicing by content type
        slices = {}
        for r in results:
            t = r["type"]
            if t not in slices: slices[t] = []
            slices[t].append(r["recall_5"])

        type_metrics = {t: (sum(v)/len(v)) for t, v in slices.items()}

        return {
            "avg_recall@5": avg_recall,
            "avg_mrr": avg_mrr,
            "type_metrics": type_metrics
        }

    def run_ablation(self, golden_sets: List[str]):
        """
        Runs a full ablation study: Dense -> Sparse -> Hybrid -> Reranked.
        """
        modes = ["dense", "sparse", "hybrid", "reranked"]
        final_report = {}

        for gs in golden_sets:
            logger.info(f"Evaluating Golden Set: {gs}")
            set_results = {}
            for mode in modes:
                set_results[mode] = self.run_golden_set(gs, mode)
            final_report[gs] = set_results

        return final_report

if __name__ == "__main__":
    # Setup components
    embedder = JinaEmbedder()
    vstore = RetrievalVectorStore()
    reranker = CrossEncoderReranker()
    engine = RetrievalEngine(embedder, vstore, reranker)

    runner = EvalRunner(engine)
    golden_files = ["backend/app/eval/golden_sets/devdocs.jsonl", "backend/app/eval/golden_sets/finance.jsonl"]
    report = runner.run_ablation(golden_files)
    print(json.dumps(report, indent=2))
