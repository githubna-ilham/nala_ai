# Module 23: RBAC & Audit Logging

## Tujuan

Membatasi akses tool SQL (Module 21) berdasarkan role staff (RBAC) dan mencatat setiap percobaan akses — baik yang diizinkan maupun ditolak — ke audit trail permanen, sebagai penutup rangkaian Module 19-23 yang relevan untuk konteks kepatuhan institusi finansial.

## Definisi

**RBAC (Role-Based Access Control)** adalah pola pembatasan akses berdasarkan **peran** (role) yang dipegang seseorang, bukan identitas individunya satu per satu — di NALA, tiga role (`staff_umum`, `staff_finance`, `supervisor`) menentukan tool mana yang boleh dipicu, bukan siapa nama orangnya. Prinsip yang dipegang sejak awal adalah **fail-safe**: kalau `role` tidak disertakan sama sekali di request, sistem mengasumsikan hak akses paling rendah (`staff_umum`) — bukan **fail-open** yang mengasumsikan akses penuh saat informasi tidak lengkap, karena fail-open jauh lebih berbahaya untuk sistem yang menyentuh data finansial nasabah.

**Audit logging** adalah pencatatan permanen atas setiap percobaan akses — siapa, tanya apa, tool apa, diizinkan atau ditolak, kapan — terpisah dari (dan melengkapi) RBAC: RBAC mencegah **sebelum** kejadian, audit logging mencatat **setelah** kejadian supaya bisa ditelusuri ulang kalau diaudit regulator. Tabel `audit_log` dibuat **append-only** dari sisi aplikasi — role `nala_app` yang menulisnya cuma diberi `INSERT`/`SELECT`, sengaja **tidak** diberi `UPDATE`/`DELETE` — supaya jejak yang sudah tercatat tidak bisa dihapus atau diubah lewat koneksi aplikasi mana pun, properti penting supaya audit trail tetap kredibel.

```mermaid
flowchart LR
    R["Request: role tidak disebutkan?"] -->|"fail-safe"| D["Default: staff_umum<br/>(hak akses terendah)"]
    U["Staff + role"] --> C{"RBAC: role berwenang<br/>untuk tool ini?"}
    C -->|"ya"| T["Tool dijalankan"]
    C -->|"tidak"| X["Ditolak, tanpa eksekusi"]
    T --> L["audit_log<br/>(append-only, nala_app)"]
    X --> L
```

## Hasil Akhir yang Diharapkan

- Role `staff_umum` ditolak saat mencoba memicu tool SQL (`query_data_operasional`), sementara `staff_finance`/`supervisor` berhasil — pengecekan role dilakukan berlapis (di `call_model` lewat filter tool, dan diverifikasi ulang di `call_tool`)
- Tool RAG tetap bisa diakses semua role tanpa pengecualian
- Tabel `audit_log` mencatat setiap percobaan tool (diizinkan maupun ditolak) beserta pertanyaan tanpa tool sama sekali — lewat role database `nala_app` yang hanya bisa `INSERT`/`SELECT`, tidak bisa `UPDATE`/`DELETE` (audit log append-only)
- `ChatRequest` menerima `user_id`/`role` dengan default paling terbatas (`staff_umum`) kalau tidak disertakan — fail-safe, bukan fail-open
- Kita paham secara eksplisit batasan yang belum diselesaikan module ini: `role`/`user_id` masih simulasi lewat body request (bukan autentikasi sungguhan), audit logging masih sinkron (belum async/queue untuk skala produksi)

## 1. Kenapa Ini Bukan "Fitur Tambahan", Tapi Syarat untuk Data Finansial

Sampai akhir Module 22, tool `query_data_operasional` (Module 21) bisa dipicu **siapa pun** yang mengirim request ke `/chat` — tidak ada pengecekan sama sekali siapa yang bertanya, atau apakah orang itu berhak melihat data pengajuan kredit/klaim asuransi nasabah. Untuk demo dan latihan sejauh ini itu cukup, tapi PT Nusantara Finance adalah institusi finansial — di dunia nyata, sektor ini diatur ketat (OJK, dan prinsip umum tata kelola data finansial): siapa yang mengakses data nasabah, kapan, dan untuk keperluan apa **harus bisa dijawab** kalau sewaktu-waktu diaudit, baik oleh auditor internal maupun regulator eksternal.

Dua kebutuhan berbeda tapi saling melengkapi:

1. **RBAC (Role-Based Access Control)** — mencegah **sebelum** kejadian: staff yang tidak berwenang tidak boleh bisa memicu tool yang mengakses data operasional sama sekali, bukan cuma "seharusnya tidak bertanya yang aneh-aneh".
2. **Audit logging** — mencatat **setelah** kejadian: kalaupun akses terjadi (baik yang diizinkan maupun yang ditolak RBAC), ada jejak permanen siapa, tanya apa, tool apa yang terlibat, dan kapan — supaya bisa ditelusuri ulang.

