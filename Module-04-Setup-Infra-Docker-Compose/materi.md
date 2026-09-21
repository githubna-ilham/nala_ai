# Module 4: Setup Infra Docker Compose

## Tujuan

Kita memahami konsep dasar Docker/Docker Compose dan FastAPI, lalu membangun sendiri secara bertahap endpoint `/chat` NALA yang terhubung ke Ollama dan memakai `NALA_SYSTEM_PROMPT` hasil Module 3, dijalankan lewat Docker Compose.

## Hasil Akhir yang Diharapkan

- Kita paham konsep image, container, dan fungsi tiap bagian `docker-compose.yml` (services, ports, volumes, environment, depends_on)
- Service `ollama` berhasil dijalankan & diverifikasi sendirian di Docker (model ter-pull, API merespons) sebelum service `api` ditambahkan
- `docker-compose.yml` NALA (service `ollama` + `api`) berhasil dijalankan dengan `docker compose up --build`
- Endpoint `/health` dan `/chat` di `app/main.py` berfungsi — `/chat` memanggil Ollama lewat `OllamaClient` dan mengembalikan jawaban
- Endpoint `/chat` sudah memakai `NALA_SYSTEM_PROMPT` hasil Module 3, terbukti dari jawaban yang berkarakter NALA, bukan lagi generik
- Kita paham kapan menggunakan `docker compose up --build` vs `up` vs `down` setiap kali kode diubah
- Kita paham alur request FastAPI ↔ Ollama serta konsep Pydantic request/response model

## 1. Apa itu Docker?

Sebelum masuk ke Docker Compose, pahami dulu Docker itu sendiri — supaya section-section berikutnya tidak terasa seperti istilah asing yang tiba-tiba muncul.

**Analogi sederhana:** bayangkan Anda mengirim kue ke teman di kota lain. Kalau Anda cuma kirim resepnya, hasilnya bisa beda — tergantung oven, bahan, dan cara teman Anda masak. Tapi kalau Anda kirim **kue yang sudah jadi, dikemas rapi dalam kotak**, teman Anda tinggal buka kotaknya — rasanya pasti sama persis dengan yang Anda buat.

**Docker bekerja seperti kotak kue itu.** Docker adalah tool yang membungkus sebuah aplikasi **beserta semua yang dibutuhkannya untuk berjalan** (kode program, dependency, pengaturan, versi software tertentu) ke dalam satu paket yang disebut **container**. Container ini bisa dijalankan di laptop mana pun — Mac, Windows, Linux, server di cloud — dan akan berperilaku **persis sama**, karena semua yang dibutuhkan sudah ada di dalam paketnya, tidak bergantung pada apa yang sudah/belum terinstall di komputer tersebut.

**Istilah-istilah dasar yang perlu diketahui:**

| Istilah | Penjelasan Sederhana |
|---|---|
| **Image** | "Resep" atau cetakan — file yang berisi definisi lengkap sebuah aplikasi + semua kebutuhannya. Belum berjalan, baru blueprint. Contoh: `ollama/ollama`, `python:3.11-slim`. |
| **Container** | Image yang **sedang dijalankan** — seperti kue yang sudah dikeluarkan dari kotak dan siap dimakan. Satu image bisa dijalankan jadi banyak container sekaligus. |
| **Docker Hub** | "Toko" tempat image-image siap pakai disimpan dan diunduh (mirip App Store, tapi untuk image aplikasi). Saat Anda menulis `image: ollama/ollama`, Docker otomatis mengunduhnya dari sini kalau belum ada di komputer Anda. |
| **Dockerfile** | Resep untuk **membuat image Anda sendiri** dari nol (misalnya image khusus untuk aplikasi NALA) — beda dengan mengunduh image jadi dari Docker Hub. |

**Kenapa ini penting untuk NALA:** tanpa Docker, kita masing-masing harus install Python versi tertentu, Ollama, dan berbagai dependency secara manual di laptop sendiri — rawan beda versi, beda hasil, beda error. Dengan Docker, cukup jalankan satu perintah, dan environment yang didapat **persis sama** di laptop siapa pun.

> 💡 Docker Compose (section berikutnya) adalah lapisan di atas Docker — kalau Docker mengurus **satu** container, Docker Compose mengurus **banyak** container (Ollama, FastAPI, nanti OpenSearch, PostgreSQL, dst) sekaligus, supaya semuanya bisa dinyalakan bersama dengan satu perintah.

---

## 2. Kenapa Docker Compose

Bayangkan Anda memiliki aplikasi NALA yang membutuhkan beberapa service untuk berjalan: Ollama (LLM lokal), FastAPI app (backend), OpenSearch (vector store, lalu hybrid search), Airflow (orchestration), dan lainnya. Tanpa Docker Compose, kita masing-masing harus:

1. **Install manual** setiap service dengan versi yang berbeda
2. **Configure** port dan environment variable untuk setiap service
3. **Jalankan satu per satu** dengan command yang berbeda di multiple terminal
4. **Debug** masalah kompatibilitas antar service

Hasilnya: **"It works on my machine"** problem — kode berjalan di laptop Anda tapi tidak di laptop peserta lain.

**Docker Compose memecahkan masalah ini:**

**Definisi Sederhana:**
Docker Compose adalah tool yang memungkinkan Anda mendefinisikan **multiple Docker containers** (containers adalah seperti "kotak virtual" yang berisi aplikasi + dependensi) dalam satu file YAML, lalu menjalankan semuanya dengan **satu command**.

**Keuntungan menggunakan Docker Compose untuk NALA:**

| Keuntungan | Penjelasan |
|---|---|
| **Konsistensi di semua device** | Kita semua menjalankan environment yang 100% sama; tidak ada lagi "works on my machine" |
| **Eliminasi instalasi manual** | Tidak perlu install Ollama, FastAPI, PostgreSQL, dsb. satu per satu; Docker Compose handle semuanya |
| **Single command untuk start/stop** | `docker-compose up` untuk start semua, `docker-compose down` untuk stop semua |
| **Port & networking otomatis** | Tidak perlu config port 8000, 5432, 6379 manual; Docker Compose setup secara otomatis |
| **Volume & data persistence** | Data dari database tidak hilang saat container di-stop; storage di-mount ke host |
| **Isolated environments** | Setiap developer memiliki environment terisolasi; tidak ada konfliks global |
| **Dokumentasi via code** | docker-compose.yml adalah dokumentasi lengkap tentang infra yang diperlukan |

**Analogi versi non-teknis:**
Jika aplikasi NALA adalah "restoran", maka Docker Compose adalah "blueprint" restoran yang menunjukkan di mana dapur, di mana kasir, di mana meja pelanggan. Blueprint ini bisa di-copy ke lokasi lain dan restoran akan berjalan dengan cara yang sama.

---

## 3. Anatomi docker-compose.yml

