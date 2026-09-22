# Module 26: Full-Stack Deployment via Docker Compose

## Tujuan

Menyatukan seluruh service NALA yang dibangun terpisah sepanjang Module 1-25 (Ollama, OpenSearch, Postgres, Airflow, API, Langfuse self-hosted) menjadi satu `docker-compose.yml` final, dengan config/secrets di `.env`, healthcheck yang benar, dan urutan startup yang bisa diandalkan di laptop peserta.

## Definisi

**Externalize config** berarti memindahkan value yang berubah-ubah atau sensitif keluar dari `docker-compose.yml` menjadi file `.env` terpisah — bukan menuliskannya langsung (`hardcode`) di dalam YAML (Bagian 2 Tahap A). Ada dua mekanisme berbeda yang sama-sama membaca file itu: **interpolasi `.env`**, yaitu `docker compose` sendiri yang membaca `.env` untuk mengisi placeholder `${VAR}` **di dalam** `docker-compose.yml` sebelum container dibuat, dan **`env_file:`**, yaitu seluruh isi `.env` disalin jadi environment variable **di dalam container** saat runtime, dibaca aplikasi lewat `os.environ` (Bagian 2 Tahap A Langkah 3). Keduanya dipakai bersamaan di module ini, untuk tujuan yang berbeda.

Healthcheck sendiri tidak otomatis membuat service saling menunggu — itu baru terjadi kalau dipasangkan dengan `depends_on: condition: service_healthy`. Bedanya penting: `depends_on` bentuk sederhana (list, dipakai sejak Module 1) cuma menjamin **urutan start** — container B mulai setelah container A mulai, bukan setelah A benar-benar bisa menjawab request. `condition: service_healthy` menaikkan jaminan itu jadi **urutan siap**: container B baru dinyalakan setelah `healthcheck` container A benar-benar melapor `healthy` (Bagian 2 Tahap B). Bedanya sering terasa persis di titik ini — "started" bukan berarti "ready".

```mermaid
flowchart LR
    E[".env"] -->|"interpolasi ${VAR}"| C["docker-compose.yml"]
    E -->|"env_file:"| A["api (runtime os.environ)"]
    C --> H["healthcheck tiap service"]
    H -->|"belum healthy"| W["api menunggu"]
    H -->|"healthy"| S["depends_on: condition:<br/>service_healthy terpenuhi"]
    S --> R["api start"]
```

## Hasil Akhir yang Diharapkan

- `.env` berisi seluruh value sensitif/konfigurasi, sudah masuk `.gitignore`, dan tidak pernah muncul di `git status` sebagai file yang akan di-commit.
- `docker compose ps` menunjukkan status `healthy` (bukan cuma `Up`) untuk `ollama`, `opensearch`, dan `postgres`, dan `api` benar-benar menunggu ketiganya sehat sebelum start.
- Satu `docker-compose.yml` final berisi seluruh sembilan service (stack inti Module 1-25 + `adminer` + Langfuse v2 dan `langfuse-db`-nya sendiri — lihat Bagian 4a soal kenapa bukan enam service Langfuse v4) dan bisa dijalankan mengikuti urutan startup bertahap tanpa error koneksi.
- `http://localhost:8000` (chat), `http://localhost:3000` (Langfuse), `http://localhost:8080` (Airflow), dan `http://localhost:5601` (OpenSearch Dashboards) semuanya bisa dibuka setelah stack jalan.
- Kita paham trade-off resource: mana service yang boleh dimatikan sementara (Langfuse) kalau RAM laptop mepet di 16GB, tanpa mengganggu fungsi inti NALA.

## 1. Kenapa Menyatukan, Bukan Membangun Baru

Sepanjang Module 1-25, NALA tumbuh service demi service — dan `docker-compose.yml`-nya ikut tumbuh **di dalam folder kerja `Nala/` yang sama**, diedit langsung tiap module menambahkan service baru:

| Rentang Module | Service baru di `docker-compose.yml` |
|---|---|
| Module 1-4 | `ollama`, `api` |
| Module 7-16 | + `opensearch`, `opensearch-dashboards`, `airflow` |
| Module 17-20 | (OpenSearch dipakai sebagai hybrid search, Langfuse observability ditambahkan) |
| Module 21-25 | + `postgres` (data operasional), LangGraph agent berjalan di dalam `api` yang sama |

Konsekuensinya: sampai akhir Module 25, tidak pernah ada **satu** `docker-compose.yml` yang benar-benar menjalankan semuanya sekaligus — tiap module cuma menjalankan service yang relevan untuk module itu (`docker compose up <service tertentu>`), bukan seluruh stack. Module ini bukan menulis service baru — service-nya sudah semua pernah dibangun. Tugasnya murni **konsolidasi**: satu `docker-compose.yml` final, satu `.env`, urutan startup yang jelas, dan kesiapan menjalankan tujuh+ container sekaligus di laptop peserta.

Ini juga titik training paling berat secara resource — persis peringatan di README utama ("Minimal 16GB RAM — untuk menjalankan LLM lokal bersamaan dengan services pendukung"). Sampai Module 25, kita tidak pernah menyalakan **seluruh** service bersamaan; Module 26 adalah pertama kalinya itu terjadi.

```mermaid
flowchart TB
    subgraph Client["Browser Peserta"]
        UI["chat.html / upload.html"]
    end

    subgraph NALA["Stack NALA (docker compose)"]
        API["api<br/>FastAPI + LangGraph Agent"]
        Ollama["ollama<br/>llama3.2:3b + nomic-embed-text"]
        OS["opensearch<br/>hybrid search (BM25 + vector)"]
        OSD["opensearch-dashboards"]
        AF["airflow<br/>ingest pipeline (standalone)"]
        PG["postgres<br/>data operasional<br/>(pengajuan kredit, klaim)"]

        Adminer["adminer<br/>GUI database (Module 25)"]

        subgraph LF["Langfuse v2 self-hosted (observability)"]
            LFWeb["langfuse<br/>(monolitik: web+worker jadi satu)"]
            LFPG["langfuse-db"]
        end
    end

    UI -->|"/chat, /chat/stream, /upload"| API
    API -->|generate & embed| Ollama
    API -->|hybrid search| OS
    API -->|SQL tool query| PG
    API -->|traces| LFWeb
    AF -->|trigger ingest| OS
    AF -->|embed| Ollama
    OSD -->|admin UI| OS
    Adminer -->|admin UI| PG
    LFWeb --> LFPG
```

