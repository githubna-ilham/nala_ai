# Module 2: Setup Ollama & Evaluasi Model

## Tujuan

Kita menginstall dan menjalankan Ollama secara lokal, mengunduh serta menjalankan model LLM pertama, dan melakukan evaluasi manual sederhana untuk membandingkan kualitas dan kecepatan beberapa model sebagai dasar pemilihan model untuk NALA.

## Hasil Akhir yang Diharapkan

- Ollama terinstall dan `ollama serve` berjalan di laptop kita (macOS/Windows/Linux)
- Model `llama3.2:3b` berhasil di-download dan dijalankan lewat CLI, mampu menjawab pertanyaan sederhana
- Kita bisa membaca log Ollama (GPU offload, tokens/detik, prompt caching) untuk menilai performa hardware
- Kita bisa mengestimasi kebutuhan RAM/VRAM untuk suatu model berdasarkan ukuran parameter dan quantization
- Kita mengisi worksheet evaluasi manual yang membandingkan minimal dua model pada 3 pertanyaan standar
- Kita bisa melakukan troubleshooting masalah umum (connection refused, out of memory, port bentrok, download gagal)

## 1. Apa itu Ollama

Ollama adalah tool open-source yang memungkinkan Anda menjalankan Large Language Model (LLM) secara lokal di komputer Anda tanpa memerlukan koneksi internet berkelanjutan atau layanan cloud. 

**Cara Kerja Ollama:**
- **Download model sekali**: Ollama mengunduh model LLM (misalnya Llama 3.2, Mistral, Qwen) dari repository resmi dan menyimpannya secara lokal di storage Anda.
- **Jalankan lewat CLI**: Setelah download, Anda dapat menjalankan model langsung dari command line interface (CLI).
- **API lokal di port 11434**: Ollama menjalankan server lokal yang mendengarkan pada port 11434, memungkinkan aplikasi Anda berkomunikasi dengan model via HTTP requests.

**Keuntungan menggunakan Ollama:**
- **Privasi**: Data Anda tidak dikirim ke server pihak ketiga
- **Kecepatan**: Respons lebih cepat karena berjalan lokal (tanpa latency jaringan)
- **Biaya**: Gratis setelah mengunduh; tidak ada biaya per-query
- **Fleksibilitas**: Dapat menjalankan berbagai model open-source
- **Offline-ready**: Tidak memerlukan koneksi internet untuk inferensi (setelah download)

---

## 2. Referensi Perintah Dasar Ollama

Sebelum masuk ke instalasi, kenali dulu perintah-perintah `ollama` yang akan dipakai berulang kali sepanjang modul ini (dan modul-modul berikutnya). Tabel ini jadi rujukan cepat — tidak perlu dihafal sekarang, cukup tahu perintah apa ada di sini supaya gampang dicari lagi nanti.

### 2.1 Menyalakan & Mematikan Ollama

| Perintah | Fungsi |
|---|---|
| `ollama serve` | Menyalakan Ollama service secara manual di **foreground** — proses tetap berjalan selama terminal itu terbuka, log inference (Bagian 4.4) muncul di sini |
| `Ctrl+C` (di terminal tempat `ollama serve` berjalan) | Mematikan service yang dijalankan manual di foreground |
| Klik ikon Ollama di menu bar (macOS) → "Quit Ollama" | Mematikan Ollama versi aplikasi desktop (berjalan di background, bukan lewat `ollama serve` manual) |
| Klik kanan ikon Ollama di system tray → "Quit" (Windows) | Sama seperti di atas, untuk Windows |
| `sudo systemctl stop ollama` (Linux, kalau diinstal sebagai systemd service) | Mematikan Ollama yang berjalan sebagai service sistem |

> 📌 **Kapan perlu mematikan Ollama?** Untuk kebutuhan modul ini, jarang perlu — biarkan Ollama tetap menyala sepanjang sesi praktik. Mematikan baru relevan kalau: (1) mau membebaskan RAM untuk aplikasi lain, (2) troubleshooting `address already in use` (Bagian 7), atau (3) mengganti versi Ollama.

