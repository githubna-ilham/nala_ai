# Building Enterprise AI Assistant with Private LLM, RAG & Agentic Tools

## Deskripsi Pelatihan

Pelatihan ini dirancang untuk membangun **NALA** (Nusantara Assistant), sebuah asisten AI enterprise privat yang menggunakan teknologi Large Language Model (LLM) lokal dengan Ollama. NALA dibangun khusus untuk PT Nusantara Finance dengan fokus pada privasi data dan keamanan informasi. Peserta akan belajar mengintegrasikan NALA dengan dua sumber data utama: dokumen prosedur operasional standar (SOP) perusahaan melalui teknologi Retrieval-Augmented Generation (RAG), serta data operasional real-time (pengajuan kredit, klaim, dll) menggunakan agentic tools dan query SQL. Materi disusun sebagai **30 modul berurutan** (Module 1 sampai Module 30) — tiap modul memperkenalkan satu lapisan fungsionalitas baru yang diintegrasikan ke dalam sistem `nala` yang sama, membangun dari fondasi sederhana menjadi sistem produksi lengkap.

## Target Peserta

Pelatihan ini dirancang untuk audiens campuran yang terdiri dari:
- **Peserta Non-Teknis**: produk manager, operations manager, business analyst yang ingin memahami kemampuan dan keterbatasan LLM lokal dalam konteks bisnis
- **Peserta Teknis**: software engineer, data engineer yang akan mengimplementasikan dan maintain sistem

**Prasyarat:** Peserta diharapkan familiar dengan command line dasar (navigasi folder, menjalankan command). Tidak wajib mahir coding untuk mengikuti modul-modul awal (Module 1-4); isi pelatihan akan membimbing langkah demi langkah dengan penjelasan untuk semua level.

## Learning Objectives

Setelah menyelesaikan seluruh 30 modul, peserta diharapkan dapat:

1. Memahami LLM lokal/privat, risiko privasi data LLM cloud, dan menulis prompt yang efektif untuk model berukuran kecil (Module 1-3)
2. Menjalankan infrastruktur Docker Compose untuk NALA, membangun FastAPI lalu menyambungkannya ke Ollama (environment, model, system prompt), membangun chat berbasis streaming (`/chat/stream`, satu-satunya endpoint chat sejak Module 8) dan pipeline RAG langkah demi langkah — data seed, embedding, OpenSearch, semantic search & vector store, RAG chain pertama, chunking, upload dokumen, sampai pipeline ingest otomatis (Airflow) — supaya NALA bisa menjawab dari dokumen SOP internal (Module 4-17)
3. Meningkatkan akurasi retrieval dokumen menggunakan BM25, hybrid search (kombinasi lexical + semantic via RRF), dan reranking, serta mengukur kualitas dengan metrik evaluasi dan observability (Module 18-22)
4. Membangun agentic tools dengan LangGraph yang memungkinkan NALA memilih antara menjawab dari dokumen RAG atau menjalankan query data operasional via SQL — termasuk memanggil beberapa tool sekaligus (multi-hop) dan routing antar tool — lengkap dengan RBAC dan audit logging (Module 23-27)
5. Menambahkan lapisan operasional dengan Redis (cache jawaban, job queue untuk upload, rate limiting per-IP), mem-polish frontend supaya siap didemokan, memahami prinsip umum etika & governance AI (bias, overreliance, akuntabilitas), dan mempresentasikan hasil capstone (Module 28-30)

## Daftar Modul

30 modul berurutan, dibangun secara progresif (modul belakangan bergantung pada kode dari modul sebelumnya):

