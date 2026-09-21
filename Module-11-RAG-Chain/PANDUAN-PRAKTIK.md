# Panduan Praktik — Module 11: RAG Chain v1

## Prasyarat
- Sudah menyelesaikan **Module 10** (Vector Store & Semantic Search) — `opensearch` sudah menyala dan sehat

## Langkah 1: `ingest_documents()` v1 — RAG mulai hidup

Sekarang tiga potongan (`extract_text()`, `embed_text()`, `VectorStore`) disatukan jadi `ingest_documents()`. **Belum ada chunking di versi ini** — tiap dokumen di-embed **utuh** jadi satu vektor:

```bash
docker compose exec api python -c "from app.ingest import ingest_documents; print(ingest_documents('/app/knowledge-base'))"
```

Outputnya adalah jumlah **dokumen** (bukan chunk — belum ada chunking) yang ter-index dari `resources/sample-knowledge-base/`. Pastikan angkanya lebih dari 0. Verifikasi lewat OpenSearch langsung:

```bash
curl "http://localhost:9200/nala-docs/_count"
```

Sekarang kembali ke `http://localhost:8000` — halaman yang sama sejak Module 5-6, tidak ada yang berubah dari sisi frontend. Bedanya sekarang index OpenSearch sudah terisi, jadi `/chat/stream` akan menemukan konteks yang relevan dan menjawab berdasarkan dokumen, bukan lagi generik. Coba tanyakan:

> "Berapa lama proses pengajuan kredit sampai pencairan dana?"

NALA seharusnya menjawab dengan angka dari dokumen, bukan estimasi generik — **ini pertama kalinya sepanjang Module 5-14, NALA benar-benar menjawab dari dokumen sungguhan.**

```bash
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Berapa lama proses pengajuan kredit sampai pencairan dana?"}]}'
```

Coba juga pertanyaan yang **sangat spesifik** ke sub-bagian dokumen, misalnya "Apa saja syarat pengajuan kredit untuk nasabah perorangan?" — jawabannya mungkin terasa kurang fokus (seluruh dokumen ikut jadi konteks, bukan cuma bagian yang relevan). Ini **bukan bug** — lihat Module 11 Bagian 7 untuk penjelasan kenapa ini terjadi dan kenapa itu jadi motivasi Module 12 (chunking).

## Troubleshooting

- **Chat menjawab generik / bilang belum ada dokumen internal padahal sudah ingest**: `/chat/stream` otomatis jatuh ke mode tanpa-konteks saat index OpenSearch masih kosong (atau belum menyala) — itu normal, bukan error, tapi tandanya ingest belum berhasil. Cek jumlah dokumen di index dengan:
  ```bash
  curl http://localhost:9200/nala-docs/_count
  ```
  Kalau `count` bernilai 0, index memang kosong — jalankan ulang Langkah 1.
