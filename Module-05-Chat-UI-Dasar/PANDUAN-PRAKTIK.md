# Panduan Praktik — Module 5: Chat UI Dasar

### Dua folder kode Module 5-14 — jangan tertukar

- **`resources/starter-code/day-2/nala/`** — folder kerja Anda. Panduan Module 5-14 membangunnya **bertahap, module demi module**: di awal Module 5 isinya baru mencakup module ini, bertambah setiap kali sebuah module selesai. Semua perintah di panduan ini dijalankan di folder ini.
- **`resources/starter-code/day-2-reference/nala/`** — kode jadi lengkap dari kesembilan module yang menghasilkan kode (Module 5-6, 8-14 — Module 7 murni konsep/diskusi, tidak ada langkah kode), frozen kecuali saat scope Module 5-14 sendiri berubah (misal dukungan PDF ditambahkan ke semua modul yang relevan sekaligus, bukan cuma salah satu). Dipakai sebagai jawaban/pembanding kalau ingin mengecek hasil akhir suatu module — bukan tempat menjalankan `docker compose`.

## Prasyarat
- Sudah menyelesaikan **Module 1-4** (Docker Desktop terinstall, `llama3.2:3b` pernah dipakai, familiar dengan `docker compose up --build`)
- Docker Desktop sudah dialokasikan resource yang cukup — lihat catatan RAM di bawah

### Matikan dulu container Module 1-4 — Anda tidak akan kembali ke situ

`resources/starter-code/day-2/nala/` **bukan project terpisah** dari Module 1-4 — ia dibuat dengan menyalin seluruh kode `day-1/nala/` lebih dulu (`ollama_client.py`, `system_prompt.py`, `main.py`, `docker-compose.yml`, dst), baru ditambah fitur-fitur baru Module 5-14 di atasnya (streaming, multi-turn, RAG chain, chunking, embedding, vector store, upload, Airflow). Dengan kata lain, **`day-2/nala/` sudah mencakup semua yang ada di Module 1-4, plus lebih banyak lagi**.

Konsekuensinya: mulai sekarang, **jalankan `docker compose` dari `day-2/nala/`, bukan lagi `day-1/nala/`**. Karena nama folder `day-1/nala` dan `day-2/nala` sama-sama `nala`, Docker Compose (yang memakai **nama folder**, bukan path lengkap, sebagai *project name* secara default) memperlakukan keduanya sebagai **project yang sama** — ini disengaja, bukan sesuatu yang perlu dihindari: kalau tiap module punya project Docker terpisah, `ollama` (dan service lain ke depannya) akan berjalan duplikat, membengkakkan RAM tanpa perlu. Dengan project yang sama, `day-2/nala/docker-compose.yml` cukup **mengambil alih** container yang sudah berjalan sejak Module 1-4 — model Ollama yang sudah di-pull otomatis ikut terbawa, tidak perlu di-pull ulang.

Tidak perlu langkah "matikan dulu" secara eksplisit — cukup jalankan compose dari `day-2/nala/` seperti biasa (Langkah 2 di bawah), Docker Compose otomatis merecreate container yang definisinya berubah. Kalau Anda tetap ingin memulai dari kondisi bersih (opsional), bisa jalankan dulu:

```bash
cd resources/starter-code/day-1/nala
docker compose down
```

Cek dengan `docker ps` untuk memastikan container mana yang aktif sebelum lanjut ke Langkah 1 di bawah.

### Catatan penting: naikkan alokasi RAM Docker Desktop

Module 5-14 menambahkan **dua service baru** di atas stack Module 1-4: **OpenSearch** (vector store, mulai Module 10) dan **Airflow** (orchestrator, mode `standalone`, mulai Module 14). Kedua service ini jauh lebih berat dibanding FastAPI/Ollama saja — OpenSearch adalah JVM yang butuh heap tersendiri, dan Airflow standalone menjalankan webserver + scheduler + database sekaligus dalam satu container.

Kalau di Module 1-4 Anda mengalokasikan Docker Desktop di batas minimal (8–12GB), **naikkan ke 16GB+** untuk Module 5-14. Ikuti langkah yang sama seperti **Langkah 0 di `Module-04-Setup-Infra-Docker-Compose/PANDUAN-PRAKTIK.md`** (Docker Desktop → ⚙️ Settings → tab Resources):

