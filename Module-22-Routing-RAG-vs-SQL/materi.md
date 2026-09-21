# Module 22: Routing — Menggabungkan RAG + SQL Tool dalam Satu Agent

## Tujuan

Memahami dan menguji bagaimana agent NALA memilih antara tool RAG (Module 20) dan tool SQL (Module 21) — termasuk kasus yang butuh keduanya secara berurutan dan kasus ambigu yang salah pilih — lalu menambahkan pengaman batas putaran tool supaya kegagalan routing tidak berujung loop tanpa henti.

## Definisi

**Routing**, di sini, bukan komponen kode terpisah yang ditulis khusus — ia adalah nama untuk keputusan yang sudah diam-diam terjadi setiap kali node `call_model` dipanggil (Module 20): LLM membaca pertanyaan dan `description` tiap tool, lalu memutuskan mau pakai tool RAG (`cari_dokumen_sop`), tool SQL (`query_data_operasional`), keduanya secara berurutan, atau tidak sama sekali. Secara umum, tool RAG cocok untuk pertanyaan tentang **aturan/prosedur** yang jawabannya statis dan tertulis di dokumen, sementara tool SQL cocok untuk pertanyaan tentang **status/jumlah/data transaksi** yang berubah setiap hari dan tidak pernah ditulis di dokumen mana pun — dua sumber jawaban yang saling melengkapi, bukan saling menggantikan.

Karena keputusan ini sepenuhnya bergantung pada kemampuan model membaca maksud pertanyaan (bukan aturan `if/else` yang pasti benar), routing bisa **salah** — model kecil seperti `llama3.2:3b` kadang memilih tool yang tidak tepat untuk pertanyaan ambigu. Module ini juga menambahkan pengaman **batas putaran tool** (`MAX_TOOL_ROUNDS`): kalau model terus-menerus meminta tool tanpa pernah berhenti, agent dipaksa menjawab dengan apa yang sudah ada lewat node `force_answer`, supaya kegagalan routing paling buruk sekalipun tidak berujung request yang menggantung tanpa batas.

```mermaid
flowchart TD
    Q["Pertanyaan"] --> D{"LLM membaca description<br/>tiap tool"}
    D -->|"aturan/prosedur"| RAG["Tool RAG"]
    D -->|"status/jumlah/data"| SQL["Tool SQL"]
    D -->|"tidak ada sinyal"| NONE["Jawab langsung"]
    RAG --> LOOP["Kembali ke call_model"]
    SQL --> LOOP
    LOOP -->|"putaran > MAX_TOOL_ROUNDS"| FA["force_answer"]
```

## Hasil Akhir yang Diharapkan

- Kita sudah mencoba dan mencatat hasil routing untuk berbagai skenario pertanyaan (satu tool RAG, satu tool SQL, butuh keduanya, tanpa tool, dan pertanyaan ambigu)
- Kita paham bahwa routing sepenuhnya keputusan LLM berdasarkan `description` skema tool, bukan aturan `if/else` yang ditulis manual — dan bahwa model kecil (`llama3.2:3b`) bisa salah pilih, ini keterbatasan yang jujur diakui, bukan bug
- Agent punya pengaman `MAX_TOOL_ROUNDS` + node `force_answer`: kalau model terus meminta tool melebihi batas putaran, agent dipaksa menjawab dengan apa yang sudah ada, bukan berjalan tanpa batas
- Pengaman ini sudah dicoba dipicu dengan `MAX_TOOL_ROUNDS` diturunkan sementara ke `1` — dan kita paham bahwa memicunya secara organik dengan `llama3.2:3b` ternyata sulit (lihat Bagian 6.b), sehingga verifikasi logikanya dilakukan juga langsung di level kode, bukan cuma lewat pengamatan end-to-end
- Tidak ada regresi pada pertanyaan sederhana satu-tool dari Module 20-21

## 1. Kenapa "Routing" Bukan Fitur Baru yang Perlu Dibangun dari Nol

Ini kemungkinan module paling ringan dari sisi kode baru di rangkaian Module 19-23, dan itu disengaja: graph LangGraph yang dibangun di Module 20 (`call_model` → `should_continue` → `call_tool`/`END`, dengan `call_tool` selalu kembali ke `call_model`) **sudah** mendukung dua tool tanpa perubahan struktural sejak Module 21 mendaftarkan `SQL_TOOL_SCHEMA` di samping `RAG_TOOL_SCHEMA`. "Routing" di sini bukan komponen kode terpisah yang harus ditulis — ia adalah **keputusan yang diambil model** setiap kali `call_model` dipanggil, berdasarkan `description` di skema tiap tool (Module 20 Bagian 4 Tahap B, Module 21 Bagian 3 Tahap C) dan isi percakapan sejauh itu.

Yang dibangun di module ini bukan mekanisme routing baru, tapi tiga hal yang justru lebih penting untuk sistem produksi: **memahami** bagaimana keputusan itu diambil, **menguji** dengan pertanyaan yang mewakili tiap skenario (termasuk yang seharusnya butuh dua tool sekaligus), dan **menambahkan pengaman** untuk kasus ketika keputusan itu meleset atau berulang tanpa henti.

