# Module 19: Setup Data Operasional — PostgreSQL & UI Form

## Tujuan

Menyiapkan sumber data operasional PT Nusantara Finance (pengajuan kredit, klaim asuransi) di PostgreSQL — dengan skema tabel, pemisahan role database sejak awal, dan **halaman web untuk staff menambah data sendiri** — sebagai fondasi yang dipakai Module 21 (SQL Tool) dan seterusnya. Module ini sengaja **tidak** memakai data dummy yang di-generate otomatis lewat skrip seeder besar — datanya sedikit di awal, staff (Anda) yang menambah sisanya lewat form, supaya data yang dipakai untuk latihan terasa seperti hasil kerja nyata, bukan angka yang sudah "disiapkan" begitu saja.

## Definisi

**Data operasional** adalah data transaksional yang berubah setiap hari — pengajuan kredit, klaim asuransi — berbeda secara mendasar dari **knowledge base** (dokumen SOP/kebijakan) yang dipakai RAG sejak Module 7: dokumen SOP jarang berubah dan menjawab pertanyaan "bagaimana prosedurnya", sedangkan data operasional berubah terus dan menjawab pertanyaan "apa status transaksi ini sekarang". Bedanya bukan cuma soal seberapa sering berubah, tapi juga *tempat penyimpanan*: dokumen SOP hidup sebagai vektor di OpenSearch (Module 10), data operasional hidup sebagai baris terstruktur di PostgreSQL — dua sumber jawaban yang akan disatukan lewat agent mulai Module 20.

Module ini juga memperkenalkan pola **pemisahan role baca/tulis** sejak level database: `nala_readonly` (cuma `SELECT`) dan `nala_writer` (cuma `INSERT`) adalah dua identitas login PostgreSQL yang terpisah, masing-masing hanya bisa melakukan satu jenis operasi — bukan sekadar konvensi penamaan, tapi dipaksakan lewat `GRANT` di level database itu sendiri. Prinsip ini disebut **least privilege**: setiap komponen (baik kode Python maupun manusia lewat form) memakai identitas dengan hak akses paling minim yang masih cukup untuk tugasnya, supaya kesalahan di satu lapisan kode tidak otomatis berarti data bisa diubah/dihapus sembarangan.

```mermaid
flowchart LR
    S["db/seed.sql<br/>(migrasi)"] --> T["Tabel: pengajuan_kredit,<br/>klaim_asuransi"]
    S --> R1["Role nala_readonly<br/>(hanya SELECT)"]
    S --> R2["Role nala_writer<br/>(hanya INSERT)"]
    F["Staff isi form<br/>/data-operasional"] -->|"pakai nala_writer"| T
    Q["Tool SQL (Module 21)"] -->|"pakai nala_readonly"| T
```

## Hasil Akhir yang Diharapkan

- Service `postgres` berjalan sehat (`docker compose ps` menunjukkan `healthy`), dengan 2 tabel: `pengajuan_kredit`, `klaim_asuransi`
- Seed awal **minimal** (2-3 baris per tabel) — cukup untuk memverifikasi skema jalan, bukan dataset lengkap
- Dua role database terpisah sejak module ini: `nala_readonly` (cuma `SELECT`, dipakai agent/SQL tool di Module 21) dan `nala_writer` (cuma `INSERT`, dipakai form UI) — keduanya **tidak** bisa saling melakukan operasi milik peran yang lain, diverifikasi langsung lewat `psql`
- Halaman baru `/data-operasional` (mengikuti pola `upload.html` Module 13) — form tambah pengajuan kredit & klaim asuransi, plus tabel daftar data yang sudah ada
- Staff sudah menambah beberapa data operasional sungguhan lewat form (bukan lewat SQL manual atau seeder) sebagai bahan uji Module 21 dan seterusnya

## 1. Kenapa Bukan Seeder Biasa

