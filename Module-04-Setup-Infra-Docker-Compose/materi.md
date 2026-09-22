# Module 4: Setup Infra Docker Compose

## Tujuan

Kita memahami konsep dasar Docker/Docker Compose, lalu membangun `docker-compose.yml` NALA secara bertahap — dimulai dari service `ollama` sendirian, diverifikasi benar-benar sehat di dalam container — sekaligus mengenal permukaan lengkap REST API Ollama, sebelum Module 5 membangun FastAPI dan Module 6 menyambungkannya ke Ollama.

## Hasil Akhir yang Diharapkan

- Kita paham konsep image, container, dan fungsi tiap bagian `docker-compose.yml` (services, ports, volumes, environment, depends_on)
- Service `ollama` berhasil dijalankan & diverifikasi sendirian di Docker — model ter-pull, `ollama list`/`curl .../api/tags` merespons, dan bisa diajak tanya-jawab langsung lewat `docker compose exec`
- Kita kenal permukaan lengkap REST API Ollama (`generate`, `chat`, `tags`, `show`, `pull`, `embed`, `ps`, dst) — bukan cuma satu endpoint yang nanti dipakai `OllamaClient`
- Kita paham kapan menggunakan `docker compose up --build` vs `up` vs `down`
- Kita siap lanjut ke Module 5 untuk membangun FastAPI, lalu Module 6 untuk menyambungkannya ke Ollama yang sudah terverifikasi ini

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

File `docker-compose.yml` adalah file konfigurasi YAML yang mendefinisikan semua service (containers) yang aplikasi Anda butuhkan, beserta setting mereka. File ini akan disimpan di `Nala/docker-compose.yml`.

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

Docker itu sendiri konsep baru, Ollama-di-dalam-container juga baru, dan FastAPI-di-dalam-container juga baru — kalau ketiganya dinyalakan bersamaan lewat satu `docker compose up` dan ada yang error, sulit menebak biang keladinya yang mana. Karena itu `docker-compose.yml` NALA dibangun **bertahap**: dulu cuma service `ollama` sendirian, dipastikan jalan, baru service `api` ditambahkan di Module 6.

Berikut isi `docker-compose.yml` di tahap pertama ini (`Nala/docker-compose.yml`) — baru berisi satu service:

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
cd Nala
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

**Langkah E — Coba tanya langsung (opsional, tapi meyakinkan):**

Langkah D tadi baru membuktikan modelnya **ada**, belum membuktikan modelnya **bisa menjawab**. `ollama list`/`curl .../api/tags` bisa saja sukses walau ada masalah lain yang baru kelihatan saat model benar-benar diminta generate jawaban. Cara paling langsung memastikannya: tanya sungguhan, persis seperti di Module 2 — bedanya sekarang Ollama-nya jalan di dalam container, jadi perintahnya dibungkus `docker compose exec`:

```bash
docker compose exec ollama ollama run llama3.2:3b "Halo, siapa kamu?"
```

`docker compose exec ollama ...` menjalankan perintah **di dalam** container `ollama` — persis seperti masuk terminal container itu lalu mengetik `ollama run` biasa. Kalau muncul jawaban (walau masih generik, belum berkarakter NALA — system prompt baru masuk di Module 6), berarti Ollama di dalam container ini benar-benar berfungsi penuh, bukan cuma "kelihatan menyala".

✅ **Checkpoint sebelum lanjut**: `docker compose ps` menunjukkan `ollama` running, `ollama list` di dalam container menampilkan `llama3.2:3b`, `curl http://localhost:11434/api/tags` dari luar container juga berhasil, **dan** `docker compose exec ollama ollama run llama3.2:3b "..."` menghasilkan jawaban nyata. Kalau salah satu belum terpenuhi, selesaikan dulu di sini — menambah service `api` di atas fondasi Ollama yang belum stabil cuma akan mempersulit debugging nanti.