1. **[Module 1: Pengantar LLM & Privasi Data](Module-01-Pengantar-LLM-Privasi-Data/materi.md)** — Konsep dasar LLM, perbedaan cloud vs lokal, risiko privasi, pengenalan tools yang akan digunakan
2. **[Module 2: Setup Ollama & Evaluasi Model](Module-02-Setup-Ollama-Evaluasi-Model/materi.md)** — Instalasi dan konfigurasi Ollama, loading model, basic inference, metrik evaluasi performa dasar (worksheet praktik: [WORKSHEET-Percobaan-Ollama.md](Module-02-Setup-Ollama-Evaluasi-Model/WORKSHEET-Percobaan-Ollama.md))
3. **[Module 3: Prompt Engineering Dasar](Module-03-Prompt-Engineering-Dasar/materi.md)** — System prompts, few-shot prompting, evaluation teknik prompt, best-practice untuk model kecil
4. **[Module 4: Setup Infra Docker Compose](Module-04-Setup-Infra-Docker-Compose/materi.md)** — Arsitektur NALA dengan Docker Compose, konfigurasi service, deployment lokal, verifikasi Ollama sendirian di container, dan referensi lengkap REST API Ollama
5. **[Module 5: FastAPI Dasar](Module-05-FastAPI-Dasar/materi.md)** — FastAPI sebagai framework API, endpoint `/health`, "cetakan" `ChatRequest`/`ChatResponse` (Pydantic) — murni FastAPI, **belum tersambung ke Ollama sama sekali**; koneksi ke Ollama dibahas terpisah, pelan-pelan, di Module 6
6. **[Module 6: Integrasi Ollama — Environment, Model & System Prompt](Module-06-Integrasi-Ollama/materi.md)** — Menyambungkan FastAPI dari Module 5 ke Ollama yang sudah berjalan di Docker sejak Module 4: `Dockerfile`, service `api` di `docker-compose.yml`, environment variable (`OLLAMA_BASE_URL`/`OLLAMA_MODEL`), `OllamaClient`, lalu endpoint `/chat` dengan system prompt generik, dan terakhir `NALA_SYSTEM_PROMPT` hasil Module 3 terintegrasi
7. **[Module 7: Chat UI Dasar](Module-07-Chat-UI-Dasar/materi.md)** — Menjalankan frontend chat sederhana yang terhubung langsung ke Ollama lewat `/chat` (tanpa RAG), memverifikasi end-to-end koneksi backend-frontend-LLM sebelum menambahkan kompleksitas dokumen — `/chat` sengaja dibuat sesederhana mungkin karena akan **diganti total** di Module 8
8. **[Module 8: Streaming & Multi-Turn Conversation](Module-08-Streaming-Multi-Turn/materi.md)** — Endpoint `/chat/stream` **menggantikan total** `/chat` (dihapus, bukan ditambah di sampingnya), streaming token-demi-token dari Ollama `/api/chat`, riwayat percakapan dengan windowing 10 pesan, UX reset percakapan — masih tanpa RAG. Mulai modul ini, `/chat/stream` jadi satu-satunya endpoint chat sepanjang sisa modul RAG
9. **[Module 9: Konsep RAG](Module-09-Konsep-RAG/materi.md)** — Sesi konsep murni (tanpa kode): kelemahan LLM (halusinasi), analogi ujian *closed-book* vs *open-book*, definisi RAG, alur kerja RAG secara garis besar, dan kapan RAG bukan solusi yang tepat — jawaban atas "kenapa" sebelum modul-modul berikutnya membangun "bagaimana"
10. **[Module 10: Setup Knowledge Base & Data Dasar Awal](Module-10-Setup-Knowledge-Base/materi.md)** — Folder `knowledge-base/` dengan data seed, fungsi `extract_text()` untuk membaca isi dokumen `.md`/`.txt`/`.pdf` apa adanya — **tidak ada chunking di modul ini**, sengaja ditunda sampai Module 15
11. **[Module 11: Embedding](Module-11-Embedding/materi.md)** — Model embedding lokal `nomic-embed-text`, fungsi `embed_text()`, kenapa embedding selalu deterministik (beda dengan `generate()`), batas context window
12. **[Module 12: OpenSearch](Module-12-OpenSearch/materi.md)** — Apa itu OpenSearch, asal-usul dari Elasticsearch, konsep index/document, REST API, kenapa OpenSearch dipilih untuk NALA, dan cara menyalakannya di Docker Compose
13. **[Module 13: Semantic Search](Module-13-Semantic-Search/materi.md)** — Lanskap vector database (vector database khusus, extension seperti pgvector, search engine seperti OpenSearch), pembahasan **detail** metrik kemiripan: cosine similarity, Euclidean distance (L2), dot product — serta kenapa ketiganya identik untuk vektor ternormalisasi — dan class `VectorStore` (`ensure_index`/`index_document`/`search`)
14. **[Module 14: RAG Chain v1](Module-14-RAG-Chain/materi.md)** — Menyatukan `extract_text()`+embedding+vector store jadi `ingest_documents()` versi pertama (satu dokumen = satu vektor utuh, **belum ada chunking**), mengisi index dengan data seed, menyambungkan retrieval ke `/chat/stream` — **RAG benar-benar hidup untuk pertama kalinya**, plus keterbatasan retrieval level-dokumen sebagai motivasi Module 15
15. **[Module 15: Chunking](Module-15-Chunking/materi.md)** — Strategi chunking (fixed-size dengan overlap, structure-aware berbasis heading Markdown), fungsi `chunk_text()`/`chunk_markdown()`, upgrade `ingest_document()` jadi level-chunk, `top_k` dinaikkan di `/chat/stream` — murni pada mesin RAG-nya sendiri, plus keterbatasan retrieval semantic murni level-chunk sebagai motivasi Module 18-19
16. **[Module 16: Upload Dokumen](Module-16-Upload-Dokumen/materi.md)** — Form upload dan endpoint `/upload`, langsung tersambung ke `ingest_document()` yang sudah level-chunk (Module 15) untuk **satu** file yang baru diupload — cara staff menambah dokumen ke sistem yang **sudah hidup**, tanpa jeda "simpan dulu proses belakangan"
17. **[Module 17: Airflow Ingest Pipeline](Module-17-Airflow-Ingest-Pipeline/materi.md)** — Pengenalan Apache Airflow, DAG design, sebagai pemicu **alternatif** untuk `ingest_documents()` (scan seluruh folder) — cocok untuk batch, audit trail, dan siap upgrade ke terjadwal
18. **[Module 18: BM25 Search](Module-18-BM25-Search/materi.md)** — Menutup keterbatasan vector search murni yang terdokumentasi di modul-modul RAG sebelumnya, dengan menambahkan `search_bm25()` (pencarian kata kunci eksak) sebagai kemampuan baru di `VectorStore`, tanpa reindex
19. **[Module 19: Hybrid Search (RRF)](Module-19-Hybrid-Search-RRF/materi.md)** — Menggabungkan BM25 (Module 18) dan vector search (Module 13) lewat Reciprocal Rank Fusion jadi `search_hybrid()`, menyambungkannya ke `/chat/stream`, dan hasil uji nyata yang jujur (perbaikan terukur, belum tuntas)
20. **[Module 20: Reranking dengan Cross-Encoder](Module-20-Reranking-Cross-Encoder/materi.md)** — Mengambil kandidat lebih besar (top-20) dari hybrid search, menyortirnya ulang dengan cross-encoder lokal (`sentence-transformers`) untuk mendapat top-3/5 yang lebih akurat dikirim ke LLM
21. **[Module 21: Observability & Tracing dengan Langfuse](Module-21-Observability-Langfuse/materi.md)** — Deploy Langfuse self-hosted (v2), instrumentasi trace/span/generation untuk `/chat/stream`, telusuri trace untuk mendiagnosis jawaban yang buruk secara per-request
22. **[Module 22: Framework Evaluasi RAG](Module-22-Evaluasi-RAG/materi.md)** — Test set berlabel kecil, metrik Precision@k/Hit Rate@k/MRR, perbandingan kuantitatif sebelum-sesudah reranking, dan LLM-as-judge lokal untuk faithfulness/relevance — pengukuran agregat yang melengkapi trace per-request Module 21
23. **[Module 23: Setup Data Operasional — PostgreSQL & UI Form](Module-23-Setup-Data-Operasional-PostgreSQL/materi.md)** — Service PostgreSQL baru, skema `pengajuan_kredit` & `klaim_asuransi`, dua role terpisah (`nala_readonly`/`nala_writer`), halaman `/data-operasional` untuk staff menambah data operasional sendiri
24. **[Module 24: Desain Agent dengan LangGraph — Tool-Calling](Module-24-LangGraph-Agent-Tool-Calling/materi.md)** — Konsep agent sebagai graph (node/edge/state) vs pipeline tetap, refactor RAG chain (Module 7-22) jadi tool pertama, tool-calling native Ollama untuk `llama3.2:3b`
25. **[Module 25: Tool Baru — Query SQL ke Data Operasional (PostgreSQL)](Module-25-SQL-Tool-Data-Operasional/materi.md)** — Tool query SQL yang dibatasi (bukan raw SQL bebas dari LLM) untuk mencegah SQL injection, membaca data lewat role `nala_readonly` yang sudah disiapkan Module 23, lalu mendaftarkannya ke agent — plus pembuktian **multi-hop** (Bagian 4): kedua tool dipanggil berurutan untuk satu pertanyaan gabungan, tanpa kode baru, murni konsekuensi desain graph Module 24
26. **[Module 26: Routing — Menggabungkan RAG + SQL Tool dalam Satu Agent](Module-26-Routing-RAG-vs-SQL/materi.md)** — Bagaimana LLM memutuskan tool mana yang dipakai, diagram keputusan, contoh pertanyaan per tool, kasus routing yang ambigu/salah, catatan trade-off model 3B vs `qwen2.5:7b`
27. **[Module 27: RBAC & Audit Logging](Module-27-RBAC-Audit-Logging/materi.md)** — Role per user/session yang membatasi akses tool SQL, pencatatan audit trail (siapa, tanya apa, tool apa, data apa, kapan) ke tabel PostgreSQL, relevansi untuk compliance sektor keuangan
28. **[Module 28: Redis — Cache, Job Queue, dan Rate Limiting](Module-28-Redis-Cache-Queue-RateLimit/materi.md)** — Satu service Redis untuk tiga kebutuhan: cache jawaban `/chat` (dengan `role` di dalam key, supaya tidak bocor antar role), job queue RQ + service `worker` supaya `/upload` tidak lagi memblokir user saat embedding, dan rate limiting per-IP supaya satu skrip tidak bisa membanjiri Ollama
29. **[Module 29: Polish Frontend untuk Demo Capstone](Module-29-Polish-Frontend-Demo/materi.md)** — Polish `chat.html`/`upload.html`: badge tool yang dipakai agent (RAG vs SQL), loading/typing indicator, cek layout responsif — tetap server-rendered Jinja2 + vanilla CSS/JS, tanpa framework baru
30. **[Module 30: Etika & Governance AI](Module-30-Ethics-Governance/materi.md)** — Sesi diskusi murni (tanpa kode): bias dari kurasi dokumen (bukan dari training model), overreliance staf pada jawaban AI, transparansi lewat tool-used badge, akuntabilitas dan human-in-the-loop untuk keputusan berdampak signifikan, plus peta risiko yang menyatukan temuan etika/governance/teknis — prinsip umum tata kelola AI, eksplisit **bukan** klaim kepatuhan regulasi spesifik

