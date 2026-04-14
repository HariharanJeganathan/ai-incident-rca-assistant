# create_tables.py
import os
import sys
import traceback
from pathlib import Path

from dotenv import load_dotenv
import psycopg

# Load .env from backend/.env
env_path = Path(__file__).parent / "backend" / ".env"
load_dotenv(env_path)

# Force UTF-8 output so emoji prints correctly on Windows
sys.stdout.reconfigure(encoding="utf-8")


def create_tables():
    """Create required database tables"""

    host = os.getenv("POSTGRES_HOST")
    database = os.getenv("POSTGRES_DB")
    raw_user = os.getenv("POSTGRES_USER", "")
    password = os.getenv("POSTGRES_PASSWORD")
    port = int(os.getenv("POSTGRES_PORT", "5432"))
    sslmode = os.getenv("POSTGRES_SSLMODE", "require")

    # psycopg3 (unlike psycopg2) does not accept "user@server" format.
    # Strip the @servername suffix if present.
    user = raw_user.split("@")[0]

    print(f"Connecting to: {host}")
    print(f"Database:      {database}")
    print(f"User:          {user}")

    try:
        conn = psycopg.connect(
            host=host,
            dbname=database,
            user=user,
            password=password,
            port=port,
            sslmode=sslmode,
            connect_timeout=10,
        )
        print("✅ Connected successfully!")

        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS incident_rca (
                id SERIAL PRIMARY KEY,
                incident_file VARCHAR(255) NOT NULL,
                rca_report TEXT NOT NULL,
                impact_level VARCHAR(50) DEFAULT 'unknown',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ Created table: incident_rca")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS incident_chat (
                id SERIAL PRIMARY KEY,
                incident_id INTEGER REFERENCES incident_rca(id) ON DELETE CASCADE,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ Created table: incident_chat")

        conn.commit()
        cursor.close()
        conn.close()

        print("\n✅ All tables created successfully!")

    except psycopg.OperationalError as e:
        print(f"\nFAILED - Connection error: {e}")
        print("\nTroubleshooting:")
        print("1. Add your local IP to the Azure PostgreSQL firewall rules")
        print("   Azure Portal -> rca-postgres-server -> Networking -> Add client IP")
        print("2. Verify password is correct")
        return False
    except Exception as e:
        print(f"\nFAILED - Unexpected error: {e}")
        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    create_tables()