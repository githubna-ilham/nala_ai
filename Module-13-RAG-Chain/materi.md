# Module 13: RAG Chain v1 — RAG Mulai "Hidup"

## Tujuan

Menyatukan tiga potongan yang sudah dibangun (`extract_text()` Module 10, `embed_text()` Module 11, `VectorStore` Module 12) jadi satu fungsi `ingest_documents()` **versi pertama** — belum ada chunking, satu dokumen di-embed jadi **satu vektor utuh**. Memakainya untuk mengisi index dengan **data seed** (Bagian 2), lalu menyambungkan `/chat/stream` — satu-satunya endpoint chat NALA sejak Module 8 — ke retrieval. Ini titik paling penting Module 7-16 sejauh ini: **RAG benar-benar bekerja untuk pertama kalinya** — NALA menjawab dari dokumen sungguhan, bukan lagi generik. Chunking (Module 14) akan meng-upgrade `ingest_documents()` ini nanti — bukan menggantinya dari nol.

## Definisi

`ingest_documents()` adalah fungsi yang menyatukan seluruh pipeline — baca dokumen, embed, simpan ke vector store — jadi satu pemanggilan. "Ingest" sendiri berarti "memasukkan data ke dalam sistem" (Bagian 1), dan begitu fungsi ini tersambung ke endpoint chat, terbentuklah **RAG chain**: rangkaian lengkap retrieval → augmented → generation yang benar-benar tersambung end-to-end, dari pertanyaan user sampai jawaban ber-konteks — inilah yang "hidup" untuk pertama kalinya di module ini (lihat Module 9 Bagian 4 untuk alur konsepnya).

Supaya jawaban yang dihasilkan benar-benar berdasarkan dokumen (bukan mengarang), dipakai **grounding** — instruksi eksplisit ke LLM supaya menjawab hanya dari konteks yang diberikan, bukan dari pengetahuan umum model (Bagian 4). Tapi grounding cuma berguna kalau ada konteks untuk dijadikan pegangan — kalau retrieval gagal atau tidak menemukan apa-apa, sistem butuh **fallback**: jalur cadangan yang tetap memberi jawaban yang jujur. Di NALA, `NALA_SYSTEM_PROMPT_NO_CONTEXT` dipakai sebagai fallback itu (Bagian 2 Langkah 3).

```mermaid
flowchart LR
    U["Pertanyaan user"] --> E["embed_text()"]
    E --> S["vector_store.search()"]
    S -->|"ada hasil"| G["Grounding:<br/>NALA_SYSTEM_PROMPT"]
    S -->|"kosong/gagal"| F["Fallback:<br/>NALA_SYSTEM_PROMPT_NO_CONTEXT"]
    G --> J["Jawaban ber-konteks"]
    F --> J2["Jawaban generik, jujur"]
```

## Hasil Akhir yang Diharapkan

- `ingest_documents()` menyatukan `extract_text()` + embedding + vector store, mengembalikan jumlah dokumen yang ter-index (satu vektor per dokumen)
- Index OpenSearch terisi dari data seed (Bagian 2) lewat pemanggilan manual satu kali
- `/chat/stream` menjawab berdasarkan isi dokumen SOP yang ter-index, bukan generik lagi, untuk pertanyaan yang jawabannya ada di knowledge base
- Multi-turn (Module 8) tetap berfungsi setelah retrieval ditambahkan — pertanyaan lanjutan tanpa kata kunci eksplisit tetap dipahami dan tetap memicu retrieval baru
- Index kosong/OpenSearch tak terjangkau menghasilkan fallback ke `NALA_SYSTEM_PROMPT_NO_CONTEXT` (jawaban tetap mengalir normal, bukan error)
- Kita memahami keterbatasan nyata retrieval **level-dokumen** (Bagian 7) sebagai motivasi jujur untuk chunking di Module 14 — bukan diklaim sebagai retrieval yang sudah optimal

## 1. Menyatukan Tiga Potongan: `ingest_documents()` v1

**Prasyarat**: sudah menyelesaikan **Module 12** (Vector Store & Semantic Search) — `opensearch` sudah menyala dan sehat.

