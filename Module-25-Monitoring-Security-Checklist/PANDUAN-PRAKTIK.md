# Panduan Praktik — Module 25: Dashboard Monitoring & Security Review Checklist

## Prasyarat

- Module 24 sudah selesai — seluruh stack (`ollama`, `api`, `opensearch`, `opensearch-dashboards`, `airflow`, `postgres`, `adminer`, `langfuse`, `langfuse-db`) sudah jalan lewat `docker compose up -d` di `resources/starter-code/day-5/nala/`, mengikuti `../Module-24-Full-Stack-Deployment/PANDUAN-PRAKTIK.md`.
- Kalau Anda mematikan Langfuse sementara untuk menghemat RAM (lihat troubleshooting Module 24), nyalakan lagi sekarang sebelum lanjut — bukan pull/start dari awal:

```bash
docker compose start langfuse langfuse-db
```

## Langkah 1: Implementasikan endpoint `/status` dan `/status/view`

Ikuti Langkah 1-2 di `../Module-25-Monitoring-Security-Checklist/materi.md` Bagian 2.b untuk menambahkan fungsi `system_status()`, endpoint `GET /status`, dan halaman `status.html`.

Setiap kali mengubah `app/main.py` atau file di `app/`, rebuild `api` saja (bukan seluruh stack):

```bash
docker compose up -d --build api
```

## Langkah 2: Verifikasi status page

```bash
curl http://localhost:8000/status
```

Lalu buka `http://localhost:8000/status/view` di browser. Coba matikan salah satu service (`docker compose stop opensearch`) dan refresh — `opensearch` di `/status` harus berubah jadi `unreachable`, bukan hang atau error 500 di endpoint `/status` itu sendiri. Nyalakan lagi setelahnya:

```bash
docker compose start opensearch
```

✅ **Indikator sukses**: `/status` selalu mengembalikan `200 OK` dengan JSON yang menyebutkan status tiap service, tidak pernah crash walau salah satu/semua service down. `/status/view` menampilkan halaman yang sama secara visual, auto-refresh.

## Langkah 3: Review Dashboard Langfuse

Kirim beberapa pertanyaan ke `http://localhost:8000` (RAG dan SQL tool), lalu buka `http://localhost:3000` dan cek trace-nya muncul — latency per trace, tool yang dipilih agent, dan trace error kalau ada. Lihat `materi.md` Bagian 2.a untuk daftar lengkap yang perlu dicek rutin.

## Langkah 4: Checklist Review Keamanan

Bersama kelompok/instruktur, bahas checklist keamanan di `materi.md` Bagian 3 (Secrets & Credentials, RBAC & Audit Logging, Prompt Injection, Rate Limiting, Data Retention). Untuk tiap poin, catat status jujur: **sudah diatasi**, **sebagian diatasi**, atau **secara eksplisit di luar cakupan** — jangan menandai selesai kalau belum benar-benar diverifikasi.

Pastikan poin Checkpoint Praktik (`materi.md` Bagian 4) terpenuhi sebelum lanjut ke panduan praktik **Module 26** (`../Module-26-Polish-Frontend-Demo/PANDUAN-PRAKTIK.md`).

## Troubleshooting

- **`/status` selalu melaporkan `postgres: unreachable` padahal `docker compose ps` bilang `healthy`**: cek `DATABASE_URL`/koneksi SQLAlchemy (atau `get_connection()` psycopg) yang dipakai `system_status()` memakai host `postgres` (nama service di Docker network), bukan `localhost` — dari dalam container `api`, `localhost` merujuk ke container itu sendiri, bukan container `postgres`.
- **Dashboard Langfuse tidak menampilkan trace baru**: cek `LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` di environment `api` sudah benar dan mengarah ke instance Langfuse yang sama dengan yang dibuka di browser — gejala umum kalau `.env` sempat diregenerasi ulang tanpa update key project Langfuse.
