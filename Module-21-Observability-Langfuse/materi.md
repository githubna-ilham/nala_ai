# Module 21: Observability & Tracing dengan Langfuse

## Tujuan

Menambahkan Langfuse self-hosted untuk mencatat setiap request `/chat/stream` (satu-satunya endpoint chat NALA sejak Module 8) sebagai satu trace terstruktur (retrieval, rerank, generation), supaya jawaban NALA yang terlihat buruk bisa ditelusuri persis di tahap mana masalahnya muncul — visibilitas per-request yang nanti dilengkapi evaluasi batch di Module 22.

## Definisi

**Observability** adalah kemampuan memahami apa yang terjadi *di dalam* sistem hanya dari data yang direkam keluar darinya — bukan sekadar "apakah request berhasil", tapi "persis di tahap mana ia berhasil atau gagal". Begitu tiap request ke NALA melewati beberapa tahap berurutan (retrieval, rerank, generation), log teks biasa tidak lagi cukup: baris-barisnya tidak terstruktur per-request, jadi sulit direkonstruksi menjadi satu alur yang bisa dibaca ujung ke ujung. Di Langfuse, satu request itu dicatat sebagai satu **trace** — unit pencatatan paling luar yang menampung seluruh perjalanan satu pertanyaan user dari awal sampai jawaban jadi.

Di dalam satu trace, tiap tahap kerja dicatat sebagai **span** — potongan waktu dengan `input`/`output`/durasi sendiri, mewakili satu langkah non-LLM seperti `retrieval` (pencarian BM25 + vector) atau `rerank` (penyusunan ulang peringkat hasil). Kalau tahapnya justru pemanggilan LLM, dipakai jenis catatan khusus yaitu **generation** — varian span yang selain `input`/`output` juga merekam jumlah *token* dan model yang dipakai, karena inilah tahap yang biayanya (latency, token) paling relevan untuk diaudit. Span dan generation ini bersarang (*nested*) di dalam trace-nya — persis meniru urutan pemanggilan asli di kode — sehingga saat dibuka di UI Langfuse, satu trace terbaca sebagai pohon: tahap mana yang lambat, tahap mana yang inputnya sudah salah sejak awal, dan tahap mana yang menghasilkan output yang berhalusinasi.

Trace baru benar-benar lengkap kalau ditutup dengan **`flush()`** — memaksa data yang masih di buffer klien Langfuse terkirim ke server sebelum proses berakhir, supaya trace tidak hilang saat request selesai lebih cepat daripada background sender-nya sempat mengirim. Untuk endpoint streaming, penutupan ini tidak bisa dilakukan di badan fungsi endpoint (karena badan fungsi selesai duluan sebelum token terakhir terkirim ke user) — trace harus ditutup di dalam generator itu sendiri, setelah token terakhir benar-benar dikirim.

```mermaid
flowchart TD
    T["Trace: satu request"]
    T --> S1["Span: retrieval"]
    T --> S2["Span: rerank"]
    T --> G["Generation: llama3.2:3b<br/>(input/output/token)"]
```

## Hasil Akhir yang Diharapkan

- Service `langfuse-db` (Postgres khusus trace, terpisah dari Postgres data operasional Module 23) dan `langfuse` (v2, self-hosted) berjalan lewat Docker Compose, bisa diakses di `http://localhost:3000`
- `/chat/stream` menghasilkan satu trace per request dengan span `retrieval` dan `rerank` (dibuka/ditutup langsung di badan endpoint) plus `generation` (dibuka/ditutup lewat generator `traced_chat_stream()` **setelah** token terakhir, bukan di badan fungsi endpoint), dengan `try/finally` supaya tetap tercatat walau koneksi terputus
- Kita bisa membuka sebuah trace di UI Langfuse dan membaca `input`/`output` tiap span untuk mendiagnosis apakah masalah ada di retrieval, reranking, atau generation
- Trade-off dicatat jujur: overhead latensi tambahan, enam container berjalan bersamaan (beban RAM terbesar sepanjang Module 1-22), dan data trace berisi potongan dokumen internal (aman karena self-hosted, jadi perhatian kalau dipindah ke cloud)

## 1. Kenapa "Baca Log Container" Tidak Lagi Cukup

Di Module 1-17, kalau `/chat/stream` menjawab aneh, menelusurinya masih realistis lewat `docker compose logs api` — alurnya pendek: terima pesan, panggil Ollama, kembalikan jawaban. Setelah Module 18-21, alur `/chat/stream` sudah jauh lebih panjang dan setiap tahap bisa jadi sumber masalah:

```mermaid
flowchart LR
    A["Pesan user"] --> B["embed_text()"]
    B --> C["search_hybrid()<br/>BM25 + vector + RRF"]
    C --> D["reranker.rerank()<br/>cross-encoder top-20→3"]
    D --> E["Susun prompt + konteks"]
    E --> F["llama3.2:3b generate()"]
    F --> G["Jawaban ke user"]
```

Kalau seorang staff komplain "NALA jawab salah untuk pertanyaan X", pertanyaan diagnostiknya sekarang bercabang: apakah `search_hybrid()` gagal menemukan chunk yang benar? Apakah chunk yang benar ditemukan tapi `reranker.rerank()` malah menurunkan peringkatnya? Apakah konteks yang dikirim ke LLM sudah benar, tapi `llama3.2:3b` sendiri yang berhalusinasi mengabaikannya? Log teks biasa di `docker compose logs` tidak terstruktur untuk menjawab ini per-request — perlu menelusuri banyak baris log manual untuk merekonstruksi satu alur request.

**Observability** menyelesaikan ini dengan mencatat setiap tahap sebagai satu **trace** terstruktur per request — menjawab kasus "satu jawaban tertentu ini kenapa salah, tepatnya di mana". Ini berbeda dari (dan nanti dilengkapi oleh) evaluasi batch di Module 22, yang mengukur kualitas rata-rata di banyak pertanyaan sekaligus: observability melihat **satu request secara mendalam**, evaluasi melihat **banyak request secara agregat**.

## 2. Langfuse: Self-Hosted, Bukan SaaS