File `docker-compose.yml` adalah file konfigurasi YAML yang mendefinisikan semua service (containers) yang aplikasi Anda butuhkan, beserta setting mereka. File ini akan disimpan di `resources/starter-code/day-1/nala/docker-compose.yml`.

### 3.1 Struktur Dasar

Berikut adalah struktur umum docker-compose.yml:

```yaml
services:       # Mulai definisi service
  service-name-1:
    image: nama-image:tag
    ports:
      - "host-port:container-port"
    volumes:
      - /path/on/host:/path/in/container
    environment:
      - ENV_VAR_NAME=value
    depends_on:
      - other-service

  service-name-2:
    image: nama-image:tag
    ports:
      - "host-port:container-port"
```

### 3.2 Penjelasan Setiap Key

**`services`**
- Daftar semua container yang akan dijalankan
- Setiap service didefinisikan dengan nama unik (misalnya `ollama`, `api`, `postgres`)

**`image`** (dalam setiap service)
- Nama Docker image yang akan dijalankan
- Format: `nama-image:tag` (contoh: `ollama:latest`, `postgres:15`, `python:3.11`)
- Docker akan download image dari Docker Hub jika belum ada di local machine

**`ports`**
- Mapping port dari host (laptop Anda) ke dalam container
- Format: `"host-port:container-port"`
- Contoh: `"8000:8000"` artinya port 8000 di laptop → port 8000 dalam container
- Saat app dijalankan, Anda akses via `http://localhost:8000`

**`volumes`**
- Mounting folder/file dari host ke dalam container
- Format: `"/path/on/host:/path/in/container"`
- Gunakan untuk:
  - Menyimpan data database sehingga tidak hilang saat container stop
  - Sharing code dari host ke container untuk development
- Contoh:
  ```yaml
  volumes:
    - ./app:/workspace/app          # Folder `app` di host → `/workspace/app` di container
    - postgres-data:/var/lib/postgresql/data  # Named volume untuk data persistence
  ```

**`environment`** (dalam setiap service)
- Variabel environment yang diset di dalam container
- Contoh:
  ```yaml
  environment:
    - OLLAMA_MODEL=llama3.2:3b
    - FASTAPI_PORT=8000
    - DATABASE_URL=postgresql://user:password@postgres:5432/nala_db
  ```
- Service bisa akses variabel ini via `os.environ['OLLAMA_MODEL']` dalam kode

**`depends_on`**
- Menentukan service lain yang harus start terlebih dahulu
- Contoh: FastAPI app depends on Ollama, jadi Ollama start duluan
- Syntax:
  ```yaml
  depends_on:
    - ollama
    - postgres
  ```

### 3.3 Contoh Konkret untuk NALA — Mulai dari Ollama Saja

Docker itu sendiri konsep baru, Ollama-di-dalam-container juga baru, dan FastAPI-di-dalam-container juga baru — kalau ketiganya dinyalakan bersamaan lewat satu `docker compose up` dan ada yang error, sulit menebak biang keladinya yang mana. Karena itu `docker-compose.yml` NALA dibangun **bertahap**: dulu cuma service `ollama` sendirian, dipastikan jalan, baru service `api` ditambahkan (section 5).

Berikut isi `docker-compose.yml` di tahap pertama ini (`resources/starter-code/day-1/nala/docker-compose.yml`) — baru berisi satu service:

```yaml
services:
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama

volumes:
  ollama_data:
```

**Penjelasan:**
- **`ollama` service**: Menjalankan Ollama di port 11434 (image `ollama/ollama` sudah otomatis menjalankan `ollama serve`, jadi tidak perlu `command` tambahan); model disimpan di volume `ollama_data` agar tidak hilang saat container di-stop
- **Belum ada `api`, `build`, `depends_on`, atau `environment`** — itu semua baru relevan begitu ada service kedua untuk dihubungkan. Untuk sekarang, cukup satu service, satu image resmi dari Docker Hub, tidak ada kode custom sama sekali.

### 3.4 Coba Duluan: Jalankan & Verifikasi Ollama di Docker

Sebelum menulis satu baris kode FastAPI, pastikan dulu fondasinya — Ollama di dalam container — benar-benar menyala dan bisa dipakai. Ini juga latihan yang lebih murni untuk memahami perintah Docker Compose dasar (section 3.5), tanpa harus sekaligus mikirin kode Python.

**Langkah A — Nyalakan service `ollama` saja:**

```bash
cd resources/starter-code/day-1/nala
docker compose up -d ollama
```

`-d` (*detached*) menjalankan container di background, supaya terminal Anda bebas dipakai untuk perintah lain.

**Langkah B — Cek container benar-benar hidup:**

```bash
docker compose ps
```
Status `ollama` harus `running` (atau `Up`), bukan `Exited`/`Restarting`.

**Langkah C — Pull model ke dalam container:**

Ollama yang berjalan **di dalam container** punya storage terpisah dari Ollama yang mungkin sudah Anda install langsung di laptop (Module 2) — modelnya perlu di-pull lagi khusus untuk container ini:

```bash
docker compose exec ollama ollama pull llama3.2:3b
```

**Langkah D — Verifikasi model & API Ollama merespons:**

```bash
docker compose exec ollama ollama list
curl http://localhost:11434/api/tags
```

`llama3.2:3b` harus muncul di kedua output — yang pertama dari dalam container (`ollama list`), yang kedua dari **luar** container, lewat port `11434` yang sudah di-mapping ke laptop Anda.

✅ **Checkpoint sebelum lanjut**: `docker compose ps` menunjukkan `ollama` running, `ollama list` di dalam container menampilkan `llama3.2:3b`, dan `curl http://localhost:11434/api/tags` dari luar container juga berhasil. Kalau salah satu belum terpenuhi, selesaikan dulu di sini — menambah service `api` di atas fondasi Ollama yang belum stabil cuma akan mempersulit debugging nanti.

Biarkan container `ollama` tetap berjalan (tidak perlu `docker compose down`) — section 5 menambahkan service `api` ke `docker-compose.yml` yang sama, dan `docker compose up --build` nanti akan menyalakan `api` sekaligus tetap memakai `ollama` yang sudah berjalan ini.

### 3.5 Command Dasar Docker Compose

Setelah docker-compose.yml siap, gunakan command ini:

```bash
# Start semua service
docker-compose up

# Start di background
docker-compose up -d

# Stop semua service
docker-compose down

# Lihat logs dari semua service
docker-compose logs -f

# Lihat logs dari service tertentu
docker-compose logs -f api

# Rebuild images
docker-compose build

# Jalankan command di dalam container
docker-compose exec api bash
```

---

## 4. Arsitektur Project NALA — Pertumbuhan Bertahap

Selama program training (27 modul), sistem NALA akan berkembang dari simple hingga full-featured. Berikut diagram yang menunjukkan service apa yang ditambahkan di tiap kelompok modul:

```mermaid
graph TD
    subgraph Stage1["Module 1-4: Foundation"]
        Ollama1["Ollama<br/>(LLM lokal)"]
        FastAPI1["FastAPI App<br/>(API Gateway)"]
        Ollama1 <-->|Inference Request| FastAPI1
    end
    
    subgraph Stage2["Module 5-14: Data & Orchestration"]
        Ollama2["Ollama"]
        FastAPI2["FastAPI App"]
        VectorDB["OpenSearch<br/>(vector store)"]
        Airflow["Airflow<br/>(Workflow Engine)"]
        Ollama2 <-->|Inference| FastAPI2
        FastAPI2 <-->|Store/Retrieve Embeddings| VectorDB
        Airflow -->|Orchestrate Tasks| FastAPI2
    end
    
    subgraph Stage3["Module 15-18: Monitoring & Search"]
        Ollama3["Ollama"]
        FastAPI3["FastAPI App"]
        Airflow3["Airflow"]
        OpenSearch["OpenSearch<br/>(hybrid: BM25 + vector)"]
        Langfuse["Langfuse<br/>(LLM Monitoring)"]
        Ollama3 <-->|Inference| FastAPI3
        FastAPI3 <-->|Hybrid Search: BM25 + Vector| OpenSearch
        Langfuse -->|Monitor Traces| FastAPI3
        Airflow3 -->|Orchestrate| FastAPI3
    end
    
    subgraph Stage4["Module 19-23: Stateful App & Agents"]
        Ollama4["Ollama"]
        FastAPI4["FastAPI App"]
        Airflow4["Airflow"]
        OpenSearch4["OpenSearch<br/>(hybrid: BM25 + vector)"]
        Langfuse4["Langfuse"]
        PostgreSQL["PostgreSQL<br/>(Data Operasional: Pengajuan Kredit, Klaim — diakses SQL Agent Tool)"]
        LangGraph["LangGraph Agent<br/>(Agentic Logic)"]
        Ollama4 <-->|Inference| FastAPI4
        FastAPI4 <-->|Hybrid Search| OpenSearch4
        FastAPI4 <-->|State/Data| PostgreSQL
        LangGraph -->|Agentic Decisions| FastAPI4
        Langfuse4 -->|Traces| FastAPI4
        Airflow4 -->|Orchestrate| FastAPI4
    end
    
    subgraph Stage5["Module 24-27: Full Integration"]
        Ollama5["Ollama"]
        FastAPI5["FastAPI App"]
        Airflow5["Airflow"]
        OpenSearch5["OpenSearch<br/>(hybrid: BM25 + vector)"]
        Langfuse5["Langfuse"]
        PostgreSQL5["PostgreSQL"]
        LangGraph5["LangGraph Agent"]
        Client["Client Apps<br/>(Web/Mobile/CLI)"]
        
        Ollama5 <-->|Inference| FastAPI5
        FastAPI5 <-->|Hybrid Search| OpenSearch5
        FastAPI5 <-->|Persistent State| PostgreSQL5
        LangGraph5 -->|Intelligent Routing| FastAPI5
        Langfuse5 -->|Observability| FastAPI5
        Airflow5 -->|Background Jobs| FastAPI5
        Client -->|REST API| FastAPI5
    end
    
    Stage1 -->|Build on| Stage2
    Stage2 -->|Add Features| Stage3
    Stage3 -->|Empower Agents| Stage4
    Stage4 -->|Integrate All| Stage5
```

**Penjelasan Diagram:**

- **Module 1-4**: Fondasi sederhana — Ollama (LLM) + FastAPI (API gateway)
- **Module 5-14**: Tambah OpenSearch sebagai vector store untuk storage embedding + Airflow untuk orchestration
- **Module 15-18**: Upgrade OpenSearch menjadi hybrid search (BM25 + vector) + Langfuse untuk monitoring LLM traces
- **Module 19-23**: Tambah PostgreSQL untuk data operasional (pengajuan kredit, klaim) yang diakses SQL agent tool + LangGraph untuk agentic reasoning
- **Module 24-27**: Semuanya terintegrasi dengan sempurna; ready untuk production atau extended use cases

---

## 5. Konsep Dasar FastAPI

FastAPI adalah framework Python modern untuk membangun API (Application Programming Interface). API adalah "pintu masuk" untuk aplikasi lain berkomunikasi dengan sistem Anda. Mari kita pahami FastAPI dari dua perspektif: **non-teknis** dan **teknis**.

### 5.1 Penjelasan Non-Teknis

**Bayangan Sederhana:**
Jika NALA adalah "asisten AI", maka FastAPI adalah "resepsionis" yang menerima pertanyaan dari klien (user, aplikasi lain, website) dan melempar pertanyaan tersebut ke asisten. Setelah asisten menjawab, resepsionis mengirim jawaban kembali ke klien.

**Alur Komunikasi (Non-teknis):**
1. **Klien mengirim pertanyaan**: "Halo NALA, apa itu machine learning?"
2. **FastAPI (resepsionis) menerima**: Catat pertanyaan, validasi format
3. **FastAPI melempar ke Ollama**: "Ollama, tolong jawab pertanyaan ini"
4. **Ollama (asisten AI) menjawab**: "Machine learning adalah..."
5. **FastAPI mengirim jawaban kembali**: Resepsionis memberikan jawaban ke klien

**Keuntungan FastAPI untuk NALA:**
- **Cepat**: Salah satu framework tercepat di Python (comparable dengan Node.js)
- **Mudah**: Syntax clean dan intuitive; cocok untuk learners
- **Automatic documentation**: FastAPI auto-generate dokumentasi interaktif (Swagger UI)
- **Type safety**: Validasi input otomatis dengan Python type hints
- **Async-ready**: Support concurrent requests (banyak user sekaligus)

### 5.2 Penjelasan Teknis

#### 5.2.1 Struktur Dasar FastAPI, Bertahap

Daripada langsung ditunjukkan kode lengkap, mari bangun aplikasi FastAPI **secara bertahap dalam 3 tahap besar** — tiap tahap menambah satu kemampuan baru di atas tahap sebelumnya, dan bisa langsung dites sebelum lanjut ke tahap berikutnya:

1. **Tahap A — FastAPI saja**, belum tersambung ke Ollama sama sekali. Fokus: memahami `app`, endpoint, dan Pydantic model murni sebagai konsep HTTP API.
2. **Tahap B — Hubungkan ke Ollama**, pakai system prompt generik dulu (misal "Kamu adalah asisten AI"). Fokus: memahami cara FastAPI memanggil layanan lain (Ollama) dan meneruskan hasilnya sebagai response.
3. **Tahap C — Integrasikan system prompt NALA**, mengganti prompt generik dengan `NALA_SYSTEM_PROMPT` hasil latihan Module 3. Fokus: bagaimana satu baris konfigurasi (system prompt) mengubah kepribadian & batasan asisten, tanpa mengubah struktur endpoint sama sekali.