Module 10-12 membangun tiga alat terpisah: `extract_text()` (Module 10), `embed_text()` (Module 11), dan `VectorStore` (Module 12). Sekarang saatnya menyatukan ketiganya jadi satu fungsi — `ingest_documents()`, yang menerima path folder dan mengembalikan jumlah dokumen yang ter-index.

⚠️ **Belum ada chunking di versi ini**: tiap dokumen dibaca `extract_text()` **secara utuh**, langsung di-embed **secara utuh** jadi satu vektor, lalu disimpan sebagai **satu entri** di OpenSearch (`doc_id` = nama file apa adanya, bukan `filename-0`, `filename-1`, dst). Ini sengaja — versi pertama RAG dibuat sesederhana mungkin supaya cepat terbukti bekerja. Bagian 7 di bawah akan menunjukkan keterbatasan nyata dari pendekatan ini, yang jadi alasan konkret Module 14 menambahkan chunking.

**Langkah 1 — Tambah `ingest_documents()` di `app/ingest.py`**

`app/ingest.py` sejak Module 10 berisi `extract_text()`. Tambahkan import dan konstanta baru di baris paling atas:

```python
# app/ingest.py
import os

from pypdf import PdfReader

from app.embeddings import embed_text
from app.vector_store import VectorStore

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OPENSEARCH_BASE_URL = os.environ.get("OPENSEARCH_BASE_URL", "http://localhost:9200")
```

Lalu tambahkan fungsi baru di akhir file:

```python
# app/ingest.py, di bawah extract_text()
def ingest_documents(folder_path: str) -> int:
    store = VectorStore(base_url=OPENSEARCH_BASE_URL, index_name="nala-docs")
    store.ensure_index()

    total_documents = 0
    for filename in sorted(os.listdir(folder_path)):
        if not filename.endswith((".md", ".txt", ".pdf")):
            continue
        content = extract_text(os.path.join(folder_path, filename))
        embedding = embed_text(content, base_url=OLLAMA_BASE_URL)
        store.index_document(
            doc_id=filename,
            text=content,
            embedding=embedding,
            metadata={"source": filename},
        )
        total_documents += 1

    return total_documents
```

Fungsi ini: memastikan index OpenSearch sudah ada (`ensure_index()`), scan semua file `.md`/`.txt`/`.pdf` di folder tersebut (urut alfabetis), baca isinya jadi string utuh (`extract_text`, Module 10), embed **seluruh isi dokumen sekaligus** (`embed_text`, Module 11), lalu index-kan satu entri per dokumen ke OpenSearch (`store.index_document`, Module 12) dengan `doc_id` = nama filenya sendiri. Inilah titik di mana ketiga potongan (ekstraksi teks, embedding, vector store) akhirnya bertemu di satu file — versi paling sederhana yang mungkin.

> **📝 Catatan penting — semua dokumen di-embed ulang, bukan cuma yang baru**: `ingest_documents()` **tidak** membedakan dokumen lama vs baru — setiap kali dipanggil, fungsi ini scan ulang **seluruh isi folder**, lalu embed ulang semuanya dari nol. **Kenapa ini tidak menyebabkan duplikat**: `doc_id=filename` bersifat deterministik — dokumen yang sama selalu punya ID yang sama, jadi `index_document()` **menimpa** (overwrite), bukan menambah entri baru — idempotent, aman dijalankan berkali-kali. **Tapi ini boros**: makin banyak dokumen lama, makin banyak panggilan Ollama yang tidak perlu tiap kali di-ingest ulang. Di production nyata, biasanya ditambah pengecekan `mtime`/hash file untuk skip dokumen yang tidak berubah — di luar cakupan training ini, demi kesederhanaan belajar konsep.

**▶️ Jalankan & lihat hasilnya**

```bash
docker compose up --build api
```

```bash
docker compose exec api python -c "from app.ingest import ingest_documents; print(ingest_documents('/app/knowledge-base'))"
```