```mermaid
sequenceDiagram
    participant U as Staff (role tertentu)
    participant API as POST /chat
    participant AG as Agent (LangGraph)
    participant SQL as Tool SQL (Module 21)
    participant DB as PostgreSQL
    participant LOG as audit_log

    U->>API: {"message": "...", "role": "...", "user_id": "..."}
    API->>AG: invoke(state termasuk role)
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

⚠️ **Batasan yang jujur perlu disampaikan sejak awal**: module ini **tidak** membangun sistem autentikasi/login sungguhan (itu di luar cakupan training ini — lihat catatan "Di Luar Cakupan" desain kurikulum). `role` dan `user_id` di sini dikirim sebagai bagian dari body request, cara paling sederhana untuk mendemonstrasikan mekanisme RBAC/audit tanpa membangun seluruh sistem session/login. Di deployment produksi sungguhan, kedua nilai itu **harus** berasal dari sesi yang sudah terautentikasi (mis. JWT/session cookie yang divalidasi di middleware), bukan dari body JSON yang bisa ditulis siapa saja — kalau tidak, siapa pun bisa mengaku `role: "supervisor"` dan RBAC ini jadi tidak berarti. Ini disebut eksplisit di Bagian 5.

## 2. Desain: Role dan Tool yang Diizinkan

| Role | `cari_dokumen_sop` (RAG) | `query_data_operasional` (SQL) | Contoh jabatan |
|---|---|---|---|
| `staff_umum` | ✅ Diizinkan | ❌ Ditolak | Staff customer service umum, hanya perlu jawab pertanyaan prosedur |
| `staff_finance` | ✅ Diizinkan | ✅ Diizinkan | Staff yang menangani pengajuan kredit/klaim, perlu lihat status transaksi |
| `supervisor` | ✅ Diizinkan | ✅ Diizinkan | Sama seperti `staff_finance` untuk cakupan Module 19-23 — di produksi biasanya juga punya akses laporan agregat lebih luas, di luar cakupan latihan ini |

Semua role tetap bisa memakai tool RAG — dokumen SOP bukan data sensitif per-nasabah, wajar diakses siapa pun yang bekerja di perusahaan. Yang dibatasi murni akses ke `query_data_operasional`, karena tool itu menyentuh data transaksi nasabah.

## 3. Struktur Kode yang Ditambahkan

Empat tahap: **Tahap A** menambah tabel `audit_log` dan role database khusus untuk menulis log, **Tahap B** membangun fungsi pencatatan audit, **Tahap C** menambahkan pengecekan RBAC ke agent (dengan pertahanan berlapis, meniru pola Module 21), **Tahap D** menyambungkan semuanya ke `/chat`.

### Tahap A — Tabel `audit_log` dan role database khusus untuk menulis log

**Langkah 1 — Tambah tabel dan role baru di `db/seed.sql`**

```sql
-- db/seed.sql — tambahan di akhir file (setelah GRANT nala_readonly dari Module 21)
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

Perhatikan: `nala_app` adalah role **ketiga** setelah `nala_admin` (Module 21 Tahap A, dipakai container init) dan `nala_readonly` (Module 21 Tahap B, dipakai tool SQL untuk `SELECT` data operasional) — bukan menambah hak akses ke role yang sudah ada. `nala_app` sengaja **hanya** diberi `INSERT` dan `SELECT` ke `audit_log`, **tidak** diberi akses apa pun ke `pengajuan_kredit`/`klaim_asuransi` (itu tugas `nala_readonly`), dan **tidak** diberi `UPDATE`/`DELETE` ke `audit_log` itu sendiri — konsekuensinya, baris audit yang sudah tercatat **tidak bisa diubah atau dihapus** lewat koneksi aplikasi mana pun, cuma bisa ditambah. Ini properti penting untuk audit trail yang kredibel: kalau aplikasi (atau siapa pun yang berhasil mengeksploitasinya) bisa menghapus jejaknya sendiri, audit log itu tidak banyak berguna untuk kepatuhan.

**▶️ Jalankan & lihat hasilnya**

```bash
docker compose down
docker volume rm nala_postgres_data 2>/dev/null || true
docker compose up -d --build postgres
docker compose logs -f postgres
```

```bash
docker compose exec postgres psql -U nala_app -d nala_operasional -c \
  "INSERT INTO audit_log (user_id, role, pertanyaan, tool_dipanggil, akses_diizinkan) VALUES ('test-user', 'staff_umum', 'tes manual', NULL, true);"
docker compose exec postgres psql -U nala_app -d nala_operasional -c "DELETE FROM audit_log WHERE id = 1;"
```

✅ **Indikator sukses**: `INSERT` berhasil (`INSERT 0 1`), tapi `DELETE` **harus gagal** dengan `permission denied for table audit_log` — bukti audit log tidak bisa dihapus lewat role aplikasi ini, konsisten dengan Bagian 1.

<details>
<summary><strong>Pakai Claude Code? Salin prompt berikut, paste untuk eksekusi Langkah 1</strong></summary>

