# Module 23: Setup Data Operasional — PostgreSQL & UI Form

## Tujuan

Menyiapkan sumber data operasional PT Nusantara Finance (pengajuan kredit, klaim asuransi) di PostgreSQL — dengan skema tabel, pemisahan role database sejak awal, dan **halaman web untuk staff menambah data sendiri** — sebagai fondasi yang dipakai Module 25 (SQL Tool) dan seterusnya. Module ini sengaja **tidak** memakai data dummy yang di-generate otomatis lewat skrip seeder besar — datanya sedikit di awal, staff (Anda) yang menambah sisanya lewat form, supaya data yang dipakai untuk latihan terasa seperti hasil kerja nyata, bukan angka yang sudah "disiapkan" begitu saja.

## Definisi

**Data operasional** adalah data transaksional yang berubah setiap hari — pengajuan kredit, klaim asuransi — berbeda secara mendasar dari **knowledge base** (dokumen SOP/kebijakan) yang dipakai RAG sejak Module 9: dokumen SOP jarang berubah dan menjawab pertanyaan "bagaimana prosedurnya", sedangkan data operasional berubah terus dan menjawab pertanyaan "apa status transaksi ini sekarang". Bedanya bukan cuma soal seberapa sering berubah, tapi juga *tempat penyimpanan*: dokumen SOP hidup sebagai vektor di OpenSearch (Module 12), data operasional hidup sebagai baris terstruktur di PostgreSQL — dua sumber jawaban yang akan disatukan lewat agent mulai Module 24.

Module ini juga memperkenalkan pola **pemisahan role baca/tulis** sejak level database: `nala_readonly` (cuma `SELECT`) dan `nala_writer` (cuma `INSERT`) adalah dua identitas login PostgreSQL yang terpisah, masing-masing hanya bisa melakukan satu jenis operasi — bukan sekadar konvensi penamaan, tapi dipaksakan lewat `GRANT` di level database itu sendiri. Prinsip ini disebut **least privilege**: setiap komponen (baik kode Python maupun manusia lewat form) memakai identitas dengan hak akses paling minim yang masih cukup untuk tugasnya, supaya kesalahan di satu lapisan kode tidak otomatis berarti data bisa diubah/dihapus sembarangan.

```mermaid
flowchart LR
    S["db/seed.sql<br/>(migrasi)"] --> T["Tabel: pengajuan_kredit,<br/>klaim_asuransi"]
    S --> R1["Role nala_readonly<br/>(hanya SELECT)"]
    S --> R2["Role nala_writer<br/>(hanya INSERT)"]
    F["Staff isi form<br/>/data-operasional"] -->|"pakai nala_writer"| T
    Q["Tool SQL (Module 25)"] -->|"pakai nala_readonly"| T
```

## Hasil Akhir yang Diharapkan

- Service `postgres` berjalan sehat (`docker compose ps` menunjukkan `healthy`), dengan 2 tabel: `pengajuan_kredit`, `klaim_asuransi`
- Seed awal **minimal** (2-3 baris per tabel) — cukup untuk memverifikasi skema jalan, bukan dataset lengkap
- Dua role database terpisah sejak module ini: `nala_readonly` (cuma `SELECT`, dipakai agent/SQL tool di Module 25) dan `nala_writer` (cuma `INSERT`, dipakai form UI) — keduanya **tidak** bisa saling melakukan operasi milik peran yang lain, diverifikasi langsung lewat `psql`
- Halaman baru `/data-operasional` (mengikuti pola `upload.html` Module 16) — form tambah pengajuan kredit & klaim asuransi, plus tabel daftar data yang sudah ada
- Staff sudah menambah beberapa data operasional sungguhan lewat form (bukan lewat SQL manual atau seeder) sebagai bahan uji Module 25 dan seterusnya

## 1. Kenapa Bukan Seeder Biasa

Pola yang lazim dipakai untuk data dummy adalah skrip seeder — satu file SQL/Python yang di-*generate* sekali, berisi puluhan baris data fiktif, dijalankan otomatis saat container pertama kali dibuat. Itu cepat, tapi punya konsekuensi pedagogis yang kurang pas untuk module ini: kita tidak pernah benar-benar "menyentuh" bagaimana data operasional itu masuk ke sistem — datanya sudah ada begitu saja, seolah-olah turun dari langit.

Module ini sengaja membalik itu: **schema dan role dibuat lewat migrasi (`db/seed.sql`), tapi isinya cuma 2-3 baris starting point** — cukup untuk memverifikasi skema tidak salah tanpa perlu tabel kosong sama sekali. Sisanya, staff (Anda) input sendiri lewat halaman `/data-operasional` yang dibangun di module ini — persis pola yang sudah dipakai sejak Module 9 (Knowledge Base: kita upload dokumen sendiri lewat form, bukan dokumen yang sudah di-mount otomatis dalam jumlah besar).

```mermaid
flowchart LR
    A["docker compose up<br/>(container pertama kali dibuat)"] --> B["db/seed.sql dijalankan otomatis<br/>oleh image Postgres"]
    B --> C["CREATE TABLE<br/>+ 2-3 baris starting point<br/>+ CREATE ROLE readonly/writer"]
    C --> D["Staff buka /data-operasional<br/>isi form, tambah data sendiri"]
    D --> E["Data operasional siap dipakai<br/>Module 25 (SQL Tool)"]
```

## 2. Dua Role Sejak Awal: Baca vs Tulis