Perhatikan satu hal penting di diagram ini: **Langfuse tetap punya database sendiri** (`langfuse-db`, terpisah dari `postgres` milik NALA), tapi **jauh lebih ringan** dari rencana awal — v2 monolitik, tidak ada ClickHouse/Redis/MinIO/worker terpisah. Ini dibahas di Bagian 4a.

## 2. Struktur Kode yang Ditambahkan

### Prasyarat

- Module 1-25 sudah selesai — RAG hybrid search (Module 17-20), agent LangGraph dengan RAG+SQL tool routing dan RBAC/audit logging (Module 21-25) sudah berjalan di `Nala/`.
- Docker Desktop dialokasikan **16GB+ RAM** — lihat catatan resource lengkap di Bagian 4. Module 26 adalah titik terberat seluruh training: sembilan container berjalan bersamaan di puncaknya.
- `openssl` tersedia di terminal (dipakai untuk generate secret acak di Langkah 1) — sudah terpasang default di macOS/Linux; pengguna Windows tanpa WSL bisa memakai `python -c "import secrets; print(secrets.token_hex(32))"` sebagai gantinya.
- Module 26 **tidak** membuat folder kerja baru — semua perubahan di bagian ini diedit langsung di `Nala/`, folder yang sama dipakai sejak Module 1. Tidak ada langkah "salin folder" — dibangun bertahap di tempat, module demi module, sama seperti Module 7-16.

**Container Module 1-25 tetap dipakai — project Docker Compose yang sama sepanjang training.** Karena `Nala/` adalah satu folder yang tidak pernah berganti nama sejak Module 1, Docker Compose (yang memakai nama folder sebagai *project name* default) memperlakukan seluruh training sebagai **satu project yang sama** — disengaja, supaya `ollama`/`opensearch`/`airflow`/dst tidak berjalan berkali-kali lipat (hemat RAM) dan data yang sudah ada (index OpenSearch, data PostgreSQL, model Ollama) otomatis ikut terbawa ke Module 26, tidak perlu diulang dari nol.

Setelah `docker-compose.yml` final dibangun (Tahap C di bawah) dan dipakai, jalankan `docker compose` **dari folder `Nala/`** seperti biasa — tidak ada langkah "matikan dulu" yang diperlukan, compose otomatis merecreate container yang definisinya berubah dan membiarkan yang lain tetap jalan. Module 26 memakai port yang sama seperti Module 17-25 (`8000` API, `11434` Ollama, `9200` OpenSearch, `8080` Airflow, `5432` Postgres, `3000` Langfuse, `5601` OpenSearch Dashboards, `8081` Adminer) — tidak ada port baru untuk Langfuse karena tetap v2 (lihat Bagian 4a), bukan v4 yang butuh port tambahan MinIO console.

Dibanding akhir Module 25, ada tiga penambahan/perubahan di project kerja peserta (`Nala/` — folder yang sama, diedit langsung di tempat sejak Module 1). Dibangun bertahap dalam 3 Tahap:

1. **Tahap A — Externalize config ke `.env`.** Sejak Module 1, `OLLAMA_MODEL`, port, dan value konfigurasi lain ditulis langsung di `docker-compose.yml` (`environment: - OLLAMA_MODEL=llama3.2:3b`). Ini cukup untuk 2 service, tapi begitu sembilan service masuk — sebagian butuh password (Postgres, Langfuse) — hardcode jadi berbahaya (lihat Module 27 checklist keamanan: "secrets tidak boleh hardcoded"). Tahap ini memindahkan semua value yang berubah-ubah atau sensitif ke satu file `.env`.
2. **Tahap B — Tambah healthcheck & `depends_on: condition: service_healthy`.** Sejak Module 7, `depends_on` di NALA cuma menjamin **urutan start**, bukan **urutan siap** — `api` bisa saja mulai sebelum `opensearch` benar-benar bisa menjawab query, karena `depends_on` tanpa `condition` cuma menunggu container *start*, bukan *ready*. Tahap ini menambah `healthcheck` di service inti supaya `depends_on` bisa menunggu sampai benar-benar siap.
3. **Tahap C — Gabungkan semua service jadi satu `docker-compose.yml`**, termasuk menambahkan Langfuse self-hosted dan dependensinya sendiri.

### Tahap A — Externalize config ke `.env`

**Langkah 1 — Buat file `.env`**

⚠️ **Revisi dari rencana awal, berdasarkan pengujian nyata**: draft pertama modul ini menulis `.env` untuk Langfuse **v4** (butuh `LANGFUSE_CLICKHOUSE_PASSWORD`, `LANGFUSE_REDIS_PASSWORD`, `LANGFUSE_MINIO_ROOT_*`, `LANGFUSE_ENCRYPTION_KEY`). Setelah dipertimbangkan (lihat Bagian 2 Tahap C untuk analisis lengkap), kurikulum ini **tetap memakai Langfuse v2** yang sudah dibangun sejak Module 20 — jauh lebih ringan (2 service database sendiri, bukan 5), dan gap performanya nyaris tidak terasa pada skala trace training ini. Jadi `.env` yang benar-benar dipakai **lebih sederhana** dari draft awal:

```bash
# Nala/.env
OLLAMA_MODEL=llama3.2:3b

POSTGRES_ADMIN_PASSWORD=ganti-password-ini

LANGFUSE_DB_PASSWORD=ganti-password-ini-juga
LANGFUSE_NEXTAUTH_SECRET=ganti-dengan-string-acak-panjang
LANGFUSE_SALT=ganti-dengan-string-acak-panjang-juga
LANGFUSE_PUBLIC_KEY=pk-lf-xxxxx   # dari project Langfuse Anda sendiri (Module 20)
LANGFUSE_SECRET_KEY=sk-lf-xxxxx   # dari project Langfuse Anda sendiri (Module 20)
```

```bash
echo "POSTGRES_ADMIN_PASSWORD=$(openssl rand -hex 16)" >> .env
echo "LANGFUSE_DB_PASSWORD=$(openssl rand -hex 16)" >> .env
echo "LANGFUSE_NEXTAUTH_SECRET=$(openssl rand -hex 32)" >> .env
echo "LANGFUSE_SALT=$(openssl rand -hex 32)" >> .env
# LANGFUSE_PUBLIC_KEY/LANGFUSE_SECRET_KEY: salin dari .env/docker-compose.yml Module 20-25 Anda sendiri,
# bukan digenerate acak — ini API key project Langfuse yang sudah dibuat sejak Module 20.
```

