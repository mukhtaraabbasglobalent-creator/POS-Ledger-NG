import sqlite3

DB_NAME = "data/posledger.db"


def credit_report():

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT
            COALESCE(SUM(total_amount),0),
            COALESCE(SUM(amount_paid),0),
            COALESCE(SUM(balance),0)
        FROM customer_credit
    """)

    totals = cur.fetchone()

    cur.execute("""
        SELECT COUNT(*)
        FROM customer_credit
        WHERE status='UNPAID'
    """)
    unpaid = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*)
        FROM customer_credit
        WHERE status='PARTLY PAID'
    """)
    partly = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*)
        FROM customer_credit
        WHERE status='PAID'
    """)
    paid = cur.fetchone()[0]

    print("\n========== CREDIT REPORT ==========\n")

    print(f"Total Credit Sales : ₦{totals[0]:,.2f}")
    print(f"Total Payments     : ₦{totals[1]:,.2f}")
    print(f"Outstanding Debt   : ₦{totals[2]:,.2f}")

    print("----------------------------------")

    print(f"Paid Accounts      : {paid}")
    print(f"Partly Paid        : {partly}")
    print(f"Unpaid Accounts    : {unpaid}")

    print("----------------------------------")

    conn.close()


if __name__ == "__main__":
    credit_report()