✅ **Indikator sukses**: mengembalikan angka sesuai jumlah dokumen `.md`/`.txt`/`.pdf` di `resources/sample-knowledge-base/` (lihat Module 10 Bagian 2) — kalau ada 2 SOP contoh plus beberapa PDF latihan, angkanya sejumlah itu. Verifikasi lewat OpenSearch langsung:

```bash
curl "http://localhost:9200/nala-docs/_count"
```

harus menunjukkan angka yang sama.

> 🔧 **Troubleshooting — chat menjawab generik / bilang belum ada dokumen internal padahal sudah ingest**: `/chat/stream` (Bagian 2) otomatis jatuh ke mode tanpa-konteks saat index OpenSearch masih kosong (atau belum menyala) — itu normal, bukan error, tapi tandanya ingest belum berhasil. Cek lagi `curl http://localhost:9200/nala-docs/_count` — kalau `count` bernilai 0, index memang kosong, jalankan ulang Langkah 1 ini.

> **📝 Catatan — beda dengan Module 14 nanti**: angka yang dikembalikan di sini adalah jumlah **dokumen**, bukan jumlah chunk — karena belum ada chunking. Setelah Module 14 meng-upgrade `ingest_documents()` untuk memecah tiap dokumen jadi beberapa chunk dulu sebelum di-embed, angka yang sama akan jauh lebih besar (satu dokumen bisa jadi 8-13 chunk, tergantung strategi chunking-nya) — perbandingan langsung ini jadi bukti konkret kenapa chunking penting, bukan cuma teori.

**Ini juga langkah "data dasar awal" yang dijanjikan Module 10 Bagian 1** — index sekarang terisi dari data seed, tanpa perlu form upload apa pun (itu baru Module 15). Kita sudah bisa lanjut ke Bagian 3 di bawah dan melihat RAG bekerja.

<details>
<summary><strong>Pakai Claude Code? Salin prompt berikut, paste untuk eksekusi Langkah 1</strong></summary>

```
Tambah ingest_documents() v1 ke app/ingest.py yang sudah ada
(Module 13) — menyatukan extract_text() (Module 10) dengan embed_text()
(Module 11) dan VectorStore (Module 12). BELUM ADA CHUNKING.

GOAL:
- Di Nala/app/ingest.py (saat ini berisi
  extract_text(), plus import `from pypdf import PdfReader`):
  - Tambah di baris PALING ATAS file: `import os`, `from
    app.embeddings import embed_text`, `from app.vector_store import
    VectorStore`, lalu dua konstanta OLLAMA_BASE_URL dan
    OPENSEARCH_BASE_URL masing-masing dari os.environ.get(...) dengan
    default http://localhost:11434 dan http://localhost:9200.
  - Tambah fungsi baru ingest_documents(folder_path: str) -> int di
    BAWAH extract_text() (jangan ubah extract_text() yang sudah ada):
    bikin VectorStore(base_url=OPENSEARCH_BASE_URL,
    index_name="nala-docs"), panggil store.ensure_index(), lalu untuk
    tiap file .md/.txt/.pdf di folder_path (urut alfabetis), panggil
    extract_text() untuk dapat isinya UTUH (bukan dipecah), embed_text()
    isinya sekaligus, lalu
    store.index_document(doc_id=filename, text=content,
    embedding=embedding, metadata={"source": filename}). Return total
    jumlah DOKUMEN (bukan chunk) yang ter-index.

CONTEXT:
- app/embeddings.py (Module 11) dan app/vector_store.py (Module 12)
  sudah ada dan tidak perlu diubah.
- BELUM ADA chunking di versi ini — satu dokumen = satu vektor. Itu
  baru ditambahkan Module 14.

GUARDRAIL:
- JANGAN ubah extract_text() yang sudah ada.
- JANGAN tambah fungsi chunk_text()/chunk_markdown() di file ini —
  itu Module 14.
- JANGAN sentuh app/main.py, docker-compose.yml, atau requirements.txt
  di langkah ini.
```

</details>

## 2. Sambungkan Retrieval ke `/chat/stream`