```
Tambah tabel audit_log dan role database khusus untuk menulis log
(Module 23, Tahap A) — role INSERT+SELECT saja, tanpa UPDATE/
DELETE.

GOAL:
- Di akhir resources/starter-code/day-4/nala/db/seed.sql (setelah
  GRANT nala_readonly yang sudah ada dari Module 21), tambahkan: CREATE
  TABLE audit_log (id SERIAL PK, waktu TIMESTAMPTZ NOT NULL DEFAULT
  now(), user_id VARCHAR(50) NOT NULL, role VARCHAR(20) NOT NULL,
  pertanyaan TEXT NOT NULL, tool_dipanggil VARCHAR(50) nullable,
  akses_diizinkan BOOLEAN NOT NULL, ringkasan_data_diakses TEXT
  nullable); CREATE ROLE nala_app WITH LOGIN PASSWORD 'app_dev_only';
  GRANT CONNECT ON DATABASE nala_operasional TO nala_app; GRANT USAGE
  ON SCHEMA public TO nala_app; GRANT INSERT, SELECT ON audit_log TO
  nala_app; GRANT USAGE, SELECT ON SEQUENCE audit_log_id_seq TO
  nala_app;

CONTEXT:
- nala_app adalah role KETIGA, terpisah dari nala_admin (init) dan
  nala_readonly (Module 21, akses SELECT ke pengajuan_kredit/
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

- **`POSTGRES_APP_DSN` memakai `nala_app`, bukan `nala_admin` atau `nala_readonly`.** Sama seperti Module 21 Bagian 4 Langkah 4 (tool SQL memakai `nala_readonly`, bukan admin), setiap komponen memakai role paling terbatas yang cukup untuk tugasnya — menulis log tidak butuh (dan tidak boleh punya) akses ke tabel data nasabah.
- **Kegagalan menulis audit log sengaja tidak melempar exception ke pemanggil.** Kalau `log_audit()` gagal (mis. PostgreSQL sedang down) dan itu membuat `/chat` ikut gagal (`500`), NALA jadi tidak bisa menjawab pertanyaan sederhana hanya karena masalah di sistem pencatatan — trade-off yang diambil di sini adalah **ketersediaan layanan chat lebih diprioritaskan** daripada audit yang sempurna 100%, dengan syarat kegagalan itu sendiri tercatat di log aplikasi (`logger.error`) supaya bisa dipantau dan ditindaklanjuti terpisah, bukan diam-diam hilang. Ini trade-off yang bisa diperdebatkan (institusi finansial yang sangat ketat mungkin memilih sebaliknya — menolak melayani permintaan kalau audit tidak bisa dijamin tercatat), disebutkan di sini secara eksplisit supaya kita tahu ini keputusan sadar, bukan kealpaan.

**▶️ Jalankan & lihat hasilnya**

```bash
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
terbatas (Module 23, Tahap B) — belum disambungkan ke endpoint
mana pun.

GOAL:
- Buat resources/starter-code/day-4/nala/app/audit.py berisi:
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

**Langkah 3 — Tambah `role` ke `AgentState`, filter tool berdasarkan role di `call_model`, dan verifikasi ulang di `call_tool`**

```python
# app/agent.py — perubahan pada AgentState dan build_agent()
class AgentState(TypedDict):
    messages: Annotated[list[dict], operator.add]
    role: str
    called_tools: Annotated[list[dict], operator.add]


SQL_ALLOWED_ROLES = {"staff_finance", "supervisor"}


def _tools_for_role(role: str) -> list[dict]:
    tools = [RAG_TOOL_SCHEMA]
    if role in SQL_ALLOWED_ROLES:
        tools.append(SQL_TOOL_SCHEMA)
    return tools


def build_agent(ollama_client, vector_store, ollama_base_url: str):
    def call_model(state: AgentState) -> dict:
        allowed_tools = _tools_for_role(state["role"])
        response_message = ollama_client.chat(state["messages"], tools=allowed_tools)
        return {"messages": [response_message]}

    def call_tool(state: AgentState) -> dict:
        last_message = state["messages"][-1]
        tool_messages = []
        called = []
        for call in last_message.get("tool_calls", []):
            name = call["function"]["name"]
            args = call["function"]["arguments"]

            if name == "query_data_operasional" and state["role"] not in SQL_ALLOWED_ROLES:
                result = (
                    "Akses ditolak: role Anda tidak berwenang mengakses data "
                    "operasional. Hubungi supervisor kalau ini seharusnya diizinkan."
                )
                called.append({"tool": name, "diizinkan": False})
            elif name == "cari_dokumen_sop":
                result = rag_search(args["query"], vector_store, ollama_base_url)
                called.append({"tool": name, "diizinkan": True})
            elif name == "query_data_operasional":
                result = query_data_operasional(**args)
                called.append({"tool": name, "diizinkan": True})
            else:
                result = f"Tool '{name}' tidak dikenal."
                called.append({"tool": name, "diizinkan": False})

            tool_messages.append({"role": "tool", "name": name, "content": result})

        return {"messages": tool_messages, "called_tools": called}

    # should_continue, force_answer, dan struktur graph TIDAK berubah dari Module 22
    ...
```

