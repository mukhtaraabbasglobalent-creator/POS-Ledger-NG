import sqlite3
from datetime import datetime, date

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def customer_collection_workspace():
    conn = get_connection()
    cur = conn.cursor()

    print("\n========================================")
    print("       POS LEDGER NG V17")
    print("   CUSTOMER COLLECTION WORKSPACE")
    print("========================================")

    search = input("Enter Customer ID or Name: ").strip()

    if not search:
        print("No customer entered.")
        conn.close()
        input("\nPress Enter to continue...")
        return

    customer = None

    if search.isdigit():
        customer = cur.execute(
            """
            SELECT *
            FROM customers
            WHERE id = ?
            LIMIT 1
            """,
            (int(search),)
        ).fetchone()
    else:
        customer = cur.execute(
            """
            SELECT *
            FROM customers
            WHERE fullname LIKE ?
            ORDER BY id
            LIMIT 1
            """,
            (f"%{search}%",)
        ).fetchone()

    if not customer:
        print("\nCustomer not found.")
        conn.close()
        input("\nPress Enter to continue...")
        return

    customer_id = customer["id"]
    customer_name = customer["fullname"] or "Unknown"
    phone = customer["phone"] or "N/A"

    # ------------------------------------
    # CUSTOMER CREDIT POSITION
    # ------------------------------------
    credit = cur.execute(
        """
        SELECT
            COALESCE(SUM(total_amount), 0) AS total_credit,
            COALESCE(SUM(amount_paid), 0) AS total_paid,
            COALESCE(SUM(balance), 0) AS outstanding,
            COUNT(*) AS credit_accounts
        FROM customer_credit
        WHERE customer_id = ?
        """,
        (customer_id,)
    ).fetchone()

    total_credit = float(credit["total_credit"] or 0)
    total_paid = float(credit["total_paid"] or 0)
    outstanding = float(credit["outstanding"] or 0)
    credit_accounts = int(credit["credit_accounts"] or 0)

    collection_rate = (
        total_paid / total_credit * 100
        if total_credit > 0 else 0
    )

    # ------------------------------------
    # OLDEST OPEN DEBT
    # ------------------------------------
    oldest = cur.execute(
        """
        SELECT created_date
        FROM customer_credit
        WHERE customer_id = ?
          AND balance > 0
        ORDER BY created_date ASC
        LIMIT 1
        """,
        (customer_id,)
    ).fetchone()

    debt_age = 0

    if oldest and oldest["created_date"]:
        try:
            created = datetime.strptime(
                oldest["created_date"][:19],
                "%Y-%m-%d %H:%M:%S"
            ).date()

            debt_age = max(
                (date.today() - created).days,
                0
            )
        except (ValueError, TypeError):
            debt_age = 0

    # ------------------------------------
    # CREDIT LIMIT
    # ------------------------------------
    credit_limit = 0.0

    if "credit_limit" in customer.keys():
        if customer["credit_limit"] is not None:
            credit_limit = float(customer["credit_limit"])

    credit_used = (
        outstanding / credit_limit * 100
        if credit_limit > 0 else 0
    )

    available_credit = max(
        credit_limit - outstanding,
        0
    )

    # ------------------------------------
    # FOLLOW-UPS
    # ------------------------------------
    followups = cur.execute(
        """
        SELECT *
        FROM collection_followups
        WHERE customer_id = ?
        ORDER BY contact_date DESC, id DESC
        """,
        (customer_id,)
    ).fetchall()

    total_followups = len(followups)

    promised_amount = sum(
        float(row["promised_amount"] or 0)
        for row in followups
        if row["promised_amount"] is not None
    )

    # ------------------------------------
    # NORMAL PAYMENT HISTORY
    # ------------------------------------
    payments = cur.execute(
        """
        SELECT *
        FROM credit_payments
        WHERE customer_id = ?
        ORDER BY payment_date DESC, id DESC
        """,
        (customer_id,)
    ).fetchall()

    normal_payment_total = sum(
        float(row["amount"] or 0)
        for row in payments
    )

    # ------------------------------------
    # HISTORICAL PAYMENTS
    # ------------------------------------
    historical = cur.execute(
        """
        SELECT *
        FROM credit_reconciliations
        WHERE customer_id = ?
          AND reconciliation_type = 'HISTORICAL_PAYMENT'
        ORDER BY reconciliation_date DESC, id DESC
        """,
        (customer_id,)
    ).fetchall()

    historical_total = sum(
        float(row["amount"] or 0)
        for row in historical
    )

    # ------------------------------------
    # OPEN CREDIT ACCOUNTS
    # ------------------------------------
    open_credits = cur.execute(
        """
        SELECT *
        FROM customer_credit
        WHERE customer_id = ?
          AND balance > 0
        ORDER BY created_date ASC
        """,
        (customer_id,)
    ).fetchall()

    # ------------------------------------
    # PROMISE STATUS
    # ------------------------------------
    today = date.today()

    upcoming_promises = []
    overdue_promises = []

    for row in followups:
        amount = float(row["promised_amount"] or 0)
        promised_date = row["promised_date"]

        if not promised_date or amount <= 0:
            continue

        try:
            pdate = datetime.strptime(
                promised_date[:10],
                "%Y-%m-%d"
            ).date()
        except (ValueError, TypeError):
            continue

        if pdate >= today:
            upcoming_promises.append(row)
        else:
            overdue_promises.append(row)

    # ------------------------------------
    # RISK / ACTION
    # ------------------------------------
    if outstanding <= 0:
        risk = "🟢 CLEARED"
        action = "NO COLLECTION ACTION REQUIRED"

    elif overdue_promises:
        risk = "🔴 HIGH RISK"
        action = "IMMEDIATE COLLECTION FOLLOW-UP"

    elif debt_age >= 90:
        risk = "🔴 HIGH RISK"
        action = "ESCALATED COLLECTION"

    elif debt_age >= 31:
        risk = "🟠 MEDIUM-HIGH RISK"
        action = "PRIORITY COLLECTION"

    elif credit_used >= 75:
        risk = "🟠 HIGH CREDIT UTILIZATION"
        action = "RESTRICT NEW CREDIT / MONITOR"

    elif upcoming_promises:
        risk = "🟡 PROMISE ACTIVE"
        action = "MONITOR PROMISED PAYMENT"

    else:
        risk = "🟢 LOW RISK"
        action = "NORMAL COLLECTION"

    # ------------------------------------
    # CUSTOMER INFORMATION
    # ------------------------------------
    print("\n========================================")
    print("       CUSTOMER INFORMATION")
    print("========================================")

    print(f"Customer ID   : {customer_id}")
    print(f"Customer Name : {customer_name}")
    print(f"Phone         : {phone}")

    # ------------------------------------
    # COLLECTION POSITION
    # ------------------------------------
    print("\n========================================")
    print("        COLLECTION POSITION")
    print("========================================")

    print(f"Total Credit     : ₦{total_credit:,.2f}")
    print(f"Total Paid       : ₦{total_paid:,.2f}")
    print(f"Outstanding      : ₦{outstanding:,.2f}")
    print(f"Credit Accounts  : {credit_accounts}")
    print(f"Collection Rate  : {collection_rate:.2f}%")
    print(f"Oldest Debt Age  : {debt_age} day(s)")

    if credit_limit > 0:
        print(f"Credit Limit     : ₦{credit_limit:,.2f}")
        print(f"Credit Used      : {credit_used:.2f}%")
        print(f"Available Credit : ₦{available_credit:,.2f}")

    # ------------------------------------
    # OPEN DEBTS
    # ------------------------------------
    print("\n========================================")
    print("             OPEN DEBTS")
    print("========================================")

    if open_credits:
        for index, row in enumerate(open_credits, 1):
            print("----------------------------------------")
            print(f"Credit #{index}")
            print(f"Credit ID : {row['id']}")
            print(f"Original  : ₦{float(row['total_amount'] or 0):,.2f}")
            print(f"Paid      : ₦{float(row['amount_paid'] or 0):,.2f}")
            print(f"Balance   : ₦{float(row['balance'] or 0):,.2f}")
            print(f"Status    : {row['status']}")
            print(f"Date      : {row['created_date']}")
    else:
        print("No open debts.")

    # ------------------------------------
    # PAYMENT ACTIVITY
    # ------------------------------------
    print("\n========================================")
    print("          PAYMENT ACTIVITY")
    print("========================================")

    print(f"Normal Payments     : ₦{normal_payment_total:,.2f}")
    print(f"Historical Payments : ₦{historical_total:,.2f}")
    print(
        f"Total Recognized    : "
        f"₦{normal_payment_total + historical_total:,.2f}"
    )

    # ------------------------------------
    # FOLLOW-UP HISTORY
    # ------------------------------------
    print("\n========================================")
    print("          COLLECTION FOLLOW-UP")
    print("========================================")

    print(f"Follow-ups Recorded : {total_followups}")
    print(f"Promised Amount     : ₦{promised_amount:,.2f}")

    if followups:
        for index, row in enumerate(followups[:5], 1):
            print("----------------------------------------")
            print(f"Follow-up #{index}")
            print(f"Date      : {row['contact_date']}")
            print(f"Method    : {row['contact_method']}")
            print(
                f"Promised  : "
                f"₦{float(row['promised_amount'] or 0):,.2f}"
            )
            print(f"Promise   : {row['promised_date']}")
            print(f"Status    : {row['status']}")
            print(f"Staff     : {row['staff_name']}")

    # ------------------------------------
    # PROMISE STATUS
    # ------------------------------------
    print("\n========================================")
    print("          PROMISE STATUS")
    print("========================================")

    print(f"Upcoming Promises : {len(upcoming_promises)}")
    print(f"Overdue Promises  : {len(overdue_promises)}")

    if upcoming_promises:
        for row in upcoming_promises:
            print("----------------------------------------")
            print(
                f"Expected : "
                f"₦{float(row['promised_amount'] or 0):,.2f}"
            )
            print(f"Date     : {row['promised_date']}")

    # ------------------------------------
    # COLLECTION RISK
    # ------------------------------------
    print("\n========================================")
    print("        COLLECTION RISK")
    print("========================================")

    print(f"Risk Status : {risk}")
    print(f"Debt Age    : {debt_age} day(s)")
    print(f"Credit Used : {credit_used:.2f}%")

    # ------------------------------------
    # RECOMMENDED ACTION
    # ------------------------------------
    print("\n========================================")
    print("      RECOMMENDED ACTION")
    print("========================================")

    print(f"ACTION : {action}")

    # ------------------------------------
    # MANAGEMENT SUMMARY
    # ------------------------------------
    print("\n========================================")
    print("       MANAGEMENT SUMMARY")
    print("========================================")

    if outstanding <= 0:
        summary = "ACCOUNT CLEARED"
    elif overdue_promises:
        summary = "IMMEDIATE COLLECTION ATTENTION REQUIRED"
    elif upcoming_promises:
        summary = "MONITOR CUSTOMER PROMISE"
    elif debt_age >= 31:
        summary = "PRIORITY COLLECTION REQUIRED"
    else:
        summary = "NORMAL COLLECTION MONITORING"

    print(f"STATUS : {summary}")
    print("----------------------------------------")
    print(f"Outstanding : ₦{outstanding:,.2f}")
    print(f"Collection  : {collection_rate:.2f}%")
    print(f"Promises    : ₦{promised_amount:,.2f}")
    print("----------------------------------------")
    print(
        "READ-ONLY: Credit/payment records "
        "were NOT modified."
    )
    print("========================================")

    conn.close()

    input("\nPress Enter to continue...")


if __name__ == "__main__":
    customer_collection_workspace()
