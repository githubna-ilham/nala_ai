# Panduan Praktik — Module 22: Routing — Menggabungkan RAG + SQL Tool dalam Satu Agent

Lanjutan langsung dari `PANDUAN-PRAKTIK.md` Module 21 — agent dengan dua tool (`cari_dokumen_sop`, `query_data_operasional`) harus sudah jalan lewat `/chat` sebelum mulai di sini. Penomoran Langkah melanjutkan penomoran global (Module 19: Langkah 1-5, Module 20: Langkah 6-10, Module 21: Langkah 11-13).

## Prasyarat
- Module 21 selesai: `/chat` bisa menjawab pertanyaan RAG maupun SQL secara terpisah, tanpa regresi.

## Langkah 14: Uji tabel skenario routing (Module 22 Bagian 2), verifikasi lawan database

Jalankan **keenam** baris tabel `materi.md` Module 22 Bagian 2 satu per satu lewat `curl -X POST http://localhost:8000/chat ...` (format sama seperti Langkah 12-13). Jangan cuma baca jawabannya sekilas — cocokkan isinya langsung dengan data asli:

```bash
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" \
  -d '{"message": "Apa saja syarat pengajuan kredit untuk nasabah perorangan?"}'

curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" \
  -d '{"message": "Berapa banyak pengajuan kredit yang statusnya pending minggu ini?"}'

curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" \
  -d '{"message": "Bagaimana status klaim asuransi nasabah N-00305?"}'

curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" \
  -d '{"message": "Kenapa pengajuan kredit nasabah N-00305 ditolak?"}'

curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" \
  -d '{"message": "Halo, kamu siapa?"}'

curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" \
  -d '{"message": "Apa itu bunga majemuk?"}'
```

Untuk pertanyaan yang menyentuh data operasional, verifikasi jawabannya langsung terhadap database, jangan percaya begitu saja:

```bash
docker exec nala-postgres-1 psql -U nala_admin -d nala_operasional \
  -c "SELECT status, count(*) FROM pengajuan_kredit GROUP BY status;"

docker exec nala-postgres-1 psql -U nala_admin -d nala_operasional \
  -c "SELECT nasabah_id, status, alasan_penolakan FROM pengajuan_kredit WHERE nasabah_id='N-00305';"
```

✅ **Indikator untuk dicatat**: keenam baris tabel routing sudah dicoba **dan** jawabannya dicocokkan manual dengan data asli — bukan cuma "tool yang benar terpanggil". Hasil pengujian nyata (Module 22 Bagian 6.a): tool yang dipanggil hampir selalu tepat, tapi jawaban akhir bisa mengarang detail yang tidak sesuai data (mis. alasan penolakan kredit) meski tool sudah mengembalikan data yang benar — sama seperti temuan Module 21 Bagian 6. Jalankan tabel ini lebih dari sekali kalau memungkinkan: hasil bisa berbeda antar-run untuk pertanyaan yang identik (lihat catatan non-determinisme di Bagian 6.a), jadi satu kali percobaan tidak cukup untuk klaim "sudah benar" atau "gagal".

## Langkah 15: Uji kasus ambigu, coba perbaikan `description` (Module 22 Bagian 4)

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Kredit saya gimana?"}'
```

Amati tool mana yang dipanggil (kalau ada) dan apakah jawabannya membantu. Coba terapkan perbaikan `description` dari Module 22 Bagian 4.b Langkah 2 ke `app/tools/sql_tool.py`, `docker compose up --build api` ulang, ulangi pertanyaan yang sama — bandingkan hasilnya.

✅ **Indikator untuk dicatat**: perbandingan sebelum/sesudah perbaikan description — tidak wajib "sempurna", tujuannya memahami bahwa description memengaruhi routing tapi bukan jaminan mutlak.

## Langkah 16: Uji `MAX_TOOL_ROUNDS`/`force_answer` (Module 22 Bagian 5-Bagian 6.b)

Ikuti Module 22 Bagian 5 Langkah 4 (tambah `force_answer`, `MAX_TOOL_ROUNDS`).

```bash
docker compose up --build api
```

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Berapa banyak pengajuan kredit yang statusnya pending?"}'
```

✅ **Indikator sukses**: jawaban tetap benar (tidak ada regresi, kasus ini jauh di bawah `MAX_TOOL_ROUNDS`).

