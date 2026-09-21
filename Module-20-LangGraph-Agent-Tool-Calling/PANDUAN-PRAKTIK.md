# Panduan Praktik — Module 20: Desain Agent dengan LangGraph — Tool-Calling

Lanjutan langsung dari `PANDUAN-PRAKTIK.md` Module 19 — folder `resources/starter-code/day-4/nala/` dan service `postgres` (dengan data operasional yang sudah Anda isi lewat form) harus sudah siap sebelum mulai di sini. Penomoran Langkah di bawah melanjutkan penomoran global dari Module 19 (Langkah 1-5), supaya referensi silang antar-panduan tetap konsisten.

## Prasyarat
- Module 19 selesai: service `postgres` sehat, tabel `pengajuan_kredit`/`klaim_asuransi` sudah berisi data (7 baris + 4 baris) lewat form `/data-operasional`, role `nala_readonly`/`nala_writer` terverifikasi dua arah.
- `docker compose up -d --build` sudah pernah dijalankan dari `resources/starter-code/day-4/nala/` — kalau container belum jalan, jalankan ulang dari folder itu sebelum melanjutkan.

## Langkah 6: Tambah dependency `langgraph`, method `chat()` di `OllamaClient` (Module 20 Tahap A)

Ikuti Module 20 Bagian 4 Tahap A Langkah 1-2 (tambah `langgraph` ke `requirements.txt`, tambah method `chat()` ke `app/ollama_client.py`).

```bash
docker compose up --build --no-deps ollama api
```

```bash
docker compose exec api python -c "
from app.ollama_client import OllamaClient
client = OllamaClient(base_url='http://ollama:11434', model='llama3.2:3b')
result = client.chat(messages=[{'role': 'user', 'content': 'Halo, siapa kamu?'}])
print(result)
"
```

✅ **Indikator sukses**: dict Python dengan `role`/`content`, tidak ada error. `/chat` belum berubah perilaku.

## Langkah 7: Tool pertama — bungkus RAG chain (Module 20 Tahap B)

Ikuti Module 20 Bagian 4 Tahap B Langkah 3 (buat `app/tools/rag_tool.py`).

```bash
docker compose exec api python -c "
from app.vector_store import VectorStore
from app.tools.rag_tool import rag_search
store = VectorStore(base_url='http://opensearch:9200', index_name='nala-docs')
print(rag_search('syarat pengajuan kredit', store, 'http://ollama:11434')[:200])
"
```

✅ **Indikator sukses**: potongan teks dari dokumen SOP (asumsi index OpenSearch dari module-module sebelumnya masih terisi — kalau kosong, jalankan ulang ingest, lihat `PANDUAN-PRAKTIK.md` module yang membangun Airflow ingest pipeline, Module 14).

## Langkah 8: Bangun graph LangGraph (Module 20 Tahap C)

Ikuti Module 20 Bagian 4 Tahap C Langkah 4-5 (system prompt agent + `app/agent.py`).

```bash
docker compose up --build api
```

✅ **Indikator sukses**: log `api` menunjukkan `Uvicorn running` tanpa traceback — `nala_agent` belum dipanggil dari endpoint mana pun di titik ini.

## Langkah 9: Sambungkan agent ke `/chat` (Module 20 Tahap C Langkah 6)

Ikuti Module 20 Bagian 4 Tahap C Langkah 6.

```bash
docker compose up --build api
```

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Apa saja syarat pengajuan kredit untuk nasabah perorangan?"}'
```

✅ **Indikator sukses**: jawaban berbasis dokumen, kualitas setara Langkah 1 (agent memakai tool RAG, hasilnya seharusnya tidak berubah dari sebelum di-refactor).

## Langkah 10: Pastikan `/chat/stream` tidak tersentuh, dan pertanyaan tanpa tool tetap jalan

```bash
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Halo, kamu siapa?"}]}'
```

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Halo, kamu siapa?"}'
```

✅ **Indikator sukses**: `/chat/stream` tetap streaming seperti sebelumnya (belum lewat agent, sesuai catatan scope Module 20 Bagian 4 Tahap C). `/chat` untuk sapaan tetap menjawab tanpa error — bukti `should_continue` mengarah ke `END` langsung tanpa memanggil tool. Module 20 selesai — lanjut ke `PANDUAN-PRAKTIK.md` di folder Module 21.

## Troubleshooting

- **`message.tool_calls` selalu kosong padahal pertanyaannya jelas butuh tool**: cek versi Ollama (`docker compose exec ollama ollama --version`) — dukungan tool-calling butuh versi yang cukup baru. Cek juga `RAG_TOOL_SCHEMA` terkirim dengan benar sebagai parameter `tools` di `OllamaClient.chat()` (Module 20 Bagian 3, ⚠️ catatan kejujuran teknis).
- **Agent tampak "menggantung" lama (timeout)**: wajar sampai batas tertentu — setiap panggilan tool berarti minimal satu panggilan tambahan ke `llama3.2:3b`, jadi pertanyaan yang butuh tool otomatis lebih lambat dari pertanyaan tanpa tool.
- **Error umum lain** (`no configuration file provided`, `failed to read dockerfile`, port sudah dipakai, dsb.): lihat bagian Troubleshooting `PANDUAN-PRAKTIK.md` module-module sebelumnya (Module 5-14) — penyebab dan solusinya sama, tidak spesifik rangkaian Module 19-23.

---

Untuk informasi lebih lanjut, lihat [materi Module 20](./materi.md) dan [README utama](../README.md).