| Setting | Minimal Module 5-14 | Direkomendasikan | Alasan |
|---|---|---|---|
| **Memory (RAM)** | 8 GB | 16 GB+ | `llama3.2:3b` (~4-6GB) + `nomic-embed-text` + OpenSearch (heap `-Xms512m -Xmx512m` minimal, tapi JVM + OS overhead-nya lebih besar dari itu) + Airflow standalone (webserver+scheduler+metadata DB dalam satu proses) berjalan bersamaan. |
| **CPUs** | 4 | 4+ | 4 service (ollama, opensearch, airflow, api) aktif sekaligus. |
| **Disk image size** | 80 GB | 100 GB+ | Image `opensearchproject/opensearch` dan `apache/airflow` cukup besar (>1GB masing-masing), ditambah image Module 1-4 yang mungkin masih tersimpan. |
| **Swap** | 1 GB | 2 GB | Buffer tambahan kalau Memory limit sempat mepet saat semua service start bersamaan. |

Kalau Anda sudah mengubah setting ini di Module 1-4 ke 16GB+, tidak perlu diubah lagi. Setelah mengubah, klik **Apply & Restart**.

Catatan: panduan Module 5-14 menyalakan service **secara bertahap**, mengikuti urutan module: `ollama`+`api` dulu di Langkah 2 di bawah (Module 5-8 cuma butuh ini — Module 7 malah tidak butuh service apa pun, murni diskusi), `opensearch` menyusul di Module 10, `airflow` terakhir di Module 14 — jadi beban RAM di Module 5-9 jauh lebih ringan dari 16GB. Alokasi 16GB+ tetap perlu disiapkan sebelum Module 14, begitu keempat service jalan bersamaan.

Kalau disk mulai penuh, bersihkan image/volume lama yang tidak terpakai (lihat peringatan di `Module-04-Setup-Infra-Docker-Compose/PANDUAN-PRAKTIK.md` soal `docker system prune -a --volumes` — perintah ini menghapus model Ollama yang sudah di-pull juga).

## Langkah 1: Masuk ke folder starter code

```bash
cd resources/starter-code/day-2/nala
```

## Langkah 2: Jalankan Ollama + API dulu (belum semua service)

Stack Module 5-14 total punya 4 service (`ollama`, `opensearch`, `airflow`, `api`), tapi Module 5-8 (chat UI, streaming/multi-turn, konsep RAG, data seed — Module 7 murni diskusi konsep, tidak butuh service sama sekali) cuma butuh **dua yang pertama** — `opensearch` baru dipakai mulai Module 10, `airflow` baru dipakai mulai Module 14. Supaya urutan belajar juga terasa di infrastrukturnya — bertahap, bukan langsung semua nyala sekaligus — nyalakan `ollama` dan `api` saja dulu, skip dua yang lain:

```bash
docker compose up --build --no-deps ollama api
```

Flag `--no-deps` penting: tanpa itu, Docker Compose otomatis ikut menyalakan `opensearch` karena `api` punya `depends_on: opensearch` di `docker-compose.yml`. Dengan `--no-deps`, benar-benar hanya 2 container yang jalan.

Ini aman meski `api` "seharusnya" nantinya butuh OpenSearch — belum sekarang. Di titik ini (`day-2/nala` baru sampai Module 5), `/chat` belum menyentuh OpenSearch sama sekali. Nanti begitu Module 11 (`/chat/stream` jadi RAG-aware) dan Module 13 (`/upload`) selesai dibangun, kedua endpoint itu akan membungkus setiap panggilan ke OpenSearch dalam `try/except httpx.HTTPError` — kalau `opensearch` tidak jalan, koneksi gagal secara terkontrol dan otomatis fallback (mode tanpa-konteks untuk chat, "tersimpan tapi belum ter-index" untuk upload), bukan crash. Lihat Module 11 Bagian 2 Langkah 3 dan Module 13 Bagian 2 Tahap B untuk penjelasan desainnya begitu Anda sampai di situ.

