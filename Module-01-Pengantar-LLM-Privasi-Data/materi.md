# Module 1: Pengantar LLM & Privasi Data

## Tujuan

Kita memahami cara kerja dasar LLM, perbedaan LLM cloud vs private/offline, dan alasan spesifik mengapa PT Nusantara Finance membutuhkan LLM privat untuk melindungi data sensitif nasabah sesuai regulasi (OJK, UU PDP). Modul ini juga memperkenalkan gambaran akhir sistem NALA yang akan dibangun sepanjang program training ini.

## Hasil Akhir yang Diharapkan

- Kita bisa menjelaskan perbedaan cloud LLM vs private/offline LLM dari segi biaya, privasi, dan kualitas
- Kita paham risiko konkret mengirim data nasabah/kredit ke API LLM cloud publik dan regulasi yang membatasinya (OJK, UU No. 27/2022, POJK No. 11/2022)
- Kita paham trade-off performa model privat vs cloud, serta strategi mitigasinya (RAG, prompt engineering, evaluasi sistematis)
- Kita punya gambaran umum studi kasus NALA yang akan dibangun sepanjang program training ini
- Kita, dalam diskusi kelompok, bisa mengidentifikasi data sensitif spesifik di organisasi kita sendiri yang tidak boleh dikirim ke LLM cloud publik

## 1. Apa itu LLM

**Large Language Model (LLM)** adalah model kecerdasan buatan yang dilatih pada miliaran kata dan teks dari internet untuk memahami dan menghasilkan bahasa manusia. Cara kerja LLM pada tingkat dasar adalah prediksi token berikutnya (next-token prediction) — model belajar pola statistik dari data pelatihan kemudian memprediksi kata apa yang paling mungkin muncul setelah serangkaian kata sebelumnya. 

Beberapa model LLM populer yang banyak digunakan saat ini termasuk **GPT-4** dari OpenAI (digunakan dalam ChatGPT), **Claude** dari Anthropic (model yang dirancang untuk keselamatan dan keandalan), **Llama** dari Meta (model open-source dengan performa tinggi), dan **Mistral** dari Mistral AI (model kompak yang efisien). Masing-masing model memiliki karakteristik unik dalam hal kemampuan, ukuran, dan optimasi untuk tugas-tugas tertentu.

---

## 2. Cloud LLM vs Private/Offline LLM

Dalam memilih solusi LLM untuk organisasi, ada dua pendekatan utama yang berbeda dalam hal arsitektur dan implementasi:

| Aspek | Cloud LLM (API Publik) | Private/Offline LLM |
|-------|------------------------|----------------------|
| **Biaya** | Model pay-per-use, biaya lebih rendah untuk volume rendah, scalable sesuai kebutuhan | Investasi infrastruktur awal tinggi (GPU/CPU), tapi biaya operasional berkurang untuk volume tinggi |
| **Kemudahan Setup** | Sangat mudah — cukup API key, langsung bisa digunakan tanpa setup teknis | Memerlukan setup infrastruktur, pemeliharaan server, dan expertise teknis |
| **Kualitas Model** | Model terbaik di kelasnya (GPT-4, Claude, dll) dengan performa maksimal | Model lebih kecil dan kompak, biasanya performa lebih rendah dari model cloud terbesar |
| **Latensi** | Bergantung pada kecepatan internet dan respons server cloud | Latensi rendah karena eksekusi lokal, tidak perlu call ke API eksternal |
| **Privasi Data** | **Data dikirim ke server pihak ketiga** — risko kebocoran dan tidak sesuai regulasi sensitif | **Data tetap di server internal** — privasi terjamin, sesuai regulasi ketat seperti OJK untuk industri finance |
| **Kebutuhan Infrastruktur** | Minimal — hanya butuh koneksi internet | Signifikan — perlu GPU/CPU powerful, cooling system, maintenance, dan monitoring |

---

## 3. Kenapa Perusahaan Finance Butuh LLM Privat

Industri keuangan seperti **PT Nusantara Finance** memiliki data yang sangat sensitif dan diatur ketat oleh regulasi. Data nasabah (identitas pribadi, status ekonomi), data kredit (riwayat pembayaran, skor kredit, jumlah utang), dan dokumen internal (prosedur operasional, policy perusahaan, data transaksi) adalah aset kritikal yang tidak boleh dibagikan ke pihak ketiga tanpa izin eksplisit.

Jika data ini dikirim ke API LLM cloud publik seperti OpenAI atau model pihak ketiga lainnya, risiko yang terjadi sangat besar: data bisa dicuri oleh hacker yang menyerang server cloud, data bisa dilanggar oleh pihak dalam yang tidak bertanggung jawab, atau — jika provider tidak memberikan jaminan kontraktual yang jelas — data berisiko turut digunakan untuk melatih model mereka (sebagian besar tier API enterprise secara kontraktual mengecualikan data pelanggan dari training, tapi risiko ini nyata ketika perlindungan kontraktual tersebut tidak ada atau tidak dibaca dengan teliti). Lebih penting lagi, **regulasi industri finansial dan perlindungan data di Indonesia (OJK, Bank Indonesia, UU No. 27/2022 tentang Perlindungan Data Pribadi, serta POJK No. 11/2022) mengatur ketat dan membatasi transfer data nasabah ke sistem eksternal tanpa perlindungan yang memadai**.

