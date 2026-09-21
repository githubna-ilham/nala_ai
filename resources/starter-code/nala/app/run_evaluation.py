from app.embeddings import embed_text
from app.eval_testset import QA_TESTSET
from app.evaluation import hit_rate_at_k, precision_at_k, reciprocal_rank
from app.reranker import Reranker
from app.vector_store import VectorStore

OLLAMA_BASE_URL = "http://ollama:11434"
OPENSEARCH_BASE_URL = "http://opensearch:9200"


def evaluate(retrieved_fn, label: str) -> dict:
    precisions, hits, rrs = [], [], []
    for item in QA_TESTSET:
        retrieved = retrieved_fn(item["question"])
        precisions.append(precision_at_k(retrieved, item["must_contain"], k=3))
        hits.append(hit_rate_at_k(retrieved, item["must_contain"], k=3))
        rrs.append(reciprocal_rank(retrieved, item["must_contain"]))

    n = len(QA_TESTSET)
    print(f"--- {label} ---")
    print(f"Precision@3 : {sum(precisions) / n:.3f}")
    print(f"Hit Rate@3  : {sum(hits) / n:.3f}")
    print(f"MRR         : {sum(rrs) / n:.3f}")
    return {"precision@3": sum(precisions) / n, "hit_rate@3": sum(hits) / n, "mrr": sum(rrs) / n}


if __name__ == "__main__":
    store = VectorStore(base_url=OPENSEARCH_BASE_URL, index_name="nala-docs")
    reranker = Reranker()

    def before_rerank(question: str) -> list[dict]:
        query_embedding = embed_text(question, base_url=OLLAMA_BASE_URL)
        return store.search_hybrid(question, query_embedding, top_k=3, candidate_pool=20)

    def after_rerank(question: str) -> list[dict]:
        query_embedding = embed_text(question, base_url=OLLAMA_BASE_URL)
        candidates = store.search_hybrid(question, query_embedding, top_k=20, candidate_pool=20)
        return reranker.rerank(question, candidates, top_k=3)

    before = evaluate(before_rerank, "SEBELUM Reranking (hybrid search saja)")
    after = evaluate(after_rerank, "SESUDAH Reranking (hybrid + cross-encoder)")

    print("\n--- Perbandingan ---")
    for metric in ["precision@3", "hit_rate@3", "mrr"]:
        delta = after[metric] - before[metric]
        print(f"{metric}: {before[metric]:.3f} -> {after[metric]:.3f} ({delta:+.3f})")
