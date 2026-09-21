# NALA — Day 2 Working Copy

Ini folder kerja untuk membangun Day 2 **secara bertahap, module demi module** — bukan kode jadi. Saat ini isinya baru mencakup **Module 1: Chat UI Dasar** (chat terhubung ke Ollama, belum ada RAG/dokumen).

Struktur akan bertambah setiap kali sebuah module selesai:
- Module 2 (Streaming & Multi-Turn) akan menambah `/chat/stream`, `chat_stream()` di `app/ollama_client.py` — masih tanpa RAG
- Module 3 (Knowledge Base) akan menambah `/upload`, `app/templates/upload.html`
- Module 4-5 (Embedding & Vector Store, lalu Chunking) akan menambah `app/embeddings.py`, `app/vector_store.py`, `app/ingest.py`, service `opensearch` di `docker-compose.yml`
- Module 6 (Airflow) akan menambah `airflow/dags/`, service `airflow`
- Module 7 (RAG Chain) akan mengubah `/chat` **dan** `/chat/stream` supaya retrieval-augmented

Ingin lihat kode jadi lengkap (semua module) sebagai referensi/perbandingan? Cek `resources/starter-code/day-2-reference/nala/` — folder itu **frozen kecuali saat scope Day 2 sendiri berubah** (misal dukungan format dokumen baru), dan dirujuk verbatim oleh ketujuh file materi `Day 2/Module-01.../materi.md` s.d. `Module-07.../materi.md`.

Lihat `Day 2/PANDUAN-PRAKTIK.md` di root repo untuk instruksi lengkap menjalankan, dan `Day 2/Module-01-Chat-UI-Dasar/materi.md` untuk panduan menulis kode Module 1 tahap demi tahap (Tahap A/B/C, termasuk prompt Claude Code siap-tempel).

## Struktur saat ini (Module 1)
- `app/main.py` — FastAPI app: `/health`, `/chat` (plain, belum RAG), `/` (chat UI)
- `app/ollama_client.py` — `OllamaClient.generate()`, byte-identical dari Day 1
- `app/system_prompt.py` — `NALA_SYSTEM_PROMPT`, byte-identical dari Day 1
- `app/templates/chat.html`, `app/static/style.css` — frontend chat
- `tests/` — unit test Module 1

## Menjalankan test

```bash
pip install -r requirements.txt
pytest
```
