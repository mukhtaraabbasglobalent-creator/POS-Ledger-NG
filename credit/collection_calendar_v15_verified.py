import sqlite3
from datetime import datetime, date

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def collection_calendar():
    conn = get_connection()
    cur = conn.cursor()

    today = date.today()

    print("\n========================================")
    print("       POS LEDGER NG V15")
    print("   COLLECTION CALENDAR & ACTION PLAN")
    print("========================================")

    # ------------------------------------
    # CURRENT RECEIVABLE POSITION
    # ------------------------------------
    totals = cur.execute("""
        SELECT
            COALESCE(SUM(total_amount), 0) AS credit,
            COALESCE(SUM(amount_paid), 0) AS paid,
            COALESCE(SUM(balance), 0) AS balance
        FROM customer_credit
        WHERE balance > 0
    """).fetchone()

    total_credit = float(totals["credit"] or 0)
    total_paid = float(totals["paid"] or 0)
    outstanding = float(totals["balance"] or 0)

    # ------------------------------------
    # CUSTOMER RECEIVABLES
    # ------------------------------------
    customer_rows = cur.execute("""
        SELECT
            cc.customer_id,
            c.fullname,
            c.phone,
            COALESCE(SUM(cc.balance), 0) AS outstanding
        FROM customer_credit cc
        LEFT JOIN customers c
            ON c.id = cc.customer_id
        WHERE cc.balance > 0
        GROUP BY cc.customer_id, c.fullname, c.phone
        ORDER BY outstanding DESC
    """).fetchall()

    # ------------------------------------
    # FOLLOW-UP PROMISES
    # ------------------------------------
    promises = cur.execute("""
        SELECT
            cf.id,
            cf.customer_id,
            cf.credit_id,
            cf.promised_amount,
            cf.promised_date,
            cf.status,
            cf.contact_method,
            cf.staff_name,
            c.fullname,
            c.phone
        FROM collection_followups cf
        LEFT JOIN customers c
            ON c.id = cf.customer_id
        WHERE cf.promised_amount > 0
        ORDER BY cf.promised_date ASC, cf.id ASC
    """).fetchall()

    upcoming = []
    overdue = []
    due_today = []

    for promise in promises:

        try:
            due_date = datetime.strptime(
                promise["promised_date"][:10],
                "%Y-%m-%d"
            ).date()
        except (ValueError, TypeError):
            continue

        item = {
            "id": promise["id"],
            "customer_id": promise["customer_id"],
            "credit_id": promise["credit_id"],
            "customer": promise["fullname"] or "Unknown",
            "phone": promise["phone"] or "N/A",
            "amount": float(
                promise["promised_amount"] or 0
            ),
            "date": due_date,
            "method": promise["contact_method"] or "N/A",
            "staff": promise["staff_name"] or "System",
            "status": promise["status"] or "PROMISE"
        }

        if due_date < today:
            overdue.append(item)

        elif due_date == today:
            due_today.append(item)

        else:
            upcoming.append(item)

    # ------------------------------------
    # OVERALL POSITION
    # ------------------------------------
    print("\n========================================")
    print("        COLLECTION POSITION")
    print("========================================")

    print(
        f"Credit Issued       : "
        f"₦{total_credit:,.2f}"
    )

    print(
        f"Collected           : "
        f"₦{total_paid:,.2f}"
    )

    print(
        f"Outstanding         : "
        f"₦{outstanding:,.2f}"
    )

    collection_rate = (
        total_paid / total_credit * 100
        if total_credit > 0 else 0
    )

    print(
        f"Collection Rate     : "
        f"{collection_rate:.2f}%"
    )

    # ------------------------------------
    # TODAY'S ACTIONS
    # ------------------------------------
    print("\n========================================")
    print("          TODAY'S ACTIONS")
    print("========================================")

    if due_today:

        for index, item in enumerate(
            due_today,
            start=1
        ):
            print("----------------------------------------")
            print(f"#{index} {item['customer']}")
            print(
                f"Customer ID : "
                f"{item['customer_id']}"
            )
            print(
                f"Phone       : "
                f"{item['phone']}"
            )
            print(
                f"Credit ID   : "
                f"{item['credit_id']}"
            )
            print(
                f"Expected    : "
                f"₦{item['amount']:,.2f}"
            )
            print(
                f"Method      : "
                f"{item['method']}"
            )
            print("Action      : COLLECT TODAY")

    else:
        print("No promises are due today.")

    # ------------------------------------
    # UPCOMING COLLECTIONS
    # ------------------------------------
    print("\n========================================")
    print("       UPCOMING COLLECTIONS")
    print("========================================")

    if upcoming:

        for index, item in enumerate(
            upcoming,
            start=1
        ):
            days = (
                item["date"] - today
            ).days

            print("----------------------------------------")
            print(f"#{index} {item['customer']}")
            print(
                f"Customer ID : "
                f"{item['customer_id']}"
            )
            print(
                f"Phone       : "
                f"{item['phone']}"
            )
            print(
                f"Expected    : "
                f"₦{item['amount']:,.2f}"
            )
            print(
                f"Promise Date: "
                f"{item['date']}"
            )
            print(
                f"Days Until  : "
                f"{days}"
            )
            print("Action      : PREPARE FOLLOW-UP")

    else:
        print("No upcoming promises.")

    # ------------------------------------
    # OVERDUE COLLECTIONS
    # ------------------------------------
    print("\n========================================")
    print("        OVERDUE COLLECTIONS")
    print("========================================")

    if overdue:

        for index, item in enumerate(
            overdue,
            start=1
        ):
            days_overdue = (
                today - item["date"]
            ).days

            print("----------------------------------------")
            print(f"#{index} {item['customer']}")
            print(
                f"Customer ID : "
                f"{item['customer_id']}"
            )
            print(
                f"Phone       : "
                f"{item['phone']}"
            )
            print(
                f"Expected    : "
                f"₦{item['amount']:,.2f}"
            )
            print(
                f"Promise Date: "
                f"{item['date']}"
            )
            print(
                f"Days Overdue: "
                f"{days_overdue}"
            )
            print(
                "Action      : URGENT COLLECTION"
            )

    else:
        print("No overdue promises.")

    # ------------------------------------
    # TOP CUSTOMERS OWING
    # ------------------------------------
    print("\n========================================")
    print("        TOP RECEIVABLE ACCOUNTS")
    print("========================================")

    if customer_rows:

        for index, customer in enumerate(
            customer_rows[:5],
            start=1
        ):
            print("----------------------------------------")
            print(
                f"#{index} "
                f"{customer['fullname'] or 'Unknown'}"
            )
            print(
                f"Customer ID : "
                f"{customer['customer_id']}"
            )
            print(
                f"Phone       : "
                f"{customer['phone'] or 'N/A'}"
            )
            print(
                f"Outstanding : "
                f"₦{float(customer['outstanding'] or 0):,.2f}"
            )

    else:
        print("No outstanding customer accounts.")

    # ------------------------------------
    # DAILY EXPECTED COLLECTION
    # ------------------------------------
    print("\n========================================")
    print("       EXPECTED COLLECTION")
    print("========================================")

    today_expected = sum(
        item["amount"] for item in due_today
    )

    upcoming_expected = sum(
        item["amount"] for item in upcoming
    )

    overdue_expected = sum(
        item["amount"] for item in overdue
    )

    print(
        f"Due Today          : "
        f"₦{today_expected:,.2f}"
    )

    print(
        f"Upcoming           : "
        f"₦{upcoming_expected:,.2f}"
    )

    print(
        f"Overdue Promises   : "
        f"₦{overdue_expected:,.2f}"
    )

    # ------------------------------------
    # MANAGEMENT ACTION
    # ------------------------------------
    print("\n========================================")
    print("        MANAGEMENT ACTION PLAN")
    print("========================================")

    if overdue:
        status = "🔴 URGENT COLLECTION REQUIRED"
    elif due_today:
        status = "🟠 COLLECTION ACTION TODAY"
    elif upcoming:
        status = "🟡 PREPARE FOR UPCOMING COLLECTIONS"
    elif outstanding > 0:
        status = "🟠 RECEIVABLES REQUIRE MONITORING"
    else:
        status = "🟢 NO OUTSTANDING RECEIVABLES"

    print(f"STATUS : {status}")
    print("----------------------------------------")

    if overdue:
        print(
            f"• {len(overdue)} overdue promise(s) "
            "require attention."
        )

    if due_today:
        print(
            f"• {len(due_today)} promise(s) "
            "are due today."
        )

    if upcoming:
        print(
            f"• {len(upcoming)} future promise(s) "
            "should be monitored."
        )

    print("----------------------------------------")
    print(
        "READ-ONLY: Credit/payment records "
        "were NOT modified."
    )
    print("========================================")

    conn.close()

    input("\nPress Enter to continue...")


if __name__ == "__main__":
    collection_calendar()