Sebelum menulis kode tool query (baru Module 25), pemisahan role database sudah disiapkan di module ini — supaya begitu Module 25 dibangun, `nala_readonly` sudah ada dan siap dipakai, tidak perlu bolak-balik migrasi:

- **`nala_writer`** — cuma `GRANT INSERT`, dipakai **jalur manusia** (form `/data-operasional`, endpoint `POST` di `app/main.py`). Manusia (staff) yang menambah data lewat form, bukan LLM.
- **`nala_readonly`** — cuma `GRANT SELECT`, disiapkan di sini tapi **belum dipakai** sampai Module 25 (SQL Tool) membangun kode yang membacanya.

Keduanya **saling tidak bisa** melakukan operasi milik peran lain — `nala_writer` tidak bisa `SELECT`, `nala_readonly` tidak bisa `INSERT`/`UPDATE`/`DELETE`. Ini bukan detail kecil: artinya kalaupun nanti ada bug di kode Python yang secara tidak sengaja mencampur kedua koneksi, PostgreSQL sendiri yang menolak operasi yang salah — pertahanan berlapis yang sama seperti yang sudah dijelaskan lebih detail nanti di Module 25 Bagian 2.

## 3. Struktur Kode yang Ditambahkan

Dua Tahap, total **6 Langkah**: **Tahap A** (Langkah 1-2) menyiapkan service PostgreSQL, skema, seed minimal, dan dua role. **Tahap B** (Langkah 3-6) membangun halaman `/data-operasional` (form + tabel daftar data), lalu mengisinya dengan data sungguhan lewat form.

### Prasyarat

- Sudah menyelesaikan **Module 1-22** (`llama3.2:3b` sudah biasa dipakai, `Nala/` berjalan dengan hybrid search + reranking + evaluasi + Langfuse). Rangkaian Module 23-27 **menambah** lapisan data operasional/agent/tool/RBAC langsung di atas file-file yang sudah ada di folder `Nala/` yang sama sejak Module 1 — tidak ada folder baru dan tidak ada project Docker baru yang perlu disiapkan.
- Docker Desktop sudah dialokasikan resource yang cukup:

| Setting | Minimal rangkaian Module 23-27 | Direkomendasikan | Alasan |
|---|---|---|---|
| **Memory (RAM)** | 16 GB | 16 GB+ (32 GB+ kalau ingin coba `qwen2.5:7b`, lihat Module 26 Bagian 4.b) | PostgreSQL menambah beban kecil-menengah di atas stack Module 7-22 yang sudah berat; agent tool-calling (mulai Module 24) memanggil Ollama beberapa kali per pertanyaan, menambah beban CPU sesaat, bukan RAM tambahan besar. |
| **CPUs** | 4 | 4+ | 5 service aktif sekaligus (ollama, opensearch, airflow, postgres, api), ditambah beberapa panggilan Ollama berurutan per request agent. |
| **Disk image size** | 100 GB | 120 GB+ | Image `postgres:16` relatif kecil (~400MB), tapi menumpuk di atas seluruh image module-module sebelumnya yang sudah ada. |

Kalau sudah di 16GB+ sejak Module 7-22, tidak perlu diubah lagi kecuali ingin mencoba `qwen2.5:7b` (Module 26 Bagian 4.b).

**Verifikasi fondasi sebelum mulai** — pastikan salinan Module 1-22 masih berjalan identik sebelum Module 23 menambah apa pun:

```bash
cd Nala
docker compose up --build --no-deps ollama api
```

Terminal baru, pastikan model sudah ada (kemungkinan sudah dari Module 2, tapi container storage terpisah per project):

```bash
docker compose exec ollama ollama pull llama3.2:3b
```

```bash
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Apa saja syarat pengajuan kredit untuk nasabah perorangan?"}]}'
```

✅ **Indikator sukses**: jawaban streaming berbasis dokumen SOP seperti akhir Module 22 (kualitas hybrid search + reranking) — bukti fondasi berjalan identik sebelum Module 23 mulai menambah apa pun.

### Tahap A — Service PostgreSQL, skema, seed minimal, dua role

**Langkah 1 — Tambah service `postgres` di `docker-compose.yml`**

```yaml
# docker-compose.yml
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: nala_operasional
      POSTGRES_USER: nala_admin
      POSTGRES_PASSWORD: ${POSTGRES_ADMIN_PASSWORD:-changeme_dev_only}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./db:/docker-entrypoint-initdb.d
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U nala_admin -d nala_operasional"]
      interval: 5s
      timeout: 5s
      retries: 10
```

Tambah `postgres_data:` ke `volumes:` top-level, dan `postgres: {condition: service_healthy}` ke `depends_on` service `api` (bersama `ollama`/`opensearch` yang sudah ada dari module-module sebelumnya — kalau `depends_on` versi Anda masih bentuk list sederhana, ubah jadi bentuk mapping supaya bisa memakai `condition`).

`POSTGRES_PASSWORD` sengaja pakai env var dengan default eksplisit `changeme_dev_only` — cukup untuk laptop training, **bukan** pola aman untuk deployment sungguhan (dibahas lagi soal secret management di Module 29 (deployment `.env`) dan Module 30 Bagian 3.a). Image resmi `postgres` otomatis menjalankan file apa pun di `/docker-entrypoint-initdb.d/` **satu kali saat volume database masih kosong** — itu cara `db/seed.sql` (Langkah 2) ter-load otomatis tanpa langkah manual tambahan.

<details>
<summary><strong>Pakai Claude Code? Salin prompt berikut, paste untuk eksekusi Langkah 1</strong></summary>

