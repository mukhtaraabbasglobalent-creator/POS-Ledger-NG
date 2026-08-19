import sqlite3
from datetime import datetime

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def collection_analytics():
    conn = get_connection()
    cur = conn.cursor()

    print("\n========================================")
    print("       POS LEDGER NG V12")
    print("   COLLECTION PERFORMANCE ANALYTICS")
    print("========================================")

    # ------------------------------------
    # OVERALL CREDIT POSITION
    # ------------------------------------
    cur.execute("""
        SELECT
            COALESCE(SUM(total_amount), 0) AS total_credit,
            COALESCE(SUM(amount_paid), 0) AS total_paid,
            COALESCE(SUM(balance), 0) AS outstanding,
            COUNT(*) AS accounts
        FROM customer_credit
    """)

    position = cur.fetchone()

    total_credit = float(position["total_credit"] or 0)
    total_paid = float(position["total_paid"] or 0)
    outstanding = float(position["outstanding"] or 0)
    accounts = int(position["accounts"] or 0)

    collection_rate = (
        (total_paid / total_credit) * 100
        if total_credit > 0 else 0
    )

    print("\n----------------------------------------")
    print("          COLLECTION POSITION")
    print("----------------------------------------")
    print(f"Credit Issued       : ₦{total_credit:,.2f}")
    print(f"Collected           : ₦{total_paid:,.2f}")
    print(f"Outstanding         : ₦{outstanding:,.2f}")
    print(f"Credit Accounts     : {accounts}")
    print(f"Collection Rate     : {collection_rate:.2f}%")

    # ------------------------------------
    # CUSTOMER PERFORMANCE
    # ------------------------------------
    cur.execute("""
        SELECT
            c.id,
            c.fullname,
            c.phone,
            COALESCE(SUM(cc.total_amount), 0) AS credit,
            COALESCE(SUM(cc.amount_paid), 0) AS paid,
            COALESCE(SUM(cc.balance), 0) AS outstanding
        FROM customers c
        JOIN customer_credit cc
            ON cc.customer_id = c.id
        GROUP BY c.id, c.fullname, c.phone
        ORDER BY outstanding DESC
    """)

    customers = cur.fetchall()

    print("\n========================================")
    print("       CUSTOMER COLLECTION PERFORMANCE")
    print("========================================")

    if not customers:
        print("No customer credit records found.")

    for index, row in enumerate(customers, start=1):

        credit = float(row["credit"] or 0)
        paid = float(row["paid"] or 0)
        debt = float(row["outstanding"] or 0)

        rate = (
            (paid / credit) * 100
            if credit > 0 else 0
        )

        print("----------------------------------------")
        print(f"#{index} {row['fullname']}")
        print(f"Customer ID : {row['id']}")
        print(f"Phone       : {row['phone'] or 'N/A'}")
        print(f"Credit      : ₦{credit:,.2f}")
        print(f"Paid        : ₦{paid:,.2f}")
        print(f"Outstanding : ₦{debt:,.2f}")
        print(f"Collection  : {rate:.2f}%")

        if debt <= 0:
            performance = "🟢 CLEARED"
        elif rate >= 75:
            performance = "🟢 GOOD"
        elif rate >= 50:
            performance = "🟡 MODERATE"
        elif rate >= 25:
            performance = "🟠 NEEDS ATTENTION"
        else:
            performance = "🔴 LOW COLLECTION"

        print(f"Performance : {performance}")

    # ------------------------------------
    # FOLLOW-UP PERFORMANCE
    # ------------------------------------
    cur.execute("""
        SELECT
            COUNT(*) AS total_followups,
            COALESCE(SUM(promised_amount), 0) AS promised
        FROM collection_followups
    """)

    followup = cur.fetchone()

    total_followups = int(
        followup["total_followups"] or 0
    )

    total_promised = float(
        followup["promised"] or 0
    )

    print("\n========================================")
    print("        FOLLOW-UP PERFORMANCE")
    print("========================================")

    print(
        f"Total Follow-ups : {total_followups}"
    )

    print(
        f"Total Promised   : ₦{total_promised:,.2f}"
    )

    # ------------------------------------
    # PROMISE STATUS ANALYSIS
    # ------------------------------------
    cur.execute("""
        SELECT
            UPPER(COALESCE(status, 'UNKNOWN')) AS status,
            COUNT(*) AS count,
            COALESCE(SUM(promised_amount), 0) AS amount
        FROM collection_followups
        GROUP BY UPPER(COALESCE(status, 'UNKNOWN'))
        ORDER BY count DESC
    """)

    promise_statuses = cur.fetchall()

    print("\n----------------------------------------")
    print("          PROMISE STATUS")
    print("----------------------------------------")

    if not promise_statuses:
        print("No promise records found.")

    for row in promise_statuses:

        print(
            f"{row['status']:<15} : "
            f"{row['count']} record(s) — "
            f"₦{float(row['amount'] or 0):,.2f}"
        )

    # ------------------------------------
    # STAFF COLLECTION ACTIVITY
    # ------------------------------------
    cur.execute("""
        SELECT
            staff_name,
            COUNT(*) AS payments,
            COALESCE(SUM(amount), 0) AS collected
        FROM credit_payments
        GROUP BY staff_name
        ORDER BY collected DESC
    """)

    staff_rows = cur.fetchall()

    print("\n========================================")
    print("        STAFF COLLECTION ACTIVITY")
    print("========================================")

    if not staff_rows:
        print("No payment records found.")

    for index, row in enumerate(
        staff_rows,
        start=1
    ):

        print("----------------------------------------")
        print(f"#{index} Staff : {row['staff_name']}")
        print(f"Payments      : {row['payments']}")
        print(
            f"Collected     : "
            f"₦{float(row['collected'] or 0):,.2f}"
        )

    # ------------------------------------
    # MANAGEMENT INSIGHT
    # ------------------------------------
    print("\n========================================")
    print("        MANAGEMENT INSIGHT")
    print("========================================")

    if outstanding <= 0:
        management_status = "🟢 ALL CREDIT CLEARED"

    elif collection_rate >= 75:
        management_status = "🟢 STRONG COLLECTION"

    elif collection_rate >= 50:
        management_status = "🟡 MODERATE COLLECTION"

    elif collection_rate >= 25:
        management_status = "🟠 COLLECTION NEEDS ATTENTION"

    else:
        management_status = "🔴 HIGH RECEIVABLE RISK"

    print(
        f"STATUS : {management_status}"
    )

    print("----------------------------------------")

    if outstanding > 0:
        print(
            f"• ₦{outstanding:,.2f} remains tied up "
            "in customer credit."
        )

    if total_followups > 0:
        print(
            f"• {total_followups} collection follow-up(s) "
            "have been recorded."
        )

    if total_promised > 0:
        print(
            f"• Customers have promised "
            f"₦{total_promised:,.2f}."
        )

    print("----------------------------------------")
    print(
        "READ-ONLY: Financial credit/payment "
        "records were NOT modified."
    )
    print("========================================")

    conn.close()

    input("\nPress Enter to continue...")


if __name__ == "__main__":
    collection_analytics()