Biarkan container `ollama` tetap berjalan (tidak perlu `docker compose down`) — Module 6 menambahkan service `api` ke `docker-compose.yml` yang sama, dan Module 6 nanti akan menyalakan `api` sekaligus tetap memakai `ollama` yang sudah berjalan ini.

<details>
<summary><strong>Pakai Claude Code? Salin prompt berikut, paste untuk eksekusi section 3.3</strong></summary>

```
Buat docker-compose.yml NALA tahap pertama — cuma service ollama,
belum ada api.

GOAL:
- Buat/timpa Nala/docker-compose.yml
  persis isinya:

  services:
    ollama:
      image: ollama/ollama:latest
      ports:
        - "11434:11434"
      volumes:
        - ollama_data:/root/.ollama

  volumes:
    ollama_data:

CONTEXT:
- Ini docker-compose.yml paling awal project NALA — sengaja cuma
  satu service supaya Ollama bisa diverifikasi sendirian dulu
  sebelum service api ditambahkan di Module 6.

GUARDRAIL:
- JANGAN tambahkan service api, build, depends_on, atau environment
  apa pun — itu semua baru masuk di Module 6.
- JANGAN buat file lain (Dockerfile, app/, requirements.txt) — itu
  bagian Tahap A/B, bukan langkah ini.
```

</details>

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

## 4. Referensi Lengkap: Ollama REST API

Bagian 3.4 tadi sudah memanggil satu endpoint Ollama lewat `curl` (`/api/tags`) untuk verifikasi. Tapi Ollama sendiri, begitu servicenya menyala di port `11434`, sudah menyediakan **seluruh** REST API ini — hampir semua yang bisa dilakukan lewat CLI `ollama <sesuatu>` punya endpoint HTTP yang setara di baliknya. Mengenal permukaan lengkapnya berguna supaya kita tahu apa lagi yang tersedia, sebelum Module 6 membangun `OllamaClient` yang cuma membungkus satu endpoint tertentu.

### 4.1 Endpoint yang Sudah Dipakai/Akan Dipakai NALA

| Endpoint | Fungsi | Dipakai di NALA |
|---|---|---|
| `POST /api/generate` | Single-prompt completion — kirim satu prompt, terima satu jawaban | `OllamaClient.generate()` (dibangun Module 6) — inti dari endpoint `/chat` NALA |
| `POST /api/chat` | Sama seperti `/api/generate`, tapi menerima `messages[]` (riwayat percakapan multi-turn dengan role `system`/`user`/`assistant`) alih-alih satu `prompt` string | Belum dipakai sampai module ini — relevan begitu NALA butuh riwayat percakapan multi-turn |
| `GET /api/tags` | Daftar model yang sudah ter-*pull* (setara `ollama list`) | Dipakai untuk verifikasi manual di Bagian 3.4 di atas (`curl http://localhost:11434/api/tags`) |
| `POST /api/show` | Detail satu model (parameter, template, system prompt bawaan) | Belum dipakai langsung dari kode NALA, tapi berguna untuk debugging manual |

**Contoh penggunaan tiap endpoint** (jalankan sambil `ollama` container dari Bagian 3.4 masih aktif):

**`POST /api/generate`** — kirim satu prompt, `stream: false` supaya jawabannya diterima utuh sekaligus (bukan token demi token):

```bash
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2:3b",
  "prompt": "Sebutkan 3 kegunaan AI di industri keuangan",
  "stream": false
}'
```

Response (dipotong):
```json
{
  "model": "llama3.2:3b",
  "response": "1. Deteksi fraud...\n2. Credit scoring...\n3. Chatbot layanan nasabah...",
  "done": true
}
```

Field `response` inilah yang diambil `OllamaClient.generate()` lewat `response.json()["response"]` (Module 6) — persis satu baris kode yang membungkus request `curl` ini.

**`POST /api/chat`** — kirim riwayat percakapan sebagai array `messages`, bukan satu `prompt` string:

