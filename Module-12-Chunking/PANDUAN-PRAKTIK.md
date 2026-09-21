# Panduan Praktik — Module 12: Chunking

## Prasyarat
- Sudah menyelesaikan **Module 11** (RAG Chain v1) — RAG sudah "hidup", index `nala-docs` sudah terisi minimal sekali

## Langkah 1: Chunking + upgrade `ingest_documents()`, naikkan `top_k`

Sekarang tambahkan `chunk_text()` (fixed-size dengan overlap) dan `chunk_markdown()` (structure-aware berbasis heading), lalu upgrade `ingest_documents()` supaya memecah dokumen jadi chunk dulu sebelum embed. Setelah kode di Module 12 Bagian 7 selesai ditulis, coba:

```bash
docker compose exec api python -c "
from app.ingest import chunk_text
text = 'x' * 1200
chunks = chunk_text(text)
print(f'Jumlah chunk: {len(chunks)}')
print(f'Panjang tiap chunk: {[len(c) for c in chunks]}')
"
```

Harus menghasilkan 3 chunk dengan panjang `[500, 500, 300]`.

```bash
docker compose exec api python -c "
from app.ingest import chunk_markdown, chunk_text, extract_text
text = extract_text('/app/knowledge-base/sop-pengajuan-kredit.md')
print('chunk_text:', len(chunk_text(text)), 'chunk')
print('chunk_markdown:', len(chunk_markdown(text)), 'chunk')
print('Chunk pertama (markdown):', chunk_markdown(text)[0])
"
```

`chunk_markdown()` harus menghasilkan **13 chunk**, `chunk_text()` cuma **8 chunk** pada dokumen yang sama — dan chunk pertama dari `chunk_markdown` berupa satu heading utuh (`# SOP Pengajuan Kredit...`), bukan potongan 500 karakter sembarang.

Setelah `ingest_documents()` di-upgrade (Module 12 Bagian 8 Langkah 3) dan `top_k` dinaikkan jadi 6 di `chat_stream()` (Module 12 Bagian 8 Langkah 4), re-ingest data seed:

```bash
docker compose exec api python -c "from app.ingest import ingest_documents; print(ingest_documents('/app/knowledge-base'))"
```

Bandingkan angkanya dengan hasil Module 11 Langkah 1 — sekarang harus **jauh lebih besar** (dulu = jumlah dokumen, sekarang = jumlah chunk). Coba lagi lewat `/chat/stream` pertanyaan spesifik yang terasa kurang fokus di Module 11 — retrieval sekarang seharusnya lebih presisi karena tiap chunk mewakili satu sub-topik, bukan seluruh dokumen. Lihat Module 12 Bagian 9 untuk kasus di mana bahkan chunking pun belum cukup (motivasi Module 15).

