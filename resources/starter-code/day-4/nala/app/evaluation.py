def is_relevant(chunk_text: str, must_contain: list[str]) -> bool:
    text_lower = chunk_text.lower()
    hits = sum(1 for kw in must_contain if kw.lower() in text_lower)
    return hits >= max(1, len(must_contain) // 2)


def precision_at_k(retrieved: list[dict], must_contain: list[str], k: int) -> float:
    top_k = retrieved[:k]
    if not top_k:
        return 0.0
    relevant_count = sum(1 for r in top_k if is_relevant(r["text"], must_contain))
    return relevant_count / len(top_k)


def hit_rate_at_k(retrieved: list[dict], must_contain: list[str], k: int) -> float:
    top_k = retrieved[:k]
    return 1.0 if any(is_relevant(r["text"], must_contain) for r in top_k) else 0.0


def reciprocal_rank(retrieved: list[dict], must_contain: list[str]) -> float:
    for i, r in enumerate(retrieved):
        if is_relevant(r["text"], must_contain):
            return 1.0 / (i + 1)
    return 0.0
