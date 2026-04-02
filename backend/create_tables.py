from backend.app.db import get_connection

conn = get_connection()
cursor = conn.cursor()

cursor.execute(
    """
CREATE TABLE IF NOT EXISTS incident_rca (
    id SERIAL PRIMARY KEY,
    incident_file TEXT,
    rca_report TEXT,
    impact_level TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""
)

cursor.execute(
    """
CREATE TABLE IF NOT EXISTS incident_chat (
    id SERIAL PRIMARY KEY,
    incident_id INTEGER NOT NULL REFERENCES incident_rca(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""
)

conn.commit()
cursor.close()
conn.close()

print("Tables created successfully")