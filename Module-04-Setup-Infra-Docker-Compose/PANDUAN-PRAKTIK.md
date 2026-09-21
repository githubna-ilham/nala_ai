# Panduan Praktik — Module 4: Setup Infra Docker Compose

## Prasyarat
- Docker Desktop sudah terinstall dan berjalan
- Minimal 16GB RAM tersedia
- Docker Desktop sudah dialokasikan resource yang cukup (lihat Langkah 0 di bawah)
- Sudah menyelesaikan Module 3 (Prompt Engineering Dasar) — Langkah 7 di bawah menggunakan system prompt yang disusun di sana

## Langkah 0: Atur RAM & Storage Docker Desktop

Secara default, Docker Desktop **tidak otomatis memakai semua resource laptop Anda** — ada batas RAM, CPU, dan disk yang dialokasikan sendiri, terpisah dari sisa laptop. Kalau batas ini terlalu kecil, container bisa lambat, gagal start, atau ke-*kill* otomatis (biasanya errornya "Killed" atau container tiba-tiba restart) — terutama untuk Ollama yang butuh RAM cukup besar untuk memuat model.

**Cara mengecek/mengubah (macOS & Windows):**

1. Buka aplikasi **Docker Desktop**
2. Klik ikon **⚙️ Settings** (gear icon, biasanya di kanan atas)
3. Masuk ke tab **Resources**

**Pengaturan yang direkomendasikan untuk NALA:**

| Setting | Minimal | Direkomendasikan | Alasan |
|---|---|---|---|
| **Memory (RAM)** | 8 GB | 12–16 GB | `llama3.2:3b` butuh ~4-6GB saat dimuat; sisanya untuk FastAPI, OS container, dan buffer. Modul-modul selanjutnya (Module 15 dst.) nanti menambah OpenSearch/PostgreSQL yang juga butuh RAM. |
| **CPUs** | 2 | 4+ | Inference LLM cukup CPU-intensive kalau tidak pakai GPU. |
| **Disk image size** | 60 GB | 100 GB+ | Setiap image Docker (Python, Ollama, nanti OpenSearch/Airflow/PostgreSQL) + model Ollama (~2GB per model) menumpuk seiring modul training berjalan. |
| **Swap** | 1 GB | 2 GB | Buffer tambahan kalau Memory limit sempat mepet. |

Setelah mengubah, klik **Apply & Restart** — Docker Desktop akan restart untuk menerapkan setting baru (container yang sedang jalan akan ikut berhenti, jalankan ulang `docker compose up --build` setelahnya).

**Kalau disk mulai penuh** (sering terjadi setelah beberapa modul training karena image/model menumpuk), bersihkan yang tidak terpakai:

```bash
docker system prune -a --volumes
```

⚠️ Perintah ini menghapus **semua** container, image, dan volume yang tidak sedang dipakai — termasuk model Ollama yang sudah di-pull (harus di-pull ulang setelahnya). Jangan jalankan sembarangan kalau ada project Docker lain di laptop yang sama yang masih dibutuhkan.

**Cek pemakaian resource real-time** (container mana yang paling banyak makan RAM/CPU):

```bash
docker stats
```

## Langkah 1: Clone & masuk ke folder starter code

```bash
cd resources/starter-code/day-1/nala
```

## Bagian A — Ollama Sendirian Dulu (belum ada FastAPI)

Prinsipnya: pastikan fondasi (Ollama di Docker) benar-benar sehat **sebelum** menambahkan kompleksitas kedua (FastAPI). Kalau Bagian A gagal, jangan lanjut ke Bagian B — debug di sini dulu, karena mustahil membedakan "Ollama-nya yang bermasalah" vs "FastAPI-nya yang bermasalah" kalau keduanya dinyalakan bersamaan sejak awal.

## Langkah 2: Nyalakan service `ollama` saja

Pastikan `docker-compose.yml` Anda di titik ini **baru** berisi service `ollama` (lihat `materi.md` section 3.3 — belum ada `api`):

```bash
docker compose up -d ollama
```

`-d` menjalankan di background. Cek statusnya:

```bash
docker compose ps
```

Kolom status `ollama` harus `running`/`Up`, bukan `Exited` atau `Restarting`.

## Langkah 3: Pull & verifikasi model di dalam container

Ollama yang berjalan **di dalam container** punya storage terpisah dari Ollama yang mungkin sudah terinstall langsung di laptop Anda (lihat Module 2) — jadi modelnya perlu di-pull lagi khusus untuk container ini (sekali saja; tersimpan permanen di volume `ollama_data` selama volume tidak dihapus).

```bash
docker compose exec ollama ollama pull llama3.2:3b
```

⚠️ Tag `:3b` **wajib** ditulis persis seperti di atas — harus sama dengan `OLLAMA_MODEL` yang akan dipakai service `api` nanti. Kalau Anda pull `llama3.2` tanpa tag, aplikasi tetap bisa gagal mencari model `llama3.2:3b` walau terlihat "mirip".

Verifikasi model sudah ada, **dari dua sisi**:

```bash
docker compose exec ollama ollama list
curl http://localhost:11434/api/tags
```

