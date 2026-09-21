# Panduan Praktik — Module 19: Setup Data Operasional — PostgreSQL & UI Form

### Folder kode belum ada — Anda akan membangunnya dari salinan Module 18

Berbeda dari module-module sebelumnya yang sudah punya `resources/starter-code/day-N/nala/` siap pakai, **`resources/starter-code/day-4/nala/` belum ada** saat panduan ini ditulis (lihat Module 19 `materi.md` bagian Tujuan). Langkah 1 di bawah membangunnya dengan menyalin seluruh isi `resources/starter-code/day-3/nala/` (hybrid search, reranking, evaluasi RAG, Langfuse — dari Module 15-18), lalu module demi module (Module 19-23) di panduan-panduan berikutnya menambah lapisan data operasional/agent/tool/RBAC di atasnya — pola yang sama seperti panduan praktik Module 5 menyalin dari Module 1-4.

Karena belum ada kode referensi (`day-4-reference/`) untuk rangkaian Module 19-23, setiap kali panduan ini menyebut "kode lengkap", itu merujuk ke bagian **"📄 Kode lengkap"** di `materi.md` module terkait — bukan folder referensi terpisah seperti sebelumnya.

## Prasyarat
- Sudah menyelesaikan **Module 1-18** (`llama3.2:3b` sudah biasa dipakai, `resources/starter-code/day-3/nala/` berjalan dengan hybrid search + reranking + evaluasi + Langfuse)
- Docker Desktop sudah dialokasikan resource yang cukup — lihat catatan RAM di bawah

### Container Module 15-18 tetap dipakai — bukan project terpisah

Sama seperti transisi antar-module sebelumnya, folder `day-2/nala`, `day-3/nala`, dan `day-4/nala` semuanya bernama `nala` — Docker Compose memakai **nama folder** (bukan path lengkap) sebagai *project name* secara default, jadi ketiganya diperlakukan sebagai **project yang sama**. Ini disengaja: kalau tiap kelompok module punya project Docker terpisah, `ollama`/`opensearch`/`airflow` akan berjalan berkali-kali lipat, membengkakkan RAM tanpa perlu — satu project yang tumbuh bertahap jauh lebih hemat, dan data (index OpenSearch, model Ollama yang sudah di-pull) otomatis ikut terbawa.

Setelah `day-4/nala/docker-compose.yml` dipakai, jalankan `docker compose` **dari folder `day-4/nala/`** untuk seterusnya:

```bash
cd resources/starter-code/day-4/nala
docker compose up --build -d
```

`day-4/nala` memakai port yang sama (`8000` api, `11434` ollama, `9200` opensearch, `8080` airflow) plus port baru `5432` untuk PostgreSQL — semuanya otomatis ter-declare begitu compose dijalankan dari sini, tidak ada langkah "matikan dulu" yang diperlukan (compose merecreate container yang berubah definisinya, container lain yang tidak berubah tetap jalan apa adanya).

### Catatan penting: naikkan alokasi RAM Docker Desktop lagi

Rangkaian Module 19-23 menambahkan **satu service baru**: **PostgreSQL** (data operasional). Dibanding OpenSearch/Airflow, PostgreSQL relatif ringan sendirian — tapi ia berjalan **bersamaan** dengan seluruh stack Module 5-18 yang sudah ada (Ollama, OpenSearch, Airflow, FastAPI) plus proses LangGraph agent yang memanggil Ollama berkali-kali per pertanyaan (multi-turn tool-calling, lihat Module 20-22).

| Setting | Minimal rangkaian Module 19-23 | Direkomendasikan | Alasan |
|---|---|---|---|
| **Memory (RAM)** | 16 GB | 16 GB+ (32 GB+ kalau ingin coba `qwen2.5:7b`, lihat Module 22 Bagian 4.b) | PostgreSQL menambah beban kecil-menengah di atas stack Module 5-18 yang sudah berat; agent tool-calling memanggil Ollama beberapa kali per pertanyaan (bukan sekali seperti sebelumnya), menambah beban CPU sesaat, bukan RAM tambahan besar. |
| **CPUs** | 4 | 4+ | 5 service aktif sekaligus (ollama, opensearch, airflow, postgres, api), ditambah beberapa panggilan Ollama berurutan per request agent. |
| **Disk image size** | 100 GB | 120 GB+ | Image `postgres:16` relatif kecil (~400MB), tapi menumpuk di atas seluruh image module-module sebelumnya yang sudah ada. |