```
Tambah service PostgreSQL di docker-compose.yml — Module 23, Langkah 1.

GOAL:
Di Nala/docker-compose.yml: tambah
service baru "postgres" (image postgres:16, POSTGRES_DB=
nala_operasional, POSTGRES_USER=nala_admin, POSTGRES_PASSWORD dari
env var POSTGRES_ADMIN_PASSWORD default changeme_dev_only, port
5432:5432, volume postgres_data:/var/lib/postgresql/data DAN
./db:/docker-entrypoint-initdb.d (mount FOLDER db, bukan file tunggal —
lebih robust di Docker Desktop), healthcheck pg_isready). Tambah postgres_data ke volumes: top-level. Tambah
depends_on postgres (condition service_healthy) ke service api
(ubah depends_on api ke bentuk mapping kalau masih list).

CONTEXT:
- Ini tabel BARU, terpisah dari OpenSearch/vector store Module 9-22.
- db/seed.sql yang dirujuk di volumes belum ada — file itu dibuat di
  Langkah 2 terpisah, jadi container postgres belum bisa dijalankan
  sampai Langkah 2 selesai.

GUARDRAIL:
- JANGAN ubah service lain (ollama, opensearch, airflow, langfuse,
  api) selain menambah depends_on di api.
- JANGAN buat file db/seed.sql di langkah ini — itu Langkah 2
  terpisah.
```

</details>

**Langkah 2 — Buat `db/seed.sql`**

```bash
mkdir -p db
```

```sql
-- db/seed.sql
CREATE TABLE pengajuan_kredit (
    id SERIAL PRIMARY KEY,
    nasabah_id VARCHAR(10) NOT NULL,
    nama_nasabah VARCHAR(100) NOT NULL,
    jumlah_pengajuan NUMERIC(15, 2) NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'disetujui', 'ditolak', 'pencairan')),
    tanggal_pengajuan DATE NOT NULL,
    alasan_penolakan TEXT
);

CREATE TABLE klaim_asuransi (
    id SERIAL PRIMARY KEY,
    nasabah_id VARCHAR(10) NOT NULL,
    nama_nasabah VARCHAR(100) NOT NULL,
    jenis_klaim VARCHAR(50) NOT NULL,
    jumlah_klaim NUMERIC(15, 2) NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'diproses', 'disetujui', 'ditolak')),
    tanggal_klaim DATE NOT NULL
);

-- Data awal minimal (starting point) — selebihnya ditambahkan staff sendiri lewat UI /data-operasional
INSERT INTO pengajuan_kredit (nasabah_id, nama_nasabah, jumlah_pengajuan, status, tanggal_pengajuan, alasan_penolakan) VALUES
('N-00231', 'Budi Santoso', 50000000, 'pending', CURRENT_DATE - 2, NULL),
('N-00305', 'Andi Wijaya', 100000000, 'ditolak', CURRENT_DATE - 5, 'Skor kredit di bawah ambang batas minimum');

INSERT INTO klaim_asuransi (nasabah_id, nama_nasabah, jenis_klaim, jumlah_klaim, status, tanggal_klaim) VALUES
('N-00305', 'Andi Wijaya', 'kendaraan', 15000000, 'disetujui', CURRENT_DATE - 20);

-- Role read-only: dipakai agent (tool query_data_operasional, dibangun Module 25) — hanya bisa SELECT
CREATE ROLE nala_readonly WITH LOGIN PASSWORD 'readonly_dev_only';
GRANT CONNECT ON DATABASE nala_operasional TO nala_readonly;
GRANT USAGE ON SCHEMA public TO nala_readonly;
GRANT SELECT ON pengajuan_kredit, klaim_asuransi TO nala_readonly;

-- Role write-only: dipakai form UI /data-operasional (input manusia, bukan LLM) — hanya bisa INSERT
CREATE ROLE nala_writer WITH LOGIN PASSWORD 'writer_dev_only';
GRANT CONNECT ON DATABASE nala_operasional TO nala_writer;
GRANT USAGE ON SCHEMA public TO nala_writer;
GRANT INSERT ON pengajuan_kredit, klaim_asuransi TO nala_writer;
GRANT USAGE, SELECT ON SEQUENCE pengajuan_kredit_id_seq, klaim_asuransi_id_seq TO nala_writer;
```

Data awal cuma 2 baris `pengajuan_kredit` + 1 baris `klaim_asuransi` — **sengaja minimal**, bukan dataset lengkap (bandingkan dengan pendekatan seeder besar yang sempat dipertimbangkan tapi tidak dipakai, lihat Bagian 1). `GRANT USAGE, SELECT ON SEQUENCE ...` untuk `nala_writer` diperlukan supaya `INSERT` ke kolom `SERIAL` (auto-increment) bisa jalan — tanpa ini, PostgreSQL menolak `INSERT` walau sudah punya `GRANT INSERT` di tabelnya, karena `nextval()` pada sequence butuh izin terpisah.

<details>
<summary><strong>Pakai Claude Code? Salin prompt berikut, paste untuk eksekusi Langkah 2</strong></summary>

