import sqlite3

conn = sqlite3.connect("data/posledger.db")
cur = conn.cursor()

cur.execute("PRAGMA table_info(products)")

for row in cur.fetchall():
    print(row)

conn.close()
