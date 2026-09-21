import logging
import os
from datetime import datetime, timezone

import psycopg

POSTGRES_APP_DSN = os.environ.get(
    "POSTGRES_APP_DSN",
    "postgresql://nala_app:app_dev_only@localhost:5432/nala_operasional",
)

logger = logging.getLogger("nala.audit")


def log_audit(
    user_id: str,
    role: str,
    pertanyaan: str,
    tool_dipanggil: str | None,
    akses_diizinkan: bool,
    ringkasan_data_diakses: str | None = None,
) -> None:
    try:
        with psycopg.connect(POSTGRES_APP_DSN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO audit_log
                        (user_id, role, pertanyaan, tool_dipanggil, akses_diizinkan, ringkasan_data_diakses)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (user_id, role, pertanyaan, tool_dipanggil, akses_diizinkan, ringkasan_data_diakses),
                )
    except psycopg.OperationalError:
        logger.error(
            "Gagal mencatat audit log (user_id=%s, tool=%s, waktu=%s) — PostgreSQL tidak terjangkau",
            user_id,
            tool_dipanggil,
            datetime.now(timezone.utc).isoformat(),
        )
