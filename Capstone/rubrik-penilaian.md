# Rubrik Penilaian Capstone

Sesuai `README.md` utama (bagian Format Evaluasi), capstone dinilai dengan **4 kriteria**. Tiap kriteria punya 4 level skor dengan deskriptor konkret — penilai memilih level yang paling sesuai dengan yang **benar-benar ditunjukkan** saat demo/presentasi, bukan yang diklaim lisan tanpa bukti.

Bobot tiap kriteria **sama (25% masing-masing)** kecuali instruktur menentukan pembobotan lain sebelum sesi capstone dimulai — kalau berbeda, sampaikan ke peserta di awal Module 29, bukan saat penilaian berlangsung.

## Kriteria 1: Fungsionalitas Sistem

Seberapa lengkap dan andal NALA berjalan end-to-end saat didemokan — mencakup chat UI, upload dokumen, RAG, agent routing (RAG vs SQL), dan deployment full-stack Module 29.

| Level | Skor | Deskriptor |
|---|---|---|
| **4 — Sangat Baik** | 90-100 | Seluruh alur berjalan tanpa intervensi manual saat demo: upload dokumen baru → ter-index → bisa ditanyakan; pertanyaan operasional ter-routing ke SQL tool dengan benar; streaming, multi-turn, dan status page semuanya berfungsi. Tidak ada error yang terlihat penilai. |
| **3 — Baik** | 75-89 | Alur inti (chat RAG, chat SQL tool) berjalan lancar; ada 1-2 fitur pendukung (upload real-time, badge tool, status page) yang sedikit kurang mulus tapi tidak menggagalkan demo — presenter berhasil menjelaskan/mengatasinya secara langsung. |
| **2 — Cukup** | 60-74 | Fungsi inti (chat, RAG) berjalan, tapi agent routing RAG-vs-SQL tidak konsisten benar, atau ada fitur Module 29-30 (deployment full-stack, monitoring) yang tidak berhasil didemokan secara live dan hanya dijelaskan lisan. |
| **1 — Perlu Perbaikan** | <60 | Demo live gagal berjalan sama sekali (harus fallback ke screenshot/rekaman untuk sebagian besar bagian), atau fungsi inti (chat dasar) tidak bisa ditunjukkan bekerja. |

## Kriteria 2: Quality of Retrieved Answers

Seberapa relevan dan akurat jawaban NALA terhadap pertanyaan yang diajukan — mencakup grounding (tidak mengarang), relevansi retrieval, dan penanganan kasus "tidak tahu".

| Level | Skor | Deskriptor |
|---|---|---|
| **4 — Sangat Baik** | 90-100 | Jawaban RAG konsisten sesuai isi dokumen sumber (bisa diverifikasi langsung oleh penilai), jawaban SQL tool akurat sesuai data operasional; NALA secara jujur mengaku tidak tahu untuk pertanyaan di luar cakupan dokumen/data, bukan mengarang. |
| **3 — Baik** | 75-89 | Mayoritas jawaban akurat dan relevan; ada 1-2 contoh jawaban yang kurang presisi (misalnya chunk yang kurang relevan ter-retrieve) tapi presenter mengenali dan menjelaskan kenapa (bukan mengklaim itu sempurna). |
| **2 — Cukup** | 60-74 | Beberapa jawaban terasa generik/tidak spesifik terhadap dokumen (indikasi retrieval kurang tepat), atau ada indikasi halusinasi ringan yang tidak diakui presenter saat ditanya. |
| **1 — Perlu Perbaikan** | <60 | Jawaban sering tidak relevan dengan pertanyaan, banyak indikasi mengarang (menjawab detail yang tidak ada di dokumen/data sebagai fakta), atau grounding tidak berfungsi (model menjawab dari pengetahuan umum meski dokumen tersedia). |

## Kriteria 3: Pemahaman Teknis tentang Trade-off yang Dilakukan

Seberapa dalam peserta memahami **kenapa** sistem dibangun dengan cara tertentu — bukan cuma bisa menjalankan, tapi bisa menjelaskan pilihan desain dan keterbatasannya.

