import sqlite3

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def collection_analytics():
    conn = get_connection()
    cur = conn.cursor()

    print("\n========================================")
    print("       POS LEDGER NG V12.1")
    print("   RECONCILED COLLECTION ANALYTICS")
    print("========================================")

    # ------------------------------------
    # CREDIT POSITION
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
    recorded_paid = float(position["total_paid"] or 0)
    outstanding = float(position["outstanding"] or 0)
    accounts = int(position["accounts"] or 0)

    # ------------------------------------
    # NORMAL PAYMENTS
    # ------------------------------------
    cur.execute("""
        SELECT
            COALESCE(SUM(amount), 0) AS total
        FROM credit_payments
    """)

    normal_paid = float(
        cur.fetchone()["total"] or 0
    )

    # ------------------------------------
    # HISTORICAL PAYMENTS
    # ------------------------------------
    cur.execute("""
        SELECT
            COALESCE(SUM(amount), 0) AS total
        FROM credit_reconciliations
        WHERE UPPER(reconciliation_type)
              = 'HISTORICAL_PAYMENT'
    """)

    historical_paid = float(
        cur.fetchone()["total"] or 0
    )

    reconciled_paid = (
        normal_paid + historical_paid
    )

    collection_rate = (
        (reconciled_paid / total_credit) * 100
        if total_credit > 0 else 0
    )

    # ------------------------------------
    # RECONCILIATION DIFFERENCE
    # ------------------------------------
    difference = (
        recorded_paid - reconciled_paid
    )

    print("\n----------------------------------------")
    print("       RECONCILED COLLECTION POSITION")
    print("----------------------------------------")

    print(
        f"Credit Issued       : ₦{total_credit:,.2f}"
    )

    print(
        f"Recorded Paid       : ₦{recorded_paid:,.2f}"
    )

    print(
        f"Normal Payments     : ₦{normal_paid:,.2f}"
    )

    print(
        f"Historical Payments : ₦{historical_paid:,.2f}"
    )

    print(
        f"Total Collected     : ₦{reconciled_paid:,.2f}"
    )

    print(
        f"Outstanding         : ₦{outstanding:,.2f}"
    )

    print(
        f"Credit Accounts     : {accounts}"
    )

    print(
        f"Collection Rate     : {collection_rate:.2f}%"
    )

    print("\n========================================")
    print("          RECONCILIATION CHECK")
    print("========================================")

    print(
        f"Recorded Paid : ₦{recorded_paid:,.2f}"
    )

    print(
        f"Payment History : ₦{reconciled_paid:,.2f}"
    )

    print(
        f"Difference     : ₦{difference:,.2f}"
    )

    if abs(difference) <= 0.000001:
        print("Integrity      : ✅ MATCH")
    else:
        print("Integrity      : ⚠️ DIFFERENCE DETECTED")

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

    for index, row in enumerate(
        customers,
        start=1
    ):

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

        print(
            f"Performance : {performance}"
        )

    # ------------------------------------
    # FOLLOW-UP ANALYSIS
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
    # STAFF NORMAL PAYMENTS
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
    print("       NORMAL PAYMENT ACTIVITY")
    print("========================================")

    for index, row in enumerate(
        staff_rows,
        start=1
    ):

        print("----------------------------------------")
        print(
            f"#{index} Staff : {row['staff_name']}"
        )
        print(
            f"Payments      : {row['payments']}"
        )
        print(
            f"Collected     : "
            f"₦{float(row['collected'] or 0):,.2f}"
        )

    # ------------------------------------
    # HISTORICAL PAYMENT ACTIVITY
    # ------------------------------------
    cur.execute("""
        SELECT
            staff_name,
            COUNT(*) AS records,
            COALESCE(SUM(amount), 0) AS collected
        FROM credit_reconciliations
        WHERE UPPER(reconciliation_type)
              = 'HISTORICAL_PAYMENT'
        GROUP BY staff_name
        ORDER BY collected DESC
    """)

    historical_rows = cur.fetchall()

    print("\n========================================")
    print("      HISTORICAL PAYMENT ACTIVITY")
    print("========================================")

    for index, row in enumerate(
        historical_rows,
        start=1
    ):

        print("----------------------------------------")
        print(
            f"#{index} Staff : {row['staff_name']}"
        )
        print(
            f"Records       : {row['records']}"
        )
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
        status = "🟢 ALL CREDIT CLEARED"
    elif collection_rate >= 75:
        status = "🟢 STRONG COLLECTION"
    elif collection_rate >= 50:
        status = "🟡 MODERATE COLLECTION"
    elif collection_rate >= 25:
        status = "🟠 COLLECTION NEEDS ATTENTION"
    else:
        status = "🔴 HIGH RECEIVABLE RISK"

    print(f"STATUS : {status}")

    print("----------------------------------------")

    print(
        f"• ₦{reconciled_paid:,.2f} total collection "
        "is recognized."
    )

    print(
        f"• ₦{outstanding:,.2f} remains outstanding."
    )

    if total_followups:
        print(
            f"• {total_followups} follow-up(s) recorded."
        )

    if total_promised:
        print(
            f"• ₦{total_promised:,.2f} promised."
        )

    print("----------------------------------------")
    print(
        "READ-ONLY: V6 credit/payment records "
        "were NOT modified."
    )
    print("========================================")

    conn.close()

    input("\nPress Enter to continue...")


if __name__ == "__main__":
    collection_analytics()
