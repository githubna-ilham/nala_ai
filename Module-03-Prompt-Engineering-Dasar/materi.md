# Module 3: Prompt Engineering Dasar

## Tujuan

Kita memahami anatomi system prompt yang baik, lalu menyusun, menguji, dan memvalidasi draft "System Prompt NALA v1" langsung di Ollama, sebagai persiapan sebelum diintegrasikan ke kode FastAPI pada Module 4.

## Hasil Akhir yang Diharapkan

- Kita paham komponen system prompt (persona, tugas, batasan, format output, few-shot) serta kapan menggunakan zero-shot vs few-shot
- Kita paham karakteristik dan keterbatasan model kecil/lokal, dan cara menulis prompt yang sesuai untuknya
- Kita, bekerja berpasangan, menghasilkan draft System Prompt NALA v1 sesuai kriteria (persona, scope, honesty, Bahasa Indonesia)
- Draft tersebut sudah diuji langsung di Ollama (via `/set system` atau Modelfile) dan lolos checkpoint dasar (mencerminkan identitas NALA, menolak menjawab di luar konteks)
- Kita paham parameter Modelfile utama (`temperature`, `num_ctx`, dsb.) dan efek nyatanya terhadap output model

## 1. Anatomi System Prompt yang Baik

System prompt adalah instruksi awal yang diberikan kepada model AI untuk mendefinisikan perilakunya. Sebuah system prompt yang baik harus memiliki beberapa komponen penting:

### Komponen Utama

**a) Persona/Peran**
Definisikan siapa atau apa model tersebut dalam konteks percakapan. Ini membantu model memahami "sudut pandang" yang harus diambil.

Contoh:
```
Kamu adalah seorang customer service representative PT Nusantara Finance yang ramah dan profesional.
```

**b) Tugas/Tujuan**
Jelaskan apa yang harus dilakukan model. Buat pernyataan ini spesifik dan terukur.

Contoh:
```
Tugasmu adalah menjawab pertanyaan pelanggan mengenai produk keuangan kami dengan jelas dan akurat.
```

**c) Batasan (Scope)**
Tentukan apa yang TIDAK boleh dilakukan model. Ini sangat penting untuk mencegah model memberikan informasi di luar domain atau menjawab pertanyaan yang tidak seharusnya dijawab.

Contoh:
```
- Jangan memberikan saran investasi personal yang spesifik
- Jangan memberikan informasi tentang produk kompetitor secara detail
- Hanya berikan informasi tentang produk PT Nusantara Finance
```

**d) Format Output**
Tentukan bagaimana model harus memformat jawabannya. Ini memastikan konsistensi dan kemudahan pemahaman.

Contoh:
```
- Jawab dalam Bahasa Indonesia yang jelas dan formal
- Gunakan bullet points untuk daftar informasi
- Jika tidak yakin, mulai dengan "Berdasarkan informasi saya..."
```

**e) Contoh (Few-shot)**
Sediakan contoh pertanyaan dan jawaban yang diinginkan. Ini membantu model memahami ekspektasi dengan lebih baik.

Contoh:
```
Q: Berapa bunga tabungan Anda?
A: Tabungan PT Nusantara Finance menawarkan bunga 4.5% per tahun untuk nominal di atas Rp 10 juta. Untuk informasi lebih lengkap, silakan hubungi cabang terdekat.
```

---

## 2. Teknik Zero-Shot vs Few-Shot

### Apa itu Zero-Shot?

Zero-shot adalah teknik memberi instruksi kepada model **tanpa memberikan contoh spesifik**. Model diminta langsung menjalankan tugas berdasarkan instruksi umum.

**Kelebihan:**
- Cepat dan efisien
- Cocok untuk tugas-tugas sederhana yang sudah dipahami model secara umum

**Kekurangan:**
- Kurang akurat untuk tugas spesifik
- Model mungkin menginterpretasikan instruksi dengan cara yang tidak diharapkan

**Contoh Zero-Shot:**
```
System Prompt:
"Kamu adalah asisten customer service. Jawab pertanyaan pelanggan dengan jelas."

User: "Bagaimana cara membuka rekening tabungan?"
```

### Apa itu Few-Shot?

Few-shot adalah teknik memberikan **satu atau beberapa contoh** jawaban yang diinginkan sebelum model menjalankan tugas sebenarnya. Ini membantu model memahami pola dan format yang diharapkan.

**Kelebihan:**
- Lebih akurat dan konsisten
- Model lebih memahami nuansa yang diinginkan
- Sangat efektif untuk tugas-tugas spesifik

**Kekurangan:**
- Memerlukan prompt yang lebih panjang
- Perlu memilih contoh yang representatif

**Contoh Few-Shot:**
```
System Prompt:
"Kamu adalah asisten customer service PT Nusantara Finance. Jawab pertanyaan pelanggan dengan jelas dan ringkas.

Contoh 1:
Q: Berapa bunga kredit Anda?
A: Kredit PT Nusantara Finance memiliki bunga mulai dari 8% hingga 12% tergantung tipe kredit dan profil peminjam.

Contoh 2:
Q: Apa syarat membuka tabungan?
A: Anda perlu KTP asli, kartu keluarga, dan nominal pembukaan minimum Rp 100.000."

User: "Bagaimana cara membuka rekening tabungan?"
```

### Perbandingan Praktis

Untuk pertanyaan yang sama, hasil zero-shot mungkin lebih umum dan generic, sementara few-shot akan menghasilkan jawaban yang lebih sesuai dengan format dan gaya yang didefinisikan dalam contoh.

Dalam praktik, **few-shot lebih disarankan** untuk tugas customer service atau domain-specific karena konsistensi dan akurasi yang lebih baik, meskipun dengan biaya computational yang sedikit lebih tinggi.

---

## 3. Structured Output

Structured output adalah teknik meminta model untuk memberikan respons dalam format yang **konsisten dan terstruktur**. Ini sangat berguna ketika output perlu diproses oleh sistem lain atau ditampilkan dalam format tertentu.

### Mengapa Structured Output Penting?

