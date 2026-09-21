# Panduan Praktik — Module 18: Observability & Tracing dengan Langfuse

## Prasyarat
- Sudah menyelesaikan **Module 17** — `resources/starter-code/day-3/nala/` sudah punya framework evaluasi bekerja
- Docker Desktop dinaikkan lagi alokasi RAM-nya untuk menampung dua service baru:

| Setting | Minimal | Direkomendasikan | Alasan |
|---|---|---|---|
| **Memory (RAM)** | 16 GB | 20 GB+ jika tersedia | Semua service sebelumnya (Ollama, OpenSearch, Airflow, api dengan reranker) + Langfuse & Postgres-nya (`langfuse-db`, terpisah dari Postgres data operasional yang baru akan muncul di Module 19) berjalan bersamaan di titik puncak. |
| **Disk image size** | 100 GB | 120 GB+ | Image `langfuse/langfuse` menambah beberapa GB lagi di atas image sebelumnya. |

Kalau laptop mulai terasa berat, pertimbangkan mematikan sementara `airflow` (tidak dipakai lagi setelah ingest, lihat Langkah 6 di bawah).

## Langkah 1: Nyalakan Langfuse

Ikuti Module 18 Bagian 4 Tahap A Langkah 1: tambah service `langfuse-db` dan `langfuse` di `docker-compose.yml`.

```bash
cd resources/starter-code/day-3/nala
docker compose up -d --build langfuse-db langfuse
```

**Proses ini akan terasa lama** — Langfuse perlu migrasi skema database saat pertama kali jalan.

```bash
docker compose logs -f langfuse
```

Tunggu sampai log menunjukkan service siap menerima koneksi, lalu `Ctrl+C`.

## Langkah 2: Buat akun, Project, dan API key Langfuse

Ikuti Module 18 Bagian 4 Langkah 2:

1. Buka `http://localhost:3000`, buat akun lokal (email + password apa saja).
2. Buat Project baru, misalnya "NALA Observability".
3. Di halaman Settings project, salin **Public Key** dan **Secret Key**.
4. Tambahkan `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST=http://langfuse:3000` ke environment service `api` di `docker-compose.yml`.

```bash
docker compose up --build -d api
```

## Langkah 3: Instrumentasi `/chat/stream`

Ikuti Module 18 Bagian 4 Tahap B Langkah 3-4 — perhatikan baik-baik penjelasan di sana tentang kenapa `generation` (pemanggilan LLM) harus ditutup **di dalam generator**, bukan di badan fungsi endpoint, sementara span `hybrid_search`/`rerank` tetap bisa dibuka/ditutup langsung di badan `chat_stream()`.

```bash
docker compose up --build api
```

```bash
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Apa saja syarat pengajuan kredit untuk nasabah perorangan?"}]}'
```

✅ **Indikator sukses**: endpoint tetap berfungsi seperti sebelumnya (tidak ada perubahan perilaku dari sisi user), dan trace baru muncul di `http://localhost:3000` halaman Traces **setelah** stream selesai diterima.

## Langkah 4: Telusuri trace di UI Langfuse

Buka trace yang baru dibuat di Langkah 3, klik untuk membuka detail. Verifikasi span `hybrid_search`, `rerank`, dan generation `llm_generate_stream` tersusun bersarang dengan `input`/`output` yang masuk akal, dan perhatikan durasi tiap span. Ikuti alur diagnosis lengkap di Module 18 Bagian 5 sebagai latihan.

## Langkah 5: Uji fallback tetap tercatat

```bash
docker compose stop opensearch
```

```bash
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Apa saja syarat pengajuan kredit?"}]}'
```

✅ **Indikator sukses**: `/chat/stream` tetap membalas (fallback `NALA_SYSTEM_PROMPT_NO_CONTEXT`, jawaban generik) — bukan error 500 — dan trace baru tetap muncul di Langfuse, dengan `level="ERROR"` tercatat di trace tersebut. Nyalakan lagi OpenSearch setelahnya:

```bash
docker compose start opensearch
```

## Langkah 6: (Opsional) Matikan Airflow sementara kalau laptop terasa berat

```bash
docker compose stop airflow
```

Airflow tidak dipakai lagi setelah ingest dokumen awal selesai — mematikannya sementara selama eksplorasi Module 17-18 membebaskan RAM untuk reranker dan Langfuse tanpa mengganggu `/chat/stream`, yang tidak bergantung pada Airflow sama sekali. Nyalakan lagi (`docker compose up -d airflow`) kapan pun dibutuhkan lagi (misalnya untuk ingest dokumen baru).

## Troubleshooting

- **`langfuse` container gagal start / `langfuse-db` connection refused**: `langfuse` butuh `langfuse-db` sudah siap menerima koneksi sebelum migrasi database berhasil — tunggu beberapa saat lebih lama, atau restart `langfuse` saja setelah `langfuse-db` benar-benar `healthy`: `docker compose restart langfuse`.
- **Trace tidak muncul sama sekali di UI Langfuse**: cek `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY`/`LANGFUSE_HOST` di environment service `api` — key yang salah biasanya gagal secara diam-diam (SDK Langfuse dirancang tidak mengganggu aplikasi utama kalau pengiriman trace gagal). Cek juga apakah `langfuse_client.flush()` benar-benar terpanggil di dalam `traced_chat_stream()` (Module 18 Bagian 4).
- **Trace `chat_stream` tidak pernah muncul, walau curl berhasil menerima seluruh stream**: kemungkinan besar instrumentasi masih ditulis di badan fungsi `chat_stream()` setelah baris `return StreamingResponse(...)` (baris itu tidak akan pernah tereksekusi tepat waktu) — pastikan `trace.update()`/`flush()` ada di dalam `traced_chat_stream()` (generator terpisah), bukan di `chat_stream()` sendiri. Lihat penjelasan lengkap Module 18 Bagian 4 Tahap B.
- **Semua service terasa sangat lambat / laptop panas / container ter-*kill***: alokasi RAM Docker Desktop kurang — lihat bagian Prasyarat di atas, naikkan ke 20GB+ kalau tersedia, atau matikan sementara `airflow` (Langkah 6) selama eksplorasi berlangsung.
- **Port sudah dipakai (3000/8000/9200/11434)**: ubah mapping port yang bentrok di `docker-compose.yml`, atau pastikan container lama sudah benar-benar dimatikan (`docker compose down` di `resources/starter-code/day-2/nala`).
