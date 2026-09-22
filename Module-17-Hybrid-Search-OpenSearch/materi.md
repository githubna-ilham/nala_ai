# Module 17: Hybrid Search (BM25 + Vector) via OpenSearch

## Tujuan

Menambahkan BM25 (lexical) di samping vector search yang sudah ada sejak Module 12, digabung lewat Reciprocal Rank Fusion (RRF), untuk mengatasi kasus nyata di mana chunk jawaban yang benar kalah oleh chunk pendek yang cuma "mirip" secara makna.

## Definisi

**BM25** adalah algoritma *lexical search* — mencocokkan **kata** secara harfiah antara query dan dokumen, dibobot berdasarkan seberapa jarang/khas kata itu muncul di seluruh index (Bagian 1). Ini kebalikan dari **vector/semantic search** yang sudah dipakai sejak Module 12: vector search mencocokkan **makna**, bukan kata persis, lewat kemiripan embedding. Keduanya bukan dua pilihan yang saling menggantikan, melainkan **saling melengkapi** — BM25 kuat di istilah eksak ("KTP", "NPWP") yang justru sering "diencerkan" maknanya oleh vector search, sementara vector search kuat menangkap parafrase yang tidak pernah bisa ditangkap BM25 sama sekali (Bagian 1).

Menggabungkan dua daftar hasil yang skornya beda skala (skor BM25 tidak berbatas, skor `knn` biasanya 0–1) ternyata bukan sekadar dijumlahkan — itu jebakan yang dibahas di Bagian 4. Solusinya di module ini adalah **Reciprocal Rank Fusion (RRF)**: teknik fusion yang sama sekali membuang skor mentah dan hanya melihat **posisi/rank** tiap dokumen di masing-masing daftar. Setiap dokumen dapat skor `1/(k + rank)` dari tiap daftar tempat ia muncul, lalu skor-skor itu dijumlahkan lintas daftar — dokumen yang sama-sama tinggi di kedua daftar akan menang, tanpa pernah perlu tahu "skor BM25 8.2 itu setara berapa skor vector" (Bagian 5).

Karena berbasis rank, RRF otomatis kebal terhadap masalah normalisasi skor yang jadi akar masalah `bool` query naif — inilah yang membuatnya jadi pendekatan fusion yang lebih *version-proof* dibanding menormalisasi skor secara manual.

```mermaid
flowchart LR
    subgraph B["Daftar BM25"]
        B1["#1 Dok A"]
        B2["#2 Dok C"]
        B3["#3 Dok B"]
    end
    subgraph V["Daftar Vector"]
        V1["#1 Dok B"]
        V2["#2 Dok A"]
        V3["#3 Dok D"]
    end
    B1 -->|"1/(k+1)"| R["RRF_score(d) =<br/>Σ 1/(k+rank)"]
    B2 -->|"1/(k+2)"| R
    B3 -->|"1/(k+3)"| R
    V1 -->|"1/(k+1)"| R
    V2 -->|"1/(k+2)"| R
    V3 -->|"1/(k+3)"| R
    R --> S["Dok A & Dok B naik<br/>(muncul di kedua daftar)"]
```

## Hasil Akhir yang Diharapkan

- `VectorStore` punya method baru `search_bm25()` dan `search_hybrid()`, tanpa perlu reindex `nala-docs`
- `/chat/stream` (satu-satunya endpoint chat NALA sejak Module 8) memanggil `search_hybrid()` (bukan `search()` murni) untuk retrieval
- Untuk query kata kunci eksak ("KTP", "NPWP", "slip gaji"), hasil BM25/hybrid terbukti berbeda urutan dibanding vector murni
- Kita paham kenapa `bool` query naif (skor BM25 + skor `knn` dijumlah langsung) salah, dan kenapa RRF (berbasis rank, bukan skor mentah) jadi solusinya
- Diuji nyata dan dicatat jujur: hybrid search menaikkan recall di level kandidat, tapi untuk kasus keras "syarat kredit nasabah perorangan" chunk yang benar masih di posisi #8 — belum masuk `top_k=3`, motivasi langsung untuk Module 18 (reranking)

## 1. Kenapa Vector Search Murni Tidak Cukup

Module 14 Bagian 9 sudah mendokumentasikan kasus nyata yang jadi motivasi module ini. Pertanyaan *"Apa saja syarat pengajuan kredit untuk nasabah perorangan?"* punya jawaban lengkap di `sop-pengajuan-kredit.md`, tepat di chunk `### 2.1 Untuk Nasabah Perorangan` — tapi chunk itu baru masuk di peringkat **`top_k=15` dari total 29 chunk** saat vector search murni dijalankan. Chunk heading pendek (`## 2. Syarat dan Ketentuan Pengajuan Kredit`) justru mendapat *similarity score* lebih tinggi, karena vektornya "tajam" (fokus ke satu makna singkat), sementara chunk jawaban yang panjang (berisi KTP, KK, slip gaji, NPWP, usia, dst) menghasilkan vektor yang "diencerkan" oleh banyak sub-konsep sekaligus.

NALA saat itu tidak salah menjawab — dengan `top_k=3` yang dipakai module ini, chunk jawaban yang tepat memang tidak pernah terlihat sama sekali. Menaikkan `top_k` ke 15 bukan solusi murah: mayoritas dari 15 chunk itu tidak relevan, dan mengirim itu semua ke `llama3.2:3b` (context window terbatas) berisiko mengencerkan fokus model, bukan membantunya.

**Akar masalahnya**: vector search murni bagus untuk menangkap *makna* (nasabah bertanya "syarat kredit", dokumen bicara "dokumen yang dibutuhkan" — beda kata, makna dekat), tapi lemah menangkap **kecocokan kata kunci eksak** — istilah seperti "KTP", "NPWP", "slip gaji", atau nomor SOP justru lebih baik ditangkap oleh pencarian lexical (keyword matching) klasik seperti **BM25**. Kedua metode punya kelemahan yang saling melengkapi:

| | Vector Search (semantic) | BM25 (lexical) |
|---|---|---|
| Kuat di | Makna yang mirip walau kata beda ("syarat kredit" ≈ "dokumen yang dibutuhkan") | Kecocokan istilah eksak ("KTP", "NPWP", nomor SOP) |
| Lemah di | Chunk pendek/heading bisa "menang" dibanding chunk panjang yang relevan (kasus di atas) | Tidak paham sinonim atau parafrase sama sekali |
| Butuh | Model embedding (`nomic-embed-text`) | Index teks biasa (sudah ada sejak Module 12 — field `text` di mapping `nala-docs`) |

**Hybrid search** menggabungkan keduanya: jalankan BM25 dan vector search secara paralel, lalu gabungkan (fusion) hasilnya jadi satu daftar peringkat. Ini bukan mengganti vector search — ini menambah satu sinyal lagi supaya chunk yang relevan secara kata kunci *maupun* makna sama-sama punya kesempatan naik ke atas.

```mermaid
flowchart LR
    Q["Pertanyaan user"] --> E["embed_text()"]
    Q --> B["Query BM25<br/>match pada field text"]
    E --> K["Query k-NN<br/>vector similarity"]
    B --> F["Fusion (RRF)"]
    K --> F
    F --> R["Top-K hasil gabungan"]
```

### Coba Langsung: Verifikasi Baseline Vector Search dengan Data Anda Sendiri