1. **Konsistensi**: Setiap jawaban mengikuti format yang sama
2. **Parsing Otomatis**: Sistem dapat dengan mudah memproses output
3. **Validasi**: Lebih mudah untuk memvalidasi bahwa output memenuhi kriteria
4. **User Experience**: Output yang terstruktur lebih mudah dibaca

### Teknik Implementasi

**a) Format Template**
Tentukan template yang harus diikuti model dalam setiap respons.

Contoh:
```
Jawab dengan format berikut:
[SALAM]: <salam singkat>
[JAWABAN]: <jawaban utama>
[DISCLAIMER]: <disclaimer jika perlu>
```

**b) Instruksi Eksplisit**
Berikan instruksi yang sangat jelas tentang apa yang harus dilakukan.

Contoh:
```
PERATURAN FORMAT:
1. Mulai dengan salam ramah yang singkat
2. Berikan jawaban singkat dan jelas dalam 2-3 kalimat
3. Jika tidak tahu, katakan "Saya tidak memiliki informasi untuk menjawab pertanyaan ini"
4. Akhiri dengan tautan ke sumber atau nomor kontak jika relevan
```

**c) Contoh Output yang Diinginkan**
Berikan contoh konkret bagaimana output harus terlihat.

Contoh:
```
Q: Berapa biaya transfer?
A:
Halo! Terima kasih atas pertanyaannya.
Biaya transfer antar bank di PT Nusantara Finance adalah Rp 6.500 untuk transfer lokal. Biaya ini dapat berbeda untuk transfer internasional.
Untuk informasi lebih detail, silakan kunjungi www.nusantara-finance.id atau hubungi 1500-nala.
```

### Best Practice untuk Structured Output

- **Jangan berlebihan**: Jangan membuat struktur yang terlalu kompleks karena model kecil mungkin sulit mengikuti
- **Konsistensi adalah kunci**: Pastikan semua contoh mengikuti pola yang sama
- **Test dengan model Anda**: Verifikasi bahwa model Anda benar-benar mengikuti struktur yang diminta

---

## 4. Catatan Khusus Model Kecil/Lokal

Model lokal dengan ukuran 1-7B parameter memiliki karakteristik berbeda dengan model besar (seperti GPT-4 atau Claude). Memahami keterbatasan ini sangat penting untuk mengoptimalkan prompt engineering.

### Karakteristik Model Kecil

**a) Sensitivitas terhadap Instruksi yang Panjang**
- Model kecil lebih sulit mengikuti instruksi yang panjang atau kompleks
- Penambahan setiap kata dalam prompt dapat mempengaruhi hasil

**Solusi:**
- Gunakan instruksi yang ringkas dan langsung
- Hindari penjelasan yang terlalu bertele-tele
- Pisahkan instruksi kompleks menjadi bagian-bagian kecil

**b) Kerentanan terhadap Ambigu**
- Instruksi yang ambigu atau tidak jelas akan menghasilkan output yang tidak konsisten
- Model kecil membutuhkan instruksi yang sangat eksplisit

**Solusi:**
- Berikan instruksi yang sangat spesifik dan tidak ada interpretasi ganda
- Gunakan contoh sebanyak mungkin untuk menjelaskan ekspektasi
- Definisikan batasan dengan sangat jelas

**c) Terbatas pada Konteks Lokal**
- Model kecil tidak mengerti konteks global yang luas
- Model kecil lebih baik ketika ditanyai tentang topik spesifik

**Solusi:**
- Fokus pada domain atau topik spesifik
- Sediakan konteks yang lengkap dalam setiap pertanyaan
- Hindari mereferensi pengetahuan luas yang mungkin tidak dimiliki model

**d) Keterbatasan dalam Reasoning Kompleks**
- Model kecil tidak sebaik model besar dalam tugas-tugas yang memerlukan reasoning multi-step
- Model kecil lebih baik untuk tugas-tugas retrieval atau generation sederhana

**Solusi:**
- Desain tugas agar lebih sederhana dan linear
- Jangan mengharapkan model kecil melakukan reasoning yang sangat kompleks
- Gunakan model kecil untuk tugas-tugas yang straightforward

### Best Practice untuk Model Kecil

1. **Instruksi Singkat & Jelas**: Tidak lebih dari 3-4 kalimat untuk peran dan tugas utama
2. **Contoh Konkret**: Sediakan minimal 2-3 contoh yang jelas
3. **Batasan Eksplisit**: Tulis apa yang TIDAK boleh dilakukan dengan sangat jelas
4. **Avoid Nested Instructions**: Hindari instruksi bertingkat yang kompleks
5. **Test Iteratif**: Selalu test dengan model Anda dan refine berdasarkan hasil

---

## 5. Latihan: Menyusun System Prompt NALA v1

Pada bagian ini, kita (bekerja secara berpasangan dengan satu anggota teknis dan satu non-teknis) akan menyusun draft system prompt untuk NALA berdasarkan kriteria yang diberikan.

### Kriteria System Prompt NALA v1

1. **Persona**: Ramah, profesional, dan merupakan staff/asisten internal PT Nusantara Finance
2. **Scope**: Hanya menjawab pertanyaan seputar produk, layanan, SOP, kebijakan, dan data operasional PT Nusantara Finance
3. **Honesty**: Jika tidak tahu jawaban, harus bilang dengan jujur (jangan mengarang/halusinasi)
4. **Bahasa**: Selalu jawab dalam Bahasa Indonesia yang jelas dan formal

### Template untuk Diisi

Gunakan template berikut sebagai panduan untuk menyusun system prompt NALA v1:

```markdown
# System Prompt NALA v1 - Template

## Persona
[Tuliskan peran/persona NALA di sini]

## Tugas Utama
[Tuliskan tugas utama NALA di sini]

## Batasan (Do's & Don'ts)
### Yang Boleh Dijawab:
- [...]
- [...]

### Yang TIDAK Boleh Dijawab:
- [...]
- [...]

## Format Output
[Jelaskan bagaimana NALA harus memformat jawabannya]

## Contoh Pertanyaan & Jawaban (Few-shot)
### Contoh 1
Q: [Pertanyaan contoh]
A: [Jawaban yang diinginkan]

### Contoh 2
Q: [Pertanyaan contoh]
A: [Jawaban yang diinginkan]

## Catatan Tambahan
[Catatan khusus jika ada]
```

