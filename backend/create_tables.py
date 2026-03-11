from app.db import get_connection

conn = get_connection()
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS incident_rca (
    id SERIAL PRIMARY KEY,
    incident_file TEXT,
    rca_report TEXT,
    impact_level TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""")

conn.commit()

cursor.close()
conn.close()

print("Table created successfully")