```mermaid
flowchart TD
    Q["Pertanyaan user"] --> M{"call_model:<br/>llama3.2:3b menganalisis"}
    M -->|"'syarat', 'prosedur',<br/>'kebijakan', 'bagaimana caranya'"| RAG["Tool: cari_dokumen_sop"]
    M -->|"'berapa', 'status',<br/>'nasabah mana', angka"| SQL["Tool: query_data_operasional"]
    M -->|"kedua sinyal muncul<br/>(mis. 'kenapa ditolak')"| BOTH["Panggil SQL dulu,<br/>lalu RAG di putaran berikutnya<br/>(loop call_tool → call_model)"]
    M -->|"tidak ada sinyal keduanya<br/>(sapaan, obrolan umum)"| NONE["Tanpa tool,<br/>jawab langsung"]
    RAG --> M
    SQL --> M
    BOTH --> M
```

## 2. Contoh Pertanyaan per Skenario

Tabel ini dipakai sebagai bahan uji coba di Langkah 1 — bukan aturan `if/else` yang ditulis di kode mana pun, murni prediksi berdasarkan `description` tiap tool (lihat kembali isi `RAG_TOOL_SCHEMA`/`SQL_TOOL_SCHEMA` di Module 20-21 untuk melihat kenapa model "seharusnya" memilih begini):

| Pertanyaan | Ekspektasi tool | Kenapa |
|---|---|---|
| "Apa saja syarat pengajuan kredit untuk nasabah perorangan?" | `cari_dokumen_sop` saja | Menanyakan **aturan/prosedur** — persis yang disebut `description` RAG tool |
| "Berapa banyak pengajuan kredit yang statusnya pending minggu ini?" | `query_data_operasional` saja | Menanyakan **jumlah/status transaksi** — persis yang disebut `description` SQL tool |
| "Bagaimana status klaim asuransi nasabah N-00087?" | `query_data_operasional` saja | Data spesifik satu nasabah, bukan prosedur umum |
| "Kenapa pengajuan kredit nasabah N-00305 ditolak?" | **Keduanya** — `query_data_operasional` (ambil `alasan_penolakan`, lihat data seed Module 21) lalu bisa jadi `cari_dokumen_sop` (kalau user lanjut bertanya "apa syarat supaya bisa diterima") | Butuh data transaksi spesifik dulu, baru (kalau perlu) konteks kebijakan |
| "Halo, kamu siapa?" | Tidak ada tool | Sapaan, tidak menyentuh dokumen atau data operasional |
| "Apa itu bunga majemuk?" | Tidak ada tool (idealnya) — atau NALA menjawab bahwa ini di luar cakupan | Di luar domain SOP/data operasional PT Nusantara Finance — lihat `NALA_SYSTEM_PROMPT_AGENT` (Module 20 Bagian 4 Langkah 4) yang membatasi topik |

## 3. Skenario "Butuh Dua Tool": Kenapa Graph yang Sudah Ada Cukup

Ambil baris keempat tabel di atas — "Kenapa pengajuan kredit nasabah N-00305 ditolak?" — sebagai contoh konkret alur multi-tool:

1. `call_model` menerima pertanyaan, memutuskan perlu `query_data_operasional(tabel="pengajuan_kredit", mode="detail_nasabah", nasabah_id="N-00305")` untuk tahu **status dan alasan penolakan** (ada di kolom `alasan_penolakan`, data seed Module 21: *"Skor kredit di bawah ambang batas minimum"*).
2. `call_tool` menjalankan tool itu, hasilnya (termasuk `alasan_penolakan`) masuk ke state sebagai pesan `role: "tool"`, lalu **kembali ke `call_model`** (edge `call_tool → call_model` dari Module 20 — inilah yang membuat alur multi-langkah mungkin tanpa kode tambahan).
3. `call_model` dipanggil lagi, sekarang dengan hasil tool sudah ada di riwayat. Kalau modelnya cukup baik, ia langsung merangkai jawaban dari data itu ("ditolak karena skor kredit di bawah ambang batas"). Kalau user lanjut bertanya "skor kredit minimum berapa?", model **bisa** memutuskan memanggil `cari_dokumen_sop` di putaran berikutnya untuk mencari angka itu di SOP — dua tool dipakai berurutan, dalam dua putaran graph yang terpisah, bukan satu pemanggilan simultan.

Tidak ada baris kode baru yang wajib ditambahkan untuk skenario ini — inilah nilai dari desain edge kondisional Module 20: `call_model` bisa dipanggil berkali-kali, tiap kali dengan riwayat yang makin lengkap, sampai ia memutuskan `should_continue` mengembalikan `END`.

## 4. Kejujuran: Routing Bisa Salah, dan Itu Bukan Bug

Model kecil (`llama3.2:3b`) yang menjalankan keputusan ini **tidak selalu** memilih tool yang tepat. Ini bukan cacat implementasi — ini keterbatasan nyata model berukuran kecil dalam membaca maksud pertanyaan yang ambigu, dan perlu kita akui apa adanya, bukan ditutup-tutupi.

### a. Kasus gagal yang realistis untuk dicoba