### Proses Kolaborasi

**Fase 1: Diskusi (15 menit)**
- Anggota non-teknis menjelaskan kebutuhan bisnis NALA
- Anggota teknis menanyakan detail teknis dan keterbatasan model

**Fase 2: Draft (20 menit)**
- Kedua anggota bersama-sama mengisi template di atas
- Pastikan persona dan tugas jelas
- Definisikan batasan dengan sangat spesifik

**Fase 3: Refinement (15 menit)**
- Review draft bersama
- Pastikan mengikuti best practice untuk model kecil
- Tambahkan contoh jika diperlukan

---

## 6. Contoh System Prompt Referensi

Berikut adalah contoh system prompt NALA yang dapat dijadikan referensi setelah kita menyusun draft sendiri. Bandingkan dengan draft kita dan diskusikan perbedaan serta kesamaannya.

```
Kamu adalah NALA, asisten AI internal PT Nusantara Finance.
Tugasmu adalah menjawab pertanyaan staff seputar SOP, kebijakan, dan data operasional perusahaan.
Aturan:
- Jawab singkat, jelas, dan dalam Bahasa Indonesia.
- Jika kamu tidak yakin atau informasinya tidak tersedia, katakan dengan jujur bahwa kamu tidak memiliki informasi tersebut. Jangan mengarang jawaban.
- Jangan menjawab pertanyaan di luar konteks pekerjaan PT Nusantara Finance.
```

### Analisis Contoh Referensi

**Kekuatan:**
- Persona jelas dan spesifik (NALA, asisten AI internal PT Nusantara Finance)
- Tugas sangat fokus (SOP, kebijakan, data operasional)
- Batasan eksplisit dengan contoh perilaku yang diinginkan
- Instruksi singkat dan cocok untuk model kecil
- Menekankan honesty dan pencegahan hallucination

**Diadaptasi dari Best Practice:**
- Mengikuti prinsip few-shot dengan contoh implicit dalam aturan
- Instruks singkat sesuai rekomendasi untuk model kecil
- Format output terstruktur (Jawab singkat, jelas, Bahasa Indonesia)
- Batasan dijelaskan dengan contoh behavior yang diinginkan

**Belajar dari Contoh Ini:**
Ketika menyusun system prompt Anda sendiri, pastikan:
1. Persona jelas dan relevan dengan konteks
2. Tugas dinyatakan dalam satu atau dua kalimat
3. Aturan/batasan dijelaskan dengan konkret, bukan abstrak
4. Tidak ada instruksi yang bertele-tele atau kompleks
5. Tekankan "jujur jika tidak tahu" untuk mencegah hallucination

### Contoh Template Section 5 Terisi

Referensi di atas adalah versi ringkas (persis yang dipakai di kode `NALA_SYSTEM_PROMPT`). Berikut versi yang sama, tapi diisi ke dalam **Template untuk Diisi** di section 5 — supaya Anda punya gambaran konkret hasil akhir tiap bagian template, bukan cuma template kosong:

```markdown
# System Prompt NALA v1 - Template

## Persona
Kamu adalah NALA (Nusantara Assistant), asisten AI internal PT Nusantara Finance. Kamu bersikap profesional, ramah, dan efisien — seperti staf knowledge management internal yang membantu sesama karyawan mencari informasi dengan cepat dan akurat.

## Tugas Utama
Menjawab pertanyaan staf PT Nusantara Finance seputar dua sumber informasi: (1) dokumen SOP, kebijakan, dan panduan internal perusahaan, dan (2) data operasional perusahaan (misalnya status pengajuan kredit atau klaim) sesuai kewenangan akses staf yang bertanya.

## Batasan (Do's & Don'ts)
### Yang Boleh Dijawab:
- Pertanyaan seputar SOP, kebijakan, dan prosedur internal PT Nusantara Finance.
- Pertanyaan seputar data operasional yang tersedia dan sesuai kewenangan akses staf yang bertanya.
- Pertanyaan klarifikasi atau lanjutan atas jawaban NALA sebelumnya dalam sesi yang sama.

### Yang TIDAK Boleh Dijawab:
- Pertanyaan di luar konteks pekerjaan PT Nusantara Finance (topik umum, berita, hiburan, dsb).
- Permintaan yang membuat NALA mengarang atau menebak jawaban ketika informasi tidak ditemukan.
- Permintaan mengakses atau membocorkan data operasional di luar kewenangan staf yang bertanya.
- Permintaan nasihat hukum, keuangan pribadi, atau keputusan bisnis final atas nama perusahaan.

## Format Output
- Jawab singkat, jelas, dan langsung ke inti (maksimal 3-4 kalimat kecuali diminta detail).
- Selalu gunakan Bahasa Indonesia yang formal namun ramah.
- Jika informasi tidak ditemukan, katakan dengan jujur — jangan mengarang jawaban.
- Kalau jawaban berasal dari dokumen SOP, sebutkan nama dokumen sumbernya secara singkat.

## Contoh Pertanyaan & Jawaban (Few-shot)
### Contoh 1
Q: Berapa lama proses persetujuan pengajuan kredit?
A: Berdasarkan SOP Pengajuan Kredit, proses persetujuan memakan waktu 3-5 hari kerja setelah dokumen lengkap diterima.

### Contoh 2
Q: Siapa nama CEO PT Nusantara Finance?
A: Maaf, saya tidak memiliki informasi tersebut di dokumen atau data yang saya akses. Silakan hubungi bagian HR untuk informasi ini.

## Catatan Tambahan
Instruksi sengaja dibuat singkat dan eksplisit (bukan bertingkat/kompleks) karena menjalankan model lokal kelas kecil (`llama3.2:3b`) — lihat section 4 soal karakteristik model kecil.
```

