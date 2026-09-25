# Module 27: RBAC & Audit Logging

## Tujuan

Membatasi akses tool SQL (Module 25) berdasarkan role staff (RBAC) dan mencatat setiap percobaan akses — baik yang diizinkan maupun ditolak — ke audit trail permanen, sebagai penutup rangkaian Module 23-27 yang relevan untuk konteks kepatuhan institusi finansial.

## Definisi

**RBAC (Role-Based Access Control)** adalah pola pembatasan akses berdasarkan **peran** (role) yang dipegang seseorang, bukan identitas individunya satu per satu — di NALA, tiga role (`staff_umum`, `staff_finance`, `supervisor`) menentukan tool mana yang boleh dipicu, bukan siapa nama orangnya. Role ini tidak lagi datang dari body request, melainkan dari **sesi login** yang dibangun di Tahap 0 (lihat Bagian 3) — sehingga tidak bisa dipalsu client. Prinsip yang dipegang adalah **fail-safe** (deny-by-default): tanpa sesi login yang valid, request ke `/chat` ditolak (`401`) dan halaman diarahkan ke `/login` — sistem tidak pernah mengasumsikan akses saat identitas tidak jelas, kebalikan dari **fail-open** yang mengasumsikan akses penuh saat informasi tidak lengkap, karena fail-open jauh lebih berbahaya untuk sistem yang menyentuh data finansial nasabah.

**Audit logging** adalah pencatatan permanen atas setiap percobaan akses — siapa, tanya apa, tool apa, diizinkan atau ditolak, kapan — terpisah dari (dan melengkapi) RBAC: RBAC mencegah **sebelum** kejadian, audit logging mencatat **setelah** kejadian supaya bisa ditelusuri ulang kalau diaudit regulator. Tabel `audit_log` dibuat **append-only** dari sisi aplikasi — role `nala_app` yang menulisnya cuma diberi `INSERT`/`SELECT`, sengaja **tidak** diberi `UPDATE`/`DELETE` — supaya jejak yang sudah tercatat tidak bisa dihapus atau diubah lewat koneksi aplikasi mana pun, properti penting supaya audit trail tetap kredibel.

```mermaid
flowchart LR
    R["Request tanpa sesi login valid?"] -->|"fail-safe (deny)"| D["Ditolak: 401 /<br/>redirect ke /login"]
    U["Sesi login valid<br/>(role dari sesi)"] --> C{"RBAC: role berwenang<br/>untuk tool ini?"}
    C -->|"ya"| T["Tool dijalankan"]
    C -->|"tidak"| X["Ditolak, tanpa eksekusi"]
    T --> L["audit_log<br/>(append-only, nala_app)"]
    X --> L
```

## Hasil Akhir yang Diharapkan

- Role `staff_umum` ditolak saat mencoba memicu tool SQL (`query_data_operasional`), sementara `staff_finance`/`supervisor` berhasil — pengecekan role dilakukan berlapis (di `call_model` lewat filter tool, dan diverifikasi ulang di `call_tool`)
- Tool RAG tetap bisa diakses semua role tanpa pengecualian
- Tabel `audit_log` mencatat setiap percobaan tool (diizinkan maupun ditolak) beserta pertanyaan tanpa tool sama sekali — lewat role database `nala_app` yang hanya bisa `INSERT`/`SELECT`, tidak bisa `UPDATE`/`DELETE` (audit log append-only)
- `role`/`user_id` datang dari **sesi login** (Tahap 0), bukan body request — tidak bisa dipalsu client; request ke `/chat` tanpa sesi valid ditolak (`401`), halaman tanpa sesi diarahkan ke `/login` (fail-safe: deny-by-default)
- Kita paham secara eksplisit batasan yang belum diselesaikan module ini: login masih **sederhana** (user hardcoded + password plaintext di kode — cukup untuk demo, produksi butuh hash password + tabel user + session store yang lebih matang), audit logging masih sinkron (belum async/queue untuk skala produksi)

## 1. Kenapa Ini Bukan "Fitur Tambahan", Tapi Syarat untuk Data Finansial

Sampai akhir Module 26, tool `query_data_operasional` (Module 25) bisa dipicu **siapa pun** yang mengirim request ke `/chat` — tidak ada pengecekan sama sekali siapa yang bertanya, atau apakah orang itu berhak melihat data pengajuan kredit/klaim asuransi nasabah. Untuk demo dan latihan sejauh ini itu cukup, tapi PT Nusantara Finance adalah institusi finansial — di dunia nyata, sektor ini diatur ketat (OJK, dan prinsip umum tata kelola data finansial): siapa yang mengakses data nasabah, kapan, dan untuk keperluan apa **harus bisa dijawab** kalau sewaktu-waktu diaudit, baik oleh auditor internal maupun regulator eksternal.

Dua kebutuhan berbeda tapi saling melengkapi:

1. **RBAC (Role-Based Access Control)** — mencegah **sebelum** kejadian: staff yang tidak berwenang tidak boleh bisa memicu tool yang mengakses data operasional sama sekali, bukan cuma "seharusnya tidak bertanya yang aneh-aneh".
2. **Audit logging** — mencatat **setelah** kejadian: kalaupun akses terjadi (baik yang diizinkan maupun yang ditolak RBAC), ada jejak permanen siapa, tanya apa, tool apa yang terlibat, dan kapan — supaya bisa ditelusuri ulang.

```mermaid
sequenceDiagram
    participant U as Staff (role tertentu)
    participant API as POST /chat
    participant AG as Agent (LangGraph)
    participant SQL as Tool SQL (Module 25)
    participant DB as PostgreSQL
    participant LOG as audit_log

    U->>API: POST /chat {"message": "..."} + cookie sesi
    API->>API: baca role & user_id dari sesi (get_current_user)
    API->>AG: invoke(state termasuk role dari sesi)
    AG->>AG: call_model memilih tool sesuai role
    alt role tidak berwenang untuk SQL
        AG->>AG: call_tool menolak, tanpa query ke DB
    else role berwenang
        AG->>SQL: query_data_operasional(...)
        SQL->>DB: SELECT (role nala_readonly)
        DB-->>SQL: hasil
    end
    AG-->>API: jawaban akhir + daftar tool yang dipanggil/ditolak
    API->>LOG: catat: user_id, role, pertanyaan, tool, izin/ditolak, waktu
    API-->>U: jawaban
```

⚠️ **Batasan yang jujur perlu disampaikan sejak awal**: berbeda dari rencana kurikulum awal (yang mengirim `role`/`user_id` lewat body request supaya sederhana), module ini **membangun login/session sederhana lebih dulu** di **Tahap 0** — supaya `role` dan `user_id` datang dari **sesi yang sudah terautentikasi** (signed session cookie yang divalidasi server), bukan dari body JSON yang bisa ditulis siapa saja. Ini menutup celah paling berbahaya: kalau role datang dari body, siapa pun bisa mengaku `role: "supervisor"` dan RBAC ini jadi tidak berarti. **Namun login-nya masih sederhana**: daftar user *hardcoded* di kode dengan password plaintext, cukup untuk mendemonstrasikan prinsip "role dari sesi", **belum** production-grade — produksi butuh hash password (bcrypt/argon2), tabel user yang bisa dikelola, dan pertimbangan session store yang lebih matang. Batasan ini disebut lagi di Bagian 5.

## 2. Desain: Role dan Tool yang Diizinkan

| Role | `cari_dokumen_sop` (RAG) | `query_data_operasional` (SQL) | Contoh jabatan |
|---|---|---|---|
| `staff_umum` | ✅ Diizinkan | ❌ Ditolak | Staff customer service umum, hanya perlu jawab pertanyaan prosedur |
| `staff_finance` | ✅ Diizinkan | ✅ Diizinkan | Staff yang menangani pengajuan kredit/klaim, perlu lihat status transaksi |
| `supervisor` | ✅ Diizinkan | ✅ Diizinkan | Sama seperti `staff_finance` untuk cakupan Module 23-27 — di produksi biasanya juga punya akses laporan agregat lebih luas, di luar cakupan latihan ini |

Semua role tetap bisa memakai tool RAG — dokumen SOP bukan data sensitif per-nasabah, wajar diakses siapa pun yang bekerja di perusahaan. Yang dibatasi murni akses ke `query_data_operasional`, karena tool itu menyentuh data transaksi nasabah.

## 3. Struktur Kode yang Ditambahkan

Lima tahap: **Tahap 0** membangun fondasi identitas — login/session sederhana supaya `role`/`user_id` datang dari sesi terautentikasi (bukan body request), **Tahap A** menambah tabel `audit_log` dan role database khusus untuk menulis log, **Tahap B** membangun fungsi pencatatan audit, **Tahap C** menambahkan pengecekan RBAC ke agent (dengan pertahanan berlapis, meniru pola Module 25), **Tahap D** menyambungkan semuanya ke `/chat` — membaca `role`/`user_id` dari sesi Tahap 0 lalu memanggil audit logging.

### Tahap 0 — Login & Session (fondasi identitas)

**Prasyarat sebelum mulai:** Module 26 selesai — agent dengan routing dua-tool dan pengaman `MAX_TOOL_ROUNDS`/`force_answer` harus sudah jalan sebelum mulai di sini.

Sebelum RBAC ada artinya, `role` harus datang dari tempat yang **tidak bisa dipalsu client**. Kalau `role` dikirim di body request, siapa pun bisa mengetik `"role": "supervisor"` dan seluruh RBAC di Tahap C-D jadi hiasan belaka. Maka Tahap 0 membangun login sederhana: server memvalidasi username+password, menyimpan `user_id`+`role` di **signed session cookie** (Starlette `SessionMiddleware`), dan seluruh endding membaca identitas dari sesi itu — bukan dari body.

**Langkah 0 — Buat `app/auth.py`, halaman login, dan pasang session di `app/main.py`**

Pertama, store user demo + helper baca sesi di `app/auth.py`:

```python
# app/auth.py
from fastapi import Request

# username -> {password, role, nama}. DEMO ONLY: hardcoded + plaintext.
# Produksi: simpan hash password (bcrypt/argon2) di DB, bukan di kode.
USERS = {
    "budi.umum": {"password": "nala123", "role": "staff_umum", "nama": "Budi Santoso"},
    "sari.finance": {"password": "nala123", "role": "staff_finance", "nama": "Sari Melati"},
    "andi.super": {"password": "nala123", "role": "supervisor", "nama": "Andi Wijaya"},
}

ROLE_LABELS = {
    "staff_umum": "Staff Umum",
    "staff_finance": "Staff Finance",
    "supervisor": "Supervisor",
}


def verify_user(username: str, password: str) -> dict | None:
    user = USERS.get(username)
    if user and user["password"] == password:
        return {"user_id": username, "role": user["role"], "nama": user["nama"]}
    return None


def get_current_user(request: Request) -> dict | None:
    """Baca user aktif dari sesi. Return None kalau belum login."""
    user_id = request.session.get("user_id")
    role = request.session.get("role")
    if not user_id or not role:
        return None
    return {
        "user_id": user_id,
        "role": role,
        "nama": request.session.get("nama", user_id),
        "role_label": ROLE_LABELS.get(role, role),
    }
```

Lalu halaman login `app/templates/login.html` (form + daftar akun demo):

```html
<!-- app/templates/login.html (ringkas) -->
<form action="/login" method="post" class="login-form">
    <label>Username <input type="text" name="username" required autofocus></label>
    <label>Password <input type="password" name="password" required></label>
    <button type="submit">Masuk</button>
</form>
{% if error %}<p class="error">{{ error }}</p>{% endif %}
```

Terakhir, pasang `SessionMiddleware` + endpoint login/logout + proteksi halaman di `app/main.py`:

```python
# app/main.py — tambahan
from fastapi.responses import RedirectResponse  # tambah ke import responses yang sudah ada
from starlette.middleware.sessions import SessionMiddleware
from app.auth import get_current_user, verify_user

# SessionMiddleware menandatangani cookie sesi (via itsdangerous) sehingga
# isinya (user_id, role) tidak bisa dipalsu client. Secret dev-only default;
# override lewat env SESSION_SECRET di produksi.
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SESSION_SECRET", "nala-dev-session-secret-change-me"),
    max_age=8 * 60 * 60,  # 8 jam
)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if get_current_user(request):
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request, "login.html", {"error": None})


@app.post("/login")
def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    user = verify_user(username, password)
    if not user:
        return templates.TemplateResponse(
            request, "login.html", {"error": "Username atau password salah."}, status_code=401
        )
    request.session["user_id"] = user["user_id"]
    request.session["role"] = user["role"]
    request.session["nama"] = user["nama"]
    return RedirectResponse("/", status_code=303)


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)
```

Setiap halaman (`/`, `/upload`, `/data-operasional` + POST-nya) mendapat pengawal di baris pertama — belum login → arahkan ke `/login`:

```python
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    # ...lalu teruskan {"user": user} ke TemplateResponse untuk banner "Masuk sebagai ..."
```

Sedangkan endpoint API `/chat` dan `/chat/stream` menolak dengan **401** kalau tidak ada sesi (dipanggil dari halaman yang sudah terproteksi, jadi cukup balas error, bukan redirect):

```python
    if not get_current_user(http_request):
        raise HTTPException(status_code=401, detail="Belum login")
```

Dua penyesuaian pendukung:

- **`Dockerfile`** — tambah `itsdangerous` sebagai **layer terpisah** (bukan menambahnya ke `requirements.txt`):

  ```dockerfile
  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt
  # itsdangerous di layer sendiri supaya layer requirements.txt di atas
  # (torch/sentence-transformers yang besar) tetap kena cache & tidak
  # diunduh ulang saat rebuild.
  RUN pip install --no-cache-dir --timeout 120 --retries 10 itsdangerous==2.2.0
  COPY app ./app
  ```

  `SessionMiddleware` memakai `itsdangerous` untuk menandatangani cookie; Starlette **tidak** memasangnya otomatis, jadi tanpa dependency ini `api` gagal di request pertama (bukan saat import — `add_middleware` menunda instansiasi). Kenapa layer terpisah, bukan `requirements.txt`: kalau `itsdangerous` ditambah ke `requirements.txt`, layer `pip install -r requirements.txt` ikut ter-invalidasi sehingga **torch (~230MB) + sentence-transformers ikut diunduh ulang** — berisiko gagal di jaringan yang tidak stabil (timeout). Dengan layer terpisah, rebuild hanya mengunduh `itsdangerous` (~15KB). Karena ada dependency baru, **rebuild wajib** (`docker compose build api` — **tanpa** `--no-cache`, supaya cache layer besar tetap dipakai).
- **`docker-compose.yml`** (service `api`) — tambah `- SESSION_SECRET=${SESSION_SECRET:-nala-dev-session-secret-change-me}` supaya secret penandatangan bisa di-override lewat `.env` di produksi (default dev cukup untuk latihan).

Kenapa dibaca dari sesi, bukan body: signed cookie ditandatangani dengan `SESSION_SECRET` yang cuma diketahui server — client bisa melihat isinya tapi tidak bisa mengubah `role` tanpa membatalkan tanda tangan. Inilah yang membuat RBAC di Tahap C-D bermakna. (Prinsip *least privilege* yang sama seperti role database di Module 23/25: identitas tidak boleh berasal dari pihak yang diaudit.)

**▶️ Jalankan & lihat hasilnya**

```bash
docker compose up -d --build api
```

Lalu buka `http://localhost:8000` di browser.

✅ **Indikator sukses** *(sudah diverifikasi runtime 2026-09-25)*:
- Buka `/` tanpa login → otomatis diarahkan ke `/login` (`303`).
- Login `budi.umum` / `nala123` → masuk ke chat, muncul banner "Masuk sebagai **Budi Santoso** [Staff Umum]"; `sari.finance` → [Staff Finance]; `andi.super` → [Supervisor].
- Password salah → halaman login tampil ulang dengan pesan "Username atau password salah." (`401`).
- `GET /logout` → kembali ke `/login`; buka `/` lagi dengan cookie lama → tetap diarahkan ke `/login` (sesi benar-benar di-clear).
- `curl http://localhost:8000/chat -X POST -H 'Content-Type: application/json' -d '{"message":"halo"}'` (tanpa cookie sesi) → balas `401`.

**Skenario uji per user**

Tiga akun demo mewakili tiga role. Kolom **Login** sudah diverifikasi runtime (2026-09-25); kolom **RAG** dan **Data operasional (SQL)** menjadi berbeda per role **setelah Tahap C-D** dipasang (di Tahap 0 saja, sebelum Tahap C, semua user yang login masih dapat agent penuh):

| User | Password | Role | Login (Tahap 0 ✅) | Tanya SOP/prosedur (RAG) | Tanya status/data nasabah (SQL) |
|---|---|---|---|---|---|
| `budi.umum` | `nala123` | `staff_umum` | ✅ banner "Budi Santoso [Staff Umum]" | ✅ dijawab | ❌ **ditolak** tanpa karangan — audit `query_data_operasional / f` (kalau model panggil tool) atau `NULL / t` (kalau model menolak sendiri); keduanya aman (Bagian 4.c) |
| `sari.finance` | `nala123` | `staff_finance` | ✅ banner "Sari Melati [Staff Finance]" | ✅ dijawab | ✅ dijawab + data; audit `query_data_operasional / t` |
| `andi.super` | `nala123` | `supervisor` | ✅ banner "Andi Wijaya [Supervisor]" | ✅ dijawab | ✅ dijawab + data; audit `query_data_operasional / t` |

Template perintah — ganti `USER` sesuai baris tabel (`budi.umum` / `sari.finance` / `andi.super`); password sama semua (`nala123`):

```bash
USER=sari.finance   # ganti sesuai user yang mau diuji

# 1. Login, simpan cookie sesi
curl -c /tmp/nala_$USER.txt -X POST http://localhost:8000/login \
  -d "username=$USER&password=nala123"

# 2. Pertanyaan prosedur (RAG) — semua role boleh
curl -b /tmp/nala_$USER.txt -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"message": "Apa syarat pengajuan kredit?"}'

# 3. Pertanyaan data operasional (SQL) — staff_finance/supervisor berhasil;
#    staff_umum mendapat "Akses ditolak..." + audit akses_diizinkan=f (Bagian 4.c)
curl -b /tmp/nala_$USER.txt -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"message": "Berapa banyak pengajuan kredit yang statusnya pending?"}'

# 4. Cek jejak audit (setelah Tahap D) — user_id harus = username sesi
docker compose exec postgres psql -U nala_admin -d nala_operasional -c \
  "SELECT user_id, role, tool_dipanggil, akses_diizinkan FROM audit_log ORDER BY id DESC LIMIT 3;"
```

✅ **Indikator sukses per user**:
- Login ketiga user + banner role benar, dan RAG dijawab untuk semua *(diverifikasi runtime 2026-09-25)*.
- `sari.finance` tanya data → `"Terdapat 1 pengajuan kredit yang statusnya pending."` + audit `query_data_operasional / t` *(diverifikasi runtime 2026-09-25)*.
- `budi.umum` tanya data → mendapat **pesan penolakan** ("Maaf, terdapat penolakan akses..." / "saya tidak memiliki akses..."), **bukan** angka dan **bukan** nama karangan; audit `query_data_operasional / f` atau `NULL / t` tergantung model memanggil tool atau menolak sendiri (keduanya aman) *(diverifikasi runtime 2026-09-25 — kedua jalur diamati; halusinasi bug awal hilang)*.
- `user_id` di `audit_log` = username sesi (`budi.umum`, `sari.finance`), bukan nilai bebas dari body *(diverifikasi runtime 2026-09-25)*.

