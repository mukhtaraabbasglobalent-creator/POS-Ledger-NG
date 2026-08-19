import sqlite3

conn = sqlite3.connect("data/posledger.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS purchases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    purchase_no TEXT UNIQUE NOT NULL,
    supplier_name TEXT NOT NULL,
    product_id INTEGER NOT NULL,
    quantity REAL NOT NULL,
    buying_price REAL NOT NULL,
    total_cost REAL NOT NULL,
    purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(product_id) REFERENCES products(id)
)
""")

conn.commit()
conn.close()

print("✅ Purchases table created successfully.")
