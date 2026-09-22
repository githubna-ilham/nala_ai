# Module 12: Vector Store — Menyalakan OpenSearch

## Tujuan

Menyiapkan **OpenSearch** sebagai vector store untuk NALA — memahami apa itu OpenSearch, kenapa dipilih dibanding alternatif lain, dan menyalakannya sehat di Docker Compose. Module ini fokus **infrastruktur**: OpenSearch benar-benar berjalan dan siap dipakai. Module 13 melanjutkan dari sini untuk membangun **semantic search** sungguhan di atasnya (metrik kemiripan, class `VectorStore`).

## Definisi

**Vector store** adalah sistem penyimpanan yang dioptimalkan untuk menyimpan dan mencari vektor secara efisien — NALA memakai **OpenSearch** untuk keperluan ini (Bagian 3), bukan database relasional biasa dengan tabel dan kolom. Kegunaan intinya: menjalankan **semantic search** (pencarian semantik) — mencari berdasarkan kemiripan **makna** vektor, bukan kecocokan kata kunci persis. Detail bagaimana "mirip" itu sebenarnya diukur (metrik matematis) dan bagaimana kode `VectorStore` NALA memanfaatkannya baru dibahas lengkap di Module 13 — di module ini, fokusnya dulu memahami **apa** OpenSearch itu dan **menyalakannya**.

```mermaid
flowchart LR
    A["Dokumen + embedding<br/>(Module 10-11)"] --> B["OpenSearch<br/>(vector store)"]
    B --> C["Siap dicari<br/>(Module 13: semantic search)"]
```

## Hasil Akhir yang Diharapkan

- OpenSearch berjalan sehat (`docker compose logs opensearch` menunjukkan cluster health `green`/`yellow`)
- `http://localhost:5601` (OpenSearch Dashboards) bisa dibuka di browser untuk menjelajahi isi OpenSearch secara visual
- Kita paham apa itu OpenSearch secara umum (asal-usulnya, konsep index/document, akses lewat REST API) — bukan cuma tahu cara memakainya
- Kita paham kenapa NALA akhirnya memilih OpenSearch dibanding alternatif lain
- `/chat/stream` (Module 7) tetap berfungsi seperti sebelumnya

## 1. Apa itu Vector Search / Vector Store

**Vector Search** adalah teknik pencarian yang memakai **kemiripan vektor** sebagai dasar menemukan dokumen relevan, bukan pencocokan kata kunci tradisional. **Vector Store** adalah database/sistem penyimpanan khusus yang dioptimalkan menyimpan dan mencari vektor secara efisien.

**Cara kerja vector search secara garis besar**: (1) pertanyaan pengguna diubah jadi vektor lewat model embedding yang sama (Module 11), (2) sistem menghitung kemiripan antara vektor query dan vektor dokumen yang tersimpan, (3) dokumen diurutkan berdasarkan skor kemiripan, (4) top-K dokumen/chunk paling relevan dikembalikan. Langkah (2) — **bagaimana** "kemiripan" itu sebenarnya dihitung, dan lanskap vector database di luar OpenSearch — dibahas detail di Module 13 Bagian 1-2. Di module ini, kita fokus dulu ke tempat penyimpanannya: OpenSearch itu sendiri.

## 2. Apa itu OpenSearch

Bayangkan OpenSearch sebagai **"mesin pencari pribadi"** — seperti Google, tapi bukan untuk mencari di seluruh internet, melainkan khusus mencari di dalam dokumen-dokumen milik NALA sendiri. Tugas utamanya dari dulu sampai sekarang sama: menerima jutaan dokumen, lalu menemukan dengan cepat mana yang paling relevan begitu ada pertanyaan masuk. Kemampuan "mencari berdasarkan kemiripan makna" (vector search, dibahas Module 13) sebenarnya **fitur tambahan** — kemampuan aslinya, sejak awal dibuat, adalah mencari dokumen berdasarkan **kata kunci** yang persis disebut, mirip cara kerja kolom pencarian di situs berita atau marketplace. Nama teknis "cara menilai kecocokan kata kunci" ini adalah **BM25** — sebuah rumus yang menghitung skor relevansi dokumen berdasarkan seberapa sering dan seberapa "penting" kata-kata pencarian muncul di dalamnya (dokumen yang mengandung kata langka/spesifik dari query dinilai lebih relevan daripada yang cuma mengandung kata umum) — istilah ini akan muncul lagi di Module 18 saat NALA menggabungkannya dengan vector search.