```
Buat db/seed.sql: skema data operasional minimal + dua role
terpisah (read-only vs write-only) — Module 23, Langkah 2.

GOAL:
Buat Nala/db/seed.sql: CREATE TABLE
pengajuan_kredit (id SERIAL PK, nasabah_id VARCHAR(10), nama_nasabah
VARCHAR(100), jumlah_pengajuan NUMERIC(15,2), status VARCHAR(20)
CHECK IN ('pending','disetujui','ditolak','pencairan'),
tanggal_pengajuan DATE, alasan_penolakan TEXT nullable) dan CREATE
TABLE klaim_asuransi (id SERIAL PK, nasabah_id VARCHAR(10),
nama_nasabah VARCHAR(100), jenis_klaim VARCHAR(50), jumlah_klaim
NUMERIC(15,2), status VARCHAR(20) CHECK IN
('pending','diproses','disetujui','ditolak'), tanggal_klaim DATE).
INSERT cuma 2 baris pengajuan_kredit + 1 baris klaim_asuransi
(data fiktif minimal, BUKAN dataset besar). Lalu CREATE ROLE
nala_readonly (LOGIN, GRANT CONNECT+USAGE+SELECT pada kedua tabel)
dan CREATE ROLE nala_writer (LOGIN, GRANT CONNECT+USAGE+INSERT pada
kedua tabel, plus GRANT USAGE,SELECT pada kedua SEQUENCE id-nya).

CONTEXT:
- Service postgres di docker-compose.yml (Langkah 1) sudah mount
  file ini ke /docker-entrypoint-initdb.d/01-seed.sql — otomatis
  dijalankan sekali oleh image Postgres saat container pertama kali
  dibuat (volume masih kosong).
- nala_readonly BELUM dipakai kode apa pun sampai Module 25 (SQL Tool)
  — di module ini cuma dibuat role-nya saja.

GUARDRAIL:
- JANGAN isi data dummy lebih dari 2-3 baris per tabel — sengaja
  minimal, sisanya ditambah lewat UI di Langkah 6.
- JANGAN gunakan data nasabah sungguhan — harus dummy/fiktif.
```

</details>

**▶️ Jalankan & lihat hasilnya**

```bash
docker compose up -d --build postgres
docker compose logs -f postgres
```

Tunggu sampai log menunjukkan `database system is ready to accept connections`, lalu `Ctrl+C`.

```bash
docker compose exec postgres psql -U nala_admin -d nala_operasional -c "SELECT COUNT(*) FROM pengajuan_kredit;"
docker compose exec postgres psql -U nala_admin -d nala_operasional -c "SELECT COUNT(*) FROM klaim_asuransi;"
```

✅ **Indikator sukses**: masing-masing mengembalikan `2` dan `1` — bukti seed minimal berjalan otomatis.

Verifikasi juga pemisahan role bekerja **dua arah**:

```bash
docker compose exec postgres psql -U nala_readonly -d nala_operasional -c "DELETE FROM pengajuan_kredit WHERE id = 1;"
docker compose exec postgres psql -U nala_writer -d nala_operasional -c "SELECT COUNT(*) FROM pengajuan_kredit;"
```

✅ **Indikator sukses**: **keduanya harus gagal** — `nala_readonly` ditolak dengan `permission denied for table pengajuan_kredit` saat `DELETE`, dan `nala_writer` **juga** ditolak `permission denied` saat `SELECT`. Kalau salah satu berhasil, berarti `GRANT` di `seed.sql` salah — cek ulang sebelum lanjut.

### Tahap B — Halaman `/data-operasional`: form tambah data + tabel daftar

**Langkah 3 — Tambah dependency database & dua fungsi koneksi**

```
# requirements.txt — tambahkan baris baru
psycopg[binary]==3.2.3
```

```python
# app/db.py
import os

import psycopg

POSTGRES_READONLY_DSN = os.environ.get(
    "POSTGRES_READONLY_DSN",
    "postgresql://nala_readonly:readonly_dev_only@localhost:5432/nala_operasional",
)

POSTGRES_WRITER_DSN = os.environ.get(
    "POSTGRES_WRITER_DSN",
    "postgresql://nala_writer:writer_dev_only@localhost:5432/nala_operasional",
)


def get_connection():
    return psycopg.connect(POSTGRES_READONLY_DSN, connect_timeout=5)


def get_write_connection():
    return psycopg.connect(POSTGRES_WRITER_DSN, connect_timeout=5)
```

Dua fungsi terpisah, masing-masing pakai DSN role yang berbeda — `get_connection()` (readonly) dipakai untuk **menampilkan** data di halaman `/data-operasional` dan nanti tool SQL Module 25, `get_write_connection()` (writer) dipakai **hanya** oleh endpoint `POST` form di Langkah 5. Tambahkan juga dua env var ini ke service `api` di `docker-compose.yml`:

```yaml
# docker-compose.yml, service api — tambahan environment
- POSTGRES_READONLY_DSN=postgresql://nala_readonly:readonly_dev_only@postgres:5432/nala_operasional
- POSTGRES_WRITER_DSN=postgresql://nala_writer:writer_dev_only@postgres:5432/nala_operasional
```

⚠️ **Catatan**: default `POSTGRES_READONLY_DSN`/`POSTGRES_WRITER_DSN` di `app/db.py` menunjuk `localhost` — kalau dipanggil dari **dalam** container `api`, harus memakai nama service Docker Compose (`postgres`), bukan `localhost`. Env var di `docker-compose.yml` service `api` (di atas) sudah meng-override ke host `postgres` yang benar; pastikan kedua baris itu ditambahkan sebelum menjalankan verifikasi di bawah.

<details>
<summary><strong>Pakai Claude Code? Salin prompt berikut, paste untuk eksekusi Langkah 3</strong></summary>

