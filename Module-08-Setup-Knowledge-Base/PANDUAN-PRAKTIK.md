# Panduan Praktik — Module 8: Setup Knowledge Base & Data Dasar Awal

## Prasyarat
- Sudah menyelesaikan **Module 7** (Konsep RAG)
- Container `ollama`+`api` dari `resources/starter-code/day-2/nala/` masih berjalan (kalau tidak, ulangi Module 5 Langkah 2) — module ini belum butuh `opensearch`/`airflow`

## Langkah 1: Verifikasi data seed dan `extract_text()`

Pastikan folder data seed sudah ada dan berisi dokumen SOP contoh:

```bash
ls resources/sample-knowledge-base/
```

`sop-pengajuan-kredit.md`, `sop-klaim-asuransi.md`, dan beberapa file PDF latihan harus muncul di listing.

Sekarang coba `extract_text()` — fungsi ini **membaca isi dokumen apa adanya, utuh**, belum ada chunking sama sekali di titik ini (chunking baru ditambahkan Module 12):

```bash
docker compose exec api python -c "
from app.ingest import extract_text
text = extract_text('/app/knowledge-base/sop-pengajuan-kredit.md')
print(repr(text[:60]))
print(f'Panjang total: {len(text)} karakter')
"
```

Harus menampilkan potongan awal isi file plus panjang total dokumen (bukan potongan). Cabang `.pdf` juga bisa dites kalau sudah ada file PDF di `resources/sample-knowledge-base/`:

```bash
docker compose exec api python -c "
from app.ingest import extract_text
import os
pdf_files = [f for f in os.listdir('/app/knowledge-base') if f.endswith('.pdf')]
print(pdf_files)
print(repr(extract_text(f'/app/knowledge-base/{pdf_files[0]}')[:60]))
"
```

Lihat Module 8 Bagian 3 untuk penjelasan lengkap logika ekstraksi PDF-nya.