Pola yang lazim dipakai untuk data dummy adalah skrip seeder — satu file SQL/Python yang di-*generate* sekali, berisi puluhan baris data fiktif, dijalankan otomatis saat container pertama kali dibuat. Itu cepat, tapi py punya konsekuensi pedagogis yang kurang pas untuk module ini: kita tidak pernah benar-benar "menyentuh" bagaimana data operasional itu masuk ke sistem — datanya sudah ada begitu saja, seolah-olah turun dari langit.

Module ini sengaja membalik itu: **schema dan role dibuat lewat migrasi (`db/seed.sql`), tapi isinya cuma 2-3 baris starting point** — cukup untuk memverifikasi skema tidak salah tanpa perlu tabel kosong sama sekali. Sisanya, staff (Anda) input sendiri lewat halaman `/data-operasional` yang dibangun di module ini — persis pola yang sudah dipakai sejak Module 7 (Knowledge Base: kita upload dokumen sendiri lewat form, bukan dokumen yang sudah di-mount otomatis dalam jumlah besar).

```mermaid
flowchart LR
    A["docker compose up<br/>(container pertama kali dibuat)"] --> B["db/seed.sql dijalankan otomatis<br/>oleh image Postgres"]
    B --> C["CREATE TABLE<br/>+ 2-3 baris starting point<br/>+ CREATE ROLE readonly/writer"]
    C --> D["Staff buka /data-operasional<br/>isi form, tambah data sendiri"]
    D --> E["Data operasional siap dipakai<br/>Module 21 (SQL Tool)"]
```

## 2. Dua Role Sejak Awal: Baca vs Tulis

Sebelum menulis kode tool query (baru Module 21), pemisahan role database sudah disiapkan di module ini — supaya begitu Module 21 dibangun, `nala_readonly` sudah ada dan siap dipakai, tidak perlu bolak-balik migrasi:

- **`nala_writer`** — cuma `GRANT INSERT`, dipakai **jalur manusia** (form `/data-operasional`, endpoint `POST` di `app/main.py`). Manusia (staff) yang menambah data lewat form, bukan LLM.
- **`nala_readonly`** — cuma `GRANT SELECT`, disiapkan di sini tapi **belum dipakai** sampai Module 21 (SQL Tool) membangun kode yang membacanya.

Keduanya **saling tidak bisa** melakukan operasi milik peran lain — `nala_writer` tidak bisa `SELECT`, `nala_readonly` tidak bisa `INSERT`/`UPDATE`/`DELETE`. Ini bukan detail kecil: artinya kalaupun nanti ada bug di kode Python yang secara tidak sengaja mencampur kedua koneksi, PostgreSQL sendiri yang menolak operasi yang salah — pertahanan berlapis yang sama seperti yang sudah dijelaskan lebih detail nanti di Module 21 Bagian 2.

## 3. Struktur Kode yang Ditambahkan

Dua Tahap: **Tahap A** menyiapkan service PostgreSQL, skema, seed minimal, dan dua role. **Tahap B** membangun halaman `/data-operasional` (form + tabel daftar data).

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
      - ./db/seed.sql:/docker-entrypoint-initdb.d/01-seed.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U nala_admin -d nala_operasional"]
      interval: 5s
      timeout: 5s
      retries: 10
```

Tambah `postgres_data:` ke `volumes:` top-level, dan `postgres: {condition: service_healthy}` ke `depends_on` service `api` (bersama `ollama`/`opensearch` yang sudah ada dari module-module sebelumnya — kalau `depends_on` versi Anda masih bentuk list sederhana, ubah jadi bentuk mapping supaya bisa memakai `condition`).

`POSTGRES_PASSWORD` sengaja pakai env var dengan default eksplisit `changeme_dev_only` — cukup untuk laptop training, **bukan** pola aman untuk deployment sungguhan (dibahas lagi soal secret management di Module 23). Image resmi `postgres` otomatis menjalankan file apa pun di `/docker-entrypoint-initdb.d/` **satu kali saat volume database masih kosong** — itu cara `db/seed.sql` (Langkah 2) ter-load otomatis tanpa langkah manual tambahan.

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

-- Role read-only: dipakai agent (tool query_data_operasional, dibangun Module 21) — hanya bisa SELECT
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

<details>
<summary><strong>Pakai Claude Code? Salin prompt berikut, paste untuk eksekusi Langkah 1-2</strong></summary>

```
Tambah service PostgreSQL, skema data operasional minimal, dan dua
role terpisah (read-only vs write-only) — Module 19, Tahap A.