**Langkah 1 — Uji pertanyaan ambigu, amati routing-nya**

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Kredit saya gimana?"}'
```

Pertanyaan ini secara sengaja tidak jelas: "kredit saya gimana" bisa berarti "apa status pengajuan saya" (butuh `query_data_operasional`, tapi **tidak ada `nasabah_id`** yang disebutkan — model tidak tahu "saya" ini siapa) atau "bagaimana prosedurnya" (`cari_dokumen_sop`). Coba amati salah satu dari tiga kemungkinan hasil:

- Model memilih `query_data_operasional` tanpa `nasabah_id` yang valid → tool mengembalikan pesan error ("nasabah_id wajib diisi") → NALA idealnya lanjut bertanya balik "boleh sebutkan ID nasabah Anda?" (kalau `NALA_SYSTEM_PROMPT_AGENT` cukup jelas mengarahkan ke situ) — **atau** malah menjawab generik seolah tidak ada masalah, yang kurang membantu.
- Model memilih `cari_dokumen_sop` dan menjawab dari SOP umum, mengabaikan bahwa user kemungkinan menanyakan status pribadi.
- Model tidak memanggil tool sama sekali dan minta klarifikasi langsung — sebenarnya respons paling aman, tapi tidak dijamin terjadi.

✅ **Indikator untuk dicatat** (bukan "sukses"/"gagal" tunggal — tujuannya observasi): catat tool mana (kalau ada) yang dipanggil, apakah error tool tertangani dengan baik, apakah jawaban akhirnya membantu atau menyesatkan. Ini bahan diskusi kelas, bukan sesuatu yang "harus diperbaiki sampai selalu benar" — beberapa ambiguitas memang tidak bisa diselesaikan tanpa informasi tambahan dari user (di sinilah RBAC/audit Module 23 juga relevan: idealnya `nasabah_id` datang dari sesi login yang terautentikasi, bukan ditanyakan ke LLM lewat teks bebas — lihat Module 23 Bagian 2).

### b. Mitigasi yang bisa dilakukan (dan batasnya)

**Langkah 2 — Perbaiki `description` tool supaya sinyal lebih tajam**

Kalau routing salah tampak sering terjadi ke arah yang bisa diprediksi, salah satu langkah termurah adalah memperjelas `description` di `RAG_TOOL_SCHEMA`/`SQL_TOOL_SCHEMA` (lihat kembali Module 20-21) — description **adalah** sinyal utama yang dipakai model untuk membedakan tool, jadi kalimat yang lebih spesifik biasanya membantu. Contoh perbaikan kecil di `SQL_TOOL_SCHEMA`:

```python
# app/tools/sql_tool.py — perbaikan description, opsional
"description": (
    "Mengambil data operasional PT Nusantara Finance — pengajuan kredit atau "
    "klaim asuransi milik nasabah tertentu, atau ringkasan jumlah berdasarkan "
    "status. WAJIB dipakai untuk pertanyaan yang menyebut kata seperti 'status', "
    "'berapa banyak', 'sudah diproses belum', atau menyebut ID nasabah. JANGAN "
    "dipakai untuk pertanyaan tentang syarat/prosedur/kebijakan umum — itu tugas "
    "tool cari_dokumen_sop."
),
```

Menambahkan kata kunci eksplisit ("WAJIB dipakai untuk...", "JANGAN dipakai untuk...") sering membantu model kecil, tapi **bukan jaminan** — ini bukan aturan `if/else` yang dieksekusi pasti, description tetap cuma teks yang "dibaca" model sebagai konteks tambahan, keputusan akhirnya tetap probabilistik.

**Langkah 3 — Kalau akurasi routing tetap kurang memadai: opsi upgrade model**

Sesuai catatan di README utama bagian "Rekomendasi Model LLM": `llama3.2:3b` dipilih sebagai default sepanjang training karena constraint RAM total stack (bukan cuma LLM) yang berjalan bersamaan di laptop kita (Ollama + OpenSearch + PostgreSQL + Airflow + FastAPI + LangGraph + Langfuse). Kalau setelah Langkah 1-2 akurasi routing dua-tool ini **masih** terasa kurang memadai untuk demo/capstone, dan laptop kita punya **RAM 32GB+**, `qwen2.5:7b` bisa dicoba sebagai alternatif opsional:

```bash
docker compose exec ollama ollama pull qwen2.5:7b
```

Lalu ganti env var `OLLAMA_MODEL` di `docker-compose.yml` (service `api`) dari `llama3.2:3b` ke `qwen2.5:7b`, `docker compose up --build api` ulang. Ini **bukan** default — hanya catatan tambahan kalau spesifikasi laptop kita memungkinkan, persis seperti yang digariskan README utama. Model yang lebih besar umumnya lebih baik membaca maksud pertanyaan ambigu, tapi trade-off RAM-nya nyata: sebaiknya jangan dipakai kalau laptop kita masih pas-pasan di 16GB, terutama kalau Module 24-27 nanti menyalakan seluruh stack production sekaligus.

## 5. Pengaman: Batas Putaran Tool (Mencegah Loop Tanpa Henti)

Ada satu risiko teknis yang belum dibahas dari graph Module 20-21: `call_tool` selalu kembali ke `call_model`, dan tidak ada yang mencegah model meminta tool **berkali-kali tanpa henti** (mis. karena tool mengembalikan hasil yang menurut model kurang meyakinkan, ia mencoba lagi dengan argumen sedikit berbeda, berulang). Ini nyata bisa terjadi pada model kecil yang kurang percaya diri pada satu hasil tool. Tambahkan pengaman sederhana:

**Langkah 4 — Tambah batas putaran tool di `app/agent.py`**

```python
# app/agent.py — tambahan
MAX_TOOL_ROUNDS = 3


def _count_tool_rounds(messages: list[dict]) -> int:
    return sum(1 for m in messages if m.get("role") == "tool")