**Cek apakah Ollama sedang menyala:**
```bash
curl http://localhost:11434
```
Kalau muncul `Ollama is running`, service aktif. Kalau `Connection refused`, service tidak berjalan (lihat Bagian 3 untuk cara menyalakannya lagi).

### 2.2 Mengelola Model

| Perintah | Fungsi |
|---|---|
| `ollama pull <model>` | Download model dari Ollama Library ke laptop Anda |
| `ollama list` | Menampilkan semua model yang sudah ter-download |
| `ollama run <model>` | Menjalankan model — masuk mode interaktif kalau tanpa argumen tambahan, atau mode single-shot kalau disertai prompt langsung: `ollama run <model> "pertanyaan"` |
| `ollama ps` | Menampilkan model yang **sedang di-load** di memori saat ini (beda dari `ollama list`, yang menampilkan semua model yang tersimpan di disk) |
| `ollama stop <model>` | Meng-unload satu model dari memori tanpa mematikan Ollama service secara keseluruhan |
| `ollama rm <model>` | Menghapus model dari disk secara permanen (perlu `ollama pull` ulang kalau ingin dipakai lagi) |
| `ollama show <model>` | Menampilkan detail model (parameter, template, system prompt bawaan) |
| `ollama show <model> --modelfile` | Menampilkan isi Modelfile dari model yang sudah pernah dibuat (dibahas Module 3) |
| `ollama cp <model> <nama-baru>` | Menduplikasi model dengan nama baru |
| `ollama --version` | Menampilkan versi Ollama yang terinstall |

### 2.3 Perintah di Dalam Sesi Interaktif

Perintah berikut hanya berlaku **setelah** Anda menjalankan `ollama run <model>` tanpa argumen (masuk ke prompt `>>>`):

| Perintah | Fungsi |
|---|---|
| `/bye` | Keluar dari sesi interaktif |
| `/exit` | Sama seperti `/bye` |
| `/clear` | Menghapus riwayat percakapan & system prompt yang sedang aktif, mulai sesi bersih |
| `/set system <teks>` | Mengatur system prompt untuk sesi ini (dibahas detail di Module 3) |
| `/show system` | Menampilkan system prompt yang sedang aktif |

Daftar lengkap perintah di atas akan langsung dipakai mulai Bagian 4 modul ini (menjalankan model pertama) dan terus dipakai di Module 3 (prompt engineering) — jadi tidak perlu dihafal sekaligus, cukup tahu ke mana harus mencari lagi kalau lupa.

---

## 3. Instalasi Ollama

### 3.1 macOS

**Opsi 1: Menggunakan Homebrew (Recommended)**
```bash
brew install ollama
```