⚠️ **Jangan** menambahkan variabel `LANGFUSE_CLICKHOUSE_PASSWORD`/`LANGFUSE_REDIS_PASSWORD`/`LANGFUSE_MINIO_ROOT_*`/`LANGFUSE_ENCRYPTION_KEY` ke `.env` — itu untuk Langfuse v4 (ClickHouse/Redis/MinIO/worker) yang **tidak** dipakai di kurikulum ini (lihat alasannya di Bagian 4a).

⚠️ Nilai `ganti-...` di atas **wajib** diganti dengan value acak sungguhan sebelum dipakai — lihat catatan keamanan lengkap di Module 27 Bagian 2.a. Password `nala_readonly`/`nala_writer`/`nala_app` (role internal PostgreSQL dari Module 21-25) **tetap hardcoded** di `db/seed.sql` dan `docker-compose.yml` — bukan terlewat, tapi keterbatasan yang diterima secara sadar: file `.sql` yang dijalankan lewat `docker-entrypoint-initdb.d` tidak bisa membaca `${VAR}` dari `.env` tanpa script wrapper tambahan (`envsubst` atau entrypoint kustom), di luar cakupan waktu modul ini. Role-role itu cuma bisa diakses dari dalam jaringan Docker internal (tidak ada port yang diekspos untuknya secara langsung selain lewat `postgres:5432` itu sendiri), jadi risikonya lebih rendah dibanding `POSTGRES_ADMIN_PASSWORD`/Langfuse yang memang perlu rotasi rutin.

<details>
<summary><strong>Pakai Claude Code? Salin prompt berikut, paste untuk eksekusi Langkah 1</strong></summary>

```
Buat file .env berisi seluruh config/secret NALA (Module 26, Tahap A,
Langkah 1) — externalize config, belum menyentuh docker-compose.yml
atau .gitignore.

GOAL:
Buat Nala/.env berisi variable:
OLLAMA_MODEL, POSTGRES_ADMIN_PASSWORD, LANGFUSE_DB_PASSWORD,
LANGFUSE_NEXTAUTH_SECRET, LANGFUSE_SALT, LANGFUSE_PUBLIC_KEY,
LANGFUSE_SECRET_KEY (dua yang terakhir disalin dari project Langfuse
yang sudah dibuat sejak Module 20, BUKAN digenerate acak) —
semua value password/secret lainnya WAJIB string acak (bukan
"changeme" atau kosong), pakai `openssl rand -hex 16` untuk
password dan `openssl rand -hex 32` untuk secret/salt.

CONTEXT:
- Folder Nala/ adalah folder kerja yang sama dipakai sejak Module 1
  — diedit langsung di tempat, bukan disalin.
- docker-compose.yml dan .gitignore BELUM disentuh di langkah ini.

GUARDRAIL:
- JANGAN pakai password kosong atau contoh yang gampang ditebak
  (mis. "changeme").
- JANGAN tambah variabel LANGFUSE_CLICKHOUSE_PASSWORD/
  LANGFUSE_REDIS_PASSWORD/LANGFUSE_MINIO_ROOT_*/
  LANGFUSE_ENCRYPTION_KEY — itu untuk Langfuse v4 yang tidak dipakai
  di kurikulum ini.
```

</details>

**Langkah 2 — Tambah `.env` ke `.gitignore`**

```bash
# Nala/.gitignore
.env
```

Ini bukan langkah kosmetik — `.env` berisi password/secret; kalau ikut ter-commit ke Git, siapa pun dengan akses repo (termasuk riwayat commit lama setelah file "dihapus") bisa membacanya. Lihat Module 27 Bagian 2.a.

<details>
<summary><strong>Pakai Claude Code? Salin prompt berikut, paste untuk eksekusi Langkah 2</strong></summary>

```
Pastikan .env tidak pernah ter-commit ke Git (Module 26, Tahap A,
Langkah 2).

GOAL:
1. Tambah/pastikan ada baris ".env" di Nala/.gitignore.
2. Kalau .env pernah ter-track Git sebelumnya, jalankan
   `git rm --cached .env` di folder Nala/.

CONTEXT:
- Nala/.env sudah dibuat di Langkah 1, berisi password/secret asli
  — jangan sampai ter-commit.

GUARDRAIL:
- JANGAN commit .env — pastikan `git status` di Nala/ tidak
  menampilkannya sebagai untracked/staged file.
- JANGAN hapus isi .env, cuma ubah .gitignore dan (kalau perlu)
  index Git.
```

</details>

**Langkah 3 — Rujuk `.env` di `docker-compose.yml` lewat `${VAR}`**

Dua mekanisme berbeda yang gampang tertukar, keduanya dipakai di Module ini:

| Mekanisme | Kerja di mana | Contoh |
|---|---|---|
| **Interpolasi `.env` di compose** | Dibaca oleh `docker compose` sendiri **sebelum** container dibuat — mengisi placeholder `${VAR}` di file `docker-compose.yml` (misalnya nilai `image: postgres:${POSTGRES_VERSION}` atau `POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}`) | `${OLLAMA_MODEL}` di baris `environment` |
| **`env_file:`** | Menyalin **seluruh isi** `.env` jadi environment variable di **dalam container** saat runtime — aplikasi (Python, dst) membacanya lewat `os.environ`, bukan `docker compose` yang membacanya | `env_file: .env` di service `api` |

Keduanya dipakai bersamaan di Module ini: interpolasi `${VAR}` untuk mengisi value di dalam `docker-compose.yml` itu sendiri (misalnya `POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}` di service `postgres`), dan `env_file: .env` di service `api` supaya kode Python (`os.environ.get("OLLAMA_MODEL")`, sudah dipakai sejak Module 1) tetap bekerja tanpa perlu menulis ulang tiap variable satu-satu di `environment:`.

**▶️ Jalankan & lihat hasilnya**

Belum ada `docker-compose.yml` yang berubah di langkah ini — cukup pastikan `.env` dan `.gitignore` sudah ada dan `.env` **tidak** muncul di `git status` sebagai file yang akan di-commit (kalau repo Git peserta sudah pernah `git add .env` sebelumnya, `.gitignore` saja tidak cukup — perlu `git rm --cached .env` juga).

```bash
cd Nala
git status
```

Verifikasi juga tidak ada secret kosong:

```bash
cat .env
```

Semua baris harus punya value setelah `=` — kalau ada yang kosong (kemungkinan `openssl` gagal dijalankan), isi manual dengan string acak sebelum lanjut.

