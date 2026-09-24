# NALA — Starter Code

Ini adalah satu-satunya folder kerja kode NALA untuk seluruh kurikulum **AI_NALA** (31 modul). Tidak ada lagi pembagian per-hari atau snapshot terpisah — kode di sini tumbuh **di tempat yang sama**, bertahap dari Module 1 sampai Module 31, mengikuti instruksi "Panduan Praktik" di tiap `materi.md`.

Isi folder ini saat ini mencerminkan state **akhir** (setelah seluruh 27 modul selesai dibangun) — dipakai sebagai referensi/jawaban kalau kode Anda sendiri (dibangun mengikuti materi tahap demi tahap) perlu dicocokkan.

## Struktur

- `app/main.py` — FastAPI app: endpoint `/health`, `/chat` (non-streaming, dipakai sejak Module 20 untuk agentic tool-calling), `/chat/stream` (streaming, satu-satunya endpoint chat non-agentic sejak Module 6), `/upload`, `/data-operasional`, `/status`
- `app/ollama_client.py` — `OllamaClient` (generate/chat, streaming & non-streaming, tool-calling)
- `app/system_prompt.py` — `NALA_SYSTEM_PROMPT`
- `app/embeddings.py`, `app/vector_store.py`, `app/ingest.py` — RAG pipeline (embedding, OpenSearch hybrid search, chunking, ingest)
- `app/reranker.py` — cross-encoder reranking (Module 16)
- `app/evaluation.py`, `app/eval_testset.py`, `app/run_evaluation.py` — framework evaluasi RAG (Module 17)
- `app/agent.py` — LangGraph agent (Module 20-22)
- `app/tools/` — `rag_tool.py`, `sql_tool.py` (Module 20-22)
- `app/db.py`, `app/audit.py` — koneksi data operasional PostgreSQL & audit logging (Module 19, 23)
- `app/templates/`, `app/static/` — frontend Jinja2 (chat, upload, data operasional, status page)
- `airflow/dags/` — DAG ingest dokumen (Module 14)
- `db/seed.sql` — seed data operasional (Module 19)
- `docker-compose.yml` — seluruh service: `ollama`, `api`, `opensearch`, `airflow`, `postgres`, `langfuse` + `langfuse-db`
- `tests/` — unit test

## Menjalankan

Lihat `materi.md` tiap modul (khususnya Module 4, bagian Panduan Praktik) untuk instruksi lengkap `docker compose up`. Untuk menjalankan test secara lokal:

```bash
pip install -r requirements.txt
pytest
```
