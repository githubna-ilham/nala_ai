# Panduan Praktik — Module 16: Reranking dengan Cross-Encoder

## Prasyarat
- Sudah menyelesaikan **Module 15** — `resources/starter-code/day-3/nala/` sudah punya `search_hybrid()` bekerja dan terhubung ke `/chat/stream`
- Docker Desktop dinaikkan alokasi RAM-nya untuk menampung reranker:

| Setting | Minimal | Direkomendasikan | Alasan |
|---|---|---|---|
| **Memory (RAM)** | 16 GB | 20 GB+ jika tersedia | `sentence-transformers` + `torch` dimuat ke memori container `api` sepanjang ia berjalan — bobot model reranker (~80MB untuk default `ms-marco-MiniLM-L-6-v2`) ditambah overhead library `torch` yang cukup besar, di atas beban Ollama + OpenSearch + Airflow yang sudah ada. |
| **CPUs** | 4 | 4+ | Reranking adalah beban CPU tambahan yang nyata — cross-encoder dihitung per pasangan query-dokumen setiap request. |
| **Disk image size** | 100 GB | 120 GB+ | Dependency `torch` (dari `sentence-transformers`) menambah beberapa GB lagi ke image `api`. |

## Langkah 1: Tambah dependency reranker dan volume cache HuggingFace

Ikuti Module 16 Bagian 5 Tahap A Langkah 1-2 di `materi.md`: tambah `sentence-transformers` ke `requirements.txt`, tambah `HF_HOME` dan volume `hf_cache` ke service `api` di `docker-compose.yml`.

```bash
cd resources/starter-code/day-3/nala
docker compose up --build api
```

⚠️ Build ini akan terasa **jauh lebih lama** dari modul sebelumnya — `sentence-transformers` menarik `torch` sebagai dependency, menambah beberapa gigabyte ke image. Ini normal, bukan tanda ada yang salah (lihat Module 16 Bagian 4).

## Langkah 2: Pre-pull model reranker sebelum dipakai

```bash
docker compose exec api python -c "
from sentence_transformers import CrossEncoder
CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
print('Model reranker berhasil diunduh dan siap dipakai offline.')
"
```

✅ **Indikator sukses**: pesan konfirmasi tercetak tanpa error. Perintah ini butuh koneksi internet (mengunduh dari HuggingFace Hub) — begitu selesai sekali, model tersimpan di volume `hf_cache` dan **tidak** diunduh ulang walau container di-*rebuild* (selama volume tidak dihapus).

## Langkah 3: Tulis `app/reranker.py` dan wiring ke `/chat/stream`

Ikuti Module 16 Bagian 5 Tahap A Langkah 3 (buat `app/reranker.py`) dan Tahap B Langkah 4-5 (wiring).

```bash
docker compose up --build api
```

```bash
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Apa saja syarat pengajuan kredit untuk nasabah perorangan?"}]}'
```

✅ **Indikator sukses**: jawaban akurat dan lengkap (8 item, termasuk "maksimal 60 tahun" yang benar — bukan "65 tahun" yang pernah dikarang sebelum grounding aktif), response time terasa jauh lebih lama dibanding Module 15 (~30-40 detik di CPU laptop training — diharapkan, lihat Module 16 Bagian 6). Coba juga matikan sementara reranking untuk membandingkan — buka terminal baru untuk `curl`-nya:

```bash
docker compose stop api
docker compose run --rm -e RERANK_ENABLED=false -p 8000:8000 api
```

Kirim pertanyaan yang sama dari terminal lain — responsnya **tetap muncul** (tidak error), tapi kualitasnya **tidak bisa diprediksi** kali ini: top-3 RRF tanpa reranking sering mengambil chunk yang "terasa berhubungan" tapi bukan yang sebenarnya menjawab, dan `llama3.2:3b` bisa bereaksi dua cara berbeda terhadap konteks yang ambigu seperti itu — kadang jujur mengaku tidak bisa menjawab spesifik (mirip Module 15 Bagian 8), kadang mengisi kekosongan itu dengan detail generik yang masuk akal tapi salah. Coba beberapa kali kalau ingin melihat kedua perilaku ini sendiri (lihat Module 16 Bagian 8 untuk kedua contoh nyata dan penjelasan lengkap kenapa ini terjadi). Setelah selesai membandingkan, `Ctrl+C` dan jalankan ulang `docker compose up --build api` (tanpa override env var) untuk melanjutkan dengan reranking aktif seperti biasa.

## Troubleshooting

- **`ModuleNotFoundError: No module named 'sentence_transformers'`**: `requirements.txt` belum ditambah (Langkah 1) atau image belum di-*rebuild* setelah ditambah — jalankan `docker compose up --build api` (bukan cuma `docker compose up`, perubahan dependency butuh rebuild image).
- **Build `api` terasa sangat lama / seperti macet setelah menambah `sentence-transformers`**: normal — `torch` adalah dependency besar. Tunggu, jangan interupsi build di tengah jalan (image yang setengah jadi bisa korup dan perlu diulang dari awal).
- **`CrossEncoder(...)` gagal/timeout saat dipanggil pertama kali**: kemungkinan besar belum di-*pre-pull* (Langkah 2) dan koneksi internet ruangan lambat/putus saat container mencoba mengunduh otomatis. Jalankan ulang Langkah 2 secara manual dengan koneksi yang stabil.
- **Model reranker diunduh ulang setiap kali `docker compose up --build`**: volume `hf_cache` belum ter-mount dengan benar, atau `HF_HOME` belum di-set — cek `docker-compose.yml` service `api` sesuai Module 16 Bagian 5 Langkah 2.
- **Semua service terasa sangat lambat / laptop panas / container ter-*kill***: alokasi RAM Docker Desktop kurang — lihat bagian Prasyarat di atas, naikkan ke 20GB+ kalau tersedia.