GOAL:
1. Di resources/starter-code/day-4/nala/docker-compose.yml: tambah
   service baru "postgres" (image postgres:16, POSTGRES_DB=
   nala_operasional, POSTGRES_USER=nala_admin, POSTGRES_PASSWORD dari
   env var POSTGRES_ADMIN_PASSWORD default changeme_dev_only, port
   5432:5432, volume postgres_data:/var/lib/postgresql/data DAN
   ./db/seed.sql:/docker-entrypoint-initdb.d/01-seed.sql, healthcheck
   pg_isready). Tambah postgres_data ke volumes: top-level. Tambah
   depends_on postgres (condition service_healthy) ke service api
   (ubah depends_on api ke bentuk mapping kalau masih list).
2. Buat resources/starter-code/day-4/nala/db/seed.sql: CREATE TABLE
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
- Ini tabel BARU, terpisah dari OpenSearch/vector store Module 7-18.
- nala_readonly BELUM dipakai kode apa pun sampai Module 21 (SQL Tool)
  — di module ini cuma dibuat role-nya saja.

GUARDRAIL:
- JANGAN ubah service lain (ollama, opensearch, airflow, langfuse,
  api) selain menambah depends_on di api.
- JANGAN isi data dummy lebih dari 2-3 baris per tabel — sengaja
  minimal, sisanya ditambah lewat UI di Tahap B.
- JANGAN gunakan data nasabah sungguhan — harus dummy/fiktif.
```

</details>

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

Dua fungsi terpisah, masing-masing pakai DSN role yang berbeda — `get_connection()` (readonly) dipakai untuk **menampilkan** data di halaman `/data-operasional` dan nanti tool SQL Module 21, `get_write_connection()` (writer) dipakai **hanya** oleh endpoint `POST` form di Langkah 5. Tambahkan juga dua env var ini ke service `api` di `docker-compose.yml`:

```yaml
# docker-compose.yml, service api — tambahan environment
- POSTGRES_READONLY_DSN=postgresql://nala_readonly:readonly_dev_only@postgres:5432/nala_operasional
- POSTGRES_WRITER_DSN=postgresql://nala_writer:writer_dev_only@postgres:5432/nala_operasional
```

**Langkah 4 — Buat `app/templates/data_operasional.html`**

Mengikuti pola `upload.html` (Module 13) — form di atas, tabel daftar data di bawah, untuk **kedua** tabel (`pengajuan_kredit`, `klaim_asuransi`):

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

Tambah juga link nav baru (`| <a href="/data-operasional">Data Operasional</a>`) ke `chat.html` dan `upload.html` yang sudah ada, dan sedikit CSS baru (`form`, `.data-table`) di `app/static/style.css` — lihat kode lengkap di akhir module ini.

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

**▶️ Jalankan & lihat hasilnya**

```bash
docker compose up --build -d postgres api
```

Buka `http://localhost:8000/data-operasional` di browser — halaman menampilkan 2 baris pengajuan kredit dan 1 baris klaim asuransi (seed dari Tahap A), dengan dua form di atasnya. Coba isi form "Tambah Pengajuan Kredit" dengan data baru, submit — baris baru harus langsung muncul di tabel di bawahnya tanpa reload manual kedua kalinya.

✅ **Indikator sukses**: form berhasil menambah data (terlihat di tabel setelah submit), dan data tersimpan permanen — refresh halaman, data yang baru ditambahkan tetap ada.

<details>
<summary><strong>Pakai Claude Code? Salin prompt berikut, paste untuk eksekusi Langkah 3-5</strong></summary>