Angka "`top_k=15` dari 29 chunk" di atas berasal dari index dan isi dokumen tertentu — bisa berbeda di komputer Anda tergantung dokumen apa saja yang sudah ter-*ingest*. Sebelum menulis kode apa pun di Bagian 6, jalankan dulu `search()` murni (vector, sudah ada sejak Module 12) untuk query yang sama, dan catat di posisi keberapa chunk `### 2.1 Untuk Nasabah Perorangan` muncul — ini baseline yang nanti dibandingkan lagi setelah `search_hybrid()` ditulis di Bagian 6:

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

✅ **Indikator sukses**: baris tercetak untuk tiap hasil — catat posisi (kalau muncul sama sekali di top-10) chunk `### 2.1 Untuk Nasabah Perorangan`. Angka ini yang jadi pembanding "sebelum" begitu `search_hybrid()` selesai ditulis dan diuji di Bagian 6.

## 2. Apa itu BM25: Cara Kerja di Balik Layar

**BM25** (singkatan dari *Best Matching 25* — versi ke-25 dari rumus yang dikembangkan tim riset *information retrieval* mulai era 1970-1990an) adalah algoritma scoring standar untuk pencarian berbasis kata kunci, dipakai sebagai default oleh hampir semua search engine modern berbasis Lucene — termasuk OpenSearch dan Elasticsearch. Intuisinya sederhana: dokumen yang **lebih sering menyebut kata-kata dari query**, terutama kata-kata yang **jarang muncul** di seluruh koleksi dokumen (makanya lebih "khas"/informatif kalau sampai cocok), mendapat skor lebih tinggi.

Tiga komponen yang menyusun skor BM25 untuk satu dokumen relatif ke satu query:

- **Term Frequency (TF)** — seberapa sering tiap kata query muncul di dokumen itu. Makin sering, skor makin tinggi, tapi dengan efek jenuh (*saturating*): kata yang muncul 10 kali tidak otomatis dianggap 10× lebih relevan daripada yang muncul sekali — ada titik di mana pengulangan tambahan berhenti menaikkan skor secara linear.
- **Inverse Document Frequency (IDF)** — seberapa **jarang** kata itu muncul di seluruh index. Kata umum seperti "dan", "yang", "untuk" muncul di hampir semua dokumen sehingga kontribusinya ke skor kecil. Kata spesifik seperti "NPWP" atau "perorangan", yang cuma muncul di segelintir chunk, punya IDF tinggi — kecocokan dengan kata semacam ini jauh lebih bermakna secara statistik.
- **Length normalization** — dokumen yang jauh lebih panjang dari rata-rata index dikenai penalti ringan, supaya dokumen panjang tidak otomatis menang cuma karena secara kebetulan punya peluang lebih besar mengandung kata-kata query di suatu tempat.

Ketiganya digabung dalam formula:

```
BM25(D, Q) = Σ IDF(qᵢ) × [f(qᵢ,D) × (k1+1)] / [f(qᵢ,D) + k1 × (1 - b + b × |D|/avgdl)]
```

di mana `f(qᵢ,D)` adalah frekuensi kata `qᵢ` di dokumen `D`, `|D|` panjang dokumen `D`, `avgdl` rata-rata panjang dokumen di seluruh index, dan `k1`/`b` adalah konstanta tuning yang mengatur seberapa besar efek saturasi TF (`k1`) dan penalti panjang dokumen (`b`) — OpenSearch memakai default `k1=1.2`, `b=0.75`, dan module ini **tidak** men-tuning nilai itu secara khusus.

```mermaid
flowchart LR
    Q["Query: 'syarat pengajuan<br/>kredit nasabah perorangan'"] --> T["Tokenisasi<br/>(pecah jadi kata)"]
    T --> TF["Term Frequency (TF)<br/>seberapa sering tiap kata<br/>muncul DI DOKUMEN ini"]
    T --> IDF["Inverse Document Frequency (IDF)<br/>seberapa JARANG kata itu<br/>di SELURUH index"]
    LEN["Length Normalization<br/>penalti dokumen kepanjangan"] --> S["Skor BM25"]
    TF --> S
    IDF --> S
```

### Perbedaan Paling Mendasar dengan Vector Search

BM25 menghitung skor dari **kehadiran kata secara literal** (setelah tokenisasi dasar — lihat Bagian 3 soal keterbatasan analyzer) — ia tidak tahu apa pun soal makna. Kata "kredit" dan "pinjaman" dianggap sepenuhnya berbeda oleh BM25, walau maknanya dekat; di sinilah **vector search justru unggul**, karena embedding menangkap kedekatan makna (Module 12). Tapi sebaliknya, BM25 kebal terhadap masalah "vektor diencerkan" yang jadi akar masalah di Bagian 1: skor BM25 untuk sebuah chunk naik proporsional dengan seberapa banyak kata **query** yang cocok persis di dalamnya, tidak peduli topik lain apa saja yang ikut dibahas di chunk itu — beda dengan vector search yang merangkum **seluruh** isi chunk jadi satu vektor tunggal.

**Contoh sederhana dulu**, sebelum kembali ke kasus NALA — bayangkan tiga kalimat pendek yang sudah di-index (bukan dari dokumen NALA, murni ilustrasi generik supaya intuisinya jelas lebih dulu):

- Dokumen A: "Seekor kucing hitam duduk di atas meja."
- Dokumen B: "Anjing coklat berlari mengejar bola di taman."
- Dokumen C: "Kucing putih dan kucing hitam bermain bersama di taman."

Query: *"kucing hitam duduk"*

| Token dari query | Muncul di dokumen mana saja? | IDF (makin jarang, makin tinggi) |
|---|---|---|
| "kucing" | A (1×), C (2×) — ada di 2 dari 3 dokumen | Sedang |
| "hitam" | A (1×), C (1×) — ada di 2 dari 3 dokumen | Sedang |
| "duduk" | Cuma A (1×) — ada di 1 dari 3 dokumen | **Tinggi** — kata paling langka, paling diskriminatif |

Dokumen A cocok dengan **ketiga** kata query, termasuk kata paling langka "duduk" — BM25 kemungkinan besar memberi skor tertinggi ke Dokumen A. Dokumen C memang menyebut "kucing hitam" (bahkan "kucing" dua kali), tapi sama sekali tidak menyebut "duduk" — kata yang justru paling informatif di query ini, karena paling jarang muncul di seluruh koleksi. Inilah kenapa IDF penting: kecocokan pada kata langka "membayar" lebih dari sekadar kecocokan pada kata umum yang muncul di mana-mana.

**Sekarang kembali ke kasus NALA** — intuisi yang sama persis berlaku, cuma skalanya lebih besar (belasan-puluhan potongan dokumen, bukan 3 kalimat) dan istilahnya spesifik domain finansial, bukan "kucing"/"anjing". Sebagai pengingat: dokumen SOP NALA sudah dipecah jadi beberapa **chunk** berdasarkan heading Markdown-nya (`chunk_markdown()`, Module 14) — satu chunk yang jadi contoh berulang di module ini berjudul `### 2.1 Untuk Nasabah Perorangan`, potongan dari `sop-pengajuan-kredit.md` yang berisi daftar syarat dokumen (KTP, KK, slip gaji, dst). Untuk query yang dipakai berulang di module ini — *"Apa saja syarat pengajuan kredit untuk nasabah perorangan?"* — begini token-token kuncinya cocok dengan chunk itu:

| Token dari query | Muncul di chunk `### 2.1`? | Kontribusi ke skor BM25 |
|---|---|---|
| "perorangan" | ✅ — persis di judul heading-nya | **Tinggi** — kata paling khas, jarang muncul di chunk lain sepanjang index |
| "nasabah" | ✅ — persis di judul heading-nya | **Tinggi** — IDF tinggi, tidak muncul di banyak chunk lain |
| "syarat" | ✅ — bagian dari konteks section 2 | Sedang |
| "pengajuan" | Mungkin muncul juga di chunk lain | Sedang |
| "kredit" | Muncul di hampir semua chunk (topik seluruh dokumen ini memang kredit) | **Rendah** — IDF rendah, kata ini terlalu umum di index ini untuk jadi pembeda |

Persis seperti "duduk" di contoh kucing tadi: "perorangan" dan "nasabah" adalah kata paling diskriminatif (jarang, spesifik) di query ini — itulah yang mendorong BM25 memberi skor tinggi ke chunk `### 2.1`, konsisten dengan angka pengujian nyata di Bagian 8: BM25 menempatkan chunk ini di peringkat **#4 dari 14** chunk, jauh lebih tinggi dibanding vector search murni yang menaruhnya di peringkat **#10 dari 14** (Bagian 1) — bukti langsung bahwa BM25 dan vector search benar-benar menilai relevansi lewat mekanisme yang sama sekali berbeda, bukan cuma varian dari hal yang sama.

### Coba Langsung: Lihat Skor BM25 Mentah dari OpenSearch

Tidak perlu menunggu sampai `search_bm25()` ditulis di Bagian 6 untuk melihat BM25 bekerja — OpenSearch sudah punya kemampuan ini sejak index `nala-docs` dibuat (Module 12), karena field `text` di mapping-nya bertipe `text` (bukan `knn_vector`). Query `match` di bawah ini langsung memanggil BM25 bawaan OpenSearch lewat REST API biasa, tanpa satu baris kode Python aplikasi pun:

```bash
curl -s -X POST "http://localhost:9200/nala-docs/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "size": 5,
    "query": { "match": { "text": "syarat pengajuan kredit nasabah perorangan" } }
  }' | python3 -m json.tool
```

Perhatikan field `"_score"` di tiap hasil — **itulah** angka yang dihasilkan formula BM25 di atas, dihitung OpenSearch di balik layar dari TF, IDF, dan length normalization tiap chunk relatif ke lima kata di query. Chunk dengan `_score` tertinggi ditaruh paling atas; kalau index Anda sama seperti di materi, chunk `### 2.1 Untuk Nasabah Perorangan` seharusnya muncul dekat urutan atas — konsisten dengan tabel token-matching di atas.

Kalau ingin tampilan lebih ringkas (cuma skor + potongan teks, tanpa metadata JSON penuh), pakai versi Python ini lewat container `api`:

```bash
docker compose exec api python -c "
import httpx

response = httpx.post(
    'http://opensearch:9200/nala-docs/_search',
    json={
        'size': 5,
        'query': {'match': {'text': 'syarat pengajuan kredit nasabah perorangan'}},
    },
)
for hit in response.json()['hits']['hits']:
    print(round(hit['_score'], 3), '-', hit['_source']['text'][:70])
"
```

✅ **Indikator sukses**: lima baris tercetak, terurut dari skor BM25 tertinggi ke terendah — bandingkan urutan ini dengan hasil `store.search()` (vector, Module 12) untuk query yang sama persis; urutannya kemungkinan besar berbeda, bukti konkret bahwa kedua metode benar-benar menilai relevansi dengan cara berbeda, persis seperti yang dijelaskan di atas.

⚠️ Ini **query mentah langsung ke OpenSearch** — belum lewat `VectorStore`, belum jadi bagian alur `/chat/stream` mana pun. Tujuannya murni eksplorasi supaya konsep BM25 di atas terasa nyata sebelum masuk ke kode aplikasi yang sesungguhnya di Bagian 6 (`search_bm25()`, yang membungkus query yang sama ini jadi method Python yang bisa dipanggil ulang).

## 3. Catatan Penting: BM25 Tidak Butuh Reindex

Kabar baik: mapping index `nala-docs` yang dibuat `VectorStore.ensure_index()` sejak Module 12 **sudah** punya field `"text": {"type": "text"}` di samping `"embedding": {"type": "knn_vector", ...}` (lihat `app/vector_store.py`, method `ensure_index()`). Field `text` bertipe `text` inilah yang otomatis bisa di-*query* dengan BM25 lewat query `match` — OpenSearch (seperti Elasticsearch) memakai BM25 sebagai algoritma scoring default untuk field bertipe `text`, tanpa konfigurasi tambahan apa pun. Artinya: **hybrid search di module ini murni penambahan, bukan migrasi** — index yang sudah terisi dari ingest sebelumnya (Module 16) tidak perlu di-*reindex* atau dihapus.

Satu keterbatasan yang jujur perlu disebut: mapping ini tidak menentukan *analyzer* khusus untuk field `text`, jadi OpenSearch memakai analyzer default (`standard`) — bukan analyzer Bahasa Indonesia dengan stemming (mis. memahami "mengajukan", "pengajuan", "diajukan" sebagai satu kata dasar yang sama). Konsekuensinya: BM25 di module ini menang di pencocokan **token eksak** ("KTP", "NPWP", "slip gaji" — persis kasus di Bagian 1), bukan karena ia memahami morfologi Bahasa Indonesia. Menambahkan analyzer `indonesian` (tersedia sebagai plugin analysis-nya OpenSearch) akan meningkatkan recall BM25 lebih jauh, tapi **butuh reindex total** (analyzer hanya berlaku untuk dokumen yang di-index setelah mapping diubah) — di luar cakupan module ini, dicatat di sini supaya tidak ada yang mengira ini sudah otomatis berjalan.

## 4. Jebakan Umum: `bool` Query Naif (Jangan Dipakai)

Cara paling intuitif yang sering dicoba pertama kali adalah menggabungkan `match` dan `knn` dalam satu query `bool`:

```json
// ANTI-POLA — jangan dipakai, lihat penjelasan di bawah
{
  "size": 3,
  "query": {
    "bool": {
      "should": [
        { "match": { "text": "syarat pengajuan kredit nasabah perorangan" } },
        { "knn": { "embedding": { "vector": [0.12, -0.03, "..."], "k": 3 } } }
      ]
    }
  }
}
```

Ini **tampak** benar dan bahkan bisa dieksekusi tanpa error — masalahnya baru terlihat begitu skor dibandingkan. Skor BM25 dari `match` tidak dibatasi rentang (bisa berupa angka seperti 8.2, 15.7, atau lebih — tergantung panjang dokumen dan frekuensi term), sementara skor `knn` di OpenSearch untuk banyak *space type* berkisar di rentang 0–1 (skor similarity yang dinormalisasi). Kalau keduanya dijumlahkan begitu saja dalam satu `bool.should`, hasilnya **didominasi skor yang skalanya lebih besar** — biasanya BM25 — bukan karena secara substantif BM25 memang harus menang, tapi murni karena satuan angkanya lebih besar. Efeknya: query ini bukan hybrid search yang seimbang, ia jadi BM25 search yang kebetulan ada sedikit noise dari vector search.

Ini justru **alasan kenapa normalisasi skor itu penting** sebelum dua metode retrieval digabung — bukan detail teknis kecil, tapi inti dari kenapa hybrid search butuh desain lebih dari sekadar "gabungkan dua query".