Langfuse adalah platform observability untuk aplikasi LLM — mencatat trace (input, output, latency, metadata) per request, bisa di-inspect lewat web UI. Konsisten dengan prinsip offline/private-first NALA, module ini men-*deploy* Langfuse **self-hosted** lewat Docker Compose, bukan memakai layanan cloud Langfuse — data trace (termasuk potongan dokumen SOP internal yang di-retrieve) tidak pernah keluar dari infrastruktur PT Nusantara Finance.

**Pilihan versi yang disengaja**: module ini memakai **Langfuse v2** (image `langfuse/langfuse:2`), bukan versi yang lebih baru. Langfuse v3+ butuh ClickHouse + Redis + object storage (S3-compatible) sebagai tambahan di atas Postgres — tiga service tambahan yang jauh melampaui anggaran RAM 16GB yang dijamin prasyarat pelatihan ini, ditambah stack yang sudah berat (Ollama + OpenSearch + Airflow + reranker + api). Langfuse v2 cukup dengan **satu** Postgres tambahan — jauh lebih realistis untuk laptop training. Konsekuensinya: kalau di masa depan NALA production di-upgrade ke versi lebih baru, akan ada pekerjaan migrasi tambahan (data trace tidak otomatis kompatibel antar major version) — trade-off yang diterima demi bisa dijalankan penuh di ruang pelatihan.

**Pola evolusi arsitektur self-hosting Langfuse** (garis besar konseptual — selalu cek dokumentasi resmi `https://langfuse.com/self-hosting` untuk versi eksak yang tersedia saat deployment sungguhan, karena proyek ini berkembang aktif):

| Versi | Arsitektur | Kompleksitas Self-Hosting |
|---|---|---|
| **v2** *(dipakai module ini)* | Aplikasi Next.js tunggal + **1 Postgres** — trace ditulis langsung ke Postgres, tanpa lapisan tambahan | Paling sederhana — 2 container (`langfuse` + `postgres`), cocok untuk skala kecil/training |
| **v3** | Memisahkan proses **ingestion** dari **aplikasi web** — menambahkan **ClickHouse** (database analitik kolumnar untuk query agregat cepat di volume trace besar) dan **object storage S3-compatible** (MinIO, untuk payload/blob besar), plus **Redis** sebagai antrian di depan proses ingestion | Jauh lebih kompleks — 4-5 service, tapi jauh lebih skalabel untuk volume trace besar |
| **v4** *(sempat direncanakan, akhirnya tidak dipakai)* | Melanjutkan arsitektur v3 — memisahkan `langfuse-web` (UI/API) dan `langfuse-worker` (proses ingestion async) jadi 2 image container terpisah, tetap dengan Postgres+ClickHouse+Redis+MinIO di belakangnya | Paling kompleks — 5+ service pendukung, didesain untuk beban produksi tinggi dengan worker yang bisa di-scale terpisah dari web UI |

Module ini sengaja pakai v2 (cukup untuk belajar konsep trace/span/generation tanpa membebani laptop training dengan service yang fungsinya — skalabilitas tinggi — belum relevan untuk puluhan trace). Draft awal kurikulum ini sempat merencanakan upgrade ke v4 di modul-modul akhir sebagai simulasi "production-grade". Setelah diuji nyata, rencana itu **dibatalkan** — untuk volume trace skala training (ratusan-ribuan baris, bukan jutaan), ClickHouse/Redis/MinIO menambah ~1,5-3GB RAM tanpa manfaat yang terasa. Keputusan finalnya: **tetap v2 sampai akhir kurikulum**. Tabel di atas tetap berguna sebagai peta arsitektur — supaya jelas apa yang sebenarnya dibayar kalau suatu saat beban trace memang menuntut v3/v4.

**Catatan kejujuran teknis**: seperti disebutkan di README pemetaan sumber materi, detail *environment variable* dan bentuk API SDK Langfuse bisa sedikit berbeda tergantung versi patch yang tersedia saat pelatihan berjalan — bagian docker-compose dan kode di bawah menunjukkan **bentuk dan pola yang benar secara konsep** (trace → span → generation → flush), tapi selalu cek dokumentasi resmi self-hosting Langfuses (`https://langfuse.com/self-hosting`) untuk nama env var/parameter persis yang berlaku di versi yang benar-benar terpasang saat pelatihan.

## 3. Postgres Langfuse ≠ Postgres Module 23

Penting untuk tidak tertukar: Postgres yang ditambahkan module ini (`langfuse-db`) **khusus untuk menyimpan data trace Langfuse** — bukan Postgres yang akan diperkenalkan Module 23 untuk data operasional (pengajuan kredit, klaim, dst, dipakai agent tool query SQL). Keduanya berdiri sendiri, database terpisah, tujuan berbeda. Module 23 akan menambah service Postgres-nya sendiri (`postgres` atau nama serupa) — jangan menyatukan keduanya walau sama-sama "Postgres".

## 4. Struktur Kode yang Ditambahkan

Dua Tahap: **Tahap A** menambah service `langfuse-db` + `langfuse` di `docker-compose.yml` dan setup akun. **Tahap B** instrumentasi `/chat/stream` (satu-satunya endpoint chat NALA) — span `retrieval`/`rerank` dibuka/ditutup langsung di badan endpoint, tapi `generation` untuk pemanggilan LLM harus ditutup **di dalam generator**, setelah token terakhir, bukan di badan fungsi endpoint, karena endpoint ini streaming.

**Prasyarat sebelum mulai:**
- Sudah menyelesaikan **Module 20** — `Nala/` sudah punya hybrid search (Module 18-19) dan reranking cross-encoder bekerja di `/chat/stream`.
- Docker Desktop dinaikkan lagi alokasi RAM-nya untuk menampung dua service baru:

| Setting | Minimal | Direkomendasikan | Alasan |
|---|---|---|---|
| **Memory (RAM)** | 16 GB | 20 GB+ jika tersedia | Semua service sebelumnya (Ollama, OpenSearch, Airflow, api dengan reranker) + Langfuse & Postgres-nya (`langfuse-db`, terpisah dari Postgres data operasional yang baru akan muncul di Module 23) berjalan bersamaan di titik puncak. |
| **Disk image size** | 100 GB | 120 GB+ | Image `langfuse/langfuse` menambah beberapa GB lagi di atas image sebelumnya. |