`llama3.2:3b` harus muncul di kedua output — yang pertama dari **dalam** container, yang kedua dari **luar** container (lewat port `11434` yang sudah di-mapping ke laptop Anda).

✅ **Checkpoint "aman" — jangan lanjut ke Bagian B kalau salah satu berikut belum terpenuhi:**
- [ ] `docker compose ps` menunjukkan `ollama` berstatus `running`
- [ ] `docker compose exec ollama ollama list` menampilkan `llama3.2:3b`
- [ ] `curl http://localhost:11434/api/tags` dari luar container berhasil dan menampilkan `llama3.2:3b`

Biarkan container `ollama` tetap berjalan (tidak perlu `docker compose down`) — Bagian B akan menambahkan service `api` ke `docker-compose.yml` yang sama.

## Bagian B — Tambahkan Service `api` (FastAPI)

Ollama sudah terverifikasi sehat di Bagian A. Sekarang service `api` ditambahkan ke `docker-compose.yml` yang sama (lihat `materi.md` Tahap B untuk penjelasan lengkap blok `api` — `build: .`, `environment`, `depends_on`), dan kode `app/main.py` dibangun bertahap mengikuti `materi.md` section 5 Tahap A-C.

## Langkah 4: Jalankan seluruh service

```bash
docker compose up --build
```

Tunggu sampai log menunjukkan `Uvicorn running on http://0.0.0.0:8000`. Container `ollama` yang sudah berjalan sejak Langkah 2 langsung dipakai apa adanya (tidak dibuat ulang dari nol) — yang di-*build* dan dinyalakan di sini cuma `api`. Kalau log menunjukkan `ollama` langsung "Up" tanpa proses pull image, itu perilaku normal, bukan error.

## Langkah 5: Cek health check

```bash
curl http://localhost:8000/health
```

Harus mengembalikan: `{"status":"ok"}`

## Langkah 6: Coba chat dengan NALA

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Halo, kamu siapa?"}'
```

Model `llama3.2:3b` **tidak perlu** di-pull ulang di sini — sudah dilakukan di Langkah 3, dan tersimpan permanen di volume `ollama_data`. NALA harus merespons sesuai system prompt yang sudah dipelajari di Module 3.

## Langkah 7: Eksperimen system prompt

Buka `app/system_prompt.py`, ubah `NALA_SYSTEM_PROMPT` sesuai hasil latihan Module 3, lalu build ulang (⚠️ `restart` saja **tidak cukup** — kode di-`COPY` ke image cuma sekali saat `build`, `docker-compose.yml` tidak mem-*mount* folder `app/`, jadi container tidak otomatis membaca perubahan file):

```bash
docker compose up --build api
```

Ulangi Langkah 6 dan bandingkan hasilnya.

## Troubleshooting

- **Container `ollama` berstatus `Exited`/`Restarting` di Langkah 2 (Bagian A, belum ada `api` sama sekali)**: cek log-nya duluan — `docker compose logs ollama`. Penyebab paling umum: RAM Docker Desktop tidak cukup (lihat Langkah 0) atau port `11434` sudah dipakai proses lain di laptop Anda (misal Ollama versi native dari Module 2 masih berjalan langsung di laptop — matikan dulu, lihat Module 2 section 2.1, sebelum menjalankan versi container-nya).
- **`no configuration file provided: not found`**: `docker compose` dijalankan bukan dari folder yang berisi `docker-compose.yml`. Pastikan Anda berada persis di `resources/starter-code/day-1/nala/` (cek dengan `ls` — harus ada `docker-compose.yml`).
- **`failed to read dockerfile: open Dockerfile: no such file or directory`**: nama file salah — harus persis `Dockerfile` (huruf besar hanya di "D"). Kalau Anda beri nama lain seperti `DockerFile` atau `dockerfile`, Docker tidak akan menemukannya walau terlihat mirip di Finder/Explorer. Cek dengan `ls` dan rename kalau perlu: `mv DockerFile Dockerfile`.
- **`failed to compute cache key: ... "/app": not found`**: normal terjadi **sebelum** folder `app/` (kode Python NALA) dibuat. Kalau Anda mengikuti urutan Task 9 → Task 10, error ini akan muncul dulu saat baru selesai Task 9 — itu tandanya semua langkah sebelumnya sudah benar, tinggal lanjut membuat folder `app/`.
- **`curl: (7) Failed to connect`**: pastikan `docker compose up` masih berjalan dan tidak ada error di log.
- **`Internal Server Error` saat POST `/chat`**: hampir selalu berarti Ollama di dalam container **belum punya model** `llama3.2:3b` (lihat Langkah 3) — bukan error di kode FastAPI-nya. Cek dengan `docker compose exec ollama ollama list`; kalau `llama3.2:3b` tidak muncul, jalankan ulang Langkah 3. Detail error Python-nya (traceback) selalu bisa dilihat di terminal yang menjalankan Langkah 4 (log container `api`).
- **Ollama lambat merespons pertama kali**: wajar, model sedang dimuat ke memori. Percobaan kedua akan lebih cepat.
- **Port 8000 sudah dipakai**: ubah mapping port di `docker-compose.yml` (misal `8001:8000`).