Sekarang index sudah terisi (Bagian 1) — saatnya membuat `/chat/stream` benar-benar **membaca** dari index itu sebelum menjawab. `/chat/stream` adalah **satu-satunya** endpoint chat sejak Module 8 (`/chat` sudah dihapus total) — jadi retrieval cukup ditambahkan di satu tempat, tidak ada endpoint kedua yang perlu disinkronkan. Dua Langkah: **Langkah 2** menyiapkan fondasi (prompt fallback + import + koneksi `VectorStore`), **Langkah 3** mengubah `/chat/stream` itu sendiri.

**Langkah 2 — Tambah `NALA_SYSTEM_PROMPT_NO_CONTEXT` dan setup `VectorStore` di `main.py`**

Di `app/system_prompt.py` (byte-identical dari Module 1-6 sejak Module 7) cuma ada `NALA_SYSTEM_PROMPT`. Tambahkan satu konstanta baru di baris paling bawah:

```python
# app/system_prompt.py
NALA_SYSTEM_PROMPT_NO_CONTEXT = """Kamu adalah NALA, asisten AI internal PT Nusantara Finance.
Tugasmu adalah menjawab pertanyaan staff seputar SOP, kebijakan, dan data operasional perusahaan.
Aturan:
- Jawab singkat, jelas, dan dalam Bahasa Indonesia.
- Jika kamu tidak yakin atau informasinya tidak tersedia, katakan dengan jujur bahwa kamu tidak memiliki informasi tersebut. Jangan mengarang jawaban.
- Jangan menjawab pertanyaan di luar konteks pekerjaan PT Nusantara Finance.
- Belum ada dokumen internal yang terhubung ke kamu saat ini, jadi jawab berdasarkan pengetahuan umum saja dan sebutkan bahwa jawaban akan lebih akurat setelah dokumen SOP diunggah.
"""
```

Lalu di `app/main.py`, tambah import dan setup baru — di baris atas:

```python
# app/main.py
from app.embeddings import embed_text
from app.system_prompt import NALA_SYSTEM_PROMPT, NALA_SYSTEM_PROMPT_NO_CONTEXT
from app.vector_store import VectorStore
```

`from app.system_prompt import NALA_SYSTEM_PROMPT` (yang sudah ada sejak Module 7) diganti jadi baris di atas.

Lalu tambah konstanta dan instance `VectorStore` baru, di dekat `KNOWLEDGE_BASE_PATH`:

```python
# app/main.py
OPENSEARCH_BASE_URL = os.environ.get("OPENSEARCH_BASE_URL", "http://localhost:9200")
vector_store = VectorStore(base_url=OPENSEARCH_BASE_URL, index_name="nala-docs")
```

Belum ada satu baris pun endpoint yang berubah di Langkah ini — cuma menyiapkan alat yang akan dipakai Langkah 3.

**▶️ Jalankan & lihat hasilnya**

```bash
docker compose up --build api
```

✅ **Indikator sukses**: log `api` tetap menunjukkan `Uvicorn running` tanpa traceback, dan `/chat/stream` masih menjawab generik seperti sebelumnya — belum ada yang berubah secara fungsional.

<details>
<summary><strong>Pakai Claude Code? Salin prompt berikut, paste untuk eksekusi Langkah 2</strong></summary>

```
Tambah NALA_SYSTEM_PROMPT_NO_CONTEXT dan setup VectorStore di main.py
(Module 13, Langkah 2) — fondasi untuk retrieval, belum mengubah
endpoint apa pun.

GOAL:
- Di Nala/app/system_prompt.py: tambah
  konstanta baru NALA_SYSTEM_PROMPT_NO_CONTEXT (string multi-baris)
  di bawah NALA_SYSTEM_PROMPT yang sudah ada — isinya sama persis
  dengan NALA_SYSTEM_PROMPT kecuali aturan terakhir diganti jadi:
  "Belum ada dokumen internal yang terhubung ke kamu saat ini, jadi
  jawab berdasarkan pengetahuan umum saja dan sebutkan bahwa jawaban
  akan lebih akurat setelah dokumen SOP diunggah."
- Di Nala/app/main.py:
  - Ganti `from app.system_prompt import NALA_SYSTEM_PROMPT` jadi
    `from app.system_prompt import NALA_SYSTEM_PROMPT,
    NALA_SYSTEM_PROMPT_NO_CONTEXT`.
  - Tambah `from app.embeddings import embed_text` dan `from
    app.vector_store import VectorStore`.
  - Tambah konstanta OPENSEARCH_BASE_URL =
    os.environ.get("OPENSEARCH_BASE_URL", "http://localhost:9200")
    dan `vector_store = VectorStore(base_url=OPENSEARCH_BASE_URL,
    index_name="nala-docs")`, ditaruh dekat KNOWLEDGE_BASE_PATH.

CONTEXT:
- app/embeddings.py dan app/vector_store.py sudah ada dari Module 11-12.
- BELUM mengubah endpoint /chat/stream sama sekali.

GUARDRAIL:
- JANGAN ubah isi fungsi chat_stream() — itu Langkah 3.
- JANGAN hapus NALA_SYSTEM_PROMPT yang sudah ada.
```