**Coba picu `force_answer` secara nyata** — turunkan `MAX_TOOL_ROUNDS` ke `1` tanpa mengubah/rebuild image (lebih cepat untuk eksperimen berulang daripada edit `app/agent.py`):

```bash
docker compose stop api
docker compose run --rm -d -e MAX_TOOL_ROUNDS=1 -p 8000:8000 --name nala-api-force-test api

# verifikasi env var benar-benar terset di container test
docker exec nala-api-force-test python -c "from app.agent import MAX_TOOL_ROUNDS; print(MAX_TOOL_ROUNDS)"
```

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Kenapa pengajuan kredit nasabah N-00305 ditolak?"}'
```

⚠️ **Ekspektasi yang realistis** (bukan tebakan, ini temuan nyata Module 22 Bagian 6.b): kemungkinan besar `force_answer` **tidak akan terpicu** oleh percobaan di atas. Pengujian sungguhan menunjukkan `llama3.2:3b` cenderung membundel semua tool call yang dianggap perlu ke **satu** giliran (bukan berurutan lewat beberapa putaran), atau berhenti lebih dulu dan mengarang jawaban ketimbang meminta putaran tool tambahan — bahkan kalau diminta eksplisit. Jangan anggap ini kegagalan latihan; ini pola nyata yang perlu didokumentasikan.

✅ **Indikator sukses yang tetap valid**: NALA tetap memberi jawaban (tidak macet/timeout) di kedua kasus (baik `force_answer` benar-benar terpicu maupun tidak). Untuk memastikan pengaman ini **benar secara logika** walau sulit dipicu organik, verifikasi langsung di level kode (Module 22 Bagian 6.b) — jalankan di dalam container test:

```bash
docker exec nala-api-force-test python -c "
from app.agent import _count_tool_rounds
messages = [
    {'role': 'system', 'content': 'x'},
    {'role': 'user', 'content': 'x'},
    {'role': 'assistant', 'content': '', 'tool_calls': [{'id': 'a', 'function': {'name': 'f', 'arguments': {}}}]},
    {'role': 'tool', 'content': 'hasil', 'tool_call_id': 'a', 'name': 'f'},
    {'role': 'assistant', 'content': '', 'tool_calls': [{'id': 'b', 'function': {'name': 'f', 'arguments': {}}}]},
]
print('tool rounds:', _count_tool_rounds(messages))  # harus 1
"
```

Bersihkan container test dan kembalikan yang normal:

```bash
docker stop nala-api-force-test
docker compose up -d api
```

Kembalikan `MAX_TOOL_ROUNDS` ke `3` (default, tidak perlu ubah kode kalau tidak pernah diubah permanen). Module 22 selesai — lanjut ke `PANDUAN-PRAKTIK.md` di folder Module 23.

## Troubleshooting

- **Routing tool terasa buruk terus-menerus meski sudah memperbaiki `description` (Module 22 Bagian 4.b)**: pertimbangkan opsi `qwen2.5:7b` (Module 22 Bagian 4.b Langkah 3) **hanya** kalau laptop punya RAM 32GB+ — jangan dipaksakan di laptop 16GB yang sudah menjalankan Ollama + OpenSearch + Airflow + PostgreSQL bersamaan, risiko container ter-*kill* karena kehabisan memory jauh lebih mengganggu daripada akurasi routing yang belum sempurna.
- **Agent tampak "menggantung" lama (timeout) untuk pertanyaan yang butuh dua tool**: wajar sampai batas tertentu — setiap putaran tool berarti minimal satu panggilan tambahan ke `llama3.2:3b` (Module 22 Bagian 1), jadi pertanyaan yang butuh dua tool berurutan otomatis lebih lambat dari pertanyaan satu-tool. Kalau benar-benar tidak pernah selesai (bukan cuma lambat), pastikan `MAX_TOOL_ROUNDS`/`force_answer` (Module 22 Bagian 5, Langkah 16) sudah terpasang dengan benar.
- **Error umum lain** (`no configuration file provided`, `failed to read dockerfile`, port sudah dipakai, dsb.): lihat bagian Troubleshooting `PANDUAN-PRAKTIK.md` module-module sebelumnya (Module 5-14) — penyebab dan solusinya sama, tidak spesifik rangkaian Module 19-23.

---

Untuk informasi lebih lanjut, lihat [materi Module 22](./materi.md) dan [README utama](../README.md).
