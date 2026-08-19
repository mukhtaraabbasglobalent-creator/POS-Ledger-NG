import sqlite3
from datetime import datetime

DB_NAME = "data/posledger.db"


def log_action(user, action, details):

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    log_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("""
        INSERT INTO audit_logs
        (
            action,
            details,
            log_date
        )
        VALUES (?, ?, ?)
    """, (
        action,
        f"{user}: {details}",
        log_date
    ))

    conn.commit()
    conn.close()
