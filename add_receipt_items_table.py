import sqlite3

DB_NAME = "data/posledger.db"

conn = sqlite3.connect(DB_NAME)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS receipt_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    receipt_no TEXT NOT NULL,

    product_id INTEGER,

    product_name TEXT NOT NULL,

    quantity REAL NOT NULL,

    unit_price REAL NOT NULL,

    line_total REAL NOT NULL
)
""")

conn.commit()
conn.close()

print("✅ receipt_items table created successfully.")
