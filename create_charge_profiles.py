import sqlite3

DB_NAME = "data/posledger.db"

conn = sqlite3.connect(DB_NAME)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS charge_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_name TEXT NOT NULL,
    provider TEXT NOT NULL,
    transaction_type TEXT NOT NULL,
    min_amount REAL NOT NULL,
    max_amount REAL NOT NULL,
    customer_charge REAL NOT NULL,
    provider_fee REAL NOT NULL
)
""")

conn.commit()
conn.close()

print("✅ charge_profiles table created successfully.")