</details>

**Langkah 3 — Ubah endpoint `/chat/stream`**

`/chat/stream` (dibangun di Module 8, menggantikan `/chat` total) sampai sekarang masih murni streaming + riwayat, tanpa retrieval. Langkah ini menambahkan retrieval ke endpoint itu — query yang di-embed adalah **pesan user terakhir saja** (bukan seluruh riwayat), karena riwayat percakapan sebelumnya belum tentu relevan sebagai kata kunci pencarian dokumen.

```python
# app/main.py
@app.post("/chat/stream")
def chat_stream(request: ChatStreamRequest) -> StreamingResponse:
    if not request.messages or request.messages[-1].role != "user":
        raise HTTPException(
            status_code=400,
            detail="messages harus non-kosong dan elemen terakhir harus role 'user'",
        )

    recent = request.messages[-HISTORY_WINDOW:]
    last_user_message = recent[-1].content

    try:
        query_embedding = embed_text(last_user_message, base_url=OLLAMA_BASE_URL)
        results = vector_store.search(query_embedding, top_k=2)
    except httpx.HTTPError:
        results = []

    if results:
        context = "\n\n".join(r["text"] for r in results)
        system_prompt = NALA_SYSTEM_PROMPT
        grounded_content = f"Konteks:\n{context}\n\nPertanyaan: {last_user_message}"
    else:
        system_prompt = NALA_SYSTEM_PROMPT_NO_CONTEXT
        grounded_content = last_user_message

    ollama_messages = [{"role": "system", "content": system_prompt}]
    ollama_messages += [{"role": m.role, "content": m.content} for m in recent[:-1]]
    ollama_messages.append({"role": "user", "content": grounded_content})

    return StreamingResponse(
        ollama_client.chat_stream(ollama_messages), media_type="text/plain"
    )
```

- **Embedding pesan user**: `embed_text(last_user_message, ...)` — model yang sama (`nomic-embed-text`, Module 11) yang dipakai saat indexing (Bagian 1), menghasilkan vektor 768-dimensi, dari pesan **terakhir** di riwayat (bukan seluruh percakapan).
- **Retrieval**: `vector_store.search(query_embedding, top_k=2)` — mengambil top-2 dokumen berdasarkan k-NN similarity (Module 12). `top_k` kecil sengaja — index baru berisi segelintir dokumen utuh (Bagian 1), bukan puluhan chunk, jadi tidak ada gunanya minta lebih dari yang ada.
- **Fallback**: dua kondisi masuk ke cabang `else` (tanpa `results`): (1) `embed_text()`/`vector_store.search()` melempar `httpx.HTTPError` (OpenSearch tidak terjangkau), atau (2) keduanya berhasil tapi `results` kosong (index belum pernah di-ingest, atau tidak ada dokumen relevan). Di kedua kasus, `NALA_SYSTEM_PROMPT_NO_CONTEXT` dipakai sebagai pengganti — isinya sama persis kecuali instruksi terakhir: alih-alih "jawab HANYA dari konteks", mengizinkan jawaban dari pengetahuan umum sambil jujur bilang belum ada dokumen internal yang terhubung.
- **Kalau retrieval berhasil**: teks dokumen (utuh, belum dipecah) digabungkan jadi satu string konteks, `grounded_content` menggantikan isi pesan user terakhir sebelum dikirim ke Ollama — riwayat pesan-pesan **sebelumnya** (`recent[:-1]`) tetap dikirim apa adanya, tidak ikut di-grounding. `windowing` (`HISTORY_WINDOW = 10`, Module 8 Bagian 4) tidak berubah sama sekali.