Kalau laptop mulai terasa berat, pertimbangkan mematikan sementara `airflow` (tidak dipakai lagi setelah ingest awal selesai — lihat Bagian 6).

### Tahap A — Tambah Service Langfuse di `docker-compose.yml`

**Langkah 1 — Tambah `langfuse-db` dan `langfuse`**

```yaml
# docker-compose.yml
services:
  # ...service ollama, opensearch, airflow, api yang sudah ada...

  langfuse-db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=langfuse
      - POSTGRES_PASSWORD=langfuse
      - POSTGRES_DB=langfuse
    volumes:
      - langfuse_db_data:/var/lib/postgresql/data

  langfuse:
    image: langfuse/langfuse:2
    environment:
      - DATABASE_URL=postgresql://langfuse:langfuse@langfuse-db:5432/langfuse
      - NEXTAUTH_URL=http://localhost:3000
      - NEXTAUTH_SECRET=ganti-dengan-random-string-yang-panjang
      - SALT=ganti-dengan-random-string-lain-yang-panjang
    ports:
      - "3000:3000"
    depends_on:
      - langfuse-db

volumes:
  # ...ollama_data, opensearch_data, hf_cache yang sudah ada...
  langfuse_db_data:
```

- **`NEXTAUTH_SECRET` dan `SALT`**: Langfuse (dibangun di atas Next.js) memakai keduanya untuk keamanan sesi login dan enkripsi — untuk lingkungan pelatihan lokal, string acak apa pun yang cukup panjang sudah memadai (bukan dipakai untuk deployment produksi sungguhan yang terekspos ke internet). **Ganti nilai placeholder ini** sebelum menjalankan — jangan disalin apa adanya.
- **Port `3000`**: web UI Langfuse — beda dari `8000` (NALA API), `8080` (Airflow), `9200` (OpenSearch), `11434` (Ollama) yang sudah dipakai sejak modul-modul sebelumnya.

<details>
<summary><strong>Pakai Claude Code? Salin prompt berikut, paste untuk eksekusi Langkah 1</strong></summary>

```
Tambah service langfuse-db dan langfuse di docker-compose.yml (Module
22, Tahap A, Langkah 1) — belum ada instrumentasi kode Python.

GOAL:
- Di Nala/docker-compose.yml, tambah dua
  service baru:
  1. langfuse-db: image postgres:15-alpine, environment
     POSTGRES_USER=langfuse, POSTGRES_PASSWORD=langfuse,
     POSTGRES_DB=langfuse, volume langfuse_db_data:/var/lib/postgresql/data.
  2. langfuse: image langfuse/langfuse:2, environment DATABASE_URL
     (postgresql ke langfuse-db), NEXTAUTH_URL=http://localhost:3000,
     NEXTAUTH_SECRET dan SALT (placeholder string, beri komentar untuk
     diganti), port "3000:3000", depends_on langfuse-db.
- Tambah langfuse_db_data ke daftar top-level volumes.

CONTEXT:
- Ini Langfuse v2 (bukan v3) — sengaja dipilih karena v3 butuh
  ClickHouse+Redis+object storage, terlalu berat untuk laptop 16GB
  yang sudah menjalankan Ollama+OpenSearch+Airflow+reranker.
- langfuse-db TERPISAH dari Postgres data operasional yang akan
  ditambahkan Module 23 — jangan digabung.

GUARDRAIL:
- JANGAN ubah service ollama, opensearch, airflow, api yang sudah
  ada — tambahan API key untuk service api itu Langkah 2, bukan di
  sini.
- JANGAN hardcode NEXTAUTH_SECRET/SALT dengan nilai yang terlihat
  seperti secret produktif sungguhan — pakai placeholder yang jelas
  harus diganti.
```

</details>

**Langkah 2 — Nyalakan, buat akun, dan ambil API key**

```bash
docker compose up -d --build langfuse-db langfuse
```

**Proses ini akan terasa lama** — Langfuse perlu migrasi skema database saat pertama kali jalan. Pantau progresnya:

```bash
docker compose logs -f langfuse
```

Tunggu sampai log menunjukkan service siap menerima koneksi, lalu `Ctrl+C` untuk keluar dari `logs -f`, baru buka `http://localhost:3000` — buat akun lokal (email+password apa saja, tidak terkirim ke mana pun karena self-hosted).

Setelah sign up/sign in, Langfuse v2 **tidak langsung** menampilkan form buat Project — ada wizard setup 4 langkah yang mudah terlewat kalau tidak diberi tahu dulu, dimulai dari halaman "Home":

![Halaman Home Langfuse meminta Organization dibuat lebih dulu sebelum Project](../resources/images/langfuse-setup/langfuse-home-get-started.png)

Klik **"+ New Organization"** — ini membuka wizard **Setup** dengan 4 langkah eksplisit (terlihat sebagai breadcrumb di bagian atas): **1. Create Organization → 2. Invite Members → 3. Create Project → 4. Setup Tracing**.

**Langkah wizard 1 — Create Organization**: isi nama bebas (misal "PT Nusantara Finance" — satu akun bisa menaungi beberapa organization, tiap organization menaungi beberapa Project), klik **Create**:

![Form Create Organization dengan input nama organization](../resources/images/langfuse-setup/langfuse-create-organization.png)

**Langkah wizard 2 — Invite Members**: langsung menampilkan tabel **Organization Members** dengan akun Anda sendiri sebagai **Owner** — untuk pelatihan solo, **tidak perlu** mengundang siapa pun di sini, langsung klik **Next** untuk lanjut:

![Halaman Invite Members menampilkan Organization Members dengan role Owner](../resources/images/langfuse-setup/langfuse-invite-members.png)

**Langkah wizard 3 — Create Project**: buat satu **Project** baru (misalnya "NALA") di dalam organization yang baru dibuat, klik **Create**:

![Form Create Project dengan input nama project](../resources/images/langfuse-setup/langfuse-create-project.png)

**Langkah wizard 4 — Setup Tracing**: setelah Project terbentuk, ambil API key-nya lewat menu **Settings → API Keys** di sidebar project (halaman **Project Settings**, bagian **General**, punya beberapa tab termasuk **API Keys**):

Klik **"+ Create new API key"** — modal berikut muncul menampilkan **Secret Key** dan **Public Key** sekaligus:

![Modal API Keys menampilkan Secret Key dan Public Key](../resources/images/langfuse-setup/langfuse-api-keys.png)

Salin keduanya sekarang — **Secret Key cuma ditampilkan sekali** di modal ini, simpan baik-baik sebelum menutupnya (kalau lupa, buat key baru — tidak bisa melihat ulang Secret Key yang lama).

Simpan keduanya sebagai environment variable baru untuk service `api` di `docker-compose.yml`:

```yaml
# docker-compose.yml, service api
environment:
  # ...environment yang sudah ada...
  - LANGFUSE_PUBLIC_KEY=pk-lf-xxxxxxxx
  - LANGFUSE_SECRET_KEY=sk-lf-xxxxxxxx
  - LANGFUSE_HOST=http://langfuse:3000
```

⚠️ Ini contoh paling sederhana untuk lingkungan pelatihan (key ditulis langsung di `docker-compose.yml`). Untuk deployment sungguhan, key sensitif seperti ini semestinya disimpan di file `.env` yang **tidak** dikomit ke git — dicatat di sini sebagai pengingat, bukan diterapkan penuh di module ini supaya tetap fokus pada instrumentasi.

Restart service `api` supaya environment variable barunya terbaca:

```bash
docker compose up --build -d api
```

**▶️ Jalankan & lihat hasilnya**

```bash
curl http://localhost:3000/api/public/health
```

✅ **Indikator sukses**: `docker compose ps` menunjukkan `langfuse-db` dan `langfuse` berstatus `running`/`healthy`, halaman `http://localhost:3000` bisa diakses dan login berhasil, Project dan API key sudah dibuat.

<details>
<summary><strong>Pakai Claude Code? Salin prompt berikut, paste untuk eksekusi Langkah 2</strong></summary>

```
Tambah environment variable Langfuse (placeholder) ke service api di
docker-compose.yml (Module 21, Tahap A, Langkah 2) — nilai key asli
didapat manual dari UI Langfuse setelah Project & API key dibuat.

GOAL:
- Di Nala/docker-compose.yml, service `api`: tambah tiga environment
  variable baru di bagian environment yang sudah ada:
  - LANGFUSE_PUBLIC_KEY=pk-lf-xxxxxxxx
  - LANGFUSE_SECRET_KEY=sk-lf-xxxxxxxx
  - LANGFUSE_HOST=http://langfuse:3000

CONTEXT:
- pk-lf-xxxxxxxx dan sk-lf-xxxxxxxx adalah PLACEHOLDER — nilai asli
  didapat manual dari halaman Settings > API Keys project Langfuse
  (langkah UI, tidak bisa diotomasi lewat Claude Code), lalu user
  menggantinya sendiri setelah prompt ini dijalankan.
- LANGFUSE_HOST memakai nama service Docker Compose `langfuse`
  (bukan localhost) karena service api memanggilnya dari dalam
  jaringan Docker yang sama.

GUARDRAIL:
- JANGAN mengarang nilai key yang terlihat seperti key produktif
  sungguhan — pakai placeholder yang jelas (pk-lf-xxxxxxxx/
  sk-lf-xxxxxxxx) supaya user tahu harus menggantinya.
- JANGAN ubah service langfuse-db atau langfuse (Tahap A, Langkah 1)
  di langkah ini.
```

</details>

### Tahap B — Instrumentasi `/chat/stream`

**Langkah 3 — Tambah dependency dan setup client Langfuse**

```
langfuse>=2.0,<3.0
```

Tambahkan ke `requirements.txt`. Lalu di `app/main.py`:

```python
# app/main.py — tambahan import
from langfuse import Langfuse

# app/main.py — tambahan dekat instance ollama_client/vector_store yang sudah ada
langfuse_client = Langfuse(
    public_key=os.environ.get("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.environ.get("LANGFUSE_SECRET_KEY"),
    host=os.environ.get("LANGFUSE_HOST", "http://localhost:3000"),
)
```

`langfuse_client` dibuat sekali sebagai instance modul-level — pola yang sama seperti `ollama_client`, `vector_store`, dan `reranker` di module-module sebelumnya.

<details>
<summary><strong>Pakai Claude Code? Salin prompt berikut, paste untuk eksekusi Langkah 3</strong></summary>

```
Tambah dependency Langfuse dan setup client Langfuse SDK di
app/main.py (Module 21, Tahap B, Langkah 3) — belum instrumentasi
endpoint /chat/stream.

GOAL:
- Di Nala/requirements.txt: tambah baris
  langfuse>=2.0,<3.0.
- Di Nala/app/main.py:
  - Tambah `from langfuse import Langfuse`.
  - Tambah instance modul-level langfuse_client = Langfuse(public_key=
    os.environ.get("LANGFUSE_PUBLIC_KEY"), secret_key=os.environ.get(
    "LANGFUSE_SECRET_KEY"), host=os.environ.get("LANGFUSE_HOST",
    "http://localhost:3000")) — ditaruh dekat instance ollama_client/
    vector_store/reranker yang sudah ada, pola modul-level yang sama.

CONTEXT:
- LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST sudah
  di-set di environment docker-compose.yml service api (Tahap A,
  Langkah 2) — kode ini hanya membacanya lewat os.environ.get().
- Ini baru setup client, BELUM instrumentasi trace/span/generation di
  /chat/stream — itu Langkah 4 terpisah.

GUARDRAIL:
- JANGAN ubah endpoint /chat/stream atau logika bisnisnya di langkah
  ini — hanya tambah dependency dan instance client.
- JANGAN hardcode API key — selalu baca dari environment variable.
```

</details>

**Langkah 4 — Bungkus retrieval, reranking, dan generation dengan span/generation, ditutup di dalam generator**

`/chat/stream` (satu-satunya endpoint chat NALA sejak Module 8) mengembalikan `StreamingResponse(ollama_client.chat_stream(...), ...)` — **generator** yang dipasangkan sebagai body response. Ini penting dipahami dulu sebelum menulis instrumentasinya: begitu fungsi `chat_stream()` mengeksekusi baris `return StreamingResponse(...)`, fungsi itu **langsung selesai (return)** — isi generator (`ollama_client.chat_stream(...)`) baru benar-benar berjalan **setelah** itu, token demi token, saat FastAPI/Starlette menariknya untuk dikirim ke browser.

