# Studi Kasus Capstone: Perluasan NALA ke Divisi Leasing Kendaraan

## Latar Belakang

PT Nusantara Finance baru saja meluncurkan lini bisnis baru: **leasing kendaraan operasional untuk korporat** (mobil dan motor untuk perusahaan mitra, bukan pembiayaan retail perorangan seperti kredit yang sudah dilayani NALA sejak Module 1-27). Divisi Leasing meminta akses ke NALA, tapi kebutuhan mereka sedikit berbeda dari divisi Kredit yang jadi basis studi kasus sejak awal training:

1. **Dokumen SOP baru**: Divisi Leasing punya SOP sendiri — *"SOP Leasing Kendaraan Operasional Korporat"* — yang belum pernah masuk ke knowledge base NALA. Dokumen ini mencakup syarat pengajuan leasing korporat, proses appraisal kendaraan, skema pembayaran (bulanan vs tahunan), dan prosedur perpanjangan/terminasi kontrak.
2. **Jenis pertanyaan operasional baru**: staf Leasing perlu bertanya soal data kontrak leasing aktif — misalnya "Berapa banyak kontrak leasing yang jatuh tempo bulan ini?" atau "Unit kendaraan apa saja yang sedang dalam proses appraisal untuk klien PT Mitra Jaya?" — pertanyaan ini **tidak bisa** dijawab dari dokumen SOP (itu prosedur, bukan data transaksional), harus di-routing ke SQL tool seperti pertanyaan data pengajuan kredit di Module 23-27, tapi menyentuh tabel/data yang berbeda (data kontrak leasing, bukan data pengajuan kredit).

## Tugas Capstone

Gunakan NALA (hasil Module 1-31 Anda) untuk menjawab kebutuhan Divisi Leasing di atas. Secara konkret:

### 1. Tambahkan dokumen SOP baru ke knowledge base

Buat (atau adaptasi dari salah satu dokumen contoh yang ada) satu dokumen SOP baru bertema leasing kendaraan operasional korporat, minimal mencakup:
- Syarat pengajuan leasing untuk korporat (dokumen legalitas perusahaan, minimal masa operasional, dst — bebas berkreasi selama masuk akal)
- Tahapan proses: pengajuan → appraisal kendaraan → persetujuan → penandatanganan kontrak → serah terima
- Skema pembayaran yang tersedia (bulanan/tahunan) dan konsekuensi keterlambatan
- Prosedur perpanjangan dan terminasi kontrak lebih awal

Upload dokumen ini lewat `/upload` (Module 16), verifikasi ter-index (Module 12-13), dan pastikan NALA bisa menjawab pertanyaan berdasarkan isinya lewat RAG.

### 2. Siapkan data operasional dummy untuk kontrak leasing

Buat tabel/data dummy baru di PostgreSQL (terpisah atau menyatu dengan skema data operasional Module 23-27, sesuai desain Anda) yang merepresentasikan kontrak leasing aktif — minimal kolom: nama klien korporat, jenis/jumlah kendaraan, tanggal mulai kontrak, tanggal jatuh tempo, status (aktif/proses appraisal/berakhir), skema pembayaran.

### 3. Perluas atau verifikasi agent routing (Module 23-27)

Pastikan agent NALA bisa membedakan dengan benar:
- Pertanyaan prosedural leasing → RAG (dokumen SOP baru)
- Pertanyaan data kontrak leasing → SQL tool (tabel baru)
- Pertanyaan lama seputar kredit (Module 1-27) → tetap berfungsi seperti sebelumnya, tidak boleh regresi

### 4. Review keamanan untuk kasus baru ini

Terapkan checklist Module 29 Bagian 3 khusus untuk data leasing baru ini — misalnya: apakah data kontrak korporat butuh pembatasan akses berbeda dari data kredit perorangan (RBAC)? Apakah ada risiko prompt injection baru kalau dokumen SOP leasing berasal dari draft yang belum direview penuh?

## Yang Dinilai Saat Demo Capstone

Gunakan `template-presentasi.md` untuk struktur presentasi, dan `rubrik-penilaian.md` untuk kriteria penilaian. Secara khusus untuk studi kasus ini, penilai akan memperhatikan:

- Apakah dokumen SOP baru benar-benar ter-retrieve dengan relevan (bukan cuma ter-upload)
- Apakah routing RAG-vs-SQL benar untuk **kedua** domain (kredit lama dan leasing baru) — bukti bahwa agent Anda men-generalisasi, bukan di-hardcode untuk satu domain saja
- Apakah fitur lama (chat kredit, multi-turn, streaming) tetap berfungsi setelah domain baru ditambahkan — tidak ada regresi
- Kualitas jawaban untuk pertanyaan di luar cakupan (baik SOP kredit lama maupun leasing baru) — NALA tetap jujur mengaku tidak tahu, bukan mengarang

## Variasi yang Diperbolehkan

Studi kasus ini adalah **contoh konkret**, bukan satu-satunya pilihan sah. Kelompok/peserta boleh mengganti dengan studi kasus lain yang setara kompleksitasnya (jenis dokumen SOP baru + jenis pertanyaan operasional baru yang perlu di-routing ke SQL tool), selama disepakati dengan instruktur sebelum sesi persiapan capstone. Yang **tidak** berubah dari brief ini, apa pun variasinya:

- Tetap harus mendemokan **kedua** kanal akses data (RAG dokumen **dan** SQL tool data operasional) dalam satu skenario yang koheren.
- Tetap sepenuhnya offline/private-first — tidak ada panggilan ke LLM cloud atau API pihak ketiga mana pun, konsisten dengan prinsip NALA sejak Module 1.
- Tetap didemokan lewat frontend web NALA (`http://localhost:8000`), bukan hanya lewat `curl`/Postman.
