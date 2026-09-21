# Panduan Praktik — Module 23: RBAC & Audit Logging

Lanjutan langsung dari `PANDUAN-PRAKTIK.md` Module 22 — agent dengan routing dua-tool dan pengaman `MAX_TOOL_ROUNDS`/`force_answer` harus sudah jalan sebelum mulai di sini. Penomoran Langkah melanjutkan penomoran global (Module 19: Langkah 1-5, Module 20: Langkah 6-10, Module 21: Langkah 11-13, Module 22: Langkah 14-16). Ini adalah panduan praktik terakhir dari rangkaian Module 19-23.

## Prasyarat
- Module 22 selesai: routing RAG/SQL sudah diuji, `MAX_TOOL_ROUNDS`/`force_answer` sudah terpasang.

## Langkah 17: Tabel `audit_log`, role `nala_app` (Module 23 Tahap A)

Ikuti Module 23 Bagian 3 Tahap A Langkah 1.

```bash
docker compose down
docker volume rm nala_postgres_data 2>/dev/null || true
docker compose up -d --build postgres
docker compose logs -f postgres
```

⚠️ **Perhatian**: reset volume ini menghapus **semua** data operasional yang sudah dimasukkan lewat form di Module 19 Langkah 5 — database kembali ke seed minimal (2 baris `pengajuan_kredit` + 1 baris `klaim_asuransi`). Ini perlu dilakukan supaya `db/seed.sql` yang baru saja ditambah tabel `audit_log` + role `nala_app` (Module 23 Tahap A) ter-*load* ulang (lihat catatan "Seed data tidak berubah setelah mengedit `db/seed.sql`" di Troubleshooting). Setelah Langkah 17-19 selesai, **ulangi Module 19 Langkah 5** (isi ulang lewat `/data-operasional` sampai `7` baris `pengajuan_kredit` dan `4` baris `klaim_asuransi`, termasuk `N-00231` `pending` dan `N-00305` `ditolak`) **sebelum** menjalankan uji Langkah 20-21 — kalau tidak, jawaban `/chat` di Langkah 20-21 tidak akan cocok dengan indikator sukses yang tercantum di sana.

```bash
docker compose exec postgres psql -U nala_app -d nala_operasional -c \
  "INSERT INTO audit_log (user_id, role, pertanyaan, tool_dipanggil, akses_diizinkan) VALUES ('test-user', 'staff_umum', 'tes manual', NULL, true);"
docker compose exec postgres psql -U nala_app -d nala_operasional -c "DELETE FROM audit_log WHERE id = 1;"
```

✅ **Indikator sukses**: `INSERT` berhasil, `DELETE` gagal dengan `permission denied`.

## Langkah 18: Fungsi `log_audit()` (Module 23 Tahap B)

Ikuti Module 23 Bagian 3 Tahap B Langkah 2. Ingat menambahkan/override `POSTGRES_APP_DSN` di `docker-compose.yml` (service `api`) memakai host `postgres` (bukan `localhost`), sama seperti catatan Langkah 3 di Module 19.

```bash
docker compose up --build api
docker compose exec api python -c "
from app.audit import log_audit
log_audit(user_id='test-user', role='staff_umum', pertanyaan='tes fungsi', tool_dipanggil=None, akses_diizinkan=True)
print('selesai')
"
docker compose exec postgres psql -U nala_admin -d nala_operasional -c "SELECT * FROM audit_log;"
```

✅ **Indikator sukses**: baris baru muncul di `audit_log`.

## Langkah 19: RBAC di agent (Module 23 Tahap C)

Ikuti Module 23 Bagian 3 Tahap C Langkah 3.

```bash
docker compose up --build api
```

✅ **Indikator sukses**: `Uvicorn running` tanpa traceback — belum ada endpoint yang mengirim `role` di titik ini.

## Langkah 20: Sambungkan ke `/chat`, uji role ditolak (Module 23 Tahap D)

Ikuti Module 23 Bagian 3 Tahap D Langkah 4.

⚠️ Pastikan data operasional sudah diisi ulang sesuai catatan Langkah 17 (`7` baris `pengajuan_kredit`, `4` baris `klaim_asuransi`) sebelum menjalankan uji di bawah — kalau belum, jumlah "pending" di jawaban tidak akan cocok dengan indikator sukses.

```bash
docker compose up --build api
```

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Berapa banyak pengajuan kredit yang statusnya pending?", "user_id": "budi.cs", "role": "staff_umum"}'
```

```bash
docker compose exec postgres psql -U nala_admin -d nala_operasional -c \
  "SELECT user_id, role, tool_dipanggil, akses_diizinkan FROM audit_log ORDER BY id DESC LIMIT 1;"
