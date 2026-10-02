import numpy as np
from typing import List, Dict, Any, Union

def calculate_recall_at_k(relevant_ids: List[str], retrieved_ids: List[str], k: int) -> float:
    """
    Calculates Recall@K: Proportion of relevant documents retrieved in the top K results.
    """
    if not relevant_ids:
        return 0.0

    top_k_retrieved = retrieved_ids[:k]
    hits = len(set(relevant_ids) & set(top_k_retrieved))
    return hits / len(relevant_ids)

def calculate_mrr(relevant_ids: List[str], retrieved_ids: List[str]) -> float:
    """
    Calculates Mean Reciprocal Rank (MRR): 1/rank of the first relevant document.
    """
    if not relevant_ids:
        return 0.0

    for rank, rid in enumerate(retrieved_ids, 1):
        if rid in relevant_ids:
            return 1.0 / rank

    return 0.0

def calculate_ndcg(relevant_ids: List[str], retrieved_ids: List[str], k: int = 10) -> float:
    """
    Calculates Normalized Discounted Cumulative Gain (nDCG).
    """
    # Simplified binary relevance nDCG
    dcg = 0.0
    for rank, rid in enumerate(retrieved_ids[:k], 1):
        if rid in relevant_ids:
            dcg += 1.0 / np.log2(rank + 1)

    if not relevant_ids:
        return 0.0

    # Ideal DCG (all relevant docs at the top)
    idcg = 0.0
    for rank in range(1, min(len(relevant_ids), k) + 1):
        idcg += 1.0 / np.log2(rank + 1)

    return dcg / idcg if idcg > 0 else 0.0
