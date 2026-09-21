import httpx

from app.embeddings import embed_text
from app.vector_store import VectorStore

RAG_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "cari_dokumen_sop",
        "description": (
            "Mencari jawaban di dokumen SOP dan kebijakan internal PT Nusantara "
            "Finance — misalnya syarat/prosedur pengajuan kredit, prosedur klaim "
            "asuransi, kebijakan internal. Gunakan untuk pertanyaan tentang ATURAN "
            "atau PROSEDUR, bukan untuk angka/status transaksi spesifik milik "
            "nasabah tertentu (untuk itu ada tool lain, lihat Module 3)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Pertanyaan atau topik yang ingin dicari di dokumen",
                },
            },
            "required": ["query"],
        },
    },
}


def rag_search(query: str, vector_store: VectorStore, ollama_base_url: str, reranker=None) -> str:
    try:
        query_embedding = embed_text(query, base_url=ollama_base_url)
        candidates = vector_store.search_hybrid(query_text=query, query_embedding=query_embedding, top_k=20)
        results = reranker.rerank(query, candidates, top_k=3) if reranker else candidates[:3]
    except httpx.HTTPError:
        return "Tidak dapat mengakses knowledge base dokumen saat ini."

    if not results:
        return "Tidak ditemukan dokumen relevan di knowledge base untuk pertanyaan ini."

    return "\n\n".join(r["text"] for r in results)
