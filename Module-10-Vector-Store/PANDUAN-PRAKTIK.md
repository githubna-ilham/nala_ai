# Panduan Praktik — Module 10: Vector Store & Semantic Search

## Prasyarat
- Sudah menyelesaikan **Module 9** (Embedding)
- RAM Docker Desktop sudah dinaikkan ke 16GB+ (lihat Module 5 — catatan RAM) sebelum menyalakan OpenSearch di langkah ini

## Langkah 1: Nyalakan OpenSearch, coba `VectorStore`

```bash
docker compose up -d --build opensearch
```

Flag `-d` (detached) supaya tidak perlu buka terminal baru — service ini jalan di background, sementara terminal `ollama`+`api` (Module 5 Langkah 2) tetap seperti semula. **Proses ini akan terasa lama** — OpenSearch butuh waktu untuk inisialisasi cluster single-node. Jangan panik kalau terlihat "diam" beberapa menit.

Pantau log untuk memastikan sudah siap:

```bash
docker compose logs -f opensearch
```

Tunggu sampai muncul log yang menyebutkan cluster health `green` atau `yellow` (bukan `red`), lalu `Ctrl+C` untuk keluar dari `logs -f` (service tetap jalan di background).

Rebuild `api` supaya `OPENSEARCH_BASE_URL` (env var baru dari module ini) ter-load:

```bash
docker compose up --build -d api
```

```bash
docker compose exec api python -c "
from app.embeddings import embed_text
from app.vector_store import VectorStore

store = VectorStore(base_url='http://opensearch:9200', index_name='nala-docs')
store.ensure_index()

vec = embed_text('Kantor cabang Surabaya buka Senin-Jumat', base_url='http://ollama:11434')
store.index_document(doc_id='test-1', text='Kantor cabang Surabaya buka Senin-Jumat', embedding=vec, metadata={'source': 'test'})

query_vec = embed_text('kapan cabang Surabaya beroperasi', base_url='http://ollama:11434')
results = store.search(query_vec, top_k=3)
print(results)
"
```

Harus tidak ada error, dan `results` menampilkan dokumen yang baru di-index **seketika** (`index_document()` minta OpenSearch refresh segera lewat `params={"refresh": "true"}` — tanpa ini, `search()` yang dipanggil langsung setelah `index_document()` bisa saja kembali kosong `[]` karena index belum sempat ter-refresh) walau kata-kata query berbeda dari kata-kata dokumen — bukti pencarian semantik bekerja. Lihat Module 10 Bagian 3 untuk penjelasan apa itu OpenSearch, Bagian 5 untuk penjelasan detail metrik kemiripan (cosine, L2, dot product) di balik pencarian ini, dan Bagian 6 untuk penjelasan tiap method `VectorStore`.

## Troubleshooting

- **OpenSearch gagal start / restart terus / error terkait `vm.max_map_count`**: OpenSearch butuh `vm.max_map_count` minimal 262144 di level OS host, sementara default macOS/Windows (lewat Docker Desktop VM) sering lebih rendah. Perbaiki dengan menjalankan (sekali saja, akan reset lagi setelah restart Docker Desktop/laptop):
  ```bash
  docker run --rm --privileged --pid=host alpine sysctl -w vm.max_map_count=262144
  ```
  Setelah itu jalankan ulang `docker compose up -d --build opensearch` (Langkah 1). Error yang sama juga bisa muncul saat menyalakan `airflow` (Module 14) — perbaikannya identik.
- **Semua service terasa sangat lambat / laptop panas / container ter-*kill***: kemungkinan besar alokasi RAM Docker Desktop kurang — lihat Prasyarat di atas dan catatan RAM di Module 5. Cek pemakaian resource real-time dengan `docker stats`.
- **Port sudah dipakai (8000/9200/11434)**: ubah mapping port di `docker-compose.yml` untuk service yang bentrok.