**Opsi 2: Download Manual**
1. Kunjungi [ollama.com](https://ollama.com)
2. Klik "Download"
3. Pilih "macOS"
4. Download installer (.dmg file)
5. Jalankan installer dan ikuti instruksi

**Verifikasi Instalasi:**
```bash
ollama --version
```

Jika berhasil, Anda akan melihat output seperti: `ollama version X.X.X`

### 3.2 Windows

1. Kunjungi [ollama.com](https://ollama.com)
2. Klik "Download"
3. Pilih "Windows"
4. Download installer (.exe file)
5. Jalankan installer (OllamaSetup.exe)
6. Ikuti wizard instalasi
7. Ollama akan dimulai otomatis setelah instalasi

**Verifikasi Instalasi (buka PowerShell atau Command Prompt):**
```powershell
ollama --version
```

**Catatan untuk Windows:**
- Ollama akan berjalan sebagai Windows service di background
- Anda dapat melihat status di system tray
- Default API endpoint tetap `http://localhost:11434`

### 3.3 Linux

**Ubuntu/Debian:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

**Fedora/RHEL:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

**Alternatif manual (semua distro):**
1. Download dari [ollama.com/download/linux](https://ollama.com/download/linux)
2. Extract file
3. Jalankan: `./ollama`

**Verifikasi Instalasi:**
```bash
ollama --version
```

**Mulai Ollama service (Linux):**
```bash
ollama serve
```

---

## 4. Menjalankan Model Pertama

### 4.1 Memulai Ollama Service

Sebelum menjalankan model, pastikan Ollama service berjalan:

**macOS/Linux:**
```bash
ollama serve
```
Output yang diharapkan: `Listening on 127.0.0.1:11434`

**Windows:**
Ollama sudah berjalan di background setelah instalasi. Periksa system tray untuk ikon Ollama.

### 4.2 Download Model

Buka terminal/PowerShell baru (jangan tutup yang menjalankan `ollama serve`) dan jalankan:

```bash
ollama pull llama3.2:3b
```

Ini akan mengunduh model Llama 3.2 3B (ukuran ~2GB). Tunggu sampai selesai.

### 4.3 Jalankan Pertanyaan Pertama

Setelah download selesai:

```bash
ollama run llama3.2:3b "Jelaskan apa itu RAG dalam satu kalimat"
```

**Output yang diharapkan:**
```
RAG (Retrieval-Augmented Generation) adalah teknik AI yang menggabungkan pencarian 
informasi dari database eksternal dengan kemampuan generasi bahasa model untuk 
menghasilkan jawaban yang lebih akurat dan berbasis fakta.
```

**Perintah-perintah tambahan:**

Menjalankan mode interaktif (chat):
```bash
ollama run llama3.2:3b
```
Kemudian ketik pertanyaan Anda dan tekan Enter. Ketik `/exit` untuk keluar.

Menjalankan dengan prompt custom:
```bash
ollama run llama3.2:3b "Tuliskan 3 keuntungan machine learning dalam bentuk list"
```

### 4.4 Apa yang Terjadi di Balik Layar

Saat pertama kali menjalankan model, `ollama serve` akan mencetak log detail di terminal. Memahami log ini berguna untuk troubleshooting dan menilai performa hardware Anda.

**Fase loading model** — ditandai baris seperti:
```
msg="Listening on 127.0.0.1:11434 (version 0.33.2)"
msg="starting llama-server" ...
load_tensors: offloaded 29/29 layers to GPU
```
`offloaded 29/29 layers to GPU` berarti seluruh layer model berhasil dipindah ke GPU (Metal di macOS/Apple Silicon, CUDA di Nvidia). Jika hanya sebagian layer yang ter-offload, model akan berjalan lebih lambat karena sisanya diproses CPU — biasanya terjadi kalau VRAM tidak cukup.

**Fase inference** — setiap request akan mencetak dua metrik timing:
```
prompt eval time = 109.77 ms / 31 tokens (282.42 tokens per second)
eval time        = 204.42 ms / 12 tokens ( 53.81 tokens per second)
```
- **Prompt eval** = kecepatan model "membaca" pertanyaan Anda (biasanya jauh lebih cepat karena diproses paralel).
- **Eval** = kecepatan model "menulis" jawaban token-per-token (autoregressive, jadi lebih lambat). Angka inilah yang paling menentukan seberapa cepat jawaban terasa muncul di layar.

Semakin besar model, semakin rendah angka tokens/detik. Ini bisa dipakai sebagai alat ukur objektif tambahan di worksheet evaluasi (section 6.3).

**Prompt caching pada percakapan berkelanjutan** — jika Anda chat multi-turn (mode interaktif `ollama run llama3.2:3b` tanpa argumen), log akan menunjukkan:
```
checking sim = 0.724 (42/58) > 0.100
selected slot by LCP similarity
cached n_tokens = 42, memory_seq_rm [42, end)
```
Ollama otomatis mendeteksi kemiripan (*Longest Common Prefix*) antara prompt baru dan riwayat percakapan sebelumnya, lalu meng-reuse bagian yang sama dari cache (KV-cache) alih-alih memproses ulang seluruh histori dari awal. Inilah kenapa giliran chat kedua dan seterusnya terasa jauh lebih responsif dibanding giliran pertama.

**Catatan penting soal port 11434 yang "sudah dipakai":** jika Anda menjalankan `ollama serve` secara manual padahal aplikasi desktop Ollama (ikon di menu bar/system tray) sudah berjalan di background, Anda akan mendapat error `address already in use` (lihat section 7). Ini normal — hanya boleh ada **satu** instance Ollama yang listen di port 11434. Untuk memastikan tidak ada instance ganda:
- **macOS/Linux**: `lsof -i :11434` untuk melihat proses yang sedang memegang port tersebut.
- Jika ingin mematikan Ollama sepenuhnya (misalnya untuk membebaskan RAM/VRAM), quit aplikasinya dari menu bar/system tray — bukan hanya `kill` proses `ollama`, karena aplikasi desktop akan otomatis me-restart proses server tersebut.

### 4.5 Akses Ollama via GUI (Alternatif Terminal)

Selain lewat terminal, aplikasi desktop Ollama juga menyediakan jendela chat (GUI) sederhana. **Ini hanya untuk uji coba manual** — kode program `nala/` yang akan dibangun mulai Module 4 berbicara ke Ollama lewat API (HTTP request), bukan lewat GUI ini.

**Membuka Ollama Chat:**

Klik ikon Ollama di menu bar (macOS, pojok kanan atas) atau system tray (Windows, pojok kanan bawah). Akan muncul jendela dengan tombol **"New Chat"**, kotak **"Send a message"**, dan dropdown pemilih model di pojok kanan bawah.

![Jendela Ollama Chat dengan peringatan model cloud](../../resources/images/ollama-setup/ollama-chat-gui.png)

> ⚠️ **Hati-hati, ada jebakan kecil di sini**: dropdown model kadang **secara otomatis memilih model cloud** (contoh: `glm-5.2:cloud`) — model yang jalan di server internet, bukan di laptop Anda. Kalau muncul pesan *"Cloud models require an Ollama account"* dengan tombol **Sign In** — **jangan klik Sign In**. Tutup pesannya (✕), lalu ganti manual ke `llama3.2:3b` di dropdown. Training ini prinsipnya **100% offline/privat** (lihat Module 1) — hanya boleh memakai model yang tersimpan di laptop sendiri.
>
> Jebakan serupa juga ada di ikon **globe (🌐)** di sebelah tombol `+` — ini adalah toggle **web search**, fitur resmi Ollama yang mencari informasi ke internet secara live lewat hosted API di `ollama.com`. Mengklik ikon ini akan memunculkan pesan *"Web search requires an Ollama account"* dengan tombol **Sign In** juga. **Jangan klik Sign In** di sini juga — cukup tutup (✕) dan biarkan toggle ini nonaktif.
>
> **Penting soal data:** selama Anda hanya melihat pesan ini dan menutupnya tanpa sign in, **tidak ada data yang terkirim ke mana pun** — fiturnya terblokir sebelum jalan. Risiko baru nyata kalau benar-benar sign in dan mengaktifkan fitur ini: query pencarian Anda akan dikirim ke server Ollama (`ollama.com`) untuk dicarikan hasil dari internet (inference model tetap jalan lokal, tapi query pencariannya keluar laptop). Ini bertentangan dengan prinsip privasi data NALA (lihat Module 1), jadi selama training tetap biarkan toggle ini nonaktif.

**Catatan tambahan — menu interaktif di terminal:**

Kalau Anda mengetik `ollama` saja di terminal (tanpa argumen apa pun), versi Ollama terbaru akan menampilkan menu interaktif "Chat, Code, & Work" berisi pintasan ke tools lain (Claude Code, OpenCode, dsb.) — ini **tidak ada hubungannya** dengan pelatihan ini. Jangan pilih opsi apa pun, cukup tekan `esc` untuk keluar.

![Menu interaktif "Chat, Code, & Work" saat mengetik ollama tanpa argumen](../../resources/images/ollama-setup/ollama-terminal-menu.png)

Perintah yang benar-benar dipakai sepanjang training ini selalu jelas dan spesifik (`ollama run`, `ollama pull`, `ollama list`, dst.) — bukan lewat menu tersebut.

> 📎 **Catatan — upload gambar di GUI:** kalau Anda mencoba upload gambar/screenshot di jendela chat ini dengan model `llama3.2:3b`, akan muncul error **"This model does not support images"**. Ini karena `llama3.2:3b` adalah varian **text-only** — kemampuan vision (memahami gambar) hanya ada di varian Llama 3.2 yang jauh lebih besar (`11b`/`90b`), yang butuh RAM jauh di atas rekomendasi training ini (lihat section 5.1). Kalau butuh model yang bisa membaca gambar/screenshot, model vision paling direkomendasikan saat ini adalah `qwen3-vl:8b` (~6.1 GB, kuat untuk OCR/dokumen, multilingual) — di luar cakupan default training ini, tapi bisa dicoba mandiri: `ollama pull qwen3-vl:8b`, lalu pilih model tersebut di dropdown sebelum upload gambar.

**Ringkasan CLI vs GUI:**

| Aspek | Terminal (CLI) | GUI (Ollama Chat) |
|---|---|---|
| Cocok untuk | Scripting, otomatisasi, worksheet praktik (Bagian 1-2) | Eksplorasi cepat tanpa command line |
| Ganti model | `ollama run <model-lain>` | Dropdown pemilih model |
| Risiko salah pakai model cloud | Kecil (nama model diketik eksplisit) | Ada — dropdown bisa default ke model cloud |
| Dipakai kode `nala/` (Module 4+)? | Tidak — kode bicara langsung ke API | Tidak — kode bicara langsung ke API |

---

## 5. Perbandingan Model yang Tersedia

Tabel berikut menunjukkan rekomendasi model untuk berbagai use case:

| Model | Ukuran | RAM Min. | Kecepatan | Kualitas Bahasa Indonesia | Catatan |
|-------|--------|----------|-----------|--------------------------|---------|
| `llama3.2:1b` | 1 GB | 4 GB | ⚡ Sangat Cepat | Baik | Ideal untuk devices terbatas; cocok untuk klasifikasi sederhana |
| `llama3.2:3b` | 2 GB | 6 GB | ⚡ Cepat | Sangat Baik | **DEFAULT RECOMMENDED** - best balance untuk training; layak untuk Q&A |
| `mistral:7b` | 4 GB | 8 GB | Sedang | Baik | General-purpose; lebih presisi dari Llama di benchmark |
| `qwen2.5:7b` | 4 GB | 8 GB | Sedang | Sangat Baik | Optimized untuk Bahasa Indonesia; bagus untuk NLP tasks |

**Rekomendasi untuk Task di Training Ini:**
- **Default Model**: `llama3.2:3b` - ringan, cepat, dan cukup berkualitas untuk pembelajaran
- **Jika RAM terbatas**: gunakan `llama3.2:1b`
- **Jika ingin kualitas lebih tinggi**: gunakan `qwen2.5:7b` atau `mistral:7b`

**Cara Download Alternatif Model:**
```bash
ollama pull qwen2.5:7b
ollama pull mistral:7b
```

### 5.1 Cara Menghitung Kebutuhan RAM/VRAM

Angka "RAM Min." di tabel atas bukan angka sembarangan — ada perhitungan di baliknya. Memahami cara hitungnya berguna kalau Anda ingin coba model lain yang tidak ada di tabel (misalnya `llama3.2:70b` atau model dari `ollama.com/library`).

**Formula dasar:**
```
Kebutuhan Memory (GB) ≈ Jumlah Parameter (Miliar) × Bytes per Parameter (quantization) + Overhead KV Cache & OS
```

**Tabel pengali berdasarkan quantization** (level kompresi model — semakin rendah bit, semakin kecil ukuran tapi kualitas sedikit turun). Angka bits/weight diambil dari dokumentasi resmi llama.cpp — mesin inference yang dipakai Ollama di balik layar (lihat Referensi di akhir modul):

| Quantization | Bits/Weight (resmi) | Bytes/Parameter | Keterangan |
|---|---|---|---|
| FP32 (full precision) | 32 | 4 byte | Kualitas maksimal, jarang dipakai untuk local inference |
| F16 | 16.0005 | 2 byte | Kualitas tinggi, dipakai untuk training/fine-tuning |
| Q8_0 | 8.5008 | ~1.06 byte | Kompresi ringan, kualitas hampir setara F16 |
| **Q4_K_M** (default Ollama) | 4.8944 | ~0.61 byte | Best balance — inilah yang otomatis dipakai saat `ollama pull` tanpa tag khusus |
| Q4_K_S | 4.6672 | ~0.58 byte | Sedikit lebih kecil dari Q4_K_M, kualitas sedikit lebih rendah |

**Contoh perhitungan nyata** (diambil dari log aktual Ollama menjalankan `llama3.2:3b`):
```
model params = 3.21 B
file type    = Q4_K_M (Medium)
file size    = 1.87 GiB
```
Artinya: 3.21 miliar parameter × ~0.61 byte/parameter ≈ 1.96 GB — mendekati 1.87 GiB aktual (selisih kecil karena beberapa tensor seperti embedding/output layer tetap disimpan di presisi lebih tinggi/F32, bukan ikut dikuantisasi ke Q4_K_M). Ini juga cocok dengan kolom "Ukuran" (~2 GB) di tabel section 5.

**Jangan lupakan KV Cache** — ini bagian yang sering terlewat. Selain ukuran file model, Ollama juga mengalokasikan memory tambahan untuk *KV cache* (menyimpan konteks percakapan yang sedang diproses). Dari log yang sama:
```
llama_kv_cache: size = 3584.00 MiB (32768 cells, 28 layers, 1 seqs)
```
Untuk model 3B dengan context length 32768 token, KV cache-nya sendiri memakan **~3.5 GB** — hampir dua kali lipat ukuran file model! Semakin panjang context length yang dipakai (`OLLAMA_CONTEXT_LENGTH`), semakin besar KV cache yang dibutuhkan.

**Rule of thumb praktis untuk estimasi cepat:**
```
RAM/VRAM Minimum ≈ (Ukuran File Model × 2) + 1 GB (overhead OS & aplikasi lain)
```
Contoh: model 2 GB (`llama3.2:3b`) → estimasi kebutuhan real ≈ (2 × 2) + 1 = **5 GB**, dibulatkan ke atas jadi rekomendasi 6 GB di tabel.

**Catatan tambahan:**
- Di GPU (Apple Silicon/Metal atau Nvidia/CUDA), yang paling menentukan adalah **VRAM tersedia**, bukan RAM sistem. Log `gpu memory ... available="25.0 GiB"` menunjukkan berapa VRAM yang bisa dipakai untuk offload layer model.
- Kalau VRAM tidak cukup untuk menampung model + KV cache, Ollama akan otomatis offload sebagian layer ke CPU (lebih lambat) — lihat kembali penjelasan `offloaded X/29 layers to GPU` di section 4.4.
- Kalau ingin hemat memory tanpa ganti model, kurangi context length lewat environment variable `OLLAMA_CONTEXT_LENGTH` (misalnya dari 32768 ke 4096) — KV cache akan mengecil proporsional.

---

## 6. Praktik Evaluasi Manual

Dalam section ini, Anda akan membandingkan respons dari dua model berbeda terhadap pertanyaan yang sama, kemudian mengevaluasi kualitas dan kecepatan mereka.

### 6.1 Setup Awal

1. Pastikan `ollama serve` sedang berjalan
2. Buka dua terminal/PowerShell windows

### 6.2 Pertanyaan Evaluasi

Gunakan **3 pertanyaan berikut** untuk mengevaluasi model:

**Pertanyaan 1 (Penjelasan Konsep):**
```bash
ollama run llama3.2:3b "Apa perbedaan antara machine learning dan deep learning? Jelaskan dalam 2-3 kalimat."
```

**Pertanyaan 2 (Terjemahan & Adaptasi Bahasa Indonesia):**
```bash
ollama run llama3.2:3b "Jelaskan konsep 'overfitting' dalam training model machine learning, menggunakan bahasa Indonesia yang mudah dipahami."
```

**Pertanyaan 3 (Kode & Penjelasan Teknis):**
```bash
ollama run llama3.2:3b "Tuliskan contoh singkat Python script untuk load model dari Hugging Face dan lakukan inference. Sertakan komentar penjelasan."
```

### 6.3 Worksheet Evaluasi Manual

Catat hasil Anda di tabel berikut. Anda dapat menjalankan pertanyaan yang sama ke model berbeda (misalnya `llama3.2:1b` vs `llama3.2:3b`, atau `llama3.2:3b` vs `qwen2.5:7b`):

| Aspek Evaluasi | Model 1: _____________ | Model 2: _____________ |
|---|---|---|
| **Pertanyaan 1: Perbedaan ML vs DL** | | |
| Kejelasan jawaban (1-5) | ☐ | ☐ |
| Akurasi konsep (1-5) | ☐ | ☐ |
| Waktu eksekusi | ☐ detik | ☐ detik |
| | | |
| **Pertanyaan 2: Overfitting** | | |
| Kejelasan jawaban (1-5) | ☐ | ☐ |
| Relevansi ke Bahasa Indonesia (1-5) | ☐ | ☐ |
| Waktu eksekusi | ☐ detik | ☐ detik |
| | | |
| **Pertanyaan 3: Kode Python** | | |
| Kode sintaks benar (1-5) | ☐ | ☐ |
| Komentar penjelasan jelas (1-5) | ☐ | ☐ |
| Waktu eksekusi | ☐ detik | ☐ detik |
| | | |
| **Overall** | | |
| Model mana yang lebih baik? | ☐ Model 1 / ☐ Model 2 / ☐ Tergantung task | |
| Alasan singkat | | |
| Mana yang lebih cepat? | ☐ Model 1 | ☐ Model 2 |

### 6.4 Cara Mengukur Waktu Eksekusi

Di bash/PowerShell, gunakan `time` command (macOS/Linux) atau measure waktu manual:

**macOS/Linux:**
```bash
time ollama run llama3.2:3b "Pertanyaan Anda di sini"
```
Lihat baris `real` untuk total waktu eksekusi.

**Windows PowerShell:**
```powershell
Measure-Command {ollama run llama3.2:3b "Pertanyaan Anda di sini"}
```

**Manual (semua platform):**
- Catat waktu sebelum menjalankan command (lihat jam)
- Jalankan command
- Catat waktu sesudah command selesai
- Selisih = waktu eksekusi

---

## 7. Troubleshooting Umum

### Masalah: Model Berjalan Terlalu Lambat

**Penyebab:**
- Model terlalu besar untuk spesifikasi hardware Anda
- RAM tidak cukup

**Solusi:**
1. Gunakan model yang lebih kecil:
   ```bash
   ollama pull llama3.2:1b
   ollama run llama3.2:1b "pertanyaan"
   ```
2. Tutup aplikasi lain yang memakan RAM
3. Cek RAM available dengan:
   - **macOS/Linux**: `free -h` atau `top`
   - **Windows**: Buka Task Manager, lihat Memory usage

### Masalah: "Connection refused" atau Ollama tidak terkoneksi

**Penyebab:**
- `ollama serve` tidak berjalan
- Port 11434 sudah dipakai aplikasi lain

**Solusi:**
1. Pastikan `ollama serve` sedang jalan di terminal/background:
   ```bash
   ollama serve
   ```
2. Jika port 11434 sudah dipakai, stop Ollama dan cek process:
   - **macOS/Linux**: `lsof -i :11434`
   - **Windows**: `netstat -ano | findstr :11434`
3. Kill process yang menggunakan port, atau restart Ollama

### Masalah: "Out of Memory" Error

**Penyebab:**
- Model terlalu besar untuk RAM sistem

**Solusi:**
1. Gunakan model lebih kecil (lihat section 5 untuk recommendations)
   ```bash
   ollama pull llama3.2:1b
   ```
2. Tambah virtual memory/swap (temporary):
   - **macOS**: Biasanya otomatis
   - **Linux**: Configure swap
   - **Windows**: Ubah virtual memory di System Properties
3. Upgrade RAM (long-term)

### Masalah: Model Download Gagal atau Lambat

**Penyebab:**
- Koneksi internet lambat
- Disk penuh

**Solusi:**
1. Cek koneksi internet Anda
2. Cek ruang disk:
   ```bash
   df -h  # macOS/Linux
   ```
3. Hapus model lama yang tidak dipakai:
   ```bash
   ollama rm llama3.2:3b  # remove model
   ```
4. Coba download ulang:
   ```bash
   ollama pull llama3.2:3b
   ```

### Masalah: API Endpoint Tidak Responsif

**Penyebab:**
- Server Ollama crashed atau tidak berjalan
- Firewall memblokir localhost:11434

**Solusi:**
1. Restart Ollama service:
   ```bash
   # Terminate running ollama serve
   # Then start again:
   ollama serve
   ```
2. Test connectivity:
   ```bash
   curl http://localhost:11434/api/tags
   ```
   Jika response JSON diterima, server berjalan normal.

### Masalah: Model Download di Lokasi yang Salah

**Penyebab:**
- Folder model Ollama tidak ditemukan atau terletak di lokasi custom

**Solusi:**
- Default model locations:
  - **macOS**: `~/.ollama/models`
  - **Linux**: `~/.ollama/models`
  - **Windows**: `C:\Users\<USERNAME>\.ollama\models`
- Untuk mengubah lokasi, set environment variable:
  ```bash
  export OLLAMA_MODELS=/path/to/custom/location  # macOS/Linux
  set OLLAMA_MODELS=C:\path\to\custom\location    # Windows
  ```

---

## Ringkasan & Next Steps

Anda telah belajar:
✅ Mengapa menggunakan Ollama untuk LLM lokal  
✅ Instalasi Ollama di platform Anda  
✅ Download dan menjalankan model pertama  
✅ Perbandingan berbagai model  
✅ Evaluasi manual respons model  
✅ Troubleshooting masalah umum  

**Next Module**: Anda akan melanjutkan ke Module 3 untuk mempelajari prompt engineering dengan model lokal yang baru saja Anda setup.

## Referensi

- Angka bits/weight per tipe quantization (section 5.1) — [llama.cpp Quantization README, ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp/blob/master/tools/quantize/README.md). Ollama memakai llama.cpp sebagai inference engine di balik layar, sehingga skema quantization GGUF ini berlaku sama.
- Data model params, file size, dan KV cache size (section 4.4 & 4.1) — diambil langsung dari log real `ollama serve` menjalankan `llama3.2:3b` (Ollama v0.33.2) pada sesi praktik modul ini, bukan dari dokumentasi eksternal.
- Penjelasan GUI vs Terminal dan screenshot (section 4.5) — diadaptasi dari materi `AI_LLM_OFFLINE/Day 1/Module-02-Ollama-Setup/materi.md` (program pelatihan terkait, repo terpisah); gambar disalin ke `resources/images/ollama-setup/` milik AI_NALA_ENTERPRISE agar repo ini tetap mandiri.
- Rekomendasi model vision & ukuran download (catatan section 4.5) — [ollama.com/library/qwen3-vl](https://ollama.com/library/qwen3-vl), [ollama.com/library/llama3.2-vision](https://ollama.com/library/llama3.2-vision).

---

## Panduan Praktik

Panduan hands-on module ini ada di file terpisah: **[WORKSHEET-Percobaan-Ollama.md](./WORKSHEET-Percobaan-Ollama.md)** — mencakup instalasi Ollama, menjalankan model pertama, dan praktik evaluasi manual (latency, kualitas jawaban, perbandingan model).

Worksheet tersebut menggunakan Ollama yang terinstall **langsung di laptop** (bukan di dalam container). Setup Ollama versi containerized (di dalam Docker, untuk aplikasi NALA) baru dilakukan di **Module 4** (`Module-04-Setup-Infra-Docker-Compose/materi.md`, bagian Panduan Praktik).

**Praktik lanjutan (gabungan dengan Module 3):** setelah menyelesaikan Module 3 (draft system prompt + `nala-v1`), kerjakan **[WORKSHEET-Evaluasi-Dampak-Prompt-Engineering.md](../Module-03-Prompt-Engineering-Dasar/WORKSHEET-Evaluasi-Dampak-Prompt-Engineering.md)** di folder Module 3 — menggabungkan metodologi evaluasi manual module ini dengan teknik prompt engineering, untuk mengukur dampak nyata system prompt terhadap kualitas dan konsistensi jawaban.

**Sesi panjang alternatif (3-4 jam, dari nol):** kalau Anda ingin mengerjakan instalasi Ollama module ini sampai prompt engineering Module 3 dalam satu sesi panjang tanpa jeda, pakai **[PANDUAN-PRAKTIK-Sesi-Gabungan-Ollama-Prompt-Engineering.md](../Module-03-Prompt-Engineering-Dasar/PANDUAN-PRAKTIK-Sesi-Gabungan-Ollama-Prompt-Engineering.md)** di folder Module 3 — 20 Langkah berurutan dari `ollama --version` sampai eksperimen `temperature`, dengan estimasi waktu per Langkah.