Bagian paling penting di sini: **pengecekan role dilakukan di `call_tool`, bukan hanya lewat `_tools_for_role()` di `call_model`.** Ini pola pertahanan berlapis yang sama seperti Module 21 Bagian 3 (validasi `tabel` diperiksa ulang di kode Python, bukan cuma dipercaya dari skema tool) — kalau `_tools_for_role()` entah bagaimana terlewat (bug, atau `state["role"]` berubah di antara `call_model` dan `call_tool` akibat kesalahan lain), `call_tool` **tetap** menolak eksekusi `query_data_operasional` untuk role yang tidak berwenang, sebelum satu baris pun query dijalankan ke database. Field baru `called_tools` mencatat **setiap** tool yang model **coba** panggil, termasuk yang ditolak RBAC — ini penting untuk Tahap D: percobaan akses yang ditolak **tetap** harus masuk audit trail, bukan cuma yang berhasil (kegagalan/percobaan akses yang tidak sah justru salah satu hal paling penting untuk terlihat di audit compliance).

**▶️ Jalankan & lihat hasilnya**

Belum ada endpoint yang mengirim `role` (itu Tahap D) — cukup pastikan tidak ada error saat startup:

```bash
docker compose up --build api
```

✅ **Indikator sukses**: log `api` menunjukkan `Uvicorn running` tanpa traceback.

<details>
<summary><strong>Pakai Claude Code? Salin prompt berikut, paste untuk eksekusi Langkah 3</strong></summary>

```
Tambah RBAC ke agent — role membatasi tool mana yang ditawarkan ke
LLM, DAN diverifikasi ulang saat eksekusi tool (pertahanan berlapis)
(Module 23, Tahap C).

GOAL:
- Di resources/starter-code/day-4/nala/app/agent.py:
  1. Tambah field baru ke AgentState: role: str, dan called_tools:
     Annotated[list[dict], operator.add].
  2. Tambah konstanta modul SQL_ALLOWED_ROLES = {"staff_finance",
     "supervisor"} dan fungsi _tools_for_role(role: str) -> list[dict]
     yang selalu menyertakan RAG_TOOL_SCHEMA, dan menyertakan
     SQL_TOOL_SCHEMA HANYA kalau role ada di SQL_ALLOWED_ROLES.
  3. Di call_model: ganti tools_schema tetap dengan
     allowed_tools = _tools_for_role(state["role"]), kirim itu sebagai
     parameter tools ke ollama_client.chat().
  4. Di call_tool: untuk tiap tool_call, KALAU name ==
     "query_data_operasional" DAN state["role"] tidak ada di
     SQL_ALLOWED_ROLES, JANGAN eksekusi query_data_operasional sama
     sekali — set result ke pesan penolakan akses, dan catat
     {"tool": name, "diizinkan": False} ke list called. Kalau role
     berwenang atau tool-nya cari_dokumen_sop, eksekusi seperti biasa
     dan catat {"tool": name, "diizinkan": True}. Tool tidak dikenal
     tetap dicatat {"tool": name, "diizinkan": False}. Tambahkan key
     "name": name ke tiap dict pesan tool (selain "role" dan
     "content"). Return {"messages": tool_messages, "called_tools":
     called}.

CONTEXT:
- should_continue, force_answer (Module 22), dan struktur graph
  (add_node/add_conditional_edges/add_edge) TIDAK berubah di langkah
  ini.
- called_tools akan dipakai app/main.py di Tahap D untuk audit log —
  belum disambungkan di langkah ini.

GUARDRAIL:
- Pengecekan role WAJIB ada di call_tool (bukan cuma di call_model
  lewat _tools_for_role) — ini pertahanan berlapis, jangan dihilangkan
  salah satunya dengan alasan "sudah dicek di tempat lain".
- JANGAN eksekusi query_data_operasional untuk role yang tidak ada di
  SQL_ALLOWED_ROLES dengan alasan apa pun.
```

</details>

### Tahap D — Sambungkan RBAC & audit logging ke `/chat`

**Langkah 4 — Perbarui `ChatRequest`, kirim `role` ke agent, panggil `log_audit()` setelah agent selesai**

```python
# app/main.py — perubahan
from app.audit import log_audit


class ChatRequest(BaseModel):
    message: str
    user_id: str = "anonim"
    role: str = "staff_umum"


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    initial_state = {
        "messages": [
            {"role": "system", "content": NALA_SYSTEM_PROMPT_AGENT},
            {"role": "user", "content": request.message},
        ],
        "role": request.role,
        "called_tools": [],
    }
    final_state = nala_agent.invoke(initial_state)
    reply = final_state["messages"][-1]["content"]

    called_tools = final_state.get("called_tools", [])
    if called_tools:
        for entry in called_tools:
            log_audit(
                user_id=request.user_id,
                role=request.role,
                pertanyaan=request.message,
                tool_dipanggil=entry["tool"],
                akses_diizinkan=entry["diizinkan"],
            )
    else:
        log_audit(
            user_id=request.user_id,
            role=request.role,
            pertanyaan=request.message,
            tool_dipanggil=None,
            akses_diizinkan=True,
        )

    return ChatResponse(reply=reply)
```

