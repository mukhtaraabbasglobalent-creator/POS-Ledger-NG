import sqlite3

DB_NAME = "data/posledger.db"

def edit_provider():

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    provider_id = input("Enter Provider ID to edit: ").strip()

    cur.execute(
        "SELECT * FROM providers WHERE id=?",
        (provider_id,)
    )

    row = cur.fetchone()

    if row is None:
        print("\n❌ Provider not found.")
        conn.close()
        return

    print(f"\nCurrent Name: {row['provider_name']}")
    print(f"Current Type: {row['provider_type']}")

    new_name = input("New Provider Name: ").strip()
    new_type = input("New Provider Type: ").strip()

    cur.execute("""
        UPDATE providers
        SET provider_name=?,
            provider_type=?
        WHERE id=?
    """, (
        new_name,
        new_type,
        provider_id
    ))

    conn.commit()
    conn.close()

    print("\n✅ Provider updated successfully.")
