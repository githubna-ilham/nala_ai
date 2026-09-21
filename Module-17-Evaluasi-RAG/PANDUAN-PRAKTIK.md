# Panduan Praktik — Module 17: Framework Evaluasi RAG

## Prasyarat
- Sudah menyelesaikan **Module 16** — `resources/starter-code/day-3/nala/` sudah punya reranking bekerja dan terhubung ke `/chat/stream`
- Tidak ada service Docker baru di module ini — alokasi RAM yang sama seperti Module 16 sudah cukup

## Langkah 1: Bangun `app/evaluation.py`, test set, dan skrip perbandingan

Ikuti Module 17 Bagian 5 Langkah 1-3: `app/evaluation.py` (fungsi metrik), `app/eval_testset.py` (10 pertanyaan berlabel), `app/run_evaluation.py` (skrip perbandingan).

```bash
cd resources/starter-code/day-3/nala
docker compose up --build api
```

Tes dulu fungsi metrik dengan data dummy (lihat Module 17 Bagian 5 Langkah 1 untuk perintah lengkap), lalu jalankan evaluasi penuh:

```bash
docker compose exec api python -m app.run_evaluation
```

✅ **Indikator sukses**: tabel perbandingan "SEBELUM Reranking" vs "SESUDAH Reranking" tercetak dengan Precision@3, Hit Rate@3, dan MRR untuk masing-masing, diikuti delta. Lihat Module 17 Bagian 7 untuk kenapa index kecil (2 dokumen) bisa membuat hasilnya terlihat kurang dramatis — ini keterbatasan yang jujur, bukan bug.

## Langkah 2: Coba LLM-as-judge lokal

```bash
docker compose exec api python -c "
from app.llm_judge import judge_answer
from app.ollama_client import OllamaClient
import os

judge_client = OllamaClient(base_url='http://ollama:11434', model=os.environ.get('OLLAMA_MODEL', 'llama3.2:3b'))

context = 'Fotokopi KTP yang masih berlaku, Fotokopi Kartu Keluarga, Slip gaji 3 bulan terakhir'
question = 'Apa saja syarat pengajuan kredit untuk nasabah perorangan?'
answer = 'Syaratnya adalah fotokopi KTP, Kartu Keluarga, dan slip gaji 3 bulan terakhir.'

result = judge_answer(judge_client, context, question, answer)
print(result)
"
```

✅ **Indikator sukses**: output berisi `faithfulness` dan `relevance` bernilai 1-5 (bukan `None` — kalau `None`, model tidak mengikuti format yang diminta, coba lagi atau baca `result['raw']` untuk melihat output mentahnya). Baca manual apakah skornya masuk akal untuk contoh ini — idealnya faithfulness dan relevance tinggi (4-5), karena `answer` memang murni berasal dari `context`.

## Troubleshooting

- **`docker compose exec api python -m app.run_evaluation` gagal dengan import error**: pastikan `app/evaluation.py`, `app/eval_testset.py`, dan `app/run_evaluation.py` sudah dibuat sesuai Langkah 1, dan `docker compose up --build api` sudah dijalankan ulang setelah menambah file baru.
- **`judge_answer()` selalu mengembalikan `None` untuk `faithfulness`/`relevance`**: `llama3.2:3b` kadang tidak mengikuti format output yang diminta secara persis — cek `result['raw']` untuk melihat apa yang sebenarnya dikembalikan model, dan coba jalankan ulang (model kecil tidak selalu konsisten di percobaan pertama).