```bash
curl http://localhost:11434/api/chat -d '{
  "model": "llama3.2:3b",
  "messages": [
    {"role": "system", "content": "Kamu adalah asisten yang menjawab singkat."},
    {"role": "user", "content": "Apa itu suku bunga acuan?"},
    {"role": "assistant", "content": "Suku bunga yang ditetapkan bank sentral sebagai acuan."},
    {"role": "user", "content": "Siapa yang menetapkannya di Indonesia?"}
  ],
  "stream": false
}'
```

Perhatikan pertanyaan terakhir ("Siapa yang menetapkannya?") cuma masuk akal **karena** ada riwayat sebelumnya dalam `messages[]` — beda dengan `/api/generate` yang cuma menerima satu `prompt` berdiri sendiri tanpa konteks percakapan.

**`GET /api/tags`** — tidak butuh body, cukup GET biasa:

```bash
curl http://localhost:11434/api/tags
```

Response (dipotong):
```json
{
  "models": [
    {"name": "llama3.2:3b", "size": 2019393189, "modified_at": "..."}
  ]
}
```

**`POST /api/show`** — minta detail satu model spesifik:

```bash
curl http://localhost:11434/api/show -d '{"model": "llama3.2:3b"}'
```

Response (dipotong) menunjukkan `parameters` (default seperti `temperature`, `num_ctx` — dibahas lengkap di Module 3 Bagian 8) dan `template` (format prompt internal model itu):
```json
{
  "parameters": "stop \"<|eot_id|>\"",
  "template": "{{ if .System }}...",
  "details": {"family": "llama", "parameter_size": "3.2B"}
}
```

### 4.2 Endpoint Lain yang Tersedia (Belum Dipakai NALA)

| Endpoint | Fungsi |
|---|---|
| `POST /api/pull` | Download model — setara `ollama pull`, tapi bisa dipicu dari kode, bukan cuma terminal |
| `DELETE /api/delete` | Hapus model dari disk — setara `ollama rm` |
| `POST /api/copy` | Duplikasi model dengan nama baru — setara `ollama cp` |
| `POST /api/create` | Build model custom dari Modelfile — setara `ollama create` (dipakai manual di Module 3, lewat CLI) |
| `POST /api/push` | Upload model ke registry Ollama sendiri — jarang relevan untuk NALA (tidak mendistribusikan model custom) |
| `POST /api/embed` | Generate embedding vector dari teks — **ini yang dipanggil** fungsi `embed_text()` NALA nanti di Module 10, di balik layar |
| `GET /api/ps` | Model yang sedang di-*load* di memori — setara `ollama ps` |
| `GET /api/version` | Versi Ollama yang terinstall |
| `HEAD` / `POST /api/blobs/:digest` | Cek/upload file model mentah (GGUF) — dipakai internal oleh `push`/`create`, jarang dipanggil langsung |

### 4.3 Contoh Cepat: Memanggil Beberapa Endpoint Lain Lewat `curl`

Endpoint-endpoint di Bagian 4.2 tidak dipakai kode NALA saat ini, tapi bisa dicoba langsung untuk memastikan pemahamannya — jalankan sambil container `ollama` dari Bagian 3.4 masih aktif:

```bash
# Cek versi Ollama
curl http://localhost:11434/api/version

# Model yang sedang di-load di memori
curl http://localhost:11434/api/ps

# Detail satu model (parameter, template)
curl http://localhost:11434/api/show -d '{"model": "llama3.2:3b"}'
```

### 4.4 Kenapa `OllamaClient` (Module 6) Nanti Cuma Membungkus Satu Endpoint

Dari daftar di atas, `OllamaClient.generate()` yang dibangun Module 6 sengaja **tidak** membungkus semua endpoint Ollama — cuma `/api/generate`, karena itulah satu-satunya yang dibutuhkan endpoint `/chat` NALA saat itu. Ini konsisten dengan pola yang berulang sepanjang training: tambahkan kemampuan **tepat saat dibutuhkan**, bukan diborong di awal. Kalau nanti NALA butuh riwayat percakapan multi-turn, `OllamaClient` akan diperluas dengan method baru yang memanggil `/api/chat` — bukan mengganti `generate()` yang sudah ada.

