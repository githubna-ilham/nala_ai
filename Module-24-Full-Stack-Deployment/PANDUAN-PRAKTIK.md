# Panduan Praktik — Module 24: Full-Stack Deployment via Docker Compose

## Sebelum Mulai: Module 24 Tidak Punya Folder Referensi Baru

Berbeda dari Module 1-23, Module 24 **tidak** menyediakan `resources/starter-code/day-5-reference/nala/` — folder kerja Module 24 (`resources/starter-code/day-5/nala/`) dibangun langsung di atas hasil kerja Module 23 Anda sendiri (`resources/starter-code/day-4/nala/`), bukan disalin dari jawaban jadi. Panduan ini membangunnya bertahap, module demi module, sama seperti panduan praktik Module 5-14.

## Prasyarat

- Module 1-23 sudah selesai — RAG hybrid search (Module 15-18), agent LangGraph dengan RAG+SQL tool routing dan RBAC/audit logging (Module 19-23) sudah berjalan di `resources/starter-code/day-4/nala/`.
- Docker Desktop dialokasikan **16GB+ RAM** — lihat catatan resource lengkap di Module 24 Bagian 4. Module 24 adalah titik terberat seluruh training: sembilan container berjalan bersamaan di puncaknya.
- `openssl` tersedia di terminal (dipakai untuk generate secret acak di Langkah 2) — sudah terpasang default di macOS/Linux; pengguna Windows tanpa WSL bisa memakai `python -c "import secrets; print(secrets.token_hex(32))"` sebagai gantinya.

### Container Module 19-23 tetap dipakai — bukan project terpisah

Konsisten dengan transisi antar rentang module sebelumnya: folder `day-N/nala` semuanya bernama `nala`, jadi Docker Compose (yang memakai nama folder sebagai *project name* default) memperlakukan semuanya sebagai **satu project yang sama** — disengaja, supaya `ollama`/`opensearch`/`airflow`/dst tidak berjalan berkali-kali lipat (hemat RAM) dan data yang sudah ada (index OpenSearch, data PostgreSQL, model Ollama) otomatis ikut terbawa ke Module 24, tidak perlu diulang dari nol.

Setelah `day-5/nala/docker-compose.yml` dibangun (Langkah 1 di bawah) dan dipakai, jalankan `docker compose` **dari folder `day-5/nala/`** untuk seterusnya — tidak ada langkah "matikan dulu" yang diperlukan, compose otomatis merecreate container yang definisinya berubah dan membiarkan yang lain tetap jalan. Module 24 memakai port yang sama seperti Module 15-23 (`8000` API, `11434` Ollama, `9200` OpenSearch, `8080` Airflow, `5432` Postgres, `3000` Langfuse, `5601` OpenSearch Dashboards, `8081` Adminer) — tidak ada port baru untuk Langfuse karena tetap v2 (lihat Module 24 Bagian 4a), bukan v4 yang butuh port tambahan MinIO console.

## Langkah 1: Salin `day-4/nala/` jadi `day-5/nala/`

```bash
cd resources/starter-code
cp -r day-4/nala day-5/nala
cd day-5/nala
```

Seluruh kode aplikasi (RAG, agent, RBAC) **tidak berubah** dari Module 23 — Module 24 murni menambah lapisan deployment/monitoring/frontend di atasnya.

## Langkah 2: Buat `.env` (Module 24 Tahap A)

```bash
cat > .env << 'EOF'
OLLAMA_MODEL=llama3.2:3b
EOF

echo "POSTGRES_ADMIN_PASSWORD=$(openssl rand -hex 16)" >> .env
echo "LANGFUSE_DB_PASSWORD=$(openssl rand -hex 16)" >> .env
echo "LANGFUSE_NEXTAUTH_SECRET=$(openssl rand -hex 32)" >> .env
echo "LANGFUSE_SALT=$(openssl rand -hex 32)" >> .env
# LANGFUSE_PUBLIC_KEY/LANGFUSE_SECRET_KEY: tambahkan manual ke .env,
# disalin dari project Langfuse Anda sendiri (Module 18) — bukan
# digenerate acak.

echo ".env" >> .gitignore
```

⚠️ Kurikulum ini memakai Langfuse **v2** (monolitik, satu `langfuse-db` sendiri) — lihat Module 24 Bagian 2 Tahap A dan Bagian 4a untuk alasannya. Jangan menambah variabel `LANGFUSE_CLICKHOUSE_PASSWORD`/`LANGFUSE_REDIS_PASSWORD`/`LANGFUSE_MINIO_ROOT_*`/`LANGFUSE_ENCRYPTION_KEY` — itu untuk Langfuse v4 (ClickHouse/Redis/MinIO/worker) yang **tidak** dipakai di sini.

Verifikasi tidak ada secret kosong:

```bash
cat .env
```

Semua baris harus punya value setelah `=` — kalau ada yang kosong (kemungkinan `openssl` gagal dijalankan), isi manual dengan string acak sebelum lanjut.

## Langkah 3: Tulis `docker-compose.yml` final (Module 24 Tahap B-C)

Ikuti **Module 24 Bagian 2 Langkah 4-6** untuk menulis `docker-compose.yml` lengkap (healthcheck, `condition: service_healthy`, semua service termasuk Langfuse). Simpan sebagai `resources/starter-code/day-5/nala/docker-compose.yml`, menggantikan yang disalin dari Module 23.

## Langkah 4: Startup bertahap — jangan `docker compose up` semuanya sekaligus