**Catatan produksi**: OpenSearch 2.11+ punya fitur bawaan untuk kasus ini — query khusus `hybrid` yang dipasangkan dengan *search pipeline* berisi `normalization-processor`, yang menormalisasi skor tiap sub-query (mis. min-max) sebelum digabung, dilakukan di sisi server. Ini pendekatan yang lebih efisien untuk skala produksi (satu request, bukan dua). Module ini tidak memakai jalur ini secara langsung — konfigurasi *search pipeline* butuh setup tambahan di luar `docker-compose.yml` yang sudah ada, dan detail parameternya bisa berbeda antar versi minor OpenSearch. Sebagai gantinya, module ini mengajarkan pendekatan yang lebih mudah diverifikasi dan version-proof: **fusion di sisi aplikasi (Python)**, memakai dua query terpisah yang masing-masing sudah dipakai sejak Module 12 (`search_bm25()` baru, dan `search()` yang sudah ada). Mekanismenya identik secara konsep, hanya lokasinya (aplikasi vs. server) yang berbeda — kalau nanti mau migrasi ke *search pipeline* bawaan OpenSearch di produksi, konsepnya (normalisasi sebelum fusion) sudah dipahami dari sini.

## 5. Reciprocal Rank Fusion (RRF): Fusion Tanpa Perlu Menormalisasi Skor

Alih-alih menormalisasi skor BM25 dan skor vector (yang butuh tahu rentang masing-masing di awal, rawan berubah tergantung data), module ini memakai **Reciprocal Rank Fusion (RRF)** — teknik fusion yang **mengabaikan skor mentah sama sekali** dan hanya memakai **peringkat (rank)** tiap dokumen di masing-masing daftar hasil:

$$\text{RRF\_score}(d) = \sum_{\text{daftar} \in \{BM25, Vector\}} \frac{1}{k + \text{rank}_{\text{daftar}}(d)}$$

Dengan `k` (konstanta, umumnya `60`) sebagai peredam supaya peringkat-peringkat teratas tidak mendominasi berlebihan. Dokumen yang muncul di peringkat atas di **kedua** daftar (BM25 maupun vector) akan mendapat skor RRF tertinggi — dokumen yang cuma muncul di satu daftar saja tetap dapat skor, tapi lebih rendah. Karena berbasis rank (bukan skor mentah), RRF otomatis kebal terhadap masalah skala yang membuat Bagian 3 gagal — tidak perlu tahu skor BM25 "biasanya" berapa dibanding skor `knn`.

**Contoh Kasus: Menggabungkan Dua Daftar Peringkat**

Anggap query "berapa lama proses cair KUR" menghasilkan dua daftar hasil terpisah — satu dari BM25 (cocok kata kunci), satu dari vector search (cocok makna) — masing-masing berisi 3 dokumen dengan skor mentah yang **skalanya sama sekali berbeda** (BM25 bisa puluhan, cosine cuma 0-1):

| Peringkat | Daftar BM25 (skor mentah) | Daftar Vector (skor mentah) |
|---|---|---|
| 1 | Dok C (skor 12.4) | Dok A (skor 0.91) |
| 2 | Dok A (skor 9.1) | Dok B (skor 0.85) |
| 3 | Dok B (skor 6.7) | Dok C (skor 0.79) |

RRF **membuang semua skor mentah itu** dan hanya memakai posisi peringkat (1, 2, 3, ...) memakai `k=60`:

```
RRF(Dok A) = 1/(60+2)  +  1/(60+1)  = 0.01613 + 0.01639 = 0.03252   (peringkat 2 di BM25, peringkat 1 di Vector)
RRF(Dok B) = 1/(60+3)  +  1/(60+2)  = 0.01587 + 0.01613 = 0.03200   (peringkat 3 di BM25, peringkat 2 di Vector)
RRF(Dok C) = 1/(60+1)  +  1/(60+3)  = 0.01639 + 0.01587 = 0.03226   (peringkat 1 di BM25, peringkat 3 di Vector)
```

| Dokumen | Peringkat BM25 | Peringkat Vector | Skor RRF | Peringkat gabungan |
|---|---|---|---|---|
| Dok A | 2 | 1 | **0.03252** | **1** — konsisten tinggi di kedua daftar |
| Dok C | 1 | 3 | 0.03226 | 2 — juara di satu daftar, lemah di daftar lain |
| Dok B | 3 | 2 | 0.03200 | 3 — konsisten sedang di kedua daftar |

**Dok A menang** bukan karena juara di salah satu daftar (dia peringkat 2 di BM25), tapi karena **konsisten baik di keduanya** — inilah inti RRF: dokumen yang relevan secara kata kunci **dan** makna diprioritaskan di atas dokumen yang cuma unggul di salah satu. Dok C sempat juara BM25 (peringkat 1) tapi lemah di vector (peringkat 3), jadi skor gabungannya turun ke posisi 2. Perhatikan juga betapa **kecil dan berdekatan** angka RRF-nya (0.032xx) — itu wajar, karena yang penting bukan besar-kecilnya angka, tapi urutan relatifnya.

## 6. Struktur Kode yang Ditambahkan

Dua Tahap: **Tahap A** menambah kemampuan baru di `VectorStore` (`search_bm25()`, `search_hybrid()`), belum dipakai siapa pun. **Tahap B** mengganti pemanggilan `vector_store.search()` di `/chat/stream` (`app/main.py`) jadi `vector_store.search_hybrid()`.

### Prasyarat & Setup Sebelum Mulai

- Sudah menyelesaikan **Module 16** (`Nala/` berjalan lengkap: chat UI, streaming/multi-turn, upload, embedding/vector store, chunking, Airflow, RAG chain)
- Docker Desktop sudah dialokasikan resource yang cukup — minimal 16GB RAM (sama seperti kebutuhan sejak Module 12-16); module ini sendiri tidak menambah service Docker baru, jadi belum perlu menaikkan alokasi lagi

`Nala/` sudah dibangun bertahap sejak Module 1 dan berjalan lengkap sampai akhir Module 16 — module ini melanjutkan **edit langsung di folder yang sama** (`Nala/`), tidak ada folder baru yang perlu dibuat atau disalin. Sepanjang seluruh kurikulum (Module 1 sampai Module 29) hanya ada **satu** folder kode: `Nala/`.

Container dan volume Docker (`ollama`, `opensearch`, `airflow`, dst) yang sudah berjalan sejak Module 7-16 tetap dipakai apa adanya di module ini — karena `docker-compose.yml` yang dipakai memang tetap sama satu-satunya, data yang sudah ada (index OpenSearch yang sudah terisi dari ingest sebelumnya, model Ollama yang sudah di-*pull*) otomatis ikut terbawa, tidak perlu diulang dari nol. Masuk ke folder dan jalankan service yang relevan:

```bash
cd Nala
docker compose up --build ollama opensearch api
```

Tiga service ini sudah pernah dijalankan sebelumnya — kalau model `llama3.2:3b` dan `nomic-embed-text` sudah pernah di-*pull* ke volume `ollama_data` sebelumnya, tidak perlu di-*pull* ulang (volume Docker persisten, selama tidak dihapus). Verifikasi:

```bash
docker compose exec ollama ollama list
```

Kalau `llama3.2:3b` dan `nomic-embed-text` sudah muncul, lanjut ke Tahap A. Kalau belum, ulangi `docker compose exec ollama ollama pull <nama-model>` untuk masing-masing (lihat Module 2 materi.md (bagian Panduan Praktik) dan Module 11 materi.md untuk detail model yang dipakai).