Asal-usulnya juga sederhana untuk dipahami: OpenSearch adalah "anak" dari produk bernama **Elasticsearch**. Beberapa tahun lalu, perusahaan pembuat Elasticsearch mengubah aturan pemakaiannya jadi lebih terbatas — komunitas dan Amazon (AWS) tidak setuju, lalu mereka meneruskan versi terakhir yang masih bebas dipakai siapa saja, dan memberinya nama baru: **OpenSearch**. Jadi kalau Anda pernah dengar nama Elasticsearch, anggap saja OpenSearch adalah versi "sepupu dekat"-nya — cara kerja dan istilah-istilahnya sangat mirip. Mesin pencarinya sendiri, jauh di dalam "mesin"-nya, dibangun di atas komponen bernama **Apache Lucene** — semacam "mesin mobil" generik yang dipakai bersama oleh OpenSearch, Elasticsearch, dan beberapa mesin pencari lain; OpenSearch dan Elasticsearch ibarat dua mobil berbeda merek yang kebetulan memakai mesin dasar yang sama.

Dua istilah yang perlu dikenal sebelum melihat kode di Bagian 4, dan keduanya sebenarnya konsep yang sudah akrab sehari-hari: **index** itu seperti satu **lemari arsip** — tempat menyimpan dokumen-dokumen yang sejenis (di NALA, satu lemari arsip bernama `nala-docs` menyimpan semua potongan dokumen SOP). **Document** itu seperti satu **lembar formulir** di dalam lemari arsip itu — satu formulir untuk satu potongan dokumen, isinya tiga kolom: teks aslinya, "sidik jari makna"-nya (vektor/embedding), dan keterangan tambahan (metadata). Untuk mengisi lemari arsip ini atau mencari isinya, NALA cukup "mengirim surat" lewat internet (disebut REST API) — tidak perlu aplikasi atau alat khusus, alasan kenapa NALA bisa berkomunikasi dengan OpenSearch memakai `httpx` yang sama dipakai untuk Ollama sejak Module 1-6.

⚠️ **Satu hal yang perlu diluruskan**: bukan berarti OpenSearch menyimpan formulir-formulir itu lalu membaca ulang **satu per satu** setiap kali ada pencarian — itu akan sangat lambat kalau dokumennya jutaan. Di belakang layar, begitu satu formulir masuk, OpenSearch diam-diam menyusun **daftar indeks/catatan bantuan** dari isinya (mirip daftar isi atau indeks di belakang buku tebal — makanya disebut "index") supaya pencarian berikutnya bisa langsung "lompat" ke bagian yang relevan, tanpa perlu membuka semua formulir satu-satu. Dua daftar bantuan ini punya nama teknis masing-masing, dan berbeda tergantung jenis pencariannya: untuk pencarian kata kunci (BM25), daftar bantuannya disebut **inverted index** — bayangkan seperti indeks di belakang buku tebal yang mendaftar "kata apa muncul di halaman berapa", cuma dibalik: bukan "halaman → kata apa saja isinya", tapi "kata apa → ada di dokumen mana saja". Untuk pencarian kemiripan makna (vector search, Module 13), daftar bantuannya disebut **HNSW** (*Hierarchical Navigable Small World*) — semacam peta jaringan pertemanan antar vektor, supaya OpenSearch bisa "meloncat" dari satu vektor ke vektor tetangganya yang mirip tanpa perlu membandingkan ke **semua** vektor yang ada satu-satu, mirip cara Anda menemukan kenalan lewat "teman dari teman" dibanding menghubungi semua orang di kota satu-satu. Formulir aslinya (JSON) tetap tersimpan utuh dan itulah yang dikembalikan sebagai hasil pencarian — cuma **cara mencarinya** yang sudah dioptimalkan lewat kedua struktur bantuan ini, bukan sekadar menyisir semua data dari atas ke bawah.