- **`ChatRequest` bertambah dua field opsional** (`user_id`, `role`, keduanya dengan default) — bukan perubahan yang merusak (*breaking change*): request lama tanpa kedua field ini (mis. dari `chat.html` yang belum diperbarui, atau script lama) tetap valid, otomatis diperlakukan sebagai `role: "staff_umum"` (paling terbatas — **fail-safe**, bukan fail-open, prinsip keamanan penting: kalau role tidak disebutkan, asumsikan yang paling rendah hak aksesnya, bukan yang paling tinggi).
- **Satu baris audit per tool yang dicoba** (termasuk yang ditolak), bukan satu baris per pertanyaan — kalau user memicu dua tool dalam satu pertanyaan (skenario "kenapa ditolak" di Module 22 Bagian 3), keduanya tercatat terpisah, masing-masing dengan status izin sendiri.
- **Pertanyaan tanpa tool sama sekali** (mis. sapaan) tetap dicatat satu baris dengan `tool_dipanggil=None` — audit trail NALA mencakup **semua** interaksi, bukan cuma yang menyentuh data sensitif, supaya pola pemakaian keseluruhan juga bisa dianalisis kalau diperlukan.

**▶️ Jalankan & lihat hasilnya**

```bash
docker compose up --build api
```

Uji **role tidak berwenang** (harus ditolak):

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Berapa banyak pengajuan kredit yang statusnya pending?", "user_id": "budi.cs", "role": "staff_umum"}'
```

⚠️ **Ekspektasi awal vs kenyataan** (lihat Bagian 4 "Hasil Uji Nyata" untuk detail lengkap): indikator sukses awalnya ditulis "jawaban menyebut akses ditolak, baris audit `tool_dipanggil='query_data_operasional', akses_diizinkan=f`". Pengujian nyata menunjukkan hasil yang berbeda — karena `_tools_for_role("staff_umum")` **tidak menyertakan** `SQL_TOOL_SCHEMA` sama sekali, model tidak pernah mengeluarkan `tool_calls` asli untuk tool itu (Ollama tidak bisa membuat `tool_calls` terstruktur untuk tool yang tidak ada di parameter `tools`) — jadi `call_tool` (Tahap C, lapis pertahanan kedua) tidak pernah tereksekusi untuk kasus ini. Yang benar-benar terjadi:

```bash
docker compose exec postgres psql -U nala_admin -d nala_operasional -c \
  "SELECT user_id, role, tool_dipanggil, akses_diizinkan FROM audit_log ORDER BY id DESC LIMIT 1;"
```

baris terakhir menunjukkan `role='staff_umum'`, `tool_dipanggil=NULL` (bukan `'query_data_operasional'`), `akses_diizinkan=t` (bukan `f`) — seolah tidak ada percobaan tool sama sekali, padahal user jelas bertanya soal data operasional. Data tetap **tidak bocor** (tidak ada query SQL yang benar-benar berjalan — barrier utama bekerja), tapi audit trail-nya tidak mencerminkan bahwa ada percobaan akses ke ranah yang dibatasi. Ini gap nyata, dibahas lebih lanjut di Bagian 4.

Uji **role berwenang** (harus berhasil):

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Berapa banyak pengajuan kredit yang statusnya pending?", "user_id": "rina.finance", "role": "staff_finance"}'
```

✅ **Indikator sukses**: jawaban berisi angka yang benar (sama seperti Module 21-22), dan baris audit terbaru menunjukkan `role='staff_finance'`, `akses_diizinkan=t`.

Terakhir, tarik seluruh audit trail untuk melihat gambaran lengkap:

```bash
docker compose exec postgres psql -U nala_admin -d nala_operasional -c \
  "SELECT waktu, user_id, role, tool_dipanggil, akses_diizinkan FROM audit_log ORDER BY waktu DESC LIMIT 10;"
```

✅ **Indikator sukses**: setiap percobaan dari Langkah ini (dan pengujian Module 20-22 sebelumnya kalau sudah dilakukan setelah Tahap A-D selesai) muncul sebagai baris terpisah, urut berdasarkan waktu.

<details>
<summary><strong>Pakai Claude Code? Salin prompt berikut, paste untuk eksekusi Langkah 4</strong></summary>

