import sqlite3
from datetime import datetime, date

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def collection_forecast():
    conn = get_connection()
    cur = conn.cursor()

    today = date.today()

    print("\n========================================")
    print("       POS LEDGER NG V14")
    print("    COLLECTION FORECAST")
    print("========================================")

    # ------------------------------------
    # OVERALL RECEIVABLES
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
    # PROMISES
    # ------------------------------------
    promises = cur.execute("""
        SELECT
            cf.id,
            cf.customer_id,
            cf.credit_id,
            cf.promised_amount,
            cf.promised_date,
            cf.status,
            c.fullname
        FROM collection_followups cf
        LEFT JOIN customers c
            ON c.id = cf.customer_id
        WHERE cf.promised_amount > 0
        ORDER BY cf.promised_date ASC, cf.id ASC
    """).fetchall()

    upcoming_total = 0.0
    overdue_total = 0.0
    upcoming_count = 0
    overdue_count = 0

    upcoming = []
    overdue = []

    for promise in promises:

        amount = float(
            promise["promised_amount"] or 0
        )

        promised_date = promise["promised_date"]

        try:
            due_date = datetime.strptime(
                promised_date[:10],
                "%Y-%m-%d"
            ).date()
        except (ValueError, TypeError):
            continue

        record = {
            "customer": promise["fullname"] or "Unknown",
            "customer_id": promise["customer_id"],
            "credit_id": promise["credit_id"],
            "amount": amount,
            "date": promised_date
        }

        if due_date >= today:
            upcoming_total += amount
            upcoming_count += 1
            upcoming.append(record)

        else:
            overdue_total += amount
            overdue_count += 1
            overdue.append(record)

    # ------------------------------------
    # UNCOMMITTED RECEIVABLES
    # ------------------------------------
    committed = upcoming_total

    uncommitted = max(
        outstanding - committed,
        0
    )

    forecast_coverage = (
        (committed / outstanding) * 100
        if outstanding > 0 else 0
    )

    # ------------------------------------
    # POSITION
    # ------------------------------------
    print("\n========================================")
    print("       RECEIVABLE POSITION")
    print("========================================")

    print(
        f"Total Credit Issued : "
        f"₦{total_credit:,.2f}"
    )

    print(
        f"Total Paid          : "
        f"₦{total_paid:,.2f}"
    )

    print(
        f"Outstanding         : "
        f"₦{outstanding:,.2f}"
    )

    print(
        f"Promised Collection : "
        f"₦{committed:,.2f}"
    )

    print(
        f"Uncommitted Debt    : "
        f"₦{uncommitted:,.2f}"
    )

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
            print("----------------------------------------")
            print(f"#{index} {item['customer']}")
            print(
                f"Customer ID : "
                f"{item['customer_id']}"
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
                f"Expected Date : "
                f"{item['date']}"
            )

    else:
        print("No upcoming collection promises.")

    # ------------------------------------
    # OVERDUE PROMISES
    # ------------------------------------
    print("\n========================================")
    print("         OVERDUE PROMISES")
    print("========================================")

    if overdue:

        for index, item in enumerate(
            overdue,
            start=1
        ):
            print("----------------------------------------")
            print(f"#{index} {item['customer']}")
            print(
                f"Customer ID : "
                f"{item['customer_id']}"
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
                f"Promise Date : "
                f"{item['date']}"
            )

    else:
        print("No overdue promises.")

    # ------------------------------------
    # FORECAST
    # ------------------------------------
    print("\n========================================")
    print("       COLLECTION FORECAST")
    print("========================================")

    print(
        f"Upcoming Promises : "
        f"{upcoming_count}"
    )

    print(
        f"Expected Collection : "
        f"₦{upcoming_total:,.2f}"
    )

    print(
        f"Overdue Promises  : "
        f"{overdue_count}"
    )

    print(
        f"Overdue Amount    : "
        f"₦{overdue_total:,.2f}"
    )

    print(
        f"Forecast Coverage : "
        f"{forecast_coverage:.2f}%"
    )

    print(
        f"Uncommitted Debt   : "
        f"₦{uncommitted:,.2f}"
    )

    # ------------------------------------
    # MANAGEMENT STATUS
    # ------------------------------------
    print("\n========================================")
    print("       MANAGEMENT FORECAST")
    print("========================================")

    if outstanding <= 0:
        status = "🟢 NO OUTSTANDING RECEIVABLES"

    elif overdue_count > 0:
        status = "🔴 OVERDUE COLLECTION RISK"

    elif forecast_coverage >= 75:
        status = "🟢 STRONG COLLECTION COVERAGE"

    elif forecast_coverage >= 40:
        status = "🟡 MODERATE COLLECTION COVERAGE"

    elif forecast_coverage > 0:
        status = "🟠 LOW COLLECTION COVERAGE"

    else:
        status = "🟠 NO COLLECTION COMMITMENTS"

    print(f"STATUS : {status}")

    print("----------------------------------------")

    if upcoming_total > 0:
        print(
            f"• ₦{upcoming_total:,.2f} "
            "has future collection commitments."
        )

    if uncommitted > 0:
        print(
            f"• ₦{uncommitted:,.2f} "
            "remains without a recorded promise."
        )

    if overdue_total > 0:
        print(
            f"• ₦{overdue_total:,.2f} "
            "is linked to overdue promises."
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
    collection_forecast()
