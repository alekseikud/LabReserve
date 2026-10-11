"""Apply numbered SQL files once, in order, after Django's auth migrations."""
from django.conf import settings
from django.db import connection, transaction


def pending_schema_files():
    files = sorted((settings.BASE_DIR / "sql").glob("[0-9]*.sql"))
    with connection.cursor() as cursor:
        cursor.execute("SELECT to_regclass('sql_schema_versions')")
        if cursor.fetchone()[0] is None:
            return files
        cursor.execute("SELECT filename FROM sql_schema_versions")
        applied = {row[0] for row in cursor.fetchall()}
    return [file for file in files if file.name not in applied]


def apply_schema():
    with transaction.atomic(), connection.cursor() as cursor:
        # Prevent two backend processes from applying the same file concurrently.
        cursor.execute("SELECT pg_advisory_xact_lock(741903)")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sql_schema_versions (
                filename varchar(255) PRIMARY KEY,
                applied_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        applied = []
        for file in pending_schema_files():
            cursor.execute(file.read_text(encoding="utf-8"))
            cursor.execute("INSERT INTO sql_schema_versions (filename) VALUES (%s)", [file.name])
            applied.append(file.name)
    return applied