---

## Panduan Praktik

### Prasyarat
- Docker Desktop sudah terinstall dan berjalan
- Minimal 16GB RAM tersedia
- Docker Desktop sudah dialokasikan resource yang cukup (lihat Langkah 0 di bawah)

### Langkah 0: Atur RAM & Storage Docker Desktop

Secara default, Docker Desktop **tidak otomatis memakai semua resource laptop Anda** — ada batas RAM, CPU, dan disk yang dialokasikan sendiri, terpisah dari sisa laptop. Kalau batas ini terlalu kecil, container bisa lambat, gagal start, atau ke-*kill* otomatis (biasanya errornya "Killed" atau container tiba-tiba restart) — terutama untuk Ollama yang butuh RAM cukup besar untuk memuat model.

**Cara mengecek/mengubah (macOS & Windows):**

1. Buka aplikasi **Docker Desktop**
2. Klik ikon **⚙️ Settings** (gear icon, biasanya di kanan atas)
3. Masuk ke tab **Resources**

**Pengaturan yang direkomendasikan untuk NALA:**

| Setting | Minimal | Direkomendasikan | Alasan |
|---|---|---|---|
| **Memory (RAM)** | 8 GB | 12–16 GB | `llama3.2:3b` butuh ~4-6GB saat dimuat; sisanya untuk FastAPI, OS container, dan buffer. Modul-modul selanjutnya (Module 15 dst.) nanti menambah OpenSearch/PostgreSQL yang juga butuh RAM. |
| **CPUs** | 2 | 4+ | Inference LLM cukup CPU-intensive kalau tidak pakai GPU. |
| **Disk image size** | 60 GB | 100 GB+ | Setiap image Docker (Python, Ollama, nanti OpenSearch/Airflow/PostgreSQL) + model Ollama (~2GB per model) menumpuk seiring modul training berjalan. |
| **Swap** | 1 GB | 2 GB | Buffer tambahan kalau Memory limit sempat mepet. |

Setelah mengubah, klik **Apply & Restart** — Docker Desktop akan restart untuk menerapkan setting baru (container yang sedang jalan akan ikut berhenti, jalankan ulang `docker compose up --build` setelahnya).

**Kalau disk mulai penuh** (sering terjadi setelah beberapa modul training karena image/model menumpuk), bersihkan yang tidak terpakai:

```bash
docker system prune -a --volumes
```

⚠️ Perintah ini menghapus **semua** container, image, dan volume yang tidak sedang dipakai — termasuk model Ollama yang sudah di-pull (harus di-pull ulang setelahnya). Jangan jalankan sembarangan kalau ada project Docker lain di laptop yang sama yang masih dibutuhkan.

**Cek pemakaian resource real-time** (container mana yang paling banyak makan RAM/CPU):

```bash
docker stats
```

### Langkah 1: Clone & masuk ke folder starter code

```bash
cd Nala
```

Prinsipnya: pastikan fondasi (Ollama di Docker) benar-benar sehat sebelum Module 6 menyambungkannya ke FastAPI — debug di sini dulu kalau ada masalah, karena akan jauh lebih sulit membedakan "Ollama-nya yang bermasalah" vs "FastAPI-nya yang bermasalah" kalau keduanya dinyalakan bersamaan.

### Langkah 2: Nyalakan service `ollama` saja

Pastikan `docker-compose.yml` Anda di titik ini **baru** berisi service `ollama` (lihat section 3.3 di atas — belum ada `api`):

```bash
docker compose up -d ollama
```

`-d` menjalankan di background. Cek statusnya:

```bash
docker compose ps
```

Kolom status `ollama` harus `running`/`Up`, bukan `Exited` atau `Restarting`.

### Langkah 3: Pull & verifikasi model di dalam container