✅ **Indikator sukses**: `.env` ada isinya (tidak ada baris kosong setelah `=`), `.gitignore` memuat baris `.env`, dan `git status` tidak menampilkan `.env` sebagai untracked/staged file.

### Tahap B — Healthcheck & `depends_on: condition: service_healthy`

**Langkah 4 — Tambah `healthcheck` di tiga service inti**

```yaml
# Nala/docker-compose.yml (potongan)
services:
  ollama:
    image: ollama/ollama:latest
    healthcheck:
      test: ["CMD-SHELL", "ollama list || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 30s
    # ports, volumes: sama seperti Module 1-25

  opensearch:
    image: opensearchproject/opensearch:2.11.0
    healthcheck:
      test: ["CMD-SHELL", "curl -s http://localhost:9200/_cluster/health | grep -qE '\"status\":\"(green|yellow)\"'"]
      interval: 15s
      timeout: 10s
      retries: 20
      start_period: 60s
    # environment, ports, volumes: sama seperti Module 7-16

  postgres:
    image: postgres:16
    environment:
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=${POSTGRES_DB}
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 15s
    # ports, volumes: sama seperti Module 21-25
```

- **`ollama`**: image resminya tidak menyertakan `curl`, jadi healthcheck memakai `ollama list` — perintah CLI Ollama sendiri, yang otomatis gagal (`exit 1`) kalau daemon di dalam container belum siap menjawab.
- **`opensearch`**: image OpenSearch resmi menyertakan `curl`, jadi healthcheck bisa langsung memanggil endpoint `_cluster/health` bawaan OpenSearch dan mengecek statusnya `green` atau `yellow` (bukan `red`) — pola yang sama seperti dicek manual lewat log di panduan praktik Module 7-16, sekarang otomatis.
- **`postgres`**: `pg_isready` adalah utility bawaan image `postgres` resmi, dirancang persis untuk healthcheck seperti ini.
- **`start_period`** memberi waktu toleransi sebelum kegagalan pertama dihitung sebagai "unhealthy" — penting untuk OpenSearch yang butuh waktu inisialisasi cluster cukup lama (lihat panduan praktik Module 7-16: "proses ini akan terasa lama").

<details>
<summary><strong>Pakai Claude Code? Salin prompt berikut, paste untuk eksekusi Langkah 4</strong></summary>

```
Tambah healthcheck di service ollama/opensearch/postgres (Module 26,
Tahap B, Langkah 4).

GOAL:
Di Nala/docker-compose.yml:
1. Tambah healthcheck di service `ollama`: test CMD-SHELL
   "ollama list || exit 1", interval 10s, timeout 5s, retries 10,
   start_period 30s.
2. Tambah healthcheck di service `opensearch`: test CMD-SHELL curl
   ke http://localhost:9200/_cluster/health, grep status green atau
   yellow, interval 15s, timeout 10s, retries 20, start_period 60s.
3. Tambah healthcheck di service `postgres`: test CMD-SHELL
   "pg_isready -U ${POSTGRES_USER}", interval 10s, timeout 5s,
   retries 10, start_period 15s.
4. JANGAN tambah healthcheck untuk airflow di langkah ini.

CONTEXT:
- File ini docker-compose.yml yang sudah dibangun sejak Module 1-25,
  diedit langsung di tempat (bukan salinan dari folder lain).
- .env sudah dibuat di Tahap A, berisi POSTGRES_USER dkk.

GUARDRAIL:
- JANGAN hapus environment/ports/volumes yang sudah ada di service
  manapun — cuma tambah healthcheck.
- JANGAN ubah depends_on di langkah ini — itu Langkah 5.
- JANGAN tambah service Langfuse di langkah ini — itu Tahap C.
```

</details>

**Langkah 5 — Ubah `depends_on` service `api` supaya menunggu "healthy", bukan cuma "started"**

```yaml
# Nala/docker-compose.yml (potongan)
  api:
    build: .
    env_file: .env
    depends_on:
      ollama:
        condition: service_healthy
      opensearch:
        condition: service_healthy
      postgres:
        condition: service_healthy
    # ports, environment, volumes lain: sama seperti Module 21-25
```

Dibanding `depends_on` bentuk list sederhana yang dipakai sejak Module 1 (`depends_on: - ollama`), bentuk `condition: service_healthy` ini membuat Docker Compose benar-benar **menunggu** `healthcheck` masing-masing service melapor sehat, baru menyalakan `api`. Tanpa ini, `api` bisa saja start duluan lalu gagal koneksi ke OpenSearch yang masih inisialisasi — errornya baru terlihat saat request pertama masuk, bukan saat startup.

⚠️ **Airflow sengaja tidak diberi `healthcheck` di sini.** Mode `standalone` (dipakai sejak Module 7) menjalankan webserver + scheduler + database metadata dalam satu proses dengan waktu startup yang tidak konsisten — healthcheck yang akurat untuknya butuh polling endpoint API Airflow yang di luar cakupan modul ini. `depends_on: - airflow` (list sederhana, bukan `condition`) tetap dipakai untuk service yang butuh Airflow start duluan; kita tetap perlu menunggu manual lewat `docker compose logs -f airflow` seperti di Module 7-16, bukan otomatis lewat healthcheck.

**▶️ Jalankan & lihat hasilnya**

```bash
docker compose up --build ollama opensearch postgres
```

Di terminal lain, pantau status healthcheck:

```bash
docker compose ps
```

✅ **Indikator sukses**: kolom `STATUS` di `docker compose ps` menunjukkan `healthy` (bukan cuma `Up`) untuk ketiga service setelah beberapa saat. Coba juga `docker compose up --build api` **sebelum** ketiganya sehat — `api` harus terlihat menunggu (bukan langsung start lalu error) di log Docker Compose.

<details>
<summary><strong>Pakai Claude Code? Salin prompt berikut, paste untuk eksekusi Langkah 5</strong></summary>

```
Ubah depends_on api jadi condition: service_healthy (Module 26,
Tahap B, Langkah 5).

GOAL:
Di Nala/docker-compose.yml, ubah depends_on di service `api` dari
bentuk list sederhana menjadi bentuk dict dengan
condition: service_healthy untuk ollama, opensearch, dan postgres.

CONTEXT:
- healthcheck ollama/opensearch/postgres sudah ditambahkan di
  Langkah 4 — langkah ini cuma mengubah bentuk depends_on api supaya
  memanfaatkannya.
- File ini docker-compose.yml yang sudah dibangun sejak Module 1-25,
  diedit langsung di tempat.

GUARDRAIL:
- JANGAN ubah healthcheck yang sudah ada di Langkah 4.
- JANGAN tambah healthcheck untuk airflow — sengaja tidak diberi
  healthcheck di module ini (lihat ⚠️ di atas).
- JANGAN tambah service Langfuse di langkah ini — itu Tahap C.
```