```
Sambungkan role ke request /chat dan panggil audit logging setelah
agent selesai memproses (Module 23, Tahap D).

GOAL:
- Di resources/starter-code/day-4/nala/app/main.py:
  1. Tambah import log_audit dari app.audit.
  2. Tambah dua field baru ke class ChatRequest: user_id: str =
     "anonim", role: str = "staff_umum" (keduanya punya default,
     bukan wajib diisi).
  3. Ubah fungsi chat(): initial_state sekarang juga menyertakan
     "role": request.role dan "called_tools": [] (selain "messages"
     yang sudah ada). Setelah final_state = nala_agent.invoke(...) dan
     reply diambil, baca called_tools = final_state.get("called_tools",
     []); kalau tidak kosong, panggil log_audit() sekali untuk TIAP
     entry di called_tools (user_id=request.user_id, role=request.role,
     pertanyaan=request.message, tool_dipanggil=entry["tool"],
     akses_diizinkan=entry["diizinkan"]); kalau kosong (tidak ada tool
     dipanggil sama sekali), panggil log_audit() sekali dengan
     tool_dipanggil=None, akses_diizinkan=True. Baru setelah itu
     return ChatResponse(reply=reply) seperti biasa.

CONTEXT:
- app/agent.py sudah menghasilkan called_tools di final_state dari
  Tahap C.
- app/audit.py sudah punya log_audit() dari Tahap B.
- Kontrak response ChatResponse{reply} TIDAK berubah — hanya
  ChatRequest yang bertambah dua field opsional (default value,
  backward compatible).

GUARDRAIL:
- JANGAN jadikan user_id/role wajib diisi (harus tetap punya default)
  — request lama tanpa kedua field ini harus tetap valid.
- JANGAN ubah endpoint /chat/stream, /health, /, /upload.
- Kegagalan log_audit() (ditangani internal di app/audit.py) TIDAK
  BOLEH membuat endpoint /chat mengembalikan error — pastikan urutan
  kode: reply sudah didapat SEBELUM log_audit() dipanggil, dan
  log_audit() sendiri sudah menangani exception-nya sendiri (dari
  Tahap B).
```

</details>

**📄 Kode lengkap Module 23** (`app/audit.py`, potongan relevan `app/agent.py` dan `app/main.py`, `db/seed.sql` tambahan — sudah ditampilkan utuh di Langkah 1-4 di atas).

## 4. Hasil Uji Nyata: Barrier Data Aman, Tapi Audit Trail Punya Celah

Bagian ini mendokumentasikan temuan sungguhan dari pengujian Tahap A-D — termasuk satu gap yang **tidak diantisipasi** rencana awal Bagian 3 Tahap D — supaya kita tahu apa yang benar-benar terjadi, bukan versi ideal di skema `audit_log`.

### a. Role tidak berwenang: jawaban jadi JSON mentah, bukan penolakan yang rapi

Uji `role: "staff_umum"` (4 kali percobaan berulang, pertanyaan identik "Berapa banyak pengajuan kredit yang statusnya pending?") **konsisten** menghasilkan jawaban berupa teks JSON mentah, bukan kalimat penolakan:

```json
{"name": "query_data_operasional", "parameters": {"query": "status pending pengajuan kredit"}}
```

Penjelasannya ada di desain `_tools_for_role()` (Bagian 3 Tahap C): untuk `staff_umum`, `SQL_TOOL_SCHEMA` **tidak pernah dikirim** ke Ollama sebagai bagian parameter `tools`. Model tetap "ingin" memanggil tool itu (dari sudut pandangnya, pertanyaan ini jelas butuh data operasional), tapi karena skema tool itu tidak tersedia untuknya, Ollama tidak bisa membungkusnya jadi field `tool_calls` yang terstruktur — hasilnya, model menulis niatnya sebagai **teks biasa** yang kebetulan berbentuk JSON, dan itu yang sampai ke user sebagai jawaban akhir.

**Yang tetap benar**: karena ini bukan `tool_calls` asli, `call_tool` tidak pernah dipanggil — **tidak ada satu query SQL pun yang benar-benar dieksekusi**. Barrier data (Bagian 3 Tahap C) bekerja seperti yang dirancang; data nasabah tidak bocor ke role yang tidak berwenang. Yang **tidak** sesuai rencana adalah kualitas pengalaman pengguna (jawaban JSON mentah membingungkan, bukan kalimat "akses ditolak" yang membantu) — lapis pertahanan kedua di `call_tool` (pengecekan `state["role"] not in SQL_ALLOWED_ROLES`) yang menghasilkan pesan penolakan rapi itu **tidak pernah tereksekusi** di skenario ini, karena tidak ada `tool_calls` yang sampai ke sana sama sekali.

### b. Konsekuensi ke audit trail: percobaan akses yang ditolak tidak tercatat sebagai percobaan

Ini akibat langsung dari Bagian 4.a yang lebih penting untuk konteks kepatuhan: karena `called_tools` di `call_tool` (Tahap C) hanya terisi kalau ada `tool_calls` asli untuk diproses, dan di skenario Bagian 4.a itu tidak pernah terjadi, `final_state["called_tools"]` tetap `[]` — kode di `app/main.py` (Tahap D) jatuh ke cabang `else`, mencatat audit log seolah **tidak ada tool yang dicoba sama sekali**:

```
role='staff_umum', tool_dipanggil=NULL, akses_diizinkan=t
```

