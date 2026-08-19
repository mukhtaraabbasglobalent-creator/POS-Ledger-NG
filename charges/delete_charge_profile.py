import sqlite3

DB_NAME = "data/posledger.db"

def delete_charge_profile():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT id, profile_name, provider FROM charge_profiles ORDER BY id")
    rows = cur.fetchall()

    if not rows:
        print("\nNo charge profiles found.")
        conn.close()
        return

    print("\n========== CHARGE PROFILES ==========")

    for row in rows:
        print(f"{row['id']}. {row['profile_name']} ({row['provider']})")

    try:
        profile_id = int(input("\nEnter Profile ID to delete: "))
    except ValueError:
        print("❌ Invalid ID.")
        conn.close()
        return

    cur.execute("DELETE FROM charge_profiles WHERE id=?", (profile_id,))
    conn.commit()

    if cur.rowcount > 0:
        print("✅ Charge profile deleted successfully.")
    else:
        print("❌ Profile not found.")

    conn.close()
