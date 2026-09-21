# Panduan Praktik — Module 3: Prompt Engineering Dasar

Panduan hands-on module ini sudah terintegrasi langsung di **`materi.md`**, khususnya:

- **Bagian 5 — Latihan: Menyusun System Prompt NALA v1**: menyusun draft system prompt.
- **Bagian 7 — Menguji System Prompt Anda Sekarang**: mengetes draft tersebut lewat `ollama create -f Modelfile` dan `ollama run`, tanpa perlu menunggu Docker/FastAPI.

Setelah system prompt v1 ini diuji manual di module ini, langkah selanjutnya (menyambungkannya ke aplikasi FastAPI + Docker Compose NALA, termasuk eksperimen rebuild-nya) ada di **Module 4** (`Module-04-Setup-Infra-Docker-Compose/PANDUAN-PRAKTIK.md`, Langkah 6).

**Praktik tambahan (gabungan Module 2 + Module 3):** setelah draft system prompt dan `nala-v1` siap, kerjakan **[WORKSHEET-Evaluasi-Dampak-Prompt-Engineering.md](./WORKSHEET-Evaluasi-Dampak-Prompt-Engineering.md)** — menggabungkan metodologi evaluasi manual Module 2 dengan teknik prompt engineering module ini, untuk **mengukur** (bukan menduga) dampak system prompt terhadap kualitas dan konsistensi jawaban.

**Sesi panjang alternatif (3-4 jam, dari nol):** kalau Anda punya blok waktu panjang dan ingin mengerjakan **instalasi Ollama sampai prompt engineering dalam satu alur tanpa jeda** (menggabungkan seluruh Module 2 + Module 3, termasuk worksheet di atas), pakai **[PANDUAN-PRAKTIK-Sesi-Gabungan-Ollama-Prompt-Engineering.md](./PANDUAN-PRAKTIK-Sesi-Gabungan-Ollama-Prompt-Engineering.md)** — 20 Langkah berurutan dengan estimasi waktu per Langkah, dari `ollama --version` sampai eksperimen `temperature`.