<details>
<summary><strong>Pakai Claude Code? Salin prompt berikut, paste untuk eksekusi Langkah 0</strong></summary>

```
Bangun login/session sederhana sebagai fondasi identitas untuk RBAC
(Module 27, Tahap 0) — role/user_id harus datang dari sesi
terautentikasi, BUKAN body request.

GOAL:
- Buat Nala/app/auth.py berisi:
  - dict USERS: 3 user demo (budi.umum->staff_umum, sari.finance->
    staff_finance, andi.super->supervisor), masing-masing {password
    "nala123", role, nama}. Plaintext, hardcoded (demo only).
  - dict ROLE_LABELS: staff_umum->"Staff Umum", staff_finance->
    "Staff Finance", supervisor->"Supervisor".
  - verify_user(username, password) -> dict|None: return
    {user_id(=username), role, nama} kalau cocok, else None.
  - get_current_user(request) -> dict|None: baca user_id & role dari
    request.session; kalau salah satu kosong return None; else return
    {user_id, role, nama, role_label}.
- Buat Nala/app/templates/login.html: form POST /login (input username
  + password), tampilkan {{ error }} kalau ada, plus daftar akun demo.
- Di Nala/app/main.py:
  - import RedirectResponse (dari fastapi.responses), SessionMiddleware
    (dari starlette.middleware.sessions), dan get_current_user +
    verify_user dari app.auth.
  - app.add_middleware(SessionMiddleware, secret_key=os.environ.get(
    "SESSION_SECRET","nala-dev-session-secret-change-me"),
    max_age=8*60*60) — pasang setelah app = FastAPI(...).
  - GET /login (render login.html; kalau sudah login redirect ke /),
    POST /login (verify_user; sukses -> set session user_id/role/nama
    + RedirectResponse("/", 303); gagal -> render login.html error,
    status 401), GET /logout (session.clear() + redirect /login).
  - Proteksi GET / , GET+POST /upload, GET /data-operasional dan kedua
    POST /data-operasional/*: di baris pertama panggil
    get_current_user(request); kalau None return
    RedirectResponse("/login", 303). Teruskan {"user": user} ke tiap
    TemplateResponse-nya.
  - /chat dan /chat/stream: tambah parameter http_request: Request,
    dan kalau not get_current_user(http_request): raise HTTPException(
    401). (Field body ChatRequest/ChatStreamRequest TIDAK berubah di
    langkah ini.)
- Di 3 template (chat.html, upload.html, data_operasional.html):
  setelah <nav>, tambah banner {% if user %}Masuk sebagai
  <b>{{ user.nama }}</b> [{{ user.role_label }}] · <a href="/logout">
  Logout</a>{% endif %}.
- Dockerfile: tambah itsdangerous sebagai layer terpisah SETELAH
  "RUN pip install -r requirements.txt" (JANGAN masukkan ke
  requirements.txt — biar layer torch/sentence-transformers yang besar
  tetap kena cache): RUN pip install --no-cache-dir --timeout 120
  --retries 10 itsdangerous==2.2.0.
- docker-compose.yml service api: tambah env
  - SESSION_SECRET=${SESSION_SECRET:-nala-dev-session-secret-change-me}

CONTEXT:
- SessionMiddleware butuh itsdangerous; Starlette tidak memasangnya
  otomatis -> tanpa dep itu, api gagal di request pertama.
- Tahap D nanti membaca role/user_id dari get_current_user() ini
  (bukan body), jadi get_current_user WAJIB sudah ada setelah langkah
  ini, dan /chat sudah punya parameter http_request.

GUARDRAIL:
- JANGAN baca role/user_id dari body request di mana pun — hanya dari
  sesi lewat get_current_user.
- JANGAN ubah logika RAG/agent/retrieval yang sudah ada — langkah ini
  murni menambah lapisan auth + banner.
- JANGAN hardcode SESSION_SECRET tanpa fallback ke env var.
```

</details>

### Tahap A — Tabel `audit_log` dan role database khusus untuk menulis log

**Prasyarat sebelum mulai:** Tahap 0 selesai — login/session sudah jalan dan `get_current_user()` sudah tersedia di `app/main.py`.

**Langkah 1 — Tambah tabel dan role baru di `db/seed.sql`**

```sql
-- db/seed.sql — tambahan di akhir file (setelah GRANT nala_readonly dari Module 23)
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    waktu TIMESTAMPTZ NOT NULL DEFAULT now(),
    user_id VARCHAR(50) NOT NULL,
    role VARCHAR(20) NOT NULL,
    pertanyaan TEXT NOT NULL,
    tool_dipanggil VARCHAR(50),
    akses_diizinkan BOOLEAN NOT NULL,
    ringkasan_data_diakses TEXT
);

CREATE ROLE nala_app WITH LOGIN PASSWORD 'app_dev_only';
GRANT CONNECT ON DATABASE nala_operasional TO nala_app;
GRANT USAGE ON SCHEMA public TO nala_app;
GRANT INSERT, SELECT ON audit_log TO nala_app;
GRANT USAGE, SELECT ON SEQUENCE audit_log_id_seq TO nala_app;
```

Perhatikan: `nala_app` adalah role **ketiga** setelah `nala_admin` (Module 23 Langkah 1, dipakai container init) dan `nala_readonly` (Module 23 Langkah 2, dipakai tool SQL untuk `SELECT` data operasional) — bukan menambah hak akses ke role yang sudah ada. `nala_app` sengaja **hanya** diberi `INSERT` dan `SELECT` ke `audit_log`, **tidak** diberi akses apa pun ke `pengajuan_kredit`/`klaim_asuransi` (itu tugas `nala_readonly`), dan **tidak** diberi `UPDATE`/`DELETE` ke `audit_log` itu sendiri — konsekuensinya, baris audit yang sudah tercatat **tidak bisa diubah atau dihapus** lewat koneksi aplikasi mana pun, cuma bisa ditambah. Ini properti penting untuk audit trail yang kredibel: kalau aplikasi (atau siapa pun yang berhasil mengeksploitasinya) bisa menghapus jejaknya sendiri, audit log itu tidak banyak berguna untuk kepatuhan.

**▶️ Jalankan & lihat hasilnya**

```bash
docker compose down
docker volume rm nala_postgres_data 2>/dev/null || true
docker compose up -d --build postgres
docker compose logs -f postgres
```

⚠️ **Perhatian**: reset volume ini menghapus **semua** data operasional yang sudah dimasukkan lewat form di Module 23 Langkah 6 — database kembali ke seed minimal (2 baris `pengajuan_kredit` + 1 baris `klaim_asuransi`). Ini perlu dilakukan supaya `db/seed.sql` yang baru saja ditambah tabel `audit_log` + role `nala_app` ter-*load* ulang (lihat catatan "Seed data tidak berubah setelah mengedit `db/seed.sql`" di Troubleshooting akhir Tahap D). Setelah Langkah 1-3 selesai, **ulangi Module 23 Langkah 6** (isi ulang lewat `/data-operasional` sampai `7` baris `pengajuan_kredit` dan `4` baris `klaim_asuransi`, termasuk `N-00231` `pending` dan `N-00305` `ditolak`) **sebelum** menjalankan uji di Langkah 4 — kalau tidak, jawaban `/chat` di Langkah 4 tidak akan cocok dengan indikator sukses yang tercantum di sana.

```bash
docker compose exec postgres psql -U nala_app -d nala_operasional -c \
  "INSERT INTO audit_log (user_id, role, pertanyaan, tool_dipanggil, akses_diizinkan) VALUES ('test-user', 'staff_umum', 'tes manual', NULL, true);"
docker compose exec postgres psql -U nala_app -d nala_operasional -c "DELETE FROM audit_log WHERE id = 1;"
```

✅ **Indikator sukses**: `INSERT` berhasil (`INSERT 0 1`), tapi `DELETE` **harus gagal** dengan `permission denied for table audit_log` — bukti audit log tidak bisa dihapus lewat role aplikasi ini, konsisten dengan Bagian 1.

**GUI untuk melihat audit log: Adminer**

Selain `psql` di terminal, tambahkan **Adminer** — GUI database ringan (image generik `adminer:latest`, jauh lebih hemat RAM dari pgAdmin, penting karena laptop sudah menjalankan Ollama + OpenSearch + PostgreSQL + Airflow + Langfuse). Tambahkan service ini di `docker-compose.yml`:

```yaml
  adminer:
    image: adminer:latest
    ports:
      - "8081:8080"   # 8080 host dipakai Airflow; Adminer di http://localhost:8081
    depends_on:
      - postgres
```

Jalankan (image kecil, tidak perlu build ulang `api`):

```bash
docker compose up -d adminer
```

Buka `http://localhost:8081`, login dengan salah satu kredensial (default, kecuali `POSTGRES_ADMIN_PASSWORD` di-override lewat `.env`):

| Field | Akses penuh (`nala_admin`) | Akses terbatas ke `audit_log` saja (`nala_app`) |
|---|---|---|
| System | PostgreSQL | PostgreSQL |
| Server | `postgres` | `postgres` |
| Username | `nala_admin` | `nala_app` |
| Password | `changeme_dev_only` | `app_dev_only` |
| Database | `nala_operasional` | `nala_operasional` |

Login pakai `nala_app` sekaligus jadi demonstrasi langsung batasan role (Bagian 3 Tahap A): coba buka tabel `pengajuan_kredit`/`klaim_asuransi` lewat akun ini — **tidak muncul/tidak bisa diakses**, karena role itu memang tidak pernah diberi `GRANT` ke tabel tersebut, hanya ke `audit_log`. Untuk melihat isi audit log, buka tabel `audit_log` → tab **Select** (baris audit akan muncul setelah Tahap D menyambungkannya ke `/chat`).