```
Bangun halaman web /data-operasional untuk staff menambah data
pengajuan kredit dan klaim asuransi secara manual — Module 19,
Tahap B.

GOAL:
1. Di resources/starter-code/day-4/nala/requirements.txt: tambah baris
   psycopg[binary]==3.2.3
2. Buat resources/starter-code/day-4/nala/app/db.py: dua konstanta DSN
   dari env var (POSTGRES_READONLY_DSN, POSTGRES_WRITER_DSN, dengan
   default masing-masing memakai nala_readonly/nala_writer), dua fungsi
   get_connection() dan get_write_connection() yang psycopg.connect()
   ke DSN masing-masing (connect_timeout=5).
3. Buat resources/starter-code/day-4/nala/app/templates/data_operasional.html:
   dua form (pengajuan kredit, klaim asuransi) dengan field sesuai
   kolom tabel masing-masing, plus dua tabel daftar data di bawah tiap
   form (loop Jinja2 atas pengajuan_kredit/klaim_asuransi dari context).
   Nav link baru "Data Operasional" ditambahkan juga ke chat.html dan
   upload.html yang sudah ada.
4. Di resources/starter-code/day-4/nala/app/main.py: import Form dari
   fastapi, dict_row dari psycopg.rows, get_connection/get_write_connection
   dari app.db. Tambah fungsi fetch_pengajuan_kredit()/fetch_klaim_asuransi()
   (SELECT via get_connection(), row_factory=dict_row). Tambah endpoint
   GET /data-operasional (render halaman dengan kedua fetch), POST
   /data-operasional/pengajuan-kredit dan POST /data-operasional/klaim-asuransi
   (terima Form(...) sesuai kolom tabel, INSERT via get_write_connection(),
   conn.commit(), lalu render ulang halaman dengan pesan sukses + data
   terbaru).
5. Tambah CSS sederhana untuk form/table di app/static/style.css.

CONTEXT:
- app/db.py (get_connection untuk readonly, get_write_connection untuk
  writer) sudah dibuat di Tahap A sebelumnya — kalau belum, buat sesuai
  Langkah 3.
- Role nala_readonly dan nala_writer sudah ada di database sejak
  Tahap A (db/seed.sql).

GUARDRAIL:
- JANGAN pakai get_write_connection() untuk operasi SELECT/fetch —
  role nala_writer tidak punya izin SELECT, akan gagal.
- JANGAN pakai get_connection() (readonly) untuk INSERT — role
  nala_readonly tidak punya izin INSERT, akan gagal.
- JANGAN ubah endpoint /chat/stream, /upload, /health yang sudah ada
  (endpoint /chat belum ada sampai Module 20 membuatnya).
```

</details>

**📄 Kode lengkap Module 19** (`docker-compose.yml` bagian `postgres`, `db/seed.sql`, `app/db.py`, `app/templates/data_operasional.html`, potongan relevan `app/main.py` — sudah ditampilkan utuh di Langkah 1-5 di atas).

## 4. Hasil Uji Nyata

Setup ini sudah diuji langsung, bukan cuma teori:

- **Pemisahan role dua arah terbukti bekerja**: `nala_readonly` ditolak saat mencoba `DELETE` (`permission denied for table pengajuan_kredit`), dan `nala_writer` **juga** ditolak saat mencoba `SELECT` — bukti kedua role benar-benar terisolasi sesuai perannya masing-masing, bukan cuma dibatasi di satu arah.
- **Form UI diuji end-to-end**: data baru ditambahkan lewat `POST /data-operasional/pengajuan-kredit` dan `POST /data-operasional/klaim-asuransi`, langsung terlihat di tabel tanpa restart container apa pun.
- **Data operasional untuk latihan Module 21 dst. sudah terisi lewat form** (bukan seeder): 7 baris `pengajuan_kredit` (variasi status: `pending`×3, `disetujui`×1, `pencairan`×1, `ditolak`×2) dan 4 baris `klaim_asuransi`, dengan beberapa `nasabah_id` sengaja muncul di kedua tabel (mis. nasabah yang kreditnya ditolak **dan** punya klaim asuransi) — bahan uji untuk skenario gabungan RAG+SQL di Module 22.