Ollama yang berjalan **di dalam container** punya storage terpisah dari Ollama yang mungkin sudah terinstall langsung di laptop Anda (lihat Module 2) — jadi modelnya perlu di-pull lagi khusus untuk container ini (sekali saja; tersimpan permanen di volume `ollama_data` selama volume tidak dihapus).

```bash
docker compose exec ollama ollama pull llama3.2:3b
```

⚠️ Tag `:3b` **wajib** ditulis persis seperti di atas — harus sama dengan `OLLAMA_MODEL` yang akan dipakai service `api` nanti. Kalau Anda pull `llama3.2` tanpa tag, aplikasi tetap bisa gagal mencari model `llama3.2:3b` walau terlihat "mirip".

Verifikasi model sudah ada, **dari dua sisi**:

```bash
docker compose exec ollama ollama list
curl http://localhost:11434/api/tags
```

`llama3.2:3b` harus muncul di kedua output — yang pertama dari **dalam** container, yang kedua dari **luar** container (lewat port `11434` yang sudah di-mapping ke laptop Anda).

✅ **Checkpoint "aman" — jangan lanjut ke Module 6 kalau salah satu berikut belum terpenuhi:**
- [ ] `docker compose ps` menunjukkan `ollama` berstatus `running`
- [ ] `docker compose exec ollama ollama list` menampilkan `llama3.2:3b`
- [ ] `curl http://localhost:11434/api/tags` dari luar container berhasil dan menampilkan `llama3.2:3b`

Biarkan container `ollama` tetap berjalan (tidak perlu `docker compose down`) — Module 6 melanjutkan dari sini dengan menambahkan service `api` ke `docker-compose.yml` yang sama.

### Troubleshooting

- **Container `ollama` berstatus `Exited`/`Restarting` di Langkah 2**: cek log-nya duluan — `docker compose logs ollama`. Penyebab paling umum: RAM Docker Desktop tidak cukup (lihat Langkah 0) atau port `11434` sudah dipakai proses lain di laptop Anda (misal Ollama versi native dari Module 2 masih berjalan langsung di laptop — matikan dulu, lihat Module 2 section 2.1, sebelum menjalankan versi container-nya).
- **`no configuration file provided: not found`**: `docker compose` dijalankan bukan dari folder yang berisi `docker-compose.yml`. Pastikan Anda berada persis di `Nala/` (cek dengan `ls` — harus ada `docker-compose.yml`).
- **Ollama lambat merespons pertama kali** (Langkah E): wajar, model sedang dimuat ke memori. Percobaan kedua akan lebih cepat.

---

## Ringkasan & Next Steps

Anda telah memahami:

✅ **Apa itu Docker** — image, container, Docker Hub, Dockerfile; kenapa aplikasi yang di-container-kan berjalan sama di laptop mana pun  
✅ **Kenapa Docker Compose** — menyatukan multiple services dalam satu environment yang consistent  
✅ **Anatomi docker-compose.yml** — struktur services, image, ports, volumes, environment, depends_on  
✅ **Ollama berjalan sendirian & terverifikasi di Docker** — model ter-pull, API merespons, bisa diajak tanya-jawab — fondasi yang siap disambungkan ke service lain  
✅ **Permukaan lengkap REST API Ollama** — `generate`, `chat`, `tags`, `show`, `pull`, `embed`, `ps`, dan lainnya — bukan cuma satu endpoint yang nanti dipakai `OllamaClient`  

**Next Steps:**
- **Praktik langsung**: lihat bagian Panduan Praktik di atas — setup docker-compose.yml, jalankan container `ollama`
- **Starter code**: `Nala/` — docker-compose NALA (baru berisi service `ollama`)
- **Module 5**: Membangun FastAPI murni (`app/main.py`, endpoint `/health`, Pydantic models) — belum terhubung ke Ollama
- **Module 6**: Menambahkan service `api` (FastAPI) ke docker-compose.yml dan menyambungkannya ke Ollama yang sudah terverifikasi di module ini