**Target akhirnya tetap satu file yang sama: `resources/starter-code/day-1/nala/app/main.py`.** File ini sudah tersedia lengkap di starter code (sebagai referensi/jawaban) — ikuti Langkah 1-7 berikut untuk menulis ulang isinya sendiri bertahap sesuai 3 tahap di atas, lalu cocokkan hasil akhirnya di Langkah 7.

### Tahap A — FastAPI saja (belum ada Ollama)

**Langkah 1 — Buat aplikasi paling minimal**

1. Buka folder `resources/starter-code/day-1/nala/app/`.
2. Buat (atau buka) file `main.py`.
3. Tulis dua baris ini sebagai isi paling awal:

```python
from fastapi import FastAPI

app = FastAPI()
```

Apa yang sebenarnya terjadi di dua baris ini?

- **`from fastapi import FastAPI`**: mengambil *class* `FastAPI` dari library FastAPI yang sudah di-install.
- **`app = FastAPI()`**: memanggil class tersebut untuk membuat satu **instance** (objek nyata) dari `FastAPI`, lalu menyimpannya ke variabel bernama `app`.

Kenapa butuh instance, bukan langsung pakai class-nya? Karena `app` inilah yang nanti jadi "wadah pusat" tempat semua endpoint didaftarkan (lihat Langkah 2), dan `app` juga yang nanti dirujuk oleh server saat menjalankan aplikasi (`uvicorn main:app` — dibahas di 5.2.6 — kata `app` di situ merujuk persis ke variabel ini). Nama variabelnya **harus** `app` (atau nama lain yang konsisten dipakai saat menjalankan server) — bukan aturan Python, tapi konvensi yang dipakai FastAPI/uvicorn untuk saling menemukan.

Baru dua baris, belum ada endpoint apa pun — tapi ini sudah aplikasi FastAPI yang valid. Di file asli `app/main.py`, baris ini ditulis sedikit lebih lengkap: `app = FastAPI(title="NALA")` — `title` dipakai untuk mempercantik dokumentasi otomatis (Swagger UI, lihat 5.2.6), tapi konsepnya sama persis. Boleh dulu tulis `FastAPI()` polos, nanti ditambah `title` di Langkah 6.

**▶️ Jalankan & lihat hasilnya**

Sampai sini `main.py` belum butuh Ollama sama sekali, jadi belum perlu Docker — cukup `uvicorn` lokal:

```bash
cd resources/starter-code/day-1/nala
pip install fastapi uvicorn
uvicorn app.main:app --reload
```

Buka `http://127.0.0.1:8000` di browser. Yang muncul: `{"detail":"Not Found"}`. Ini **bukan error** — ini bukti nyata: servernya sudah menyala, tapi belum ada "pintu" (endpoint) yang didaftarkan ke `app`. Biarkan `uvicorn` tetap jalan (jangan `Ctrl+C` dulu — `--reload` akan otomatis membaca ulang file setiap kali disimpan), lanjut ke Langkah 2.

**Langkah 2 — Tambah satu endpoint paling sederhana**

Endpoint adalah "pintu" yang bisa diakses dari luar. Di file `main.py` yang sama, tambahkan endpoint paling sederhana: cek status.

1. Di bawah baris `app = FastAPI()`, tambahkan:

```python
@app.get("/health")
def health_check():
    return {"status": "ok"}
```

2. Simpan file.

- **`@app.get("/health")`**: ini disebut *decorator* — cara FastAPI tahu "kalau ada yang akses path `/health` dengan method GET, jalankan fungsi di bawah ini".
- **`def health_check(): return {"status": "ok"}`**: fungsi biasa, mengembalikan dictionary Python — FastAPI otomatis mengubahnya jadi JSON.

**▶️ Jalankan & lihat hasilnya**

Karena `uvicorn --reload` masih jalan dari Langkah 1, file otomatis ke-reload begitu disimpan (lihat log terminal: `Reloading...`). Buka terminal baru, lalu:

```bash
curl http://127.0.0.1:8000/health
```

Harus muncul `{"status":"ok"}` — beda dari `{"detail":"Not Found"}` di Langkah 1, karena sekarang `/health` sudah terdaftar. Sengaja belum ada endpoint `/chat` — itu langkah berikutnya, karena `/chat` butuh konsep tambahan: data yang dikirim *dari* klien (bukan cuma dikembalikan *ke* klien).

**Langkah 3 — Definisikan bentuk data yang diharapkan (Pydantic)**

Endpoint `/health` tadi gampang — dia tidak butuh apa-apa dari orang yang mengaksesnya, cuma dipanggil lalu jawab "ok". Tapi `/chat` beda: NALA perlu tahu dulu **apa pertanyaan** yang mau ditanyakan user. Di sinilah **Pydantic** dipakai — library Python untuk mendefinisikan "bentuk data yang wajib dipenuhi".

**Bayangkan begini:** sebelum kotak saran boleh diisi orang, biasanya disediakan dulu selembar formulir kosong, bukan kertas polos. Formulirnya sudah ada kolom bertuliskan "Pertanyaan Anda: ___________". Siapa pun yang mau bertanya, **wajib** isi kolom itu — tidak bisa kirim kertas kosong atau coret-coretan bebas. Pydantic itu fungsinya persis seperti formulir ini, tapi ditulis dalam kode.

Masih di file `main.py` yang sama:

1. Di baris paling atas file, tambahkan import Pydantic: `from pydantic import BaseModel`
2. Di bawah `app = FastAPI()` (sebelum endpoint `/health`), tambahkan:

```python
class ChatRequest(BaseModel):
    message: str
```

Cara bacanya: **`ChatRequest`** ini nama "formulir"-nya (bebas dinamai apa saja, tapi dikasih nama yang menjelaskan isinya — "permintaan chat"). Di dalamnya cuma ada satu baris, `message: str` — artinya formulir ini punya **satu kolom wajib** bernama `message`, dan isinya **harus** berupa teks (`str`, singkatan dari *string*). Kalau nanti ada yang kirim data tanpa kolom `message`, atau isi `message` dengan angka, FastAPI akan **otomatis menolak** duluan sebelum kode Anda sempat dijalankan — Anda tidak perlu repot menulis pengecekan manual sendiri.

Perhatikan: sejauh ini baru **bikin formulirnya saja**. Belum ditempel ke pintu (endpoint) mana pun — itu baru terjadi nanti di Langkah 5.

**▶️ Jalankan & lihat hasilnya**

Simpan file, biarkan `uvicorn` reload. Belum ada endpoint baru yang memakai `ChatRequest`, jadi belum ada hal baru untuk di-`curl` — cukup pastikan **tidak ada error** di log terminal `uvicorn` (kalau ada salah ketik/indentasi, errornya akan langsung terlihat di sana). `curl http://127.0.0.1:8000/health` masih harus tetap `{"status":"ok"}` seperti Langkah 2, tanda file masih valid.