Satu istilah lagi yang muncul di konfigurasi Bagian 4: **cluster** dan **node** — anggap saja **node** itu satu "gedung kantor cabang" tempat OpenSearch bekerja, dan **cluster** adalah kumpulan beberapa gedung yang bekerja sama. Di lingkungan production sungguhan, biasanya dipakai beberapa gedung (node) sekaligus supaya kalau satu gedung bermasalah, gedung lain tetap bisa melayani, dan pekerjaannya juga terbagi rata. Untuk training ini, cukup **satu gedung saja** (`discovery.type=single-node`) — jauh lebih ringan buat laptop, dan cara kerjanya tetap sama persis dengan yang dipakai di lingkungan production sungguhan.

**Single-node** berarti cuma **satu** proses OpenSearch yang menyimpan **seluruh** data dan mengerjakan **seluruh** pencarian sendirian — kalau container ini mati, seluruh sistem pencarian ikut mati, tidak ada cadangan. **Multi-node** (cluster sungguhan) memecah satu index yang sama jadi beberapa potongan yang disebar ke beberapa node (disebut *sharding*), dan tiap potongan biasanya punya salinan/cadangan di node lain (disebut *replica*) — aplikasi tetap bicara ke "satu alamat cluster" seolah-olah itu satu mesin, tapi di baliknya permintaan pencarian otomatis dipecah, dikerjakan paralel di beberapa node, lalu hasilnya digabung. Kalau satu node mati, data yang tadi cuma ada di situ masih bisa diambil dari salinannya di node lain.

```mermaid
flowchart LR
    subgraph Single["Single-node (dipakai training ini)"]
        N1["Node tunggal<br/>seluruh data + seluruh pencarian"]
    end
    subgraph Multi["Multi-node / cluster (production skala besar)"]
        NA["Node A<br/>sebagian data + salinan data node lain"]
        NB["Node B<br/>sebagian data + salinan data node lain"]
        NC["Node C<br/>sebagian data + salinan data node lain"]
        NA --- NB --- NC
    end
```

**Apakah NALA perlu multi-node?** Tidak, untuk skala dan kebutuhannya sekarang:
- **Skala datanya kecil** — dokumen SOP/kebijakan internal, paling ratusan sampai ribuan chunk, bukan jutaan dokumen. Single-node sanggup menangani ini tanpa masalah performa.
- **Ini aplikasi internal, bukan layanan publik skala besar** — multi-node menyelesaikan masalah "banyak user mengakses bersamaan dalam jumlah besar" dan/atau "data terlalu besar untuk satu mesin". Staff yang memakai NALA jumlahnya terbatas, bukan jutaan user simultan.
- **High availability (HA) biasanya krusial untuk sistem yang tidak boleh down sama sekali** (misal sistem pembayaran real-time). Kalau OpenSearch NALA sempat down beberapa menit karena container di-restart, dampaknya cuma staff tidak bisa pakai chatbot sebentar — bukan kerugian finansial langsung. Kompleksitas setup multi-node (beberapa mesin/VM, jaringan antar node, koordinasi cluster) tidak sepadan dengan manfaatnya di skala ini.
- **Migrasi ke multi-node nanti, kalau memang dibutuhkan, tidak perlu mengubah kode aplikasi sama sekali** — `VectorStore` bicara ke OpenSearch lewat REST API biasa (`httpx`), endpoint-nya sama persis baik di belakangnya satu node atau sepuluh node. Yang berubah cuma konfigurasi infrastruktur, bukan `app/vector_store.py` (Module 13).

