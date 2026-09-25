# NALA — Starter Code

Ini adalah satu-satunya folder kerja kode NALA untuk seluruh kurikulum **AI_NALA** (31 modul). Tidak ada lagi pembagian per-hari atau snapshot terpisah — kode di sini tumbuh **di tempat yang sama**, bertahap dari Module 1 sampai Module 31, mengikuti instruksi "Panduan Praktik" di tiap `materi.md`.

Isi folder ini saat ini mencerminkan state **akhir** (setelah seluruh 31 modul selesai dibangun) — dipakai sebagai referensi/jawaban kalau kode Anda sendiri (dibangun mengikuti materi tahap demi tahap) perlu dicocokkan.

## Struktur

- `app/main.py` — FastAPI app: endpoint `/health`, `/chat` (non-streaming, dipakai sejak Module 24 untuk agentic tool-calling), `/chat/stream` (streaming, satu-satunya endpoint chat non-agentic sejak Module 8), `/upload`, `/data-operasional`, `/login`, `/logout`
- `app/ollama_client.py` — `OllamaClient` (generate/chat, streaming & non-streaming, tool-calling)
- `app/system_prompt.py` — `NALA_SYSTEM_PROMPT`
- `app/embeddings.py`, `app/vector_store.py`, `app/ingest.py` — RAG pipeline (embedding, OpenSearch vector + BM25 + hybrid search, chunking, ingest)
- `app/reranker.py` — cross-encoder reranking (Module 20)
- `app/evaluation.py`, `app/eval_testset.py`, `app/run_evaluation.py` — framework evaluasi RAG (Module 22)
- `app/agent.py` — LangGraph agent (Module 24)
- `app/tools/` — `rag_tool.py` (Module 24), `sql_tool.py` (Module 25)
- `app/db.py` — koneksi data operasional PostgreSQL (Module 23)
- `app/auth.py`, `app/audit.py` — login/session & audit logging (Module 27)
- `app/cache.py`, `app/queue.py`, `app/jobs.py`, `app/rate_limit.py` — lapisan Redis: cache jawaban, job queue ingest, rate limiting (Module 28)
- `app/templates/`, `app/static/` — frontend Jinja2 (login, chat, upload, data operasional)
- `airflow/dags/` — DAG ingest dokumen (Module 17)
- `db/seed.sql` — seed data operasional (Module 23)
- `docker-compose.yml` — seluruh service: `ollama`, `api`, `redis`, `worker`, `opensearch`, `opensearch-dashboards`, `airflow`, `postgres`, `adminer`, `langfuse` + `langfuse-db`
- `tests/` — unit test

## Menjalankan

Lihat `materi.md` tiap modul (khususnya Module 4, bagian Panduan Praktik) untuk instruksi lengkap `docker compose up`. Untuk menjalankan test secara lokal:

```bash
pip install -r requirements.txt
pytest
```
