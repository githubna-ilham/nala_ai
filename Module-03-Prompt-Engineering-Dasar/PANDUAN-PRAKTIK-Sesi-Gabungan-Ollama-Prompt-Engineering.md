# Panduan Praktik Sesi Gabungan — Ollama dari Nol sampai Prompt Engineering (Module 2 + Module 3)

Ini adalah panduan praktik **berdiri sendiri** (terpisah dari `Module-02-Setup-Ollama-Evaluasi-Model/materi.md` bagian Panduan Praktik, `Module-02-Setup-Ollama-Evaluasi-Model/WORKSHEET-Percobaan-Ollama.md`, `Module-03-Prompt-Engineering-Dasar/materi.md` bagian Panduan Praktik, dan `WORKSHEET-Evaluasi-Dampak-Prompt-Engineering.md`) yang menggabungkan **seluruh** praktik Module 2 dan Module 3 jadi satu sesi hands-on berurutan, mulai dari instalasi Ollama di laptop yang masih kosong sampai eksplorasi lengkap semua parameter generasi, perbandingan multi-model, environment variable konfigurasi service, dan pemanggilan REST API Ollama langsung (persis yang akan dipakai kode Python di Module 4). Dirancang untuk dikerjakan dalam **satu sesi sangat panjang (8-9 jam, sangat disarankan dipecah jadi beberapa sesi)**, dengan estimasi waktu di tiap Langkah supaya Anda bisa mengatur ritme dan istirahat.

**Kenapa digabung jadi satu file terpisah?** Module 2 dan Module 3 masing-masing punya materi & worksheet sendiri yang bisa dikerjakan terpisah di hari/sesi berbeda. Panduan ini untuk skenario sebaliknya: kalau kita punya blok waktu panjang (misal workshop setengah hari) dan ingin mengerjakan instalasi sampai prompt engineering **tanpa jeda**, dengan satu alur Langkah yang mengalir dari awal ke akhir.

## Prasyarat

- Laptop dengan **minimal 16GB RAM** (lihat `README.md` root — Prasyarat Komputer)
- **Belum perlu** Docker Desktop untuk panduan ini — semua praktik di sini berjalan langsung di laptop (bukan container). Docker baru dibutuhkan mulai Module 4.
- Koneksi internet stabil (untuk download installer Ollama + model, sekitar 2-3GB)
- Text editor (VS Code, Notepad, TextEdit, atau apa saja) untuk membuat file `Modelfile` di Langkah 18
- Waktu blok kosong 3-4 jam tanpa gangguan

**Estimasi total waktu:** ~530-550 menit / 8,8-9,2 jam (mengikuti rincian per Langkah di bawah), belum termasuk waktu download model tambahan di Bagian F (bervariasi tergantung kecepatan internet — `qwen2.5:7b`/`mistral:7b` masing-masing ~4GB, bisa 15-30 menit).

---

## Bagian A: Instalasi & Percobaan Dasar (Langkah 1-8, ~95 menit)

### Langkah 1: Instal Ollama (~15 menit)

Pilih sesuai sistem operasi Anda.

**macOS — Opsi 1: Homebrew (disarankan)**
```bash
brew install ollama
```

