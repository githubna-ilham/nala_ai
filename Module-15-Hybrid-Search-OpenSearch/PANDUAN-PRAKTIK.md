# Panduan Praktik — Module 15: Hybrid Search (BM25 + Vector) via OpenSearch

### Catatan penting sebelum mulai

`resources/starter-code/day-3/nala/` **belum ada** di titik materi ini ditulis — akan dibangun secara manual oleh peserta mengikuti panduan ini, sama seperti situasi Module 4 `PANDUAN-PRAKTIK.md` yang ditulis sebelum starter code project ini sendiri ada. Perintah-perintah di bawah ini mendeskripsikan **apa yang akan dijalankan** peserta setelah folder tersebut dibangun — bukan hasil verifikasi terhadap sistem yang sudah berjalan. Kalau ada perintah yang tidak berjalan persis seperti yang tertulis begitu Anda benar-benar menjalankannya, cocokkan dulu dengan kode lengkap ("📄 Kode lengkap") di `materi.md` — itu sumber kebenaran yang lebih rinci dari sekadar cuplikan perintah di sini.

Titik awal `resources/starter-code/day-3/nala/` adalah **salinan lengkap `resources/starter-code/day-2/nala/`** — folder kerja Anda sendiri (bukan folder reference), lengkap dengan kustomisasi yang sudah Anda buat sepanjang Module 5-14 (misal isi `NALA_SYSTEM_PROMPT` versi Anda sendiri, penyesuaian `top_k`):

```bash
cp -r resources/starter-code/day-2/nala resources/starter-code/day-3/nala
```

Berbeda dari modul-modul sebelumnya yang punya dua folder kode (kerja bertahap + reference frozen), Module 15 dan seterusnya (sampai Module 18) **hanya** punya satu folder (`resources/starter-code/day-3/nala/`) — dibangun langsung di situ, module demi module, memakai kode lengkap di tiap `materi.md` sebagai rujukan kalau ingin membandingkan hasil.

## Prasyarat
- Sudah menyelesaikan **Module 14** (`resources/starter-code/day-2/nala/` berjalan lengkap: chat UI, streaming/multi-turn, upload, embedding/vector store, chunking, Airflow, RAG chain)
- Docker Desktop sudah dialokasikan resource yang cukup — minimal 16GB RAM (sama seperti kebutuhan sejak Module 10-14); module ini sendiri tidak menambah service Docker baru, jadi belum perlu menaikkan alokasi lagi

### Container Module 5-14 tetap dipakai — bukan project terpisah

Karena nama folder `day-2/nala/` dan `day-3/nala/` sama-sama `nala`, Docker Compose (yang memakai **nama folder**, bukan path lengkap, sebagai *project name* secara default) memperlakukan keduanya sebagai **project yang sama**. Ini **disengaja**, bukan kebetulan yang perlu dihindari: kalau tiap folder starter code punya project Docker terpisah, `ollama`, `opensearch`, `airflow` dkk akan berjalan **duplikat** — RAM yang dipakai membengkak drastis. Dengan project yang sama, `day-3/nala/docker-compose.yml` cukup **mengambil alih** container yang sama yang sudah berjalan sejak Module 5-14 — data (index OpenSearch yang sudah terisi dari ingest sebelumnya, model Ollama yang sudah di-pull) otomatis ikut terbawa, tidak perlu diulang dari nol.

Konsekuensi praktis: setelah ini, jalankan `docker compose` **dari folder `day-3/nala/`**, bukan lagi `day-2/nala/` — begitu `day-3/nala/docker-compose.yml` dipakai sekali, ia menjadi definisi aktif untuk project `nala` sampai Anda kembali menjalankan compose dari folder lama (yang akan mengambilnya alih lagi, sama-sama valid, cuma tidak disarankan dicampur berulang-ulang tanpa alasan jelas — pilih satu folder aktif per sesi kerja).

## Langkah 1: Masuk ke folder starter code, mulai service yang sudah ada sejak Module 5-14

```bash
cd resources/starter-code/day-3/nala
docker compose up --build ollama opensearch api
```

Tiga service ini sudah pernah dijalankan sebelumnya — kalau model `llama3.2:3b` dan `nomic-embed-text` sudah pernah di-*pull* ke volume `ollama_data` sebelumnya, tidak perlu di-*pull* ulang (volume Docker persisten, selama tidak dihapus). Verifikasi:

```bash
docker compose exec ollama ollama list
```

Kalau `llama3.2:3b` dan `nomic-embed-text` sudah muncul, lanjut ke Langkah 2. Kalau belum, ulangi `docker compose exec ollama ollama pull <nama-model>` untuk masing-masing (lihat Module 2 `PANDUAN-PRAKTIK.md` dan Module 9 `materi.md` untuk detail model yang dipakai).