Bandingkan dua versi ini: versi ringkas di atas dipakai langsung sebagai kode (`NALA_SYSTEM_PROMPT`) karena model kecil butuh instruksi sesingkat mungkin; versi terstruktur ini lebih untuk tahap **desain & dokumentasi** — memudahkan tim (terutama anggota non-teknis) memahami dan mendiskusikan tiap bagian sebelum dipadatkan jadi versi produksi.

---

## 7. Menguji System Prompt Anda Sekarang

Draft `System Prompt NALA v1` yang baru saja disusun di section 5 **tidak perlu menunggu Module 4** untuk dicoba — Ollama sudah bisa menerima system prompt langsung dari terminal. Menguji draft sekarang penting supaya Anda dapat feedback nyata (bukan cuma dugaan di atas kertas) sebelum lanjut ke integrasi kode di Module 4.

> 📌 **Ini baru v1, bukan versi final.** System prompt yang diuji di sini akan terus berkembang di modul-modul berikutnya seiring NALA bertambah kemampuan: Module 11 menambah instruksi *grounding* (jawab hanya dari dokumen yang di-retrieve, sebutkan sumbernya), Module 17 kemungkinan di-tuning ulang berdasarkan hasil evaluasi RAG, dan Module 22 diperluas dengan instruksi *tool-use* (kapan pakai RAG dokumen vs kapan query data operasional). Jadi jangan terlalu lama "menyempurnakan" draft sekarang — cukup pastikan persona & aturan dasarnya benar, detailnya akan menyusul.

> ⚠️ **Koreksi:** flag `ollama run --system "..."` **tidak tersedia** (cek `ollama run --help` — flag ini tidak ada di daftar). Dua cara di bawah ini adalah yang benar-benar berfungsi.

### 7.1 Cara Cepat: `/set system` di Mode Interaktif

Cocok untuk iterasi cepat saat masih menyusun/merevisi draft.

```bash
ollama run llama3.2:3b
```

Setelah muncul prompt `>>>`, ketik (satu baris penuh, tanpa Enter di tengah):

```
/set system Kamu adalah NALA, asisten AI internal PT Nusantara Finance. Tugasmu adalah menjawab pertanyaan staff seputar SOP, kebijakan, dan data operasional perusahaan. Jawab singkat, jelas, dan dalam Bahasa Indonesia. Jika kamu tidak yakin, katakan dengan jujur bahwa kamu tidak memiliki informasi tersebut.
```

💡 `/set system` membaca **satu baris penuh** sebagai system prompt — kalau di layar Anda baris ini terlihat panjang/perlu di-scroll, itu wajar (command-nya memang sepanjang itu); saat benar-benar diketik atau di-paste ke terminal, tetap perlakukan sebagai satu baris utuh. Untuk praktik sesungguhnya, ganti teks setelah `/set system` dengan draft `System Prompt NALA v1` lengkap hasil kerja Anda di section 5.

Ollama akan konfirmasi `Set system message.` — setelah itu, semua pertanyaan di sesi yang sama akan mengikuti system prompt tersebut. Coba langsung:
```
Siapa kamu?
```

**Checkpoint**: jawaban model harus mencerminkan persona NALA (bukan jawaban generik "Saya adalah model bahasa AI..."). Kalau belum sesuai, ketik `/set system` lagi dengan draft yang direvisi — tidak perlu keluar dari sesi.

Perintah pendukung lain di mode ini:
```
/show system   # menampilkan system prompt yang sedang aktif
/clear         # menghapus system prompt & riwayat percakapan, mulai bersih
/bye           # keluar dari sesi
```

### 7.2 Cara Persisten: Modelfile

Kalau draft sudah stabil dan ingin dipakai berulang tanpa mengetik ulang tiap sesi, bungkus jadi model custom lewat **Modelfile**. Konsepnya mirip `Dockerfile`: file teks deklaratif yang mendefinisikan "resep" sebuah model turunan — base model apa, system prompt apa, dan parameter generasi apa — lalu di-build sekali jadi model baru yang siap dipakai berulang.

> ⚠️ **Penting — ini bukan perintah, ini isi sebuah file.** `Modelfile` bukan command yang diketik di terminal, melainkan **file teks biasa** yang harus dibuat dan disimpan terlebih dahulu, baru kemudian dirujuk lewat perintah `ollama create`. Kalau ini pertama kali dengar istilah "Modelfile", ikuti dua langkah terpisah di bawah — jangan coba-coba paste isi Modelfile langsung ke terminal, itu tidak akan berfungsi.

**Langkah A — Buat file-nya (pakai text editor, bukan terminal):**

1. Buka text editor apa saja (VS Code, Notepad, TextEdit, dll).
2. Ketik/paste isi berikut:
   ```
   FROM llama3.2:3b
   SYSTEM """Kamu adalah NALA, asisten AI internal PT Nusantara Finance. Tugasmu adalah menjawab pertanyaan staff seputar SOP, kebijakan, dan data operasional perusahaan. Jawab singkat, jelas, dan dalam Bahasa Indonesia. Jika kamu tidak yakin, katakan dengan jujur bahwa kamu tidak memiliki informasi tersebut."""
   ```
3. Simpan file dengan **nama persis `Modelfile`** — tanpa ekstensi apa pun (bukan `Modelfile.txt`). Simpan di folder mana saja yang mudah diingat, misalnya `resources/starter-code/day-1/nala/`.

**Langkah B — Baru sekarang buka Terminal, dan jalankan perintahnya di sana:**

```bash
cd resources/starter-code/day-1/nala   # masuk ke folder tempat Modelfile disimpan
ollama create nala-v1 -f Modelfile     # baca file itu, buat model baru "nala-v1"
ollama run nala-v1                     # coba jalankan model yang baru dibuat
```

Perintah `ollama create` artinya: "baca file bernama `Modelfile` di folder ini (`-f Modelfile`), lalu build model baru bernama `nala-v1`." Dengan `nala-v1`, system prompt sudah otomatis ter-set setiap kali model dijalankan — tidak perlu `/set system` manual lagi.

**Instruksi lain yang umum dipakai di Modelfile:**