✅ **Indikator sukses**:
- Adminer reachable di `http://localhost:8081` *(diverifikasi runtime 2026-09-25 — container `adminer:latest` up, HTTP 200)*.
- Login `nala_app` bisa melihat tabel `audit_log` tapi **tidak** melihat `pengajuan_kredit`/`klaim_asuransi` *(diverifikasi runtime 2026-09-25 di level DB: `nala_app` INSERT ke `audit_log` OK, DELETE ditolak `permission denied`, dan SELECT `pengajuan_kredit` ditolak `permission denied` — persis yang di-surface Adminer)*.

<details>
<summary><strong>Pakai Claude Code? Salin prompt berikut, paste untuk eksekusi Langkah 1</strong></summary>

```
Tambah tabel audit_log dan role database khusus untuk menulis log,
plus service Adminer untuk GUI database (Module 27, Tahap A) — role
INSERT+SELECT saja, tanpa UPDATE/DELETE.

GOAL:
- Di akhir Nala/db/seed.sql (setelah
  GRANT nala_readonly yang sudah ada dari Module 23), tambahkan: CREATE
  TABLE audit_log (id SERIAL PK, waktu TIMESTAMPTZ NOT NULL DEFAULT
  now(), user_id VARCHAR(50) NOT NULL, role VARCHAR(20) NOT NULL,
  pertanyaan TEXT NOT NULL, tool_dipanggil VARCHAR(50) nullable,
  akses_diizinkan BOOLEAN NOT NULL, ringkasan_data_diakses TEXT
  nullable); CREATE ROLE nala_app WITH LOGIN PASSWORD 'app_dev_only';
  GRANT CONNECT ON DATABASE nala_operasional TO nala_app; GRANT USAGE
  ON SCHEMA public TO nala_app; GRANT INSERT, SELECT ON audit_log TO
  nala_app; GRANT USAGE, SELECT ON SEQUENCE audit_log_id_seq TO
  nala_app;
- Di Nala/docker-compose.yml, tambahkan service adminer:
  image adminer:latest, ports "8081:8080", depends_on: [postgres].
  (8080 host sudah dipakai Airflow, jadi map ke 8081.)

CONTEXT:
- nala_app adalah role KETIGA, terpisah dari nala_admin (init) dan
  nala_readonly (Module 23, akses SELECT ke pengajuan_kredit/
  klaim_asuransi). nala_app TIDAK diberi akses apa pun ke dua tabel
  itu, hanya ke audit_log.
- Sengaja TIDAK ada GRANT UPDATE/DELETE ke nala_app — audit_log harus
  append-only dari sisi aplikasi.

GUARDRAIL:
- JANGAN beri nala_app akses SELECT/INSERT/apa pun ke pengajuan_kredit
  atau klaim_asuransi.
- JANGAN beri GRANT UPDATE atau DELETE ke audit_log untuk role mana
  pun yang baru ditambahkan di langkah ini.
```

</details>

### Tahap B — Fungsi pencatatan audit

**Langkah 2 — Tambah `POSTGRES_APP_DSN` dan fungsi `log_audit()` di `app/audit.py`**

```python
# app/audit.py
import logging
import os
from datetime import datetime, timezone

import psycopg

POSTGRES_APP_DSN = os.environ.get(
    "POSTGRES_APP_DSN",
    "postgresql://nala_app:app_dev_only@localhost:5432/nala_operasional",
)

logger = logging.getLogger("nala.audit")


def log_audit(
    user_id: str,
    role: str,
    pertanyaan: str,
    tool_dipanggil: str | None,
    akses_diizinkan: bool,
    ringkasan_data_diakses: str | None = None,
) -> None:
    try:
        with psycopg.connect(POSTGRES_APP_DSN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO audit_log
                        (user_id, role, pertanyaan, tool_dipanggil, akses_diizinkan, ringkasan_data_diakses)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (user_id, role, pertanyaan, tool_dipanggil, akses_diizinkan, ringkasan_data_diakses),
                )
    except psycopg.OperationalError:
        # Audit log gagal tercatat TIDAK BOLEH menggagalkan jawaban ke user —
        # tapi kegagalannya sendiri wajib terlihat di log aplikasi supaya tim
        # ops tahu ada celah di jejak audit yang perlu ditindaklanjuti.
        logger.error(
            "Gagal mencatat audit log (user_id=%s, tool=%s, waktu=%s) — PostgreSQL tidak terjangkau",
            user_id,
            tool_dipanggil,
            datetime.now(timezone.utc).isoformat(),
        )
```

Dua keputusan desain yang perlu dijelaskan:

- **`POSTGRES_APP_DSN` memakai `nala_app`, bukan `nala_admin` atau `nala_readonly`.** Sama seperti Module 25 Tahap A (tool SQL memakai `nala_readonly`, bukan admin), setiap komponen memakai role paling terbatas yang cukup untuk tugasnya — menulis log tidak butuh (dan tidak boleh punya) akses ke tabel data nasabah.
- **Kegagalan menulis audit log sengaja tidak melempar exception ke pemanggil.** Kalau `log_audit()` gagal (mis. PostgreSQL sedang down) dan itu membuat `/chat` ikut gagal (`500`), NALA jadi tidak bisa menjawab pertanyaan sederhana hanya karena masalah di sistem pencatatan — trade-off yang diambil di sini adalah **ketersediaan layanan chat lebih diprioritaskan** daripada audit yang sempurna 100%, dengan syarat kegagalan itu sendiri tercatat di log aplikasi (`logger.error`) supaya bisa dipantau dan ditindaklanjuti terpisah, bukan diam-diam hilang. Ini trade-off yang bisa diperdebatkan (institusi finansial yang sangat ketat mungkin memilih sebaliknya — menolak melayani permintaan kalau audit tidak bisa dijamin tercatat), disebutkan di sini secara eksplisit supaya kita tahu ini keputusan sadar, bukan kealpaan.

Ingat menambahkan/override `POSTGRES_APP_DSN` di `docker-compose.yml` (service `api`) memakai host `postgres` (bukan `localhost`), sama seperti catatan Langkah 3 di Module 23.

**▶️ Jalankan & lihat hasilnya**

```bash
docker compose up --build api
docker compose exec api python -c "
from app.audit import log_audit
log_audit(user_id='test-user', role='staff_umum', pertanyaan='tes fungsi', tool_dipanggil=None, akses_diizinkan=True)
print('selesai, cek tabel audit_log')
"
docker compose exec postgres psql -U nala_admin -d nala_operasional -c "SELECT * FROM audit_log;"
```

✅ **Indikator sukses**: baris baru muncul di `audit_log` dengan `user_id='test-user'`, `waktu` terisi otomatis (`DEFAULT now()`).

<details>
<summary><strong>Pakai Claude Code? Salin prompt berikut, paste untuk eksekusi Langkah 2</strong></summary>

```
Buat fungsi pencatatan audit log yang memakai role database read-write
terbatas (Module 27, Tahap B) — belum disambungkan ke endpoint
mana pun.

GOAL:
- Buat Nala/app/audit.py berisi:
  - konstanta POSTGRES_APP_DSN dari env var POSTGRES_APP_DSN (default
    postgresql://nala_app:app_dev_only@localhost:5432/nala_operasional)
  - logger = logging.getLogger("nala.audit")
  - fungsi log_audit(user_id: str, role: str, pertanyaan: str,
    tool_dipanggil: str | None, akses_diizinkan: bool,
    ringkasan_data_diakses: str | None = None) -> None yang membuka
    koneksi psycopg.connect(POSTGRES_APP_DSN, connect_timeout=5) di
    dalam try, INSERT satu baris ke audit_log dengan keenam parameter
    itu (pakai placeholder %s, parameter terpisah — bukan f-string),
    dan except psycopg.OperationalError: log error via logger.error
    (jangan raise ulang, jangan biarkan exception ini menggagalkan
    pemanggil).

CONTEXT:
- Tabel audit_log dan role nala_app sudah dibuat di Tahap A.
- Fungsi ini akan dipanggil dari app/main.py di Tahap D — belum di
  langkah ini.

GUARDRAIL:
- JANGAN biarkan kegagalan koneksi database membuat fungsi ini
  melempar exception ke pemanggil — harus ditangani via try/except,
  cukup dicatat lewat logger.
- JANGAN pakai f-string/format string untuk menyisipkan nilai ke SQL —
  wajib placeholder %s.
```

</details>

### Tahap C — RBAC di dalam agent (pertahanan berlapis)

**Langkah 3 — Tambah `role` ke `AgentState`, tawarkan semua tool ke model, tegakkan RBAC saat eksekusi di `call_tool`**

> **Desain penting (baca Bagian 4 dulu kalau ingin alasan lengkapnya):** RBAC di NALA ditegakkan **saat eksekusi tool** (`call_tool`), **bukan** dengan menyembunyikan skema tool dari role tertentu di `call_model`. Semua role ditawari kedua tool; kalau role tak berwenang mencoba `query_data_operasional`, `call_tool` mengembalikan penolakan rapi dan mencatatnya ke audit. Pendekatan ini dipilih setelah pengujian menunjukkan bahwa menyembunyikan tool (desain awal) justru membuat model **mengarang** jawaban dan percobaannya **tak tercatat** (lihat Bagian 4).

