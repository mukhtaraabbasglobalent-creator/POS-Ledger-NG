import sqlite3

DB_NAME = "data/posledger.db"


def overdue_accounts():

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    print("\n========== OVERDUE ACCOUNTS ==========\n")

    cur.execute("""
        SELECT
            cc.id,
            c.fullname,
            cc.balance,
            cc.status,
            cc.created_date
        FROM customer_credit cc
        JOIN customers c
            ON cc.customer_id = c.id
        WHERE cc.balance > 0
        ORDER BY cc.created_date ASC
    """)

    rows = cur.fetchall()

    if not rows:
        print("✅ No overdue accounts.")
        conn.close()
        return

    print("=" * 70)
    print(f"{'ID':<5}{'Customer':<25}{'Balance':<15}{'Status'}")
    print("=" * 70)

    total_balance = 0

    for row in rows:
        print(
            f"{row['id']:<5}"
            f"{row['fullname']:<25}"
            f"₦{row['balance']:,.2f}".ljust(15)
            + row["status"]
        )

        total_balance += row["balance"]

    print("=" * 70)
    print(f"Total Outstanding: ₦{total_balance:,.2f}")
    print("=" * 70)

    conn.close()


if __name__ == "__main__":
    overdue_accounts()