**macOS — Opsi 2: Download manual**
1. Kunjungi [ollama.com](https://ollama.com), klik "Download", pilih "macOS"
2. Download file `.dmg`, jalankan installer, ikuti instruksi

**Windows**
1. Kunjungi [ollama.com](https://ollama.com), klik "Download", pilih "Windows"
2. Download `OllamaSetup.exe`, jalankan, ikuti wizard instalasi
3. Ollama otomatis berjalan sebagai Windows service di background setelah instalasi selesai — cek ikon di system tray

**Linux (Ubuntu/Debian/Fedora/RHEL)**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```
Alternatif manual: download dari [ollama.com/download/linux](https://ollama.com/download/linux), extract, jalankan `./ollama`.

**Checkpoint — verifikasi instalasi (semua OS):**
```bash
ollama --version
```
Harus muncul output seperti `ollama version X.X.X`. Kalau muncul `command not found`, instalasi belum berhasil — ulangi langkah di atas atau cek PATH environment variable.

### Langkah 2: Nyalakan Ollama Service (~5 menit)

**macOS/Windows:** aplikasi Ollama biasanya sudah berjalan otomatis di background (cek ikon menu bar/system tray). Kalau belum:
```bash
ollama serve
```
Biarkan terminal ini terbuka (service berjalan di foreground) — buka terminal **baru** untuk perintah-perintah selanjutnya.

**Linux:**
```bash
ollama serve
```
Sama seperti di atas, biarkan berjalan di terminal terpisah.

**Checkpoint:** buka terminal baru, jalankan `curl http://localhost:11434` — harus muncul `Ollama is running`. Kalau muncul `Connection refused`, service belum jalan — ulangi Langkah ini.

### Langkah 3: Download Model Pertama (~10-15 menit, tergantung koneksi)

```bash
ollama pull llama3.2:3b
```

Model ini berukuran ~1.87GB — proses download akan menampilkan progress bar. Sambil menunggu, baca sekilas kenapa model ini yang dipilih: model 3B parameter, sudah mendukung tool-calling (dipakai nanti di Module 20), cukup kecil untuk berjalan nyaman di laptop 16GB RAM sekaligus menjalankan service lain (OpenSearch, PostgreSQL, dst di modul-modul berikutnya).

**Checkpoint:**
```bash
ollama list
```
`llama3.2:3b` harus muncul di daftar.

### Langkah 4: Jalankan Pertanyaan Pertama & Baca Log (~10 menit)

```bash
ollama run llama3.2:3b "Tuliskan 3 keuntungan machine learning dalam bentuk list"
```

Perhatikan output di terminal tempat `ollama serve` berjalan (Langkah 2) — akan muncul log seperti:
```
load_tensors: offloaded 29/29 layers to GPU
```
`offloaded 29/29 layers to GPU` berarti seluruh layer model berhasil dipindah ke GPU (Metal di Apple Silicon, CUDA di Nvidia) — model akan berjalan lebih cepat. Kalau cuma sebagian ter-offload, sisanya diproses CPU (lebih lambat), biasanya karena VRAM terbatas.

Lalu akan muncul dua metrik timing:
```
prompt eval time = 109.77 ms / 31 tokens (282.42 tokens per second)
eval time        = 204.42 ms / 12 tokens ( 53.81 tokens per second)
```
- **Prompt eval** = kecepatan model "membaca" pertanyaan Anda
- **Eval** = kecepatan model "menulis" jawaban token-per-token — angka inilah yang paling menentukan seberapa cepat jawaban terasa muncul

**Checkpoint — catat angka Anda sendiri:**

| Metrik | Nilai Anda |
|---|---|
| Layers ter-offload ke GPU | ___/___ |
| Eval speed (tokens/detik) | ___ |

### Langkah 5: Mode Single-Shot vs Interaktif (~10 menit)

**Single-shot** (satu pertanyaan, keluar otomatis):
```bash
ollama run llama3.2:3b "Sebutkan 3 kegunaan AI di industri keuangan"
```

**Interaktif** (sesi berkelanjutan):
```bash
ollama run llama3.2:3b
```
Setelah muncul prompt `>>>`, ajukan pertanyaan, lalu ajukan pertanyaan lanjutan yang merujuk jawaban sebelumnya, contoh: `Jelaskan lebih detail poin nomor 2`. Ketik `/exit` untuk keluar.

**Checkpoint — jawab sendiri:**
| Observasi | Jawaban Anda |
|---|---|
| Apakah mode interaktif "ingat" konteks pertanyaan sebelumnya? | |
| Giliran pertanyaan ke-2 di mode interaktif terasa lebih cepat dari giliran pertama — kenapa? (petunjuk: *prompt caching*/KV-cache, model me-reuse bagian percakapan yang mirip lewat teknik *Longest Common Prefix*, tidak memproses ulang seluruh histori dari nol) | |

### Langkah 6: Melihat Model yang Sedang Berjalan (~5 menit)

```bash
ollama ps
```

| Field Output | Artinya |
|---|---|
| `NAME` | Nama model yang sedang di-load di memori |
| `SIZE` | Ukuran model di memori (RAM/VRAM) |
| `PROCESSOR` | Persentase diproses CPU vs GPU |
| `UNTIL` | Kapan model akan di-unload otomatis dari memori kalau tidak dipakai |

```bash
ollama list
```
Catat model apa saja yang sudah ter-pull di laptop Anda.

### Langkah 7: GUI vs Terminal (~10 menit)

1. Jalankan pertanyaan yang sama persis lewat terminal:
   ```bash
   ollama run llama3.2:3b "Ringkas dalam 1 kalimat: apa itu suku bunga acuan?"
   ```
2. Buka aplikasi Ollama Chat (ikon di menu bar/system tray), pastikan dropdown model sudah `llama3.2:3b` (**bukan** model cloud yang biasanya bertanda `*.cloud`), lalu ajukan pertanyaan persis sama di kotak chat.

**Checkpoint:**
| Observasi | Jawaban Anda |
|---|---|
| Apakah jawaban dari terminal dan GUI konsisten (isi & gaya mirip)? | |
| Mana yang lebih praktis untuk demo cepat ke audiens non-teknis: terminal atau GUI? Kenapa? | |

### Langkah 8: Batasan Model — Coba Upload Gambar (~5 menit)

Di jendela GUI Ollama Chat (model masih `llama3.2:3b`), coba upload file gambar/screenshot apa saja lewat tombol `+`.

**Checkpoint:**
| Observasi | Jawaban Anda |
|---|---|
| Pesan error apa yang muncul? | |
| Kenapa error ini muncul — apa bedanya `llama3.2:3b` dari model vision seperti `qwen3-vl:8b`? | |
| Untuk NALA (chatbot berbasis teks SOP & data operasional), apakah kemampuan vision ini dibutuhkan? | |

---

## Bagian B: Knowledge Cutoff, RAM, dan Evaluasi Model (Langkah 9-12, ~70 menit)

### Langkah 9: Cek Knowledge Cutoff Model (~15 menit)

**Knowledge cutoff** adalah batas waktu data training model — model tidak tahu apa pun setelah tanggal tersebut, dan tidak otomatis update seperti mesin pencari.

Jalankan keempat pertanyaan berikut:
```bash
ollama run llama3.2:3b "Kapan data training kamu berakhir? Sebutkan bulan dan tahun perkiraan knowledge cutoff kamu."
```
```bash
ollama run llama3.2:3b "Siapa Presiden Indonesia saat ini?"
```
```bash
ollama run llama3.2:3b "Apa kebijakan suku bunga acuan Bank Indonesia bulan ini?"
```
```bash
ollama run llama3.2:3b "Versi terbaru dari model Llama berapa?"
```

**Checkpoint:**

| Pertanyaan | Jawaban Model (ringkas) | Benar / Salah / Mengaku Tidak Tahu |
|---|---|---|
| Knowledge cutoff model | | ☐ Benar ☐ Salah ☐ Mengaku tidak tahu |
| Presiden Indonesia saat ini | | ☐ Benar ☐ Salah ☐ Mengaku tidak tahu |
| Suku bunga BI bulan ini | | ☐ Benar ☐ Salah ☐ Mengaku tidak tahu |
| Versi terbaru Llama | | ☐ Benar ☐ Salah ☐ Mengaku tidak tahu |

**Refleksi:** Apakah model pernah menjawab percaya diri padahal salah/kedaluwarsa (*hallucination*)? Beri contoh dari tabel di atas.

### Langkah 10: Pengantar Singkat ke RAG (~10 menit, diskusi/refleksi, tanpa kode)

Dari Langkah 9, Anda sudah membuktikan sendiri dua keterbatasan mendasar LLM lokal:
1. **Knowledge cutoff** — tidak tahu kejadian setelah tanggal training
2. **Tidak ada akses ke data privat/internal** — model dasar dilatih dari data publik, bukan dokumen SOP PT Nusantara Finance

Kedua keterbatasan ini adalah alasan utama kenapa Module 7 dan seterusnya memperkenalkan **RAG (Retrieval-Augmented Generation)**: alih-alih berharap model "sudah tahu" dari hasil training, sistem **mencari (retrieve)** potongan dokumen relevan lebih dulu, menyisipkannya ke prompt sebagai konteks tambahan, baru model menjawab berdasarkan konteks itu — bukan hanya dari memori training-nya.

**Refleksi:** Bayangkan Anda bertanya ke NALA: *"Apa syarat pengajuan restrukturisasi kredit untuk nasabah yang telat bayar 3 bulan?"* — kenapa `llama3.2:3b` tanpa RAG kemungkinan besar akan menjawab ngasal atau generik untuk pertanyaan ini? Dokumen apa yang perlu di-retrieve lebih dulu supaya NALA bisa menjawab akurat?

### Langkah 11: Hitung RAM/VRAM Model (~20 menit)

Formula: `Kebutuhan Memory (GB) ≈ Jumlah Parameter (Miliar) × Bytes per Parameter (quantization)`. Untuk quantization default Q4_K_M, bytes/parameter ≈ 0.61.

1. Buka [ollama.com/library](https://ollama.com/library), cari model **`qwen3-vl:8b`**, catat jumlah parameter (dari nama tag), ukuran file download, dan tipe quantization default.
2. Hitung manual: parameter × 0.61 = ___ GB, lalu bandingkan dengan ukuran file asli di halaman library. Berapa selisihnya (%)? (Selisih wajar terjadi karena tensor tertentu tetap disimpan F32 penuh, bukan ter-quantize semua.)
3. Estimasi RAM minimum pakai rule of thumb `(ukuran file × 2) + 1 GB`:

| Model | Ukuran File | Estimasi RAM Minimum |
|---|---|---|
| `llama3.2:3b` | ~1.87 GB | ~5 GB |
| `qwen3-vl:8b` (hitungan Anda) | ___ | ___ |

**Refleksi:** Kalau laptop Anda hanya punya 8GB RAM total, apakah `qwen3-vl:8b` masih aman dijalankan bersamaan aplikasi lain (browser, IDE)?

### Langkah 12: Evaluasi Manual — Bandingkan Kecepatan & Kualitas (~25 menit)

Jalankan tiga pertanyaan berikut, ukur waktu eksekusi pakai `time` (macOS/Linux) atau `Measure-Command` (PowerShell):

```bash
time ollama run llama3.2:3b "Apa perbedaan antara machine learning dan deep learning? Jelaskan dalam 2-3 kalimat."
```
```bash
time ollama run llama3.2:3b "Jelaskan konsep 'overfitting' dalam training model machine learning, menggunakan bahasa Indonesia yang mudah dipahami."
```
```bash
time ollama run llama3.2:3b "Tuliskan contoh singkat Python script untuk load model dari Hugging Face dan lakukan inference. Sertakan komentar penjelasan."
```
Lihat baris `real` untuk total waktu eksekusi.

**Checkpoint:**

| Pertanyaan | Kejelasan Jawaban (1-5) | Akurasi (1-5) | Waktu (`real`) |
|---|---|---|---|
| ML vs DL | | | ___ detik |
| Overfitting | | | ___ detik |
| Kode Python | | | ___ detik |

**Opsional (kalau punya waktu lebih):** ulangi ketiga pertanyaan dengan model lain yang sudah Anda pull (misal `llama3.2:1b`), bandingkan kecepatan vs kualitas — model lebih kecil biasanya lebih cepat tapi jawabannya kurang detail/akurat.

---

## Bagian C: Prompt Engineering — Konsep & Menyusun System Prompt NALA (Langkah 13-16, ~65 menit)

### Langkah 13: Anatomi System Prompt yang Baik (~10 menit, baca + diskusi)

Buka `materi.md` Bagian 1 module ini — pelajari komponen utama system prompt yang baik: **Persona** (siapa asisten ini), **Tugas Utama** (apa yang boleh dijawab), **Batasan** (apa yang tidak boleh dijawab/dilakukan), **Format Output** (bagaimana jawaban disusun).

**Checkpoint diskusi:** sebutkan satu contoh chatbot/asisten AI yang pernah Anda pakai (ChatGPT, Siri, dll) — komponen mana dari keempat di atas yang menurut Anda paling terlihat jelas dari cara dia menjawab?

### Langkah 14: Zero-Shot vs Few-Shot (~15 menit, praktik)

**Zero-shot** (tanpa contoh, model menebak format sendiri):
```bash
ollama run llama3.2:3b "Klasifikasikan sentimen kalimat berikut: 'Pelayanan customer service sangat lambat dan tidak membantu.'"
```

**Few-shot** (dengan 2-3 contoh format yang diinginkan sebelum pertanyaan asli):
```bash
ollama run llama3.2:3b
```
Di mode interaktif, ketik (satu blok):
```
Klasifikasikan sentimen kalimat menjadi Positif/Negatif/Netral.

Contoh:
Kalimat: "Prosesnya cepat dan stafnya ramah."
Sentimen: Positif

Kalimat: "Biasa saja, tidak ada yang istimewa."
Sentimen: Netral

Sekarang klasifikasikan:
Kalimat: "Pelayanan customer service sangat lambat dan tidak membantu."
Sentimen:
```

**Checkpoint:**
| Observasi | Jawaban Anda |
|---|---|
| Apakah format jawaban zero-shot konsisten dengan yang Anda inginkan (cuma satu kata: Positif/Negatif/Netral)? | |
| Apakah few-shot menghasilkan format yang lebih konsisten/sesuai harapan? | |

### Langkah 15: Structured Output — Kenapa Penting untuk Model Kecil (~10 menit, baca + praktik singkat)

Baca `materi.md` Bagian 3 module ini soal kenapa structured output (format terstruktur seperti JSON, atau format terlabel jelas) penting terutama untuk model kecil yang lebih mudah "melenceng" dari format bebas.

**Praktik singkat:** minta model menjawab dalam format terstruktur eksplisit:
```bash
ollama run llama3.2:3b "Ekstrak informasi berikut dari teks ini dalam format:
Nama: ...
Jumlah Pinjaman: ...
Tujuan: ...

Teks: Budi mengajukan pinjaman sebesar 50 juta rupiah untuk modal usaha warung makannya."
```

**Checkpoint:** apakah model mengikuti format `Nama: / Jumlah Pinjaman: / Tujuan:` yang diminta, atau menyimpang ke format bebas?

### Langkah 16: Menyusun System Prompt NALA v1 (~30 menit)

Sekarang susun draft **System Prompt NALA v1** Anda sendiri, mengisi template di `materi.md` Bagian 5 module ini:

```markdown
# System Prompt NALA v1 - Template

## Persona
[Isi di sini]

## Tugas Utama
[Isi di sini]

## Batasan (Do's & Don'ts)
### Yang Boleh Dijawab:
[Isi di sini]

### Yang TIDAK Boleh Dijawab:
[Isi di sini]

## Format Output
[Isi di sini]

## Contoh Pertanyaan & Jawaban (Few-shot)
[Isi di sini, minimal 2 contoh]

## Catatan Tambahan
[Isi jika ada]
```

Kalau mengerjakan berpasangan (satu anggota non-teknis, satu teknis): anggota non-teknis menjelaskan kebutuhan bisnis NALA (~10 menit diskusi), lalu berdua mengisi template bersama (~15 menit draft), lalu review sekilas bersama (~5 menit refinement) — pastikan batasan dijelaskan konkret, bukan abstrak, dan instruksi tidak bertele-tele (ingat: model kecil butuh instruksi singkat & eksplisit, lihat `materi.md` Bagian 4).

Setelah draft selesai, bandingkan dengan contoh referensi di `materi.md` Bagian 6 — perhatikan bagaimana versi ringkas (yang jadi kode `NALA_SYSTEM_PROMPT`) berbeda dari versi terstruktur di template (versi terstruktur untuk tahap desain/diskusi, versi ringkas untuk produksi).

**Checkpoint:** draft `System Prompt NALA v1` Anda sudah lengkap — persona jelas, tugas fokus, batasan konkret dengan contoh perilaku, dan minimal 2 contoh few-shot.

---

## Bagian D: Menguji System Prompt Secara Nyata (Langkah 17-20, ~60 menit)

### Langkah 17: Uji Cepat via `/set system` (~10 menit)

```bash
ollama run llama3.2:3b
```
Setelah muncul prompt `>>>`, ketik (satu baris penuh):
```
/set system <tempel draft System Prompt NALA v1 Anda dari Langkah 16, dipadatkan jadi beberapa kalimat>
```

Ollama akan konfirmasi `Set system message.`. Coba langsung: `Siapa kamu?`

**Checkpoint:** jawaban model harus mencerminkan persona NALA (bukan "Saya adalah model bahasa AI..."). Kalau belum sesuai, ketik `/set system` lagi dengan draft yang direvisi — tidak perlu keluar dari sesi.

Perintah pendukung: `/show system` (lihat system prompt aktif), `/clear` (hapus system prompt & riwayat, mulai bersih), `/bye` (keluar).

> ⚠️ **Koreksi:** flag `ollama run --system "..."` **tidak tersedia** di versi Ollama saat ini (cek `ollama run --help`) — `/set system` di atas adalah cara yang benar-benar berfungsi.

### Langkah 18: Buat Model Persisten via Modelfile (~20 menit)

**Langkah A — Buat file (pakai text editor, bukan terminal):**

1. Buka text editor, buat file baru
2. Ketik:
   ```
   FROM llama3.2:3b
   SYSTEM """<tempel draft System Prompt NALA v1 Anda, dipadatkan>"""
   PARAMETER temperature 0.3
   PARAMETER num_ctx 4096
   ```
3. Simpan dengan nama persis `Modelfile` (**tanpa** ekstensi apa pun), di folder yang mudah diingat, misal `resources/starter-code/nala/`

**Langkah B — Build & jalankan (di Terminal):**
```bash
cd resources/starter-code/nala
ollama create nala-v1 -f Modelfile
ollama run nala-v1
```

`ollama create` membaca `Modelfile` di folder itu, lalu build model baru `nala-v1` dengan system prompt dan parameter sudah otomatis ter-set — tidak perlu `/set system` manual lagi.

**Kenapa `temperature 0.3`?** Parameter ini (rentang 0.0-1.0, default ~0.8) mengatur seberapa "kreatif"/acak jawaban model. Untuk asisten internal seperti NALA, nilai rendah (0.2-0.4) disarankan: jawaban lebih konsisten, lebih kecil kemungkinan mengarang. `num_ctx 4096` menaikkan context window dari default (sering 2048) supaya NALA bisa menyimpan percakapan lebih panjang tanpa "lupa" instruksi awal.

**Checkpoint:** setelah `ollama create` selesai (muncul `success`):
```bash
ollama list          # nala-v1 harus muncul
ollama run nala-v1
```
Coba dua pertanyaan: `Siapa kamu?` (harus mencerminkan persona NALA) dan `Siapa presiden Indonesia?` (sesuai batasan di system prompt, seharusnya tidak menjawab asal — mengarahkan kembali ke konteks PT Nusantara Finance atau mengaku di luar cakupan). Keluar dengan `/bye`.

### Langkah 19: Worksheet Evaluasi Dampak — Tiga Kondisi Berdampingan (~30 menit)

Ini bagian inti yang **mengukur** dampak nyata prompt engineering, menggabungkan metodologi evaluasi Bagian B dengan hasil Bagian C-D. Jalankan **tiga pertanyaan yang sama** di **tiga kondisi**, catat hasilnya.

**Pertanyaan uji (dipakai di ketiga kondisi):**
1. `Siapa kamu?`
2. `Apa syarat pengajuan kredit di PT Nusantara Finance?`
3. `Bagaimana cara membuat kue coklat yang lembut?`

**Kondisi 1 — Tanpa system prompt** (model polos):
```bash
ollama run llama3.2:3b "Siapa kamu?"
```
*(ulangi untuk pertanyaan 2 dan 3)*

**Kondisi 2 — Dengan `/set system` draft Anda** (dari Langkah 17, masih aktif kalau sesi belum ditutup, atau set ulang)

**Kondisi 3 — Model persisten `nala-v1`** (dari Langkah 18):
```bash
ollama run nala-v1 "Siapa kamu?"
```

**Checkpoint — tabel gabungan:**

| Aspek | Kondisi 1: Tanpa Prompt | Kondisi 2: `/set system` | Kondisi 3: `nala-v1` |
|---|---|---|---|
| Persona sesuai NALA? | ☐ | ☐ | ☐ |
| Jujur soal data tidak diketahui (bukan mengarang)? | ☐ | ☐ | ☐ |
| Menolak pertanyaan di luar topik (kue coklat)? | ☐ | ☐ | ☐ |
| Perlu diketik ulang tiap sesi baru? | — | ☐ Ya | ☐ Tidak (persisten) |

**Refleksi:** dari ketiga kondisi, mana yang paling siap dipakai sebagai fondasi `NALA_SYSTEM_PROMPT` di kode Python (Module 4)?

### Langkah 20: Eksperimen Konsistensi — Efek `temperature` (~20 menit)

Jalankan pertanyaan yang sama ke `nala-v1` (temperature 0.3) **3 kali berturut-turut**, keluar (`/bye`) dan jalankan ulang tiap kali supaya independen:
```bash
ollama run nala-v1 "Apa syarat pengajuan kredit di PT Nusantara Finance?"
```

Lalu edit `Modelfile`, ganti `PARAMETER temperature 0.3` jadi `PARAMETER temperature 0.9`, build dengan nama baru:
```bash
ollama create nala-v1-eksperimen -f Modelfile
```
Jalankan pertanyaan yang sama **3 kali lagi** ke `nala-v1-eksperimen`.

**Checkpoint:**

| Percobaan | temperature 0.3 | temperature 0.9 |
|---|---|---|
| 1 | | |
| 2 | | |
| 3 | | |

**Refleksi:** mana yang lebih konsisten antar percobaan? Untuk NALA versi produksi, `temperature` berapa yang lebih tepat?

**Bersih-bersih:** hapus model eksperimen setelah selesai:
```bash
ollama rm nala-v1-eksperimen
```

---

## Bagian E: Eksplorasi Lengkap Parameter Generasi (Langkah 21-29, ~85 menit)

Langkah 18-20 sudah memakai dua parameter (`temperature`, `num_ctx`) untuk `nala-v1`. Ollama sebenarnya punya jauh lebih banyak `PARAMETER` yang bisa diset lewat Modelfile — masing-masing memengaruhi gaya jawaban dengan cara berbeda. Bagian ini menguji **satu per satu**, memakai prompt yang sama supaya efeknya jelas terlihat, dan membandingkan hasil Anda dengan **hasil uji nyata** yang sudah didokumentasikan di `materi.md` Bagian 8 module ini (bukan contoh karangan — itu benar-benar output `llama3.2:3b`).

**Prompt uji yang dipakai di seluruh Bagian E** (kecuali disebutkan lain): *"Deskripsikan produk tabungan PT Nusantara Finance dalam satu kalimat promosi yang menarik."*

Untuk tiap Langkah: edit `Modelfile` Anda, ganti/tambah satu baris `PARAMETER`, build dengan nama baru, jalankan, catat hasil, lalu bandingkan dengan tabel "Sebelum vs Sesudah" di `materi.md` Bagian 8.

### Langkah 21: `top_k` — Mempersempit Pilihan Kata (~8 menit)

```
FROM llama3.2:3b
PARAMETER top_k 10
```
```bash
ollama create nala-topk -f Modelfile
ollama run nala-topk "Deskripsikan produk tabungan PT Nusantara Finance dalam satu kalimat promosi yang menarik."
```
Default `top_k` adalah 40 (memilih dari 40 token berpeluang tertinggi tiap langkah); di sini diturunkan ke 10 (lebih sempit, jawaban lebih "aman"/predictable).

**Checkpoint:** catat jawaban Anda, bandingkan dengan tabel `top_k` di `materi.md` Bagian 8 — apakah gaya bahasanya terasa lebih "generik"/kurang variatif dibanding jawaban default di Langkah 18?

### Langkah 22: `top_p` — Nucleus Sampling (~8 menit)

```
FROM llama3.2:3b
PARAMETER top_p 0.5
```
```bash
ollama create nala-topp -f Modelfile
ollama run nala-topp "Deskripsikan produk tabungan PT Nusantara Finance dalam satu kalimat promosi yang menarik."
```
Default 0.9 diturunkan ke 0.5 — token dipilih hanya dari kumpulan yang kumulatif probabilitasnya mencapai 50% teratas (jauh lebih sempit dari 90%).

**Checkpoint:** bandingkan dengan `materi.md` Bagian 8. `top_p` dan `top_k` sama-sama "mempersempit pilihan" tapi dengan mekanisme beda — menurut Anda, kapan `top_p` lebih masuk akal dipakai dibanding `top_k`?

### Langkah 23: `min_p` — Filter Kualitas Alternatif (~8 menit)

```
FROM llama3.2:3b
PARAMETER min_p 0.05
```
```bash
ollama create nala-minp -f Modelfile
ollama run nala-minp "Deskripsikan produk tabungan PT Nusantara Finance dalam satu kalimat promosi yang menarik."
```
`min_p` (default 0.0/nonaktif) membuang kandidat token yang probabilitasnya jauh di bawah token terbaik — alternatif yang lebih baru dari `top_p`.

**Checkpoint:** bandingkan hasil Anda dengan `materi.md` Bagian 8.

### Langkah 24: `repeat_penalty` — Mencegah Pengulangan (~10 menit)

Prompt khusus untuk Langkah ini (jawaban panjang lebih menunjukkan efek pengulangan): *"Jelaskan pentingnya SOP secara detail, buat sepanjang mungkin, minimal 150 kata."*

```
FROM llama3.2:3b
PARAMETER repeat_penalty 1.1
```
```bash
ollama create nala-rp -f Modelfile
ollama run nala-rp "Jelaskan pentingnya SOP secara detail, buat sepanjang mungkin, minimal 150 kata."
```
Lalu **ulangi dengan nilai ekstrem** untuk melihat efek sampingnya:
```
FROM llama3.2:3b
PARAMETER repeat_penalty 1.5
```
```bash
ollama create nala-rp-ekstrem -f Modelfile
ollama run nala-rp-ekstrem "Jelaskan pentingnya SOP secara detail, buat sepanjang mungkin, minimal 150 kata."
```

**Checkpoint:** baca temuan penting di `materi.md` Bagian 8 soal `repeat_penalty 1.5` — apakah jawaban `nala-rp-ekstrem` Anda juga mulai melenceng topik/tidak koheren seperti yang didokumentasikan? Ini contoh nyata **trade-off**: parameter yang menyelesaikan satu masalah (pengulangan) bisa menciptakan masalah baru (koherensi) kalau nilainya terlalu agresif.

### Langkah 25: `repeat_last_n` — Jendela Pengecekan Pengulangan (~8 menit)

```
FROM llama3.2:3b
PARAMETER repeat_penalty 1.3
PARAMETER repeat_last_n 256
```
```bash
ollama create nala-rln -f Modelfile
ollama run nala-rln "Jelaskan pentingnya SOP secara detail, buat sepanjang mungkin, minimal 150 kata."
```
`repeat_penalty` ditahan tetap di 1.3 (bukan default) supaya perbandingan dengan `materi.md` Bagian 8 adil — yang diuji murni efek jendela `repeat_last_n` yang diperlebar dari default 64 ke 256.

**Checkpoint:** bandingkan dengan tabel `repeat_last_n` di `materi.md` Bagian 8 — apakah jawaban Anda juga melenceng topik seperti temuan yang didokumentasikan?

### Langkah 26: `num_predict` — Batas Maksimal Token (~7 menit)

Prompt khusus: *"Jelaskan sejarah lengkap SOP perusahaan dari awal."*

```
FROM llama3.2:3b
PARAMETER num_predict 20
```
```bash
ollama create nala-np -f Modelfile
ollama run nala-np "Jelaskan sejarah lengkap SOP perusahaan dari awal."
```

**Checkpoint:** apakah jawaban Anda terpotong tepat di sekitar 20 token (kemungkinan besar di tengah kata/kalimat, persis seperti temuan di `materi.md` Bagian 8)? Parameter ini paling "bersih" efeknya dibanding parameter lain di Bagian E — kenapa?

### Langkah 27: `stop` — Menghentikan Generasi di Titik Tertentu (~7 menit)

Prompt khusus: *"Tulis angka 1 sampai 10 dipisah spasi, lalu tulis kata SELESAI di akhir."*

```
FROM llama3.2:3b
PARAMETER stop "SELESAI"
```
```bash
ollama create nala-stop -f Modelfile
ollama run nala-stop "Tulis angka 1 sampai 10 dipisah spasi, lalu tulis kata SELESAI di akhir."
```

**Checkpoint:** apakah generasi berhenti **tepat sebelum** kata "SELESAI" muncul (kata itu sendiri tidak ikut ditulis)? Untuk NALA, kapan menurut Anda parameter `stop` ini berguna (petunjuk: pola gagal umum pada model kecil — melanjutkan percakapan seolah dialog dengan dirinya sendiri, menulis ulang label seperti "Pertanyaan:")?

### Langkah 28: `seed` — Reproducibility (~10 menit)

Prompt khusus: *"Tulis satu kalimat unik tentang kucing."*

**Tanpa `seed`, jalankan 2x:**
```bash
ollama run llama3.2:3b "Tulis satu kalimat unik tentang kucing."
ollama run llama3.2:3b "Tulis satu kalimat unik tentang kucing."
```

**Dengan `seed`, jalankan 2x:**
```
FROM llama3.2:3b
PARAMETER seed 42
```
```bash
ollama create nala-seed -f Modelfile
ollama run nala-seed "Tulis satu kalimat unik tentang kucing."
ollama run nala-seed "Tulis satu kalimat unik tentang kucing."
```

**Checkpoint:**

| Kondisi | Run 1 | Run 2 | Identik? |
|---|---|---|---|
| Tanpa `seed` | | | ☐ Ya ☐ Tidak |
| Dengan `seed 42` | | | ☐ Ya ☐ Tidak |

Bandingkan dengan `materi.md` Bagian 8 — seharusnya dua run dengan `seed` sama menghasilkan jawaban **identik karakter-per-karakter**. Kenapa parameter ini berguna untuk testing/debugging tapi **tidak** dipakai untuk NALA versi produksi (petunjuk: tujuan produksi adalah jawaban yang stabil secara *kualitas*, bukan identik secara harfiah)?

### Langkah 29: Verifikasi & Bersih-Bersih Model Eksperimen (~10 menit)

Setelah Langkah 21-28, Anda punya cukup banyak model eksperimen (`nala-topk`, `nala-topp`, `nala-minp`, `nala-rp`, `nala-rp-ekstrem`, `nala-rln`, `nala-np`, `nala-stop`, `nala-seed`).

```bash
ollama list
```
Verifikasi parameter tersimpan sesuai yang ditulis, untuk salah satu model:
```bash
ollama show nala-rp --parameters
```

**Bersih-bersih** — hapus semua model eksperimen (kecuali `nala-v1` dari Langkah 18, yang masih dipakai sampai Module 4):
```bash
ollama rm nala-topk nala-topp nala-minp nala-rp nala-rp-ekstrem nala-rln nala-np nala-stop nala-seed
```

**Checkpoint refleksi:** dari 8 parameter yang baru diuji (`top_k`, `top_p`, `min_p`, `repeat_penalty`, `repeat_last_n`, `num_predict`, `stop`, `seed`), selain `temperature` dan `num_ctx` yang sudah dipakai `nala-v1`, adakah parameter lain yang menurut Anda **layak** ditambahkan ke Modelfile NALA produksi? Untuk yang mana, dan kenapa?

---

## Bagian F: Perbandingan Multi-Model & KV Cache (Langkah 30-32, ~55 menit)

Sejauh ini seluruh sesi memakai `llama3.2:3b` saja. Bagian ini menambah satu model pembanding — mengulang metodologi evaluasi dari Langkah 12, tapi lintas model, plus menyelami komponen memori yang sering terlewat: **KV cache**.

### Langkah 30: Pull Model Pembanding (~20-30 menit, tergantung koneksi)

Pilih salah satu (atau keduanya kalau waktu memungkinkan):
```bash
ollama pull qwen2.5:7b
```
atau
```bash
ollama pull mistral:7b
```

Sambil menunggu, baca tabel perbandingan di `materi.md` Module 2 Bagian 4 — `qwen2.5:7b` dioptimalkan untuk Bahasa Indonesia, `mistral:7b` general-purpose dengan presisi lebih tinggi di benchmark, keduanya butuh RAM minimum ~8GB (vs `llama3.2:3b` yang cuma ~6GB).

**Checkpoint:**
```bash
ollama list
```
Model baru harus muncul di daftar.

### Langkah 31: Evaluasi Lintas Model — Ulangi 3 Pertanyaan Langkah 12 (~20 menit)

Jalankan **tiga pertanyaan yang sama persis** dari Langkah 12, kali ini ke model baru, ukur waktu dengan `time`:

```bash
time ollama run qwen2.5:7b "Apa perbedaan antara machine learning dan deep learning? Jelaskan dalam 2-3 kalimat."
```
```bash
time ollama run qwen2.5:7b "Jelaskan konsep 'overfitting' dalam training model machine learning, menggunakan bahasa Indonesia yang mudah dipahami."
```
```bash
time ollama run qwen2.5:7b "Tuliskan contoh singkat Python script untuk load model dari Hugging Face dan lakukan inference. Sertakan komentar penjelasan."
```

**Checkpoint — tabel perbandingan lengkap:**

| Pertanyaan | `llama3.2:3b` (Langkah 12) | Model baru — Kejelasan (1-5) | Model baru — Akurasi (1-5) | Model baru — Waktu |
|---|---|---|---|---|
| ML vs DL | ___ detik | | | ___ detik |
| Overfitting | ___ detik | | | ___ detik |
| Kode Python | ___ detik | | | ___ detik |

**Refleksi:** model mana yang lebih cepat? Model mana yang jawabannya lebih baik dalam Bahasa Indonesia? Untuk kasus NALA (asisten internal, RAM laptop kita saat training dibatasi 16GB total termasuk service lain di Module 24+), apakah selisih kualitas ini sepadan dengan selisih kebutuhan RAM (~6GB vs ~8GB) dan kecepatan?

### Langkah 32: Baca Log KV Cache — Komponen Memori yang Sering Terlewat (~10-15 menit)

Jalankan model baru sekali lagi, perhatikan baris log di terminal `ollama serve` (Langkah 2) yang memuat `llama_kv_cache`:
```bash
ollama run qwen2.5:7b "Halo"
```

Cari baris seperti:
```
llama_kv_cache: size = XXXX.XX MiB (XXXXX cells, XX layers, 1 seqs)
```

**Checkpoint:**

| Data dari log Anda | Nilai |
|---|---|
| Ukuran KV cache (MiB) | |
| Jumlah layer | |

Bandingkan dengan contoh `llama3.2:3b` di `materi.md` Module 2 Bagian 4.1: KV cache-nya ~3.5GB — **hampir dua kali lipat** ukuran file model itu sendiri (~1.87GB). Ini kenapa rule of thumb `(ukuran file × 2) + 1GB` (dipakai di Langkah 11) sudah memperhitungkan KV cache, bukan cuma ukuran file model.

**Refleksi penutup Bagian F:** kalau nanti di Module 4 (Docker Compose) atau Module 24 (Full-Stack Deployment) Anda perlu menjalankan Ollama **bersamaan** dengan banyak service lain, komponen memori mana yang paling penting diperhitungkan — ukuran file model, atau KV cache? Kenapa?

**Bersih-bersih (opsional):** kalau tidak ingin menyimpan model besar ini, hapus setelah selesai:
```bash
ollama rm qwen2.5:7b
```

---

## Bagian G: Konfigurasi Lanjutan — Environment Variables & REST API Langsung (Langkah 33-40, ~110 menit)

Sejauh ini Anda berinteraksi dengan Ollama lewat CLI (`ollama run`, `/set system`). Tapi aplikasi NALA (mulai Module 4) **tidak** memanggil CLI — ia memanggil **REST API** Ollama langsung lewat HTTP. Bagian ini menjembatani keduanya: mengenal environment variable yang mengatur perilaku service, lalu memanggil endpoint API yang sama persis yang akan dipakai kode Python nanti.

### Langkah 33: Environment Variables — Mengatur Perilaku Ollama Service (~20 menit)

Environment variable di-set **sebelum** `ollama serve` dijalankan (atau sebelum aplikasi desktop dibuka, untuk macOS/Windows lewat cara khusus OS masing-masing). Kenali dulu enam yang paling relevan:

| Variable | Fungsi | Default |
|---|---|---|
| `OLLAMA_HOST` | Alamat & port tempat Ollama listen (defaultnya cuma bisa diakses dari `localhost`) | `127.0.0.1:11434` |
| `OLLAMA_MODELS` | Folder tempat model disimpan di disk | `~/.ollama/models` (macOS/Linux), `C:\Users\<USER>\.ollama\models` (Windows) |
| `OLLAMA_CONTEXT_LENGTH` | Context length default untuk **semua** model kalau tidak di-override per-model lewat `num_ctx` di Modelfile | 2048 |
| `OLLAMA_KEEP_ALIVE` | Berapa lama model tetap di memori setelah request terakhir, sebelum otomatis di-unload | `5m` |
| `OLLAMA_MAX_LOADED_MODELS` | Maksimal berapa model boleh di-load **bersamaan** di memori | otomatis (berdasar RAM/VRAM tersedia) |
| `OLLAMA_NUM_PARALLEL` | Maksimal berapa request diproses **paralel** untuk satu model | otomatis (biasanya 4) |

**Praktik — ubah `OLLAMA_KEEP_ALIVE` jadi sangat singkat, amati efeknya:**

Matikan dulu Ollama yang berjalan (lihat Bagian 2.1), lalu nyalakan ulang dengan environment variable custom:

```bash
OLLAMA_KEEP_ALIVE=10s ollama serve
```

Di terminal baru, jalankan satu pertanyaan, lalu segera cek `ollama ps` berulang kali tiap beberapa detik:
```bash
ollama run llama3.2:3b "Halo"
ollama ps
```

**Checkpoint:** dengan `OLLAMA_KEEP_ALIVE=10s`, model harus **hilang** dari `ollama ps` sekitar 10 detik setelah request terakhir (dibanding default 5 menit). Matikan `ollama serve` ini (`Ctrl+C`), nyalakan ulang **tanpa** environment variable custom untuk melanjutkan ke Langkah berikutnya.

**Refleksi:** untuk NALA yang dipakai sepanjang jam kerja (banyak request tersebar, kadang berjeda), `OLLAMA_KEEP_ALIVE` yang terlalu singkat berisiko apa? (Petunjuk: setiap kali model di-unload lalu diminta lagi, ada waktu *reload* — lihat log `load_tensors` di Bagian 4.4.)

### Langkah 34: REST API Dasar — `/api/tags` dan `/api/show` (~15 menit)

Pastikan `ollama serve` berjalan normal (default), lalu panggil API langsung pakai `curl` — **tanpa** CLI `ollama` sama sekali:

```bash
curl http://localhost:11434/api/tags
```
Bandingkan output JSON ini dengan `ollama list` — isinya sama, cuma `ollama list` adalah **pembungkus** yang memformat hasil `/api/tags` supaya enak dibaca di terminal.

```bash
curl http://localhost:11434/api/show -d '{"model": "llama3.2:3b"}'
```

**Checkpoint:** cari field `parameters` dan `template` di output JSON — apakah `parameters` menunjukkan nilai yang sama dengan yang pernah Anda lihat lewat `ollama show llama3.2:3b --parameters` (kalau belum pernah, coba jalankan sekarang untuk bandingkan)?

### Langkah 35: `/api/generate` — Non-Streaming vs Streaming (~20 menit)

Ini endpoint yang dipakai untuk pertanyaan single-turn (mirip `ollama run <model> "prompt"`, tapi lewat HTTP).

**Non-streaming** (`stream: false` — respons ditunggu utuh, baru dikembalikan sekaligus):
```bash
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2:3b",
  "prompt": "Sebutkan 3 kegunaan AI di industri keuangan",
  "stream": false
}'
```
Perhatikan: request ini **menggantung** (tidak ada output apa pun) selama model memproses, baru muncul satu JSON utuh di akhir — field `response` berisi seluruh jawaban.

**Streaming** (`stream: true`, default kalau field ini tidak disertakan):
```bash
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2:3b",
  "prompt": "Sebutkan 3 kegunaan AI di industri keuangan"
}'
```

**Checkpoint:**
| Observasi | Jawaban Anda |
|---|---|
| Pada mode non-streaming, apa yang terlihat di terminal selama menunggu? | |
| Pada mode streaming, bagaimana bentuk output-nya berbeda? (petunjuk: banyak baris JSON kecil-kecil berturut-turut, satu per token, field `"done": false` sampai baris terakhir `"done": true`) | |

**Refleksi:** Module 2 membangun `/chat` (non-streaming), lalu Module 6 menggantinya total dengan `/chat/stream`. Sekarang Anda sudah melihat **langsung** di level API mentah kenapa keduanya butuh cara handling berbeda di kode Python — `stream: false` cukup satu `response.json()`, sedangkan `stream: true` butuh membaca response baris-per-baris selagi data mengalir masuk.

### Langkah 36: `/api/chat` — Percakapan Multi-Turn via API (~20 menit)

Berbeda dari `/api/generate` (satu prompt string), `/api/chat` menerima **riwayat percakapan** sebagai list `messages` — ini yang dipakai NALA untuk percakapan multi-turn (Module 4 dan seterusnya).

```bash
curl http://localhost:11434/api/chat -d '{
  "model": "llama3.2:3b",
  "messages": [
    {"role": "system", "content": "Kamu adalah asisten yang menjawab singkat."},
    {"role": "user", "content": "Apa ibukota Indonesia?"}
  ],
  "stream": false
}'
```

Sekarang **lanjutkan** percakapan yang sama — sertakan jawaban model sebelumnya sebagai bagian dari `messages`, tambah pertanyaan lanjutan:

```bash
curl http://localhost:11434/api/chat -d '{
  "model": "llama3.2:3b",
  "messages": [
    {"role": "system", "content": "Kamu adalah asisten yang menjawab singkat."},
    {"role": "user", "content": "Apa ibukota Indonesia?"},
    {"role": "assistant", "content": "Jakarta."},
    {"role": "user", "content": "Berapa perkiraan jumlah penduduknya?"}
  ],
  "stream": false
}'
```

**Checkpoint:** apakah model menjawab pertanyaan kedua dengan benar memahami bahwa "-nya" merujuk ke Jakarta (konteks dari riwayat), bukan bertanya balik "penduduk apa"?

**Refleksi:** field `role` di tiap elemen `messages` ada tiga: `system`, `user`, `assistant`. Anda sudah menyusun `System Prompt NALA v1` di Bagian C — sekarang Anda tahu **persis** field mana di JSON request yang akan diisi draft itu nanti di kode FastAPI (`app/system_prompt.py`, Module 4).

### Langkah 37: `keep_alive` per-Request (~10 menit)

Selain environment variable global (Langkah 33), `keep_alive` juga bisa diset **per-request** — override sesaat tanpa perlu restart `ollama serve`:

```bash
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2:3b",
  "prompt": "Halo",
  "stream": false,
  "keep_alive": "1m"
}'
```

```bash
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2:3b",
  "prompt": "Halo",
  "stream": false,
  "keep_alive": 0
}'
```

**Checkpoint:** setelah request kedua (`keep_alive: 0`), langsung cek `ollama ps` — model harus **langsung hilang** dari daftar (di-unload seketika, tidak menunggu timeout apa pun). Kapan menurut Anda `keep_alive: 0` berguna untuk NALA (petunjuk: skenario testing/CI, atau server dengan banyak model bergantian yang jarang dipakai ulang)?

### Langkah 38: Menjalankan Dua Model Bersamaan (~15 menit)

```bash
ollama run llama3.2:3b "Halo dari model pertama" &
ollama run qwen2.5:7b "Halo dari model kedua" &
wait
```
*(kalau belum pull `qwen2.5:7b` di Bagian F, ganti dengan `llama3.2:1b` — `ollama pull llama3.2:1b` dulu kalau belum ada)*

Segera setelah keduanya berjalan (atau selagi masih berjalan), cek:
```bash
ollama ps
```

**Checkpoint:** apakah **kedua** model muncul di `ollama ps` secara bersamaan? Berapa total SIZE gabungan keduanya — apakah mendekati/melebihi RAM laptop Anda?

**Refleksi:** ini relevan langsung untuk Module 24 (Full-Stack Deployment) — kalau NALA production nanti perlu menjalankan model utama (`llama3.2:3b`) sekaligus model reranker (Module 16, lewat `sentence-transformers`, bukan Ollama) atau model embedding (`nomic-embed-text`, Module 9) **bersamaan**, `OLLAMA_MAX_LOADED_MODELS` dan total RAM tersedia jadi constraint nyata, bukan cuma teori.

### Langkah 39: Custom Bind Address — `OLLAMA_HOST` (~10 menit)

Secara default, Ollama cuma bisa diakses dari `localhost` (komputer yang sama). Ini penting dipahami karena nanti di Module 4, aplikasi FastAPI NALA berjalan **di dalam container Docker terpisah** — container itu perlu mengakses Ollama lewat alamat selain `localhost`.

Matikan Ollama yang berjalan, nyalakan ulang dengan bind address berbeda:
```bash
OLLAMA_HOST=0.0.0.0:11434 ollama serve
```

Di terminal lain, cek dengan alamat IP eksplisit (ganti `127.0.0.1` sesuai kebutuhan — di sini kita tetap dari komputer yang sama untuk kesederhanaan):
```bash
curl http://127.0.0.1:11434/api/tags
```

**Checkpoint:** masih berfungsi seperti biasa? `0.0.0.0` berarti Ollama sekarang listen di **semua** network interface, bukan cuma `localhost` — inilah yang membuat container Docker (yang punya "alamat" jaringan sendiri, beda dari host laptop-nya) bisa menjangkau Ollama di Module 4 lewat `host.docker.internal` atau alamat network Docker, bukan `localhost` biasa.

Matikan lagi (`Ctrl+C`), nyalakan ulang **tanpa** `OLLAMA_HOST` custom (kembali ke default) sebelum melanjutkan.

### Langkah 40: Refleksi Penutup Bagian G — Menghubungkan ke Module 4 (~10 menit)

1. Kode Python di Module 4 (`OllamaClient`, dibahas di `Module-04-Setup-Infra-Docker-Compose/materi.md`) pada dasarnya adalah **pembungkus** di atas `curl` yang baru saja Anda jalankan manual — memanggil `/api/generate` atau `/api/chat` lewat library `httpx`/`requests`, bukan lewat CLI `ollama`. Endpoint mana (`/api/generate` atau `/api/chat`) yang menurut Anda lebih cocok dipakai NALA, yang harus mengingat riwayat percakapan multi-turn (Module 6)?
2. Dari environment variable di Langkah 33, mana yang menurut Anda **wajib** di-set eksplisit saat NALA di-deploy di Docker Compose (Module 4 dan Module 24), dan mana yang aman dibiarkan default?
3. `stream: true` vs `stream: false` (Langkah 35) — hubungkan dengan keputusan desain yang sudah dibahas: Module 2 sengaja membangun `/chat` non-streaming dulu (sederhana), baru Module 6 mengganti total ke `/chat/stream`. Sekarang setelah melihat perbedaan bentuk response JSON-nya langsung, menurut Anda kenapa tim menunda streaming ke modul terpisah, bukan langsung di Module 2?

---

## Ringkasan Waktu

| Bagian | Langkah | Estimasi |
|---|---|---|
| A — Instalasi & Percobaan Dasar | 1-8 | ~95 menit |
| B — Knowledge Cutoff, RAM, Evaluasi | 9-12 | ~70 menit |
| C — Prompt Engineering & Menyusun System Prompt | 13-16 | ~65 menit |
| D — Menguji System Prompt Secara Nyata | 17-20 | ~60 menit |
| E — Eksplorasi Lengkap Parameter Generasi | 21-29 | ~85 menit |
| F — Perbandingan Multi-Model & KV Cache | 30-32 | ~55 menit |
| G — Environment Variables & REST API Langsung | 33-40 | ~110 menit |
| **Total** | | **~540 menit (~9 jam)** — sangat disarankan dipecah jadi 2-3 sesi (misal Bagian A-D sesi pagi, E-F sesi siang, G sesi terpisah/hari lain), sesuaikan jeda istirahat sesuai kebutuhan |

## Troubleshooting Lengkap

| Masalah | Penyebab | Solusi |
|---|---|---|
| `ollama: command not found` | Instalasi belum berhasil / PATH belum ter-set | Ulangi Langkah 1; cek PATH environment variable |
| `Connection refused` saat `curl localhost:11434` | `ollama serve` belum berjalan | Ulangi Langkah 2 |
| `address already in use` saat `ollama serve` manual | Aplikasi desktop Ollama sudah berjalan di background | Cukup satu instance yang listen di port 11434 — tidak perlu jalankan `ollama serve` manual lagi. Cek proses: `lsof -i :11434` (macOS/Linux) atau `netstat -ano \| findstr :11434` (Windows) |
| Model berjalan sangat lambat, banyak layer tidak ter-offload ke GPU | RAM/VRAM tidak cukup untuk model + KV cache (lihat Langkah 32) | Cek Langkah 11 untuk estimasi kebutuhan; tutup aplikasi lain yang memakan memori; pertimbangkan model lebih kecil (`llama3.2:1b`) |
| `Out of Memory` error | Model terlalu besar untuk RAM sistem | Gunakan model lebih kecil (`ollama pull llama3.2:1b`); tutup aplikasi lain; cek RAM available (`free -h`/Task Manager) |
| Model download gagal/lambat | Koneksi internet lambat, atau disk penuh | Cek koneksi internet; cek ruang disk tersedia (model besar seperti `qwen2.5:7b` butuh ~4-5GB free space) |
| `ollama create` gagal, error "file not found" | Nama file `Modelfile` salah, atau `ollama create` dijalankan dari folder yang salah | Pastikan nama file persis `Modelfile` (tanpa ekstensi apa pun); jalankan `ollama create` dari folder yang sama tempat file itu disimpan |
| `ollama create` gagal, error "unknown parameter" | Nama parameter di Modelfile tidak valid (lihat `materi.md` Bagian 8 — beberapa nama lama seperti `numa`, `rope_frequency_base` sudah tidak dikenali versi Ollama terbaru) | Cek ejaan parameter, bandingkan dengan tabel resmi di `materi.md` Bagian 8 |
| Jawaban model terasa "melenceng topik"/tidak koheren setelah mengubah parameter | Nilai parameter (terutama `repeat_penalty`/`repeat_last_n`) terlalu agresif untuk model kecil | Lihat temuan Langkah 24-25 — turunkan ke nilai lebih konservatif (mis. `repeat_penalty 1.1` bukan `1.5`) |
| `curl` mengembalikan `{"error":"model ... not found"}` | Nama model di body JSON tidak persis sama dengan yang muncul di `ollama list` (termasuk tag, misal `llama3.2:3b` bukan `llama3.2`) | Cek ulang `ollama list`, salin nama model persis termasuk tag setelah `:` |
| `curl` menggantung tanpa respons sama sekali | Ollama service tidak berjalan, atau `OLLAMA_HOST` custom dari Langkah 39 belum dikembalikan ke default | Cek `curl http://localhost:11434` dulu (Bagian 2.1); pastikan tidak ada environment variable `OLLAMA_HOST` custom yang masih aktif di terminal Anda |
| Response `/api/generate`/`/api/chat` error "invalid character" atau JSON parse error | Body JSON di `curl -d '...'` tidak valid (tanda kutip tidak seimbang, koma berlebih) | Periksa ulang tanda kutip `"` dan koma di body JSON — paling gampang salah ketik saat menyalin manual, bukan copy-paste langsung |
| Dua model di Langkah 38 tidak muncul bersamaan di `ollama ps`, salah satu ter-unload | RAM tidak cukup untuk memuat keduanya sekaligus, atau `OLLAMA_MAX_LOADED_MODELS` membatasi | Ini temuan yang **valid**, bukan error — catat sebagai observasi di checkpoint Langkah 38, bukan sesuatu yang perlu "diperbaiki" |

---

**Next:** Draft `System Prompt NALA v1` yang sudah divalidasi di Langkah 19-20 siap dipindahkan jadi konstanta Python `NALA_SYSTEM_PROMPT` di `Module-04-Setup-Infra-Docker-Compose/materi.md`, bagian Panduan Praktik, Langkah 6 — di sana system prompt yang sama akan dikirim otomatis lewat API tiap ada request masuk ke endpoint `/chat`, bukan diketik manual lagi.