```python
# app/agent.py — perubahan pada AgentState dan build_agent()
class AgentState(TypedDict):
    messages: Annotated[list[dict], operator.add]
    role: str
    called_tools: Annotated[list[dict], operator.add]


SQL_ALLOWED_ROLES = {"staff_finance", "supervisor"}

# Tawarkan SEMUA tool ke SEMUA role; RBAC ditegakkan saat eksekusi di call_tool.
ALL_TOOLS = [RAG_TOOL_SCHEMA, SQL_TOOL_SCHEMA]


def build_agent(ollama_client, vector_store, ollama_base_url: str, reranker=None, trace=None, model_name: str = "llama3.2:3b"):
    def call_model(state: AgentState) -> dict:
        # Semua role ditawari semua tool; keputusan izin ada di call_tool.
        response_message = ollama_client.chat(state["messages"], tools=ALL_TOOLS)
        return {"messages": [response_message]}

    def call_tool(state: AgentState) -> dict:
        last_message = state["messages"][-1]
        tool_messages = []
        called = []
        for call in last_message.get("tool_calls", []):
            name = call["function"]["name"]
            args = call["function"]["arguments"]

            try:
                if name == "query_data_operasional" and state["role"] not in SQL_ALLOWED_ROLES:
                    result = (
                        "Akses ditolak: role Anda tidak berwenang mengakses data "
                        "operasional. Hubungi supervisor kalau ini seharusnya diizinkan."
                    )
                    called.append({"tool": name, "diizinkan": False})
                elif name == "cari_dokumen_sop":
                    result = rag_search(args["query"], vector_store, ollama_base_url, reranker=reranker)
                    called.append({"tool": name, "diizinkan": True})
                elif name == "query_data_operasional":
                    result = query_data_operasional(**args)
                    called.append({"tool": name, "diizinkan": True})
                else:
                    result = f"Tool '{name}' tidak dikenal."
                    called.append({"tool": name, "diizinkan": False})
            except (TypeError, KeyError) as e:
                result = f"Tool '{name}' dipanggil dengan argumen tidak lengkap/tidak valid ({e}). Coba tanyakan ulang dengan lebih spesifik."
                called.append({"tool": name, "diizinkan": True})

            tool_messages.append({"role": "tool", "content": result, "tool_call_id": call.get("id"), "name": name})

        return {"messages": tool_messages, "called_tools": called}

    # should_continue, force_answer, dan struktur graph TIDAK berubah dari Module 26
    ...
```

Yang **dipertahankan apa adanya** dari module sebelumnya (jangan dihapus saat menyalin blok di atas): signature `build_agent()` tetap membawa `reranker`, `trace`, dan `model_name` (sejak Module 24 Bagian 7a-7b, dipertahankan Module 25) — `reranker=reranker` di pemanggilan `rag_search()` bergantung pada itu, kalau parameternya hilang reranking Module 20 ikut mati diam-diam; blok `try/except (TypeError, KeyError)` dan `"tool_call_id": call.get("id")` di pesan `role: "tool"` juga tetap seperti versi final Module 25 (lihat Module 25 Tahap B). Logika RBAC baru module ini sengaja diletakkan **di dalam** `try` yang sama supaya semua cabang tool tertangani seragam. Catatan soal `called.append()` di cabang `except`: kolom `akses_diizinkan` di `audit_log` merekam **keputusan RBAC** (role ini berwenang atau tidak), bukan keberhasilan eksekusi tool — jadi argumen tool yang tidak lengkap tetap dicatat `diizinkan: True`, karena role-nya memang berwenang; yang gagal adalah pemanggilannya, bukan otorisasinya.

Bagian paling penting di sini: **pengecekan role dilakukan di `call_tool` saat eksekusi.** Semua role ditawari `query_data_operasional` di `call_model`, tapi kalau `state["role"]` tidak ada di `SQL_ALLOWED_ROLES`, `call_tool` **menolak** eksekusinya — mengembalikan pesan "Akses ditolak: ..." sebelum satu baris pun query dijalankan ke database, dan mencatat `{"tool": name, "diizinkan": False}`. Ini analog dengan Module 25 Bagian 3 (validasi `tabel` diperiksa ulang di kode Python, tidak cuma dipercaya dari skema tool): keputusan keamanan ada di kode yang mengeksekusi, bukan di apa yang "ditawarkan" ke model. Field baru `called_tools` mencatat **setiap** tool yang model coba panggil, termasuk yang ditolak RBAC — ini penting untuk Tahap D: percobaan akses yang ditolak **tetap** masuk audit trail (percobaan akses tidak sah justru salah satu hal paling penting untuk terlihat di audit compliance).

Ada satu penyesuaian pendukung di **`app/system_prompt.py`**: `NALA_SYSTEM_PROMPT_AGENT` diperkuat dengan aturan anti-halusinasi khusus data nasabah — model dilarang mengarang nama/ID/status/jumlah nasabah, dilarang mengaku punya "data operasional" kalau tidak ada hasil tool, dan wajib meneruskan pesan "Akses ditolak" apa adanya. Ini melengkapi barrier di `call_tool`: barrier mencegah eksekusi, prompt mencegah model menutupi penolakan dengan karangan.

**▶️ Jalankan & lihat hasilnya**

Belum ada endpoint yang mengirim `role` (itu Tahap D) — cukup pastikan tidak ada error saat startup:

```bash
docker compose up --build api
```

✅ **Indikator sukses**: log `api` menunjukkan `Uvicorn running` tanpa traceback.

<details>
<summary><strong>Pakai Claude Code? Salin prompt berikut, paste untuk eksekusi Langkah 3</strong></summary>

```
Tambah RBAC ke agent — semua role ditawari semua tool, tapi eksekusi
query_data_operasional untuk role tak berwenang DIBLOKIR di call_tool
(RBAC ditegakkan saat eksekusi) (Module 27, Tahap C).

GOAL:
- Di Nala/app/agent.py:
  1. Tambah field baru ke AgentState: role: str, dan called_tools:
     Annotated[list[dict], operator.add].
  2. Tambah konstanta modul SQL_ALLOWED_ROLES = {"staff_finance",
     "supervisor"} dan ALL_TOOLS = [RAG_TOOL_SCHEMA, SQL_TOOL_SCHEMA].
     JANGAN membuat fungsi filter tool per-role — semua role ditawari
     semua tool.
  3. Di call_model: kirim ALL_TOOLS sebagai parameter tools ke
     ollama_client.chat() untuk semua role.
  4. Di call_tool: untuk tiap tool_call, KALAU name ==
     "query_data_operasional" DAN state["role"] tidak ada di
     SQL_ALLOWED_ROLES, JANGAN eksekusi query_data_operasional sama
     sekali — set result ke pesan penolakan akses, dan catat
     {"tool": name, "diizinkan": False} ke list called. Kalau role
     berwenang atau tool-nya cari_dokumen_sop, eksekusi seperti biasa
     dan catat {"tool": name, "diizinkan": True}. Tool tidak dikenal
     tetap dicatat {"tool": name, "diizinkan": False}. Seluruh rantai
     if/elif/else ini diletakkan DI DALAM blok try/except (TypeError,
     KeyError) yang sudah ada dari Module 25 — jangan dibuat di
     luarnya. PERTAHANKAN key "name" dan "tool_call_id":
     call.get("id") yang sudah ada di tiap dict pesan tool. Return
     {"messages": tool_messages, "called_tools": called}.

CONTEXT:
- should_continue, force_answer (Module 26), dan struktur graph
  (add_node/add_conditional_edges/add_edge) TIDAK berubah di langkah
  ini.
- Versi call_tool yang ada sekarang sudah membawa dari Module 25:
  signature build_agent(ollama_client, vector_store, ollama_base_url,
  reranker=None, trace=None, model_name="llama3.2:3b"), pemanggilan
  rag_search(..., reranker=reranker), blok try/except (TypeError,
  KeyError), dan "tool_call_id" di pesan role tool — langkah ini hanya
  MENAMBAH lapisan RBAC di atasnya.
- called_tools akan dipakai app/main.py di Tahap D untuk audit log —
  belum disambungkan di langkah ini.

GUARDRAIL:
- Pengecekan role WAJIB ada di call_tool — di sinilah RBAC ditegakkan.
  JANGAN kembali menyembunyikan SQL_TOOL_SCHEMA dari role tertentu di
  call_model (itu desain lama yang memicu halusinasi + gap audit,
  Bagian 4).
- JANGAN eksekusi query_data_operasional untuk role yang tidak ada di
  SQL_ALLOWED_ROLES dengan alasan apa pun.
- JANGAN hapus history/HISTORY_WINDOW (Module 25 Langkah 4), parameter
  reranker/trace/model_name di build_agent(), blok try/except
  (TypeError, KeyError), maupun tool_call_id di pesan role tool
  (Module 25).

Selain itu, perkuat Nala/app/system_prompt.py (NALA_SYSTEM_PROMPT_AGENT):
tambahkan aturan bahwa model DILARANG mengarang nama/ID/status/jumlah
nasabah, DILARANG mengaku punya "data operasional" kalau tidak ada
hasil tool, dan WAJIB meneruskan pesan "Akses ditolak: ..." apa adanya
tanpa mengarang data pengganti.
```

</details>

### Tahap D — Sambungkan RBAC & audit logging ke `/chat`

**Langkah 4 — Baca `role`/`user_id` dari sesi, kirim `role` ke agent, panggil `log_audit()` setelah agent selesai**

```python
# app/main.py — perubahan
from app.audit import log_audit


# ChatRequest TIDAK bertambah field role/user_id — identitas datang dari sesi
# (Tahap 0), bukan body. Field message & history dari Module 25 dipertahankan.
class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []  # sudah ada dari Module 25 Langkah 4 — jangan dihapus


@app.post("/chat", response_model=ChatResponse)
def chat(http_request: Request, request: ChatRequest) -> ChatResponse:
    user = get_current_user(http_request)  # 401-guard ini sudah dipasang di Tahap 0
    if not user:
        raise HTTPException(status_code=401, detail="Belum login")

    history_messages = [{"role": m.role, "content": m.content} for m in request.history]
    recent_history = (history_messages + [{"role": "user", "content": request.message}])[-HISTORY_WINDOW:]

    initial_state = {
        "messages": [
            {"role": "system", "content": NALA_SYSTEM_PROMPT_AGENT},
            *recent_history,
        ],
        "role": user["role"],          # dari sesi, bukan body
        "called_tools": [],
    }
    final_state = nala_agent.invoke(initial_state)
    reply = final_state["messages"][-1]["content"]

    called_tools = final_state.get("called_tools", [])
    if called_tools:
        for entry in called_tools:
            log_audit(
                user_id=user["user_id"],
                role=user["role"],
                pertanyaan=request.message,
                tool_dipanggil=entry["tool"],
                akses_diizinkan=entry["diizinkan"],
            )
    else:
        log_audit(
            user_id=user["user_id"],
            role=user["role"],
            pertanyaan=request.message,
            tool_dipanggil=None,
            akses_diizinkan=True,
        )

    return ChatResponse(reply=reply)
```

