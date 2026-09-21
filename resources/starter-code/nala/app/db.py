import os

import psycopg

POSTGRES_READONLY_DSN = os.environ.get(
    "POSTGRES_READONLY_DSN",
    "postgresql://nala_readonly:readonly_dev_only@localhost:5432/nala_operasional",
)

POSTGRES_WRITER_DSN = os.environ.get(
    "POSTGRES_WRITER_DSN",
    "postgresql://nala_writer:writer_dev_only@localhost:5432/nala_operasional",
)


def get_connection():
    return psycopg.connect(POSTGRES_READONLY_DSN, connect_timeout=5)


def get_write_connection():
    return psycopg.connect(POSTGRES_WRITER_DSN, connect_timeout=5)
