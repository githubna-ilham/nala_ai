# Worksheet Gabungan — Evaluasi Dampak Prompt Engineering di Ollama (Module 2 + Module 3)

Worksheet ini menggabungkan dua kemampuan yang sudah dipelajari terpisah: **metodologi evaluasi manual** dari Module 2 (mengukur kecepatan & kualitas jawaban dengan tabel terstruktur) dan **teknik prompt engineering** dari Module 3 (system prompt, few-shot, Modelfile, parameter `temperature`). Alih-alih membandingkan dua *model* seperti di Module 2, di sini Anda membandingkan tiga *kondisi prompt* pada **model yang sama** (`llama3.2:3b`) — supaya dampak nyata dari system prompt terhadap kualitas, konsistensi, dan perilaku model bisa **diukur**, bukan hanya diduga-duga.

**Prasyarat:**
- Module 2 selesai — `ollama serve` berjalan, `llama3.2:3b` sudah di-pull.
- Module 3 Bagian 5 selesai — draft **System Prompt NALA v1** Anda sendiri sudah disusun.
- Module 3 Bagian 7 selesai — model custom `nala-v1` sudah dibuat lewat `ollama create nala-v1 -f Modelfile`.

---

## Bagian 1: Baseline — Model Tanpa System Prompt Apa Pun

Sebelum mengukur dampak prompt engineering, kita perlu titik pembanding: bagaimana `llama3.2:3b` polos (tanpa instruksi apa pun) menjawab tiga jenis pertanyaan yang relevan untuk NALA.

Jalankan tiap pertanyaan pakai `time` (lihat Module 2 section 6.4 kalau lupa caranya), model **polos** tanpa `/set system`:

```bash
time ollama run llama3.2:3b "Siapa kamu?"
```
```bash
time ollama run llama3.2:3b "Apa syarat pengajuan kredit di PT Nusantara Finance?"
```
```bash
time ollama run llama3.2:3b "Bagaimana cara membuat kue coklat yang lembut?"
```

### 1.1 Worksheet Baseline

| Pertanyaan | Ringkasan Jawaban | Waktu (`real`) | Observasi |
|---|---|---|---|
| "Siapa kamu?" | | ___ detik | Apakah jawaban generik ("Saya model bahasa AI...") atau mengklaim jadi NALA? |
| "Syarat pengajuan kredit PT Nusantara Finance?" | | ___ detik | ☐ Mengaku tidak tahu ☐ Mengarang jawaban (*hallucination*) — model tidak punya akses ke SOP internal, lihat Module 2 Bagian 2-3 |
| "Cara membuat kue coklat?" | | ___ detik | Apakah model menjawab? (wajar kalau iya — belum ada batasan topik apa pun) |

**Refleksi 1:** Tanpa system prompt, apakah model punya cara untuk tahu bahwa ia "seharusnya" cuma menjawab soal PT Nusantara Finance? Kenapa/kenapa tidak?

---

## Bagian 2: Setelah System Prompt — `/set system` (Draft Module 3 Bagian 5)

Sekarang aktifkan draft **System Prompt NALA v1** Anda dengan `/set system` (lihat Module 3 Bagian 7.1), lalu ulangi **persis tiga pertanyaan yang sama**:

```bash
ollama run llama3.2:3b
```
```
/set system <tempel draft System Prompt NALA v1 Anda dari Module 3 Bagian 5 di sini>
```

Lalu ajukan ketiga pertanyaan Bagian 1 satu per satu di sesi interaktif yang sama (tidak perlu `time` di sini — mode interaktif tidak cocok diukur `time` per pertanyaan, cukup rasakan apakah terasa lebih lambat/sama dibanding Bagian 1).

### 2.1 Worksheet Setelah System Prompt

| Pertanyaan | Ringkasan Jawaban | Berubah dari Baseline? | Observasi |
|---|---|---|---|
| "Siapa kamu?" | | ☐ Ya ☐ Tidak | Apakah sekarang mencerminkan persona NALA? |
| "Syarat pengajuan kredit PT Nusantara Finance?" | | ☐ Ya ☐ Tidak | Apakah sekarang mengaku tidak tahu (sesuai instruksi "jujur jika tidak tahu"), bukan mengarang? |
| "Cara membuat kue coklat?" | | ☐ Ya ☐ Tidak | Apakah sekarang menolak/mengarahkan kembali ke topik PT Nusantara Finance? |

**Refleksi 2:** Draft system prompt Anda menyelesaikan berapa dari 3 masalah di atas (persona, honesty soal data tidak diketahui, batasan topik)? Kalau ada yang belum berubah, bagian mana dari draft Anda (Persona/Batasan/Format Output di Module 3 Bagian 5) yang perlu diperjelas?

---

## Bagian 3: Model Persisten (`nala-v1`) — Efek Parameter `temperature` terhadap Konsistensi