**Langkah 4 — Definisikan juga bentuk data yang dikembalikan**

Kalau Langkah 3 tadi formulir **untuk pertanyaan yang masuk**, Langkah 4 ini formulir **untuk jawaban yang keluar** — semacam "struk balasan" yang dikembalikan NALA ke user. Tambahkan tepat di bawah `ChatRequest`:

```python
class ChatResponse(BaseModel):
    reply: str
```

Polanya sama persis seperti Langkah 3: nama "formulir"-nya `ChatResponse`, dan cuma ada satu kolom wajib, `reply` (isinya teks) — ini yang nanti diisi jawaban NALA. Sekarang ada dua "formulir": `ChatRequest` (apa yang **masuk**, dari user) dan `ChatResponse` (apa yang **keluar**, dari NALA). Keduanya masih murni Pydantic — belum tersambung ke Ollama sama sekali, baru "cetakan"-nya saja.

**▶️ Jalankan & lihat hasilnya**

Sama seperti Langkah 3 — simpan, cek log `uvicorn` tidak error, `curl .../health` masih `{"status":"ok"}`. Setelah ini, `Ctrl+C` di terminal `uvicorn` untuk berhenti — mulai Langkah 5, cara menjalankannya berpindah ke Docker.

**📄 Kode lengkap Tahap A** (murni FastAPI, belum ada Ollama sama sekali):

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


@app.get("/health")
def health_check():
    return {"status": "ok"}
```

Perhatikan: `ChatRequest` dan `ChatResponse` sudah ada, tapi **belum dipakai di endpoint mana pun** — belum ada `/chat`. Itu jugalah kenapa file ini masih bisa jalan hanya dengan `uvicorn`, tanpa Docker/Ollama sama sekali.

⚠️ **Kenapa pindah ke Docker mulai Langkah 5:** `/chat` akan memanggil Ollama, dan Ollama di sini jalan sebagai **container terpisah** (service `ollama` di `docker-compose.yml`) — bukan proses yang bisa diakses `uvicorn` lokal. `docker compose up --build` di Langkah 5 akan **build image** service `api` dari `Dockerfile` (isinya persis `main.py` Anda + dependency di `requirements.txt`) dan menyambungkannya ke `ollama` lewat `docker-compose.yml` (`OLLAMA_BASE_URL=http://ollama:11434`).

### Tahap B — Hubungkan ke Ollama (system prompt generik dulu)

FastAPI-nya sudah siap (Tahap A). Ollama sendiri sudah dinyalakan & diverifikasi jalan di Docker sejak section 3.4 — kalau belum, selesaikan dulu di sana sebelum lanjut. Sekarang keduanya disambungkan lewat `docker-compose.yml`.

**Langkah 4.5 — Tambahkan service `api` ke `docker-compose.yml`**

Buka `docker-compose.yml`, tambahkan blok `api` di samping `ollama`:

```yaml
services:
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama

  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434
      - OLLAMA_MODEL=llama3.2:3b
    depends_on:
      - ollama

volumes:
  ollama_data:
```

**Penjelasan blok `api`:**
- **`build: .`** — beda dari `ollama` yang pakai `image:` (image jadi dari Docker Hub), `api` di-**build** dari `Dockerfile` lokal (dibahas sekilas di section 1) — sehingga dependency Python (FastAPI, `httpx`, dll di `requirements.txt`) ter-install ke dalam image custom ini.
- **`environment: OLLAMA_BASE_URL=http://ollama:11434`** — perhatikan host-nya `ollama`, **bukan** `localhost`. Di dalam jaringan internal Docker Compose, tiap service bisa saling memanggil pakai **nama service**-nya sebagai hostname — `api` memanggil `ollama` lewat nama itu, bukan lewat `localhost:11434` seperti kalau Anda mengetes dari laptop langsung (section 3.4 Langkah D).
- **`depends_on: - ollama`** — memberi tahu Docker Compose untuk menyalakan `ollama` **lebih dulu** sebelum `api`. Ini cuma menjamin urutan start container, **bukan** menjamin Ollama sudah selesai loading model saat `api` mulai menerima request — itu sebabnya Ollama diverifikasi sehat dulu secara terpisah di section 3.4, bukan diandalkan ke `depends_on` saja.

Untuk "menghubungi" Ollama dari kode Python, dibutuhkan beberapa file tambahan:

1. `app/ollama_client.py` — isinya class `OllamaClient` (menggunakan library `httpx` untuk memanggil API Ollama lewat HTTP).
2. `app/__init__.py` — file kosong (0 baris), tapi keberadaannya wajib: ini yang membuat Python mengenali folder `app/` sebagai *package*, supaya `from app.ollama_client import ...` bisa jalan.

**Pre-flight check**

- [ ] `app/__init__.py` ada (boleh kosong, 0 baris)
- [ ] `app/ollama_client.py` ada

```bash
ls app/
```

> ⚠️ **Kalau `ollama_client.py` tidak ada** (pernah terjadi kalau folder `app/` di-duplikat lewat Finder/VS Code — "duplicate" kadang memindah, bukan menyalin), buat manual dengan isi berikut:
> ```python
> # app/ollama_client.py
> import httpx
>
>
> class OllamaClient:
>     def __init__(self, base_url: str, model: str):
>         self.base_url = base_url
>         self.model = model
>
>     def generate(self, system_prompt: str, user_message: str) -> str:
>         with httpx.Client() as client:
>             response = client.post(
>                 f"{self.base_url}/api/generate",
>                 json={
>                     "model": self.model,
>                     "system": system_prompt,
>                     "prompt": user_message,
>                     "stream": False,
>                 },
>                 timeout=60.0,
>             )
>             response.raise_for_status()
>             return response.json()["response"]
> ```
> **Penjelasan Singkat**
> - **`__init__(self, base_url, model)`**: ini *constructor* — kode yang otomatis jalan sekali, tepat saat `OllamaClient(...)` dipanggil (lihat Langkah 5, `ollama_client = OllamaClient(...)`). Tugasnya cuma menyimpan `base_url` (alamat server Ollama, misal `http://ollama:11434`) dan `model` (nama model, misal `llama3.2:3b`) ke dalam objeknya sendiri (`self.base_url`, `self.model`), supaya nanti bisa dipakai lagi di method lain — tanpa perlu diketik ulang tiap kali.
> - **`generate(self, system_prompt, user_message)`**: ini method yang **benar-benar mengirim pertanyaan ke Ollama** dan menunggu jawabannya. Alurnya: (1) susun request HTTP `POST` ke `{base_url}/api/generate` — endpoint bawaan Ollama — berisi `model`, `system` (system prompt), dan `prompt` (pertanyaan user); (2) `response.raise_for_status()` melempar error kalau Ollama merespons gagal (misal model belum di-pull); (3) `response.json()["response"]` mengambil teks jawabannya saja dari balasan Ollama, lalu dikembalikan sebagai string biasa. Inilah yang dipanggil `main.py` lewat `ollama_client.generate(system_prompt=..., user_message=...)` di Langkah 5.
>
> Kalau `__init__.py` juga tidak ada, buat file kosong dengan nama itu — tanpa file ini, `from app.ollama_client import ...` gagal dengan `ModuleNotFoundError: No module named 'app.ollama_client'` (persis error kalau `ollama_client.py` sendiri yang hilang). Error yang sama padahal kedua file sudah ada → cek `python3 -m pip show httpx`.