```

Di dalam `build_agent(...)`, tambahkan node `force_answer` dan perbarui `should_continue`:

```python
# app/agent.py — di dalam build_agent(), tambahan/perubahan
    def force_answer(state: AgentState) -> dict:
        response_message = ollama_client.chat(state["messages"])  # tanpa parameter tools
        return {"messages": [response_message]}

    def should_continue(state: AgentState) -> str:
        last_message = state["messages"][-1]
        if last_message.get("tool_calls"):
            if _count_tool_rounds(state["messages"]) >= MAX_TOOL_ROUNDS:
                return "force_answer"
            return "call_tool"
        return END

    graph = StateGraph(AgentState)
    graph.add_node("call_model", call_model)
    graph.add_node("call_tool", call_tool)
    graph.add_node("force_answer", force_answer)
    graph.set_entry_point("call_model")
    graph.add_conditional_edges(
        "call_model",
        should_continue,
        {"call_tool": "call_tool", "force_answer": "force_answer", END: END},
    )
    graph.add_edge("call_tool", "call_model")
    graph.add_edge("force_answer", END)
```

- **`_count_tool_rounds`**: menghitung berapa kali pesan `role: "tool"` sudah muncul di riwayat — proxy sederhana untuk "berapa putaran tool sudah dilewati" (bukan berapa banyak tool dipanggil per putaran, kalau model minta dua tool sekaligus dalam satu `tool_calls`, itu tetap dihitung sebagai penambahan ke jumlah pesan tool, wajar untuk batas pengaman yang tidak perlu presisi sempurna).
- **`force_answer`**: dipanggil kalau batas `MAX_TOOL_ROUNDS` (3) tercapai **dan** model masih ingin memanggil tool lagi — memanggil `ollama_client.chat()` **tanpa** parameter `tools`, memaksa model menjawab dengan apa pun yang sudah ada di riwayat, tidak diberi opsi memanggil tool lagi sama sekali di putaran ini.
- **`graph.add_edge("force_answer", END)`**: `force_answer` selalu berakhir di `END` — tidak ada jalan untuk masuk ke loop tool lagi setelahnya.

Ini keputusan desain yang jujur, bukan solusi sempurna: `force_answer` bisa saja menghasilkan jawaban yang kurang lengkap (model dipaksa menjawab walau merasa datanya kurang) — tapi trade-off ini diterima karena **lebih baik jawaban kurang lengkap daripada request yang menggantung tanpa batas** (dan berpotensi memicu banyak query database/embedding berulang tanpa manfaat).

**▶️ Jalankan & lihat hasilnya**

```bash
docker compose up --build api
```

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Berapa banyak pengajuan kredit yang statusnya pending?"}'
```

✅ **Indikator sukses**: jawaban tetap benar seperti Module 21 (pertanyaan ini normalnya cuma butuh 1 putaran tool, jauh di bawah `MAX_TOOL_ROUNDS=3`, jadi `force_answer` seharusnya tidak pernah terpanggil di kasus ini — buktikan tidak ada regresi). Untuk benar-benar menguji `force_answer`, sengaja turunkan `MAX_TOOL_ROUNDS` ke `1` sementara, lalu ulangi pertanyaan yang butuh dua tool (baris keempat tabel Bagian 2) — amati bahwa NALA tetap memberi jawaban (bukan macet/timeout) walau mungkin kurang lengkap karena dipotong setelah 1 putaran. Kembalikan `MAX_TOOL_ROUNDS` ke `3` setelah percobaan ini.

<details>
<summary><strong>Pakai Claude Code? Salin prompt berikut, paste untuk eksekusi Langkah 4</strong></summary>

```
Tambah pengaman batas putaran tool ke agent supaya tidak berpotensi
loop tak berhenti (Module 22, Langkah 4).

GOAL:
- Di Nala/app/agent.py:
  1. Tambah konstanta modul MAX_TOOL_ROUNDS = 3 dan fungsi
     _count_tool_rounds(messages: list[dict]) -> int yang menghitung
     sum(1 for m in messages if m.get("role") == "tool").
  2. Di dalam build_agent(), tambah node baru force_answer(state) yang
     memanggil ollama_client.chat(state["messages"]) TANPA parameter
     tools sama sekali, return {"messages": [hasil]}.
  3. Ubah should_continue(state): kalau last_message punya tool_calls
     DAN _count_tool_rounds(state["messages"]) >= MAX_TOOL_ROUNDS,
     return "force_answer"; kalau ada tool_calls tapi belum mencapai
     batas, return "call_tool" seperti sebelumnya; kalau tidak ada
     tool_calls, return END seperti sebelumnya.
  4. Tambah graph.add_node("force_answer", force_answer); update
     add_conditional_edges dari call_model supaya mapping-nya jadi
     {"call_tool": "call_tool", "force_answer": "force_answer", END:
     END}; tambah graph.add_edge("force_answer", END).

CONTEXT:
- Tujuan: kalau model terus-menerus meminta tool tanpa pernah berhenti
  (bisa terjadi pada model kecil), setelah MAX_TOOL_ROUNDS putaran tool
  agent dipaksa menjawab tanpa opsi tool lagi, bukan berjalan tanpa
  batas.
- Struktur node call_model dan call_tool yang sudah ada dari Module
  1-2 TIDAK diubah isinya, hanya edge dan node baru yang ditambahkan.

GUARDRAIL:
- JANGAN ubah isi call_model atau call_tool.
- JANGAN hapus edge call_tool -> call_model yang sudah ada.
- force_answer TIDAK BOLEH mengirim parameter tools ke
  ollama_client.chat() — itu intinya, supaya model tidak bisa minta
  tool lagi di putaran ini.
```