- **Catatan implementasi nyata:** contoh di atas memakai `nala_agent.invoke(...)` (agent modul-level, gaya Module 24-26). Di kode NALA yang sebenarnya, `/chat` **membangun agent per-request** (`agent = build_agent(..., trace=trace, model_name=...)`) supaya tiap request punya trace Langfuse sendiri (Module 22/24) — jadi baca `nala_agent.invoke` di sini sebagai `agent.invoke` pada agent yang baru dibangun. Yang penting sama: `initial_state` menyertakan `"role"` (dari sesi) dan `"called_tools": []`, lalu `final_state.get("called_tools")` dipakai untuk audit.
- **Field `history` dan windowing `HISTORY_WINDOW` dipertahankan apa adanya dari Module 25 Langkah 4** (`ChatMessage` juga sudah didefinisikan di sana, di atas `ChatRequest`) — kalau keduanya ikut terhapus, dukungan multi-turn di `/chat` mati diam-diam. Module ini hanya **membaca sesi** dan menambah audit, tidak mengganti field lama.
- **`ChatRequest` TIDAK bertambah field `role`/`user_id`** — inilah perbedaan inti dari rencana kurikulum awal. Identitas dibaca dari `get_current_user(http_request)` (sesi Tahap 0), bukan body JSON. Konsekuensinya **fail-safe** jadi lebih tegas daripada sekadar default `staff_umum`: tanpa sesi valid, `/chat` langsung **ditolak `401`** (deny-by-default), bukan diam-diam diperlakukan sebagai role terendah lalu diproses. Tidak ada lagi celah "client mengaku `role: supervisor`" karena `role` tidak pernah dibaca dari input client.
- **Satu baris audit per tool yang dicoba** (termasuk yang ditolak), bukan satu baris per pertanyaan — kalau user memicu dua tool dalam satu pertanyaan (skenario multi-hop, Module 25 Bagian 4), keduanya tercatat terpisah, masing-masing dengan status izin sendiri.
- **Pertanyaan tanpa tool sama sekali** (mis. sapaan) tetap dicatat satu baris dengan `tool_dipanggil=None` — audit trail NALA mencakup **semua** interaksi, bukan cuma yang menyentuh data sensitif, supaya pola pemakaian keseluruhan juga bisa dianalisis kalau diperlukan.

**▶️ Jalankan & lihat hasilnya**

```bash
docker compose up --build api
```

⚠️ Pastikan data operasional sudah diisi ulang sesuai catatan di Langkah 1 (`7` baris `pengajuan_kredit`, `4` baris `klaim_asuransi`, via `/data-operasional` — lihat Module 23 Langkah 6) sebelum menjalankan uji di bawah — kalau belum, jumlah "pending" di jawaban tidak akan cocok dengan indikator sukses.

Karena `role` kini datang dari **sesi** (Tahap 0), bukan body, cara paling natural menguji adalah **login di browser** sebagai user yang berbeda lalu bertanya di halaman chat. Untuk uji dari terminal, login dulu untuk menyimpan cookie sesi, lalu pakai cookie itu (`-c` menyimpan, `-b` mengirim):

Uji **role tidak berwenang** — login sebagai `budi.umum` (staff_umum):

```bash
curl -c /tmp/nala_cookies.txt -X POST http://localhost:8000/login \
  -d 'username=budi.umum&password=nala123'
curl -b /tmp/nala_cookies.txt -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Berapa banyak pengajuan kredit yang statusnya pending?"}'
```

Ekspektasi (desain final Tahap C, RBAC di eksekusi): jawaban berupa **pesan penolakan** ("Akses ditolak: role Anda tidak berwenang...") — **bukan** angka data dan **bukan** nama nasabah karangan. Cek jejaknya:

```bash
docker compose exec postgres psql -U nala_admin -d nala_operasional -c \
  "SELECT user_id, role, tool_dipanggil, akses_diizinkan FROM audit_log ORDER BY id DESC LIMIT 1;"
```

baris terakhir menunjukkan `user_id='budi.umum'`, `role='staff_umum'`, dan **salah satu**: `tool_dipanggil='query_data_operasional', akses_diizinkan=f` (model memanggil tool → diblokir) atau `tool_dipanggil=NULL, akses_diizinkan=t` (model menolak sendiri). Yang **wajib** benar di kedua kasus: jawaban ke pengguna berupa penolakan, **bukan** angka data dan **bukan** nama nasabah karangan. Data tidak bocor (barrier di `call_tool`). *(Perbaikan Bagian 4.c — kalau justru muncul nama karangan seolah dari data operasional, itu regresi ke desain lama; lihat Bagian 4.a.)*

Uji **role berwenang** — login sebagai `sari.finance` (staff_finance):

```bash
curl -c /tmp/nala_cookies.txt -X POST http://localhost:8000/login \
  -d 'username=sari.finance&password=nala123'
curl -b /tmp/nala_cookies.txt -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Berapa banyak pengajuan kredit yang statusnya pending?"}'
```

✅ **Indikator sukses** *(diverifikasi runtime 2026-09-25)*: login `sari.finance` lalu tanya "Berapa banyak pengajuan kredit yang statusnya pending?" → jawaban `"Terdapat 1 pengajuan kredit yang statusnya pending."` (benar, seed punya 1 pending), dan baris audit menunjukkan `user_id='sari.finance'`, `role='staff_finance'`, `tool_dipanggil='query_data_operasional'`, `akses_diizinkan=t`.

Terakhir, tarik seluruh audit trail untuk melihat gambaran lengkap:

```bash
docker compose exec postgres psql -U nala_admin -d nala_operasional -c \
  "SELECT waktu, user_id, role, tool_dipanggil, akses_diizinkan FROM audit_log ORDER BY waktu DESC LIMIT 10;"
```

✅ **Indikator sukses**: setiap percobaan dari Langkah ini (dan pengujian Module 24-25 sebelumnya kalau sudah dilakukan setelah Tahap A-D selesai) muncul sebagai baris terpisah, urut berdasarkan waktu — `user_id` kini berisi username asli dari sesi (`budi.umum`, `sari.finance`), bukan nilai bebas yang diketik di body.

<details>
<summary><strong>Pakai Claude Code? Salin prompt berikut, paste untuk eksekusi Langkah 4</strong></summary>

```
Baca role/user_id dari sesi (Tahap 0), kirim role ke agent, dan
panggil audit logging setelah agent selesai memproses
(Module 27, Tahap D).

GOAL:
- Di Nala/app/main.py:
  1. Tambah import log_audit dari app.audit.
  2. JANGAN tambah field role/user_id ke ChatRequest — biarkan hanya
     message + history: list[ChatMessage] = [] (dari Module 25). Role
     & user_id datang dari sesi, bukan body.
  3. Fungsi chat() sudah punya parameter http_request: Request dan
     401-guard (dari Tahap 0). Di dalamnya panggil
     user = get_current_user(http_request) (guard 401 kalau None,
     sudah ada dari Tahap 0). initial_state sekarang juga menyertakan
     "role": user["role"] dan "called_tools": [] (selain "messages"
     yang sudah ada). Pembangunan "messages" TIDAK berubah dari
     Module 25: system prompt + *recent_history, dengan
     recent_history = (history_messages + [pesan user baru])
     [-HISTORY_WINDOW:]. Setelah final_state = nala_agent.invoke(...) dan
     reply diambil, baca called_tools = final_state.get("called_tools",
     []); kalau tidak kosong, panggil log_audit() sekali untuk TIAP
     entry di called_tools (user_id=user["user_id"], role=user["role"],
     pertanyaan=request.message, tool_dipanggil=entry["tool"],
     akses_diizinkan=entry["diizinkan"]); kalau kosong, panggil
     log_audit() sekali dengan tool_dipanggil=None,
     akses_diizinkan=True. Baru setelah itu return ChatResponse(reply=
     reply).

CONTEXT:
- Tahap 0 sudah menambahkan get_current_user(), SessionMiddleware, dan
  parameter http_request + 401-guard di /chat — langkah ini memakainya,
  tidak membangunnya ulang.
- app/agent.py sudah menghasilkan called_tools di final_state dari
  Tahap C.
- app/audit.py sudah punya log_audit() dari Tahap B.
- Kontrak response ChatResponse{reply} TIDAK berubah, dan ChatRequest
  TIDAK bertambah field.
- ChatRequest & chat() sudah punya dukungan riwayat multi-turn dari
  Module 25 Langkah 4 (ChatMessage, history, HISTORY_WINDOW) — semua
  DIPERTAHANKAN.

GUARDRAIL:
- JANGAN baca role/user_id dari body request — HANYA dari sesi lewat
  get_current_user. Ini inti keamanan module ini.
- JANGAN ubah endpoint /chat/stream (selain 401-guard Tahap 0),
  /health, /, /upload.
- JANGAN hapus history/HISTORY_WINDOW (Module 25 Langkah 4), parameter
  reranker/trace/model_name di build_agent(), blok try/except
  (TypeError, KeyError), maupun tool_call_id di pesan role tool
  (Module 25).
- Kegagalan log_audit() (ditangani internal di app/audit.py) TIDAK
  BOLEH membuat endpoint /chat mengembalikan error — pastikan urutan
  kode: reply sudah didapat SEBELUM log_audit() dipanggil, dan
  log_audit() sendiri sudah menangani exception-nya sendiri (dari
  Tahap B).
```

</details>

