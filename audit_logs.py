import sqlite3

DB_NAME = "data/posledger.db"


def view_audit_logs():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT NOT NULL,
        details TEXT,
        log_date TEXT NOT NULL
    )
    """)

    cur.execute("""
    SELECT id, action, details, log_date
    FROM audit_logs
    ORDER BY id DESC
    """)

    rows = cur.fetchall()

    print("\n========== AUDIT LOGS ==========")
    if not rows:
        print("No audit logs found.")
        conn.close()
        return

    for row in rows:
        print("----------------------------------------")
        print(f"ID      : {row['id']}")
        print(f"Action  : {row['action']}")
        print(f"Details : {row['details']}")
        print(f"Date    : {row['log_date']}")

    print("----------------------------------------")

    conn.close()
if __name__ == "__main__":
    view_audit_logs()