</details>

**📄 Kode lengkap Module 22** (`app/agent.py` versi lengkap dengan node `force_answer` — potongan relevan sudah ditampilkan utuh di Langkah 4 di atas; digabungkan dengan `app/agent.py` dari Module 20-21, tidak ada file lain yang berubah).

## 6. Hasil Uji Nyata

Bagian ini mendokumentasikan pengujian sungguhan yang dilakukan terhadap kode di atas — termasuk temuan yang **tidak sesuai rencana awal** — supaya kita tahu apa yang benar-benar terjadi, bukan versi ideal yang seharusnya terjadi.

### a. Tabel Bagian 2 dijalankan ulang lewat `/chat`

Keenam pertanyaan di Bagian 2 dijalankan langsung ke endpoint agent (`llama3.2:3b`, `MAX_TOOL_ROUNDS=3`, tanpa perubahan lain), lalu jawabannya diverifikasi manual terhadap isi database (`docker exec nala-postgres-1 psql ...`):

| Pertanyaan | Tool dipanggil | Hasil | Verifikasi |
|---|---|---|---|
| Syarat kredit nasabah perorangan | `cari_dokumen_sop` | ✅ Sesuai — daftar dokumen (KTP, KK, slip gaji) memang bagian syarat perorangan, bukan tercampur dengan syarat badan usaha | Dicocokkan manual dengan isi dokumen SOP |
| Jumlah pengajuan kredit status pending | `query_data_operasional` | ✅ Sesuai — "3 pengajuan pending" | `SELECT status, count(*) ... GROUP BY status` → pending=3 |
| Status klaim asuransi N-00305 | `query_data_operasional` | ✅ Sesuai — disetujui, Rp 15.000.000, 29 Agustus 2026 | Cocok dengan baris `klaim_asuransi` |
| Kenapa pengajuan kredit N-00305 ditolak | `query_data_operasional` | ❌ **Mengarang** — jawab "tidak memiliki surat keterangan penghasilan dari pemberi kerja yang valid", lalu menambahkan info SOP soal persetujuan Board 2 minggu yang tidak relevan dengan pertanyaan | Data asli di kolom `alasan_penolakan`: **"Skor kredit di bawah ambang batas minimum"** — sama sekali tidak disebut model |
| Halo, kamu siapa? | Tidak ada | ✅ Sesuai — perkenalan singkat, tidak halusinasi | — |
| Apa itu bunga majemuk? | Tidak ada | ❌ **Melanggar batasan domain** — menjawab panjang lebar soal bunga majemuk alih-alih menolak/mengarahkan kembali ke topik PT Nusantara Finance, walau `NALA_SYSTEM_PROMPT_AGENT` tidak eksplisit menyuruh menolak topik di luar domain (hanya menyuruh pakai tool untuk hal terkait SOP/data) | Dibandingkan dengan ekspektasi tabel Bagian 2 |

**4/6 sesuai ekspektasi, 2/6 gagal.** Catatan penting: pada percobaan sebelumnya (sesi lain, model & kode identik), pertanyaan pertama ("syarat perorangan") justru **gagal** — RAG mengambil bagian dokumen syarat badan usaha, bukan perorangan. Pada percobaan ini pertanyaan yang sama **berhasil**. Ini bukan kontradiksi — ini bukti langsung bahwa kegagalan routing/retrieval pada model sekecil ini **tidak konsisten antar-run untuk pertanyaan yang identik**, sejalan dengan temuan konsistensi sintesis jawaban di Module 21 Bagian 6. Jangan menjalankan tabel ini sekali lalu menyimpulkan "sudah beres" — jalankan berkali-kali kalau ingin klaim yang bisa dipercaya.

Kegagalan Q4 ("mengarang alasan penolakan") sangat mirip pola yang sudah didokumentasikan Module 21 Bagian 6: tool mengembalikan data yang benar (dibuktikan lewat `alasan_penolakan` di database), tapi model tidak memakainya saat menyusun jawaban akhir — ini bukan masalah routing (tool yang benar dipanggil), murni masalah sintesis.

### b. Pengaman `MAX_TOOL_ROUNDS`/`force_answer`: logikanya benar, tapi susah dipicu organik

Rencana awal Langkah 4 adalah: turunkan `MAX_TOOL_ROUNDS` ke `1`, ulangi pertanyaan dua-tool (baris keempat tabel Bagian 2), amati `force_answer` benar-benar mencegah loop. Percobaan nyata (`docker compose run --rm -e MAX_TOOL_ROUNDS=1 ...`) menunjukkan sesuatu yang tidak diantisipasi:

1. **Percobaan 1** — pertanyaan yang secara eksplisit minta dua data terpisah (status kredit nasabah A + status klaim nasabah B): model **membundel kedua `tool_calls` sekaligus dalam satu giliran** (`agent_call_model` pertama langsung berisi 2 `tool_calls`). Karena `_count_tool_rounds` menghitung jumlah pesan `role: "tool"` (bukan jumlah giliran `call_model`), ini tetap tercatat sebagai 1 putaran meski ada 2 hasil tool — `should_continue` tidak pernah mengembalikan `"force_answer"`.
2. **Percobaan 2** — pertanyaan kondisional ("kalau statusnya ditolak, baru cari SOP syaratnya") yang seharusnya baru bisa diputuskan **setelah** melihat hasil tool pertama: model tetap membundel kedua tool call di giliran pertama, tanpa menunggu hasil round 1.
3. **Percobaan 3** — state riwayat dibuat manual (bukan dari model) supaya sudah ada 1 putaran tool selesai, lalu `agent.invoke()` dipanggil langsung supaya `call_model` sungguhan (model asli, bukan simulasi) yang memutuskan giliran berikutnya. Hasilnya: model **tidak meminta tool kedua sama sekali** — ia langsung menjawab, dan jawabannya **mengarang** isi SOP yang sama sekali tidak pernah diambil dari `cari_dokumen_sop` (bertentangan langsung dengan instruksi `NALA_SYSTEM_PROMPT_AGENT`: "Jangan mengarang jawaban").
4. **Percobaan 4** — sama seperti #3, tapi pesan user ditambahi instruksi eksplisit "WAJIB panggil tool cari_dokumen_sop, jangan jawab dari ingatanmu": model tetap tidak mengeluarkan `tool_calls` sungguhan — ia hanya **menulis di teks jawaban** "saya akan memanggil tool cari_dokumen_sop..." lalu lanjut mengarang isi SOP tanpa benar-benar memanggilnya.

Karena `should_continue` cuma mengarahkan ke `force_answer` ketika `last_message` **punya** `tool_calls` DAN batas putaran tercapai, dan di keempat percobaan ini `last_message` tidak pernah punya `tool_calls` pada titik yang relevan (baik karena dibundel di awal, atau karena model berhenti minta tool), `force_answer` **tidak pernah benar-benar tereksekusi lewat jalur nyata** di keempat percobaan ini.

**Verifikasi yang tetap dilakukan** (supaya klaim "pengaman ini bekerja" tidak sekadar asumsi): logika `should_continue` diuji langsung di level kode dengan state buatan yang meniru situasi 1 putaran tool sudah lewat dan `last_message` punya `tool_calls`:

```python
messages_after_1_round = [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "", "tool_calls": [...]},  # putaran 1
    {"role": "tool", "content": "...", "tool_call_id": "x", "name": "..."},
    {"role": "assistant", "content": "", "tool_calls": [...]},  # model minta putaran 2
]
# _count_tool_rounds(...) == 1, MAX_TOOL_ROUNDS == 1
# → should_continue(...) mengembalikan "force_answer" — TERKONFIRMASI
```

**Kesimpulan jujur soal bagian ini**: kode pengaman `MAX_TOOL_ROUNDS`/`force_answer` **benar secara logika** (dibuktikan langsung, bukan diasumsikan), tapi kondisi yang memicunya di dunia nyata — model meminta tool secara berurutan sampai melewati batas — **jarang atau tidak pernah terjadi secara organik** dengan `llama3.2:3b` pada skenario yang dicoba. Pola kegagalan model kecil ini justru kebalikan dari yang diantisipasi Langkah 4: bukan meminta tool **terlalu banyak** (risiko yang coba dicegah `force_answer`), tapi berhenti **terlalu cepat** dan mengarang jawaban begitu ada 1 hasil tool di riwayat — bahkan ketika diperintah eksplisit untuk memanggil tool lagi. `force_answer` tetap berguna sebagai pengaman defensif untuk model lain (mis. `qwen2.5:7b` yang mungkin lebih "gigih" minta tool berulang), tapi untuk `llama3.2:3b` spesifik, risiko yang lebih mendesak untuk ditangani sebenarnya adalah halusinasi saat berhenti dini — sesuatu yang di luar cakupan pengaman ini dan belum ada mitigasinya di rangkaian Module 19-23.

## 7. Apa yang TIDAK Ada di Module Ini

- Pembatasan siapa yang boleh memicu tool SQL — Module 23 (RBAC).
- Pencatatan tool mana yang dipanggil untuk keperluan audit — Module 23 (sengaja belum dicatat permanen di sini, walau secara teknis bisa dilihat manual dari log kalau `print()` debug Module 20 masih ada).
- Perubahan pada `/chat/stream` — masih sama seperti Module 20 Bagian 4 Tahap C, tetap di luar cakupan rangkaian Module 19-23.

## 8. Checkpoint Praktik

Langkah eksekusi lengkap ada di bagian **Panduan Praktik** di bawah (Langkah 14-16). Yang perlu dipastikan sebelum lanjut ke Module 23:

- [ ] Keenam baris tabel Bagian 2 sudah dicoba **lebih dari sekali**, hasil routing dan kebenaran jawabannya dicatat (tool mana yang dipanggil, jawaban dicocokkan manual dengan isi database/dokumen — lihat Bagian 6.a) — jangan simpulkan dari satu kali percobaan, hasilnya bisa beda antar-run untuk pertanyaan yang sama
- [ ] Kasus ambigu Bagian 4.a sudah dicoba minimal sekali, hasilnya didiskusikan (bukan harus "benar", cukup dipahami kenapa)
- [ ] Logika `should_continue`/`force_answer` sudah diverifikasi benar (baik lewat percobaan `MAX_TOOL_ROUNDS=1` maupun lewat pengujian langsung di level kode seperti Bagian 6.b) — kita paham bahwa memicunya secara organik dengan `llama3.2:3b` bisa jadi sulit, dan itu sendiri temuan yang sah untuk dicatat, bukan kegagalan pengujian
- [ ] Tidak ada regresi pada pertanyaan sederhana satu-tool dari Module 20-21