| Instruksi | Fungsi | Contoh |
|---|---|---|
| `FROM` | Base model yang jadi dasar (wajib, baris pertama) | `FROM llama3.2:3b` |
| `SYSTEM` | System prompt bawaan model turunan | `SYSTEM """..."""` |
| `PARAMETER` | Parameter generasi bawaan (bisa lebih dari satu baris) | `PARAMETER temperature 0.3` |
| `TEMPLATE` | Format prompt template (jarang perlu diubah untuk model populer — sudah punya default yang benar) | — |

**Parameter yang relevan untuk NALA** (ditambahkan sebagai baris `PARAMETER` terpisah di Modelfile):

```
FROM llama3.2:3b
SYSTEM """Kamu adalah NALA, asisten AI internal PT Nusantara Finance. Tugasmu adalah menjawab pertanyaan staff seputar SOP, kebijakan, dan data operasional perusahaan. Jawab singkat, jelas, dan dalam Bahasa Indonesia. Jika kamu tidak yakin, katakan dengan jujur bahwa kamu tidak memiliki informasi tersebut."""
PARAMETER temperature 0.3
PARAMETER num_ctx 4096
```

- **`temperature`** (0.0–1.0, default ~0.8) — seberapa "kreatif"/acak jawaban model. Untuk asisten internal seperti NALA, nilai rendah (0.2–0.4) lebih disarankan: jawaban lebih konsisten dan lebih kecil kemungkinan mengarang (halusinasi) dibanding nilai default yang dioptimalkan untuk percakapan kasual/kreatif.
- **`num_ctx`** — ukuran context window (berapa token riwayat percakapan + system prompt yang diingat model). Default sering 2048; dinaikkan ke 4096 supaya NALA bisa menyimpan percakapan lebih panjang tanpa "lupa" instruksi awal.

Untuk NALA di titik ini, cukup fokus ke `temperature` dan `num_ctx` seperti contoh di atas. Daftar lengkap semua parameter yang bisa diset (26 parameter, dikelompokkan per kategori) dibahas terpisah di **section 8**.

**Mengelola model custom:**

```bash
ollama list                # lihat semua model, termasuk nala-v1
ollama create nala-v1 -f Modelfile   # (re-)build ulang setelah Modelfile diubah — versi lama otomatis ditimpa
ollama rm nala-v1           # hapus model custom kalau sudah tidak dipakai
ollama show nala-v1 --modelfile   # tampilkan ulang isi Modelfile dari model yang sudah di-build
```

**Praktik baik:** simpan file `Modelfile` di dalam repo project (bukan cuma di riwayat terminal) supaya konfigurasi model NALA bisa di-review lewat git dan reproducible di komputer siapa pun — sama seperti `docker-compose.yml` disimpan di repo, bukan diketik ulang manual tiap kali.

**Checkpoint — verifikasi model custom:**

Setelah `ollama create` selesai (muncul `success`), pastikan model benar-benar berhasil dibuat dan berperilaku sesuai sebelum lanjut:

```bash
ollama list          # nala-v1 harus muncul di daftar
ollama run nala-v1
```

Setelah masuk prompt `>>>`, coba dua jenis pertanyaan:

1. **Pertanyaan identitas** — `Siapa kamu?` → jawaban harus mencerminkan persona NALA (bukan "Saya adalah model bahasa AI...").
2. **Pertanyaan di luar konteks** — `Siapa presiden Indonesia?` → sesuai aturan di system prompt, model seharusnya tidak menjawab asal, melainkan mengarahkan kembali ke konteks PT Nusantara Finance atau mengaku pertanyaan itu di luar cakupannya.

Kalau kedua jawaban sudah sesuai, berarti Modelfile bekerja dengan benar — system prompt dan parameter sudah persisten di `nala-v1` tanpa perlu `/set system` manual lagi. Keluar dengan `/bye`.

### 7.3 Hubungannya dengan Module 4

Kedua cara di atas adalah **cara uji manual**, bukan cara production dipakai NALA. Di Module 4, draft yang sudah divalidasi dengan `/set system` (atau Modelfile) ini akan dipindahkan menjadi konstanta Python `NALA_SYSTEM_PROMPT` (`app/system_prompt.py`), lalu dikirim otomatis lewat API (field `system` di request `/api/generate` atau role `system` di `/api/chat`) setiap ada request masuk ke endpoint `/chat` — tidak perlu diketik ulang oleh siapa pun setiap kali NALA dipakai.

| Tahap | Tempat | Cara |
|---|---|---|
| Draft & uji cepat (Module 3, sekarang) | Terminal | `/set system` atau Modelfile |
| Produksi (Module 4) | Kode FastAPI | Konstanta `NALA_SYSTEM_PROMPT`, dikirim via API `system` field |

---

## 8. Referensi Lengkap Parameter Ollama

Bagian ini adalah referensi semua `PARAMETER` yang bisa diset lewat Modelfile (section 7.2). Ada dua sumber yang sengaja dipisah supaya jelas mana yang benar-benar bisa diandalkan:

- **Resmi didokumentasikan** — tercantum di [docs.ollama.com/modelfile](https://docs.ollama.com/modelfile), dijamin stabil dan didukung.
- **Diterima tapi tidak lagi didokumentasikan resmi** — diverifikasi langsung dengan mencoba satu per satu ke Ollama v0.33.2 yang terinstall (`ollama create` menerimanya tanpa error), tapi **tidak muncul** di dokumentasi resmi saat ini. Kemungkinan peninggalan versi lama (opsi runtime `llama.cpp` di baliknya) yang masih diteruskan, tapi bisa saja dihapus/berubah perilaku tanpa pemberitahuan di versi mendatang. Gunakan dengan hati-hati, terutama untuk kebutuhan production.

### Sampling & Gaya Jawaban

**Resmi didokumentasikan:**

| Parameter | Fungsi | Default |
|---|---|---|
| `temperature` | Tingkat "kreativitas"/keacakan jawaban (lihat penjelasan di section 7.2) | 0.8 |
| `top_k` | Batasi pilihan token ke K kandidat teratas per langkah — nilai kecil (mis. 10-20) bikin jawaban lebih fokus | 40 |
| `top_p` | Nucleus sampling — batasi kandidat token berdasar kumulatif probabilitas, bekerja bersama `top_k` | 0.9 |
| `min_p` | Ambang probabilitas minimum relatif terhadap token terbaik — alternatif yang lebih baru dari `top_p` | 0.0 |
| `repeat_penalty` | Menekan model supaya tidak mengulang kata/frasa yang sama | 1.0 (nonaktif) |
| `repeat_last_n` | Berapa token terakhir yang dicek untuk `repeat_penalty` | 64 |
| `seed` | Angka acak tetap supaya output reproducible antar run (berguna untuk testing/debugging, bukan untuk production) | 0 |
| `num_predict` | Batas maksimal token yang dihasilkan dalam satu jawaban | -1 (tanpa batas) |
| `draft_num_predict` | Batas token draft untuk *speculative decoding* (hanya relevan kalau memakai draft model terpisah) | 4 |
| `stop` | Teks yang menghentikan generasi begitu muncul (bisa lebih dari satu baris `PARAMETER stop "..."`) | — |

**Diterima tapi tidak lagi didokumentasikan resmi:**

| Parameter | Fungsi |
|---|---|
| `typical_p` | Varian sampling berbasis "entropi tipikal" |
| `presence_penalty` | Menekan token yang sudah pernah muncul (mendorong topik baru) |
| `frequency_penalty` | Menekan token berdasar seberapa sering sudah muncul |
| `penalize_newline` | Apakah baris baru (`\n`) ikut kena penalti pengulangan |
| `mirostat`, `mirostat_eta`, `mirostat_tau` | Algoritma sampling alternatif yang menargetkan tingkat "kejutan" (perplexity) tertentu secara otomatis |
| `num_keep` | Berapa token dari awal prompt yang selalu dipertahankan saat context window penuh |

### Context & Memori

**Resmi didokumentasikan:**

| Parameter | Fungsi | Default |
|---|---|---|
| `num_ctx` | Ukuran context window — berapa token riwayat percakapan + system prompt yang diingat model (lihat penjelasan di section 7.2) | 2048 |

### Performa & Hardware

**Diterima tapi tidak lagi didokumentasikan resmi** (biasanya tidak perlu diubah untuk kelas training ini):

| Parameter | Fungsi |
|---|---|
| `num_gpu` | Jumlah layer model yang di-offload ke GPU |
| `main_gpu` | GPU mana yang jadi GPU utama (kalau ada lebih dari satu) |
| `num_thread` | Jumlah CPU thread yang dipakai untuk komputasi |
| `num_batch` | Ukuran batch saat memproses prompt |
| `low_vram` | Mode hemat VRAM untuk GPU dengan memori terbatas |
| `use_mmap` | Apakah model di-load pakai memory-mapped file (default biasanya lebih hemat RAM) |
| `use_mlock` | Kunci model di RAM supaya tidak di-swap ke disk oleh OS |
| `vocab_only` | Hanya load vocabulary tanpa bobot model (dipakai untuk tooling, bukan inference normal) |

> ⚠️ **Catatan:** beberapa nama parameter yang sering muncul di tutorial lama (`numa`, `embedding_only`, `rope_frequency_base`, `rope_frequency_scale`, `tfs_z`) **sudah tidak valid sama sekali** di versi Ollama saat ini — kalau dipakai, `ollama create` akan gagal dengan `Error: unknown parameter`. Ini beda dengan kelompok "diterima tapi tidak didokumentasikan" di atas — nama-nama ini benar-benar ditolak, bukan sekadar tidak resmi.

Untuk NALA di titik ini, cukup fokus ke `temperature` dan `num_ctx` (lihat contoh Modelfile di section 7.2) — keduanya resmi didokumentasikan dan paling berdampak untuk kasus penggunaan asisten internal. Parameter lain di kelompok "resmi" (seperti `stop` atau `top_p`) baru relevan kalau ada kebutuhan spesifik; parameter di kelompok "tidak resmi" sebaiknya dihindari kecuali benar-benar diperlukan dan sudah diuji.

**Sumber:** [Modelfile Reference — docs.ollama.com](https://docs.ollama.com/modelfile) (parameter resmi), ditambah verifikasi empiris langsung ke `ollama create` versi v0.33.2 (parameter tidak resmi & yang sudah tidak valid).

### Contoh Satu-per-Satu: Parameter Resmi

Daripada satu Modelfile besar berisi semua parameter sekaligus, berikut tiap parameter resmi ditunjukkan **terpisah** — supaya efeknya masing-masing lebih jelas terlihat, tidak tercampur. Semua contoh pakai base `FROM llama3.2:3b` dan sudah diuji berhasil di-build satu per satu dengan `ollama create`.

**`temperature`** — turunkan dari default 0.8 ke 0.3 supaya jawaban NALA lebih konsisten, bukan kreatif:
```
FROM llama3.2:3b
PARAMETER temperature 0.3
```

**`top_k`** — persempit dari default 40 ke 20 supaya pilihan kata lebih fokus, cocok dipasangkan dengan `temperature` rendah:
```
FROM llama3.2:3b
PARAMETER top_k 20
```

**`top_p`** — sedikit lebih ketat dari default 0.9 ke 0.85, bekerja bersama `top_k`:
```
FROM llama3.2:3b
PARAMETER top_p 0.85
```

**`min_p`** — naikkan dari default 0.0 ke 0.05 untuk membuang kandidat token yang probabilitasnya jauh di bawah token terbaik (filter kualitas tambahan):
```
FROM llama3.2:3b
PARAMETER min_p 0.05
```

**`repeat_penalty`** — aktifkan ringan dari default 1.0 (nonaktif) ke 1.1 supaya NALA tidak mengulang kalimat yang sama saat jawaban panjang:
```
FROM llama3.2:3b
PARAMETER repeat_penalty 1.1
```

**`repeat_last_n`** — perpanjang dari default 64 ke 128, jendela pengecekan pengulangan lebih luas — relevan kalau nanti jawaban menyertakan konteks RAG yang panjang (Module 11):
```
FROM llama3.2:3b
PARAMETER repeat_last_n 128
```

**`num_predict`** — batasi dari default -1 (tanpa batas) ke 300 token, supaya NALA tidak "ngobrol" kepanjangan untuk pertanyaan simpel:
```
FROM llama3.2:3b
PARAMETER num_predict 300
```

**`stop`** — hentikan generasi begitu model mulai menulis `"Pertanyaan:"` sendiri, pola gagal yang umum terjadi pada model kecil (model melanjutkan percakapan seolah dialog dengan dirinya sendiri):
```
FROM llama3.2:3b
PARAMETER stop "Pertanyaan:"
```

**`seed`** — angka tetap supaya output reproducible antar run. Berguna untuk testing/debugging (bandingkan dua Modelfile dengan seed sama), **tidak dipakai untuk NALA versi production** karena tujuannya justru jawaban yang stabil secara kualitas, bukan identik secara harfiah:
```
FROM llama3.2:3b
PARAMETER seed 42
```

**`draft_num_predict`** — hanya relevan kalau memakai *speculative decoding* dengan draft model tambahan (di luar cakupan training ini, karena `llama3.2:3b` dipakai berdiri sendiri tanpa draft model):
```
FROM llama3.2:3b
PARAMETER draft_num_predict 4
```

Verifikasi tiap Modelfile setelah build (pola sama seperti checkpoint di section 7.2):

```bash
ollama create nala-test -f Modelfile
ollama show nala-test --parameters   # cek parameter tersimpan sesuai yang ditulis
ollama run nala-test
```

### Hasil Uji Coba: Sebelum vs Sesudah

Setiap pasangan di bawah ini adalah **hasil run nyata** dari `llama3.2:3b` (bukan contoh karangan) — prompt yang sama dijalankan dua kali: sekali dengan nilai default, sekali dengan parameter yang diubah.

**`temperature`** — prompt: *"Deskripsikan produk tabungan PT Nusantara Finance dalam satu kalimat promosi yang menarik."*

| Sebelum (default 0.8) | Sesudah (0.3) |
|---|---|
| "Tabungan Anda lebih aman dan maju dengan PT Nusantara Finance, yang menawarkan suku bunga yang kompetitif dan kemudahan akses untuk memulai tabungan Anda hari ini!" | "Tabungan PT Nusantara Finance menawarkan kesempatan untuk membangun kekayaan Anda dengan mudah dan aman, dengan bunga yang kompetitif dan fleksibilitas pembayaran yang fleksibel, sehingga Anda dapat mencapai tujuan keuangan Anda dengan lebih cepat dan nyaman." |

> ⚠️ Catatan jujur: dari **satu kali run**, beda gaya bahasa terlihat tapi tidak dramatis — `temperature` memengaruhi *distribusi* kemungkinan jawaban, bukan menjamin jawaban tertentu di setiap run. Efeknya baru terlihat jelas kalau prompt yang sama dijalankan berkali-kali: di `temperature` rendah, jawaban antar-run akan jauh lebih mirip satu sama lain dibanding di `temperature` tinggi.

**`top_k`** — prompt sama:

| Sebelum (default 40) | Sesudah (10) |
|---|---|
| "Tabungan PT Nusantara Finance menawarkan kesempatan investasi yang aman dan mudah, memberikan Anda kekuatan keuangan yang stabil untuk mencapai tujuan Anda dalam jangka panjang!" | "Tabungan PT Nusantara Finance memberikan kesempatan Anda untuk mencapai tujuan keuangan Anda dengan mudah, aman, dan fleksibel, sehingga Anda bisa merencanakan masa depan yang cerah dan stabil." |

**`top_p`** — prompt sama:

| Sebelum (default 0.9) | Sesudah (0.5) |
|---|---|
| "Tabungan PT Nusantara Finance adalah pilihan yang cerdas untuk jangka panjang, memberikan Anda kekuatan keuangan yang stabil dan aman, sehingga Anda bisa meraih impian Anda dengan lebih mudah dan nyaman." | "Tabungan PT Nusantara Finance menawarkan kesempatan untuk membangun keuangan yang kuat dan stabil dengan bunga yang tinggi dan flexibilitas pembayaran yang fleksibel, sehingga Anda dapat mencapai tujuan keuangan Anda dengan mudah dan aman." |

**`min_p`** — prompt sama:

| Sebelum (default 0.0) | Sesudah (0.2) |
|---|---|
| PT Nusantara Finance menawarkan produk tabungan "Tabungan Nusantara" yang memberikan keuntungan bunga dan keamanan investasi, sehingga Anda dapat memanfaatkan uang tabungan Anda dengan cara yang aman dan menguntungkan. | "Tabungan PT Nusantara Finance adalah pilihan yang tepat untuk Anda yang ingin memulai kehidupan tabungan yang sehat dan stabil, dengan potensi untuk mendapatkan bunga yang menarik dan akses ke berbagai layanan keuangan yang lengkap!" |

**`repeat_penalty`** — prompt: *"Jelaskan pentingnya SOP secara detail, buat sepanjang mungkin, minimal 150 kata."* (jawaban asli panjang, dipotong ke bagian yang relevan):

| Sebelum (default 1.0, nonaktif) | Sesudah (1.5) |
|---|---|
| ...poin 4-7 berpola nyaris identik: *"Meningkatkan Keselamatan: SOP membantu meningkatkan keselamatan dalam suatu proses, karena telah ditentukan secara eksplisit langkah-langkah..."*, *"Meningkatkan Kepatuhan: ... karena telah ditentukan secara eksplisit..."*, *"Meningkatkan Transparansi: ... karena telah ditentukan secara eksplisit..."* — pola kalimat yang sama diulang berkali-kali. | Repetisi pola kalimat memang berkurang, tapi di paruh kedua jawaban modelnya mulai **melenceng topik** (tiba-tiba membahas "Sistem Operasi Pertahanan" dan isu kekerasan, bukan SOP perusahaan) dan tata bahasanya kacau ("dijelaskan denga", "diadu-adukan"). |

> ⚠️ **Temuan penting:** `repeat_penalty` terlalu tinggi (1.5) pada model kecil (`llama3.2:3b`) bisa **mengorbankan koherensi** demi menghindari pengulangan — model "dipaksa" memilih kata lain meski hasilnya jadi tidak masuk akal. Ini alasan kenapa contoh Modelfile NALA di atas memakai nilai yang jauh lebih konservatif (`1.1`), bukan langsung ke nilai agresif.

**`repeat_last_n`** — prompt sama, `repeat_penalty` ditahan tetap di `1.3` supaya perbandingan adil:

| Sebelum (8, jendela pendek) | Sesudah (256, jendela panjang) |
|---|---|
| Struktur list 10 poin, tapi tetap sangat berpola/repetitif per poin ("SOP membantu meningkatkan X dalam pengolahan dan penyampaian tugas-tugas... pekerja dapat melakukan tugas-tugas dengan lebih Y"). | Isi jawaban **melenceng total** dari topik SOP perusahaan menjadi "Sistem Operasi Pertahanan" (kekerasan, privasi) — jauh lebih tidak koheren. |

> ⚠️ Sama seperti `repeat_penalty`, jendela `repeat_last_n` yang terlalu lebar dikombinasikan dengan penalti yang sudah aktif bisa membuat model kecil kehilangan arah. Untuk NALA, nilai moderat (`128`, seperti di contoh Modelfile) lebih aman daripada ekstrem di salah satu sisi.

**`num_predict`** — prompt: *"Jelaskan sejarah lengkap SOP perusahaan dari awal."*

| Sebelum (-1, tanpa batas) | Sesudah (20) |
|---|---|
| Jawaban lengkap ~400 kata, mencakup "Periode Awal (Abad ke-17-18)" sampai "Six Sigma Modern (2000-an)", diakhiri kesimpulan. | "SOP (Standard Operating Procedure) adalah sebuah sistem yang digunakan untuk mengatur dan mengontrol pros" *(terpotong di tengah kata — persis 20 token)* |

Ini yang paling bersih menunjukkan efeknya: `num_predict` langsung memotong output di jumlah token yang ditentukan, tidak peduli kalimatnya selesai atau belum.

**`stop`** — prompt: *"Tulis angka 1 sampai 10 dipisah spasi, lalu tulis kata SELESAI di akhir."*

| Sebelum (tanpa `stop`) | Sesudah (`stop "SELESAI"`) |
|---|---|
| `1 2 3 4 5 6 7 8 9 10 SELESAI` — kata "SELESAI" ikut ditulis. | `1 2 3 4 5 6 7 8 9 10` — generasi berhenti **tepat sebelum** kata "SELESAI" muncul. |

**`seed`** — prompt: *"Tulis satu kalimat unik tentang kucing."*, dijalankan 2x untuk tiap kondisi:

| Tanpa `seed` (2 run) | Dengan `seed 42` (2 run) |
|---|---|
| Run 1: "Kucing memiliki kemampuan untuk menenangkan nyawa manusia dengan hanya menunggangi langkah mereka..." <br> Run 2: "Kucing memiliki kemampuan untuk membuat kebun binatang di rumah mereka sendiri..." — **berbeda** | Run 1: "Kucing memiliki kemampuan untuk mengenali suara yang sangat sulit didengar oleh manusia..." <br> Run 2: "Kucing memiliki kemampuan untuk mengenali suara yang sangat sulit didengar oleh manusia..." — **identik persis** |

Ini pembuktian paling jelas: tanpa `seed`, dua run dengan prompt sama menghasilkan jawaban berbeda. Dengan `seed` yang sama, dua run menghasilkan jawaban **identik karakter-per-karakter**.

**`draft_num_predict`** — tidak ada demo before/after: parameter ini hanya berpengaruh kalau Ollama dijalankan dengan *draft model* terpisah untuk speculative decoding (setup dua model sekaligus), yang di luar cakupan training ini. Mengujinya dengan `llama3.2:3b` berdiri sendiri (seperti parameter lain di atas) tidak akan menunjukkan efek apa pun karena mekanismenya memang tidak aktif tanpa draft model.

---

## Panduan Praktik

Panduan hands-on module ini sudah terintegrasi langsung di bagian-bagian di atas, khususnya:

- **Bagian 5 — Latihan: Menyusun System Prompt NALA v1**: menyusun draft system prompt.
- **Bagian 7 — Menguji System Prompt Anda Sekarang**: mengetes draft tersebut lewat `ollama create -f Modelfile` dan `ollama run`, tanpa perlu menunggu Docker/FastAPI.

Setelah system prompt v1 ini diuji manual di module ini, langkah selanjutnya (menyambungkannya ke aplikasi FastAPI + Docker Compose NALA, termasuk eksperimen rebuild-nya) ada di **Module 4** (`Module-04-Setup-Infra-Docker-Compose/materi.md`, bagian Panduan Praktik, Langkah 6).

**Praktik tambahan (gabungan Module 2 + Module 3):** setelah draft system prompt dan `nala-v1` siap, kerjakan **[WORKSHEET-Evaluasi-Dampak-Prompt-Engineering.md](./WORKSHEET-Evaluasi-Dampak-Prompt-Engineering.md)** — menggabungkan metodologi evaluasi manual Module 2 dengan teknik prompt engineering module ini, untuk **mengukur** (bukan menduga) dampak system prompt terhadap kualitas dan konsistensi jawaban.

**Sesi panjang alternatif (3-4 jam, dari nol):** kalau Anda punya blok waktu panjang dan ingin mengerjakan **instalasi Ollama sampai prompt engineering dalam satu alur tanpa jeda** (menggabungkan seluruh Module 2 + Module 3, termasuk worksheet di atas), pakai **[PANDUAN-PRAKTIK-Sesi-Gabungan-Ollama-Prompt-Engineering.md](./PANDUAN-PRAKTIK-Sesi-Gabungan-Ollama-Prompt-Engineering.md)** — 20 Langkah berurutan dengan estimasi waktu per Langkah, dari `ollama --version` sampai eksperimen `temperature`.