```
Tambah dependency database (psycopg) dan dua fungsi koneksi
terpisah (readonly vs writer) — Module 23, Langkah 3.

GOAL:
1. Di Nala/requirements.txt: tambah baris
   psycopg[binary]==3.2.3
2. Buat Nala/app/db.py: dua konstanta DSN
   dari env var (POSTGRES_READONLY_DSN, POSTGRES_WRITER_DSN, dengan
   default masing-masing memakai nala_readonly/nala_writer di
   localhost), dua fungsi get_connection() dan get_write_connection()
   yang psycopg.connect() ke DSN masing-masing (connect_timeout=5).
3. Di Nala/docker-compose.yml service api: tambah dua environment
   POSTGRES_READONLY_DSN dan POSTGRES_WRITER_DSN yang menunjuk host
   "postgres" (nama service, BUKAN localhost).

CONTEXT:
- Role nala_readonly dan nala_writer sudah ada di database sejak
  Langkah 2 (db/seed.sql).
- Default DSN di app/db.py sengaja pakai localhost (memudahkan akses
  dari luar container saat debugging) — env var di docker-compose.yml
  service api yang meng-override ke host postgres saat kode berjalan
  di dalam container.

GUARDRAIL:
- JANGAN tukar DSN readonly/writer — get_connection() harus memakai
  DSN nala_readonly, get_write_connection() harus memakai DSN
  nala_writer.
```

</details>

**▶️ Jalankan & lihat hasilnya**

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

**Langkah 4 — Buat `app/templates/data_operasional.html`, tambah nav, dan CSS-nya**

Ada **tiga** perubahan file di langkah ini: (1) template baru `app/templates/data_operasional.html`, (2) satu link nav baru di `chat.html` dan `upload.html` yang sudah ada, (3) sedikit CSS baru (`form`, `.data-table`) di `app/static/style.css`. Ketiganya ditampilkan di bawah ini.

Mengikuti pola `upload.html` (Module 16) — form di atas, tabel daftar data di bawah, untuk **kedua** tabel (`pengajuan_kredit`, `klaim_asuransi`):

```html
<!-- app/templates/data_operasional.html -->
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <title>NALA — Data Operasional</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <div class="container">
        <h1>Data Operasional</h1>
        <nav><a href="/">Chat</a> | <a href="/upload">Knowledge Base</a> | <a href="/data-operasional">Data Operasional</a></nav>
        {% if message %}<p class="success">{{ message }}</p>{% endif %}

        <h2>Tambah Pengajuan Kredit</h2>
        <form action="/data-operasional/pengajuan-kredit" method="post">
            <input type="text" name="nasabah_id" placeholder="ID Nasabah (mis. N-00512)" required>
            <input type="text" name="nama_nasabah" placeholder="Nama Nasabah" required>
            <input type="number" name="jumlah_pengajuan" placeholder="Jumlah Pengajuan (Rp)" step="1" min="0" required>
            <select name="status" required>
                <option value="pending">pending</option>
                <option value="disetujui">disetujui</option>
                <option value="ditolak">ditolak</option>
                <option value="pencairan">pencairan</option>
            </select>
            <input type="date" name="tanggal_pengajuan" required>
            <input type="text" name="alasan_penolakan" placeholder="Alasan penolakan (opsional)">
            <button type="submit">Tambah Pengajuan Kredit</button>
        </form>

        <h2>Daftar Pengajuan Kredit</h2>
        {% if pengajuan_kredit %}
        <table class="data-table">
            <thead><tr><th>ID Nasabah</th><th>Nama</th><th>Jumlah</th><th>Status</th><th>Tanggal</th></tr></thead>
            <tbody>
                {% for row in pengajuan_kredit %}
                <tr>
                    <td>{{ row.nasabah_id }}</td>
                    <td>{{ row.nama_nasabah }}</td>
                    <td>{{ "{:,.0f}".format(row.jumlah_pengajuan) }}</td>
                    <td>{{ row.status }}</td>
                    <td>{{ row.tanggal_pengajuan }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}<p class="hint">Belum ada data pengajuan kredit.</p>{% endif %}

        <hr>

        <h2>Tambah Klaim Asuransi</h2>
        <form action="/data-operasional/klaim-asuransi" method="post">
            <input type="text" name="nasabah_id" placeholder="ID Nasabah (mis. N-00512)" required>
            <input type="text" name="nama_nasabah" placeholder="Nama Nasabah" required>
            <input type="text" name="jenis_klaim" placeholder="Jenis Klaim (mis. kesehatan, kendaraan)" required>
            <input type="number" name="jumlah_klaim" placeholder="Jumlah Klaim (Rp)" step="1" min="0" required>
            <select name="status" required>
                <option value="pending">pending</option>
                <option value="diproses">diproses</option>
                <option value="disetujui">disetujui</option>
                <option value="ditolak">ditolak</option>
            </select>
            <input type="date" name="tanggal_klaim" required>
            <button type="submit">Tambah Klaim Asuransi</button>
        </form>

        <h2>Daftar Klaim Asuransi</h2>
        {% if klaim_asuransi %}
        <table class="data-table">
            <thead><tr><th>ID Nasabah</th><th>Nama</th><th>Jenis</th><th>Jumlah</th><th>Status</th><th>Tanggal</th></tr></thead>
            <tbody>
                {% for row in klaim_asuransi %}
                <tr>
                    <td>{{ row.nasabah_id }}</td>
                    <td>{{ row.nama_nasabah }}</td>
                    <td>{{ row.jenis_klaim }}</td>
                    <td>{{ "{:,.0f}".format(row.jumlah_klaim) }}</td>
                    <td>{{ row.status }}</td>
                    <td>{{ row.tanggal_klaim }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}<p class="hint">Belum ada data klaim asuransi.</p>{% endif %}
    </div>
</body>
</html>
```

