import sqlite3

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def receivables_dashboard():
    conn = get_connection()
    cur = conn.cursor()

    print("\n========================================")
    print("       POS LEDGER NG V8")
    print("        RECEIVABLES DASHBOARD")
    print("========================================")

    # ------------------------------------
    # TOTAL CREDIT SALES
    # ------------------------------------
    cur.execute("""
        SELECT
            COALESCE(SUM(total_amount), 0) AS total_credit,
            COALESCE(SUM(amount_paid), 0) AS total_paid,
            COALESCE(SUM(balance), 0) AS outstanding,
            COUNT(*) AS credit_accounts
        FROM customer_credit
    """)

    totals = cur.fetchone()

    total_credit = float(totals["total_credit"] or 0)
    total_paid = float(totals["total_paid"] or 0)
    outstanding = float(totals["outstanding"] or 0)
    credit_accounts = int(totals["credit_accounts"] or 0)

    # ------------------------------------
    # CUSTOMERS OWING
    # ------------------------------------
    cur.execute("""
        SELECT COUNT(DISTINCT customer_id)
        FROM customer_credit
        WHERE balance > 0
    """)

    customers_owing = int(cur.fetchone()[0] or 0)

    # ------------------------------------
    # CLEARED CUSTOMERS
    # ------------------------------------
    cur.execute("""
        SELECT COUNT(DISTINCT customer_id)
        FROM customer_credit
        GROUP BY customer_id
        HAVING SUM(balance) <= 0
    """)

    cleared_customers = len(cur.fetchall())

    # ------------------------------------
    # COLLECTION RATE
    # ------------------------------------
    if total_credit > 0:
        collection_rate = (total_paid / total_credit) * 100
    else:
        collection_rate = 0

    # ------------------------------------
    # CREDIT EXPOSURE
    # ------------------------------------
    if total_credit > 0:
        exposure_rate = (outstanding / total_credit) * 100
    else:
        exposure_rate = 0

    # ------------------------------------
    # DASHBOARD
    # ------------------------------------
    print("\n----------------------------------------")
    print("             OVERALL POSITION")
    print("----------------------------------------")

    print(
        f"Total Credit Sales      : "
        f"₦{total_credit:,.2f}"
    )

    print(
        f"Total Collected         : "
        f"₦{total_paid:,.2f}"
    )

    print(
        f"Outstanding Receivables : "
        f"₦{outstanding:,.2f}"
    )

    print(
        f"Credit Accounts         : "
        f"{credit_accounts}"
    )

    print(
        f"Customers Owing         : "
        f"{customers_owing}"
    )

    print(
        f"Cleared Customers       : "
        f"{cleared_customers}"
    )

    print(
        f"Collection Rate         : "
        f"{collection_rate:.2f}%"
    )

    print(
        f"Outstanding Exposure    : "
        f"{exposure_rate:.2f}%"
    )

    print("----------------------------------------")

    # ------------------------------------
    # TOP DEBTORS
    # ------------------------------------
    print("\n========================================")
    print("             TOP DEBTORS")
    print("========================================")

    cur.execute("""
        SELECT
            c.id,
            c.fullname,
            c.phone,
            COALESCE(SUM(cc.balance), 0) AS outstanding,
            COALESCE(c.credit_limit, 0) AS credit_limit
        FROM customers c
        JOIN customer_credit cc
            ON cc.customer_id = c.id
        GROUP BY
            c.id,
            c.fullname,
            c.phone,
            c.credit_limit
        HAVING outstanding > 0
        ORDER BY outstanding DESC
    """)

    debtors = cur.fetchall()

    if not debtors:
        print("No outstanding customers.")
    else:
        rank = 1

        for debtor in debtors:

            debt = float(
                debtor["outstanding"] or 0
            )

            limit = float(
                debtor["credit_limit"] or 0
            )

            if limit > 0:
                utilization = (
                    debt / limit
                ) * 100
            else:
                utilization = 0

            print("----------------------------------------")
            print(f"#{rank} Customer : {debtor['fullname']}")
            print(
                f"   Customer ID : "
                f"{debtor['id']}"
            )
            print(
                f"   Phone       : "
                f"{debtor['phone'] or 'N/A'}"
            )
            print(
                f"   Outstanding : "
                f"₦{debt:,.2f}"
            )
            print(
                f"   Credit Limit: "
                f"₦{limit:,.2f}"
            )
            print(
                f"   Utilization : "
                f"{utilization:.2f}%"
            )

            rank += 1

    print("----------------------------------------")

    # ------------------------------------
    # ACCOUNT HEALTH
    # ------------------------------------
    print("\n========================================")
    print("             ACCOUNT HEALTH")
    print("========================================")

    if outstanding <= 0:
        print("STATUS : ✅ NO OUTSTANDING RECEIVABLES")

    elif exposure_rate < 25:
        print("STATUS : 🟢 LOW CREDIT EXPOSURE")

    elif exposure_rate < 50:
        print("STATUS : 🟡 MODERATE CREDIT EXPOSURE")

    elif exposure_rate < 75:
        print("STATUS : 🟠 HIGH CREDIT EXPOSURE")

    else:
        print("STATUS : 🔴 VERY HIGH CREDIT EXPOSURE")

    print("========================================")

    conn.close()

    input("\nPress Enter to continue...")


if __name__ == "__main__":
    receivables_dashboard()
