import sqlite3

DB_NAME = "data/posledger.db"

def get_providers():

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
    SELECT id, provider_name
    FROM providers
    ORDER BY provider_name
    """)

    rows = cur.fetchall()

    conn.close()

    return rows