Perubahan kedua — tambah link nav baru ke `chat.html` dan `upload.html` yang sudah ada, supaya halaman baru ini bisa dijangkau dari halaman lain (bukan cuma dengan mengetik URL-nya):

```html
<!-- app/templates/chat.html dan app/templates/upload.html — tambahkan item terakhir di <nav> yang sudah ada -->
<nav><a href="/">Chat</a> | <a href="/upload">Knowledge Base</a> | <a href="/data-operasional">Data Operasional</a></nav>
```

Perubahan ketiga — CSS. Template di atas memakai `class="data-table"` dan dua `<form>` yang field-nya tersusun vertikal; tanpa aturan berikut, tabelnya tampil tanpa garis dan input-nya berdempetan menyamping. Tambahkan di akhir `app/static/style.css` (class lain yang dipakai template — `.container`, `.success`, `.hint` — sudah ada sejak module-module sebelumnya):

```css
/* app/static/style.css — tambahan Module 23.
   Selector di-scope `:not(#chat-form)` supaya aturan flex-column ini TIDAK menimpa
   layout baris `#chat-form` (input + tombol "Kirim" menyamping) yang dibuat sejak Module 8. */
form:not(#chat-form) {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-bottom: 24px;
    max-width: 480px;
}

form:not(#chat-form) input,
form:not(#chat-form) select,
form:not(#chat-form) button {
    padding: 8px;
    font-size: 14px;
}

.data-table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 24px;
}

.data-table th,
.data-table td {
    border: 1px solid #ddd;
    padding: 6px 10px;
    text-align: left;
}

.data-table th {
    background: #f4f4f4;
}
```

<details>
<summary><strong>Pakai Claude Code? Salin prompt berikut, paste untuk eksekusi Langkah 4</strong></summary>

```
Buat halaman /data-operasional (template + nav + CSS) untuk staff
menambah data pengajuan kredit dan klaim asuransi — Module 23,
Langkah 4.

GOAL:
1. Buat Nala/app/templates/data_operasional.html:
   dua form (pengajuan kredit, klaim asuransi) dengan field sesuai
   kolom tabel masing-masing, plus dua tabel daftar data di bawah tiap
   form (loop Jinja2 atas pengajuan_kredit/klaim_asuransi dari context).
2. Tambah nav link baru "Data Operasional" (href="/data-operasional")
   ke Nala/app/templates/chat.html dan Nala/app/templates/upload.html
   yang sudah ada.
3. Tambah CSS sederhana untuk form dan tabel (class .data-table) di
   Nala/app/static/style.css.

CONTEXT:
- Mengikuti pola upload.html (Module 16) — form di atas, tabel daftar
  data di bawah.
- Endpoint yang merender template ini (GET /data-operasional) belum
  ada — dibuat di Langkah 5 terpisah, jadi halaman ini belum bisa
  diakses lewat browser sampai Langkah 5 selesai.

GUARDRAIL:
- JANGAN buat endpoint FastAPI apa pun di langkah ini — hanya file
  template, nav link, dan CSS.
```

</details>

**Langkah 5 — Tambah endpoint di `app/main.py`**

```python
# app/main.py — tambahan import
from fastapi import Form
from psycopg.rows import dict_row
from app.db import get_connection, get_write_connection

# app/main.py — tambahan fungsi helper
def fetch_pengajuan_kredit() -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT nasabah_id, nama_nasabah, jumlah_pengajuan, status, tanggal_pengajuan "
                "FROM pengajuan_kredit ORDER BY id DESC"
            )
            return cur.fetchall()


def fetch_klaim_asuransi() -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT nasabah_id, nama_nasabah, jenis_klaim, jumlah_klaim, status, tanggal_klaim "
                "FROM klaim_asuransi ORDER BY id DESC"
            )
            return cur.fetchall()


# app/main.py — tambahan endpoint
@app.get("/data-operasional", response_class=HTMLResponse)
def data_operasional_page(request: Request):
    return templates.TemplateResponse(
        "data_operasional.html",
        {
            "request": request,
            "message": None,
            "pengajuan_kredit": fetch_pengajuan_kredit(),
            "klaim_asuransi": fetch_klaim_asuransi(),
        },
    )


@app.post("/data-operasional/pengajuan-kredit", response_class=HTMLResponse)
def add_pengajuan_kredit(
    request: Request,
    nasabah_id: str = Form(...),
    nama_nasabah: str = Form(...),
    jumlah_pengajuan: float = Form(...),
    status: str = Form(...),
    tanggal_pengajuan: str = Form(...),
    alasan_penolakan: str = Form(""),
):
    with get_write_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO pengajuan_kredit "
                "(nasabah_id, nama_nasabah, jumlah_pengajuan, status, tanggal_pengajuan, alasan_penolakan) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (nasabah_id, nama_nasabah, jumlah_pengajuan, status, tanggal_pengajuan, alasan_penolakan or None),
            )
        conn.commit()

    return templates.TemplateResponse(
        "data_operasional.html",
        {
            "request": request,
            "message": f"Pengajuan kredit untuk nasabah '{nasabah_id}' berhasil ditambahkan.",
            "pengajuan_kredit": fetch_pengajuan_kredit(),
            "klaim_asuransi": fetch_klaim_asuransi(),
        },
    )