Jadi single-node di sini bukan "versi murah/kurang lengkap" — untuk skala dan kebutuhan NALA, itu memang pilihan yang tepat, bukan kompromi sementara.

```mermaid
flowchart TD
    subgraph OS["OpenSearch (single-node)"]
        I["Index: nala-docs"]
        I --> D1["Document<br/>{text, embedding, metadata}"]
        I --> D2["Document<br/>{text, embedding, metadata}"]
        I --> D3["... document lain"]
    end
    API["NALA (httpx)"] -->|"REST API HTTP"| OS
```

## 3. Kenapa Akhirnya OpenSearch untuk NALA

Vector database di luar OpenSearch bisa dikelompokkan jadi tiga kategori besar (dibahas lengkap dengan contoh dan analogi di **Module 13 Bagian 1**): (a) vector database khusus seperti Pinecone/Weaviate/Milvus/Qdrant/Chroma, (b) extension pada database yang sudah ada seperti pgvector untuk PostgreSQL, dan (c) search engine dengan kemampuan vector search seperti OpenSearch/Elasticsearch. NALA memilih **OpenSearch** — kategori (c) — bukan Pinecone/Weaviate/Milvus/Qdrant (kategori a) maupun pgvector (kategori b). Alasannya konkret, bukan sekadar "yang paling populer":

- **Dual Role, alasan paling menentukan**: di titik ini (Module 12) OpenSearch dipakai sebagai *pure vector store*; nanti (Module 18) bisa di-upgrade jadi *hybrid search* (BM25 keyword + vector) **tanpa mengganti infrastruktur** — satu platform untuk dua kebutuhan. Vector database khusus (kategori a) tidak punya kemampuan keyword search bawaan sekuat ini; kalau dipilih, Module 18 harus menambah **sistem search terpisah** di luar vector database-nya sendiri, lalu menggabungkan hasil keduanya secara manual — kompleksitas ekstra yang tidak perlu untuk skala training ini.
- **pgvector sempat jadi kandidat, tapi ditunda**: karena NALA nanti (Module 22) juga akan memakai PostgreSQL untuk data operasional, pgvector (kategori b) terlihat menarik supaya tidak perlu service tambahan. Tapi di Module 7-17 ini PostgreSQL belum ada sama sekali di stack NALA — menambahkannya di titik ini cuma untuk vector store berarti mengenalkan service baru yang lebih awal dari waktunya, dan performa pencarian vektornya pada skala data yang akan terus tumbuh (ribuan dokumen ke depan) kalah dibanding search engine yang memang dioptimalkan untuk ini.
- **Production-ready**: distribusi open-source dari Elasticsearch (AWS), battle-tested di enterprise, dokumentasi lengkap.
- **Security & control**: bisa dijalankan on-premises, kontrol penuh atas data dan privasi — konsisten dengan prinsip Module 1-4.
- **Integration ready**: OpenSearch punya REST API HTTP biasa — NALA mengaksesnya langsung lewat `httpx` (dependency yang sudah dipakai sejak Module 1-6 untuk Ollama), **bukan** library client resmi `opensearch-py`. Satu HTTP client dipakai konsisten untuk semua pemanggilan eksternal, tanpa menambah dependency baru.

Tidak ada satu kategori yang "paling benar" secara universal — pilihannya tergantung kebutuhan. NALA jatuh ke kategori (c) karena alasan-alasan di atas. Perbandingan lengkap ketiga kategori — termasuk analogi toko buku dan tabel trade-off — ada di **Module 13 Bagian 1**.

## 4. Struktur yang Ditambahkan: Service `opensearch` dan `opensearch-dashboards`

**Langkah 1 — Service `opensearch`**