**Troubleshooting Langkah 1-4**

- **`message.tool_calls` selalu kosong padahal pertanyaannya jelas butuh tool**: cek versi Ollama (`docker compose exec ollama ollama --version`) — dukungan tool-calling butuh versi yang cukup baru. Cek juga `RAG_TOOL_SCHEMA`/`SQL_TOOL_SCHEMA` terkirim dengan benar sebagai parameter `tools` di `OllamaClient.chat()` (Module 24 Bagian 3, ⚠️ catatan kejujuran teknis).
- **`psycopg.OperationalError: connection to server ... failed`**: kemungkinan besar DSN masih memakai `localhost` padahal dipanggil dari dalam container `api` — harus memakai nama service Docker Compose (`postgres`), lihat catatan di Module 23 Langkah 3 dan Langkah 2 di atas. Cek juga `postgres` sudah `healthy` (`docker compose ps`).
- **`permission denied for table ...` padahal seharusnya diizinkan**: cek role/DSN yang dipakai — tool SQL (Module 25) harus memakai `nala_readonly`, form `/data-operasional` (Module 23) harus memakai `nala_writer`, audit logging (Module 27) harus memakai `nala_app`; tertukar salah satunya akan memicu `permission denied` untuk operasi yang seharusnya sah (mis. `nala_readonly` dipakai untuk `INSERT` ke `audit_log` akan gagal, karena `nala_readonly` tidak pernah diberi `GRANT` ke tabel itu).
- **Seed data tidak berubah setelah mengedit `db/seed.sql`**: script init PostgreSQL cuma jalan sekali saat volume database masih kosong — kalau volume `postgres_data` sudah ada dari percobaan sebelumnya, `docker compose up` **tidak** menjalankan ulang seed. Hapus volume dulu (`docker compose down && docker volume rm nala_postgres_data`) lalu `docker compose up -d --build postgres` lagi. Ini juga penyebab paling umum kalau tabel/role baru "tidak muncul" setelah mengikuti Langkah 1 — ingat, reset volume juga menghapus data hasil form (lihat catatan di Langkah 1).
- **Agent tampak "menggantung" lama (timeout) untuk pertanyaan yang butuh dua tool**: wajar sampai batas tertentu — setiap putaran tool berarti minimal satu panggilan tambahan ke `llama3.2:3b` (Module 26 Bagian 1), jadi pertanyaan yang butuh dua tool berurutan otomatis lebih lambat dari pertanyaan satu-tool. Kalau benar-benar tidak pernah selesai (bukan cuma lambat), pastikan `MAX_TOOL_ROUNDS`/`force_answer` (Module 26 Bagian 5) sudah terpasang dengan benar.
- **Request `/chat` pertama lambat / dulu `500` di ~60 detik** (khas `qwen2.5:7b` di CPU): ini **cold-start** — model 4.7GB baru dimuat ke memory + sintesis di CPU bisa >60 detik. *Diamati langsung 2026-09-25.* **Sudah diperbaiki di Module 28:** `OllamaClient` kini memakai `OLLAMA_TIMEOUT` (default **180 detik**, env di `docker-compose.yml`), jadi request pertama sabar menunggu, bukan gagal. Kalau masih ingin lebih cepat saat demo, **pra-panaskan** model: `curl http://localhost:11434/api/generate -d '{"model":"qwen2.5:7b","prompt":"halo","stream":false,"keep_alive":"30m"}'` (`keep_alive` menjaga model resident); request berikutnya normal (~12 dtk untuk SQL, lebih lama untuk RAG karena embedding+rerank). Cek model resident: `docker compose exec ollama ollama ps`.
- **`docker compose exec postgres psql -U nala_admin ...` minta password / gagal autentikasi**: pastikan env var `POSTGRES_ADMIN_PASSWORD` (kalau di-override di `.env` atau shell) konsisten dengan yang dipakai saat container `postgres` dibuat — kalau volume sudah lama ada dengan password lama, password baru di env var tidak otomatis berlaku sampai volume direset (sama seperti poin seed data di atas).
- **Routing tool terasa buruk terus-menerus meski sudah memperbaiki `description` (Module 26 Bagian 4.b)**: pertimbangkan opsi `qwen2.5:7b` (Module 26 Bagian 4.c) **hanya** kalau laptop punya RAM 32GB+ — jangan dipaksakan di laptop 16GB yang sudah menjalankan Ollama + OpenSearch + Airflow + PostgreSQL bersamaan, risiko container ter-*kill* karena kehabisan memory jauh lebih mengganggu daripada akurasi routing yang belum sempurna.
- **Error umum lain** (`no configuration file provided`, `failed to read dockerfile`, port sudah dipakai, dsb.): lihat Troubleshooting di bagian praktik materi.md module-module sebelumnya (Module 7-17) — penyebab dan solusinya sama, tidak spesifik rangkaian Module 23-27.

**📄 Kode lengkap Module 27** (`app/audit.py`, potongan relevan `app/agent.py` dan `app/main.py`, `db/seed.sql` tambahan — sudah ditampilkan utuh di Langkah 1-4 di atas).

## 4. Perjalanan Desain RBAC: Kenapa Ditegakkan di Eksekusi, Bukan di Filter Tool

Desain RBAC di module ini **bukan** hasil sekali jadi — bentuk finalnya (Tahap C: tawarkan semua tool + blokir di `call_tool`) dipilih **setelah** pengujian membongkar masalah pada desain pertama. Bagian ini mendokumentasikan perjalanannya secara jujur, karena keputusan desainnya sendiri adalah pelajaran pentingnya.

### a. Desain awal (menyembunyikan tool per-role) → model mengarang, bukan menolak dengan rapi

Desain pertama memfilter tool di `call_model`: `staff_umum` **tidak diberi** `SQL_TOOL_SCHEMA` sama sekali (fungsi `_tools_for_role()`). Idenya "kalau tool-nya tidak ada, model tidak bisa memakainya". Pengujian nyata (2026-09-25, diuji lewat body request maupun via login `budi.umum`) menunjukkan dua kegagalan:

1. **Jawaban JSON mentah** — model tetap "ingin" memanggil tool (pertanyaan jelas butuh data), tapi karena skemanya tidak tersedia, Ollama tidak bisa membungkusnya jadi `tool_calls` terstruktur. Model menuliskan niatnya sebagai teks, mis. `{"name": "query_data_operasional", ...}` — membingungkan pengguna.
2. **Model mengarang lalu berbohong soal sumber** — pada percobaan lain, `budi.umum` bertanya "siapa nasabah dengan id N-00305" dan model menjawab *"Nasabah dengan ID N-00305 adalah Prartha Wijaya. Informasi ini didapatkan dari data operasional..."* — padahal data asli N-00305 adalah **Andi Wijaya** (model **mengarang**), dan **tidak ada query yang pernah dijalankan** (audit: `tool_dipanggil=NULL`). Barrier data tetap aman (tidak ada kebocoran), tapi model **menutupi** ketiadaan akses dengan karangan yang seolah-olah dari data operasional — jauh lebih berbahaya daripada JSON mentah, karena pengguna bisa percaya.

Akar keduanya sama: karena `SQL_TOOL_SCHEMA` disembunyikan, tidak pernah ada `tool_calls` asli, jadi `call_tool` (tempat penolakan rapi seharusnya dibuat) **tidak pernah kebagian giliran**.

### b. Konsekuensi ke audit trail: percobaan akses yang ditolak tidak tercatat

Karena `call_tool` tak pernah jalan di skenario di atas, `called_tools` tetap `[]`, dan `app/main.py` mencatat audit seolah tidak ada tool yang dicoba:

```
role='staff_umum', tool_dipanggil=NULL, akses_diizinkan=t
```

Dari sudut kepatuhan, "staff tak berwenang mencoba mengakses data nasabah" justru **paling** perlu terlihat di jejak audit — lebih penting daripada akses yang berhasil. Desain filter-di-`call_model` efektif mencegah kebocoran, tapi efek sampingnya menyembunyikan percobaan itu dari audit.

### c. Perbaikan yang diterapkan: RBAC di eksekusi + prompt anti-halusinasi

Solusinya (kini **sudah diterapkan** di Tahap C, bukan lagi "pengembangan lanjutan"): **tawarkan `SQL_TOOL_SCHEMA` ke semua role** di `call_model` (`ALL_TOOLS`), tapi **blokir eksekusinya di `call_tool`** untuk role tak berwenang — mengembalikan pesan "Akses ditolak: ..." dan mencatat `{"diizinkan": False}`. Ditambah aturan anti-halusinasi di `NALA_SYSTEM_PROMPT_AGENT` (dilarang mengarang data nasabah / mengaku punya data operasional tanpa hasil tool).

Hasil pengujian nyata untuk `staff_umum` (2026-09-25) menunjukkan **dua kemungkinan jalur — keduanya aman, tidak ada karangan**:

- **Model memanggil tool** (sering pada pertanyaan "berapa banyak..."): `call_tool` mengembalikan "Akses ditolak", model meneruskannya (mis. *"Maaf, terdapat penolakan akses... role saya tidak berwenang..."*), dan audit mencatat `tool_dipanggil='query_data_operasional', akses_diizinkan=f` → **gap Bagian 4.b tertutup**.
- **Model menolak sendiri tanpa memanggil tool** (kadang pada pertanyaan "siapa nasabah..."): dipengaruhi prompt anti-halusinasi, model langsung menjawab tidak punya akses (mis. *"Maaf, saya tidak memiliki informasi... tool tidak dapat memberikan detail pribadi tanpa izin"*) tanpa mengarang. Audit mencatat `tool_dipanggil=NULL, akses_diizinkan=t` (seperti pertanyaan tanpa tool), tapi **teks pertanyaannya tetap tercatat** di kolom `pertanyaan`.