```

⚠️ **Ekspektasi awal vs kenyataan** (temuan nyata Module 23 Bagian 4, bukan cuma teori): jawabannya kemungkinan besar berupa **teks JSON mentah** (mis. `{"name": "query_data_operasional", "parameters": {...}}`), bukan kalimat penolakan yang rapi — dan baris audit terbaru kemungkinan besar menunjukkan `tool_dipanggil` **kosong** dengan `akses_diizinkan=t`, **bukan** `tool_dipanggil='query_data_operasional'`/`akses_diizinkan=f` seperti yang mungkin diasumsikan pertama kali. Ini bukan kegagalan langkah — data tetap tidak bocor (tidak ada query yang benar-benar jalan ke `pengajuan_kredit`), tapi audit trail punya gap nyata untuk kasus ini. Baca Module 23 Bagian 4 untuk penjelasan penuh kenapa ini terjadi (filter tool di `call_model` mencegah `tool_calls` asli terbentuk, sehingga `call_tool` — tempat logging izin ditulis — tidak pernah kebagian giliran).

## Langkah 21: Uji role berwenang, tarik seluruh audit trail

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Berapa banyak pengajuan kredit yang statusnya pending?", "user_id": "rina.finance", "role": "staff_finance"}'
```

```bash
docker compose exec postgres psql -U nala_admin -d nala_operasional -c \
  "SELECT waktu, user_id, role, tool_dipanggil, akses_diizinkan FROM audit_log ORDER BY waktu DESC LIMIT 10;"
```

✅ **Indikator sukses**: jawaban berisi angka yang benar, baris audit terbaru `akses_diizinkan=t`, dan riwayat 10 baris terakhir menunjukkan campuran percobaan yang diizinkan/ditolak dari Langkah 20-21. Rangkaian Module 19-23 selesai — NALA sekarang agentic dengan data operasional, RBAC, dan audit trail lengkap.

## Troubleshooting

- **`message.tool_calls` selalu kosong padahal pertanyaannya jelas butuh tool**: cek versi Ollama (`docker compose exec ollama ollama --version`) — dukungan tool-calling butuh versi yang cukup baru. Cek juga `RAG_TOOL_SCHEMA`/`SQL_TOOL_SCHEMA` terkirim dengan benar sebagai parameter `tools` di `OllamaClient.chat()` (Module 20 Bagian 3, ⚠️ catatan kejujuran teknis).
- **`psycopg.OperationalError: connection to server ... failed`**: kemungkinan besar DSN masih memakai `localhost` padahal dipanggil dari dalam container `api` — harus memakai nama service Docker Compose (`postgres`), lihat catatan di Module 19 Langkah 3 dan Langkah 18 di atas. Cek juga `postgres` sudah `healthy` (`docker compose ps`).
- **`permission denied for table ...` padahal seharusnya diizinkan**: cek role/DSN yang dipakai — tool SQL (Module 21) harus memakai `nala_readonly`, form `/data-operasional` (Module 19) harus memakai `nala_writer`, audit logging (Module 23) harus memakai `nala_app`; tertukar salah satunya akan memicu `permission denied` untuk operasi yang seharusnya sah (mis. `nala_readonly` dipakai untuk `INSERT` ke `audit_log` akan gagal, karena `nala_readonly` tidak pernah diberi `GRANT` ke tabel itu).
- **Seed data tidak berubah setelah mengedit `db/seed.sql`**: script init PostgreSQL cuma jalan sekali saat volume database masih kosong — kalau volume `postgres_data` sudah ada dari percobaan sebelumnya, `docker compose up` **tidak** menjalankan ulang seed. Hapus volume dulu (`docker compose down && docker volume rm nala_postgres_data`) lalu `docker compose up -d --build postgres` lagi. Ini juga penyebab paling umum kalau tabel/role baru "tidak muncul" setelah mengikuti Langkah 17 — ingat, reset volume juga menghapus data hasil form (lihat catatan di Langkah 17).
- **Agent tampak "menggantung" lama (timeout) untuk pertanyaan yang butuh dua tool**: wajar sampai batas tertentu — setiap putaran tool berarti minimal satu panggilan tambahan ke `llama3.2:3b` (Module 22 Bagian 1), jadi pertanyaan yang butuh dua tool berurutan otomatis lebih lambat dari pertanyaan satu-tool. Kalau benar-benar tidak pernah selesai (bukan cuma lambat), pastikan `MAX_TOOL_ROUNDS`/`force_answer` (Module 22 Bagian 5) sudah terpasang dengan benar.
- **`docker compose exec postgres psql -U nala_admin ...` minta password / gagal autentikasi**: pastikan env var `POSTGRES_ADMIN_PASSWORD` (kalau di-override di `.env` atau shell) konsisten dengan yang dipakai saat container `postgres` dibuat — kalau volume sudah lama ada dengan password lama, password baru di env var tidak otomatis berlaku sampai volume direset (sama seperti poin seed data di atas).
- **Routing tool terasa buruk terus-menerus meski sudah memperbaiki `description` (Module 22 Bagian 4.b)**: pertimbangkan opsi `qwen2.5:7b` (Module 22 Bagian 4.b Langkah 3) **hanya** kalau laptop punya RAM 32GB+ — jangan dipaksakan di laptop 16GB yang sudah menjalankan Ollama + OpenSearch + Airflow + PostgreSQL bersamaan, risiko container ter-*kill* karena kehabisan memory jauh lebih mengganggu daripada akurasi routing yang belum sempurna.
- **Error umum lain** (`no configuration file provided`, `failed to read dockerfile`, port sudah dipakai, dsb.): lihat bagian Troubleshooting `PANDUAN-PRAKTIK.md` module-module sebelumnya (Module 5-14) — penyebab dan solusinya sama, tidak spesifik rangkaian Module 19-23.

---

Untuk informasi lebih lanjut, lihat [materi Module 23](./materi.md) dan [README utama](../README.md).