</details>

### Tahap C — Gabungkan semua service (Langfuse tetap v2, keputusan sadar — lihat Bagian 4a)

**Langkah 6 — Kode lengkap `docker-compose.yml` final Module 26**

Tahap ini paling besar — menyatukan `ollama`, `opensearch`, `opensearch-dashboards`, `postgres`, `airflow`, `api`, `adminer` (Module 1-25, disalin tanpa perubahan logika, ditambah healthcheck dari Tahap B) dengan `langfuse-db` + `langfuse` yang **sudah berjalan sejak Module 20** — bukan stack baru yang ditulis dari nol di sini.

⚠️ **Revisi dari rencana awal, berdasarkan pengujian nyata**: draft pertama modul ini merancang Langfuse **v4** (`langfuse/langfuse` + `langfuse/langfuse-worker` + PostgreSQL + ClickHouse + Redis + MinIO — enam service pendukung) sebagai "self-hosted yang benar". Setelah dianalisis (lihat Bagian 4a) — untuk volume trace di skala training ini (ratusan-ribuan baris, bukan jutaan), ClickHouse/Redis/MinIO menambah **~1,5-3GB RAM** tanpa manfaat yang terasa, dan Redis khususnya **tidak bisa** ditambahkan sebagian ke v2 (v2 tidak punya titik integrasi Redis sama sekali di kodenya — mengonfirmasi lewat dokumentasi resmi Langfuse). Keputusan final: **tetap pakai `langfuse/langfuse:2`** (monolitik, cuma butuh 1 PostgreSQL sendiri) yang sudah terbukti jalan sejak Module 20. Kalau kelas Anda punya alasan kuat untuk trafik produksi sungguhan, v4 tetap valid sebagai referensi — cek dokumentasi self-hosting resmi Langfuse untuk versi dan environment variable yang berlaku saat itu.

```yaml
# Nala/docker-compose.yml — VERSI NYATA, sudah dijalankan dan diverifikasi
services:
  ollama:
    image: ollama/ollama:latest
    ports:
      - '11434:11434'
    volumes:
      - ollama_data:/root/.ollama
    healthcheck:
      test: ["CMD-SHELL", "ollama list || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 30s

  api:
    build: .
    ports:
      - '8000:8000'
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434
      - OLLAMA_MODEL=${OLLAMA_MODEL}
      - KNOWLEDGE_BASE_PATH=/app/knowledge-base
      - OPENSEARCH_BASE_URL=http://opensearch:9200
      - HF_HOME=/app/.cache/huggingface
      - LANGFUSE_PUBLIC_KEY=${LANGFUSE_PUBLIC_KEY}
      - LANGFUSE_SECRET_KEY=${LANGFUSE_SECRET_KEY}
      - LANGFUSE_HOST=http://langfuse:3000
      - POSTGRES_READONLY_DSN=postgresql://nala_readonly:readonly_dev_only@postgres:5432/nala_operasional
      - POSTGRES_WRITER_DSN=postgresql://nala_writer:writer_dev_only@postgres:5432/nala_operasional
      - POSTGRES_APP_DSN=postgresql://nala_app:app_dev_only@postgres:5432/nala_operasional
    volumes:
      - ../resources/sample-knowledge-base:/app/knowledge-base
      - hf_cache:/app/.cache/huggingface
    depends_on:
      ollama:
        condition: service_healthy
      opensearch:
        condition: service_healthy
      postgres:
        condition: service_healthy

  opensearch:
    image: opensearchproject/opensearch:2.11.0
    environment:
      - discovery.type=single-node
      - plugins.security.disabled=true
      - OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx512m
      - DISABLE_INSTALL_DEMO_CONFIG=true
    ports:
      - '9200:9200'
    volumes:
      - opensearch_data:/usr/share/opensearch/data
    healthcheck:
      test: ["CMD-SHELL", "curl -s http://localhost:9200/_cluster/health | grep -q '\"status\":\"green\"\\|\"status\":\"yellow\"'"]
      interval: 10s
      timeout: 5s
      retries: 15
      start_period: 30s

  opensearch-dashboards:
    image: opensearchproject/opensearch-dashboards:2.11.0
    environment:
      - 'OPENSEARCH_HOSTS=["http://opensearch:9200"]'
      - DISABLE_SECURITY_DASHBOARDS_PLUGIN=true
    ports:
      - '5601:5601'
    depends_on:
      - opensearch

  airflow:
    image: apache/airflow:2.10.2
    command: standalone
    environment:
      - AIRFLOW__CORE__LOAD_EXAMPLES=false
      - AIRFLOW__CORE__DAGS_FOLDER=/opt/airflow/dags
      - OLLAMA_BASE_URL=http://ollama:11434
      - OPENSEARCH_BASE_URL=http://opensearch:9200
      - _PIP_ADDITIONAL_REQUIREMENTS=pypdf==5.1.0 httpx==0.27.2
    ports:
      - '8080:8080'
    volumes:
      - ./airflow/dags:/opt/airflow/dags
      - ./app:/opt/airflow/dags/app
      - ../resources/sample-knowledge-base:/opt/airflow/knowledge-base
    depends_on:
      - opensearch
      - ollama

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

  adminer:
    image: adminer:latest
    ports:
      - "8081:8080"
    depends_on:
      postgres:
        condition: service_healthy

  langfuse-db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=langfuse
      - POSTGRES_PASSWORD=${LANGFUSE_DB_PASSWORD}
      - POSTGRES_DB=langfuse
    volumes:
      - langfuse_db_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U langfuse -d langfuse"]
      interval: 5s
      timeout: 5s
      retries: 10

  langfuse:
    image: langfuse/langfuse:2
    environment:
      - DATABASE_URL=postgresql://langfuse:${LANGFUSE_DB_PASSWORD}@langfuse-db:5432/langfuse
      - NEXTAUTH_URL=http://localhost:3000
      - NEXTAUTH_SECRET=${LANGFUSE_NEXTAUTH_SECRET}
      - SALT=${LANGFUSE_SALT}
    ports:
      - "3000:3000"
    depends_on:
      langfuse-db:
        condition: service_healthy

volumes:
  ollama_data:
  opensearch_data:
  hf_cache:
  langfuse_db_data:
  postgres_data:
```