## Capstone

Paket capstone ada di **[`Capstone/`](Capstone/)**, terpisah dari ke-30 modul di atas karena bukan materi berurutan yang dibangun bertahap — ini paket evaluasi akhir:

- **[`rubrik-penilaian.md`](Capstone/rubrik-penilaian.md)** — 4 kriteria penilaian (fungsionalitas sistem, quality of retrieved answers, pemahaman teknis trade-off, presentasi & komunikasi), masing-masing dengan level skor konkret
- **[`template-presentasi.md`](Capstone/template-presentasi.md)** — Outline yang wajib dicakup peserta/kelompok saat presentasi: problem framing, architecture walkthrough, skrip demo, trade-off, rencana lanjutan
- **[`case-study-brief.md`](Capstone/case-study-brief.md)** — Studi kasus perbaikan konkret untuk PT Nusantara Finance yang jadi dasar demo capstone (dokumen SOP baru untuk RAG + jenis pertanyaan operasional baru untuk routing ke SQL tool)

## Stack Teknologi

Pelatihan menggunakan stack teknologi modern yang seimbang antara kemudahan pembelajaran dan production-ready:

- **Ollama** — Runtime lokal untuk LLM open-source, memastikan data tidak dikirim ke API pihak ketiga
- **FastAPI** — Framework Python lightweight untuk REST API
- **OpenSearch** — Distributed search engine untuk vector embeddings dan hybrid search
- **PostgreSQL** — Database relasional untuk data operasional perusahaan
- **Apache Airflow** — Orchestration platform untuk pipeline ETL dan document processing
- **LangGraph** — Framework untuk membangun agentic workflows dengan state management
- **Langfuse** — Observability platform untuk monitoring, evaluasi, dan debugging LLM applications
- **Docker Compose** — Container orchestration lokal untuk menjalankan semua service dengan mudah