Ikuti urutan ini (bukan satu perintah besar) — alasannya ada di Module 24 Bagian 3-4:

**4a. Lapisan dasar**

```bash
docker compose up -d ollama postgres opensearch langfuse-db
```

Pantau sampai semuanya `healthy`:

```bash
watch docker compose ps
```

(Kalau `watch` tidak tersedia, ulangi `docker compose ps` manual tiap 15-30 detik.) Ini bisa memakan beberapa menit — OpenSearch paling lama, konsisten dengan pengalaman Module 5-14.

**4b. Model Ollama** (kalau `ollama_data` volume Module 24 baru/kosong — cek dulu dengan `docker compose exec ollama ollama list`, model dari Module 1-23 bisa saja sudah tersimpan di volume yang sama kalau nama volume tidak berubah)

```bash
docker compose exec ollama ollama pull llama3.2:3b
docker compose exec ollama ollama pull nomic-embed-text
```

**4c. Lapisan menengah** (paralel, tidak saling bergantung satu sama lain)

```bash
docker compose up -d opensearch-dashboards airflow adminer
```

Airflow tetap butuh dipantau manual (tidak ada healthcheck, lihat Module 24 Bagian 2 Tahap B):

```bash
docker compose logs -f airflow
```

Tunggu sampai muncul password admin dan indikasi webserver listen, lalu `Ctrl+C`.

**4d. Lapisan aplikasi**

```bash
docker compose up -d api langfuse
```

## Langkah 5: Verifikasi semua service hidup

```bash
docker compose ps
```

Semua baris `STATUS` harus `Up` (yang punya healthcheck: `(healthy)`). Buka satu per satu di browser:

- `http://localhost:8000` — Chat NALA
- `http://localhost:8000/upload` — Knowledge base
- `http://localhost:8000/status/view` — Status page (Module 25)
- `http://localhost:3000` — Langfuse (setup akun admin pertama kali diminta di sini)
- `http://localhost:8080` — Airflow
- `http://localhost:5601` — OpenSearch Dashboards

## Langkah 6: Coba end-to-end — RAG dan SQL tool sekaligus

Kirim dua jenis pertanyaan ke `http://localhost:8000` untuk memverifikasi routing agent Module 19-23 masih bekerja di stack gabungan ini:

1. Pertanyaan dokumen SOP (RAG): *"Apa saja syarat pengajuan kredit untuk nasabah perorangan?"*
2. Pertanyaan data operasional (SQL tool): sesuaikan dengan data dummy Module 19-23 Anda, misalnya *"Berapa banyak pengajuan kredit yang statusnya masih diproses?"*

Amati badge tool (Module 26) muncul sesuai jenis pertanyaan, dan cek trace-nya muncul di dashboard Langfuse (`http://localhost:3000`).

Setelah stack ini jalan dan diverifikasi, lanjutkan ke panduan praktik **Module 25** (`../Module-25-Monitoring-Security-Checklist/PANDUAN-PRAKTIK.md`) untuk menambahkan status page dan menjalankan checklist keamanan.

## Troubleshooting

- **Laptop sangat lambat / container ter-*kill* / Docker Desktop crash**: ini kemungkinan besar RAM tidak cukup untuk menjalankan sembilan container sekaligus. Ikuti saran Module 24 Bagian 4: matikan sementara stack Langfuse (`docker compose stop langfuse langfuse-db`) selama latihan Module 24 dan Module 26, nyalakan lagi khusus saat giliran Module 25 atau demo capstone yang perlu menunjukkan dashboard.
- **`langfuse` terus `Restarting` / error koneksi database (`Error: P1000: Authentication failed`) saat startup**: dua kemungkinan — (1) `langfuse-db` belum benar-benar `healthy` saat `langfuse` mencoba connect, cek `docker compose ps langfuse-db` dan tunggu; (2) **lebih sering terjadi kalau melanjutkan dari volume Module 15-23 yang sudah ada** — password di `.env` tidak otomatis jadi password sungguhan di database yang sudah pernah di-init (lihat Module 24 Bagian 4a "Gotcha Rotasi Password" untuk penjelasan lengkap + cara fix pakai `ALTER USER`).
- **Password baru di `.env` tidak berfungsi setelah `docker compose up` ulang** (untuk `postgres` ATAU `langfuse-db`): ini bukan bug — PostgreSQL cuma menerapkan `POSTGRES_PASSWORD` saat volume data masih kosong, bukan tiap restart. Kalau melanjutkan dari volume yang sudah ada isinya (skenario umum di Module 24 karena project Docker Compose dipakai bersama sejak Module 15-23), jalankan `ALTER USER <role> PASSWORD '<value baru>';` manual lewat `psql` di masing-masing database, baru `docker compose restart <service>`. Detail lengkap dan contoh perintah ada di Module 24 Bagian 4a.
- **Port `3000`/`5601`/`8081` sudah dipakai**: ubah mapping port service yang bentrok di `docker-compose.yml` (misal `3001:3000` untuk Langfuse) — aplikasi lain di laptop (dev server Node.js umum memakai `3000`) sering memakai port ini juga.
- **`OpenSearch`/`vm.max_map_count`, password admin Airflow hilang, `no configuration file provided`, dsb.**: sama persis dengan troubleshooting panduan praktik Module 5-14 — service-service ini tidak berubah perilakunya di Module 24, cuma dijalankan bersamaan dengan lebih banyak service lain. Rujuk bagian Troubleshooting panduan praktik Module 5-14 untuk keduanya.
