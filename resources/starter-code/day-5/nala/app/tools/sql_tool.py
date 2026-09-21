import psycopg

from app.db import get_connection

SQL_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "query_data_operasional",
        "description": (
            "Mengambil data operasional PT Nusantara Finance — pengajuan kredit atau "
            "klaim asuransi milik nasabah tertentu, atau ringkasan jumlah berdasarkan "
            "status. Gunakan untuk pertanyaan tentang STATUS, JUMLAH, atau DATA "
            "TRANSAKSI spesifik (bukan untuk pertanyaan tentang prosedur/syarat, itu "
            "tugas tool cari_dokumen_sop)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "tabel": {
                    "type": "string",
                    "enum": ["pengajuan_kredit", "klaim_asuransi"],
                    "description": "Tabel data yang ingin diquery",
                },
                "mode": {
                    "type": "string",
                    "enum": ["hitung_per_status", "detail_nasabah"],
                    "description": (
                        "hitung_per_status: hitung jumlah baris per status (opsional "
                        "difilter status tertentu). detail_nasabah: ambil detail "
                        "baris untuk satu nasabah_id tertentu."
                    ),
                },
                "status": {
                    "type": "string",
                    "enum": ["pending", "disetujui", "ditolak", "pencairan", "diproses"],
                    "description": "Filter status (opsional, hanya untuk mode hitung_per_status)",
                },
                "nasabah_id": {
                    "type": "string",
                    "description": "ID nasabah (wajib untuk mode detail_nasabah), format N-XXXXX",
                },
            },
            "required": ["tabel", "mode"],
        },
    },
}

_ALLOWED_TABLES = {"pengajuan_kredit", "klaim_asuransi"}
_ALLOWED_STATUS = {"pending", "disetujui", "ditolak", "pencairan", "diproses"}
_MAX_ROWS = 20
_CURRENCY_COLUMNS = {"jumlah_pengajuan", "jumlah_klaim"}


def _format_value(col: str, val) -> str:
    if col in _CURRENCY_COLUMNS and val is not None:
        return f"Rp {val:,.0f}".replace(",", ".")
    return str(val)


def query_data_operasional(
    tabel: str, mode: str, status: str | None = None, nasabah_id: str | None = None
) -> str:
    if tabel not in _ALLOWED_TABLES:
        return f"Tabel '{tabel}' tidak dikenal/tidak diizinkan."

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                if mode == "hitung_per_status":
                    if status is not None and status not in _ALLOWED_STATUS:
                        return f"Status '{status}' tidak dikenal."
                    if status:
                        cur.execute(
                            f"SELECT status, COUNT(*) FROM {tabel} WHERE status = %s GROUP BY status",  # noqa: S608
                            (status,),
                        )
                    else:
                        cur.execute(
                            f"SELECT status, COUNT(*) FROM {tabel} GROUP BY status"  # noqa: S608
                        )
                    rows = cur.fetchall()
                    if not rows:
                        return "Tidak ada data yang cocok."
                    return "\n".join(f"{s}: {c}" for s, c in rows)

                elif mode == "detail_nasabah":
                    if not nasabah_id:
                        return "nasabah_id wajib diisi untuk mode detail_nasabah."
                    cur.execute(
                        f"SELECT * FROM {tabel} WHERE nasabah_id = %s LIMIT %s",  # noqa: S608
                        (nasabah_id, _MAX_ROWS),
                    )
                    columns = [desc[0] for desc in cur.description]
                    rows = cur.fetchall()
                    if not rows:
                        return f"Tidak ditemukan data untuk nasabah_id '{nasabah_id}' di tabel {tabel}."
                    return "\n".join(
                        ", ".join(f"{col}={_format_value(col, val)}" for col, val in zip(columns, row))
                        for row in rows
                    )

                return f"Mode '{mode}' tidak dikenal."
    except psycopg.OperationalError:
        return "Tidak dapat terhubung ke database operasional saat ini."
