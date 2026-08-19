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
    print("       POS LEDGER NG V10")
    print("     COLLECTION MANAGEMENT")
    print("========================================")

    # ------------------------------------
    # OPEN RECEIVABLES
    # ------------------------------------

    cur.execute("""
        SELECT
            cc.id AS credit_id,
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
    # OVERALL COLLECTION POSITION
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

    collection_rate = (
        (total_paid / total_credit) * 100
        if total_credit > 0
        else 0
    )

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
        f"{len(credits)}"
    )

    # ------------------------------------
    # COLLECTION ACTION LIST
    # ------------------------------------

    print("\n========================================")
    print("        COLLECTION ACTION LIST")
    print("========================================")

    if not credits:
        print("✅ No outstanding accounts.")

    else:

        for number, row in enumerate(
            credits,
            start=1
        ):

            balance = float(
                row["balance"] or 0
            )

            age = calculate_age(
                row["created_date"]
            )

            priority = collection_priority(
                balance,
                age
            )

            action = collection_action(age)

            print("----------------------------------------")

            print(
                f"#{number} "
                f"{row['fullname']}"
            )

            print(
                f"Credit ID   : "
                f"{row['credit_id']}"
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
                f"Debt Age    : "
                f"{age} day(s)"
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

    cur.execute("""
        SELECT
            c.id,
            c.fullname,
            c.phone,
            COALESCE(SUM(cc.total_amount), 0)
                AS total_credit,
            COALESCE(SUM(cc.amount_paid), 0)
                AS total_paid,
            COALESCE(SUM(cc.balance), 0)
                AS outstanding
        FROM customers c
        JOIN customer_credit cc
            ON cc.customer_id = c.id
        GROUP BY
            c.id,
            c.fullname,
            c.phone
        HAVING outstanding > 0
        ORDER BY outstanding DESC
    """)

    customers = cur.fetchall()

    if not customers:
        print("No customers require collection.")

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
    # COLLECTION RECOMMENDATIONS
    # ------------------------------------

    print("\n========================================")
    print("       COLLECTION RECOMMENDATIONS")
    print("========================================")

    if not credits:

        print(
            "✅ No collection actions required."
        )

    else:

        recommendations = []

        for row in credits:

            balance = float(
                row["balance"] or 0
            )

            age = calculate_age(
                row["created_date"]
            )

            if age > 60:
                recommendations.append(
                    f"URGENT: Contact "
                    f"{row['fullname']} "
                    f"about {money(balance)}."
                )

            elif age > 30:
                recommendations.append(
                    f"FOLLOW-UP: Contact "
                    f"{row['fullname']} "
                    f"about {money(balance)}."
                )

            else:
                recommendations.append(
                    f"NORMAL: Monitor "
                    f"{row['fullname']} "
                    f"({money(balance)})."
                )

        for item in recommendations:
            print(f"• {item}")

    # ------------------------------------
    # MANAGEMENT SUMMARY
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