| Level | Skor | Deskriptor |
|---|---|---|
| **4 — Sangat Baik** | 90-100 | Peserta bisa menjelaskan minimal 3 trade-off konkret dari training ini (contoh: model 3B vs akurasi routing Module 23-27, vector search murni vs hybrid+reranking Module 17-22, grounding ketat vs fleksibilitas jawaban Module 7-16, Airflow vs upload endpoint) dengan alasan yang benar secara teknis, termasuk kapan pilihan itu bisa berubah di konteks lain. |
| **3 — Baik** | 75-89 | Peserta bisa menjelaskan 2+ trade-off dengan benar saat ditanya, meski tidak proaktif diangkat di presentasi awal. |
| **2 — Cukup** | 60-74 | Peserta menyebutkan trade-off tapi penjelasannya dangkal atau sebagian tidak akurat secara teknis (misalnya salah memahami kenapa suatu keputusan diambil). |
| **1 — Perlu Perbaikan** | <60 | Peserta tidak bisa menjelaskan trade-off apa pun saat ditanya, atau menjawab dengan "karena diminta modul" tanpa pemahaman alasan teknis di baliknya. |

**Area trade-off yang relevan untuk digali** (bukan daftar wajib, tapi rujukan penilai): pilihan model `llama3.2:3b` (README utama), grounding vs fleksibilitas (Module 13 Bagian 4), keterbatasan vector search murni sebelum hybrid+reranking (Module 13 Bagian 7, Module 17-22), Airflow vs upload endpoint (Module 13 Bagian 5), agent routing RAG-vs-SQL (Module 23-27), RBAC/prompt injection sebagai risiko yang diakui bukan diselesaikan (Module 30 Bagian 3), dan resource/RAM full-stack (Module 29 Bagian 4).

## Kriteria 4: Presentasi dan Komunikasi Hasil

Seberapa jelas dan meyakinkan peserta mengomunikasikan apa yang dibangun — kepada audiens campuran teknis dan non-teknis, konsisten dengan target peserta training ini.

| Level | Skor | Deskriptor |
|---|---|---|
| **4 — Sangat Baik** | 90-100 | Presentasi terstruktur jelas (problem framing → arsitektur → demo → trade-off → next steps, lihat `template-presentasi.md`), bisa dipahami peserta non-teknis maupun teknis, demo di dalam alokasi waktu, menjawab pertanyaan penilai dengan percaya diri dan akurat. |
| **3 — Baik** | 75-89 | Struktur presentasi jelas dan demo berjalan, tapi ada bagian yang terlalu teknis untuk audiens non-teknis atau sebaliknya terlalu dangkal untuk audiens teknis, atau sedikit melebihi alokasi waktu. |
| **2 — Cukup** | 60-74 | Presentasi kurang terstruktur (melompat-lompat, sulit diikuti), atau demo memakan waktu jauh lebih lama dari alokasi karena tidak dipersiapkan alur yang jelas. |
| **1 — Perlu Perbaikan** | <60 | Presentasi tidak mengikuti alur yang bisa diikuti audiens, tidak ada demo hidup sama sekali, atau tidak bisa menjawab pertanyaan dasar tentang apa yang ditampilkan. |

## Catatan untuk Penilai

- Rubrik ini dinilai **per kelompok/peserta**, bukan relatif dibanding kelompok lain — dua kelompok bisa sama-sama mendapat skor tinggi kalau memang sama-sama layak.
- Kegagalan teknis kecil saat demo live (lihat catatan fallback di Module 31 materi.md, bagian Panduan Praktik > Troubleshooting) **tidak otomatis** menjatuhkan skor Kriteria 1 ke level terendah — nilai bagaimana presenter menangani kegagalan itu di bawah Kriteria 4, bukan menghukum dua kali di kedua kriteria untuk masalah yang sama.
- Skor akhir = rata-rata (atau rata-rata berbobot, kalau bobot disesuaikan) dari keempat kriteria, dibulatkan sesuai kebijakan standar penilaian institusi penyelenggara.
