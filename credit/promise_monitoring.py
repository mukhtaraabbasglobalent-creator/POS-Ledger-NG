import sqlite3
from datetime import datetime, date

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def promise_monitoring():
    conn = get_connection()
    cur = conn.cursor()

    today = date.today()

    print("\n========================================")
    print("       POS LEDGER NG V11.2")
    print("       PROMISE MONITORING")
    print("========================================")

    cur.execute("""
        SELECT
            f.*,
            c.fullname,
            c.phone,
            cc.total_amount,
            cc.amount_paid,
            cc.balance AS credit_balance
        FROM collection_followups f
        JOIN customers c
            ON c.id = f.customer_id
        LEFT JOIN customer_credit cc
            ON cc.id = f.credit_id
        WHERE UPPER(f.status) IN ('PROMISE', 'PROMISED')
        ORDER BY f.promised_date ASC, f.id ASC
    """)

    promises = cur.fetchall()

    print("\n========================================")
    print("          PROMISE MONITOR")
    print("========================================")

    if not promises:
        print("----------------------------------------")
        print("No active payment promises found.")
        print("----------------------------------------")

    upcoming = 0
    due_today = 0
    overdue = 0
    completed = 0

    for index, row in enumerate(promises, start=1):

        promised_amount = float(
            row["promised_amount"] or 0
        )

        credit_balance = float(
            row["credit_balance"] or 0
        )

        promised_date_text = row["promised_date"]

        try:
            promised_date = datetime.strptime(
                promised_date_text,
                "%Y-%m-%d"
            ).date()
        except (TypeError, ValueError):
            promised_date = None

        # --------------------------------
        # DETERMINE PROMISE STATUS
        # --------------------------------

        if credit_balance <= 0:
            monitor_status = "COMPLETED"
            completed += 1

        elif promised_date is None:
            monitor_status = "NO DATE"

        elif promised_date < today:
            monitor_status = "OVERDUE"
            overdue += 1

        elif promised_date == today:
            monitor_status = "DUE TODAY"
            due_today += 1

        else:
            monitor_status = "UPCOMING"
            upcoming += 1

        print("----------------------------------------")
        print(f"#{index} {row['fullname']}")
        print("----------------------------------------")
        print(f"Customer ID      : {row['customer_id']}")
        print(f"Credit ID        : {row['credit_id']}")
        print(f"Phone            : {row['phone'] or 'N/A'}")
        print(f"Staff            : {row['staff_name'] or 'System'}")
        print(f"Promised Amount  : ₦{promised_amount:,.2f}")
        print(f"Promised Date    : {promised_date_text or 'N/A'}")
        print(f"Current Debt     : ₦{credit_balance:,.2f}")
        print(f"Monitor Status   : {monitor_status}")
        print(f"Notes            : {row['notes'] or 'N/A'}")

    # --------------------------------
    # MANAGEMENT SUMMARY
    # --------------------------------

    print("\n========================================")
    print("        PROMISE MONITORING SUMMARY")
    print("========================================")

    print(f"Upcoming Promises : {upcoming}")
    print(f"Due Today         : {due_today}")
    print(f"Overdue Promises  : {overdue}")
    print(f"Completed         : {completed}")

    print("----------------------------------------")

    if overdue > 0:
        status = "🔴 OVERDUE PROMISES REQUIRE ACTION"
    elif due_today > 0:
        status = "🟠 PROMISES DUE TODAY"
    elif upcoming > 0:
        status = "🟢 PROMISES ON TRACK"
    else:
        status = "⚪ NO ACTIVE PROMISES"

    print(f"STATUS : {status}")

    print("----------------------------------------")
    print(
        "READ-ONLY: Credit/payment records "
        "were NOT modified."
    )

    print("========================================")

    conn.close()

    input("\nPress Enter to continue...")


if __name__ == "__main__":
    promise_monitoring()