Kalau sudah di 16GB+ sejak Module 5-18, tidak perlu diubah lagi kecuali ingin mencoba `qwen2.5:7b` (Module 22 Bagian 4.b).

## Langkah 1: Salin dari Module 18, masuk ke folder starter code

```bash
cd resources/starter-code
cp -r day-3/nala day-4/nala
cd day-4/nala
```

Seluruh isi `day-3/nala/` (termasuk `app/`, `docker-compose.yml`, `requirements.txt`, dan konfigurasi hybrid search/reranking/Langfuse dari Module 15-18) ikut tersalin — rangkaian Module 19-23 **menambah** lapisan data operasional/agent/tool di atasnya, bukan menulis ulang dari nol. Verifikasi dulu fondasinya masih utuh sebelum menambah apa pun:

```bash
docker compose up --build --no-deps ollama api
```

Terminal baru, pastikan model sudah ada (kemungkinan sudah dari Module 2, tapi container storage terpisah per project):

```bash
docker compose exec ollama ollama pull llama3.2:3b
```

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Apa saja syarat pengajuan kredit untuk nasabah perorangan?"}'
```

✅ **Indikator sukses**: jawaban berbasis dokumen SOP seperti akhir Module 18 (kualitas hybrid search + reranking) — bukti salinan berjalan identik sebelum Module 19 mulai menambah apa pun.

## Langkah 2: Service PostgreSQL, skema, seed minimal, dua role (Module 19 Tahap A)

Ikuti Module 19 Bagian 3 Tahap A Langkah 1-2 (service `postgres` di `docker-compose.yml`, `db/seed.sql` — skema `pengajuan_kredit`/`klaim_asuransi`, seed minimal 2-3 baris, dan **kedua** role `nala_readonly`/`nala_writer` dibuat sejak awal, sekaligus).

```bash
docker compose up -d --build postgres
docker compose logs -f postgres
```

Tunggu sampai log menunjukkan `database system is ready to accept connections`, lalu `Ctrl+C`.

```bash
docker compose exec postgres psql -U nala_admin -d nala_operasional -c "SELECT COUNT(*) FROM pengajuan_kredit;"
docker compose exec postgres psql -U nala_admin -d nala_operasional -c "SELECT COUNT(*) FROM klaim_asuransi;"
```

✅ **Indikator sukses**: `2` dan `1` (sesuai seed minimal — lihat Module 19 Bagian 3 Tahap A Langkah 2).

Verifikasi juga pemisahan role bekerja **dua arah** (bukan cuma satu arah):

```bash
docker compose exec postgres psql -U nala_readonly -d nala_operasional -c "DELETE FROM pengajuan_kredit WHERE id = 1;"
docker compose exec postgres psql -U nala_writer -d nala_operasional -c "SELECT COUNT(*) FROM pengajuan_kredit;"
```

✅ **Indikator sukses**: **keduanya harus gagal** — `nala_readonly` ditolak `permission denied` saat `DELETE`, dan `nala_writer` **juga** ditolak `permission denied` saat `SELECT`. Kalau salah satu berhasil, cek ulang `GRANT` di `db/seed.sql` sebelum lanjut.

## Langkah 3: Koneksi database — `app/db.py` (Module 19 Tahap B Langkah 3)

Ikuti Module 19 Bagian 3 Tahap B Langkah 3 (`psycopg[binary]` di `requirements.txt`, `app/db.py` dengan dua fungsi `get_connection()`/`get_write_connection()`).

⚠️ Catatan: `POSTGRES_READONLY_DSN`/`POSTGRES_WRITER_DSN` default di `app/db.py` menunjuk `localhost` — dari dalam container `api`, tambahkan kedua env var ini di `docker-compose.yml` (service `api`) memakai host `postgres` (nama service, bukan `localhost`) sebelum menjalankan perintah di bawah.

```bash
docker compose up --build --no-deps ollama api
```

```bash
docker compose exec api python -c "
from app.db import get_connection, get_write_connection
with get_connection() as conn:
    print('readonly ok')
with get_write_connection() as conn:
    print('writer ok')