**▶️ Jalankan & lihat hasilnya**

```bash
docker compose up --build api
```

```bash
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Berapa lama proses pengajuan kredit sampai pencairan dana?"}]}'
```

✅ **Indikator sukses**: jawaban menyebut angka dari dokumen (bukan estimasi generik), muncul bertahap (streaming) — **ini pertama kalinya sepanjang Module 7-16, NALA benar-benar menjawab dari dokumen sungguhan.** Bandingkan dengan jawaban Module 7-8 (sebelum RAG) yang selalu generik. Coba juga percakapan multi-turn (pertanyaan lanjutan tanpa menyebut kata kunci) — harus tetap dipahami **dan** tetap memicu retrieval baru untuk tiap pesan.

<details>
<summary><strong>Pakai Claude Code? Salin prompt berikut, paste untuk eksekusi Langkah 3</strong></summary>

```
Ubah endpoint POST /chat/stream supaya retrieval-augmented (Module 13,
Langkah 3).

GOAL:
- Di Nala/app/main.py, di dalam fungsi
  chat_stream() (endpoint POST /chat/stream), SETELAH baris
  `recent = request.messages[-HISTORY_WINDOW:]` yang sudah ada,
  tambahkan: last_user_message = recent[-1].content; try/except:
  di dalam try, query_embedding = embed_text(last_user_message,
  base_url=OLLAMA_BASE_URL), lalu results =
  vector_store.search(query_embedding, top_k=2); di except
  httpx.HTTPError: results = []. Kalau results ada isinya, susun
  context dari r["text"] tiap hasil, system_prompt =
  NALA_SYSTEM_PROMPT, grounded_content = f"Konteks:\n{context}\n\n
  Pertanyaan: {last_user_message}"; kalau tidak, system_prompt =
  NALA_SYSTEM_PROMPT_NO_CONTEXT, grounded_content =
  last_user_message. Lalu ganti baris penyusunan ollama_messages yang
  sudah ada supaya: [{"role": "system", "content": system_prompt}] +
  [{"role": m.role, "content": m.content} for m in recent[:-1]] +
  [{"role": "user", "content": grounded_content}].

CONTEXT:
- vector_store, embed_text, NALA_SYSTEM_PROMPT_NO_CONTEXT sudah
  di-setup di Langkah 2.
- Validasi 400 dan windowing (HISTORY_WINDOW) yang sudah ada dari
  Module 8 TIDAK berubah.
- Ini SATU-SATUNYA endpoint chat sejak Module 8 — tidak ada endpoint
  /chat lain yang perlu disinkronkan.

GUARDRAIL:
- JANGAN ubah endpoint /health atau /.
- JANGAN ubah signature chat_stream() atau model ChatStreamRequest/ChatMessage.
```

</details>

## 3. NALA Sekarang Menjawab dari Dokumen — Verifikasi Menyeluruh

Coba beberapa skenario untuk memastikan RAG benar-benar bekerja:

**a. Pertanyaan yang jawabannya ada di dokumen:**
```bash
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Dokumen apa saja yang saya butuhkan untuk mengajukan kredit?"}]}'
```
✅ Jawaban menyebut KTP, NPWP, laporan keuangan, dst — persis dari `sop-pengajuan-kredit.md`.

**b. Index kosong → fallback, bukan crash:**
```bash
curl -X DELETE http://localhost:9200/nala-docs
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Berapa lama proses pengajuan kredit?"}]}'
```
✅ Stream tetap mengalir normal (bukan error/hang), jawaban terasa generik. Jalankan ulang `ingest_documents()` (Bagian 1) untuk mengisi index kembali.

