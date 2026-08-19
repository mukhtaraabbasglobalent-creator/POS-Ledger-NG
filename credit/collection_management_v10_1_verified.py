import sqlite3
from datetime import datetime

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def money(value):
    return f"₦{float(value or 0):,.2f}"


def calculate_age(date_string):
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


def collection_priority(balance, age):
    balance = float(balance or 0)

    if age > 90 or balance >= 100000:
        return "🔴 CRITICAL"

    if age > 60 or balance >= 50000:
        return "🟠 HIGH"

    if age > 30 or balance >= 20000:
        return "🟡 MEDIUM"

    return "🟢 NORMAL"


def collection_action(age):
    if age > 90:
        return "ESCALATE COLLECTION"

    if age > 60:
        return "URGENT FOLLOW-UP"

    if age > 30:
        return "FOLLOW-UP CUSTOMER"

    return "NORMAL COLLECTION"


def collection_management():
    conn = get_connection()
    cur = conn.cursor()

    print("\n========================================")
    print("       POS LEDGER NG V10.1")
    print("   COLLECTION MANAGEMENT")
    print("========================================")

    # ------------------------------------
    # OVERALL POSITION
    # ------------------------------------

    cur.execute("""
        SELECT
            COALESCE(SUM(total_amount), 0)
                AS total_credit,
            COALESCE(SUM(amount_paid), 0)
                AS total_paid,
            COALESCE(SUM(balance), 0)
                AS outstanding
        FROM customer_credit
    """)

    overall = cur.fetchone()

    total_credit = float(
        overall["total_credit"] or 0
    )

    total_paid = float(
        overall["total_paid"] or 0
    )

    outstanding = float(
        overall["outstanding"] or 0
    )

    collection_rate = (
        (total_paid / total_credit) * 100
        if total_credit > 0
        else 0
    )

    cur.execute("""
        SELECT COUNT(*)
        FROM customer_credit
        WHERE balance > 0
    """)

    open_accounts = cur.fetchone()[0]

    print("\n----------------------------------------")
    print("        COLLECTION POSITION")
    print("----------------------------------------")

    print(
        f"Credit Under Collection : "
        f"{money(total_credit)}"
    )

    print(
        f"Collected               : "
        f"{money(total_paid)}"
    )

    print(
        f"Outstanding             : "
        f"{money(outstanding)}"
    )

    print(
        f"Collection Rate         : "
        f"{collection_rate:.2f}%"
    )

    print(
        f"Open Credit Accounts    : "
        f"{open_accounts}"
    )

    # ------------------------------------
    # CUSTOMER-LEVEL COLLECTION ACTIONS
    # ------------------------------------

    cur.execute("""
        SELECT
            c.id AS customer_id,
            c.fullname,
            c.phone,
            c.credit_limit,

            COALESCE(
                SUM(cc.total_amount),
                0
            ) AS total_credit,

            COALESCE(
                SUM(cc.amount_paid),
                0
            ) AS total_paid,

            COALESCE(
                SUM(cc.balance),
                0
            ) AS outstanding,

            MIN(cc.created_date)
                AS oldest_credit

        FROM customers c

        JOIN customer_credit cc
            ON cc.customer_id = c.id

        WHERE cc.balance > 0

        GROUP BY
            c.id,
            c.fullname,
            c.phone,
            c.credit_limit

        HAVING outstanding > 0

        ORDER BY outstanding DESC
    """)

    customers = cur.fetchall()

    print("\n========================================")
    print("    CUSTOMER COLLECTION ACTIONS")
    print("========================================")

    if not customers:

        print(
            "✅ No customers require collection."
        )

    else:

        for number, row in enumerate(
            customers,
            start=1
        ):

            customer_outstanding = float(
                row["outstanding"] or 0
            )

            customer_credit = float(
                row["total_credit"] or 0
            )

            customer_paid = float(
                row["total_paid"] or 0
            )

            age = calculate_age(
                row["oldest_credit"]
            )

            priority = collection_priority(
                customer_outstanding,
                age
            )

            action = collection_action(age)

            utilization = (
                (
                    customer_outstanding
                    / float(row["credit_limit"])
                ) * 100
                if row["credit_limit"]
                else 0
            )

            print("----------------------------------------")

            print(
                f"#{number} "
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
                f"Credit      : "
                f"{money(customer_credit)}"
            )

            print(
                f"Paid        : "
                f"{money(customer_paid)}"
            )

            print(
                f"Outstanding : "
                f"{money(customer_outstanding)}"
            )

            print(
                f"Oldest Debt : "
                f"{age} day(s)"
            )

            print(
                f"Credit Used : "
                f"{utilization:.2f}%"
            )

            print(
                f"Priority    : "
                f"{priority}"
            )

            print(
                f"Recommended : "
                f"{action}"
            )

    # ------------------------------------
    # CUSTOMER COLLECTION SUMMARY
    # ------------------------------------

    print("\n========================================")
    print("       CUSTOMER COLLECTION SUMMARY")
    print("========================================")

    if not customers:

        print("No outstanding customers.")

    else:

        for row in customers:

            credit = float(
                row["total_credit"] or 0
            )

            paid = float(
                row["total_paid"] or 0
            )

            debt = float(
                row["outstanding"] or 0
            )

            rate = (
                (paid / credit) * 100
                if credit > 0
                else 0
            )

            print("----------------------------------------")

            print(
                f"Customer    : "
                f"{row['fullname']}"
            )

            print(
                f"Phone       : "
                f"{row['phone'] or 'N/A'}"
            )

            print(
                f"Credit      : "
                f"{money(credit)}"
            )

            print(
                f"Paid        : "
                f"{money(paid)}"
            )

            print(
                f"Outstanding : "
                f"{money(debt)}"
            )

            print(
                f"Collection  : "
                f"{rate:.2f}%"
            )

    # ------------------------------------
    # MANAGEMENT RECOMMENDATIONS
    # ------------------------------------

    print("\n========================================")
    print("       COLLECTION RECOMMENDATIONS")
    print("========================================")

    if not customers:

        print(
            "✅ No collection actions required."
        )

    else:

        for row in customers:

            balance = float(
                row["outstanding"] or 0
            )

            age = calculate_age(
                row["oldest_credit"]
            )

            action = collection_action(age)

            if age > 60:

                print(
                    f"🔴 URGENT: {row['fullname']} "
                    f"— {money(balance)} "
                    f"— {action}"
                )

            elif age > 30:

                print(
                    f"🟡 FOLLOW-UP: {row['fullname']} "
                    f"— {money(balance)} "
                    f"— {action}"
                )

            else:

                print(
                    f"🟢 NORMAL: {row['fullname']} "
                    f"— {money(balance)} "
                    f"— {action}"
                )

    # ------------------------------------
    # MANAGEMENT STATUS
    # ------------------------------------

    print("\n========================================")
    print("        MANAGEMENT SUMMARY")
    print("========================================")

    if outstanding <= 0:

        print(
            "STATUS : ✅ RECEIVABLES CLEARED"
        )

    elif collection_rate >= 75:

        print(
            "STATUS : 🟢 STRONG COLLECTION"
        )

    elif collection_rate >= 50:

        print(
            "STATUS : 🟡 MODERATE COLLECTION"
        )

    elif collection_rate >= 25:

        print(
            "STATUS : 🟠 COLLECTION NEEDS ATTENTION"
        )

    else:

        print(
            "STATUS : 🔴 COLLECTION PERFORMANCE LOW"
        )

    print("========================================")

    conn.close()

    input("\nPress Enter to continue...")


if __name__ == "__main__":
    collection_management()