**Konsekuensinya**: kode instrumentasi yang ditulis persis setelah `return StreamingResponse(...)` di badan fungsi `chat_stream()` **tidak akan pernah tereksekusi pada waktu yang tepat** — fungsi sudah `return` duluan. Trace tidak bisa ditutup (`trace.update(output=...)`, `langfuse_client.flush()`) di badan fungsi endpoint — ia harus ditutup **di dalam generator itu sendiri**, tepat setelah token terakhir selesai di-`yield`. Span untuk tahap yang bukan pemanggilan LLM (`retrieval`, `rerank`) tidak kena masalah ini — keduanya selesai penuh **sebelum** token pertama dikirim, jadi tetap bisa dibuka/ditutup langsung di badan `chat_stream()`; hanya `generation` (pemanggilan LLM) yang harus dibungkus generator terpisah.

```mermaid
sequenceDiagram
    participant F as chat_stream()
    participant G as Generator (traced_stream)
    participant B as Browser

    F->>F: trace = langfuse_client.trace(...)
    F->>F: buat generator traced_stream() (BELUM jalan)
    F->>B: return StreamingResponse(traced_stream(), ...)
    Note over F: Fungsi chat_stream() SELESAI di sini
    loop token demi token
        G->>G: token = next(ollama_client.chat_stream(...))
        G->>B: yield token
    end
    G->>G: accumulated selesai — trace.update() + flush() DI SINI
```

```python
# app/main.py
def traced_chat_stream(trace, ollama_messages: list[dict]):
    generation = trace.generation(
        name="llm_generate_stream",
        model=os.environ.get("OLLAMA_MODEL", "llama3.2:3b"),
        input=ollama_messages,
    )
    accumulated = ""
    try:
        for token in ollama_client.chat_stream(ollama_messages):
            accumulated += token
            yield token
    finally:
        generation.end(output=accumulated)
        trace.update(output={"reply": accumulated})
        langfuse_client.flush()


@app.post("/chat/stream")
def chat_stream(request: ChatStreamRequest) -> StreamingResponse:
    if not request.messages or request.messages[-1].role != "user":
        raise HTTPException(
            status_code=400,
            detail="messages harus non-kosong dan elemen terakhir harus role 'user'",
        )

    recent = request.messages[-HISTORY_WINDOW:]
    last_user_message = recent[-1].content

    trace = langfuse_client.trace(name="chat_stream", input={"message": last_user_message})

    if request.use_rag:
        try:
            do_rerank = request.use_reranking and reranker is not None
            pool_size = 20 if do_rerank else (3 if request.search_method == "hybrid" else 6)

            retrieval_span = trace.span(
                name="retrieval",
                input={"query": last_user_message, "method": request.search_method},
            )
            if request.search_method == "bm25":
                candidates = vector_store.search_bm25(last_user_message, top_k=pool_size)
            elif request.search_method == "hybrid":
                query_embedding = embed_text(last_user_message, base_url=OLLAMA_BASE_URL)
                candidates = vector_store.search_hybrid(
                    query_text=last_user_message,
                    query_embedding=query_embedding,
                    top_k=pool_size,
                )
            else:
                query_embedding = embed_text(last_user_message, base_url=OLLAMA_BASE_URL)
                candidates = vector_store.search(query_embedding, top_k=pool_size)
            retrieval_span.end(output={"candidate_count": len(candidates)})

            if do_rerank:
                rerank_span = trace.span(name="rerank", input={"candidate_count": len(candidates)})
                results = reranker.rerank(last_user_message, candidates, top_k=3)
                rerank_span.end(output={"top_chunks": [r["text"][:100] for r in results]})
            else:
                results = candidates
        except httpx.HTTPError as exc:
            results = []
            trace.update(output={"error": f"retrieval_failed: {exc}"}, level="ERROR")
    else:
        results = []

    if request.use_rag and results:
        context = "\n\n".join(
            f"[{r['metadata']['source']}]\n{r['text']}" for r in results
        )
        system_prompt = NALA_SYSTEM_PROMPT
        grounded_content = f"Konteks:\n{context}\n\nPertanyaan: {last_user_message}"
    elif request.use_rag:
        system_prompt = NALA_SYSTEM_PROMPT_NO_CONTEXT
        grounded_content = last_user_message
    else:
        system_prompt = NALA_SYSTEM_PROMPT_RAG_OFF
        grounded_content = last_user_message

    ollama_messages = [{"role": "system", "content": system_prompt}]
    ollama_messages += [{"role": m.role, "content": m.content} for m in recent[:-1]]
    ollama_messages.append({"role": "user", "content": grounded_content})

    return StreamingResponse(
        traced_chat_stream(trace, ollama_messages), media_type="text/plain"
    )
```

- **`trace = langfuse_client.trace(...)`**: dibuat di **awal** `chat_stream()` (setelah validasi 400) — satu trace mewakili **satu request** secara utuh.
- **`trace.span(...)`**: dipakai untuk tahap yang bukan pemanggilan LLM langsung — `retrieval` dan `rerank` masing-masing jadi satu span bersarang di dalam trace, dengan `input`/`output` ringkas (bukan seluruh isi chunk, cukup jumlah dan cuplikan — trace yang terlalu besar memperlambat UI Langfuse saat dibuka).
- **`trace.generation(...)`**: khusus untuk pemanggilan model bahasa — Langfuse membedakan `generation` dari `span` biasa karena `generation` punya field khusus terkait LLM (`model`, token usage kalau tersedia) yang ditampilkan berbeda di UI. Dibuat **di dalam** `traced_chat_stream()`, bukan di `chat_stream()`, karena alasan di atas.
- **`traced_chat_stream()`** adalah generator **baru** yang membungkus `ollama_client.chat_stream()` yang sudah ada sejak Module 8 — bukan menggantikannya. Ia meneruskan (`yield token`) setiap token persis seperti aslinya, sambil diam-diam mengumpulkannya ke `accumulated`.
- **`try/finally`**: memastikan `generation.end()`, `trace.update()`, dan `flush()` tetap terpanggil bahkan kalau streaming terputus di tengah jalan (misalnya koneksi browser terputus) — `finally` selalu jalan baik generator sampai habis normal maupun berhenti karena exception/`GeneratorExit`.
- **`retrieval_span`/`rerank_span`** tetap dibuat dan ditutup langsung di badan `chat_stream()` — bagian ini **bukan** bagian yang streaming (retrieval dan reranking selesai penuh sebelum token pertama dikirim), jadi tidak kena masalah generator yang sama seperti bagian generation.
- **`langfuse_client.flush()`**: Langfuse SDK mengirim trace secara **asinkron** dan di-*buffer* secara default — `flush()` memaksa semua trace yang tertunda benar-benar terkirim ke server Langfuse sebelum generator selesai. Tanpa `flush()` eksplisit, ada risiko trace terakhir sebuah request hilang kalau proses `api` berhenti sebelum buffer sempat terkirim otomatis.
- `trace` dibuat sekali di `chat_stream()`, lalu **dioper sebagai parameter** ke `traced_chat_stream()` — trace yang sama dipakai untuk mencatat span retrieval/rerank (selesai sebelum streaming) maupun generation (selesai setelah streaming), semuanya tetap tergabung dalam satu trace per request.

