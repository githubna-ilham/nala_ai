QA_TESTSET = [
    {
        "question": "Apa saja syarat pengajuan kredit untuk nasabah perorangan?",
        "must_contain": ["KTP", "Kartu Keluarga", "slip gaji", "NPWP"],
    },
    {
        "question": "Dokumen apa yang dibutuhkan badan usaha untuk mengajukan kredit?",
        "must_contain": ["Akte Pendirian", "NPWP Perusahaan", "Laporan Keuangan"],
    },
    {
        "question": "Berapa usia minimal dan maksimal nasabah perorangan untuk mengajukan kredit?",
        "must_contain": ["usia minimal 21 tahun", "maksimal 60 tahun"],
    },
    {
        "question": "Berapa lama proses verifikasi dokumen setelah pengajuan kredit?",
        "must_contain": ["2-3 hari kerja", "verifikasi kelengkapan dokumen"],
    },
    {
        "question": "Apa yang dilakukan tim Credit Analysis dalam proses penilaian kredit?",
        "must_contain": ["BI Checking", "debt-to-income ratio", "plafon kredit"],
    },
    {
        "question": "Berapa lama waktu persetujuan kredit untuk pengajuan di bawah Rp 500 juta?",
        "must_contain": ["processing time 1 hari kerja", "Komite Kredit"],
    },
    {
        "question": "Berapa lama pencairan dana setelah kredit disetujui?",
        "must_contain": ["2-3 hari kerja setelah approval", "Perjanjian Kredit"],
    },
    {
        "question": "Kapan NPWP dibutuhkan untuk pengajuan kredit perorangan?",
        "must_contain": ["NPWP", "bagi pengajuan di atas Rp 500 juta"],
    },
    {
        "question": "Bagaimana cara menghubungi bagian Customer Service NALA?",
        "must_contain": ["Ext. 1001", "cs@nusantarafinance.co.id"],
    },
    {
        "question": "Apa saja jenis kredit yang dilayani PT Nusantara Finance?",
        "must_contain": ["Kredit Konsumsi", "Kredit Modal Kerja", "Kredit Pemilikan Rumah"],
    },
]
