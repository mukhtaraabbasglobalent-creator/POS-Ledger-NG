import sqlite3

DB_NAME = "data/posledger.db"


def view_providers():

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
    SELECT *
    FROM providers
    ORDER BY provider_name
    """)

    rows = cur.fetchall()

    print("\n========== PROVIDERS ==========")

    if not rows:
        print("No providers found.")
        conn.close()
        return

    for row in rows:

        print("--------------------------------")
        print(f"ID      : {row['id']}")
        print(f"Provider: {row['provider_name']}")
        print(f"Type    : {row['provider_type']}")
        print(f"Status  : {row['status']}")

    conn.close()