Bagian 1-2 menguji **isi** system prompt. Bagian ini menguji dimensi lain: **konsistensi** jawaban, yang di Module 3 Bagian 7.2 dikendalikan lewat parameter `temperature`. Model yang sama bisa menjawab pertanyaan yang sama secara berbeda-beda di tiap percobaan — untuk asisten internal seperti NALA, ini bisa jadi masalah (jawaban SOP semestinya konsisten, bukan berubah-ubah tiap ditanya).

### 3.1 Jalankan Pertanyaan yang Sama 3x ke `nala-v1` (temperature 0.3)

```bash
ollama run nala-v1 "Apa syarat pengajuan kredit di PT Nusantara Finance?"
```

Jalankan **3 kali berturut-turut** (keluar dari sesi dengan `/bye` tiap kali, lalu jalankan ulang — supaya tiap percobaan independen, tidak terpengaruh cache riwayat sebelumnya).

| Percobaan | Ringkasan Jawaban |
|---|---|
| 1 | |
| 2 | |
| 3 | |

**Observasi:** Apakah ketiga jawaban di atas secara substansi **konsisten** (sama-sama mengaku tidak tahu / sama-sama mengarahkan ke dokumen SOP), atau bervariasi jauh?

### 3.2 Eksperimen: Naikkan `temperature` ke 0.9, Ulangi

Edit `Modelfile` Anda (dari Module 3 Bagian 7.2), ganti baris `PARAMETER temperature 0.3` jadi `PARAMETER temperature 0.9`, lalu build ulang dengan nama model baru supaya `nala-v1` yang lama tidak tertimpa:

```bash
ollama create nala-v1-eksperimen -f Modelfile
```

Jalankan pertanyaan yang sama **3 kali lagi** ke `nala-v1-eksperimen`:

```bash
ollama run nala-v1-eksperimen "Apa syarat pengajuan kredit di PT Nusantara Finance?"
```

| Percobaan | Ringkasan Jawaban |
|---|---|
| 1 | |
| 2 | |
| 3 | |

**Refleksi 3:** Bandingkan variasi jawaban di `temperature 0.3` (3.1) vs `temperature 0.9` (3.2). Mana yang lebih konsisten? Apakah ini sesuai penjelasan `temperature` di Module 3 Bagian 7.2 ("nilai rendah = jawaban lebih konsisten, lebih kecil kemungkinan mengarang")? Untuk NALA versi produksi, `temperature` berapa yang menurut Anda lebih tepat — dan kenapa?

**Bersih-bersih (opsional):** setelah selesai, hapus model eksperimen supaya tidak menumpuk di `ollama list`:
```bash
ollama rm nala-v1-eksperimen
```

---

## Bagian 4: Tabel Ringkasan — Tiga Kondisi Berdampingan

Satukan hasil Bagian 1-3 ke satu tabel, supaya dampak prompt engineering terlihat jelas dalam satu pandangan:

| Aspek | Tanpa System Prompt (Bagian 1) | `/set system` Draft (Bagian 2) | `nala-v1` Persisten, temp 0.3 (Bagian 3.1) |
|---|---|---|---|
| Persona sesuai NALA? | ☐ | ☐ | ☐ |
| Jujur soal data tidak diketahui (bukan mengarang)? | ☐ | ☐ | ☐ |
| Menolak pertanyaan di luar topik? | ☐ | ☐ | ☐ |
| Konsistensi jawaban antar percobaan | — (belum diuji) | — (belum diuji) | ☐ Konsisten ☐ Bervariasi |
| Perlu diketik ulang tiap sesi baru? | — | ☐ Ya (manual tiap sesi) | ☐ Tidak (persisten) |

---

## Bagian 5: Refleksi Penutup — Menuju Module 4

1. Dari tiga kondisi di atas, mana yang paling siap dipakai sebagai fondasi `NALA_SYSTEM_PROMPT` di kode Python (Module 4)? Kenapa?
2. Worksheet ini menguji prompt engineering **secara manual lewat terminal** — apa yang menurut Anda akan berubah/perlu disesuaikan ketika system prompt yang sama nanti dipanggil otomatis lewat API oleh aplikasi FastAPI NALA (Module 4), bukan diketik manual?
3. Modul-modul mendatang akan memperluas system prompt ini lebih jauh: Module 12 menambah instruksi *grounding* (jawab hanya dari dokumen yang di-retrieve), Module 23 menambah instruksi *tool-use* (RAG vs SQL). Berdasarkan hasil eksperimen `temperature` di Bagian 3, apakah Anda akan mengubah nilai `temperature` seiring NALA bertambah kompleks? Kenapa/kenapa tidak?

---

**Next:** Lanjut ke `Module-04-Setup-Infra-Docker-Compose/materi.md`, bagian Panduan Praktik, untuk memindahkan draft system prompt yang sudah divalidasi di sini menjadi konstanta `NALA_SYSTEM_PROMPT` di kode FastAPI.
