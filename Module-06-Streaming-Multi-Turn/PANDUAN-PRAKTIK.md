# Panduan Praktik — Module 6: Streaming & Multi-Turn Conversation

## Prasyarat
- Sudah menyelesaikan **Module 5** (Chat UI Dasar) — container `ollama`+`api` dari `resources/starter-code/day-2/nala/` masih berjalan (kalau tidak, ulangi Module 5 Langkah 2)
- Belum butuh `opensearch` atau `airflow` di module ini

## Langkah 1: `/chat/stream` menggantikan `/chat` total, coba streaming

Halaman chat (`http://localhost:8000`) sekarang memanggil `/chat/stream`, dan **`/chat` sudah dihapus** dari `app/main.py` — bukan cuma tidak dipanggil lagi dari frontend. Kirim pertanyaan apa saja dan perhatikan jawaban NALA **muncul bertahap kata demi kata**, bukan langsung muncul utuh seperti di Module 5. Kalau koneksi lambat, jeda antar-token akan terlihat jelas — itu tanda streaming benar-benar berjalan token-demi-token dari Ollama, bukan efek animasi di frontend.

Belum ada dokumen atau RAG di titik ini — jawabannya akan tetap generik seperti Module 5, bedanya cuma **cara** jawabannya muncul (bertahap, bukan sekaligus). Lihat Module 6 Bagian 2 kenapa NALA sengaja pindah ke **satu** endpoint chat saja mulai sekarang — bukan mempertahankan `/chat` dan `/chat/stream` berdampingan. Streaming dulu, RAG menyusul mulai Module 11.

Verifikasi bahwa `/chat` benar-benar sudah hilang, bukan cuma tidak dipakai:

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" -d '{"message": "test"}'
```

✅ Harus `404`.

Kalau ingin memverifikasi `/chat/stream` lewat `curl` (perhatikan flag `-N` supaya curl tidak buffer output dan token terlihat muncul bertahap di terminal):

```bash
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Halo, kamu siapa?"}]}'
```

Perhatikan bedanya dari `/chat` (sudah dihapus): body sekarang `messages` (array), bukan `message` (string tunggal), dan responsnya teks mengalir — bukan JSON `{"reply": "..."}`. **Mulai langkah ini, `/chat/stream` adalah satu-satunya endpoint chat NALA sepanjang sisa Module 5-14** — tidak akan ada endpoint chat baru lagi.

## Langkah 2: Coba percakapan multi-turn

Di halaman chat yang sama, kirim dua pertanyaan berurutan **tanpa reload**:

1. "Berapa lama proses pengajuan kredit?"
2. Lanjutkan dengan: "Kalau untuk nasabah yang sudah lama jadi customer?"

Pertanyaan kedua tidak menyebut "kredit" atau "proses" sama sekali — NALA seharusnya tetap paham bahwa ini masih soal proses kredit, karena riwayat percakapan (termasuk pertanyaan dan jawaban pertama) ikut terkirim di `messages`. Amati juga:

- **Badge jumlah pesan** di atas kolom chat bertambah setiap kali Anda mengirim pesan.
- Kirim beberapa pertanyaan lagi sampai lebih dari 8 pesan — keterangan "windowing aktif" akan muncul, menandakan hanya 10 pesan terakhir yang dikirim ke NALA.
- Klik **"Mulai percakapan baru"** — dialog konfirmasi muncul; setelah dikonfirmasi, riwayat kosong dan pertanyaan lanjutan tidak lagi memahami konteks sebelumnya (membuktikan riwayat benar-benar direset, bukan cuma tampilan yang dibersihkan).

## Troubleshooting

- **`/chat` mengembalikan 404 setelah Langkah 1**: ini **normal**, bukan bug — `/chat` sengaja dihapus total di module ini, digantikan `/chat/stream`. Kalau Anda masih mencoba memanggil `/chat` di Langkah 2 dan seterusnya (di module-module berikutnya), gunakan `/chat/stream` (body `messages`, bukan `message`).
- **`400 Bad Request` saat memanggil `/chat/stream`**: hampir selalu berarti body request salah bentuk — pastikan mengirim `messages` (array of `{role, content}`), bukan `message` (string, itu format `/chat` yang sudah dihapus sejak Langkah 1), dan pastikan elemen **terakhir** di array selalu `role: "user"`.
- **Streaming di browser terasa "meledak sekaligus" (tidak bertahap)**: kemungkinan proxy/antivirus lokal melakukan buffering. Coba dulu lewat `curl -N` (Langkah 1) untuk memastikan server memang mengirim bertahap — kalau `curl` juga terlihat sekaligus, cek apakah `StreamingResponse` di `app/main.py` benar-benar dipanggil (bukan tertimpa jadi response biasa).
- **Pertanyaan lanjutan tidak nyambung meski sudah di percakapan yang sama**: cek di DevTools browser (tab Network) apakah body request ke `/chat/stream` benar-benar berisi seluruh `conversation` (bukan cuma pesan terakhir) — kemungkinan state `conversation` di `chat.html` ter-reset tanpa sengaja, atau halaman sempat di-reload di antara pertanyaan.
- **Chat menjawab generik / bilang belum ada dokumen internal**: ini **selalu normal** di module ini — `/chat/stream` belum punya logika retrieval sama sekali (baru ditambahkan di Module 11), jadi memang selalu menjawab generik, bukan tanda ada yang salah.