## Format Evaluasi

Evaluasi peserta dilakukan melalui tiga tahap:

1. **Pretest (sebelum Module 1)** — Kuis pilihan ganda 10 soal untuk mengukur pengetahuan awal peserta tentang LLM, private vs cloud inference, RAG basics, agentic tools, dan Docker
2. **Posttest (setelah Module 30, sebelum capstone)** — Kuis serupa dengan pretest untuk mengukur improvement knowledge
3. **Capstone Presentation** — Setiap peserta atau kelompok mempresentasikan hasil praktik mereka dengan rubrik penilaian: (1) fungsionalitas sistem, (2) quality of retrieved answers, (3) pemahaman teknis tentang trade-off yang dilakukan, (4) presentasi dan komunikasi hasil

## Prasyarat Komputer

Peserta harus menyiapkan laptop dengan spesifikasi berikut sebelum modul pertama dimulai:

- **Docker Desktop** terinstall dan berjalan di laptop (tersedia untuk Windows, macOS, Linux)
- **Minimal 16GB RAM** tersedia — untuk menjalankan LLM lokal (Ollama) bersamaan dengan services pendukung (FastAPI, OpenSearch, PostgreSQL, Airflow, LangGraph)
- **Koneksi internet stabil** — diperlukan saat awal pelatihan untuk pull Docker images dan download model Ollama (ukuran ~5-10GB tergantung model); setelah itu sistem berjalan full offline
- **Text editor atau IDE** — VS Code, JetBrains, atau editor pilihan untuk mengedit kode Python dan YAML; disarankan minimal 50GB free disk space untuk Docker images dan model storage