Bandingkan dengan ekspektasi awal Bagian 3 Tahap D Langkah 4 yang menulis `tool_dipanggil='query_data_operasional', akses_diizinkan=f` — **itu tidak terjadi** pada implementasi nyata ini. Untuk role `staff_finance` (berwenang), alurnya sesuai rencana: `tool_calls` asli terbentuk, `call_tool` tereksekusi, `called_tools` terisi `{"tool": "query_data_operasional", "diizinkan": true}`, audit log mencatat `tool_dipanggil='query_data_operasional', akses_diizinkan=t` — persis seperti didesain.

**Kenapa ini penting untuk konteks kepatuhan (bukan cuma detail teknis)**: dari sudut pandang audit compliance, "staff yang tidak berwenang mencoba mengakses data nasabah" adalah salah satu kejadian yang **paling** perlu terlihat di jejak audit — justru lebih penting daripada mencatat akses yang berhasil. Implementasi saat ini punya gap di titik itu: filter tool di level `call_model` (lapis pertama, Bagian 3 Tahap C) efektif mencegah kebocoran data, tapi **efek sampingnya** justru menyembunyikan percobaan itu dari audit trail, karena `call_tool` (tempat logging keputusan izin ditulis) tidak pernah kebagian giliran.

### c. Mitigasi yang belum diimplementasikan (dicatat untuk Module 24-27/pengembangan lanjutan)

Perbaikan paling langsung: bandingkan `state["role"]` dengan permintaan aktual di `call_model` **sebelum** memanggil `ollama_client.chat()` — kalau isi pesan user mengandung sinyal kuat butuh data operasional (sulit dideteksi robust tanpa NLU tambahan), atau lebih sederhana: selalu sertakan `SQL_TOOL_SCHEMA` ke **semua** role saat memanggil model, tapi tetap blokir eksekusinya di `call_tool` (lapis kedua) seperti sudah dirancang — pendekatan ini mengorbankan sedikit "kebersihan" filter tapi memastikan `call_tool` (dan pencatatan audit-nya) selalu kebagian giliran untuk tool SQL, apa pun rolenya. Trade-off-nya: model tetap "tahu" tool itu ada meski tidak boleh dipakai role tertentu, sedikit menambah panjang prompt tool yang dikirim ke Ollama. Ini **belum diimplementasikan** di rangkaian Module 19-23 — dicatat di sini sebagai temuan jujur untuk didiskusikan, bukan diperbaiki diam-diam supaya materi terlihat sempurna.

## 5. Trade-off yang Diambil (dan yang Sengaja Ditinggalkan)

Sesuai prinsip kurikulum ini untuk jujur soal keterbatasan (lihat catatan retrieval Module 7-18), berikut yang **tidak** diselesaikan module ini:

- **Autentikasi sungguhan tidak dibangun** (Bagian 1) — `role`/`user_id` dari body request adalah simulasi, bukan mekanisme aman. Ini catatan paling penting untuk dibawa ke Module 24-27/produksi: RBAC di atas fondasi yang tidak terautentikasi cuma berguna untuk demo, bukan untuk deployment nyata.
- **Audit log bisa "kebanjiran" kalau trafik tinggi** — setiap tool yang dicoba (termasuk yang ditolak) menulis satu baris `INSERT` sinkron sebelum response dikirim ke user, menambah latency kecil ke tiap request yang memicu tool. Untuk skala training ini dampaknya tidak terasa; untuk produksi dengan trafik tinggi, pola yang lebih matang biasanya menulis audit log secara asinkron/lewat queue supaya tidak memperlambat response ke user — di luar cakupan rangkaian Module 19-23.
- **Role di module ini hardcoded jadi tiga pilihan tetap** (`staff_umum`, `staff_finance`, `supervisor`) — sistem RBAC produksi biasanya menyimpan role di tabel terpisah yang bisa dikelola admin tanpa deploy ulang kode. Untuk kurikulum ini, tiga role cukup untuk mendemonstrasikan mekanismenya.
- **`ringkasan_data_diakses` di `audit_log` belum diisi** (masih `None` di semua pemanggilan `log_audit()`, lihat Tahap D) — kolom ini sengaja disiapkan skemanya untuk pengembangan lanjutan (mis. mencatat `nasabah_id` spesifik yang diakses per query), tapi mengisinya butuh mem-parsing argumen tool lebih detail per jenis tool, di luar cakupan waktu rangkaian Module 19-23. Disebutkan di sini supaya kita tahu ini keterbatasan yang disengaja, bukan kolom yang terlupa.
- **Gap audit untuk role tidak berwenang** (Bagian 4.b, ditemukan lewat pengujian, bukan disengaja) — percobaan akses SQL oleh role yang tidak berwenang tidak tercatat sebagai percobaan tool di `audit_log` (`tool_dipanggil` tetap `NULL`), karena filter tool di `call_model` mencegah `tool_calls` asli terbentuk sebelum `call_tool` (tempat logging keputusan izin) sempat berjalan. Data tetap aman (tidak ada query yang benar-benar dieksekusi), tapi jejak auditnya tidak selengkap yang diasumsikan rencana awal — mitigasi belum diimplementasikan, lihat Bagian 4.c.

