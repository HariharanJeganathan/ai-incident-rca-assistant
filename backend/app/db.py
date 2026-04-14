# backend/app/db.py
import os
import psycopg


def get_connection():
    host = os.getenv("POSTGRES_HOST")
    database = os.getenv("POSTGRES_DB", "postgres")
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    port = int(os.getenv("POSTGRES_PORT", "5432"))
    sslmode = os.getenv("POSTGRES_SSLMODE", "require")

    # psycopg3 does not accept "user@servername" format — strip the suffix
    user = (user or "").split("@")[0]

    missing = [
        name
        for name, value in (
            ("POSTGRES_HOST", host),
            ("POSTGRES_USER", user),
            ("POSTGRES_PASSWORD", password),
        )
        if not value
    ]
    if missing:
        raise ValueError(
            f"PostgreSQL environment variables are missing: {', '.join(missing)}"
        )

    return psycopg.connect(
        host=host,
        dbname=database,
        user=user,
        password=password,
        port=port,
        sslmode=sslmode,
    )