**▶️ Jalankan & lihat hasilnya**

```bash
docker compose up --build api
```

```bash
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Apa saja syarat pengajuan kredit untuk nasabah perorangan?"}]}'
```

✅ **Indikator sukses**: streaming tetap berjalan token demi token seperti Module 8 (tidak ada perubahan perilaku dari sisi user), dan trace baru untuk `chat_stream` muncul di `http://localhost:3000` (halaman **Traces** project Anda) **setelah** curl selesai menerima seluruh stream (bukan langsung saat request dikirim) — bukti `flush()` di dalam generator benar-benar menunggu token terakhir, bukan terpanggil prematur. Klik trace tersebut untuk melihat span `retrieval`, `rerank`, dan generation `llm_generate_stream` tersusun bersarang dengan waktu eksekusi masing-masing.

**Uji juga alur fallback tetap tercatat saat OpenSearch mati** (mensimulasikan kegagalan):

```bash
docker compose stop opensearch
```

```bash
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Apa saja syarat pengajuan kredit?"}]}'
```

✅ **Indikator sukses**: `/chat/stream` tetap membalas (fallback `NALA_SYSTEM_PROMPT_NO_CONTEXT`, jawaban generik) — bukan error 500 — dan trace baru tetap muncul di Langfuse, dengan `level="ERROR"` tercatat di trace tersebut (Bagian 5d). Nyalakan lagi OpenSearch setelahnya:

```bash
docker compose start opensearch
```

<details>
<summary><strong>Pakai Claude Code? Salin prompt berikut, paste untuk eksekusi Langkah 4</strong></summary>

```
Instrumentasi /chat/stream dengan Langfuse trace/span/generation —
trace ditutup DI DALAM generator, bukan di badan fungsi endpoint
(Module 21, Tahap B, Langkah 4).

GOAL:
- Di Nala/app/main.py:
  - Tambah fungsi generator baru traced_chat_stream(trace,
    ollama_messages: list[dict]): buat generation =
    trace.generation(name="llm_generate_stream", model=...,
    input=ollama_messages); accumulated = ""; try: for token in
    ollama_client.chat_stream(ollama_messages): accumulated += token;
    yield token — finally: generation.end(output=accumulated);
    trace.update(output={"reply": accumulated});
    langfuse_client.flush().
  - Di dalam chat_stream() (satu-satunya endpoint chat NALA): buat
    trace = langfuse_client.trace(name="chat_stream",
    input={"message": last_user_message}) setelah validasi 400.
    Bungkus pemanggilan search_hybrid() dengan trace.span(
    name="retrieval", ...) lalu .end(output=...), dan
    reranker.rerank() dengan trace.span(name="rerank", ...) lalu
    .end(output=...) — keduanya dibuka/ditutup langsung di badan
    chat_stream(), karena selesai sebelum streaming dimulai. Ganti
    baris terakhir `return StreamingResponse(
    ollama_client.chat_stream(ollama_messages), media_type="text/plain")`
    jadi `return StreamingResponse(traced_chat_stream(trace,
    ollama_messages), media_type="text/plain")`.

CONTEXT:
- StreamingResponse membuat fungsi endpoint return SEBELUM generator
  benar-benar dieksekusi, jadi trace.update()/flush() TIDAK BISA
  ditaruh di badan chat_stream() setelah baris return — harus di
  dalam generator terpisah (traced_chat_stream) yang dipanggil
  setelah token terakhir.
- ollama_client.chat_stream() yang sudah ada TIDAK diubah — dibungkus,
  bukan diganti isinya.
- Alur retrieval-rerank-generate di chat_stream() sudah lengkap dari
  Module 18-20 — module ini HANYA menambah instrumentasi observability
  di sekitarnya, tidak mengubah logika bisnisnya.
- langfuse_client sudah dibuat sebagai instance modul-level di Langkah
  3 — pakai langsung, jangan buat instance baru.

GUARDRAIL:
- WAJIB pakai try/finally di traced_chat_stream() supaya trace tetap
  ditutup walau streaming terputus di tengah jalan.
- JANGAN ubah validasi 400 atau logika windowing (HISTORY_WINDOW) yang
  sudah ada.
- JANGAN ubah logika bisnis chat_stream() (retrieval, reranking,
  fallback, isi prompt) — hanya tambah pembungkus
  trace/span/generation di sekitarnya.
```

</details>

**📄 Kode lengkap** (bagian relevan `app/main.py` setelah Module 21 — lihat Bagian 4 Tahap B untuk fungsi `traced_chat_stream()` dan `chat_stream()` secara utuh; setup `langfuse_client` di Bagian 4 Tahap B Langkah 3).

### Troubleshooting