## 5. Checkpoint Praktik

Langkah eksekusi lengkap ada di bagian **Panduan Praktik** di bawah (Langkah 1-5). Yang perlu dipastikan sebelum lanjut ke Module 20:

- [ ] Service `postgres` sehat (`healthy`), 2 tabel terbentuk dengan seed minimal (2 baris + 1 baris)
- [ ] `nala_readonly` ditolak `INSERT`/`UPDATE`/`DELETE`, `nala_writer` ditolak `SELECT` — dua arah, bukan cuma satu
- [ ] Halaman `/data-operasional` menampilkan data yang ada dan berhasil menerima data baru lewat kedua form
- [ ] Sudah ada beberapa baris data operasional sungguhan (ditambahkan lewat form, bukan SQL manual) sebagai bahan uji Module 21 dan seterusnya

## Kesimpulan

Module ini menyiapkan fondasi data operasional NALA dengan filosofi yang konsisten dengan Module 7 (Knowledge Base): sumber data baru diperkenalkan lewat halaman web yang staff pakai sendiri, bukan data yang tiba-tiba "sudah ada" lewat skrip seeder. Pemisahan role baca/tulis (`nala_readonly`/`nala_writer`) disiapkan sejak awal — supaya begitu Module 20 (LangGraph Agent) dan Module 21 (SQL Tool) dibangun di atasnya, fondasi keamanannya sudah teruji, bukan ditambal belakangan.

Module 20 selanjutnya membangun agent LangGraph (fokus pada tool dokumen SOP dulu, melanjutkan RAG chain Module 7-18) — belum menyentuh data operasional yang baru disiapkan di module ini. Module 21 baru kembali ke data ini, membangun tool SQL yang membaca lewat `nala_readonly` yang sudah ada di sini, lalu mendaftarkannya ke agent yang sudah dibangun Module 20.

## Panduan Praktik

> Catatan penomoran: bagian ini memakai penomoran "Langkah" tersendiri (Langkah 1-5) yang berbeda dari "Langkah 1-5" di dalam Bagian 3 Tahap A/B di atas — keduanya kebetulan bernomor sama tapi berasal dari dua urutan yang terpisah. Penomoran "Langkah" di Panduan Praktik ini juga bersambung lintas-module (Module 20 melanjutkan dari Langkah 6, dst.) sebagai peninggalan dari saat panduan ini masih satu dokumen gabungan Module 19-23.

**Panduan Praktik — Module 19: Setup Data Operasional — PostgreSQL & UI Form**

#### Folder kode belum ada — Anda akan membangunnya dari salinan Module 18

Berbeda dari module-module sebelumnya yang sudah punya `resources/starter-code/day-N/nala/` siap pakai, **`resources/starter-code/day-4/nala/` belum ada** saat panduan ini ditulis (lihat Module 19 bagian Tujuan di atas). Langkah 1 di bawah membangunnya dengan menyalin seluruh isi `resources/starter-code/day-3/nala/` (hybrid search, reranking, evaluasi RAG, Langfuse — dari Module 15-18), lalu module demi module (Module 19-23) di bagian Panduan Praktik berikutnya menambah lapisan data operasional/agent/tool/RBAC di atasnya — pola yang sama seperti panduan praktik Module 5 menyalin dari Module 1-4.

Karena belum ada kode referensi (`day-4-reference/`) untuk rangkaian Module 19-23, setiap kali panduan ini menyebut "kode lengkap", itu merujuk ke bagian **"📄 Kode lengkap"** di `materi.md` module terkait — bukan folder referensi terpisah seperti sebelumnya.

### Prasyarat
- Sudah menyelesaikan **Module 1-18** (`llama3.2:3b` sudah biasa dipakai, `resources/starter-code/day-3/nala/` berjalan dengan hybrid search + reranking + evaluasi + Langfuse)
- Docker Desktop sudah dialokasikan resource yang cukup — lihat catatan RAM di bawah

