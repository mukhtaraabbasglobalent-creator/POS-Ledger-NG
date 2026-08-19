import sqlite3

conn = sqlite3.connect("data/posledger.db")
cur = conn.cursor()

columns = [
    ("username", "TEXT"),
    ("email", "TEXT"),
    ("phone", "TEXT"),
    ("role", "TEXT DEFAULT 'Admin'"),
    ("email_verified", "INTEGER DEFAULT 0"),
    ("phone_verified", "INTEGER DEFAULT 0"),
    ("twofa_enabled", "INTEGER DEFAULT 0"),
    ("status", "TEXT DEFAULT 'Active'"),
    ("last_login", "TEXT")
]

for name, dtype in columns:
    try:
        cur.execute(f"ALTER TABLE users ADD COLUMN {name} {dtype}")
        print(f"Added: {name}")
    except sqlite3.OperationalError:
        print(f"Already exists: {name}")

conn.commit()
conn.close()

print("Users table updated successfully.")
