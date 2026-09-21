# app/embeddings.py
import httpx


def embed_text(text: str, base_url: str, model: str = "nomic-embed-text") -> list[float]:
    with httpx.Client() as client:
        response = client.post(
            f"{base_url}/api/embed",
            json={"model": model, "input": text},
            timeout=60.0,
        )
        response.raise_for_status()
        return response.json()["embeddings"][0]