# Panduan Praktik — Module 13: Upload Dokumen

## Prasyarat
- Sudah menyelesaikan **Module 12** (Chunking) — `ingest_documents()` sudah level-chunk

## Langkah 1: Upload dokumen baru lewat halaman `/upload`

Buka `http://localhost:8000/upload` di browser. Halaman ini punya form upload dengan input file yang membatasi tipe ke `.md`, `.txt`, atau `.pdf` (lihat `accept=".md,.txt,.pdf"` di `app/templates/upload.html`).

1. Siapkan file teks singkat baru (misalnya `catatan-test.md`) berisi satu-dua kalimat — contoh: "Kantor cabang NALA di Surabaya buka setiap hari Senin sampai Jumat pukul 08.00-16.00." Atau pakai salah satu dari 10 dokumen PDF latihan di `resources/sample-knowledge-base/`.
2. Upload file tersebut lewat form.
3. Halaman akan menampilkan pesan **"berhasil diunggah dan di-index (N chunk...)"** — `ingest_documents()` (sudah ada sejak Module 11, sudah di-upgrade untuk chunking di Module 12) langsung dipanggil, tidak ada jeda "simpan dulu proses belakangan". Lihat Module 13 Bagian 1 untuk penjelasan lengkap.
4. Cek file benar-benar tersimpan — dua cara, pilih salah satu:
   - Di dalam container: `docker compose exec api ls -la /app/knowledge-base`
   - Langsung di laptop Anda (tanpa masuk container): `ls resources/sample-knowledge-base/` — folder ini adalah bind mount yang sama persis dengan `/app/knowledge-base` di container, jadi isinya selalu identik.

   Nama file yang Anda upload harus muncul di kedua tempat itu.
5. Halaman `/upload` juga menampilkan **daftar dokumen di knowledge base** — dokumen contoh yang sudah ada sejak awal (termasuk 10 PDF latihan) harus langsung terlihat begitu halaman dibuka, dan dokumen yang baru Anda upload harus langsung muncul di daftar itu setelah halaman reload, tanpa perlu refresh manual kedua kalinya.
6. Coba tanyakan isi dokumen yang baru diupload ke `/chat/stream`, misalnya "Kapan kantor cabang Surabaya buka?" — NALA harus bisa menjawab **tanpa restart apa pun**, membuktikan pipeline upload → chunking → index → retrieve berjalan end-to-end:

```bash
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Kapan kantor cabang Surabaya buka?"}]}'
```

