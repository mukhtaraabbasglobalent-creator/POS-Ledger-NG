import sqlite3
from datetime import datetime, date

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def executive_receivables():
    conn = get_connection()
    cur = conn.cursor()

    today = date.today()

    print("\n========================================")
    print("       POS LEDGER NG V16")
    print("   EXECUTIVE RECEIVABLES DASHBOARD")
    print("========================================")

    # ------------------------------------
    # RECEIVABLE POSITION
    # ------------------------------------
    position = cur.execute("""
        SELECT
            COALESCE(SUM(total_amount), 0) AS credit,
            COALESCE(SUM(amount_paid), 0) AS paid,
            COALESCE(SUM(balance), 0) AS outstanding,
            COUNT(*) AS accounts
        FROM customer_credit
        WHERE balance > 0
    """).fetchone()

    credit = float(position["credit"] or 0)
    paid = float(position["paid"] or 0)
    outstanding = float(position["outstanding"] or 0)
    accounts = int(position["accounts"] or 0)

    collection_rate = (
        paid / credit * 100
        if credit > 0 else 0
    )

    # ------------------------------------
    # CUSTOMERS OWING
    # ------------------------------------
    customer_count = cur.execute("""
        SELECT COUNT(DISTINCT customer_id)
        FROM customer_credit
        WHERE balance > 0
    """).fetchone()[0]

    # ------------------------------------
    # PROMISE ANALYSIS
    # ------------------------------------
    promises = cur.execute("""
        SELECT
            promised_amount,
            promised_date
        FROM collection_followups
        WHERE promised_amount > 0
    """).fetchall()

    upcoming_amount = 0.0
    overdue_amount = 0.0
    upcoming_count = 0
    overdue_count = 0

    for row in promises:

        amount = float(row["promised_amount"] or 0)

        try:
            promise_date = datetime.strptime(
                row["promised_date"][:10],
                "%Y-%m-%d"
            ).date()
        except (ValueError, TypeError):
            continue

        if promise_date >= today:
            upcoming_amount += amount
            upcoming_count += 1
        else:
            overdue_amount += amount
            overdue_count += 1

    # ------------------------------------
    # FORECAST COVERAGE
    # ------------------------------------
    forecast_coverage = (
        upcoming_amount / outstanding * 100
        if outstanding > 0 else 0
    )

    uncommitted = max(
        outstanding - upcoming_amount,
        0
    )

    # ------------------------------------
    # TOP DEBTORS
    # ------------------------------------
    debtors = cur.execute("""
        SELECT
            cc.customer_id,
            c.fullname,
            c.phone,
            SUM(cc.balance) AS outstanding
        FROM customer_credit cc
        LEFT JOIN customers c
            ON c.id = cc.customer_id
        WHERE cc.balance > 0
        GROUP BY
            cc.customer_id,
            c.fullname,
            c.phone
        ORDER BY outstanding DESC
        LIMIT 5
    """).fetchall()

    # ------------------------------------
    # MAIN POSITION
    # ------------------------------------
    print("\n========================================")
    print("        FINANCIAL POSITION")
    print("========================================")

    print(
        f"Credit Issued       : "
        f"₦{credit:,.2f}"
    )

    print(
        f"Collected           : "
        f"₦{paid:,.2f}"
    )

    print(
        f"Outstanding         : "
        f"₦{outstanding:,.2f}"
    )

    print(
        f"Collection Rate     : "
        f"{collection_rate:.2f}%"
    )

    print(
        f"Open Credit Accounts: "
        f"{accounts}"
    )

    print(
        f"Customers Owing    : "
        f"{customer_count}"
    )

    # ------------------------------------
    # COLLECTION INTELLIGENCE
    # ------------------------------------
    print("\n========================================")
    print("      COLLECTION INTELLIGENCE")
    print("========================================")

    print(
        f"Upcoming Promises   : "
        f"{upcoming_count}"
    )

    print(
        f"Expected Collection : "
        f"₦{upcoming_amount:,.2f}"
    )

    print(
        f"Overdue Promises    : "
        f"{overdue_count}"
    )

    print(
        f"Overdue Amount      : "
        f"₦{overdue_amount:,.2f}"
    )

    print(
        f"Forecast Coverage   : "
        f"{forecast_coverage:.2f}%"
    )

    print(
        f"Uncommitted Debt    : "
        f"₦{uncommitted:,.2f}"
    )

    # ------------------------------------
    # TOP DEBTORS
    # ------------------------------------
    print("\n========================================")
    print("             TOP DEBTORS")
    print("========================================")

    if debtors:

        for index, debtor in enumerate(
            debtors,
            start=1
        ):
            debtor_amount = float(
                debtor["outstanding"] or 0
            )

            print("----------------------------------------")
            print(
                f"#{index} "
                f"{debtor['fullname'] or 'Unknown'}"
            )
            print(
                f"Customer ID : "
                f"{debtor['customer_id']}"
            )
            print(
                f"Phone       : "
                f"{debtor['phone'] or 'N/A'}"
            )
            print(
                f"Outstanding : "
                f"₦{debtor_amount:,.2f}"
            )

    else:
        print("No outstanding debtors.")

    # ------------------------------------
    # MANAGEMENT STATUS
    # ------------------------------------
    print("\n========================================")
    print("       EXECUTIVE MANAGEMENT STATUS")
    print("========================================")

    if outstanding <= 0:
        status = "🟢 HEALTHY — NO RECEIVABLE EXPOSURE"

    elif overdue_count > 0:
        status = "🔴 HIGH COLLECTION RISK"

    elif forecast_coverage >= 75:
        status = "🟢 STRONG COLLECTION COVERAGE"

    elif forecast_coverage >= 40:
        status = "🟡 MODERATE COLLECTION COVERAGE"

    else:
        status = "🟠 COLLECTION NEEDS ATTENTION"

    print(f"STATUS : {status}")

    print("----------------------------------------")

    if outstanding > 0:
        print(
            f"• ₦{outstanding:,.2f} remains outstanding."
        )

    if upcoming_amount > 0:
        print(
            f"• ₦{upcoming_amount:,.2f} "
            "has future collection commitments."
        )

    if uncommitted > 0:
        print(
            f"• ₦{uncommitted:,.2f} "
            "has no recorded future promise."
        )

    if overdue_amount > 0:
        print(
            f"• ₦{overdue_amount:,.2f} "
            "is connected to overdue promises."
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
    executive_receivables()