## 6. Apa yang TIDAK Ada di Module Ini

- Login/session/JWT sungguhan — lihat Bagian 1 dan Bagian 5.
- Audit logging asinkron/queue — lihat Bagian 5.
- Mitigasi gap audit untuk percobaan akses role tidak berwenang (Bagian 4.b-c) — teridentifikasi lewat pengujian, belum diperbaiki di rangkaian Module 19-23.
- UI khusus NALA untuk melihat audit trail (mis. halaman `/audit-log` custom seperti `/data-operasional`) — bisa jadi bahan capstone (Module 24-27) kalau kelompok tertentu ingin menambahkannya. Untuk kebutuhan langsung, `docker-compose.yml` menyediakan **Adminer** (`http://localhost:8081`, image generik `adminer:latest`, bukan dibuat khusus untuk NALA) sebagai GUI database ringan — jauh lebih hemat RAM dibanding pgAdmin, penting karena laptop kita sudah menjalankan banyak service sekaligus (Ollama, OpenSearch, PostgreSQL, Airflow, Langfuse).

  Login Adminer (`http://localhost:8081`) pakai salah satu kredensial berikut (default, kecuali `POSTGRES_ADMIN_PASSWORD` di-override lewat `.env`):

  | Field | Akses penuh (`nala_admin`) | Akses terbatas ke `audit_log` saja (`nala_app`) |
  |---|---|---|
  | System | PostgreSQL | PostgreSQL |
  | Server | `postgres` | `postgres` |
  | Username | `nala_admin` | `nala_app` |
  | Password | `changeme_dev_only` | `app_dev_only` |
  | Database | `nala_operasional` | `nala_operasional` |

  Login dengan `nala_app` sekaligus jadi demonstrasi langsung dari batasan role itu sendiri (Bagian 3 Tahap A) — coba buka tabel `pengajuan_kredit`/`klaim_asuransi` lewat akun ini, harusnya **tidak muncul/tidak bisa diakses** karena role tersebut memang tidak pernah diberi `GRANT` ke tabel itu, cuma ke `audit_log`.

## 7. Checkpoint Praktik

Langkah eksekusi lengkap ada di **Langkah 17-21 `PANDUAN-PRAKTIK.md`**. Yang perlu dipastikan sebelum rangkaian Module 19-23 dianggap selesai:

- [ ] Role `staff_umum` **tidak berhasil** mendapatkan data operasional (jawaban JSON mentah atau pesan lain — bukan angka data sungguhan); pahami dari Bagian 4.a-b bahwa ini **tidak** otomatis tercatat di `audit_log` sebagai percobaan yang ditolak (`tool_dipanggil` tetap kosong) — ini gap nyata, bukan yang seharusnya diverifikasi "berhasil ditolak dengan rapi"
- [ ] Role `staff_finance`/`supervisor` berhasil memicu tool SQL, tercatat di `audit_log` dengan `tool_dipanggil='query_data_operasional'`, `akses_diizinkan=true`
- [ ] Pertanyaan tanpa tool (mis. sapaan) tetap tercatat satu baris di `audit_log`
- [ ] `audit_log` tidak bisa di-`DELETE`/`UPDATE` lewat role `nala_app` (diverifikasi lewat `psql -U nala_app`)
- [ ] Tool RAG (Module 20) tetap bisa diakses semua role tanpa pengecualian, termasuk `staff_umum`

## Kesimpulan Module 19-23: NALA Jadi Agentic

Module 19-23 mengubah NALA dari sistem yang selalu menjalankan urutan langkah tetap (RAG chain Module 7-18) menjadi agent yang **memutuskan sendiri** kapan mencari dokumen, kapan mengambil data operasional, kapan menolak karena tidak berwenang — dengan jejak audit atas setiap keputusan itu. Empat module saling membangun: Module 20 memberi fondasi graph + tool pertama (refactor RAG lama), Module 21 menambah tool kedua dengan disiplin keamanan berlapis (whitelist, parameterized query, role database read-only), Module 22 membuktikan graph yang sama menangani dua tool (termasuk kasus butuh keduanya) tanpa perubahan struktural, dan Module 23 menutup dengan RBAC + audit yang relevan langsung untuk konteks kepatuhan PT Nusantara Finance sebagai institusi finansial — **dengan catatan jujur (Bagian 4) bahwa barrier data terbukti aman lewat pengujian nyata, tapi audit trail-nya sendiri punya gap yang belum diperbaiki untuk kasus role tidak berwenang**.

Yang **belum** selesai secara jujur: autentikasi sungguhan (Bagian 1, Bagian 5), skala produksi untuk audit logging (Bagian 5), gap audit trail untuk percobaan akses ditolak (Bagian 4), dan kualitas routing yang bergantung pada model kecil (Module 22 Bagian 4) — semuanya bahan diskusi terbuka menuju Module 24-27, yang akan men-deploy seluruh stack ini (termasuk PostgreSQL dan service baru dari rangkaian Module 19-23 lainnya) sebagai satu sistem produksi dan mempersiapkan capstone.