Dengan menggunakan LLM privat atau offline yang berjalan di server internal PT Nusantara Finance, data tetap berada di bawah kontrol perusahaan dan tidak ada risiko kebocoran ke pihak ketiga. Ini memenuhi kebutuhan hukum dan membangun kepercayaan nasabah bahwa informasi pribadi mereka aman.

---

## 4. Trade-off yang Harus Disadari Peserta

Model LLM privat atau offline yang berjalan di infrastruktur lokal umumnya **lebih kecil dan lebih sederhana dibanding model cloud terbesar** seperti GPT-4. Akibatnya, model privat sering kali memiliki performa lebih rendah dalam hal pemahaman konteks kompleks, penalaran multi-tahap, atau generasi teks berkualitas tinggi. Ini adalah trade-off fundamental: kita mengorbankan sedikit kualitas untuk mendapatkan privasi dan kontrol data.

Namun, ada strategi-strategi yang terbukti efektif untuk menutup gap performa ini: **RAG (Retrieval-Augmented Generation)** memungkinkan model mengakses dokumen internal sebagai konteks tambahan sehingga jawaban lebih relevan dan akurat; **prompt engineering** yang baik bisa membimbing model untuk memberikan output berkualitas tinggi; dan **evaluasi sistematis** memastikan hasil LLM memenuhi standar bisnis sebelum deploy ke produksi.

Itulah alasan mengapa kurikulum ini dirancang bertahap lintas modul — setiap modul berikutnya akan mengajarkan teknik dan strategi untuk memaksimalkan potensi LLM privat sehingga performanya setara atau mendekati model cloud terbesar, sambil tetap menjaga privasi data perusahaan.

---

## 5. Perkenalan Studi Kasus NALA

Sepanjang program pelatihan ini (27 modul), kita akan membangun **NALA (Nusantara Assistant)** — sebuah sistem LLM privat yang dirancang khusus untuk PT Nusantara Finance. NALA mampu menjawab pertanyaan dari dua sumber data utama: (1) **Dokumen SOP Internal** — panduan operasional, policy perusahaan, prosedur kredit, dan tata cara layanan; (2) **Data Operasional** — data pengajuan kredit, data klaim, riwayat transaksi, dan informasi nasabah (dengan akses terenkripsi dan kontrol ketat).

Gambaran akhir NALA pada **akhir program pelatihan (Module 30)** adalah sistem yang dapat menerima pertanyaan dalam bahasa Indonesia natural (misalnya: "Apa persyaratan untuk pengajuan kredit modal kerja?", "Berapa lama proses klaim asuransi diproses?") dan memberikan jawaban akurat berdasarkan dokumen dan data internal, tanpa mengirim informasi sensitif ke layanan cloud eksternal. NALA akan menjadi assistant yang meningkatkan efisiensi operasional PT Nusantara Finance dan kepuasan nasabah melalui respons cepat dan akurat, sambil tetap menjaga keamanan dan privasi data tertinggi.

---

## 6. Diskusi Kelompok (10 menit)

Kita akan dibagi menjadi kelompok kecil (3-5 orang). Setiap kelompok mendapat pertanyaan berikut untuk didiskusikan selama 10 menit, kemudian share ringkasan jawaban ke kelas.

**Pertanyaan Diskusi:**

**"Bayangkan Anda bekerja di perusahaan tempat Anda saat ini. Data atau dokumen apa yang ada di organisasi Anda yang sensitif dan TIDAK BOLEH dikirim ke LLM cloud publik (seperti ChatGPT atau layanan cloud lainnya)? Mengapa data tersebut sensitif, dan regulasi atau kebijakan apa yang melarang pengiriman data tersebut?"**

**Contoh jawaban yang diharapkan:**
- Kelompok Finance: data nasabah, data rekening bank, data kredit (sensitif karena regulasi OJK)
- Kelompok HR: data karyawan, gaji, evaluasi performa (sensitif karena privasi karyawan dan keamanan organisasi)
- Kelompok Legal: dokumen kontrak rahasia, dokumen litigasi, IP perusahaan (sensitif karena kerahasiaan komersial dan hukum)
- Kelompok IT: password, konfigurasi sistem, data backup (sensitif karena keamanan siber)
- Kelompok Marketing: data pelanggan, strategi bisnis, data kampanye (sensitif karena keunggulan kompetitif)

Diskusi ini membantu kita menyadari bahwa privasi data bukan hanya konsep abstrak, tetapi relevan langsung dengan pekerjaan kita sehari-hari. Ini juga membangun motivasi mengapa NALA dan sistem LLM privat sangat penting untuk organisasi kita.

---

## Panduan Praktik

Module ini adalah sesi konsep (lihat bagian-bagian di atas) — tidak ada langkah hands-on/terminal tersendiri.

Satu-satunya aktivitas praktik di module ini adalah **Diskusi Kelompok** (lihat bagian "6. Diskusi Kelompok" di atas), yang tidak membutuhkan setup infra apa pun.

Setup Docker/Ollama/terminal pertama kali dimulai di **Module 2** (`Module-02-Setup-Ollama-Evaluasi-Model/WORKSHEET-Percobaan-Ollama.md`).