#### Container Module 15-18 tetap dipakai — bukan project terpisah

Sama seperti transisi antar-module sebelumnya, folder `day-2/nala`, `day-3/nala`, dan `day-4/nala` semuanya bernama `nala` — Docker Compose memakai **nama folder** (bukan path lengkap) sebagai *project name* secara default, jadi ketiganya diperlakukan sebagai **project yang sama**. Ini disengaja: kalau tiap kelompok module punya project Docker terpisah, `ollama`/`opensearch`/`airflow` akan berjalan berkali-kali lipat, membengkakkan RAM tanpa perlu — satu project yang tumbuh bertahap jauh lebih hemat, dan data (index OpenSearch, model Ollama yang sudah di-pull) otomatis ikut terbawa.

Setelah `day-4/nala/docker-compose.yml` dipakai, jalankan `docker compose` **dari folder `day-4/nala/`** untuk seterusnya:

```bash
cd resources/starter-code/day-4/nala
docker compose up --build -d
```

`day-4/nala` memakai port yang sama (`8000` api, `11434` ollama, `9200` opensearch, `8080` airflow) plus port baru `5432` untuk PostgreSQL — semuanya otomatis ter-declare begitu compose dijalankan dari sini, tidak ada langkah "matikan dulu" yang diperlukan (compose merecreate container yang berubah definisinya, container lain yang tidak berubah tetap jalan apa adanya).

#### Catatan penting: naikkan alokasi RAM Docker Desktop lagi

Rangkaian Module 19-23 menambahkan **satu service baru**: **PostgreSQL** (data operasional). Dibanding OpenSearch/Airflow, PostgreSQL relatif ringan sendirian — tapi ia berjalan **bersamaan** dengan seluruh stack Module 5-18 yang sudah ada (Ollama, OpenSearch, Airflow, FastAPI) plus proses LangGraph agent yang memanggil Ollama berkali-kali per pertanyaan (multi-turn tool-calling, lihat Module 20-22).

| Setting | Minimal rangkaian Module 19-23 | Direkomendasikan | Alasan |
|---|---|---|---|
| **Memory (RAM)** | 16 GB | 16 GB+ (32 GB+ kalau ingin coba `qwen2.5:7b`, lihat Module 22 Bagian 4.b) | PostgreSQL menambah beban kecil-menengah di atas stack Module 5-18 yang sudah berat; agent tool-calling memanggil Ollama beberapa kali per pertanyaan (bukan sekali seperti sebelumnya), menambah beban CPU sesaat, bukan RAM tambahan besar. |
| **CPUs** | 4 | 4+ | 5 service aktif sekaligus (ollama, opensearch, airflow, postgres, api), ditambah beberapa panggilan Ollama berurutan per request agent. |
| **Disk image size** | 100 GB | 120 GB+ | Image `postgres:16` relatif kecil (~400MB), tapi menumpuk di atas seluruh image module-module sebelumnya yang sudah ada. |

Kalau sudah di 16GB+ sejak Module 5-18, tidak perlu diubah lagi kecuali ingin mencoba `qwen2.5:7b` (Module 22 Bagian 4.b).

### Langkah 1: Salin dari Module 18, masuk ke folder starter code

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

### Langkah 2: Service PostgreSQL, skema, seed minimal, dua role (Module 19 Tahap A)

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

### Langkah 3: Koneksi database — `app/db.py` (Module 19 Tahap B Langkah 3)

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

### Langkah 4: Halaman `/data-operasional` — form + tabel daftar (Module 19 Tahap B Langkah 4-5)

Ikuti Module 19 Bagian 3 Tahap B Langkah 4-5 (`app/templates/data_operasional.html`, endpoint `GET /data-operasional` + `POST /data-operasional/pengajuan-kredit` + `POST /data-operasional/klaim-asuransi` di `app/main.py`, plus nav link baru di `chat.html`/`upload.html`).

```bash
docker compose up --build -d postgres api
```

Buka `http://localhost:8000/data-operasional` di browser.