```yaml
# docker-compose.yml
services:
  ollama:
    image: ollama/ollama:latest
    ports:
      - '11434:11434'
    volumes:
      - ollama_data:/root/.ollama

  opensearch:
    image: opensearchproject/opensearch:2.11.0
    environment:
      - discovery.type=single-node
      - plugins.security.disabled=true
      - OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx512m
      - DISABLE_INSTALL_DEMO_CONFIG=true
    ports:
      - '9200:9200'
    volumes:
      - opensearch_data:/usr/share/opensearch/data

  api:
    build: .
    ports:
      - '8000:8000'
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434
      - OLLAMA_MODEL=llama3.2:3b
      - KNOWLEDGE_BASE_PATH=/app/knowledge-base
      - OPENSEARCH_BASE_URL=http://opensearch:9200
    volumes:
      - ./knowledge-base:/app/knowledge-base
    depends_on:
      - ollama
      - opensearch

volumes:
  ollama_data:
  opensearch_data:
```

- **`discovery.type=single-node`**: OpenSearch normalnya didesain untuk cluster banyak node — flag ini bilang "cuma ada 1 node", supaya tidak menunggu node lain yang tidak akan pernah muncul.
- **`plugins.security.disabled=true`**: mematikan autentikasi/TLS bawaan, wajar untuk lingkungan training lokal supaya `httpx` bisa langsung `PUT`/`POST` tanpa perlu setup certificate/credential.
- **`DISABLE_INSTALL_DEMO_CONFIG=true`**: mencegah OpenSearch **menginstall konfigurasi keamanan demo** saat pertama kali start — normalnya (tanpa flag ini), OpenSearch otomatis membuat sertifikat TLS demo dan user default (`admin`/`admin`, password bawaan yang sudah dikenal publik) sebagai bagian dari setup awal plugin security. Flag ini relevan meski `plugins.security.disabled=true` sudah mematikan plugin-nya, karena dua alasan: (1) *belt-and-suspenders* — proses instalasi demo config bisa saja tetap berjalan duluan sebelum plugin itu benar-benar nonaktif, flag ini mencegah langkah instalasinya sama sekali, bukan cuma menonaktifkan hasilnya; (2) startup lebih cepat dan bersih — generate sertifikat + setup user demo butuh waktu dan menghasilkan log tambahan setiap kali container start, overhead yang tidak perlu untuk training lokal yang memang tidak butuh autentikasi sama sekali. Tidak relevan untuk production (yang justru harus mengaktifkan security sungguhan, bukan mematikannya).
- **`OPENSEARCH_BASE_URL=http://opensearch:9200`** di service `api`: env var baru, disiapkan untuk dibaca `VectorStore` yang baru dibangun di Module 13 — belum ada kode yang memakainya di module ini.

**▶️ Jalankan & lihat hasilnya**

> **Prasyarat RAM**: pastikan alokasi RAM Docker Desktop sudah dinaikkan ke 16GB+ (lihat Module 7, bagian setup — catatan RAM) sebelum menyalakan OpenSearch di langkah ini. OpenSearch cukup berat untuk RAM Docker yang mepet.

```bash
docker compose up -d --build opensearch
```

Flag `-d` (detached) supaya tidak perlu buka terminal baru — service ini jalan di background, sementara terminal `ollama`+`api` (Module 7) tetap seperti semula. **Proses ini akan terasa lama** — OpenSearch butuh waktu untuk inisialisasi cluster single-node. Jangan panik kalau terlihat "diam" beberapa menit.

Tunggu OpenSearch siap:

```bash
docker compose logs -f opensearch
```

Tunggu sampai muncul log cluster health `green` atau `yellow` (bukan `red`), lalu `Ctrl+C` untuk keluar dari `logs -f` (service tetap jalan di background). Rebuild `api` supaya `OPENSEARCH_BASE_URL` (env var baru dari module ini) ter-load:

```bash
docker compose up --build -d api
```

✅ **Indikator sukses**: `docker compose logs opensearch` menunjukkan cluster health `green`/`yellow` (bukan `red`), dan `docker compose ps` menunjukkan `opensearch` berstatus `running`/`healthy`. Belum ada kode Python yang memanggil OpenSearch — itu baru terjadi di Module 13, begitu class `VectorStore` dibangun.

**Troubleshooting**

