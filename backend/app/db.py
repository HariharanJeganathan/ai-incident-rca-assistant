import psycopg2

def get_connection():

    conn = psycopg2.connect(
        host="rca-postgres-server.postgres.database.azure.com",
        database="postgres",
        user="rca_admin",
        password="Jodranaanu@2804",
        port=5432,
        sslmode="require"
    )

    return conn