**c. Multi-turn tetap jalan setelah retrieval ditambahkan:**
```bash
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"messages": [
    {"role": "user", "content": "Berapa lama proses pengajuan kredit sampai pencairan dana?"},
    {"role": "assistant", "content": "Menurut konteks yang diberikan, waktu estimasi untuk proses pengajuan kredit sampai pencairan dana adalah 2-3 hari kerja setelah mendapatkan persetujuan (approval)."},
    {"role": "user", "content": "Kalau untuk nasabah yang sudah lama jadi customer, apakah lebih cepat?"}
  ]}'
```
✅ Pertanyaan kedua tidak menyebut kata "kredit" sama sekali — NALA harus tetap paham ini masih soal proses kredit, sekaligus tetap melakukan retrieval baru untuk pertanyaan lanjutan ini.

## 4. Grounding: Kenapa NALA Tidak (Selalu) Mengarang

`NALA_SYSTEM_PROMPT` (Module 1-6, tidak diganti nama) sudah mencakup instruksi **grounding** — memaksa model menjawab **hanya** dari konteks yang diberikan, bukan dari pengetahuan umum. `NALA_SYSTEM_PROMPT_NO_CONTEXT` (Bagian 2) sama persis kecuali instruksi terakhir: mengizinkan pengetahuan umum saat retrieval gagal/kosong, sambil jujur bilang belum ada dokumen. Ini instruksi grounding yang membuat jawaban Module 7-8, 9-11 (sebelum ada retrieval, atau saat index kosong) terasa "generik tapi jujur", bukan mengarang seolah tahu SOP internal — konsisten dengan pembahasan halusinasi di Module 9 Bagian 1.

⚠️ Grounding lewat instruksi prompt **membantu**, tapi bukan jaminan mutlak — model kecil (`llama3.2:3b`) tetap bisa sesekali mengabaikan instruksi ini. Ini akan dibahas lebih detail konsistensinya di Module 21 saat model dipakai untuk tool-calling.

## 5. Data Operasional: Upload vs Airflow (Preview Module 15-16)

Sejauh ini, data seed (Bagian 1) diisi lewat pemanggilan `ingest_documents()` secara manual dari terminal. Module 14 dulu meng-**upgrade** `ingest_documents()` supaya memecah dokumen jadi chunk sebelum embed, baru Module 15-16 menambahkan **dua cara lain** memicu proses yang sudah di-upgrade itu:

| Aspek | Endpoint Upload (Module 15) | Airflow Pipeline (Module 16) |
|---|---|---|
| Trigger | Staff upload lewat form web | Manual trigger di Airflow UI/CLI |
| Cocok untuk | Satu dokumen, cepat, reaktif | Batch, audit trail, siap upgrade ke terjadwal |
| Kode yang dipanggil | `ingest_documents()` — versi **upgrade** dari Module 14 | `ingest_documents()` — fungsi **sama persis** dengan yang dipanggil Upload |

**Poin penting**: kode `/chat/stream` di module ini **tidak akan berubah sama sekali** setelah Module 14-16 selesai — chunking, upload, dan Airflow cuma menambah/mengubah **cara mengisi index**, retrieval-nya tetap membaca index `nala-docs` apa adanya, tidak peduli dokumen itu masuk lewat CLI manual (Bagian 1), form upload (Module 15), atau Airflow (Module 16), dan tidak peduli isinya satu vektor per dokumen (sekarang) atau beberapa chunk per dokumen (setelah Module 14). Ini dibuktikan langsung setelah Module 15-16 selesai.

## 6. Bentuk Uji Coba per Checklist

Skenario konkret untuk memverifikasi Bagian 3 — pakai pertanyaan yang jawabannya cukup jelas ada di salah satu dari dua dokumen SOP, supaya hasilnya bisa diprediksi. Karena retrieval di module ini masih level-dokumen (Bagian 7), pertanyaan yang **sangat spesifik** ke sub-bagian dokumen (misal "syarat nasabah perorangan") tetap terjawab — seluruh dokumen ikut jadi konteks — tapi jawabannya bisa terasa kurang fokus dibanding setelah Module 14 menambahkan chunking.