> ⚠️ **Kalau muncul `ModuleNotFoundError: No module named 'httpx'` saat Anda coba jalankan dengan `uvicorn` lokal**: itu tandanya `httpx` belum ter-install di Python lokal Anda — wajar, karena `httpx` cuma otomatis ter-install **di dalam container** lewat `requirements.txt`, bukan di komputer Anda langsung. Kalau sekadar mau membetulkan error importnya: `python3 -m pip install httpx` (atau `pip3 install httpx`). Tapi ingat: **mulai Tahap B ini seharusnya dijalankan pakai `docker compose up --build`, bukan `uvicorn` lokal** — walau error `httpx` sudah beres, `uvicorn` lokal tetap akan gagal manggil `/chat` karena tidak ada Ollama yang bisa dihubungi di `http://localhost:11434` dari luar container.

**Langkah 5 — Tambahkan koneksi ke Ollama dengan system prompt generik**

1. Tambah import di baris atas: `import os` dan `from app.ollama_client import OllamaClient`.
2. Buat instance-nya di bawah `app = FastAPI()`:
   ```python
   ollama_client = OllamaClient(
       base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
       model=os.environ.get("OLLAMA_MODEL", "llama3.2:3b"),
   )
   ```
3. Tambahkan endpoint `/chat`, memakai dua model dari Langkah 3-4, dengan system prompt **generik dulu** (bukan `NALA_SYSTEM_PROMPT` — itu Tahap C):
   ```python
   @app.post("/chat", response_model=ChatResponse)
   def chat(request: ChatRequest) -> ChatResponse:
       reply = ollama_client.generate(
           system_prompt="Kamu adalah asisten AI yang menjawab singkat dan jelas.",
           user_message=request.message,
       )
       return ChatResponse(reply=reply)
   ```

**Penjelasan Singkat**

- **`@app.post("/chat", ...)`**: beda dari `/health` (GET) — **POST**, karena klien mengirim data, bukan cuma menerima.
- **`request: ChatRequest`**: FastAPI otomatis baca JSON masuk & validasi sesuai `ChatRequest` (Langkah 3); data salah bentuk otomatis ditolak sebelum masuk fungsi.
- **`ollama_client.generate(...)`**: titik hubung FastAPI ↔ Ollama — mengirim request, menunggu jawaban.
- **`ChatResponse(reply=reply)`**: dibungkus balik jadi JSON sesuai `ChatResponse` (Langkah 4).

**Jalankan**

Simpan file. Mulai dari sini pakai Docker (bukan `uvicorn` lagi):

```bash
cd resources/starter-code/day-1/nala
docker compose up --build
```

Docker Compose cukup pintar untuk tidak membuat ulang container yang sudah berjalan dan tidak berubah konfigurasinya — `ollama` (sudah menyala sejak section 3.4) langsung dipakai apa adanya, yang benar-benar di-*build* dan dinyalakan di sini cuma `api`. Kalau log menunjukkan `ollama` langsung "Up" tanpa proses pull image, itu perilaku normal, bukan error.

**Output yang Diharapkan**
```
... Uvicorn running on http://0.0.0.0:8000
```

Model `llama3.2:3b` **tidak perlu** di-pull ulang di sini — sudah dilakukan di section 3.4 Langkah C, dan tersimpan permanen di volume `ollama_data` selama volume itu tidak dihapus. Kalau ingin memastikan, cek lagi:
```bash
docker compose exec ollama ollama list
```

Tes kedua endpoint:
```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Halo, kamu siapa?"}'
```

✅ **Indikator sukses**: `/health` → `{"status":"ok"}`. `/chat` → jawaban **generik** ("saya asisten AI..."), belum berkarakter NALA — wajar, system prompt-nya masih placeholder. Biarkan `docker compose up` tetap berjalan, lanjut ke Langkah 6.

**Kapan pakai command Docker yang mana**

Mulai sini sampai akhir Tahap C, Anda akan bolak-balik edit kode lalu perlu menjalankannya lagi. Command yang dipakai **beda-beda tergantung apa yang diubah**:

| Situasi | Command | Kenapa |
|---|---|---|
| Ubah isi `main.py`, `system_prompt.py`, atau file lain di `app/` | `docker compose up --build api` | `docker-compose.yml` **tidak** me-mount folder `app/` ke dalam container — kode di-`COPY` ke image cuma sekali saat `build` (lihat `Dockerfile`). `restart` cuma menyalakan ulang container dari image yang sama persis, jadi kode lama yang tetap terpakai. Rebuild ini **cepat** (beberapa detik) karena layer `pip install` di-cache — cuma langkah `COPY app ./app` yang diulang. |
| Ubah `requirements.txt` atau `Dockerfile` | `docker compose up --build api` | Command sama persis seperti di atas — bedanya cuma rebuild-nya **lebih lambat**, karena layer `pip install` ikut di-*invalidate* dan harus jalan ulang, bukan cuma layer `COPY app`. |
| Mau berhenti sepenuhnya (tutup laptop, selesai sesi latihan) | `docker compose down` | Mematikan **dan menghapus** container (bukan cuma pause) — port `8000`/`11434` jadi bebas lagi. Model Ollama yang sudah di-*pull* **tidak ikut hilang** (tersimpan di volume `ollama_data`, lihat `docker-compose.yml`). |
| Mau lanjut lagi setelah `down`, tidak ada perubahan kode sejak terakhir | `docker compose up` (tanpa `--build`) | Image sebelumnya masih ada dan masih sesuai kode terakhir, tidak perlu dibangun ulang dari nol — lebih cepat. |
| Container `api` error/nyangkut, tidak jelas kenapa | `docker compose down` lalu `docker compose up --build` | "Matikan total, nyalakan dari nol" — cara paling ampuh membersihkan state yang aneh. |

> 💡 **Aturan cepat**: `restart` **tidak pernah cukup** untuk perubahan kode apa pun di setup ini — selalu `docker compose up --build api` setiap kali file di `app/`, `requirements.txt`, atau `Dockerfile` berubah. Satu-satunya yang berbeda adalah kecepatannya (detik vs lebih lama), bukan apakah `--build`-nya perlu atau tidak.

**📄 Kode lengkap Tahap B** (sudah tersambung ke Ollama, system prompt masih generik):

