# Panduan Praktik — Module 14: Airflow Ingest Pipeline

## Prasyarat
- Sudah menyelesaikan **Module 13** (Upload Dokumen)
- RAM Docker Desktop di 16GB+ (lihat Module 5 — catatan RAM) — di langkah ini keempat service (`ollama`, `opensearch`, `airflow`, `api`) akan jalan bersamaan untuk pertama kalinya

## Langkah 1: Nyalakan Airflow, trigger DAG

```bash
docker compose up -d --build airflow
```

**Proses ini akan terasa lama** — Airflow `standalone` perlu inisialisasi database metadata + membuat user admin sebelum webserver-nya siap.

```bash
docker compose logs -f airflow
```

Tunggu sampai muncul baris log yang mengandung kata `password` (ini password admin, simpan) serta indikasi webserver sudah listen di port 8080, lalu `Ctrl+C` untuk keluar dari `logs -f`.

Sekarang trigger DAG `ingest_documents` — fungsi yang sama persis dengan yang dipanggil manual di Module 11-12 dan lewat form upload di Module 13, dipicu lewat Airflow sebagai cara **lain**. Ada dua cara — pilih salah satu.

### Opsi A: Lewat Airflow UI (menunjukkan orchestration ala produksi)

1. Buka `http://localhost:8080` di browser.
2. Login dengan username `admin` dan password yang tercetak di log container `airflow` saat startup (atau cari lagi dengan cara di bagian Troubleshooting).
3. Cari DAG bernama **`ingest_documents`**, aktifkan toggle-nya (kalau masih off), lalu klik tombol **Trigger DAG** (ikon ▶️).
4. Tunggu task `ingest_documents` selesai (status berubah jadi hijau/`success`). Cek log task untuk melihat jumlah chunk yang ter-index.

### Opsi B: Lewat CLI

```bash
docker compose exec airflow airflow dags trigger ingest_documents
```

Memonitor dari CLI:

```bash
docker compose exec airflow airflow dags list-runs --dag-id ingest_documents
```

Verifikasi akhir — coba tanyakan sesuatu ke `/chat/stream` yang jawabannya ada di dokumen yang baru saja di-trigger-ulang lewat Airflow, **tanpa mengubah satu baris pun kode `/chat/stream`**. Ini bukti nyata bahwa retrieval generik terhadap sumber data — tidak peduli dokumen masuk lewat CLI manual (Module 11-12), form upload (Module 13), atau Airflow (langkah ini), `/chat/stream` selalu membaca index `nala-docs` yang sama.

## Yang Perlu Dipastikan Sebelum Module 14 Dianggap Selesai

- [ ] `docker compose up -d --build airflow` berhasil, webserver Airflow bisa diakses di `http://localhost:8080`
- [ ] DAG `ingest_documents` muncul dan bisa di-trigger (Opsi A atau B)
- [ ] Task DAG selesai dengan status `success`, log menunjukkan jumlah chunk yang ter-index
- [ ] `/chat/stream` bisa menjawab dari dokumen yang baru di-ingest ulang lewat Airflow, tanpa mengubah kode `/chat/stream`
- [ ] Keempat service (`ollama`, `opensearch`, `airflow`, `api`) berjalan bersamaan tanpa container ter-*kill*

Begitu kelima hal ini terverifikasi, Module 14 selesai — NALA sudah punya RAG chain lengkap dari dokumen mentah sampai jawaban ber-konteks, dengan **tiga** cara data bisa masuk (seed manual, upload web, Airflow), semuanya bermuara ke fungsi `ingest_documents()` yang sama.

## Troubleshooting

- **OpenSearch/Airflow gagal start / restart terus / error terkait `vm.max_map_count`**: butuh `vm.max_map_count` minimal 262144 di level OS host. Perbaiki dengan (sekali saja, reset lagi setelah restart Docker Desktop/laptop):
  ```bash
  docker run --rm --privileged --pid=host alpine sysctl -w vm.max_map_count=262144
  ```
  Setelah itu jalankan ulang `docker compose up -d --build airflow` (Langkah 1).
- **Lupa/tidak sempat mencatat password admin Airflow**: cari lagi di log container:
  ```bash
  docker compose logs airflow | grep -i password
  ```
  Kalau tidak muncul apa-apa, password biasa tersimpan di file `standalone_admin_password.txt` di dalam `AIRFLOW_HOME` — bisa juga dicek dengan `docker compose exec airflow cat /opt/airflow/standalone_admin_password.txt`.
- **DAG `ingest_documents` tidak muncul di Airflow UI**: tunggu sebentar — Airflow scan folder DAGs secara berkala, bukan instan. Kalau setelah 1-2 menit masih tidak muncul, cek log container `airflow` untuk error parsing DAG (`docker compose logs airflow`).
- **Semua service terasa sangat lambat / laptop panas / container ter-*kill***: kemungkinan besar alokasi RAM Docker Desktop kurang — lihat catatan RAM di Module 5 dan naikkan ke 16GB+. Cek pemakaian resource real-time dengan `docker stats`.
- **Port sudah dipakai (8000/8080/9200/11434)**: ubah mapping port di `docker-compose.yml` untuk service yang bentrok (misal `8081:8080` untuk Airflow).