Contoh konkret: coba tanyakan "Apa saja syarat pengajuan kredit untuk nasabah perorangan?" — jawabannya mungkin terasa kurang fokus (seluruh dokumen ikut jadi konteks, bukan cuma bagian yang relevan). Ini **bukan bug** — lihat Bagian 7 untuk penjelasan kenapa ini terjadi dan kenapa itu jadi motivasi Module 14 (chunking).

## 7. Catatan: Keterbatasan Retrieval Level-Dokumen (Preview Module 14)

RAG sudah bekerja (Bagian 3) — tapi retrieval-nya masih sangat kasar: **satu dokumen SOP yang panjang di-embed jadi satu vektor tunggal**, lalu **seluruh isinya** (bisa ribuan karakter) dikirim utuh sebagai konteks ke LLM, walau pertanyaan user cuma butuh satu-dua kalimat spesifik di dalamnya.

**Dua konsekuensi nyata dari ini**:

1. **Konteks yang dikirim ke LLM jauh lebih besar dari yang perlu.** Kalau ada 2 dokumen SOP relevan (`top_k=2`), keduanya dikirim **utuh** — model kecil (`llama3.2:3b`, context window terbatas) harus "menyaring" sendiri bagian mana yang relevan dari ribuan karakter, alih-alih menerima langsung bagian yang sudah difokuskan.
2. **Satu vektor tidak bisa mewakili banyak sub-topik sekaligus dengan baik.** Model embedding merangkum **seluruh** isi dokumen (semua tahapan, semua syarat, semua istilah) jadi satu vektor 768-dimensi — makna spesifik seperti "syarat khusus nasabah perorangan" jadi "diencerkan" oleh bagian-bagian lain dokumen yang tidak berhubungan (misal bagian tentang pencairan dana atau kontak layanan). Akibatnya, similarity antara query yang sangat spesifik dan vektor dokumen yang "umum" ini tidak setajam kalau saja ada representasi yang fokus ke bagian itu saja.

**Ini persis motivasi Module 14**: chunking memecah tiap dokumen jadi potongan-potongan kecil **sebelum** di-embed, supaya tiap vektor mewakili satu sub-topik yang fokus (misal satu vektor khusus untuk bagian "syarat nasabah perorangan"), dan konteks yang dikirim ke LLM jadi jauh lebih ringkas dan relevan. Setelah Module 14, kita akan mengulang perbandingan retrieval sebelum/sesudah chunking secara langsung — termasuk kasus di mana bahkan chunking pun ternyata belum menyelesaikan semuanya (motivasi lebih lanjut untuk hybrid search + reranking di Module 17).

## 8. Checkpoint Praktik

Yang perlu dipastikan sebelum lanjut ke Module 14:

- [ ] `ingest_documents()` mengembalikan jumlah dokumen lebih dari 0 (satu vektor per dokumen, bukan per chunk)
- [ ] `/chat/stream` menjawab berdasarkan isi dokumen SOP (bukan generik) untuk pertanyaan yang jawabannya ada di knowledge base, sambil tetap streaming bertahap
- [ ] Percakapan multi-turn tetap berfungsi setelah retrieval ditambahkan
- [ ] Index kosong menghasilkan fallback ke jawaban generik, bukan crash
- [ ] Kita paham keterbatasan retrieval level-dokumen (Bagian 7) sebagai motivasi Module 14, bukan dianggap "RAG sudah optimal"

Begitu kelima hal ini terverifikasi, lanjut ke Module 14 — menambahkan chunking (memecah dokumen jadi potongan fokus sebelum di-embed), sebelum Module 15 menambah form upload web sebagai cara staff menambahkan dokumen baru ke sistem yang **sudah hidup** ini.

---

> 📌 **Catatan untuk fasilitator**: setelah Module 14 (Chunking), Module 15 (Upload), dan Module 16 (Airflow) selesai dibangun, kembali ke module ini untuk verifikasi tambahan — pastikan dokumen yang diupload lewat form web atau di-trigger lewat Airflow **langsung bisa ditanyakan** ke `/chat/stream` tanpa mengubah satu baris pun kode di module ini. Ini bukti nyata desain "retrieval generik terhadap sumber data" yang dijelaskan Bagian 5.
