import sqlite3

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def calculate_risk(
    outstanding,
    credit_limit,
    collection_rate,
    total_outcomes,
    fulfilled,
    partial,
    missed,
):
    score = 0

    utilization = (
        outstanding / credit_limit * 100
        if credit_limit > 0
        else 0
    )

    # Credit utilization
    if utilization >= 80:
        score += 30
    elif utilization >= 60:
        score += 20
    elif utilization >= 40:
        score += 10
    elif utilization >= 20:
        score += 5

    # Collection performance
    if collection_rate < 25:
        score += 25
    elif collection_rate < 50:
        score += 15
    elif collection_rate < 75:
        score += 5

    # Repayment outcomes
    if total_outcomes > 0:
        missed_rate = missed / total_outcomes * 100
        partial_rate = partial / total_outcomes * 100
        fulfilled_rate = fulfilled / total_outcomes * 100

        if missed_rate >= 50:
            score += 30
        elif missed_rate > 0:
            score += 20

        if partial_rate >= 50:
            score += 15
        elif partial_rate > 0:
            score += 5

        if fulfilled_rate >= 80:
            score -= 15

    score = max(0, min(100, score))

    if score >= 75:
        status = "CRITICAL"
        action = "SUSPEND NEW CREDIT REVIEW"
    elif score >= 50:
        status = "HIGH"
        action = "REVIEW BEFORE ADDITIONAL CREDIT"
    elif score >= 25:
        status = "MODERATE"
        action = "MONITOR REPAYMENT"
    else:
        status = "LOW"
        action = "NORMAL CREDIT MONITORING"

    return score, status, action, utilization


def get_customer_risk(cur, customer_id):
    customer = cur.execute("""
        SELECT
            id,
            fullname,
            phone,
            credit_limit
        FROM customers
        WHERE id = ?
    """, (customer_id,)).fetchone()

    if not customer:
        return None

    credit = cur.execute("""
        SELECT
            COALESCE(SUM(total_amount), 0) AS total_credit,
            COALESCE(SUM(amount_paid), 0) AS total_paid,
            COALESCE(SUM(balance), 0) AS outstanding
        FROM customer_credit
        WHERE customer_id = ?
    """, (customer_id,)).fetchone()

    outcomes = cur.execute("""
        SELECT
            COUNT(*) AS total_outcomes,

            COALESCE(
                SUM(
                    CASE
                        WHEN outcome = 'FULFILLED'
                        THEN 1 ELSE 0
                    END
                ), 0
            ) AS fulfilled,

            COALESCE(
                SUM(
                    CASE
                        WHEN outcome = 'PARTIALLY FULFILLED'
                        THEN 1 ELSE 0
                    END
                ), 0
            ) AS partial,

            COALESCE(
                SUM(
                    CASE
                        WHEN outcome = 'MISSED'
                        THEN 1 ELSE 0
                    END
                ), 0
            ) AS missed

        FROM collection_outcomes
        WHERE customer_id = ?
    """, (customer_id,)).fetchone()

    total_credit = float(
        credit["total_credit"] or 0
    )

    total_paid = float(
        credit["total_paid"] or 0
    )

    outstanding = float(
        credit["outstanding"] or 0
    )

    credit_limit = float(
        customer["credit_limit"] or 0
    )

    collection_rate = (
        total_paid / total_credit * 100
        if total_credit > 0
        else 0
    )

    total_outcomes = int(
        outcomes["total_outcomes"] or 0
    )

    fulfilled = int(
        outcomes["fulfilled"] or 0
    )

    partial = int(
        outcomes["partial"] or 0
    )

    missed = int(
        outcomes["missed"] or 0
    )

    score, status, action, utilization = calculate_risk(
        outstanding,
        credit_limit,
        collection_rate,
        total_outcomes,
        fulfilled,
        partial,
        missed,
    )

    return {
        "id": customer["id"],
        "fullname": customer["fullname"],
        "phone": customer["phone"],
        "credit_limit": credit_limit,
        "total_credit": total_credit,
        "total_paid": total_paid,
        "outstanding": outstanding,
        "collection_rate": collection_rate,
        "utilization": utilization,
        "outcomes": total_outcomes,
        "fulfilled": fulfilled,
        "partial": partial,
        "missed": missed,
        "score": score,
        "status": status,
        "action": action,
    }


