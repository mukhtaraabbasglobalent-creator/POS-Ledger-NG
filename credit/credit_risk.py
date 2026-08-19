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
    """
    Read-only customer credit-risk scoring.

    Score:
        0-24   LOW
        25-49  MODERATE
        50-74  HIGH
        75-100 CRITICAL

    Higher score = higher credit risk.
    """

    score = 0

    # -------------------------------------------------
    # 1. Credit utilization
    # -------------------------------------------------
    utilization = (
        outstanding / credit_limit * 100
        if credit_limit > 0
        else 0
    )

    if utilization >= 80:
        score += 30
    elif utilization >= 60:
        score += 20
    elif utilization >= 40:
        score += 10
    elif utilization >= 20:
        score += 5

    # -------------------------------------------------
    # 2. Collection performance
    # -------------------------------------------------
    if collection_rate < 25:
        score += 25
    elif collection_rate < 50:
        score += 15
    elif collection_rate < 75:
        score += 5

    # -------------------------------------------------
    # 3. Promise outcomes
    # -------------------------------------------------
    if total_outcomes > 0:

        missed_rate = (
            missed / total_outcomes * 100
        )

        partial_rate = (
            partial / total_outcomes * 100
        )

        fulfillment_rate = (
            fulfilled / total_outcomes * 100
        )

        if missed_rate >= 50:
            score += 30
        elif missed_rate > 0:
            score += 20

        if partial_rate >= 50:
            score += 15
        elif partial_rate > 0:
            score += 5

        if fulfillment_rate >= 80:
            score -= 15

    else:
        # No outcome history.
        # Do not penalize customer for lack of data.
        score += 0

    score = max(0, min(100, score))

    if score >= 75:
        risk = "🔴 CRITICAL"
        action = "SUSPEND NEW CREDIT REVIEW"

    elif score >= 50:
        risk = "🟠 HIGH"
        action = "REVIEW BEFORE ADDITIONAL CREDIT"

    elif score >= 25:
        risk = "🟡 MODERATE"
        action = "MONITOR REPAYMENT"

    else:
        risk = "🟢 LOW"
        action = "NORMAL CREDIT MONITORING"

    return score, utilization, risk, action


def credit_risk(customer_id=None):
    conn = get_connection()
    cur = conn.cursor()

    if customer_id is None:
        customers = cur.execute("""
            SELECT
                id,
                fullname,
                phone,
                credit_limit
            FROM customers
            ORDER BY id
        """).fetchall()
    else:
        customers = cur.execute("""
            SELECT
                id,
                fullname,
                phone,
                credit_limit
            FROM customers
            WHERE id = ?
        """, (customer_id,)).fetchall()

    print("\n========================================")
    print("       POS LEDGER NG V20")
    print("     CUSTOMER CREDIT RISK")
    print("========================================")

    if not customers:
        print("\nNo customer found.")
        conn.close()
        input("\nPress Enter to continue...")
        return

    for customer in customers:

        cid = customer["id"]

        credit = cur.execute("""
            SELECT
                COALESCE(SUM(total_amount), 0)
                    AS total_credit,

                COALESCE(SUM(amount_paid), 0)
                    AS total_paid,

                COALESCE(SUM(balance), 0)
                    AS outstanding,

                COUNT(*) AS credit_accounts

            FROM customer_credit
            WHERE customer_id = ?
        """, (cid,)).fetchone()

        outcomes = cur.execute("""
            SELECT

                COUNT(*) AS total_outcomes,

                COALESCE(
                    SUM(
                        CASE
                            WHEN outcome = 'FULFILLED'
                            THEN 1
                            ELSE 0
                        END
                    ),
                    0
                ) AS fulfilled,

                COALESCE(
                    SUM(
                        CASE
                            WHEN outcome =
                                'PARTIALLY FULFILLED'
                            THEN 1
                            ELSE 0
                        END
                    ),
                    0
                ) AS partial,

                COALESCE(
                    SUM(
                        CASE
                            WHEN outcome = 'MISSED'
                            THEN 1
                            ELSE 0
                        END
                    ),
                    0
                ) AS missed

            FROM collection_outcomes
            WHERE customer_id = ?
        """, (cid,)).fetchone()

        total_credit = float(
            credit["total_credit"] or 0
        )

        total_paid = float(
            credit["total_paid"] or 0
        )

        outstanding = float(
            credit["outstanding"] or 0
        )

        credit_accounts = int(
            credit["credit_accounts"] or 0
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

        collection_rate = (
            total_paid /
            total_credit *
            100
            if total_credit > 0
            else 0
        )

        credit_limit = float(
            customer["credit_limit"] or 0
        )

        score, utilization, risk, action = calculate_risk(
            outstanding,
            credit_limit,
            collection_rate,
            total_outcomes,
            fulfilled,
            partial,
            missed,
        )

        print("\n========================================")
        print("       CUSTOMER INFORMATION")
        print("========================================")

        print(
            f"Customer ID   : {cid}"
        )

        print(
            f"Customer Name : {customer['fullname']}"
        )

        print(
            f"Phone         : {customer['phone']}"
        )

        print(
            f"Credit Limit  : "
            f"₦{credit_limit:,.2f}"
        )

        print("\n========================================")
        print("        CREDIT POSITION")
        print("========================================")

        print(
            f"Total Credit  : "
            f"₦{total_credit:,.2f}"
        )

        print(
            f"Total Paid    : "
            f"₦{total_paid:,.2f}"
        )

        print(
            f"Outstanding   : "
            f"₦{outstanding:,.2f}"
        )

        print(
            f"Credit Used   : "
            f"{utilization:.2f}%"
        )

        print(
            f"Collection    : "
            f"{collection_rate:.2f}%"
        )

        print(
            f"Credit Accounts: "
            f"{credit_accounts}"
        )

        print("\n========================================")
        print("       REPAYMENT EVIDENCE")
        print("========================================")

        print(
            f"Outcome Records : "
            f"{total_outcomes}"
        )

        print(
            f"Fulfilled       : "
            f"{fulfilled}"
        )

        print(
            f"Partially Filled: "
            f"{partial}"
        )

        print(
            f"Missed          : "
            f"{missed}"
        )

        print("\n========================================")
        print("        RISK ASSESSMENT")
        print("========================================")

        print(
            f"Risk Score     : "
            f"{score}/100"
        )

        print(
            f"Risk Status    : "
            f"{risk}"
        )

        print(
            f"Recommended Action : "
            f"{action}"
        )

        print("\n========================================")
        print("       MANAGEMENT SUMMARY")
        print("========================================")

        if total_outcomes == 0:
            print(
                "• No repayment outcome history "
                "is available yet."
            )

        print(
            f"• ₦{outstanding:,.2f} remains "
            "outstanding."
        )

        print(
            f"• Credit utilization is "
            f"{utilization:.2f}%."
        )

        print(
            f"• Collection rate is "
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
    credit_risk()
