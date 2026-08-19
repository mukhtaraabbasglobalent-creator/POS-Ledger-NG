import sqlite3
from datetime import datetime, date

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def parse_date(value):
    if not value:
        return None

    try:
        return datetime.strptime(
            value[:10],
            "%Y-%m-%d"
        ).date()
    except ValueError:
        return None


def get_customer_name(cur, customer_id):
    row = cur.execute("""
        SELECT fullname
        FROM customers
        WHERE id = ?
    """, (customer_id,)).fetchone()

    return row["fullname"] if row else "Unknown"


def get_payment_total(cur, customer_id, credit_id):
    normal = cur.execute("""
        SELECT COALESCE(SUM(amount), 0) AS total
        FROM credit_payments
        WHERE customer_id = ?
          AND credit_id = ?
    """, (
        customer_id,
        credit_id
    )).fetchone()["total"]

    historical = cur.execute("""
        SELECT COALESCE(SUM(amount), 0) AS total
        FROM credit_reconciliations
        WHERE customer_id = ?
          AND credit_id = ?
          AND UPPER(reconciliation_type)
              = 'HISTORICAL_PAYMENT'
    """, (
        customer_id,
        credit_id
    )).fetchone()["total"]

    return float(normal or 0) + float(historical or 0)


def promise_effectiveness():
    conn = get_connection()
    cur = conn.cursor()

    today = date.today()

    print("\n========================================")
    print("       POS LEDGER NG V13")
    print("  PROMISE FULFILLMENT & EFFECTIVENESS")
    print("========================================")

    # ------------------------------------
    # LOAD PROMISES
    # ------------------------------------
    promises = cur.execute("""
        SELECT *
        FROM collection_followups
        WHERE promised_amount > 0
        ORDER BY promised_date ASC, id ASC
    """).fetchall()

    print("\n========================================")
    print("          PROMISE ANALYSIS")
    print("========================================")

    if not promises:
        print("No payment promises found.")

    fulfilled = 0
    partial = 0
    missed = 0
    upcoming = 0

    total_promised = 0.0
    total_matched = 0.0

    results = []

    for index, promise in enumerate(
        promises,
        start=1
    ):

        customer_id = promise["customer_id"]
        credit_id = promise["credit_id"]

        promised_amount = float(
            promise["promised_amount"] or 0
        )

        promised_date = parse_date(
            promise["promised_date"]
        )

        customer_name = get_customer_name(
            cur,
            customer_id
        )

        actual_paid = get_payment_total(
            cur,
            customer_id,
            credit_id
        )

        total_promised += promised_amount

        # --------------------------------
        # Determine status
        # --------------------------------
        if promised_date and promised_date > today:
            status = "UPCOMING"
            upcoming += 1

        elif actual_paid >= promised_amount:
            status = "FULFILLED"
            fulfilled += 1

        elif actual_paid > 0:
            status = "PARTIALLY FULFILLED"
            partial += 1

        else:
            status = "MISSED"
            missed += 1

        matched = min(
            actual_paid,
            promised_amount
        )

        total_matched += matched

        results.append({
            "customer": customer_name,
            "customer_id": customer_id,
            "credit_id": credit_id,
            "promised": promised_amount,
            "paid": actual_paid,
            "date": promise["promised_date"],
            "status": status
        })

        print("----------------------------------------")
        print(f"#{index} {customer_name}")
        print(f"Customer ID     : {customer_id}")
        print(f"Credit ID       : {credit_id}")
        print(
            f"Promised Amount : "
            f"₦{promised_amount:,.2f}"
        )
        print(
            f"Matched Payment : "
            f"₦{matched:,.2f}"
        )
        print(
            f"Promised Date   : "
            f"{promise['promised_date']}"
        )
        print(f"Status          : {status}")
        print(
            f"Staff           : "
            f"{promise['staff_name']}"
        )

    # ------------------------------------
    # EFFECTIVENESS
    # ------------------------------------
    fulfillment_rate = (
        (total_matched / total_promised) * 100
        if total_promised > 0 else 0
    )

    print("\n========================================")
    print("       PROMISE EFFECTIVENESS")
    print("========================================")

    print(
        f"Total Promised     : "
        f"₦{total_promised:,.2f}"
    )

    print(
        f"Matched Payments   : "
        f"₦{total_matched:,.2f}"
    )

    print(
        f"Fulfillment Rate   : "
        f"{fulfillment_rate:.2f}%"
    )

    print("\n----------------------------------------")
    print("          PROMISE COUNTS")
    print("----------------------------------------")

    print(
        f"Fulfilled          : {fulfilled}"
    )

    print(
        f"Partially Fulfilled: {partial}"
    )

    print(
        f"Missed             : {missed}"
    )

    print(
        f"Upcoming           : {upcoming}"
    )

    # ------------------------------------
    # MANAGEMENT ASSESSMENT
    # ------------------------------------
    print("\n========================================")
    print("       COLLECTION EFFECTIVENESS")
    print("========================================")

    if total_promised == 0:
        effectiveness = "⚪ NO PROMISE DATA"

    elif fulfillment_rate >= 80:
        effectiveness = "🟢 EXCELLENT"

    elif fulfillment_rate >= 60:
        effectiveness = "🟢 GOOD"

    elif fulfillment_rate >= 40:
        effectiveness = "🟡 MODERATE"

    elif fulfillment_rate > 0:
        effectiveness = "🟠 WEAK"

    else:
        effectiveness = "🔴 NO FULFILLMENT"

    print(
        f"STATUS : {effectiveness}"
    )

    print("----------------------------------------")

    if upcoming:
        print(
            f"• {upcoming} promise(s) are still upcoming."
        )

    if fulfilled:
        print(
            f"• {fulfilled} promise(s) have been fulfilled."
        )

    if partial:
        print(
            f"• {partial} promise(s) are partially fulfilled."
        )

    if missed:
        print(
            f"• {missed} promise(s) require collection attention."
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
    promise_effectiveness()