@app.post("/data-operasional/klaim-asuransi", response_class=HTMLResponse)
def add_klaim_asuransi(
    request: Request,
    nasabah_id: str = Form(...),
    nama_nasabah: str = Form(...),
    jenis_klaim: str = Form(...),
    jumlah_klaim: float = Form(...),
    status: str = Form(...),
    tanggal_klaim: str = Form(...),
):
    with get_write_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO klaim_asuransi "
                "(nasabah_id, nama_nasabah, jenis_klaim, jumlah_klaim, status, tanggal_klaim) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (nasabah_id, nama_nasabah, jenis_klaim, jumlah_klaim, status, tanggal_klaim),
            )
        conn.commit()

    return templates.TemplateResponse(
        "data_operasional.html",
        {
            "request": request,
            "message": f"Klaim asuransi untuk nasabah '{nasabah_id}' berhasil ditambahkan.",
            "pengajuan_kredit": fetch_pengajuan_kredit(),
            "klaim_asuransi": fetch_klaim_asuransi(),
        },
    )
```

Perhatikan: `add_pengajuan_kredit`/`add_klaim_asuransi` memakai `get_write_connection()` (role `nala_writer`, cuma `INSERT`), sementara `fetch_*` (dipanggil di ketiga endpoint untuk menampilkan tabel) memakai `get_connection()` (role `nala_readonly`, cuma `SELECT`) — dua fungsi koneksi dari Langkah 3 masing-masing dipakai sesuai perannya, tidak pernah tertukar.

<details>
<summary><strong>Pakai Claude Code? Salin prompt berikut, paste untuk eksekusi Langkah 5</strong></summary>

```
Tambah endpoint GET/POST /data-operasional di app/main.py — Module
23, Langkah 5.

GOAL:
Di Nala/app/main.py: import Form dari
fastapi, dict_row dari psycopg.rows, get_connection/get_write_connection
dari app.db. Tambah fungsi fetch_pengajuan_kredit()/fetch_klaim_asuransi()
(SELECT via get_connection(), row_factory=dict_row). Tambah endpoint
GET /data-operasional (render data_operasional.html dengan kedua fetch),
POST /data-operasional/pengajuan-kredit dan POST /data-operasional/klaim-asuransi
(terima Form(...) sesuai kolom tabel, INSERT via get_write_connection(),
conn.commit(), lalu render ulang halaman dengan pesan sukses + data
terbaru).

CONTEXT:
- app/db.py (Langkah 3) dan app/templates/data_operasional.html
  (Langkah 4) sudah dibuat sebelumnya.

GUARDRAIL:
- JANGAN pakai get_write_connection() untuk operasi SELECT/fetch —
  role nala_writer tidak punya izin SELECT, akan gagal.
- JANGAN pakai get_connection() (readonly) untuk INSERT — role
  nala_readonly tidak punya izin INSERT, akan gagal.
- JANGAN ubah endpoint /chat/stream, /upload, /health yang sudah ada
  (endpoint /chat belum ada sampai Module 24 membuatnya).
```

</details>

**▶️ Jalankan & lihat hasilnya**

```bash
docker compose up --build -d postgres api
```

Buka `http://localhost:8000/data-operasional` di browser — halaman menampilkan 2 baris pengajuan kredit dan 1 baris klaim asuransi (seed dari Tahap A), dengan dua form di atasnya. Coba isi form "Tambah Pengajuan Kredit" dengan data baru, submit — baris baru harus langsung muncul di tabel di bawahnya tanpa reload manual kedua kalinya.

✅ **Indikator sukses**: form berhasil menambah data (terlihat di tabel setelah submit), dan data tersimpan permanen — refresh halaman, data yang baru ditambahkan tetap ada.

**Langkah 6 — Isi data operasional lewat form**

Tambahkan data lewat kedua form di `/data-operasional` sampai datanya representatif untuk latihan module-module berikutnya — bukan lewat SQL manual atau seeder. Target yang dipakai di contoh-contoh Module 24-27 selanjutnya (lihat Bagian 4 "Hasil Uji Nyata" di bawah): total **7 baris** `pengajuan_kredit` (variasi status: `pending`×3, `disetujui`×1, `pencairan`×1, `ditolak`×2 — dua di antaranya sudah ada dari seed Langkah 2: `N-00231` `pending` dan `N-00305` `ditolak` dengan `alasan_penolakan` "Skor kredit di bawah ambang batas minimum", jadi tambahkan **5 baris lagi** lewat form) dan total **4 baris** `klaim_asuransi` (1 sudah ada dari seed — `N-00305`, jenis `kendaraan`, `disetujui` — tambahkan **3 baris lagi**), dengan minimal satu `nasabah_id` yang sengaja muncul di kedua tabel (mis. `N-00305`, yang kreditnya ditolak **dan** punya klaim asuransi — bahan uji skenario gabungan RAG+SQL di Module 25 Bagian 4).

```bash
docker compose exec postgres psql -U nala_admin -d nala_operasional -c "SELECT COUNT(*) FROM pengajuan_kredit;"
docker compose exec postgres psql -U nala_admin -d nala_operasional -c "SELECT COUNT(*) FROM klaim_asuransi;"
```

✅ **Indikator sukses**: `7` dan `4` (berbeda dari indikator `2`/`1` di Langkah 2 — itu memverifikasi seed awal, ini memverifikasi data hasil input manual lewat form sudah representatif), dan refresh halaman `/data-operasional` menunjukkan seluruh baris yang baru ditambahkan tetap ada (data tersimpan permanen). Langkah 6 ini murni input data manual lewat UI, bukan perubahan kode — tidak ada prompt Claude Code untuk langkah ini.