- **OpenSearch gagal start / restart terus / error terkait `vm.max_map_count`**: OpenSearch butuh `vm.max_map_count` minimal 262144 di level OS host, sementara default macOS/Windows (lewat Docker Desktop VM) sering lebih rendah. Perbaiki dengan menjalankan (sekali saja, akan reset lagi setelah restart Docker Desktop/laptop):
  ```bash
  docker run --rm --privileged --pid=host alpine sysctl -w vm.max_map_count=262144
  ```
  Setelah itu jalankan ulang `docker compose up -d --build opensearch`. Error yang sama juga bisa muncul saat menyalakan `airflow` (Module 17) — perbaikannya identik.
- **Semua service terasa sangat lambat / laptop panas / container ter-*kill***: kemungkinan besar alokasi RAM Docker Desktop kurang — lihat catatan Prasyarat RAM di atas dan Module 7. Cek pemakaian resource real-time dengan `docker stats`.
- **Port sudah dipakai (8000/9200/11434)**: ubah mapping port di `docker-compose.yml` untuk service yang bentrok.

<details>
<summary><strong>Pakai Claude Code? Salin prompt berikut, paste untuk eksekusi Langkah 1</strong></summary>

```
Tambah service opensearch di docker-compose.yml NALA (Module 12) —
BELUM membuat kode Python apa pun.

GOAL:
- Di Nala/docker-compose.yml: tambah
  service baru `opensearch` (image opensearchproject/opensearch:2.11.0,
  environment discovery.type=single-node,
  plugins.security.disabled=true,
  OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx512m,
  DISABLE_INSTALL_DEMO_CONFIG=true, port 9200:9200, volume
  opensearch_data:/usr/share/opensearch/data), tambah
  `- OPENSEARCH_BASE_URL=http://opensearch:9200` ke environment
  service `api`, tambah `opensearch` ke depends_on service `api`, dan
  tambah `opensearch_data:` ke top-level volumes.

CONTEXT:
- Env var OPENSEARCH_BASE_URL disiapkan untuk dibaca class VectorStore
  yang baru dibangun di Module 13 — belum ada kode yang memakainya
  di module ini.

GUARDRAIL:
- JANGAN buat app/vector_store.py di langkah ini — itu Module 13.
- JANGAN ubah service ollama atau api selain menambah environment
  dan depends_on yang disebutkan.
- JANGAN tambah service airflow — itu baru masuk Module 17.
```

</details>

**Langkah 2 — Service `opensearch-dashboards` (UI visual untuk OpenSearch)**

Sejauh ini, satu-satunya cara "melihat" isi OpenSearch adalah lewat `curl`/Postman — cukup untuk verifikasi cepat, tapi tidak praktis untuk menjelajahi data atau menulis query lebih rumit. **OpenSearch Dashboards** (setara Kibana) memberi tampilan web visual: **Dev Tools** untuk menulis & menjalankan query langsung dari browser, dan **Discover** untuk menelusuri isi index per baris tanpa perlu mengetik query sama sekali. Tambahkan sebagai service baru di `docker-compose.yml`, sejajar dengan `opensearch`:

```yaml
  opensearch-dashboards:
    image: opensearchproject/opensearch-dashboards:2.11.0
    environment:
      - 'OPENSEARCH_HOSTS=["http://opensearch:9200"]'
      - DISABLE_SECURITY_DASHBOARDS_PLUGIN=true
    ports:
      - '5601:5601'
    depends_on:
      - opensearch