## Kesimpulan

Module ini tidak menambah tool baru — ia menunjukkan bahwa desain graph dari Module 20 (edge kondisional + loop-back) sudah cukup fleksibel untuk menangani routing dua-tool, termasuk kasus yang butuh keduanya secara berurutan, tanpa perubahan struktural. Yang ditambahkan justru kejujuran teknis: routing berbasis LLM kecil **akan** kadang salah, itu bukan cacat implementasi tapi batas kemampuan model — mitigasinya (description tool yang lebih tajam, opsi upgrade ke `qwen2.5:7b` untuk laptop yang mampu) mengurangi tapi tidak menghilangkan masalah ini, dan pengaman `MAX_TOOL_ROUNDS`/`force_answer` memastikan kegagalan routing paling buruk sekalipun (loop tak berhenti) tidak membuat sistem macet — **meski pengujian nyata (Bagian 6.b) menunjukkan mode kegagalan `llama3.2:3b` yang lebih sering justru berhenti terlalu cepat dan mengarang, bukan meminta tool berlebihan**, jadi pengaman ini lebih relevan sebagai jaring pengaman defensif untuk model lain daripada risiko yang paling sering muncul di kurikulum ini. Module 23 menutup rangkaian Module 19-23 dengan lapisan yang sengaja belum disentuh di sini: siapa boleh memicu tool mana, dan jejak audit atas semua keputusan ini.

## Panduan Praktik

> Catatan penomoran: bagian ini memakai penomoran "Langkah" tersendiri (melanjutkan urutan global lintas-module: Module 19 = Langkah 1-5, Module 20 = Langkah 6-10, Module 21 = Langkah 11-13, module ini = Langkah 14-16) yang berbeda dari "Langkah 1-4" di dalam bagian struktur kode materi.md di atas — keduanya kebetulan bertumpang tindih penomoran tapi berasal dari dua urutan yang terpisah, peninggalan dari saat panduan ini masih satu dokumen gabungan Module 19-23.

**Panduan Praktik — Module 22: Routing — Menggabungkan RAG + SQL Tool dalam Satu Agent**

Lanjutan langsung dari bagian Panduan Praktik di materi Module 21 — agent dengan dua tool (`cari_dokumen_sop`, `query_data_operasional`) harus sudah jalan lewat `/chat` sebelum mulai di sini. Penomoran Langkah melanjutkan penomoran global (Module 19: Langkah 1-5, Module 20: Langkah 6-10, Module 21: Langkah 11-13).

### Prasyarat
- Module 21 selesai: `/chat` bisa menjawab pertanyaan RAG maupun SQL secara terpisah, tanpa regresi.

### Langkah 14: Uji tabel skenario routing (Module 22 Bagian 2), verifikasi lawan database

Jalankan **keenam** baris tabel `materi.md` Module 22 Bagian 2 satu per satu lewat `curl -X POST http://localhost:8000/chat ...` (format sama seperti Langkah 12-13). Jangan cuma baca jawabannya sekilas — cocokkan isinya langsung dengan data asli:

```bash
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" \
  -d '{"message": "Apa saja syarat pengajuan kredit untuk nasabah perorangan?"}'

curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" \
  -d '{"message": "Berapa banyak pengajuan kredit yang statusnya pending minggu ini?"}'

curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" \
  -d '{"message": "Bagaimana status klaim asuransi nasabah N-00305?"}'

curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" \
  -d '{"message": "Kenapa pengajuan kredit nasabah N-00305 ditolak?"}'

curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" \
  -d '{"message": "Halo, kamu siapa?"}'

curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" \
  -d '{"message": "Apa itu bunga majemuk?"}'
```

Untuk pertanyaan yang menyentuh data operasional, verifikasi jawabannya langsung terhadap database, jangan percaya begitu saja:

```bash
docker exec nala-postgres-1 psql -U nala_admin -d nala_operasional \
  -c "SELECT status, count(*) FROM pengajuan_kredit GROUP BY status;"

docker exec nala-postgres-1 psql -U nala_admin -d nala_operasional \
  -c "SELECT nasabah_id, status, alasan_penolakan FROM pengajuan_kredit WHERE nasabah_id='N-00305';"
```

✅ **Indikator untuk dicatat**: keenam baris tabel routing sudah dicoba **dan** jawabannya dicocokkan manual dengan data asli — bukan cuma "tool yang benar terpanggil". Hasil pengujian nyata (Module 22 Bagian 6.a): tool yang dipanggil hampir selalu tepat, tapi jawaban akhir bisa mengarang detail yang tidak sesuai data (mis. alasan penolakan kredit) meski tool sudah mengembalikan data yang benar — sama seperti temuan Module 21 Bagian 6. Jalankan tabel ini lebih dari sekali kalau memungkinkan: hasil bisa berbeda antar-run untuk pertanyaan yang identik (lihat catatan non-determinisme di Bagian 6.a), jadi satu kali percobaan tidak cukup untuk klaim "sudah benar" atau "gagal".

