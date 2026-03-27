import os

import psycopg2


def get_connection():
    host = os.getenv("POSTGRES_HOST")
    database = os.getenv("POSTGRES_DB", "postgres")
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    port = int(os.getenv("POSTGRES_PORT", "5432"))
    sslmode = os.getenv("POSTGRES_SSLMODE", "require")

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

    return psycopg2.connect(
        host=host,
        database=database,
        user=user,
        password=password,
        port=port,
        sslmode=sslmode,
    )