```python
import os

from fastapi import FastAPI
from pydantic import BaseModel

from app.ollama_client import OllamaClient

app = FastAPI()

ollama_client = OllamaClient(
    base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
    model=os.environ.get("OLLAMA_MODEL", "llama3.2:3b"),
)


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    reply = ollama_client.generate(
        system_prompt="Kamu adalah asisten AI yang menjawab singkat dan jelas.",
        user_message=request.message,
    )
    return ChatResponse(reply=reply)
```

Dibandingkan **Kode lengkap Tahap A**, yang berubah cuma 3 hal: (1) tambah `import os` dan `from app.ollama_client import OllamaClient`, (2) tambah baris `ollama_client = OllamaClient(...)`, dan (3) endpoint `/chat` sekarang benar-benar terisi (sebelumnya cuma "cetakan" `ChatRequest`/`ChatResponse` yang belum dipakai).

### Tahap C — Integrasikan system prompt NALA

**Langkah 6 — Ganti system prompt generik dengan `NALA_SYSTEM_PROMPT`**

Di Langkah 5, asisten AI-nya sudah tersambung, tapi "kepribadiannya" masih generik — cuma dibisiki "kamu asisten AI yang menjawab singkat dan jelas". **System prompt** itu ibarat **briefing** yang diberikan ke asisten sebelum dia mulai kerja: siapa dia, tugasnya apa, batasannya apa. Sekarang briefing generik itu diganti dengan briefing yang sesungguhnya, khusus untuk NALA.

File tetangga kedua yang dibutuhkan adalah `app/system_prompt.py` — isinya satu konstanta, `NALA_SYSTEM_PROMPT = "..."`, yaitu **hasil latihan Module 3** (Prompt Engineering Dasar) yang sudah Anda susun sendiri di sana. File ini cuma "membungkus" teks briefing itu jadi konstanta Python.

**✅ Cek dulu sebelum lanjut**: `ls app/` — harus ada `system_prompt.py`. Kalau belum ada, buat filenya manual, isinya konstanta `NALA_SYSTEM_PROMPT` dengan teks hasil latihan Module 3 Anda sendiri, contoh bentuknya:

```python
# app/system_prompt.py
NALA_SYSTEM_PROMPT = """Kamu adalah NALA, asisten AI internal PT Nusantara Finance.
Tugasmu adalah menjawab pertanyaan staff seputar SOP, kebijakan, dan data operasional perusahaan.
Aturan:
- Jawab singkat, jelas, dan dalam Bahasa Indonesia.
- Jika kamu tidak yakin atau informasinya tidak tersedia, katakan dengan jujur bahwa kamu tidak memiliki informasi tersebut. Jangan mengarang jawaban.
- Jangan menjawab pertanyaan di luar konteks pekerjaan PT Nusantara Finance.
"""
```

Ganti isi teksnya sesuai hasil latihan Module 3 Anda sendiri — contoh di atas cuma template kalau filenya hilang/belum dibuat. Kalau nanti mau bereksperimen ulang dengan isi prompt-nya, edit file ini (lihat `PANDUAN-PRAKTIK.md` Langkah 6) — bukan tulis ulang `main.py`.

1. Tambahkan import: `from app.system_prompt import NALA_SYSTEM_PROMPT`
2. Di endpoint `/chat`, ganti string generik dari Langkah 5 dengan `NALA_SYSTEM_PROMPT`:

```python
@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    reply = ollama_client.generate(
        system_prompt=NALA_SYSTEM_PROMPT,
        user_message=request.message,
    )
    return ChatResponse(reply=reply)
```

Perhatikan: **struktur endpoint sama sekali tidak berubah** dari Langkah 5 — cuma satu argumen yang diganti. Ini poin pentingnya: system prompt adalah *konfigurasi kepribadian & batasan* asisten, terpisah total dari *struktur* endpoint-nya. Ganti isi `NALA_SYSTEM_PROMPT` kapan pun tanpa perlu menyentuh `main.py`.

**▶️ Jalankan & lihat hasilnya**

`docker compose up` dari Langkah 5 masih boleh tetap jalan. Simpan file, lalu rebuild `api` supaya kode terbaru terbaca — cukup cepat karena cuma `system_prompt.py`/`main.py` yang berubah, bukan `requirements.txt` (lihat tabel "Kapan pakai command Docker yang mana" di atas: `restart` saja **tidak cukup**, kode di-`COPY` ke image cuma sekali saat `build`):

```bash
docker compose up --build api
```

Ulangi tes `/chat` yang **sama persis** seperti di Langkah 5:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Halo, kamu siapa?"}'
```

Bandingkan jawabannya dengan Langkah 5: sekarang harus terasa lebih spesifik sesuai aturan di `NALA_SYSTEM_PROMPT` (jawab dalam Bahasa Indonesia, tidak mengarang jawaban, dsb) — bukan lagi jawaban generik "saya asisten AI...".

**📄 Kode lengkap Tahap C** dibandingkan **Kode lengkap Tahap B**: hanya 2 baris yang berubah — `system_prompt="Kamu adalah asisten AI..."` (string generik) diganti `system_prompt=NALA_SYSTEM_PROMPT` (import dari `app/system_prompt.py`), plus satu baris import tambahan di atas. **Tidak ada satu pun baris struktur endpoint yang berubah** — itulah inti pelajaran Tahap C.

**Langkah 7 — Bandingkan dengan file aslinya**

Setelah Langkah 1-6 (Tahap A-C), file `main.py` Anda seharusnya berisi ini — ini juga sekaligus **Kode lengkap Tahap C**, versi final (susunan file boleh sedikit beda, isinya yang harus sama):

```python
import os

from fastapi import FastAPI
from pydantic import BaseModel

from app.ollama_client import OllamaClient
from app.system_prompt import NALA_SYSTEM_PROMPT

app = FastAPI(title="NALA")

ollama_client = OllamaClient(
    base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
    model=os.environ.get("OLLAMA_MODEL", "llama3.2:3b"),
)


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    reply = ollama_client.generate(
        system_prompt=NALA_SYSTEM_PROMPT,
        user_message=request.message,
    )
    return ChatResponse(reply=reply)
```

Buka file asli `resources/starter-code/day-1/nala/app/main.py` dan bandingkan — ini persis isinya. Kalau tiap langkah/tahap di atas sudah masuk akal, file ini seharusnya juga langsung masuk akal, meski susunan baris atau nama variabel Anda sedikit berbeda.

Detail lengkap menjalankan stack ini termasuk troubleshooting (error Docker, port bentrok, dll) ada di `PANDUAN-PRAKTIK.md`.

#### 5.2.2 HTTP Method & Semantics

| Method | Semantik | Contoh Use Case |
|--------|----------|-----------------|
| **GET** | Retrieve data (safe, idempotent) | `/health` — cek status service |
| **POST** | Create/process data (can modify state) | `/chat` dengan request body — process pertanyaan |
| **PUT** | Replace resource | `/config/{id}` — update konfigurasi model |
| **DELETE** | Remove resource | `/chat-history/{id}` — delete riwayat chat |

Untuk NALA, **GET** dan **POST** adalah yang paling penting.

#### 5.2.3 Request-Response Model (Pydantic)

Pydantic adalah library untuk data validation dan parsing. Pydantic model define struktur data yang diharapkan.

**Contoh:**

```python
from pydantic import BaseModel

