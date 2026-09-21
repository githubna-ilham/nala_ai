# NALA — Day 2 Starter Code

RAG pipeline: document ingestion, embedding lokal (Ollama `nomic-embed-text`), vector search (OpenSearch), pipeline ingest otomatis (Airflow standalone), dan frontend chat + upload dokumen.

Lihat `Day 2/PANDUAN-PRAKTIK.md` di root repo untuk instruksi lengkap.

## Struktur
- `app/main.py` — FastAPI app: `/health`, `/chat` (RAG), `/` (chat UI), `/upload` (form + handler)
- `app/embeddings.py` — panggil Ollama embedding API
- `app/vector_store.py` — wrapper OpenSearch (index & search)
- `app/ingest.py` — chunking + indexing, dipakai bersama oleh Airflow DAG dan endpoint upload
- `airflow/dags/` — DAG ingest dokumen terjadwal/manual-trigger
- `tests/` — unit test

## Menjalankan test

```bash
pip install -r requirements.txt
pytest
```
