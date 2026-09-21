# Panduan Praktik — Module 9: Embedding

## Prasyarat
- Sudah menyelesaikan **Module 8** (Setup Knowledge Base & Data Dasar Awal)
- Container `ollama`+`api` masih berjalan — module ini belum butuh `opensearch`/`airflow`

## Langkah 1: Pull model `nomic-embed-text`, coba `embed_text()`

Belum butuh OpenSearch di langkah ini — cukup model embedding-nya dulu:

```bash
docker compose exec ollama ollama pull nomic-embed-text
```

`nomic-embed-text` tidak pakai tag, sesuai default parameter `model` di `app/embeddings.py`. Verifikasi kedua model (chat + embedding) sudah ada:

```bash
docker compose exec ollama ollama list
```

`llama3.2:3b` dan `nomic-embed-text` harus muncul berdua di daftar.

```bash
docker compose exec api python -c "
from app.embeddings import embed_text
vec = embed_text('Kantor cabang Surabaya buka Senin-Jumat', base_url='http://ollama:11434')
print(f'Dimensi: {len(vec)}')
print(f'Contoh nilai: {vec[:3]}')
"
```

Harus mengembalikan `Dimensi: 768`, dan mengembalikan vektor yang **sama persis** kalau dijalankan berulang kali dengan teks yang sama (embedding tidak punya elemen acak, beda dengan `generate()`). Lihat Module 9 Bagian 4 untuk penjelasan lengkap.

## Troubleshooting

- **`Internal Server Error` saat memanggil `embed_text()` atau saat ingest**: cek dulu model mana yang belum ter-pull (`docker compose exec ollama ollama list`) — module ini butuh dua model sekaligus: `llama3.2:3b` (dari Module 5) dan `nomic-embed-text` (Langkah 1 di atas). Kalau salah satu tidak muncul, ulangi langkah pull yang sesuai.