```

- **`OPENSEARCH_HOSTS`**: memberi tahu Dashboards di mana OpenSearch-nya — pakai hostname `opensearch` (nama service di Docker Compose network), bukan `localhost`, karena Dashboards mengaksesnya dari **dalam** container lain, bukan dari laptop Anda.
- **`DISABLE_SECURITY_DASHBOARDS_PLUGIN=true`**: pasangan dari `plugins.security.disabled=true` di service `opensearch` — Dashboards juga punya plugin security sendiri yang harus dimatikan senada, supaya tidak minta login padahal OpenSearch di baliknya sudah tanpa autentikasi sama sekali.
- **`depends_on: opensearch`**: Dashboards tidak ada gunanya kalau OpenSearch-nya sendiri belum menyala — urutan start dijamin, walau (seperti biasa) `depends_on` tanpa `condition` cuma menjamin urutan *start*, bukan urutan *siap* (dibahas lebih detail nanti di Module 27).
- **Tambahan RAM**: ~512MB-1GB di atas kebutuhan `opensearch` sendiri — total alokasi RAM Docker Desktop 16GB+ (Module 7) sudah memperhitungkan ini.

**▶️ Jalankan & lihat hasilnya**

```bash
docker compose up -d --build opensearch-dashboards
```

Tunggu sampai siap (biasanya lebih cepat dari `opensearch` sendiri):

```bash
docker compose logs -f opensearch-dashboards
```

Tunggu sampai muncul log semacam `Server running at http://0.0.0.0:5601`, lalu `Ctrl+C`. Buka `http://localhost:5601` di browser — halaman OpenSearch Dashboards akan muncul (skip langkah "create tenant"/login kalau muncul, karena security plugin sudah dimatikan).

✅ **Indikator sukses**: `http://localhost:5601` terbuka di browser tanpa error, dan lewat menu **Dev Tools** Anda bisa menjalankan `GET nala-docs/_count` (setelah index `nala-docs` dibuat di Module 13) dan melihat hasilnya langsung di layar, tanpa terminal.

<details>
<summary><strong>Pakai Claude Code? Salin prompt berikut, paste untuk eksekusi Langkah 2</strong></summary>

```
Tambah service opensearch-dashboards di docker-compose.yml NALA
(Module 12, Langkah 2) — BELUM membuat kode Python apa pun.

GOAL:
- Di Nala/docker-compose.yml: tambah service baru
  `opensearch-dashboards` (image
  opensearchproject/opensearch-dashboards:2.11.0, environment
  OPENSEARCH_HOSTS=["http://opensearch:9200"] dan
  DISABLE_SECURITY_DASHBOARDS_PLUGIN=true, port 5601:5601,
  depends_on: opensearch).

CONTEXT:
- Service opensearch sudah ada dari Langkah 1 — opensearch-dashboards
  cuma UI visual tambahan untuk melihat isinya, tidak dipanggil oleh
  kode Python NALA sama sekali.

GUARDRAIL:
- JANGAN ubah service opensearch, api, atau ollama.
- JANGAN tambah volume baru — opensearch-dashboards tidak menyimpan
  data sendiri, semua datanya ada di opensearch.
```

</details>

## 5. Checkpoint Praktik

Yang perlu dipastikan sebelum lanjut ke Module 13:

- [ ] `docker compose logs opensearch` menunjukkan cluster health `green`/`yellow`, bukan `red`
- [ ] `http://localhost:5601` (OpenSearch Dashboards) terbuka di browser tanpa error
- [ ] Kita paham OpenSearch pada dasarnya adalah full-text search engine (fork open-source Elasticsearch) yang belakangan ditambahi kemampuan vector search — bukan produk yang dari awal dibangun cuma untuk vektor
- [ ] Kita bisa menjelaskan konsep index dan document di OpenSearch, dan kenapa NALA mengaksesnya lewat REST API HTTP biasa (`httpx`), bukan library client khusus
- [ ] Kita paham alasan utama NALA memilih OpenSearch dibanding vector database khusus atau pgvector
- [ ] `/chat/stream` (Module 7) masih berfungsi seperti sebelumnya

Begitu keenam hal ini terverifikasi, lanjut ke Module 13 — membangun **semantic search** sungguhan di atas OpenSearch yang sudah menyala ini: memahami metrik kemiripan (cosine similarity, L2, dot product) dan membangun class `VectorStore` yang menyambungkan embedding (Module 11) ke OpenSearch (module ini).
