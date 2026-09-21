# Panduan Praktik — Module 26: Polish Frontend untuk Demo Capstone

## Prasyarat

- Module 24 (full-stack deployment) dan Module 25 (status page + checklist keamanan) sudah selesai — stack lengkap sudah jalan di `resources/starter-code/day-5/nala/`.

## Langkah 1: Implementasikan Module 26 (Polish Frontend)

Ikuti Langkah-langkah di `../Module-26-Polish-Frontend-Demo/materi.md`:

- **Tahap A** — tambah typing indicator.
- **Tahap B** — tambah tool-used badge (RAG vs SQL).
- **Tahap C** — cek dan perbaiki layout responsif.

Setiap kali mengubah `app/main.py`, `app/templates/chat.html`, atau `app/static/style.css`, rebuild `api` saja (bukan seluruh stack):

```bash
docker compose up -d --build api
```

## Langkah 2: Uji Coba Menyeluruh via UI

Setelah Module 24-26 selesai, verifikasi semuanya langsung lewat browser (bukan cuma `curl`) — ini juga bentuk gladi bersih sebelum demo capstone, dan sekaligus dress rehearsal yang menyatukan hasil ketiga module tersebut:

- [ ] **Typing indicator** (Module 26 Tahap A) — buka `http://localhost:8000`, kirim pertanyaan apa saja di mode biasa maupun mode Agent. Tiga titik animasi harus muncul sebentar sebelum jawaban tampil, lalu hilang otomatis begitu token/jawaban pertama tiba.
- [ ] **Tool badge** (Module 26 Tahap B) — centang "Pakai Agent", pilih role `staff_finance`. Tanya soal SOP (mis. *"Apa saja syarat pengajuan kredit untuk nasabah perorangan?"*) → badge biru "Dokumen SOP (RAG)" muncul. Tanya soal data (mis. *"Berapa banyak pengajuan kredit yang statusnya pending?"*) → badge oranye "Data Operasional (SQL)". Coba juga role `staff_umum` dengan pertanyaan data — amati apakah badge muncul (lihat gap RBAC, Module 22 Bagian 6, sebelum menyimpulkan ini "salah").
- [ ] **Layout responsif** (Module 26 Tahap C) — buka DevTools (`Cmd+Shift+M`/`Ctrl+Shift+M`), set lebar 375px lalu 768px. Cek halaman Chat, `/status/view`, dan `/data-operasional` — tidak ada elemen terpotong/overflow horizontal.
- [ ] **Status page** (Module 25) — `http://localhost:8000/status/view`, pastikan auto-refresh (tunggu 15 detik, perhatikan halaman reload sendiri) dan semua service `ok`/hijau.
- [ ] **Adminer** (Module 23) — `http://localhost:8081`, login `nala_admin` + password dari `.env` (`POSTGRES_ADMIN_PASSWORD`, atau `changeme_dev_only` kalau belum pernah diganti/di-`ALTER USER`). Cek tabel `audit_log` menampilkan baris-baris dari pengujian di atas.
- [ ] **Langfuse** (`http://localhost:3000`) — cek trace dari percakapan barusan, termasuk field `tool_used` yang ikut tercatat di `trace.update()` (Module 26).

Kalau ada satu poin yang hasilnya tidak sesuai, cek dulu apakah itu memang gap/keterbatasan yang sudah didokumentasikan (Module 24 Bagian 4a, Module 22 Bagian 6, Module 23 Bagian 4) sebelum menganggapnya bug baru.

Setelah semua poin di atas terpenuhi, lanjutkan ke panduan praktik **Module 27** (`../Module-27-Ethics-Governance/PANDUAN-PRAKTIK.md`) untuk diskusi etika & governance dan persiapan capstone.

## Troubleshooting

- **Badge tool tidak pernah muncul / selalu kosong**: badge dibaca dari field `tool_used` di response JSON `/chat` (mode Agent, non-streaming) — bukan dari parsing stream. Cek dulu response mentah lewat `curl -X POST http://localhost:8000/chat ...` dan pastikan `tool_used` benar-benar ada di JSON-nya; kalau tidak, cek `called_tools`/`diizinkan` di `app/main.py` (Module 26 Bagian 2 Tahap B) sesuai implementasi Module 23 Anda.
- **Typing indicator tidak hilang otomatis / macet di tiga titik animasi**: cek `replyEl.innerHTML` benar-benar ditimpa penuh begitu chunk pertama diterima dari stream (bukan di-append) — lihat kode Langkah 1 Tahap A di `materi.md`.