### Langkah 15: Uji kasus ambigu, coba perbaikan `description` (Module 22 Bagian 4)

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Kredit saya gimana?"}'
```

Amati tool mana yang dipanggil (kalau ada) dan apakah jawabannya membantu. Coba terapkan perbaikan `description` dari Module 22 Bagian 4.b Langkah 2 ke `app/tools/sql_tool.py`, `docker compose up --build api` ulang, ulangi pertanyaan yang sama — bandingkan hasilnya.

✅ **Indikator untuk dicatat**: perbandingan sebelum/sesudah perbaikan description — tidak wajib "sempurna", tujuannya memahami bahwa description memengaruhi routing tapi bukan jaminan mutlak.

### Langkah 16: Uji `MAX_TOOL_ROUNDS`/`force_answer` (Module 22 Bagian 5-Bagian 6.b)

Ikuti Module 22 Bagian 5 Langkah 4 (tambah `force_answer`, `MAX_TOOL_ROUNDS`).

```bash
docker compose up --build api
```

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Berapa banyak pengajuan kredit yang statusnya pending?"}'
```

✅ **Indikator sukses**: jawaban tetap benar (tidak ada regresi, kasus ini jauh di bawah `MAX_TOOL_ROUNDS`).

**Coba picu `force_answer` secara nyata** — turunkan `MAX_TOOL_ROUNDS` ke `1` tanpa mengubah/rebuild image (lebih cepat untuk eksperimen berulang daripada edit `app/agent.py`):

```bash
docker compose stop api
docker compose run --rm -d -e MAX_TOOL_ROUNDS=1 -p 8000:8000 --name nala-api-force-test api

# verifikasi env var benar-benar terset di container test
docker exec nala-api-force-test python -c "from app.agent import MAX_TOOL_ROUNDS; print(MAX_TOOL_ROUNDS)"
```

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Kenapa pengajuan kredit nasabah N-00305 ditolak?"}'
```

⚠️ **Ekspektasi yang realistis** (bukan tebakan, ini temuan nyata Module 22 Bagian 6.b): kemungkinan besar `force_answer` **tidak akan terpicu** oleh percobaan di atas. Pengujian sungguhan menunjukkan `llama3.2:3b` cenderung membundel semua tool call yang dianggap perlu ke **satu** giliran (bukan berurutan lewat beberapa putaran), atau berhenti lebih dulu dan mengarang jawaban ketimbang meminta putaran tool tambahan — bahkan kalau diminta eksplisit. Jangan anggap ini kegagalan latihan; ini pola nyata yang perlu didokumentasikan.

✅ **Indikator sukses yang tetap valid**: NALA tetap memberi jawaban (tidak macet/timeout) di kedua kasus (baik `force_answer` benar-benar terpicu maupun tidak). Untuk memastikan pengaman ini **benar secara logika** walau sulit dipicu organik, verifikasi langsung di level kode (Module 22 Bagian 6.b) — jalankan di dalam container test:

```bash
docker exec nala-api-force-test python -c "
from app.agent import _count_tool_rounds
messages = [
    {'role': 'system', 'content': 'x'},
    {'role': 'user', 'content': 'x'},
    {'role': 'assistant', 'content': '', 'tool_calls': [{'id': 'a', 'function': {'name': 'f', 'arguments': {}}}]},
    {'role': 'tool', 'content': 'hasil', 'tool_call_id': 'a', 'name': 'f'},
    {'role': 'assistant', 'content': '', 'tool_calls': [{'id': 'b', 'function': {'name': 'f', 'arguments': {}}}]},
]
print('tool rounds:', _count_tool_rounds(messages))  # harus 1
"
```

Bersihkan container test dan kembalikan yang normal:

```bash
docker stop nala-api-force-test
docker compose up -d api
```

Kembalikan `MAX_TOOL_ROUNDS` ke `3` (default, tidak perlu ubah kode kalau tidak pernah diubah permanen). Module 22 selesai — lanjut ke bagian Panduan Praktik di materi Module 23.

### Troubleshooting

- **Routing tool terasa buruk terus-menerus meski sudah memperbaiki `description` (Module 22 Bagian 4.b)**: pertimbangkan opsi `qwen2.5:7b` (Module 22 Bagian 4.b Langkah 3) **hanya** kalau laptop punya RAM 32GB+ — jangan dipaksakan di laptop 16GB yang sudah menjalankan Ollama + OpenSearch + Airflow + PostgreSQL bersamaan, risiko container ter-*kill* karena kehabisan memory jauh lebih mengganggu daripada akurasi routing yang belum sempurna.
- **Agent tampak "menggantung" lama (timeout) untuk pertanyaan yang butuh dua tool**: wajar sampai batas tertentu — setiap putaran tool berarti minimal satu panggilan tambahan ke `llama3.2:3b` (Module 22 Bagian 1), jadi pertanyaan yang butuh dua tool berurutan otomatis lebih lambat dari pertanyaan satu-tool. Kalau benar-benar tidak pernah selesai (bukan cuma lambat), pastikan `MAX_TOOL_ROUNDS`/`force_answer` (Module 22 Bagian 5, Langkah 16) sudah terpasang dengan benar.
- **Error umum lain** (`no configuration file provided`, `failed to read dockerfile`, port sudah dipakai, dsb.): lihat bagian Panduan Praktik > Troubleshooting di materi.md module-module sebelumnya (Module 5-14) — penyebab dan solusinya sama, tidak spesifik rangkaian Module 19-23.

---

Untuk informasi lebih lanjut, lihat [README utama](../README.md).
