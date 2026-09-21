# Panduan Praktik — Module 2: Setup Ollama & Evaluasi Model

Panduan hands-on module ini ada di file terpisah: **[WORKSHEET-Percobaan-Ollama.md](./WORKSHEET-Percobaan-Ollama.md)** — mencakup instalasi Ollama, menjalankan model pertama, dan praktik evaluasi manual (latency, kualitas jawaban, perbandingan model).

Worksheet tersebut menggunakan Ollama yang terinstall **langsung di laptop** (bukan di dalam container). Setup Ollama versi containerized (di dalam Docker, untuk aplikasi NALA) baru dilakukan di **Module 4** (`Module-04-Setup-Infra-Docker-Compose/PANDUAN-PRAKTIK.md`).

**Praktik lanjutan (gabungan dengan Module 3):** setelah menyelesaikan Module 3 (draft system prompt + `nala-v1`), kerjakan **[WORKSHEET-Evaluasi-Dampak-Prompt-Engineering.md](../Module-03-Prompt-Engineering-Dasar/WORKSHEET-Evaluasi-Dampak-Prompt-Engineering.md)** di folder Module 3 — menggabungkan metodologi evaluasi manual module ini dengan teknik prompt engineering, untuk mengukur dampak nyata system prompt terhadap kualitas dan konsistensi jawaban.

**Sesi panjang alternatif (3-4 jam, dari nol):** kalau Anda ingin mengerjakan instalasi Ollama module ini sampai prompt engineering Module 3 dalam satu sesi panjang tanpa jeda, pakai **[PANDUAN-PRAKTIK-Sesi-Gabungan-Ollama-Prompt-Engineering.md](../Module-03-Prompt-Engineering-Dasar/PANDUAN-PRAKTIK-Sesi-Gabungan-Ollama-Prompt-Engineering.md)** di folder Module 3 — 20 Langkah berurutan dari `ollama --version` sampai eksperimen `temperature`, dengan estimasi waktu per Langkah.