Pastikan juga index `nala-docs` di OpenSearch masih terisi dari ingest sebelumnya:

```bash
curl http://localhost:9200/nala-docs/_count
```

Kalau `count` bernilai `0` (index kosong, misalnya karena volume `opensearch_data` baru), jalankan ulang ingest:

```bash
docker compose exec api python -c "from app.ingest import ingest_documents; print(ingest_documents('/app/knowledge-base'))"
```

### Tahap A — Tambah `search_bm25()` dan `search_hybrid()` di `app/vector_store.py`

**Langkah 1 — Tambah `_id` ke hasil `search()` yang sudah ada**

RRF butuh identitas unik tiap dokumen untuk mencocokkan kemunculannya di dua daftar hasil (BM25 dan vector) — `search()` yang sudah ada sejak Module 12 belum mengembalikan `_id` (ID dokumen OpenSearch, bukan `metadata`). Tambahkan satu key ke setiap hasil:

```python
# app/vector_store.py — di dalam method search() yang sudah ada
def search(self, query_embedding: list[float], top_k: int = 3) -> list[dict]:
    with httpx.Client() as client:
        response = client.post(
            f"{self.base_url}/{self.index_name}/_search",
            json={
                "size": top_k,
                "query": {
                    "knn": {"embedding": {"vector": query_embedding, "k": top_k}}
                },
            },
            timeout=30.0,
        )
        response.raise_for_status()
        hits = response.json()["hits"]["hits"]
        return [
            {
                "_id": hit["_id"],
                "text": hit["_source"]["text"],
                "score": hit["_score"],
                "metadata": hit["_source"]["metadata"],
            }
            for hit in hits
        ]
```

Satu-satunya perubahan: baris `"_id": hit["_id"],` ditambahkan ke dict hasil. Ini **tidak** memutus pemanggil yang sudah ada — kode Module 12 yang memakai `r["text"]` atau `r["metadata"]` tetap berfungsi, `_id` cuma key tambahan.

<details>
<summary><strong>Pakai Claude Code? Salin prompt berikut, paste untuk eksekusi Langkah 1</strong></summary>

```
Tambah key _id ke hasil search() yang sudah ada di VectorStore
(Module 17, Tahap A, Langkah 1) — belum dipakai method atau endpoint
baru apa pun.

GOAL:
- Di Nala/app/vector_store.py, method search() yang sudah ada:
  tambahkan key "_id": hit["_id"] ke setiap dict di list yang
  dikembalikan (selain "text", "score", "metadata" yang sudah ada).

CONTEXT:
- File ini (`app/vector_store.py`) sudah ada di `Nala/` sejak
  Module 12 — edit langsung di file yang sama, tidak ada folder
  lain yang perlu disalin.
- _id ini dibutuhkan RRF (Langkah 3) untuk mencocokkan dokumen yang
  sama di dua daftar hasil (BM25 dan vector).

GUARDRAIL:
- JANGAN ubah signature search() (nama, parameter, return type list
  of dict) — cuma tambah key _id ke tiap dict hasil.
- JANGAN ubah ensure_index() atau index_document().
- JANGAN sentuh app/main.py di langkah ini.
```

</details>

**Langkah 2 — Tambah method `search_bm25()`**

```python
# app/vector_store.py
def search_bm25(self, query_text: str, top_k: int = 10) -> list[dict]:
    with httpx.Client() as client:
        response = client.post(
            f"{self.base_url}/{self.index_name}/_search",
            json={
                "size": top_k,
                "query": {"match": {"text": query_text}},
            },
            timeout=30.0,
        )
        response.raise_for_status()
        hits = response.json()["hits"]["hits"]
        return [
            {
                "_id": hit["_id"],
                "text": hit["_source"]["text"],
                "score": hit["_score"],
                "metadata": hit["_source"]["metadata"],
            }
            for hit in hits
        ]
```

Perhatikan kemiripannya dengan `search()`: bedanya cuma bagian `query` — `{"match": {"text": query_text}}` (BM25 lexical, mencari `query_text` mentah, bukan embedding) menggantikan `{"knn": {...}}`. Ini query BM25 paling dasar di OpenSearch — tidak butuh konfigurasi index tambahan (lihat Bagian 2), field `text` sudah otomatis punya scoring BM25 bawaan.

**▶️ Jalankan & lihat hasilnya**

```bash
docker compose up --build api
```

```bash
docker compose exec api python -c "
from app.vector_store import VectorStore
store = VectorStore(base_url='http://opensearch:9200', index_name='nala-docs')
results = store.search_bm25('syarat KTP NPWP slip gaji', top_k=5)
for r in results:
    print(r['score'], '-', r['text'][:60])
"
```

✅ **Indikator sukses**: tidak ada error, dan hasil teratas berisi kata-kata yang cocok persis dengan query ("KTP", "NPWP", "slip gaji") — bandingkan dengan hasil `store.search()` (vector) untuk query yang sama, urutannya kemungkinan besar berbeda.

<details>
<summary><strong>Pakai Claude Code? Salin prompt berikut, paste untuk eksekusi Langkah 2</strong></summary>

```
Tambah method baru search_bm25() di VectorStore (Module 17, Tahap A,
Langkah 2) — belum dipakai endpoint apa pun.

GOAL:
- Di Nala/app/vector_store.py, tambah method baru
  search_bm25(self, query_text: str, top_k: int = 10) -> list[dict]:
  POST ke {base_url}/{index_name}/_search dengan body {"size": top_k,
  "query": {"match": {"text": query_text}}}, parse hits sama persis
  seperti search() (termasuk _id), return list of dict {_id, text,
  score, metadata}.

CONTEXT:
- File ini (`app/vector_store.py`) sudah ada di `Nala/` sejak
  Module 12 — edit langsung di file yang sama, tidak ada folder lain
  yang perlu disalin.
- Key _id di hasil search() sudah ditambahkan di Langkah 1.
- Field "text" di mapping index nala-docs (dibuat ensure_index())
  sudah bertipe "text" sejak Module 12 — BM25 bisa langsung dipakai
  tanpa reindex.

GUARDRAIL:
- JANGAN ubah search() yang sudah ada.
- JANGAN ubah ensure_index() atau index_document().
- JANGAN sentuh app/main.py di langkah ini.
```

</details>

**Langkah 3 — Tambah method `search_hybrid()` dengan RRF**

```python
# app/vector_store.py
def search_hybrid(
    self,
    query_text: str,
    query_embedding: list[float],
    top_k: int = 3,
    candidate_pool: int = 20,
    rrf_k: int = 60,
) -> list[dict]:
    bm25_results = self.search_bm25(query_text, top_k=candidate_pool)
    vector_results = self.search(query_embedding, top_k=candidate_pool)

    fused_scores: dict[str, float] = {}
    doc_lookup: dict[str, dict] = {}

    for rank, hit in enumerate(bm25_results):
        fused_scores[hit["_id"]] = fused_scores.get(hit["_id"], 0.0) + 1.0 / (rrf_k + rank + 1)
        doc_lookup[hit["_id"]] = hit

    for rank, hit in enumerate(vector_results):
        fused_scores[hit["_id"]] = fused_scores.get(hit["_id"], 0.0) + 1.0 / (rrf_k + rank + 1)
        doc_lookup.setdefault(hit["_id"], hit)

    ranked_ids = sorted(fused_scores, key=fused_scores.get, reverse=True)[:top_k]
    return [
        {**doc_lookup[doc_id], "rrf_score": fused_scores[doc_id]}
        for doc_id in ranked_ids
    ]
```