- **`langfuse` container gagal start / `langfuse-db` connection refused**: `langfuse` butuh `langfuse-db` sudah siap menerima koneksi sebelum migrasi database berhasil — tunggu beberapa saat lebih lama, atau restart `langfuse` saja setelah `langfuse-db` benar-benar `healthy`: `docker compose restart langfuse`.
- **Trace tidak muncul sama sekali di UI Langfuse**: cek `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY`/`LANGFUSE_HOST` di environment service `api` — key yang salah biasanya gagal secara diam-diam (SDK Langfuse dirancang tidak mengganggu aplikasi utama kalau pengiriman trace gagal). Cek juga apakah `langfuse_client.flush()` benar-benar terpanggil di dalam `traced_chat_stream()` (Tahap B Langkah 4).
- **Trace `chat_stream` tidak pernah muncul, walau curl berhasil menerima seluruh stream**: kemungkinan besar instrumentasi masih ditulis di badan fungsi `chat_stream()` setelah baris `return StreamingResponse(...)` (baris itu tidak akan pernah tereksekusi tepat waktu) — pastikan `trace.update()`/`flush()` ada di dalam `traced_chat_stream()` (generator terpisah), bukan di `chat_stream()` sendiri. Lihat penjelasan lengkap di Tahap B Langkah 4 di atas.
- **Semua service terasa sangat lambat / laptop panas / container ter-*kill***: alokasi RAM Docker Desktop kurang — lihat bagian Prasyarat di awal Bagian 4, naikkan ke 20GB+ kalau tersedia, atau matikan sementara `airflow` (lihat Bagian 6) selama eksplorasi berlangsung.
- **Port sudah dipakai (3000/8000/9200/11434)**: ubah mapping port yang bentrok di `docker-compose.yml`, atau pastikan container lama sudah benar-benar dimatikan (`docker compose down` di `Nala`).

## 5. Menelusuri Jawaban Buruk Lewat UI Langfuse

### a. Navigasi Dasar

Setelah login ke `http://localhost:3000`, sidebar kiri punya beberapa menu utama: **Dashboard** (ringkasan statistik — jumlah trace, latency rata-rata), **Tracing** (daftar semua trace — ini yang paling sering dipakai), lalu **Users**, **Prompts**, **Datasets**, **Scores/Evaluation** (fitur lanjutan, belum dipakai di module ini).

### b. Melihat Daftar Trace

Klik **Tracing** di sidebar → tabel berisi semua trace, terurut dari yang **terbaru di atas**, dengan kolom `Name` (`chat` atau `chat_stream`, sesuai nama yang di-set di kode), `Timestamp`, `Latency`, dan cuplikan `Input`/`Output`. Bisa **search/filter** — misal cari trace yang `input`-nya mengandung kata tertentu, berguna kalau staff komplain soal pertanyaan spesifik dan Anda perlu menemukan trace-nya di antara banyak trace lain.

### c. Membaca Struktur Satu Trace

Klik salah satu baris trace untuk membuka detail — strukturnya **bersarang (nested)**, terlihat sebagai pohon:

```
chat_stream (trace)
├── retrieval (span)
├── rerank (span)
└── llm_generate_stream (generation)
```

Alur debugging sebuah jawaban yang terasa buruk (misalnya staff komplain jawaban tidak akurat):

1. Buka `http://localhost:3000`, masuk ke halaman **Tracing**, cari trace yang sesuai (bisa difilter berdasarkan waktu, atau cari `input` yang mengandung pertanyaan yang dikomplain).
2. Buka trace tersebut — klik node trace paling atas, lihat `Input` (pertanyaan user) dan `Output` (jawaban final) di panel kanan. Perhatikan **urutan span**: `retrieval` → `rerank` → `llm_generate`/`llm_generate_stream`.
3. Klik span `retrieval`: lihat `output.candidate_count` — kalau nol atau sangat kecil, kemungkinan besar masalahnya di retrieval (index kosong, atau dokumen yang relevan memang belum ter-*ingest*), bukan di LLM.
4. Klik span `rerank`: lihat `output.top_chunks` — apakah cuplikan chunk yang dipilih **benar-benar** relevan dengan pertanyaan? Kalau kandidat di `retrieval` sudah benar tapi `rerank` menaruh chunk yang salah di posisi teratas, itu petunjuk model reranker perlu ditinjau (atau `RERANK_ENABLED=false` sementara sebagai pembanding).
5. Klik span `llm_generate`/`llm_generate_stream`: baca `input` (prompt lengkap yang dikirim ke `llama3.2:3b`, termasuk konteks yang disusun) dan `output` (jawaban model). Kalau konteks di `input` sudah benar tapi `output` tetap salah/mengarang, itu petunjuk masalahnya ada di generation — grounding di system prompt (Module 14 Bagian 4) mungkin perlu diperkuat, atau modelnya memang mengabaikan instruksi untuk kasus tertentu.
6. Perhatikan **durasi tiap span** (ditampilkan di UI sebagai badge kecil di samping tiap node, atau saat hover) — kalau `rerank` memakan waktu jauh lebih lama dari yang diharapkan, itu petunjuk nyata untuk pertimbangan trade-off di Module 20 Bagian 6 (`RERANK_ENABLED=false` sebagai katup pengaman). Di sistem ini, generation (LLM) biasanya paling dominan durasinya dibanding kedua span retrieval.

Alur ini yang membedakan observability dari sekadar membaca log: setiap tahap punya **input dan output yang tercatat terpisah**, jadi diagnosis "di tahap mana masalahnya muncul" tidak perlu menebak-nebak dari baris log yang bercampur.

### d. Trace yang Error

Trace dengan `level="ERROR"` (hasil `trace.update(output={"error": ...}, level="ERROR")` di Bagian 4 Tahap B Langkah 4, dipicu misalnya saat OpenSearch tidak terjangkau) biasanya ditandai dengan warna/badge berbeda di daftar **Tracing** — klik untuk lihat pesan error-nya di `Output`. Ini memastikan kegagalan terkontrol (fallback ke jawaban generik, bukan crash 500) tetap **tercatat dan bisa ditelusuri**, bukan diam-diam hilang begitu saja.

### e. Catatan: Kolom "Scores" Masih Kosong

Tiap trace juga punya field `scores` (terlihat kosong `[]` kalau dicek lewat API `GET /api/public/traces`, atau tab **Scores** di UI) — ini **normal** untuk module ini, bukan bug. "Scores" di Langfuse adalah fitur terpisah untuk melekatkan penilaian kualitas ke sebuah trace (dari manusia lewat UI, atau dari kode). Module 21 ini cuma fokus mencatat **apa yang terjadi** (trace/span/generation), belum menilai **seberapa bagus** hasilnya.