def portfolio_risk():
    conn = get_connection()
    cur = conn.cursor()

    customers = cur.execute("""
        SELECT id
        FROM customers
        ORDER BY id
    """).fetchall()

    records = []

    for row in customers:
        result = get_customer_risk(
            cur,
            row["id"]
        )

        if result is None:
            continue

        # Only include customers with credit activity.
        if (
            result["total_credit"] > 0
            or result["outstanding"] > 0
        ):
            records.append(result)

    total_credit = sum(
        r["total_credit"]
        for r in records
    )

    total_paid = sum(
        r["total_paid"]
        for r in records
    )

    total_outstanding = sum(
        r["outstanding"]
        for r in records
    )

    collection_rate = (
        total_paid / total_credit * 100
        if total_credit > 0
        else 0
    )

    low = [
        r for r in records
        if r["status"] == "LOW"
    ]

    moderate = [
        r for r in records
        if r["status"] == "MODERATE"
    ]

    high = [
        r for r in records
        if r["status"] == "HIGH"
    ]

    critical = [
        r for r in records
        if r["status"] == "CRITICAL"
    ]

    attention = [
        r for r in records
        if r["status"] in (
            "HIGH",
            "CRITICAL"
        )
    ]

    print("\n========================================")
    print("       POS LEDGER NG V22")
    print("       PORTFOLIO RISK DASHBOARD")
    print("========================================")

    print("\n========================================")
    print("       PORTFOLIO POSITION")
    print("========================================")

    print(
        f"Credit Customers : {len(records)}"
    )

    print(
        f"Credit Issued    : "
        f"₦{total_credit:,.2f}"
    )

    print(
        f"Total Collected  : "
        f"₦{total_paid:,.2f}"
    )

    print(
        f"Outstanding      : "
        f"₦{total_outstanding:,.2f}"
    )

    print(
        f"Collection Rate  : "
        f"{collection_rate:.2f}%"
    )

    print("\n========================================")
    print("        RISK DISTRIBUTION")
    print("========================================")

    print(
        f"🟢 LOW       : {len(low)}"
    )

    print(
        f"🟡 MODERATE  : {len(moderate)}"
    )

    print(
        f"🟠 HIGH      : {len(high)}"
    )

    print(
        f"🔴 CRITICAL  : {len(critical)}"
    )

    print("\n========================================")
    print("     CUSTOMERS NEEDING ATTENTION")
    print("========================================")

    if not attention:
        print(
            "No high or critical-risk "
            "customers detected."
        )
    else:
        attention.sort(
            key=lambda r: (
                -r["score"],
                -r["outstanding"]
            )
        )

        for index, customer in enumerate(
            attention,
            start=1
        ):
            print("----------------------------------------")
            print(
                f"#{index} "
                f"{customer['fullname']}"
            )

            print(
                f"Customer ID : "
                f"{customer['id']}"
            )

            print(
                f"Outstanding : "
                f"₦{customer['outstanding']:,.2f}"
            )

            print(
                f"Risk Score  : "
                f"{customer['score']}/100"
            )

            print(
                f"Risk Status : "
                f"{customer['status']}"
            )

            print(
                f"Action      : "
                f"{customer['action']}"
            )

    print("\n========================================")
    print("        PORTFOLIO CUSTOMER RISK")
    print("========================================")

    if not records:
        print(
            "No credit customers found."
        )
    else:
        records.sort(
            key=lambda r: (
                -r["score"],
                -r["outstanding"]
            )
        )

        for index, customer in enumerate(
            records,
            start=1
        ):
            print("----------------------------------------")
            print(
                f"#{index} "
                f"{customer['fullname']}"
            )

            print(
                f"Customer ID : "
                f"{customer['id']}"
            )

            print(
                f"Outstanding : "
                f"₦{customer['outstanding']:,.2f}"
            )

            print(
                f"Collection  : "
                f"{customer['collection_rate']:.2f}%"
            )

            print(
                f"Credit Used : "
                f"{customer['utilization']:.2f}%"
            )

            print(
                f"Risk Score  : "
                f"{customer['score']}/100"
            )

            print(
                f"Risk Status : "
                f"{customer['status']}"
            )

    print("\n========================================")
    print("      MANAGEMENT RECOMMENDATION")
    print("========================================")

    if critical:
        print(
            "STATUS : 🔴 CRITICAL PORTFOLIO RISK"
        )
        print(
            f"• {len(critical)} customer(s) "
            "require immediate review."
        )

    elif high:
        print(
            "STATUS : 🟠 HIGH PORTFOLIO RISK"
        )
        print(
            f"• {len(high)} customer(s) "
            "require management attention."
        )

    elif moderate:
        print(
            "STATUS : 🟡 MODERATE PORTFOLIO RISK"
        )
        print(
            f"• {len(moderate)} customer(s) "
            "should be monitored."
        )

    else:
        print(
            "STATUS : 🟢 LOW PORTFOLIO RISK"
        )
        print(
            "• No high or critical-risk "
            "customers detected."
        )

    if total_outstanding > 0:
        print(
            f"• ₦{total_outstanding:,.2f} "
            "remains outstanding."
        )

    print(
        f"• Portfolio collection rate is "
        f"{collection_rate:.2f}%."
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
    portfolio_risk()
