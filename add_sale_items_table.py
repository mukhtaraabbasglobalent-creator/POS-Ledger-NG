import sqlite3
import os

DB = "data/posledger.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS sale_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    product_name TEXT NOT NULL,
    sku TEXT,
    quantity REAL NOT NULL,
    buying_price REAL NOT NULL,
    selling_price REAL NOT NULL,
    line_subtotal REAL NOT NULL,
    line_cogs REAL NOT NULL,
    line_profit REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (sale_id) REFERENCES sales(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
)
""")

cur.execute("""
CREATE INDEX IF NOT EXISTS idx_sale_items_sale_id
ON sale_items(sale_id)
""")

cur.execute("""
CREATE INDEX IF NOT EXISTS idx_sale_items_product_id
ON sale_items(product_id)
""")

conn.commit()
conn.close()

print("✅ sale_items table ready.")