Pastikan juga index `nala-docs` di OpenSearch masih terisi dari ingest sebelumnya:

```bash
curl http://localhost:9200/nala-docs/_count
```

Kalau `count` bernilai `0` (index kosong, misalnya karena volume `opensearch_data` baru), jalankan ulang ingest:

```bash
docker compose exec api python -c "from app.ingest import ingest_documents; print(ingest_documents('/app/knowledge-base'))"
```

## Langkah 2: Bandingkan `search()` vs `search_hybrid()` sebelum menulis kode

Sebelum menulis `search_bm25()`/`search_hybrid()`, coba dulu query yang sama lewat `search()` murni (vector, sudah ada sejak Module 10) untuk melihat baseline yang akan dibandingkan:

```bash
docker compose exec api python -c "
from app.embeddings import embed_text
from app.vector_store import VectorStore

store = VectorStore(base_url='http://opensearch:9200', index_name='nala-docs')
query = 'Apa saja syarat pengajuan kredit untuk nasabah perorangan?'
query_embedding = embed_text(query, base_url='http://ollama:11434')

results = store.search(query_embedding, top_k=10)
for i, r in enumerate(results):
    print(i, round(r['score'], 4), '-', r['text'][:70])
"
```

Catat di posisi keberapa chunk `### 2.1 Untuk Nasabah Perorangan` muncul (kalau muncul sama sekali di top-10) — ini baseline yang akan dibandingkan setelah Langkah 3-4.

## Langkah 3: Tulis `search_bm25()` dan `search_hybrid()`

Ikuti Module 15 Bagian 6 Tahap A Langkah 1-3 di `materi.md` untuk menambah `_id` ke `search()`, lalu method baru `search_bm25()` dan `search_hybrid()` di `app/vector_store.py`.

```bash
docker compose up --build api
```

```bash
docker compose exec api python -c "
from app.embeddings import embed_text
from app.vector_store import VectorStore

store = VectorStore(base_url='http://opensearch:9200', index_name='nala-docs')
query = 'Apa saja syarat pengajuan kredit untuk nasabah perorangan?'
query_embedding = embed_text(query, base_url='http://ollama:11434')

results = store.search_hybrid(query, query_embedding, top_k=10, candidate_pool=20)
for i, r in enumerate(results):
    print(i, round(r['rrf_score'], 4), '-', r['text'][:70])
"
```

✅ **Indikator sukses**: bandingkan posisi chunk `### 2.1` di sini dengan catatan Langkah 2 — seharusnya naik ke posisi yang lebih tinggi (idealnya masuk top-5).

## Langkah 4: Wiring hybrid search ke `/chat/stream`

Ikuti Module 15 Bagian 6 Tahap B Langkah 4.

```bash
docker compose up --build api
```

```bash
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Apa saja syarat pengajuan kredit untuk nasabah perorangan?"}]}'
```

✅ **Indikator sukses**: jawaban terasa lebih relevan dibanding sebelumnya (menyebut konteks yang lebih tepat sasaran), tapi untuk pertanyaan spesifik ini **belum tentu** sudah menyebut item konkret (KTP, Kartu Keluarga, slip gaji, NPWP) — hybrid search terbukti meningkatkan peringkat chunk yang benar (dari #10-14 di vector murni jadi sekitar #8), tapi belum cukup untuk masuk `top_k=3` di kasus keras ini (lihat data lengkap di Module 15 Bagian 8). Kalau jawabannya masih bilang "tidak ditemukan informasi spesifik", itu **bukan tanda ada yang salah** — itu justru bukti grounding masih bekerja jujur (Module 11 Bagian 2.d), dan alasan kenapa Module 16 (reranking) berikutnya diperlukan. Lihat Module 15 Bagian 7 untuk checklist lengkap sebelum lanjut ke Module 16.

## Troubleshooting

- **`search_hybrid()` melempar error field `text` tidak ditemukan / query `match` gagal**: index `nala-docs` yang dipakai kemungkinan dibuat sebelum field `text` ada di mapping (versi index yang sangat lama) — hapus dan buat ulang index (`curl -X DELETE http://localhost:9200/nala-docs`) lalu jalankan ulang `ingest_documents()` (lihat Langkah 1).
- **Port sudah dipakai (8000/9200/11434)**: ubah mapping port yang bentrok di `docker-compose.yml`, atau pastikan container lama sudah benar-benar dimatikan (`docker compose down` di `resources/starter-code/day-2/nala`).
- **`docker compose exec ollama ollama list` tidak menampilkan model**: model belum pernah di-pull ke volume container ini — jalankan ulang `docker compose exec ollama ollama pull <nama-model>` (lihat Langkah 1).
