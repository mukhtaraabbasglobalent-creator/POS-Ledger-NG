import sqlite3

DB_NAME = "data/posledger.db"

conn = sqlite3.connect(DB_NAME)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS providers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_name TEXT UNIQUE NOT NULL,
    provider_type TEXT NOT NULL,
    status TEXT DEFAULT 'Active'
)
""")

conn.commit()
conn.close()

print("✅ providers table created successfully.")