✅ **Indikator sukses**: halaman menampilkan 2 baris pengajuan kredit dan 1 baris klaim asuransi (seed dari Langkah 2), dengan dua form di atasnya, tidak ada error render.

### Langkah 5: Isi data operasional lewat form (bahan uji Module 21 dan seterusnya)

Tambahkan data lewat kedua form di `/data-operasional` sampai datanya representatif untuk latihan module-module berikutnya — bukan lewat SQL manual atau seeder. Target yang dipakai di contoh-contoh Module 20-23 selanjutnya (lihat Module 19 Bagian 4 "Hasil Uji Nyata"): total **7 baris** `pengajuan_kredit` (variasi status: `pending`×3, `disetujui`×1, `pencairan`×1, `ditolak`×2 — dua di antaranya sudah ada dari seed Langkah 2: `N-00231` `pending` dan `N-00305` `ditolak` dengan `alasan_penolakan` "Skor kredit di bawah ambang batas minimum", jadi tambahkan **5 baris lagi** lewat form) dan total **4 baris** `klaim_asuransi` (1 sudah ada dari seed — `N-00305`, jenis `kendaraan`, `disetujui` — tambahkan **3 baris lagi**), dengan minimal satu `nasabah_id` yang sengaja muncul di kedua tabel (mis. `N-00305`, yang kreditnya ditolak **dan** punya klaim asuransi — bahan uji skenario gabungan RAG+SQL di Module 22).

```bash
docker compose exec postgres psql -U nala_admin -d nala_operasional -c "SELECT COUNT(*) FROM pengajuan_kredit;"
docker compose exec postgres psql -U nala_admin -d nala_operasional -c "SELECT COUNT(*) FROM klaim_asuransi;"
```

✅ **Indikator sukses**: `7` dan `4`, dan refresh halaman `/data-operasional` menunjukkan seluruh baris yang baru ditambahkan tetap ada (data tersimpan permanen). Module 19 selesai — lanjut ke bagian Panduan Praktik di materi Module 20.

### Troubleshooting

- **`psycopg.OperationalError: connection to server ... failed`**: kemungkinan besar DSN masih memakai `localhost` padahal dipanggil dari dalam container `api` — harus memakai nama service Docker Compose (`postgres`), lihat catatan di Langkah 3. Cek juga `postgres` sudah `healthy` (`docker compose ps`).
- **`permission denied for table ...` padahal seharusnya diizinkan**: cek role/DSN yang dipakai — form `/data-operasional` (Module 19) harus memakai `nala_writer`, tool SQL (Module 21) harus memakai `nala_readonly`; tertukar salah satunya akan memicu `permission denied` untuk operasi yang seharusnya sah.
- **Seed data tidak berubah setelah mengedit `db/seed.sql`**: script init PostgreSQL cuma jalan sekali saat volume database masih kosong — kalau volume `postgres_data` sudah ada dari percobaan sebelumnya, `docker compose up` **tidak** menjalankan ulang seed. Hapus volume dulu (`docker compose down && docker volume rm nala_postgres_data`) lalu `docker compose up -d --build postgres` lagi. Ini juga penyebab paling umum kalau tabel/role baru "tidak muncul" setelah mengikuti Langkah 2.
- **`docker compose exec postgres psql -U nala_admin ...` minta password / gagal autentikasi**: pastikan env var `POSTGRES_ADMIN_PASSWORD` (kalau di-override di `.env` atau shell) konsisten dengan yang dipakai saat container `postgres` dibuat — kalau volume sudah lama ada dengan password lama, password baru di env var tidak otomatis berlaku sampai volume direset (sama seperti poin seed data di atas).
- **Error umum lain** (`no configuration file provided`, `failed to read dockerfile`, port sudah dipakai, dsb.): lihat bagian Panduan Praktik > Troubleshooting di materi.md module-module sebelumnya (Module 5-14) — penyebab dan solusinya sama, tidak spesifik rangkaian Module 19-23.

---

Untuk informasi lebih lanjut, lihat [README utama](../README.md).