class ChatRequest(BaseModel):
    """Model untuk request ke NALA"""
    message: str  # Required

class ChatResponse(BaseModel):
    """Model untuk response dari NALA"""
    reply: str

@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """
    Endpoint dengan input validation dan output schema
    - Input: ChatRequest (auto-validated)
    - Output: ChatResponse (JSON schema enforced)
    """
    # Process pertanyaan
    reply = ollama_client.generate(system_prompt=NALA_SYSTEM_PROMPT, user_message=request.message)

    # Return response sesuai ChatResponse schema
    return ChatResponse(reply=reply)
```

**Keuntungan Pydantic:**
- **Auto-validation**: Jika client kirim data yang salah (misalnya `temperature: "not-a-number"`), Pydantic auto-reject dengan error message
- **Auto-serialization**: Python object → JSON otomatis
- **Auto-documentation**: Pydantic schema → OpenAPI schema → Swagger UI

#### 5.2.4 Async/Await untuk Concurrent Requests

FastAPI support async handling, memungkinkan multiple requests diproses sekaligus tanpa blocking.

```python
import httpx
from fastapi import FastAPI
from pydantic import BaseModel

from app.system_prompt import NALA_SYSTEM_PROMPT  # hasil latihan Module 3

app = FastAPI()

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str

# Async function untuk call external API (Ollama)
async def ask_ollama(message: str, model: str, system_prompt: str):
    """Non-blocking call ke Ollama API"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://ollama:11434/api/generate",
            json={
                "model": model,
                "prompt": message,
                "system": system_prompt,  # system prompt NALA v1 dari Module 3
                "stream": False,          # tanpa ini, Ollama mengembalikan newline-delimited
                                          # JSON per token, bukan satu objek JSON utuh
            }
        )
    return response.json()

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Async endpoint — dapat handle multiple requests concurrently
    Input tetap lewat Pydantic model (ChatRequest), bukan raw query parameter
    """
    result = await ask_ollama(request.message, model="llama3.2:3b", system_prompt=NALA_SYSTEM_PROMPT)
    return ChatResponse(reply=result["response"])

# Simulasi: 2 requests bisa diproses "simultaneously"
# Request 1: async function menunggu response dari Ollama → tidak block
# Request 2: selama Request 1 menunggu, FastAPI process Request 2
```

#### 5.2.5 Routing & Path Parameters

```python
class MessageRequest(BaseModel):
    message: str

@app.get("/chat/{chat_id}")
async def get_chat(chat_id: int):
    """
    Get chat history untuk chat_id tertentu
    - Path parameter: chat_id diambil dari URL
    - Contoh: GET /chat/123 → chat_id = 123
    """
    return {"chat_id": chat_id, "messages": [...]}

@app.post("/chat/{chat_id}/message")
async def add_message(chat_id: int, request: MessageRequest):
    """
    Add message ke chat tertentu
    - Path parameter: chat_id dari URL
    - Request body: MessageRequest (Pydantic model), bukan raw query parameter
    """
    return {"chat_id": chat_id, "message": request.message, "status": "added"}
```

#### 5.2.6 Running FastAPI Server

```bash
# Install uvicorn (ASGI server untuk FastAPI)
pip install fastapi uvicorn

# Jalankan server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Server akan berjalan di http://localhost:8000
# Swagger UI (dokumentasi interaktif) di http://localhost:8000/docs
```

### 5.3 Ringkasan: FastAPI untuk NALA

| Aspek | Penjelasan |
|-------|-----------|
| **Purpose** | Menyediakan HTTP API untuk aplikasi lain berkomunikasi dengan NALA |
| **Key Concept (Non-teknis)** | Resepsionis yang menerima pertanyaan, melempar ke asisten (Ollama), kembalikan jawaban |
| **Key Concept (Teknis)** | Framework Python untuk build REST API dengan automatic validation, documentation, async support |
| **Untuk NALA (Module 1-4)** | FastAPI app yang menerima request user di `/chat`, kirim ke Ollama, return jawaban |
| **Untuk NALA (Module 19+)** | FastAPI app juga integrate dengan PostgreSQL, LangGraph Agent, OpenSearch (hybrid search) untuk full-featured RAG + agentic system |

### 5.4 Contoh Endpoint NALA yang Akan Dibangun

Selama training, Anda akan implement endpoint seperti:

```python
# Module 1-4
@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """Simple Q&A endpoint"""
    reply = ollama_client.generate(system_prompt=NALA_SYSTEM_PROMPT, user_message=request.message)
    return ChatResponse(reply=reply)

# Module 11+
@app.post("/rag/ask")
async def rag_ask(query: str):
    """RAG: retrieve relevant docs (dari OpenSearch) + generate answer"""
    retrieved_docs = opensearch.search(query)
    context = "\n".join([doc for doc in retrieved_docs])
    prompt = f"Context: {context}\n\nQuestion: {query}"
    answer = ollama_inference(prompt)
    return {"query": query, "answer": answer, "sources": retrieved_docs}

# Module 19+
@app.post("/agent/ask")
async def agent_ask(query: str):
    """Agentic: LangGraph agent decides which tools to use"""
    state = agent.invoke({"query": query})
    return {"query": query, "answer": state["answer"], "tools_used": state["tools"]}
```

---

## Ringkasan & Next Steps

Anda telah memahami:

✅ **Apa itu Docker** — image, container, Docker Hub, Dockerfile; kenapa aplikasi yang di-container-kan berjalan sama di laptop mana pun  
✅ **Kenapa Docker Compose** — menyatukan multiple services dalam satu environment yang consistent  
✅ **Anatomi docker-compose.yml** — struktur services, image, ports, volumes, environment, depends_on  
✅ **Arsitektur NALA bertahap** — pertumbuhan dari simple (Ollama + FastAPI) → full-featured (+ OpenSearch, Airflow, Langfuse, PostgreSQL, LangGraph)  
✅ **Konsep dasar FastAPI** — HTTP framework untuk build API, request/response models, routing, async support  

**Next Steps:**
- **Praktik langsung**: lihat `PANDUAN-PRAKTIK.md` — setup docker-compose.yml, jalankan containers
- **Starter code**: `resources/starter-code/day-1/nala/` — struktur project FastAPI app dan docker-compose NALA
- **Module 5+**: Extend docker-compose.yml dengan service tambahan (OpenSearch, Airflow, PostgreSQL, dsb)
