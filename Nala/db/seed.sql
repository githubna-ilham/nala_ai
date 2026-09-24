-- db/seed.sql
CREATE TABLE pengajuan_kredit (
    id SERIAL PRIMARY KEY,
    nasabah_id VARCHAR(10) NOT NULL,
    nama_nasabah VARCHAR(100) NOT NULL,
    jumlah_pengajuan NUMERIC(15, 2) NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'disetujui', 'ditolak', 'pencairan')),
    tanggal_pengajuan DATE NOT NULL,
    alasan_penolakan TEXT
);

CREATE TABLE klaim_asuransi (
    id SERIAL PRIMARY KEY,
    nasabah_id VARCHAR(10) NOT NULL,
    nama_nasabah VARCHAR(100) NOT NULL,
    jenis_klaim VARCHAR(50) NOT NULL,
    jumlah_klaim NUMERIC(15, 2) NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'diproses', 'disetujui', 'ditolak')),
    tanggal_klaim DATE NOT NULL
);

-- Data awal minimal (starting point) — selebihnya ditambahkan staff sendiri lewat UI /data-operasional
INSERT INTO pengajuan_kredit (nasabah_id, nama_nasabah, jumlah_pengajuan, status, tanggal_pengajuan, alasan_penolakan) VALUES
('N-00231', 'Budi Santoso', 50000000, 'pending', CURRENT_DATE - 2, NULL),
('N-00305', 'Andi Wijaya', 100000000, 'ditolak', CURRENT_DATE - 5, 'Skor kredit di bawah ambang batas minimum');

INSERT INTO klaim_asuransi (nasabah_id, nama_nasabah, jenis_klaim, jumlah_klaim, status, tanggal_klaim) VALUES
('N-00305', 'Andi Wijaya', 'kendaraan', 15000000, 'disetujui', CURRENT_DATE - 20);

-- Role read-only: dipakai agent (tool query_data_operasional, dibangun Module 25) — hanya bisa SELECT
CREATE ROLE nala_readonly WITH LOGIN PASSWORD 'readonly_dev_only';
GRANT CONNECT ON DATABASE nala_operasional TO nala_readonly;
GRANT USAGE ON SCHEMA public TO nala_readonly;
GRANT SELECT ON pengajuan_kredit, klaim_asuransi TO nala_readonly;

-- Role write-only: dipakai form UI /data-operasional (input manusia, bukan LLM) — hanya bisa INSERT
CREATE ROLE nala_writer WITH LOGIN PASSWORD 'writer_dev_only';
GRANT CONNECT ON DATABASE nala_operasional TO nala_writer;
GRANT USAGE ON SCHEMA public TO nala_writer;
GRANT INSERT ON pengajuan_kredit, klaim_asuransi TO nala_writer;
GRANT USAGE, SELECT ON SEQUENCE pengajuan_kredit_id_seq, klaim_asuransi_id_seq TO nala_writer;