Jadi perbaikan ini **menghilangkan halusinasi** (masalah paling berbahaya — model tak lagi mengarang nama nasabah seolah dari data operasional) di **kedua** jalur; penutupan gap audit sebagai baris `f` bergantung pada apakah model kecil memilih memanggil tool (non-deterministik). Untuk audit yang 100% deterministik, produksi bisa menambah deteksi intent sebelum `call_model` — di luar cakupan module ini.

Trade-off (disadari): model tetap "tahu" tool SQL ada meski tak boleh memakainya, sedikit menambah panjang prompt tool. Sepadan demi penolakan rapi tanpa halusinasi.

> ✅ **Status verifikasi (2026-09-25, setelah rebuild):** `budi.umum` tanya "siapa nasabah N-00305" → menjawab tidak punya akses, **tanpa** mengarang "Prartha/Andi Wijaya" (bug awal hilang); tanya "berapa banyak pending" → *"terdapat penolakan akses..."* + audit `query_data_operasional / f`. `sari.finance` tetap mendapat data + audit `t`.

## 5. Trade-off yang Diambil (dan yang Sengaja Ditinggalkan)

Sesuai prinsip kurikulum ini untuk jujur soal keterbatasan (lihat catatan retrieval Module 9-22), berikut yang **tidak** diselesaikan module ini:

- **Autentikasi dibangun, tapi masih sederhana** (Bagian 1, Tahap 0) — `role`/`user_id` kini datang dari sesi login (signed session cookie), bukan body request, jadi celah "client mengaku supervisor" sudah ditutup. Yang **belum** production-grade: daftar user *hardcoded* di kode dengan password plaintext (produksi butuh hash bcrypt/argon2 + tabel user yang bisa dikelola admin), dan session store masih bersandar pada cookie sederhana (produksi mungkin butuh server-side session store, rotasi secret, dan CSRF protection pada form). Ini catatan untuk dibawa ke produksi: fondasi identitas sudah ada dan benar arsitekturnya, tapi kerasnya masih level demo.
- **Audit log bisa "kebanjiran" kalau trafik tinggi** — setiap tool yang dicoba (termasuk yang ditolak) menulis satu baris `INSERT` sinkron sebelum response dikirim ke user, menambah latency kecil ke tiap request yang memicu tool. Untuk skala training ini dampaknya tidak terasa; untuk produksi dengan trafik tinggi, pola yang lebih matang biasanya menulis audit log secara asinkron/lewat queue supaya tidak memperlambat response ke user — di luar cakupan rangkaian Module 23-27.
- **Role di module ini hardcoded jadi tiga pilihan tetap** (`staff_umum`, `staff_finance`, `supervisor`) — sistem RBAC produksi biasanya menyimpan role di tabel terpisah yang bisa dikelola admin tanpa deploy ulang kode. Untuk kurikulum ini, tiga role cukup untuk mendemonstrasikan mekanismenya.
- **`ringkasan_data_diakses` di `audit_log` belum diisi** (masih `None` di semua pemanggilan `log_audit()`, lihat Tahap D) — kolom ini sengaja disiapkan skemanya untuk pengembangan lanjutan (mis. mencatat `nasabah_id` spesifik yang diakses per query), tapi mengisinya butuh mem-parsing argumen tool lebih detail per jenis tool, di luar cakupan waktu rangkaian Module 23-27. Disebutkan di sini supaya kita tahu ini keterbatasan yang disengaja, bukan kolom yang terlupa.
- **Gap audit untuk role tidak berwenang — SUDAH DIATASI** (Bagian 4): gap ini (percobaan akses ditolak tak tercatat) ditemukan lewat pengujian, lalu **diperbaiki** dengan menegakkan RBAC di eksekusi (`call_tool`) alih-alih menyembunyikan tool di `call_model` — sekarang percobaan yang ditolak tercatat `tool_dipanggil='query_data_operasional', akses_diizinkan=f`. Dicantumkan di sini sebagai catatan perjalanan, bukan keterbatasan yang tersisa.

## 6. Apa yang TIDAK Ada di Module Ini

- Login/session **production-grade** (hash password, tabel user yang dikelola admin, CSRF protection, JWT) — login sesi *sederhana* sudah dibangun di Tahap 0; yang belum ada adalah pengerasannya. Lihat Bagian 1 dan Bagian 5.
- Audit logging asinkron/queue — lihat Bagian 5.
- ~~Mitigasi gap audit untuk percobaan akses role tidak berwenang~~ — **sudah diimplementasikan** di module ini (RBAC ditegakkan di `call_tool` + prompt anti-halusinasi, Bagian 4.c). Bukan lagi item yang tertinggal.
- ~~UI `chat.html` belum mengirim `role`/`user_id`~~ — **sudah tidak berlaku sejak Tahap 0**: role datang dari sesi login, jadi tool SQL kini bisa diuji **langsung di browser** (login sebagai `sari.finance`/`andi.super` untuk role berwenang, atau `budi.umum` untuk melihat penolakan), tidak lagi terbatas `curl`. Ini keuntungan pedagogis nyata dari mendahulukan login. Catatan: rencana "dropdown role di UI" yang sebelumnya diarahkan ke Module 29 (Polish Frontend) kini **digantikan** oleh login sesungguhnya — memilih role lewat dropdown tidak lagi masuk akal ketika role sudah terikat ke identitas terautentikasi (Module 29 bisa fokus ke polish lain).
- UI khusus NALA untuk melihat audit trail (mis. halaman `/audit-log` custom seperti `/data-operasional`) — belum ada, dan memang di luar cakupan pelatihan ini — cocok jadi pengembangan lanjutan sesudah pelatihan kalau tim ingin menambahkannya. Untuk kebutuhan langsung, **Adminer** (GUI database ringan) **sudah ditambahkan di module ini** — lihat setup, kredensial (`nala_admin`/`nala_app`), dan cara pakainya di **Tahap A** (`http://localhost:8081`) — supaya audit log bisa langsung diinspeksi lewat GUI begitu tabelnya dibuat.

## 7. Checkpoint Praktik

Langkah eksekusi lengkap ada di Bagian 3 (Tahap 0-D, Langkah 0-4) di atas. Yang perlu dipastikan sebelum rangkaian Module 23-27 dianggap selesai:

- [ ] Login sesi berfungsi (Tahap 0): buka `/` tanpa login → diarahkan ke `/login`; login `budi.umum`/`nala123` → masuk, banner "Masuk sebagai ..." muncul; `/logout` → kembali ke `/login`; `/chat` tanpa sesi → `401`
- [ ] Role `staff_umum` **tidak berhasil** mendapatkan data operasional — mendapat pesan penolakan, **bukan** angka data dan **bukan** nama nasabah karangan (audit `query_data_operasional / f` bila model memanggil tool, atau `NULL / t` bila model menolak sendiri — keduanya aman, RBAC di eksekusi Bagian 4.c). Kalau justru muncul nama nasabah karangan seolah dari data operasional, itu regresi ke desain lama (Bagian 4.a) — cek `call_model` menawarkan `ALL_TOOLS` dan system prompt anti-halusinasi terpasang.
- [ ] Role `staff_finance`/`supervisor` berhasil memicu tool SQL, tercatat di `audit_log` dengan `tool_dipanggil='query_data_operasional'`, `akses_diizinkan=true`
- [ ] Pertanyaan tanpa tool (mis. sapaan) tetap tercatat satu baris di `audit_log`
- [ ] `audit_log` tidak bisa di-`DELETE`/`UPDATE` lewat role `nala_app` (diverifikasi lewat `psql -U nala_app`)
- [ ] Tool RAG (Module 24) tetap bisa diakses semua role tanpa pengecualian, termasuk `staff_umum`

## Kesimpulan Module 23-27: NALA Jadi Agentic

Module 23-27 mengubah NALA dari sistem yang selalu menjalankan urutan langkah tetap (RAG chain Module 9-22) menjadi agent yang **memutuskan sendiri** kapan mencari dokumen, kapan mengambil data operasional, kapan menolak karena tidak berwenang — dengan jejak audit atas setiap keputusan itu. Lima module saling membangun: Module 23 menyiapkan fondasi data operasional di PostgreSQL beserta role database terpisah (`nala_admin`, `nala_readonly`, `nala_writer`), Module 24 memberi fondasi graph + tool pertama (refactor RAG lama), Module 25 menambah tool kedua dengan disiplin keamanan berlapis (whitelist, parameterized query, role database read-only) sekaligus membuktikan graph yang sama bisa memanggil dua tool berurutan (multi-hop) dalam satu pertanyaan tanpa kode baru (Module 25 Bagian 4), Module 26 menangani kasus pertanyaan ambigu dan salah pilih tool (routing) beserta pengaman `MAX_TOOL_ROUNDS`/`force_answer`, dan Module 27 menutup dengan login/session (Tahap 0) sebagai fondasi identitas + RBAC + audit yang relevan langsung untuk konteks kepatuhan PT Nusantara Finance sebagai institusi finansial — **dengan catatan jujur (Bagian 4) bahwa desain RBAC-nya sempat direvisi: barrier data terbukti aman, dan setelah pengujian membongkar gap audit pada desain awal, RBAC dipindah ke lapisan eksekusi sehingga percobaan akses yang ditolak pun ikut tercatat**.

Yang **belum** selesai secara jujur: autentikasi *production-grade* (login sesi sederhana sudah ada di Tahap 0, tapi password masih plaintext/hardcoded — Bagian 1, Bagian 5), skala produksi untuk audit logging (Bagian 5), dan kualitas routing yang bergantung pada model kecil (Module 26 Bagian 4) — semuanya bahan diskusi terbuka menuju **Module 28 (Redis: cache, job queue, rate limiting)** sebagai lapisan operasional berikutnya di atas stack ini, lalu Module 29 (polish frontend) dan Module 30 (peta arsitektur RAG), Module 31 (etika & governance), dan Module 32 (stress testing) yang menutup pelatihan.

---

Untuk informasi lebih lanjut, lihat [README utama](../README.md).