Peserta akan menerima checklist setup environment sebelum pelatihan dimulai untuk memastikan semua environment siap.

## Rekomendasi Model LLM

Model default yang dipakai konsisten sepanjang seluruh 30 modul adalah **`llama3.2:3b`** (lihat perhitungan RAM/VRAM di `Module-02-Setup-Ollama-Evaluasi-Model/materi.md` section 5.1). Alasan memakai satu model yang sama sepanjang training:

- **Constraint RAM total stack, bukan cuma LLM** — prasyarat di atas hanya mensyaratkan minimal 16GB RAM untuk menjalankan Ollama **bersamaan** dengan OpenSearch, PostgreSQL, Airflow, FastAPI, LangGraph, dan Langfuse via Docker Compose. Model 7B (butuh ~8GB RAM+overhead) berisiko membuat laptop peserta kehabisan memory begitu seluruh service aktif bersamaan.
- **Llama 3.2 sudah mendukung tool-calling** — Module 23 butuh agentic tool-calling (LangGraph routing ke RAG vs SQL tool); model family Llama 3.2 (termasuk varian 3B) sudah punya dukungan tool-calling di Ollama, jadi tidak perlu model lebih besar hanya demi fitur ini.
- **Konsistensi kurikulum** — project `nala` tumbuh progresif dari Module 1 ke Module 30; mengganti model di tengah jalan berisiko membuat system prompt/prompt engineering yang sudah dibuat di Module 3 perlu di-tuning ulang.

**Opsi upgrade (khusus peserta dengan RAM 32GB+):** Jika di Module 25 akurasi routing RAG-vs-SQL kurang memadai dengan model 3B, `qwen2.5:7b` bisa dijadikan alternatif opsional. Ini sebaiknya diperkenalkan sebagai catatan tambahan di materi Module 25, bukan sebagai default, mengingat prasyarat komputer di atas hanya menjamin 16GB RAM untuk seluruh peserta.

---

**Informasi Lebih Lanjut:** Lihat folder `Module-01-*` sampai `Module-30-*` — tiap folder berisi satu `materi.md` yang mencakup materi konsep sekaligus panduan praktik hands-on (bagian "Panduan Praktik" di akhir file) — dan `Capstone/` untuk paket evaluasi akhir (rubrik penilaian, template presentasi, studi kasus capstone).
