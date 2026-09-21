# Worksheet — Percobaan Ollama, Knowledge Cutoff & Pengantar RAG

Worksheet ini melengkapi `materi.md` (khususnya section 4, 5.1, dan 6). Kerjakan langsung di terminal (dan sesekali GUI) sambil mengisi tabel jawaban di bawah setiap bagian.

**Prasyarat:** `ollama serve` sudah berjalan dan minimal satu model (`llama3.2:3b`) sudah di-pull (lihat materi.md section 4.2).

---

## Bagian 1: Percobaan Dasar Ollama

Coba masing-masing perintah berikut, lalu catat observasi Anda.

### 1.1 Mode single-shot vs mode interaktif

```bash
ollama run llama3.2:3b "Sebutkan 3 kegunaan AI di industri keuangan"
```

```bash
ollama run llama3.2:3b
```
Di mode interaktif, coba ajukan pertanyaan lanjutan yang merujuk ke jawaban sebelumnya (contoh: "Jelaskan lebih detail poin nomor 2"). Ketik `/exit` untuk keluar.

| Observasi | Catatan Anda |
|---|---|
| Apakah mode interaktif "ingat" konteks pertanyaan sebelumnya? | |
| Apa bedanya kecepatan respons single-shot vs giliran ke-2 di mode interaktif? (lihat materi.md section 4.4 soal prompt caching) | |

### 1.2 Melihat model yang sedang di-load

```bash
ollama ps
```

| Field di output | Artinya menurut Anda |
|---|---|
| `NAME` | |
| `SIZE` | |
| `PROCESSOR` (CPU/GPU %) | |
| `UNTIL` (kapan model di-unload dari memori) | |

### 1.3 Melihat daftar model yang sudah terpasang

```bash
ollama list
```

Catat model apa saja yang sudah Anda pull, dan bandingkan ukurannya dengan tabel perbandingan model di materi.md section 5.

### 1.4 GUI vs Terminal (lihat materi.md section 4.5)

1. Jalankan pertanyaan yang sama persis lewat terminal dan lewat GUI Ollama Chat:
   ```bash
   ollama run llama3.2:3b "Ringkas dalam 1 kalimat: apa itu suku bunga acuan?"
   ```
2. Buka aplikasi Ollama Chat (ikon di menu bar/system tray), pastikan dropdown model sudah `llama3.2:3b` (bukan model cloud), lalu ajukan pertanyaan yang sama di kotak "Send a message".

| Observasi | Catatan Anda |
|---|---|
| Apakah jawaban dari terminal dan GUI konsisten (isi & gaya bahasanya mirip)? | |
| Mana yang menurut Anda lebih praktis untuk demo cepat ke non-teknis: terminal atau GUI? Kenapa? | |
| Apakah Anda sempat melihat dropdown model default ke model cloud (`*.cloud`)? Bagaimana cara Anda memperbaikinya? | |

### 1.5 Batasan Model: Coba Upload Gambar (lihat materi.md section 4.5)

Di jendela GUI Ollama Chat yang sama (model masih `llama3.2:3b`), coba upload sembarang file gambar/screenshot lewat tombol `+`.

| Observasi | Catatan Anda |
|---|---|
| Pesan error apa yang muncul? | |
| Kenapa error ini muncul — apa yang membedakan `llama3.2:3b` dari model vision seperti `qwen3-vl:8b`? | |
| Untuk kasus NALA (chatbot berbasis teks SOP & data operasional), apakah kemampuan vision ini dibutuhkan? Kenapa? | |

---

## Bagian 2: Cek Knowledge Cutoff Model

**Knowledge cutoff** adalah batas waktu data training suatu model — model tidak tahu apa pun yang terjadi setelah tanggal tersebut, karena ia hanya belajar dari data yang tersedia sampai titik itu. Ini penting dipahami sebelum memakai LLM lokal untuk kebutuhan bisnis: model **tidak otomatis update** seperti mesin pencari.

### 2.1 Jalankan pertanyaan-pertanyaan berikut

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

### 2.2 Worksheet Hasil

| Pertanyaan | Jawaban Model (ringkas) | Benar / Salah / Tidak Tahu | Kenapa? |
|---|---|---|---|
| Knowledge cutoff model | | ☐ Benar ☐ Salah ☐ Mengaku tidak tahu | |
| Presiden Indonesia saat ini | | ☐ Benar ☐ Salah ☐ Mengaku tidak tahu | |
| Suku bunga BI bulan ini | | ☐ Benar ☐ Salah ☐ Mengaku tidak tahu | |
| Versi terbaru Llama | | ☐ Benar ☐ Salah ☐ Mengaku tidak tahu | |

### 2.3 Refleksi

1. Apakah model pernah menjawab dengan percaya diri padahal jawabannya salah/sudah kedaluwarsa (*hallucination*)? Beri contoh dari tabel di atas.
2. Untuk kasus NALA (asisten AI PT Nusantara Finance), data internal apa saja yang **pasti tidak diketahui** oleh model dasar seperti `llama3.2:3b`? (Contoh: SOP internal terbaru, data pengajuan kredit nasabah, kebijakan cuti karyawan.)

