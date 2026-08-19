import sqlite3
from datetime import datetime

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def money(value):
    return f"₦{float(value or 0):,.2f}"


def days_old(date_string):
    try:
        created = datetime.strptime(
            date_string,
            "%Y-%m-%d %H:%M:%S"
        )

        return max(
            (datetime.now() - created).days,
            0
        )

    except Exception:
        return 0


def aging_bucket(days):
    if days <= 7:
        return "0–7 DAYS"
    elif days <= 30:
        return "8–30 DAYS"
    elif days <= 60:
        return "31–60 DAYS"
    elif days <= 90:
        return "61–90 DAYS"
    else:
        return "90+ DAYS"


def risk_level(balance, credit_limit, age):
    balance = float(balance or 0)
    credit_limit = float(credit_limit or 0)

    if balance <= 0:
        return "🟢 CLEARED"

    utilization = (
        (balance / credit_limit) * 100
        if credit_limit > 0
        else 100
    )

    if age > 90 or utilization >= 90:
        return "🔴 CRITICAL"

    if age > 60 or utilization >= 75:
        return "🟠 HIGH"

    if age > 30 or utilization >= 50:
        return "🟡 MEDIUM"

    return "🟢 LOW"


def receivables_intelligence():
    conn = get_connection()
    cur = conn.cursor()

    print("\n========================================")
    print("       POS LEDGER NG V9")
    print("    RECEIVABLES INTELLIGENCE")
    print("========================================")

    cur.execute("""
        SELECT
            cc.id,
            cc.customer_id,
            cc.total_amount,
            cc.amount_paid,
            cc.balance,
            cc.status,
            cc.created_date,
            c.fullname,
            c.phone,
            c.credit_limit
        FROM customer_credit cc
        JOIN customers c
            ON c.id = cc.customer_id
        WHERE cc.balance > 0
        ORDER BY cc.balance DESC
    """)

    credits = cur.fetchall()

    # ------------------------------------
    # OVERALL TOTALS
    # ------------------------------------

    total_credit = sum(
        float(row["total_amount"] or 0)
        for row in credits
    )

    total_paid = sum(
        float(row["amount_paid"] or 0)
        for row in credits
    )

    outstanding = sum(
        float(row["balance"] or 0)
        for row in credits
    )

    print("\n----------------------------------------")
    print("          RECEIVABLE POSITION")
    print("----------------------------------------")

    print(
        f"Outstanding Receivables : "
        f"{money(outstanding)}"
    )

    print(
        f"Open Credit Accounts    : "
        f"{len(credits)}"
    )

    if total_credit > 0:
        collection_rate = (
            total_paid / total_credit
        ) * 100
    else:
        collection_rate = 0

    print(
        f"Collection Rate         : "
        f"{collection_rate:.2f}%"
    )

    # ------------------------------------
    # AGING ANALYSIS
    # ------------------------------------

    buckets = {
        "0–7 DAYS": 0,
        "8–30 DAYS": 0,
        "31–60 DAYS": 0,
        "61–90 DAYS": 0,
        "90+ DAYS": 0
    }

    for row in credits:
        age = days_old(row["created_date"])
        bucket = aging_bucket(age)

        buckets[bucket] += float(
            row["balance"] or 0
        )

    print("\n========================================")
    print("          RECEIVABLE AGING")
    print("========================================")

    for bucket, amount in buckets.items():
        print(
            f"{bucket:<12} : "
            f"{money(amount)}"
        )

    # ------------------------------------
    # CUSTOMER RISK
    # ------------------------------------

    print("\n========================================")
    print("         CUSTOMER RISK ANALYSIS")
    print("========================================")

    if not credits:
        print("No outstanding customer accounts.")

    else:

        for index, row in enumerate(
            credits,
            start=1
        ):

            age = days_old(
                row["created_date"]
            )

            risk = risk_level(
                row["balance"],
                row["credit_limit"],
                age
            )

            credit_limit = float(
                row["credit_limit"] or 0
            )

            balance = float(
                row["balance"] or 0
            )

            utilization = (
                (balance / credit_limit) * 100
                if credit_limit > 0
                else 0
            )

            print("----------------------------------------")

            print(
                f"#{index} "
                f"{row['fullname']}"
            )

            print(
                f"Customer ID : "
                f"{row['customer_id']}"
            )

            print(
                f"Phone       : "
                f"{row['phone'] or 'N/A'}"
            )

            print(
                f"Outstanding : "
                f"{money(balance)}"
            )

            print(
                f"Age         : "
                f"{age} day(s)"
            )

            print(
                f"Credit Used : "
                f"{utilization:.2f}%"
            )

            print(
                f"Risk        : "
                f"{risk}"
            )

    # ------------------------------------
    # COLLECTION PRIORITY
    # ------------------------------------

    print("\n========================================")
    print("        COLLECTION PRIORITY")
    print("========================================")

    priority_rows = []

    for row in credits:

        age = days_old(
            row["created_date"]
        )

        balance = float(
            row["balance"] or 0
        )

        # Higher score = more urgent
        score = (
            balance / 100
            + age * 10
        )

        priority_rows.append(
            (score, row, age)
        )

    priority_rows.sort(
        key=lambda x: x[0],
        reverse=True
    )

    if not priority_rows:
        print("No collection actions required.")

    else:

        for index, (
            score,
            row,
            age
        ) in enumerate(
            priority_rows,
            start=1
        ):

            print("----------------------------------------")

            print(
                f"Priority #{index}"
            )

            print(
                f"Customer    : "
                f"{row['fullname']}"
            )

            print(
                f"Outstanding : "
                f"{money(row['balance'])}"
            )

            print(
                f"Age         : "
                f"{age} day(s)"
            )

            if age > 60:
                action = (
                    "URGENT COLLECTION"
                )
            elif age > 30:
                action = (
                    "FOLLOW UP CUSTOMER"
                )
            else:
                action = (
                    "NORMAL COLLECTION"
                )

            print(
                f"Action      : "
                f"{action}"
            )

    # ------------------------------------
    # MANAGEMENT WARNINGS
    # ------------------------------------

    print("\n========================================")
    print("        MANAGEMENT WARNINGS")
    print("========================================")

    warnings = []

    for row in credits:

        age = days_old(
            row["created_date"]
        )

        balance = float(
            row["balance"] or 0
        )

        credit_limit = float(
            row["credit_limit"] or 0
        )

        if age > 90:
            warnings.append(
                f"{row['fullname']} "
                f"has debt older than 90 days."
            )

        if (
            credit_limit > 0
            and balance >= credit_limit * 0.9
        ):
            warnings.append(
                f"{row['fullname']} "
                f"is approaching the credit limit."
            )

    if not warnings:
        print("✅ No critical receivables warnings.")

    else:

        for warning in warnings:
            print(f"⚠️ {warning}")

    print("\n========================================")
    print("       END V9 ANALYSIS")
    print("========================================")

    conn.close()

    input("\nPress Enter to continue...")


if __name__ == "__main__":
    receivables_intelligence()