Sembilan service total (bukan tiga belas seperti estimasi awal berbasis v4) — `ollama`, `api`, `opensearch`, `opensearch-dashboards`, `airflow`, `postgres`, `adminer` (Module 25, UI database ringan), `langfuse-db`, `langfuse`. Ini konfigurasi yang **sudah dijalankan langsung** (`docker compose up -d`), bukan ilustratif — lihat Bagian 4a untuk hasil pengujiannya, termasuk satu gotcha nyata soal rotasi password.

**▶️ Jalankan & lihat hasilnya**

Jangan langsung `docker compose up` semuanya sekaligus dari kondisi dingin — ikuti urutan startup bertahap di **Bagian 3, Langkah 7-9** di bawah (lapisan dasar → model Ollama → lapisan menengah → lapisan aplikasi), lalu verifikasi dan uji end-to-end di sana.

<details>
<summary><strong>Pakai Claude Code? Salin prompt berikut, paste untuk eksekusi Langkah 6</strong></summary>

```
Satukan seluruh service Module 1-25 dengan Langfuse self-hosted jadi satu
docker-compose.yml final (Module 26, Tahap C).

GOAL:
Update Nala/docker-compose.yml (folder kerja
yang sudah dipakai sejak Module 1-25) supaya:
1. Tambah healthcheck di ollama dan opensearch (Tahap B), ubah
   depends_on api jadi condition: service_healthy untuk ollama,
   opensearch, DAN postgres (postgres sudah punya healthcheck dari
   Module 21-25, tinggal disambung).
2. Ganti value environment yang sensitif jadi ${VAR} merujuk .env:
   OLLAMA_MODEL, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY di service
   api; POSTGRES_PASSWORD di service postgres jadi
   ${POSTGRES_ADMIN_PASSWORD:-changeme_dev_only}; POSTGRES_PASSWORD
   di langfuse-db jadi ${LANGFUSE_DB_PASSWORD}; NEXTAUTH_SECRET/SALT
   di langfuse jadi ${LANGFUSE_NEXTAUTH_SECRET}/${LANGFUSE_SALT}, dan
   DATABASE_URL di langfuse ikut memakai ${LANGFUSE_DB_PASSWORD}.
3. Tambah healthcheck pg_isready di langfuse-db, ubah depends_on
   langfuse jadi condition: service_healthy ke langfuse-db.
4. JANGAN tambah service Langfuse v4 (ClickHouse/Redis/MinIO/worker)
   — kurikulum ini SENGAJA tetap pakai langfuse/langfuse:2 (monolitik,
   1 Postgres sendiri) karena gap performa v4 tidak terasa di skala
   training dan v3/v4 butuh RAM tambahan signifikan (lihat materi Bagian 4a).

CONTEXT:
- Postgres role nala_readonly/nala_writer/nala_app (Module 23/25)
  TETAP pakai password hardcoded di environment api dan db/seed.sql —
  ini keterbatasan yang diterima sadar (seed.sql tidak bisa baca
  ${VAR} tanpa wrapper tambahan), JANGAN diubah di langkah ini.
- Kalau volume postgres_data/langfuse_db_data SUDAH ada dari Module 21-25
  (project Docker Compose "nala" dipakai bersama), mengganti password
  di .env TIDAK otomatis mengubah password sungguhan di database —
  perlu ALTER USER manual (lihat materi Bagian 4a) atau reset volume.

GUARDRAIL:
- JANGAN ubah logika/environment service ollama, opensearch,
  opensearch-dashboards, postgres, airflow, api di luar poin 1-2 di
  atas — service-service ini SUDAH BENAR dari Module 1-25.
- JANGAN commit .env, dan JANGAN tulis password sungguhan langsung
  di docker-compose.yml — semua secret WAJIB lewat ${VAR} dari .env.
- JANGAN tambah ClickHouse/Redis/MinIO/langfuse-worker — keputusan
  sadar untuk tetap di Langfuse v2 (lihat Bagian 4a).
```

</details>

**📄 Kode lengkap**: lihat blok YAML lengkap di Langkah 6 di atas — itu adalah `docker-compose.yml` final Module 26.

## 3. Startup Bertahap, Verifikasi, dan Uji End-to-End

Menjalankan sembilan service sekaligus dari kondisi dingin (image belum pernah di-pull, volume kosong) nyaris selalu bermasalah — bukan karena konfigurasinya salah, tapi karena **kecepatan siap tiap service jauh berbeda**, sama seperti sudah dialami di Module 7-16 (OpenSearch dan Airflow "terasa lama"). `depends_on: condition: service_healthy` (Tahap B) sudah **mengotomatiskan** sebagian urutan ini untuk `api` (menunggu `ollama`/`opensearch`/`postgres`) dan `langfuse` (menunggu `langfuse-db`) — tapi tetap lebih aman menjalankan `docker compose up` bertahap per lapisan daripada semuanya sekaligus, terutama di percobaan pertama.

**Langkah 7 — Startup bertahap (jangan `docker compose up` semuanya sekaligus)**

**7a. Lapisan dasar** (`ollama`, `postgres`, `opensearch`, `langfuse-db`) — tunggu semuanya `healthy` sebelum lanjut:

```bash
docker compose up -d ollama postgres opensearch langfuse-db
```

Pantau sampai semuanya `healthy`:

```bash
watch docker compose ps
```

(Kalau `watch` tidak tersedia, ulangi `docker compose ps` manual tiap 15-30 detik.) Ini bisa memakan beberapa menit — OpenSearch paling lama, konsisten dengan pengalaman Module 7-16.

**7b. Model Ollama** (kalau volume `ollama_data` Module 26 baru/kosong — cek dulu dengan `docker compose exec ollama ollama list`, model dari Module 1-25 bisa saja sudah tersimpan di volume yang sama kalau nama volume tidak berubah)

```bash
docker compose exec ollama ollama pull llama3.2:3b
docker compose exec ollama ollama pull nomic-embed-text
```

**7c. Lapisan menengah** (`opensearch-dashboards`, `airflow`, `adminer` — paralel, tidak saling bergantung satu sama lain, bisa dinyalakan begitu lapisan dasar `healthy`):

```bash
docker compose up -d opensearch-dashboards airflow adminer
```

Airflow tetap butuh dipantau manual (sengaja tidak diberi `healthcheck`, lihat ⚠️ di Tahap B):

```bash
docker compose logs -f airflow
```

Tunggu sampai muncul password admin dan indikasi webserver listen, lalu `Ctrl+C`.