- **`candidate_pool=20`**: jumlah kandidat yang diambil dari **masing-masing** metode (BM25 dan vector) sebelum fusion — bukan `top_k` final. Nilai ini dibuat lebih besar dari `top_k` supaya fusion punya cukup bahan untuk memilih dari kedua sisi; default `20` ini juga yang nanti dipakai apa adanya oleh Module 18 (reranking) sebagai ukuran *candidate set* sebelum cross-encoder menyortirnya ulang — bukan kebetulan, ini desain yang sengaja disiapkan untuk Module 18.
- **`doc_lookup`**: dictionary bantu supaya isi dokumen (`text`, `metadata`, dst) tidak perlu dicari ulang — disimpan begitu pertama kali ditemui. `setdefault()` pada loop `vector_results` sengaja dipakai (bukan `=`) supaya versi BM25 yang tersimpan lebih dulu tidak tertimpa kalau dokumen yang sama muncul di kedua daftar (isinya identik, cuma untuk menghindari kerja dua kali).
- **`rrf_k=60`**: konstanta standar RRF dari literatur information retrieval — meredam dominasi peringkat #1 supaya dokumen di peringkat #2-3 dari kedua daftar tetap kompetitif melawan dokumen yang cuma nomor #1 di satu daftar saja.
- Hasil akhir diurutkan berdasarkan `fused_scores` (menurun), dipotong ke `top_k`, dan tiap dict hasil ditambah key `rrf_score` (skor fusion, berbeda dari `score` yang merupakan skor asli BM25/vector sebelum digabung).

**▶️ Jalankan & lihat hasilnya**

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

results = store.search_hybrid(query, query_embedding, top_k=5, candidate_pool=20)
for r in results:
    print(round(r['rrf_score'], 4), '-', r['text'][:70])
"
```

✅ **Indikator sukses**: tidak ada error, dan chunk `### 2.1 Untuk Nasabah Perorangan` (yang di Module 14 Bagian 9 baru muncul di `top_k=15` lewat vector search murni) sekarang seharusnya muncul jauh lebih tinggi — idealnya masuk `top_k=5` — karena BM25 menangkap kecocokan kata "syarat", "perorangan" secara eksak, ditambah sinyal semantik dari vector search.

<details>
<summary><strong>Pakai Claude Code? Salin prompt berikut, paste untuk eksekusi Langkah 3</strong></summary>

```
Tambah method search_hybrid() dengan Reciprocal Rank Fusion (RRF) di
VectorStore (Module 17, Tahap A, Langkah 3) — belum dipakai endpoint
apa pun.

GOAL:
- Di Nala/app/vector_store.py, tambah
  method search_hybrid(self, query_text: str, query_embedding:
  list[float], top_k: int = 3, candidate_pool: int = 20, rrf_k: int
  = 60) -> list[dict]:
  1. bm25_results = self.search_bm25(query_text, top_k=candidate_pool)
  2. vector_results = self.search(query_embedding, top_k=candidate_pool)
  3. Hitung fused_scores: dict[str, float] — untuk tiap daftar, untuk
     tiap (rank, hit) lewat enumerate(): fused_scores[hit["_id"]] +=
     1.0 / (rrf_k + rank + 1) (default 0.0 kalau belum ada).
  4. doc_lookup: dict[str, dict] menyimpan hit pertama kali ditemui
     per _id (pakai setdefault() untuk hasil vector supaya tidak
     menimpa versi BM25 yang sudah tersimpan).
  5. Urutkan _id berdasarkan fused_scores menurun, ambil top_k.
  6. Return list of dict = isi doc_lookup untuk tiap _id terpilih,
     ditambah key "rrf_score": fused_scores[_id].

CONTEXT:
- search_bm25() dan _id di search() sudah ditambahkan di Langkah 1-2.
- top_k default 3 tapi Module 18 nanti akan memanggil method ini
  dengan top_k=20 (candidate set untuk reranking) — desain method ini
  sudah harus mendukung top_k besar tanpa perubahan lagi.

GUARDRAIL:
- JANGAN ubah search() atau search_bm25() yang sudah ada.
- JANGAN sentuh app/main.py di langkah ini — itu Tahap B.
```

</details>

**📄 Kode lengkap Tahap A** (`app/vector_store.py`, versi setelah Module 17):

```python
from urllib.parse import quote

import httpx


class VectorStore:
    def __init__(self, base_url: str, index_name: str):
        self.base_url = base_url
        self.index_name = index_name

    def ensure_index(self, dims: int = 768) -> None:
        with httpx.Client() as client:
            check = client.head(f"{self.base_url}/{self.index_name}", timeout=10.0)
            if check.status_code == 200:
                return
            response = client.put(
                f"{self.base_url}/{self.index_name}",
                json={
                    "settings": {"index": {"knn": True}},
                    "mappings": {
                        "properties": {
                            "text": {"type": "text"},
                            "embedding": {
                                "type": "knn_vector",
                                "dimension": dims,
                            },
                            "metadata": {"type": "object"},
                        }
                    },
                },
                timeout=30.0,
            )
            response.raise_for_status()

    def index_document(
        self, doc_id: str, text: str, embedding: list[float], metadata: dict
    ) -> None:
        with httpx.Client() as client:
            response = client.put(
                f"{self.base_url}/{self.index_name}/_doc/{quote(doc_id, safe='')}",
                json={"text": text, "embedding": embedding, "metadata": metadata},
                params={"refresh": "true"},
                timeout=30.0,
            )
            response.raise_for_status()

    def search(self, query_embedding: list[float], top_k: int = 3) -> list[dict]:
        with httpx.Client() as client:
            response = client.post(
                f"{self.base_url}/{self.index_name}/_search",
                json={
                    "size": top_k,
                    "query": {
                        "knn": {"embedding": {"vector": query_embedding, "k": top_k}}
                    },
                },
                timeout=30.0,
            )
            response.raise_for_status()
            hits = response.json()["hits"]["hits"]
            return [
                {
                    "_id": hit["_id"],
                    "text": hit["_source"]["text"],
                    "score": hit["_score"],
                    "metadata": hit["_source"]["metadata"],
                }
                for hit in hits
            ]

    def search_bm25(self, query_text: str, top_k: int = 10) -> list[dict]:
        with httpx.Client() as client:
            response = client.post(
                f"{self.base_url}/{self.index_name}/_search",
                json={
                    "size": top_k,
                    "query": {"match": {"text": query_text}},
                },
                timeout=30.0,
            )
            response.raise_for_status()
            hits = response.json()["hits"]["hits"]
            return [
                {
                    "_id": hit["_id"],
                    "text": hit["_source"]["text"],
                    "score": hit["_score"],
                    "metadata": hit["_source"]["metadata"],
                }
                for hit in hits
            ]

    def search_hybrid(
        self,
        query_text: str,
        query_embedding: list[float],
        top_k: int = 3,
        candidate_pool: int = 20,
        rrf_k: int = 60,
    ) -> list[dict]:
        bm25_results = self.search_bm25(query_text, top_k=candidate_pool)
        vector_results = self.search(query_embedding, top_k=candidate_pool)

        fused_scores: dict[str, float] = {}
        doc_lookup: dict[str, dict] = {}

        for rank, hit in enumerate(bm25_results):
            fused_scores[hit["_id"]] = fused_scores.get(hit["_id"], 0.0) + 1.0 / (rrf_k + rank + 1)
            doc_lookup[hit["_id"]] = hit

        for rank, hit in enumerate(vector_results):
            fused_scores[hit["_id"]] = fused_scores.get(hit["_id"], 0.0) + 1.0 / (rrf_k + rank + 1)
            doc_lookup.setdefault(hit["_id"], hit)

        ranked_ids = sorted(fused_scores, key=fused_scores.get, reverse=True)[:top_k]
        return [
            {**doc_lookup[doc_id], "rrf_score": fused_scores[doc_id]}
            for doc_id in ranked_ids
        ]
```

