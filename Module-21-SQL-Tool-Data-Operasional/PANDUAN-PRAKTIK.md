# Panduan Praktik — Module 21: Tool Baru — Query SQL ke Data Operasional (PostgreSQL)

Lanjutan langsung dari `PANDUAN-PRAKTIK.md` Module 20 — agent LangGraph dengan tool `cari_dokumen_sop` harus sudah jalan lewat `/chat` sebelum mulai di sini. Penomoran Langkah melanjutkan penomoran global (Module 19: Langkah 1-5, Module 20: Langkah 6-10).

## Prasyarat
- Module 20 selesai: endpoint `/chat` sudah membalas lewat agent (tool RAG), `/chat/stream` tidak berubah.
- Data operasional dari Module 19 (7 baris `pengajuan_kredit`, 4 baris `klaim_asuransi`) masih ada di database.

## Langkah 11: Tool query-builder untuk data operasional (Module 21)

Ikuti Module 21 `materi.md` bagian tool query-builder (`app/tools/sql_tool.py`) — dibangun di atas `get_connection()` (`app/db.py`) dan role `nala_readonly` yang sudah disiapkan Module 19, bukan raw SQL bebas dari LLM.

```bash
docker compose exec api python -c "
from app.tools.sql_tool import query_data_operasional
print(query_data_operasional(tabel='pengajuan_kredit', mode='hitung_per_status'))
"
```

✅ **Indikator sukses**: daftar status beserta jumlahnya (mis. `pending: 3`, dst.) sesuai data yang sudah dimasukkan lewat form di Module 19 Langkah 5.

## Langkah 12: Daftarkan tool SQL ke agent (Module 21)

Ikuti Module 21 `materi.md` bagian pendaftaran tool SQL ke agent (`app/agent.py`).

```bash
docker compose up --build api
```

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Berapa banyak pengajuan kredit yang statusnya pending?"}'
```

✅ **Indikator sukses**: jawaban menyebut angka yang sesuai (`3`, mengikuti distribusi data Module 19 Langkah 5).

## Langkah 13: Uji detail nasabah, pastikan tool RAG tidak rusak

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Bagaimana status pengajuan kredit nasabah N-00231?"}'

curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Apa saja syarat pengajuan kredit untuk nasabah perorangan?"}'
```

✅ **Indikator sukses**: pertanyaan pertama menyebut status `pending` untuk N-00231; pertanyaan kedua tetap menjawab dari dokumen SOP seperti sebelumnya. Module 21 selesai — lanjut ke `PANDUAN-PRAKTIK.md` di folder Module 22.

## Troubleshooting

- **`permission denied for table ...` padahal seharusnya diizinkan**: tool SQL (Module 21) harus memakai `nala_readonly` (bukan `nala_admin`/`nala_writer`) — tertukar salah satunya akan memicu `permission denied` untuk operasi yang seharusnya sah.
- **Angka yang dijawab `/chat` tidak cocok dengan database**: verifikasi manual dulu isi tabel (`docker compose exec postgres psql -U nala_admin -d nala_operasional -c "SELECT status, COUNT(*) FROM pengajuan_kredit GROUP BY status;"`) — kalau datanya beda dari yang diasumsikan, ulangi Module 19 Langkah 5 sampai datanya sesuai target (7 baris `pengajuan_kredit`, 4 baris `klaim_asuransi`).
- **Error umum lain** (`no configuration file provided`, `failed to read dockerfile`, port sudah dipakai, dsb.): lihat bagian Troubleshooting `PANDUAN-PRAKTIK.md` module-module sebelumnya (Module 5-14) — penyebab dan solusinya sama, tidak spesifik rangkaian Module 19-23.

---

Untuk informasi lebih lanjut, lihat [materi Module 21](./materi.md) dan [README utama](../README.md).