Koneksi yang belum bisa dimanfaatkan di sini: Module 22 nanti membangun `judge_answer()` (`app/llm_judge.py`) yang menghasilkan skor `faithfulness`/`relevance` — secara konsep persis jenis data yang cocok dikirim lewat `trace.score(name=..., value=..., comment=...)`, supaya skor itu langsung terlihat melekat di tiap trace UI, bukan cuma di output terpisah `run_evaluation.py`. Di titik ini fungsinya memang belum ada; dicatat di sini sebagai perluasan alami yang masuk akal begitu Module 22 selesai.

## 6. Trade-off Observability: Overhead yang Tidak Gratis

**Yang didapat:**
- Debugging jawaban buruk jadi jauh lebih cepat — tidak perlu mereproduksi ulang masalah sambil membaca log manual, cukup buka trace yang sudah tersimpan.
- Visibilitas latensi per tahap (retrieval vs rerank vs generation) — data konkret untuk memutuskan optimisasi mana yang paling berdampak, bukan tebakan.
- Riwayat trace historis jadi bahan mentah untuk test set evaluasi yang dibangun Module 22 — pertanyaan nyata dari staff yang jawabannya buruk bisa langsung dijadikan entri di `QA_TESTSET`, bukan mengarang pertanyaan uji dari nol.

**Yang dibayar:**
- **Latensi tambahan per request** — setiap `trace.span()`/`.generation()` dan `flush()` adalah kerja tambahan (walau SDK Langfuse mem-buffer dan mengirim secara batch di background, `flush()` eksplisit di akhir `traced_chat_stream()` menunggu pengiriman selesai). Untuk `/chat/stream`, ini terjadi **setelah** token terakhir dikirim ke user, jadi user tidak merasakan langsung — tapi tetap menahan koneksi/proses sedikit lebih lama di sisi server.
- **Dua service tambahan** (`langfuse`, `langfuse-db`) menambah beban RAM di atas stack yang sudah berat sejak Module 20 (reranker). Ini kemungkinan besar titik dengan jumlah service **terbanyak** sepanjang Module 1-22: `ollama`, `opensearch`, `airflow`, `api` (dengan reranker), `langfuse`, `langfuse-db` — enam container berjalan bersamaan. Kalau laptop mulai terasa berat, pertimbangkan mematikan sementara `airflow`: DAG-nya cuma dipicu manual (lihat Module 17 Bagian 6, "Cara Trigger DAG Manual") dan tidak dipakai lagi setelah ingest dokumen awal selesai, jadi mematikannya sementara selama eksplorasi Langfuse tidak mengganggu `/chat/stream`, yang tidak bergantung pada Airflow sama sekali:

  ```bash
  docker compose stop airflow
  ```

  Nyalakan lagi kapan pun dibutuhkan (misalnya untuk ingest dokumen baru):

  ```bash
  docker compose up -d airflow
  ```
- **Data trace berisi potongan dokumen internal** (chunk SOP yang di-retrieve, muncul di `output` span `retrieval`/`rerank`) — karena Langfuse dijalankan self-hosted (Bagian 2), ini tidak masalah untuk skenario pelatihan/privasi data. Kalau suatu saat Langfuse dipindah ke layanan cloud (bukan self-hosted), ini jadi pertimbangan privasi data yang serius dan tidak boleh dilakukan tanpa tinjauan keamanan — dicatat di sini sebagai pengingat prinsip, bukan skenario yang direncanakan.

## 7. Checkpoint Praktik

Langkah eksekusi lengkap ada di Bagian 4 (Struktur Kode yang Ditambahkan) di atas, Langkah 1-4. Yang perlu dipastikan sebelum Module 18-22 dianggap selesai:

- [ ] `http://localhost:3000` bisa diakses, akun dan Project sudah dibuat, API key sudah tersambung ke service `api`
- [ ] Trace baru muncul di Langfuse setiap kali `/chat/stream` dipanggil, dengan span `retrieval`, `rerank`, dan generation `llm_generate_stream` tersusun bersarang, muncul setelah stream selesai (bukan gagal/tidak muncul sama sekali)
- [ ] Minimal satu trace sudah dibuka manual dan ditelusuri lewat UI (Bagian 5) untuk memverifikasi input/output tiap span masuk akal
- [ ] Kalau `opensearch` dimatikan paksa (mensimulasikan kegagalan), `/chat/stream` tetap fallback ke jawaban generik (bukan crash) **dan** trace tetap tercatat dengan `level="ERROR"` (lihat Bagian 4 Tahap B Langkah 4)

## Kesimpulan

Module ini membungkus **seluruh** yang sudah dibangun sepanjang Module 18-20 — hybrid search (Module 18-19) dan reranking (Module 20) — dengan visibilitas per-request. Sebelumnya, kalau ada satu jawaban NALA yang terlihat buruk, jalan satu-satunya adalah menduga-duga atau membaca log mentah; sekarang, tiap trace menunjukkan persis apa yang terjadi di tiap tahap (kandidat yang ditemukan, urutan setelah rerank, prompt lengkap yang dikirim ke LLM, jawaban akhir), lengkap dengan waktu eksekusinya.

Tapi trace cuma menjawab pertanyaan **per kasus**: "jawaban yang ini kenapa buruk?" Ia tidak menjawab pertanyaan yang sama pentingnya: **"secara keseluruhan, apakah retrieval NALA benar-benar membaik setelah hybrid search dan reranking — atau cuma kebetulan bagus di contoh yang kita coba?"** Untuk itu butuh pengukuran agregat di banyak pertanyaan sekaligus, dengan metrik yang sama setiap kali. Module 22 membangun itu: test set berlabel, Precision@k/Hit Rate@k/MRR, dan LLM-as-judge — memakai trace yang baru saja mulai terkumpul di module ini sebagai salah satu sumber pertanyaan ujinya.

Satu keuntungan urutan ini: begitu Module 22 menjalankan evaluasi batch, setiap pemanggilan retrieval di dalamnya **sudah otomatis ter-trace** — jadi kalau ada pertanyaan di test set yang skornya jeblok, Anda bisa langsung membuka trace-nya di Langfuse untuk melihat kenapa, tanpa menjalankan ulang apa pun.