### Tahap B — Ganti Pemanggilan di `/chat/stream`

**Langkah 4 — Ganti `vector_store.search()` jadi `vector_store.search_hybrid()`**

Di `app/main.py`, endpoint `/chat/stream` (satu-satunya endpoint chat NALA sejak Module 8, dibangun sebagai RAG chain di Module 13) memanggil:

```python
# SEBELUM (Module 13) — di dalam chat_stream()
query_embedding = embed_text(last_user_message, base_url=OLLAMA_BASE_URL)
results = vector_store.search(query_embedding, top_k=3)
```

Ganti jadi:

```python
# SESUDAH (Module 17) — di dalam chat_stream()
query_embedding = embed_text(last_user_message, base_url=OLLAMA_BASE_URL)
results = vector_store.search_hybrid(
    query_text=last_user_message,
    query_embedding=query_embedding,
    top_k=3,
)
```

Tidak ada yang lain berubah — blok `try/except httpx.HTTPError` di sekitarnya (fallback ke `NALA_SYSTEM_PROMPT_NO_CONTEXT`, lihat Module 13 Bagian 2.d) tetap sama persis, karena `search_hybrid()` bisa melempar `httpx.HTTPError` yang sama seperti `search()` (dua-duanya memanggil OpenSearch lewat `httpx`). `top_k=3` di module ini **belum** memakai `candidate_pool=20` secara sengaja — itu baru relevan mulai Module 18 begitu ada reranker yang bisa memanfaatkan kandidat sebanyak itu. Dengan `top_k=3`, `search_hybrid()` tetap mengambil 20 kandidat dari masing-masing metode di baliknya (default `candidate_pool=20`), tapi langsung memotong ke 3 teratas via RRF sebelum dikembalikan — cukup untuk manfaat hybrid search saja, sebelum reranking ditambahkan.

**▶️ Jalankan & lihat hasilnya**

```bash
docker compose up --build api
```

```bash
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Apa saja syarat pengajuan kredit untuk nasabah perorangan?"}]}'
```

✅ **Indikator sukses**: jawaban terasa lebih relevan dibanding sebelumnya, idealnya menyebut item konkret dari `### 2.1` (KTP, Kartu Keluarga, slip gaji, dst) — bandingkan dengan jawaban yang lebih umum/tidak lengkap yang didapat di Module 13 sebelum hybrid search ditambahkan, muncul bertahap seperti biasa (flag `-N`).

