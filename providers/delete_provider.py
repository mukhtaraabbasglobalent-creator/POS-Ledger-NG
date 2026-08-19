import sqlite3

DB_NAME = "data/posledger.db"

def delete_provider():

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    provider_id = input("Enter Provider ID to delete: ").strip()

    cur.execute(
        "SELECT * FROM providers WHERE id=?",
        (provider_id,)
    )

    row = cur.fetchone()

    if row is None:
        print("\n❌ Provider not found.")
        conn.close()
        return

    confirm = input(
        f"Delete '{row['provider_name']}'? (y/n): "
    ).strip().lower()

    if confirm == "y":

        cur.execute(
            "DELETE FROM providers WHERE id=?",
            (provider_id,)
        )

        conn.commit()

        print("\n✅ Provider deleted successfully.")

    else:

        print("\nCancelled.")

    conn.close()