**7d. Lapisan aplikasi** (`api`, `langfuse` — baru dinyalakan setelah lapisan di bawahnya siap, karena keduanya langsung melakukan koneksi database saat startup, bukan lazy-connect):

```bash
docker compose up -d api langfuse
```

**Langkah 8 — Verifikasi semua service hidup**

```bash
docker compose ps
```

Semua baris `STATUS` harus `Up` (yang punya healthcheck: `(healthy)`). Buka satu per satu di browser:

- `http://localhost:8000` — Chat NALA
- `http://localhost:8000/upload` — Knowledge base
- `http://localhost:8000/status/view` — Status page (Module 27)
- `http://localhost:3000` — Langfuse (setup akun admin pertama kali diminta di sini)
- `http://localhost:8080` — Airflow
- `http://localhost:5601` — OpenSearch Dashboards

✅ **Indikator sukses**: semua service berstatus `Up` (yang punya healthcheck: `healthy`), tidak ada yang `Restarting` terus-menerus, dan seluruh URL di atas bisa dibuka.

**Langkah 9 — Coba end-to-end: RAG dan SQL tool sekaligus**

Kirim dua jenis pertanyaan ke `http://localhost:8000` untuk memverifikasi routing agent Module 21-25 masih bekerja di stack gabungan ini:

1. Pertanyaan dokumen SOP (RAG): *"Apa saja syarat pengajuan kredit untuk nasabah perorangan?"*
2. Pertanyaan data operasional (SQL tool): sesuaikan dengan data dummy Module 21-25 Anda, misalnya *"Berapa banyak pengajuan kredit yang statusnya masih diproses?"*

Amati badge tool (Module 28) muncul sesuai jenis pertanyaan, dan cek trace-nya muncul di dashboard Langfuse (`http://localhost:3000`).

✅ **Indikator sukses**: kedua jenis pertanyaan dijawab dengan tool yang sesuai, dan traces-nya muncul di Langfuse.

Setelah stack ini jalan dan diverifikasi, lanjutkan ke **Module 27 materi.md** (`../Module-27-Monitoring-Security-Checklist/materi.md`) untuk menambahkan status page dan menjalankan checklist keamanan.

## 4. Resource Awareness: Titik Terberat Seluruh Training

Root README mensyaratkan **minimal 16GB RAM** sejak awal training, dengan alasan eksplisit: "menjalankan LLM lokal (Ollama) bersamaan dengan services pendukung". Module 26 adalah titik di mana syarat itu benar-benar diuji — sembilan container, termasuk satu JVM (`opensearch`), berjalan bersamaan.

| Kelompok Service | Perkiraan Beban |
|---|---|
| `ollama` (model + inference) | Terberat untuk CPU/RAM saat generate aktif — `llama3.2:3b` (~4-6GB termuat) |
| `opensearch` | JVM heap `-Xms512m -Xmx512m` minimal, overhead OS+JVM lebih besar dari heap-nya |
| `airflow` standalone | Webserver + scheduler + metadata DB dalam satu proses |
| `postgres` (data operasional) | Ringan saat idle, wajar untuk dataset training kecil |
| `langfuse` + `langfuse-db` | Ringan (v2 monolitik, 2 container total) — lihat Bagian 4a kenapa ini bukan 6 container v4 |
| `adminer` | Nyaris tidak terasa (~20MB image, tanpa proses berat) |

### 4a. Hasil Uji Nyata: Kenapa Langfuse Tetap v2, dan Gotcha Rotasi Password

**Keputusan v2 vs v4** — draft awal modul ini merancang Langfuse v4 (`langfuse-web` + `langfuse-worker` + ClickHouse + Redis + MinIO + Postgres, 6 container). Sebelum menulis konfigurasi itu, dianalisis dulu manfaatnya untuk skala training kita:

- ClickHouse ada untuk **query analytics atas volume trace besar** (ribuan-jutaan baris) — total trace seluruh training ini kemungkinan di bawah beberapa ribu baris, PostgreSQL polos menanganinya instan, tidak ada bottleneck yang akan terasa.
- Redis ada untuk **antrian async** supaya `INSERT` trace tidak memblokir response ke user — tapi dikonfirmasi lewat [dokumentasi resmi Langfuse](https://langfuse.com/self-hosting/v2/deployment-guide) bahwa **v2 tidak punya titik integrasi Redis sama sekali** — menambah Redis tanpa migrasi penuh ke v3/v4 (worker + ClickHouse) akan jadi container mubazir, tidak dipakai kode manapun.
- Biaya nyata menambah v4: ClickHouse sendiri butuh ~1-2GB RAM minimal, Redis+MinIO menambah lagi — total tambahan realistis **~1,5-3GB RAM** tanpa manfaat yang terasa di skala kita, bertentangan dengan peringatan RAM 16GB yang berulang di kurikulum ini.

**Keputusan: tetap `langfuse/langfuse:2`** (monolitik, 1 Postgres sendiri) — sudah jalan sejak Module 20, terverifikasi ulang di Module 26 tanpa masalah fungsional.

**Gotcha nyata yang ditemukan saat migrasi ke `.env`**: karena `Nala/` adalah folder kerja tunggal yang dipakai terus-menerus sejak Module 1 (nama project Docker Compose sama sepanjang training — lihat Prasyarat), volume `postgres_data`/`langfuse_db_data` **sudah ada** dari Module 21-25 dengan password lama ter-bake di dalamnya. Mengganti `POSTGRES_ADMIN_PASSWORD`/`LANGFUSE_DB_PASSWORD` di `.env` lalu `docker compose up` ulang **tidak** membuat password baru itu benar-benar aktif — PostgreSQL cuma menjalankan `POSTGRES_PASSWORD` env var saat volume data **masih kosong** (inisialisasi pertama), bukan setiap restart. Dibuktikan langsung:

```bash
# Password BARU dari .env — GAGAL saat volume sudah ada isinya
docker exec nala-api-1 python -c "
import psycopg
psycopg.connect('postgresql://nala_admin:PASSWORD_BARU@postgres:5432/nala_operasional')
"
# FATAL: password authentication failed for user "nala_admin"

# Password LAMA (default Module 21-25) — tetap yang aktif
docker exec nala-api-1 python -c "
import psycopg
psycopg.connect('postgresql://nala_admin:changeme_dev_only@postgres:5432/nala_operasional')
"
# berhasil connect
```

Langfuse mengalami hal sama persis — lognya menunjukkan `Error: P1000: Authentication failed against database server at langfuse-db`. **Perbaikan**: jalankan `ALTER USER` manual untuk menyinkronkan password sungguhan di database dengan value baru di `.env` (bukan reset volume — supaya data yang sudah diisi Module 25 tidak hilang):

```bash
docker exec nala-postgres-1 psql -U nala_admin -d nala_operasional \
  -c "ALTER USER nala_admin PASSWORD '<value dari POSTGRES_ADMIN_PASSWORD di .env>';"
docker exec nala-langfuse-db-1 psql -U langfuse -d langfuse \
  -c "ALTER USER langfuse PASSWORD '<value dari LANGFUSE_DB_PASSWORD di .env>';"
docker compose restart langfuse
```

**Pelajaran yang bisa kita ambil**: "externalize ke `.env`" itu mudah kalau volume masih kosong (deployment baru) — begitu ada data lama yang mau dipertahankan (skenario paling realistis di produksi sungguhan: rotasi password rutin tanpa downtime/reset data), butuh langkah tambahan (`ALTER USER`) yang tidak otomatis dari `docker-compose.yml` manapun. Ini bukan kegagalan desain — ini properti dasar bagaimana image Postgres resmi bekerja, dan perlu dipahami sebelum melakukan rotasi password di lingkungan mana pun yang datanya ingin dipertahankan.

**Kalau RAM benar-benar mepet di 16GB:** stack Langfuse (2 container: `langfuse`, `langfuse-db`) adalah kandidat pertama untuk dimatikan sementara (`docker compose stop langfuse langfuse-db`) — NALA (chat, RAG, agent) tetap berfungsi penuh tanpa Langfuse, cuma kehilangan observability/tracing (Module 27). Ini trade-off yang jujur untuk kita sadari, bukan disembunyikan: **Langfuse penting untuk observability produksi, tapi bukan dependency fungsional NALA** — beda dengan OpenSearch/Postgres yang kalau mati, `/chat/stream` dan `/chat` langsung kehilangan kemampuan inti (fallback ke jawaban generik, lihat Module 13 Bagian 2 Langkah 3).

Untuk kelas dengan variasi RAM laptop yang lebar, pertimbangkan opsi ini (dibahas juga di bagian Troubleshooting di bawah):
- Kalau RAM laptop kita 16GB pas-pasan: jalankan stack inti (tanpa Langfuse) untuk latihan Module 26 dan 28, nyalakan Langfuse khusus saat giliran latihan Module 27, matikan lagi sesudahnya.
- Kalau RAM laptop kita 32GB+: bisa menjalankan semuanya bersamaan sepanjang hari tanpa masalah — dan kalau kelas benar-benar butuh skala trace besar (bukan konteks training ini), v4 tetap opsi valid, cek dokumentasi self-hosting resmi Langfuse untuk versi terkini.

### Troubleshooting

- **Laptop sangat lambat / container ter-*kill* / Docker Desktop crash**: ini kemungkinan besar RAM tidak cukup untuk menjalankan sembilan container sekaligus. Matikan sementara stack Langfuse (`docker compose stop langfuse langfuse-db`) selama latihan Module 26 dan Module 28, nyalakan lagi khusus saat giliran Module 27 atau demo capstone yang perlu menunjukkan dashboard.
- **`langfuse` terus `Restarting` / error koneksi database (`Error: P1000: Authentication failed`) saat startup**: dua kemungkinan — (1) `langfuse-db` belum benar-benar `healthy` saat `langfuse` mencoba connect, cek `docker compose ps langfuse-db` dan tunggu; (2) **lebih sering terjadi kalau melanjutkan dari volume Module 17-25 yang sudah ada** — password di `.env` tidak otomatis jadi password sungguhan di database yang sudah pernah di-init (lihat "Gotcha Rotasi Password" di atas untuk penjelasan lengkap + cara fix pakai `ALTER USER`).
- **Password baru di `.env` tidak berfungsi setelah `docker compose up` ulang** (untuk `postgres` ATAU `langfuse-db`): ini bukan bug — PostgreSQL cuma menerapkan `POSTGRES_PASSWORD` saat volume data masih kosong, bukan tiap restart. Kalau melanjutkan dari volume yang sudah ada isinya (skenario umum di Module 26 karena project Docker Compose dipakai bersama sejak Module 17-25), jalankan `ALTER USER <role> PASSWORD '<value baru>';` manual lewat `psql` di masing-masing database, baru `docker compose restart <service>`. Detail lengkap dan contoh perintah ada di bagian "Gotcha Rotasi Password" di atas.
- **Port `3000`/`5601`/`8081` sudah dipakai**: ubah mapping port service yang bentrok di `docker-compose.yml` (misal `3001:3000` untuk Langfuse) — aplikasi lain di laptop (dev server Node.js umum memakai `3000`) sering memakai port ini juga.
- **`OpenSearch`/`vm.max_map_count`, password admin Airflow hilang, `no configuration file provided`, dsb.**: sama persis dengan troubleshooting panduan praktik Module 7-16 — service-service ini tidak berubah perilakunya di Module 26, cuma dijalankan bersamaan dengan lebih banyak service lain. Rujuk bagian Troubleshooting panduan praktik Module 7-16 untuk keduanya.

## 5. Apa yang TIDAK Ada di Module Ini

- Tidak ada service baru yang **logikanya** baru — semua kode aplikasi (`app/main.py`, agent LangGraph, RAG chain) sudah selesai di Module 1-25. Module ini murni infrastruktur deployment.
- Tidak membahas deployment ke cloud/server produksi sungguhan (load balancer, TLS/HTTPS, container orchestration seperti Kubernetes) — di luar cakupan training ini yang fokus offline/private-first di laptop peserta.
- Tidak membahas backup/disaster recovery volume Docker secara mendalam — disinggung sebagai catatan best-practice, bukan diimplementasikan.

## Kesimpulan

Module ini menyatukan seluruh pekerjaan Module 1-25 menjadi satu `docker-compose.yml` yang bisa dijalankan dengan satu urutan perintah yang jelas — bukan tujuh potongan konfigurasi yang tersebar di folder berbeda. Tiga kebiasaan deployment yang dibangun di sini (`.env` untuk config/secrets, healthcheck untuk urutan startup yang benar, kesadaran resource untuk sistem yang berat) berlaku umum di luar konteks NALA — bukan trik khusus training ini. Module 27 melanjutkan dari titik ini: begitu semua service jalan, bagaimana cara tahu semuanya **tetap** sehat, dan apa yang perlu direview dari sisi keamanan sebelum NALA dianggap layak dipakai staf sungguhan.