Tapi untuk pertanyaan spesifik ini, jawaban **belum tentu** sudah menyebut keempat item itu secara lengkap — hybrid search terbukti menaikkan peringkat chunk yang benar (dari #10-14 di vector murni jadi sekitar #8, lihat Bagian 8), tapi belum cukup untuk selalu masuk `top_k=3` di kasus keras ini. Kalau jawabannya masih bilang "tidak ditemukan informasi spesifik", itu **bukan tanda ada yang salah** — itu justru bukti grounding masih bekerja jujur (Module 13 Bagian 2.d), dan alasan kenapa Module 18 (reranking) berikutnya diperlukan. Lihat Bagian 7 untuk checklist lengkap sebelum lanjut ke Module 18.

<details>
<summary><strong>Pakai Claude Code? Salin prompt berikut, paste untuk eksekusi Langkah 4</strong></summary>

```
Ganti vector_store.search() jadi vector_store.search_hybrid() di
/chat/stream (Module 17, Tahap B, Langkah 4).

GOAL:
- Di Nala/app/main.py:
  - Di dalam fungsi chat_stream() (endpoint /chat/stream — satu-
    satunya endpoint chat NALA): ganti pemanggilan `results =
    vector_store.search(query_embedding, top_k=3)` jadi `results =
    vector_store.search_hybrid(query_text=last_user_message,
    query_embedding=query_embedding, top_k=3)`.

CONTEXT:
- search_hybrid() sudah ada di app/vector_store.py sejak Tahap A.
- Blok try/except httpx.HTTPError di sekitar pemanggilan ini TIDAK
  berubah — search_hybrid() melempar httpx.HTTPError yang sama
  seperti search().

GUARDRAIL:
- JANGAN ubah urutan argumen embed_text() atau logika fallback
  NALA_SYSTEM_PROMPT_NO_CONTEXT.
- JANGAN ubah endpoint /health, /, /upload.
- JANGAN ubah app/vector_store.py di langkah ini — sudah selesai di
  Tahap A.
```

</details>

**📄 Kode lengkap Tahap B** (bagian relevan `app/main.py` setelah Module 17 — hanya menunjukkan fungsi yang berubah, sisanya identik dengan akhir Module 13):

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
        results = vector_store.search_hybrid(
            query_text=last_user_message,
            query_embedding=query_embedding,
            top_k=3,
        )
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

### Troubleshooting

- **`search_hybrid()` melempar error field `text` tidak ditemukan / query `match` gagal**: index `nala-docs` yang dipakai kemungkinan dibuat sebelum field `text` ada di mapping (versi index yang sangat lama) — hapus dan buat ulang index (`curl -X DELETE http://localhost:9200/nala-docs`) lalu jalankan ulang `ingest_documents()` (lihat Prasyarat & Setup Sebelum Mulai di atas).
- **Port sudah dipakai (8000/9200/11434)**: ubah mapping port yang bentrok di `docker-compose.yml`, atau pastikan container lama sudah benar-benar dimatikan (`docker compose down` di `Nala`).
- **`docker compose exec ollama ollama list` tidak menampilkan model**: model belum pernah di-pull ke volume container ini — jalankan ulang `docker compose exec ollama ollama pull <nama-model>` (lihat Prasyarat & Setup Sebelum Mulai di atas).

## 7. Checkpoint Praktik

Langkah eksekusi lengkap ada di Bagian 6 di atas (Tahap A Langkah 1-3, Tahap B Langkah 4). Yang perlu dipastikan sebelum lanjut ke Module 18:

- [ ] `store.search_bm25()` mengembalikan hasil yang cocok kata kunci eksak dengan query
- [ ] `store.search_hybrid()` mengembalikan hasil yang berbeda urutannya dibanding `store.search()` murni, untuk query yang sama, dan skor `rrf_score` untuk chunk `### 2.1 Untuk Nasabah Perorangan` naik dibanding peringkatnya di `store.search()` murni (lihat Bagian 8 di bawah — belum tentu masuk `top_k=3`, itu wajar di titik ini)
- [ ] `/chat/stream` tetap streaming bertahap dan menjawab dengan kualitas yang lebih baik dibanding sebelum hybrid search ditambahkan

## 8. Hasil Uji Nyata: Perbaikan Terukur, Belum Tuntas

Pengujian langsung terhadap index `nala-docs` (13 chunk `sop-pengajuan-kredit.md`) untuk query *"Apa saja syarat pengajuan kredit untuk nasabah perorangan?"* memberi angka konkret, bukan cuma klaim teoretis:

| Metode | Peringkat chunk `### 2.1 Untuk Nasabah Perorangan` |
|---|---|
| Vector murni (`store.search()`) | #10 dari 14 |
| BM25 saja (`store.search_bm25()`) | **#4** dari 14 |
| Hybrid RRF (`store.search_hybrid()`) | #8 dari 14 |

BM25 sendirian, untuk kasus spesifik ini, sebenarnya mengungguli hasil gabungan RRF — bukan aneh, ini konsekuensi logis dari RRF: dokumen ini kuat secara lexical (peringkat #4) tapi tetap lemah secara semantic (peringkat #10), jadi skor RRF gabungannya "ditarik turun" oleh komponen vector yang masih rendah. Hasilnya: **`top_k=3` di `/chat/stream` masih belum cukup untuk pertanyaan spesifik ini** — chunk yang benar ada di posisi #8, bukan di 3 besar.

### Alat Bantu: Cek Posisi Chunk Tertentu di Ketiga Metode

Angka-angka di tabel atas didapat dari index dan isi dokumen tertentu — bisa berbeda di komputer Anda tergantung dokumen apa saja yang sudah ter-*ingest*. Daripada percaya begitu saja pada angka di materi, pakai *helper* ini untuk mengecek posisi chunk **apa pun** yang Anda harapkan, untuk pertanyaan **apa pun**:

```python
# Tempel fungsi ini sekali di sesi python -c, lalu panggil untuk query/potongan apa pun
def cari_posisi(query_text, query_embedding, potongan_teks, max_k=50):
    """Cari posisi (rank, 0-based) sebuah chunk di search(), search_bm25(), dan search_hybrid().

    potongan_teks: sepotong kalimat unik yang pasti ada di chunk yang dicari
    (mis. 'Fotokopi KTP') — dipakai untuk mengenali chunk yang benar di
    daftar hasil, bukan dibandingkan dengan skor.
    """
    metode = {
        "Vector murni": store.search(query_embedding, top_k=max_k),
        "BM25 saja": store.search_bm25(query_text, top_k=max_k),
        "Hybrid RRF": store.search_hybrid(query_text, query_embedding, top_k=max_k, candidate_pool=max_k),
    }
    for label, hasil in metode.items():
        posisi = next((i for i, r in enumerate(hasil) if potongan_teks in r["text"]), None)
        if posisi is None:
            print(f"{label}: tidak ditemukan di top-{max_k}")
        else:
            print(f"{label}: posisi #{posisi} dari {len(hasil)}")
```

Contoh pemakaian lengkap (bisa langsung disalin ke `docker compose exec api python -c "..."`):

```bash
docker compose exec api python -c "
from app.embeddings import embed_text
from app.vector_store import VectorStore

store = VectorStore(base_url='http://opensearch:9200', index_name='nala-docs')

def cari_posisi(query_text, query_embedding, potongan_teks, max_k=50):
    metode = {
        'Vector murni': store.search(query_embedding, top_k=max_k),
        'BM25 saja': store.search_bm25(query_text, top_k=max_k),
        'Hybrid RRF': store.search_hybrid(query_text, query_embedding, top_k=max_k, candidate_pool=max_k),
    }
    for label, hasil in metode.items():
        posisi = next((i for i, r in enumerate(hasil) if potongan_teks in r['text']), None)
        if posisi is None:
            print(f'{label}: tidak ditemukan di top-{max_k}')
        else:
            print(f'{label}: posisi #{posisi} dari {len(hasil)}')

query = 'Apa saja syarat pengajuan kredit untuk nasabah perorangan?'
query_embedding = embed_text(query, base_url='http://ollama:11434')
cari_posisi(query, query_embedding, 'Fotokopi KTP')
"
```

Ganti `query` dengan pertanyaan apa pun yang ingin dicoba, dan `'Fotokopi KTP'` dengan potongan teks unik dari chunk yang Anda harapkan muncul — cara ini jauh lebih cepat daripada scroll manual lewat puluhan baris hasil `print()` seperti yang dipakai di Bagian 7. `max_k=50` cukup besar untuk index saat ini yang masih berisi belasan-puluhan chunk; naikkan kalau index Anda sudah jauh lebih besar (banyak dokumen ter-*ingest*).

⚠️ **Jebakan umum — dua argumen ini gampang tertukar**: `query` (baris `query = '...'`) adalah **pertanyaan** yang mau dicari, sedangkan argumen ketiga `cari_posisi(query, query_embedding, '...')` adalah **potongan isi dokumen** yang diharapkan muncul di jawaban — bukan pertanyaannya lagi. Kalau keduanya tertukar (misal argumen ketiga ikut diisi pertanyaan, bukan potongan isi dokumen), hasilnya akan selalu "tidak ditemukan di top-N" untuk ketiga metode sekaligus — bukan berarti retrieval-nya gagal, tapi karena `potongan_teks` yang dicocokkan (`if potongan_teks in r["text"]`) memang tidak pernah muncul persis sebagai substring di teks chunk manapun. Kalau ketiga metode kompak "tidak ditemukan", curigai dulu argumen yang tertukar, baru curigai retrieval-nya.

Alat bantu yang sama ini juga berguna di Module 18 (mengecek apakah reranking benar-benar menaikkan posisi chunk yang diharapkan) dan Module 19 (dasar dari cara kerja framework evaluasi precision/recall/MRR) — jangan dihapus setelah dipakai di sini.

Ini bukan bug, dan bukan berarti Module 17 gagal — dibanding vector murni, hybrid search tetap terbukti menaikkan peringkat chunk yang benar (walau untuk kasus ini, tidak sebesar yang BM25 sendirian capai). Yang perlu dipahami jujur: RRF adalah kompromi yang tidak selalu optimal per-kasus — ia menyeimbangkan dua sinyal secara umum, bukan memilih "yang terbaik" untuk tiap query. Kasus keras seperti ini (dokumen kuat di satu sinyal, lemah di sinyal lain) adalah motivasi nyata untuk Module 18 (reranking), yang menilai relevansi tiap kandidat secara langsung — bukan mengombinasikan dua rank secara membabi buta.

## Kesimpulan

Module ini menutup celah yang secara eksplisit didokumentasikan sebagai keterbatasan di akhir Module 16: vector search murni bisa kalah oleh chunk pendek yang "kebetulan" mirip secara makna, padahal kecocokan kata kunci eksak justru menunjuk ke chunk yang benar. Hybrid search (BM25 + vector, digabung lewat RRF berbasis rank — bukan skor mentah yang rawan beda skala) memperbaiki ini **tanpa reindex** dan **tanpa mengubah kontrak endpoint** (`/chat/stream` tetap menerima/mengembalikan bentuk yang sama).

Yang belum diselesaikan (dan sudah dibuktikan langsung dengan angka di Bagian 8): hybrid search memperbaiki *recall* di level kandidat (dokumen yang benar kini punya peluang lebih besar masuk top-K yang lebih besar seperti `candidate_pool=20`), tapi belum tentu selalu menaruhnya di posisi #1-3 secara konsisten — kombinasi BM25+vector tetap heuristik berbasis rank, bukan penilaian relevansi langsung. Module 18 (Reranking) mengambil pool kandidat yang lebih besar (`candidate_pool=20`, sudah disiapkan di `search_hybrid()`) dan menyortirnya ulang pakai model yang secara khusus dilatih untuk menilai relevansi query-dokumen — dibahas berikutnya di Module 18.
