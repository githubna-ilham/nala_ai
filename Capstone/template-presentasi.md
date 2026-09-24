# Template & Outline Presentasi Capstone

Gunakan outline ini untuk menyusun presentasi capstone — baik sebagai slide, dokumen, atau sekadar catatan alur bicara (format bebas, format inti yang wajib dicakup ada di bawah). Alokasi waktu total per kelompok/peserta: **10-15 menit** (termasuk tanya-jawab singkat) — lihat README utama untuk alokasi total sesi capstone.

## 1. Problem Framing (± 2 menit)

Jelaskan **studi kasus** yang jadi dasar demo — bisa memakai `case-study-brief.md` yang disediakan, atau variasi yang disepakati dengan instruktur.

Wajib dijawab:
- Masalah/kebutuhan apa yang coba diselesaikan? (contoh: staff finance kesulitan mencari SOP terbaru, atau butuh cara cepat cek status pengajuan kredit tanpa akses langsung ke database)
- Siapa penggunanya? (staff non-teknis PT Nusantara Finance — konsisten dengan target pengguna NALA sejak awal training)
- Kenapa ini butuh RAG **dan** agentic tool (bukan cuma salah satu)?

## 2. Architecture Walkthrough (± 3 menit)

Tunjukkan (boleh pakai diagram Mermaid dari materi Module 4 atau Module 29 sebagai basis, disesuaikan) arsitektur NALA yang dipakai:

- Service apa saja yang berjalan (Ollama, OpenSearch, PostgreSQL, Airflow, Langfuse, dst)
- Alur satu pertanyaan dari user sampai jawaban keluar — sebutkan di titik mana agent memutuskan RAG vs SQL tool
- Apa yang **berbeda/disesuaikan** dari default training (kalau ada) untuk studi kasus spesifik kelompok Anda

## 3. Skrip Demo (± 5 menit)

**Wajib demo lewat frontend web** (`http://localhost:8000`), bukan hanya `curl`/Postman — sesuai persyaratan capstone di spec training ("termasuk demo lewat frontend, bukan hanya curl/Postman").

Skenario demo yang disarankan (sesuaikan dengan studi kasus Anda):

1. **Upload dokumen baru** (kalau studi kasus melibatkan jenis dokumen baru) — tunjukkan form `/upload`, lalu langsung tanyakan isinya lewat chat untuk membuktikan pipeline ingest → index → retrieve bekerja tanpa restart.
2. **Pertanyaan RAG** — tanyakan sesuatu yang jawabannya ada di dokumen SOP, tunjukkan badge "Dokumen SOP (RAG)" (Module 31) muncul, dan jawabannya sesuai isi dokumen.
3. **Pertanyaan data operasional** — tanyakan sesuatu yang butuh SQL tool, tunjukkan badge "Data Operasional (SQL)" muncul, dan jawabannya sesuai data di database.
4. **Pertanyaan di luar cakupan** — tanyakan sesuatu yang sengaja tidak ada di dokumen/data, tunjukkan NALA jujur mengaku tidak tahu (grounding, Module 13 Bagian 4) alih-alih mengarang.
5. **(Opsional tapi dianjurkan)** Tunjukkan trace pertanyaan-pertanyaan di atas lewat dashboard Langfuse (`http://localhost:3000`) untuk membuktikan observability berjalan.

**Siapkan fallback** (screenshot/rekaman singkat dari uji coba sebelumnya) kalau demo live gagal di tengah presentasi — lihat catatan di Module 32 materi.md, bagian Panduan Praktik > Troubleshooting. Kegagalan teknis yang ditangani dengan tenang **tidak** otomatis menjatuhkan nilai (lihat `rubrik-penilaian.md` Kriteria 4).

## 4. Trade-off yang Diambil (± 3 menit)

Ini bagian yang paling menentukan skor Kriteria 3 di rubrik — jangan dilewati atau diringkas jadi satu kalimat generik. Pilih **minimal 2-3 trade-off** yang benar-benar relevan dengan kelompok/studi kasus Anda dan jelaskan:

- **Apa** trade-off-nya (dua pilihan yang bertentangan)
- **Kenapa** pilihan yang diambil dianggap tepat untuk kasus ini
- **Kapan** pilihan itu bisa berubah kalau konteksnya beda

Contoh area (pilih yang relevan, tidak wajib semua):
- Model `llama3.2:3b` vs model lebih besar (akurasi vs resource, README utama & Module 23-28)
- Grounding ketat (menolak menjawab di luar konteks) vs fleksibilitas jawaban (Module 13 Bagian 4)
- Vector search murni vs hybrid search + reranking (Module 17-22, Module 13 Bagian 7)
- Airflow scheduled ingest vs upload endpoint instan (Module 13 Bagian 5)
- Bagaimana agent Anda menangani ambiguitas routing RAG vs SQL (Module 23-28)
- Risiko keamanan yang diakui tapi belum diselesaikan penuh (prompt injection, rate limiting — Module 30 Bagian 3)

## 5. Apa yang Akan Diperbaiki dengan Waktu Lebih (± 2 menit)

Tutup presentasi dengan jujur — apa yang **belum** sempat/belum bisa diselesaikan, dan langkah konkret apa yang akan diambil kalau ada waktu tambahan. Ini bukan pengakuan kegagalan — justru menunjukkan pemahaman batas sistem yang dibangun (selaras dengan Kriteria 3 rubrik).

Contoh format:
> "Kalau ada waktu lebih, kami akan [X] karena [alasan]. Saat ini [Y] belum kami tangani karena [batasan waktu/scope training], tapi kami tahu pendekatannya adalah [Z]."

## Checklist Sebelum Naik Presentasi

- [ ] Stack Docker Compose sudah `Up`/`healthy` (`docker compose ps`)
- [ ] Dokumen/data studi kasus sudah ter-upload dan ter-index
- [ ] Sudah dicoba end-to-end minimal sekali sebelum sesi (bukan pertama kali dicoba di depan penilai)
- [ ] Fallback (screenshot/rekaman) siap kalau demo live bermasalah
- [ ] Tahu jawaban untuk pertanyaan trade-off yang mungkin ditanya penilai (lihat Bagian 4 di atas)