Tunggu sampai log `api` menunjukkan `Uvicorn running on http://0.0.0.0:8000`. Prosesnya jauh lebih cepat dari menyalakan keempat service sekaligus, karena tidak perlu menunggu inisialisasi cluster OpenSearch atau database metadata Airflow.

## Langkah 3: Pull model untuk chat (di terminal baru)

Sama seperti Module 1-4, Ollama di dalam container punya storage terpisah — model perlu di-pull ulang khusus untuk container ini. Di titik ini kita baru butuh **satu model**: `llama3.2:3b` untuk chat/generation. Model untuk embedding (`nomic-embed-text`) belum dibutuhkan — itu baru dipakai mulai Module 9, jadi baru kita pull nanti di Module 9 Langkah 1 (bukan sekarang, supaya jelas step mana yang butuh apa).

Buka **terminal baru** (biarkan terminal Langkah 2 tetap berjalan), masuk ke folder yang sama (`resources/starter-code/day-2/nala`), lalu:

```bash
docker compose exec ollama ollama pull llama3.2:3b
```

⚠️ Tag `:3b` wajib ditulis persis — harus sama dengan `OLLAMA_MODEL` di `docker-compose.yml`.

Verifikasi model sudah ada:

```bash
docker compose exec ollama ollama list
```

`llama3.2:3b` harus muncul di daftar.

## Langkah 4: Coba chat dulu lewat `/chat`, sebelum ada dokumen

Sebelum menyentuh dokumen sama sekali, buka `http://localhost:8000` di browser — ini halaman chat (`chat.html`) versi paling sederhana, memakai endpoint `/chat` (kirim satu pesan, tunggu, terima satu balasan utuh). Coba kirim pesan apa saja, misalnya:

> "Halo, kamu siapa?"

NALA akan tetap membalas — koneksi UI → FastAPI → Ollama sudah bekerja — tapi jawabannya generik karena belum ada dokumen internal untuk dirujuk sama sekali (belum ada RAG di titik ini). Tujuannya memverifikasi dulu bahwa fondasi chat sudah jalan, sebelum lapisan streaming (Module 6) dan RAG (Module 8-14) ditambahkan di atasnya.

⚠️ **`/chat` di langkah ini bersifat sementara** — Module 6 Langkah 1 akan **menghapus total** endpoint ini dan menggantikannya dengan `/chat/stream`. Sengaja dibangun dulu di sini supaya fondasi (Docker, network, model) terverifikasi dengan kontrak paling sederhana, sebelum kompleksitas streaming ditambahkan.

Kalau ingin memverifikasi lewat `curl` juga bisa, response-nya tetap `{"reply": "..."}` seperti Module 1-4:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Halo, kamu siapa?"}'
```

## Troubleshooting

- **`no configuration file provided: not found`**: `docker compose` dijalankan bukan dari folder yang berisi `docker-compose.yml`. Pastikan Anda berada persis di `resources/starter-code/day-2/nala/` (cek dengan `ls`).
- **`failed to read dockerfile: open Dockerfile: no such file or directory`**: nama file salah — harus persis `Dockerfile`. Cek dengan `ls` dan rename kalau perlu: `mv DockerFile Dockerfile`.
- **`Internal Server Error` saat chat**: cek dulu model Ollama sudah ter-pull (`docker compose exec ollama ollama list`) — di titik ini baru `llama3.2:3b` (Langkah 3) yang dibutuhkan. Detail traceback Python bisa dilihat di log container `api` (terminal yang menjalankan Langkah 2).
- **Port sudah dipakai (8000/11434)**: ubah mapping port di `docker-compose.yml` untuk service yang bentrok (misal `8001:8000`).
- **Semua service terasa sangat lambat / laptop panas / container ter-*kill***: kemungkinan besar alokasi RAM Docker Desktop kurang — lihat bagian Prasyarat di atas. Cek pemakaian resource real-time dengan `docker stats`. Beban RAM di module ini masih ringan (cuma `ollama`+`api`); ini jadi penting begitu `opensearch` (Module 10) dan `airflow` (Module 14) ikut menyala.