---

## Bagian 3: Pengantar ke RAG — Kenapa Knowledge Cutoff Ini Penting?

Dari Bagian 2, Anda sudah membuktikan sendiri dua keterbatasan mendasar model LLM lokal:

1. **Knowledge cutoff** — model tidak tahu kejadian/data setelah tanggal training-nya.
2. **Tidak ada akses ke data privat/internal** — model dasar dari `ollama pull` dilatih dari data publik di internet, bukan dokumen SOP atau data operasional PT Nusantara Finance. Model tidak mungkin tahu isi dokumen internal perusahaan hanya dengan bertanya langsung.

Kedua keterbatasan ini adalah alasan utama kenapa modul-modul berikutnya (mulai Module 7) akan memperkenalkan **RAG (Retrieval-Augmented Generation)**.

**Konsep singkat RAG** (akan dibahas detail mulai Module 7 dst.):
- Alih-alih berharap model "sudah tahu" jawabannya dari hasil training, sistem **mencari (retrieve)** potongan dokumen relevan terlebih dahulu (misalnya dari SOP internal PT Nusantara Finance yang disimpan di knowledge base).
- Potongan dokumen itu kemudian **disisipkan ke dalam prompt** sebagai konteks tambahan, sebelum dikirim ke model.
- Model menjawab **berdasarkan konteks yang diberikan**, bukan hanya dari memori training-nya — sehingga jawaban bisa akurat untuk data yang baru atau bersifat privat/internal, tanpa perlu melatih ulang (fine-tune) model.

Dengan kata lain: RAG tidak membuat model "lebih pintar" secara permanen, tapi memberi model **bahan bacaan yang tepat** pada saat itu juga, mirip seperti memberi seseorang dokumen referensi sebelum menjawab pertanyaan, alih-alih mengandalkan ingatannya saja.

### 3.1 Refleksi Penutup

Bayangkan Anda bertanya ke NALA: *"Apa syarat pengajuan restrukturisasi kredit untuk nasabah yang telat bayar 3 bulan?"*

1. Kenapa `llama3.2:3b` tanpa RAG kemungkinan besar akan menjawab ngasal atau generik untuk pertanyaan ini?
2. Dokumen apa yang menurut Anda perlu di-retrieve terlebih dahulu supaya NALA bisa menjawab dengan akurat?

Jawaban Anda di sini akan jadi bekal masuk ke Module 7 (Konsep RAG).

---

## Bagian 4: Praktik Hitung RAM/VRAM Model Baru

Gunakan formula dan tabel bits/weight di materi.md section 5.1 untuk menghitung estimasi kebutuhan RAM model **yang belum ada di tabel section 5** — latihan ini menguji apakah Anda benar-benar paham cara pakai formulanya, bukan cuma menghafal tabel.

### 4.1 Cek data model di Ollama Library

Buka [ollama.com/library](https://ollama.com/library), cari model **`qwen3-vl:8b`** (model vision yang disebut di section 4.5), lalu catat:

| Data | Nilai |
|---|---|
| Jumlah parameter (approx, dari nama tag) | |
| Ukuran file download yang tertera di halaman library | |
| Tipe quantization default (biasanya Q4_K_M kecuali disebutkan lain) | |

### 4.2 Hitung manual, lalu bandingkan

Pakai formula di section 5.1:
```
Kebutuhan Memory (GB) ≈ Jumlah Parameter (Miliar) × Bytes per Parameter (quantization)
```

| Langkah | Hasil Anda |
|---|---|
| Bytes/parameter untuk Q4_K_M (dari tabel section 5.1) | ~0.61 byte |
| Perhitungan Anda: parameter × 0.61 | ___ GB |
| Ukuran file asli di ollama.com/library (section 5.1 di atas) | ___ GB |
| Selisihnya berapa besar (dalam %)? Menurut Anda kenapa ada selisih (lihat penjelasan tensor F32 di section 5.1)? | |

### 4.3 Estimasi RAM minimum

Pakai rule of thumb `(ukuran file × 2) + 1 GB` di section 5.1:

| Model | Ukuran File | Estimasi RAM Minimum |
|---|---|---|
| `llama3.2:3b` (sudah dihitungkan di materi) | ~1.87 GB | ~5 GB |
| `qwen3-vl:8b` (hitungan Anda) | ___ | ___ |

**Refleksi:** Kalau laptop Anda hanya punya 8GB RAM total (bukan 16GB seperti prasyarat training di README utama), apakah `qwen3-vl:8b` masih aman dijalankan bersamaan dengan aplikasi lain (browser, IDE, dll)? Jelaskan alasan Anda.

---

**Next:** Lanjut ke `Module-07-Konsep-RAG/materi.md` untuk pembahasan RAG secara penuh.