**📄 Kode lengkap Module 23** (`docker-compose.yml` bagian `postgres`, `db/seed.sql`, `app/db.py`, `app/templates/data_operasional.html`, tambahan `app/static/style.css`, potongan relevan `app/main.py` — sudah ditampilkan utuh di Langkah 1-5 di atas).

### Troubleshooting

- **`psycopg.OperationalError: connection to server ... failed`**: kemungkinan besar DSN masih memakai `localhost` padahal dipanggil dari dalam container `api` — harus memakai nama service Docker Compose (`postgres`), lihat catatan di Langkah 3. Cek juga `postgres` sudah `healthy` (`docker compose ps`).
- **`permission denied for table ...` padahal seharusnya diizinkan**: cek role/DSN yang dipakai — form `/data-operasional` (Module 23) harus memakai `nala_writer`, tool SQL (Module 25) harus memakai `nala_readonly`; tertukar salah satunya akan memicu `permission denied` untuk operasi yang seharusnya sah.
- **Seed data tidak berubah setelah mengedit `db/seed.sql`**: script init PostgreSQL cuma jalan sekali saat volume database masih kosong — kalau volume `postgres_data` sudah ada dari percobaan sebelumnya, `docker compose up` **tidak** menjalankan ulang seed. Hapus volume dulu (`docker compose down && docker volume rm nala_postgres_data`) lalu `docker compose up -d --build postgres` lagi. Ini juga penyebab paling umum kalau tabel/role baru "tidak muncul" setelah mengikuti Langkah 2.
- **`docker compose exec postgres psql -U nala_admin ...` minta password / gagal autentikasi**: pastikan env var `POSTGRES_ADMIN_PASSWORD` (kalau di-override di `.env` atau shell) konsisten dengan yang dipakai saat container `postgres` dibuat — kalau volume sudah lama ada dengan password lama, password baru di env var tidak otomatis berlaku sampai volume direset (sama seperti poin seed data di atas).
- **Error umum lain** (`no configuration file provided`, `failed to read dockerfile`, port sudah dipakai, dsb.): lihat bagian Troubleshooting di materi.md module-module sebelumnya (Module 7-17) — penyebab dan solusinya sama, tidak spesifik rangkaian Module 23-27.

## 4. Hasil Uji Nyata

Setup ini sudah diuji langsung, bukan cuma teori:

- **Pemisahan role dua arah terbukti bekerja**: `nala_readonly` ditolak saat mencoba `DELETE` (`permission denied for table pengajuan_kredit`), dan `nala_writer` **juga** ditolak saat mencoba `SELECT` — bukti kedua role benar-benar terisolasi sesuai perannya masing-masing, bukan cuma dibatasi di satu arah.
- **Form UI diuji end-to-end**: data baru ditambahkan lewat `POST /data-operasional/pengajuan-kredit` dan `POST /data-operasional/klaim-asuransi`, langsung terlihat di tabel tanpa restart container apa pun.
- **Data operasional untuk latihan Module 25 dst. sudah terisi lewat form** (bukan seeder): 7 baris `pengajuan_kredit` (variasi status: `pending`×3, `disetujui`×1, `pencairan`×1, `ditolak`×2) dan 4 baris `klaim_asuransi`, dengan beberapa `nasabah_id` sengaja muncul di kedua tabel (mis. nasabah yang kreditnya ditolak **dan** punya klaim asuransi) — bahan uji untuk skenario gabungan RAG+SQL di Module 25 Bagian 4.

## 5. Checkpoint Praktik

Langkah eksekusi lengkap ada di Bagian 3 di atas (Langkah 1-6). Yang perlu dipastikan sebelum lanjut ke Module 24:

- [ ] Service `postgres` sehat (`healthy`), 2 tabel terbentuk dengan seed minimal (2 baris + 1 baris)
- [ ] `nala_readonly` ditolak `INSERT`/`UPDATE`/`DELETE`, `nala_writer` ditolak `SELECT` — dua arah, bukan cuma satu
- [ ] Halaman `/data-operasional` menampilkan data yang ada dan berhasil menerima data baru lewat kedua form
- [ ] Sudah ada beberapa baris data operasional sungguhan (ditambahkan lewat form, bukan SQL manual) sebagai bahan uji Module 25 dan seterusnya

## Kesimpulan

Module ini menyiapkan fondasi data operasional NALA dengan filosofi yang konsisten dengan Module 9 (Knowledge Base): sumber data baru diperkenalkan lewat halaman web yang staff pakai sendiri, bukan data yang tiba-tiba "sudah ada" lewat skrip seeder. Pemisahan role baca/tulis (`nala_readonly`/`nala_writer`) disiapkan sejak awal — supaya begitu Module 24 (LangGraph Agent) dan Module 25 (SQL Tool) dibangun di atasnya, fondasi keamanannya sudah teruji, bukan ditambal belakangan.

Module 24 selanjutnya membangun agent LangGraph (fokus pada tool dokumen SOP dulu, melanjutkan RAG chain Module 9-22) — belum menyentuh data operasional yang baru disiapkan di module ini. Module 25 baru kembali ke data ini, membangun tool SQL yang membaca lewat `nala_readonly` yang sudah ada di sini, lalu mendaftarkannya ke agent yang sudah dibangun Module 24.

---

Untuk informasi lebih lanjut, lihat [README utama](../README.md).