"
```

✅ **Indikator sukses**: `readonly ok` dan `writer ok` tercetak, tidak ada error.

## Langkah 4: Halaman `/data-operasional` — form + tabel daftar (Module 19 Tahap B Langkah 4-5)

Ikuti Module 19 Bagian 3 Tahap B Langkah 4-5 (`app/templates/data_operasional.html`, endpoint `GET /data-operasional` + `POST /data-operasional/pengajuan-kredit` + `POST /data-operasional/klaim-asuransi` di `app/main.py`, plus nav link baru di `chat.html`/`upload.html`).

```bash
docker compose up --build -d postgres api
```

Buka `http://localhost:8000/data-operasional` di browser.

✅ **Indikator sukses**: halaman menampilkan 2 baris pengajuan kredit dan 1 baris klaim asuransi (seed dari Langkah 2), dengan dua form di atasnya, tidak ada error render.

## Langkah 5: Isi data operasional lewat form (bahan uji Module 21 dan seterusnya)

Tambahkan data lewat kedua form di `/data-operasional` sampai datanya representatif untuk latihan module-module berikutnya — bukan lewat SQL manual atau seeder. Target yang dipakai di contoh-contoh Module 20-23 selanjutnya (lihat Module 19 Bagian 4 "Hasil Uji Nyata"): total **7 baris** `pengajuan_kredit` (variasi status: `pending`×3, `disetujui`×1, `pencairan`×1, `ditolak`×2 — dua di antaranya sudah ada dari seed Langkah 2: `N-00231` `pending` dan `N-00305` `ditolak` dengan `alasan_penolakan` "Skor kredit di bawah ambang batas minimum", jadi tambahkan **5 baris lagi** lewat form) dan total **4 baris** `klaim_asuransi` (1 sudah ada dari seed — `N-00305`, jenis `kendaraan`, `disetujui` — tambahkan **3 baris lagi**), dengan minimal satu `nasabah_id` yang sengaja muncul di kedua tabel (mis. `N-00305`, yang kreditnya ditolak **dan** punya klaim asuransi — bahan uji skenario gabungan RAG+SQL di Module 22).

```bash
docker compose exec postgres psql -U nala_admin -d nala_operasional -c "SELECT COUNT(*) FROM pengajuan_kredit;"
docker compose exec postgres psql -U nala_admin -d nala_operasional -c "SELECT COUNT(*) FROM klaim_asuransi;"
```

✅ **Indikator sukses**: `7` dan `4`, dan refresh halaman `/data-operasional` menunjukkan seluruh baris yang baru ditambahkan tetap ada (data tersimpan permanen). Module 19 selesai — lanjut ke `PANDUAN-PRAKTIK.md` di folder Module 20.

## Troubleshooting

- **`psycopg.OperationalError: connection to server ... failed`**: kemungkinan besar DSN masih memakai `localhost` padahal dipanggil dari dalam container `api` — harus memakai nama service Docker Compose (`postgres`), lihat catatan di Langkah 3. Cek juga `postgres` sudah `healthy` (`docker compose ps`).
- **`permission denied for table ...` padahal seharusnya diizinkan**: cek role/DSN yang dipakai — form `/data-operasional` (Module 19) harus memakai `nala_writer`, tool SQL (Module 21) harus memakai `nala_readonly`; tertukar salah satunya akan memicu `permission denied` untuk operasi yang seharusnya sah.
- **Seed data tidak berubah setelah mengedit `db/seed.sql`**: script init PostgreSQL cuma jalan sekali saat volume database masih kosong — kalau volume `postgres_data` sudah ada dari percobaan sebelumnya, `docker compose up` **tidak** menjalankan ulang seed. Hapus volume dulu (`docker compose down && docker volume rm nala_postgres_data`) lalu `docker compose up -d --build postgres` lagi. Ini juga penyebab paling umum kalau tabel/role baru "tidak muncul" setelah mengikuti Langkah 2.
- **`docker compose exec postgres psql -U nala_admin ...` minta password / gagal autentikasi**: pastikan env var `POSTGRES_ADMIN_PASSWORD` (kalau di-override di `.env` atau shell) konsisten dengan yang dipakai saat container `postgres` dibuat — kalau volume sudah lama ada dengan password lama, password baru di env var tidak otomatis berlaku sampai volume direset (sama seperti poin seed data di atas).
- **Error umum lain** (`no configuration file provided`, `failed to read dockerfile`, port sudah dipakai, dsb.): lihat bagian Troubleshooting `PANDUAN-PRAKTIK.md` module-module sebelumnya (Module 5-14) — penyebab dan solusinya sama, tidak spesifik rangkaian Module 19-23.

---

Untuk informasi lebih lanjut, lihat [materi Module 19](./materi.md) dan [README utama](../README.md).
