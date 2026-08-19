import sqlite3

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def explain_risk(
    outstanding,
    credit_limit,
    collection_rate,
    total_outcomes,
    fulfilled,
    partial,
    missed,
):
    score = 0
    factors = []

    # ----------------------------------------
    # CREDIT UTILIZATION
    # ----------------------------------------
    utilization = (
        outstanding / credit_limit * 100
        if credit_limit > 0
        else 0
    )

    utilization_points = 0

    if utilization >= 80:
        utilization_points = 30
        factors.append(
            f"High credit utilization "
            f"({utilization:.2f}%)"
        )
    elif utilization >= 60:
        utilization_points = 20
        factors.append(
            f"Elevated credit utilization "
            f"({utilization:.2f}%)"
        )
    elif utilization >= 40:
        utilization_points = 10
        factors.append(
            f"Moderate credit utilization "
            f"({utilization:.2f}%)"
        )
    elif utilization >= 20:
        utilization_points = 5
        factors.append(
            f"Credit utilization is "
            f"{utilization:.2f}%"
        )
    else:
        factors.append(
            f"Low credit utilization "
            f"({utilization:.2f}%)"
        )

    score += utilization_points

    # ----------------------------------------
    # COLLECTION PERFORMANCE
    # ----------------------------------------
    collection_points = 0

    if collection_rate < 25:
        collection_points = 25
        factors.append(
            f"Low collection rate "
            f"({collection_rate:.2f}%)"
        )
    elif collection_rate < 50:
        collection_points = 15
        factors.append(
            f"Collection rate needs attention "
            f"({collection_rate:.2f}%)"
        )
    elif collection_rate < 75:
        collection_points = 5
        factors.append(
            f"Moderate collection performance "
            f"({collection_rate:.2f}%)"
        )
    else:
        factors.append(
            f"Strong collection performance "
            f"({collection_rate:.2f}%)"
        )

    score += collection_points

    # ----------------------------------------
    # REPAYMENT OUTCOMES
    # ----------------------------------------
    outcome_points = 0

    if total_outcomes == 0:
        factors.append(
            "No repayment outcome history "
            "available"
        )

    else:
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
            outcome_points += 30
            factors.append(
                f"High missed-promise rate "
                f"({missed_rate:.2f}%)"
            )
        elif missed_rate > 0:
            outcome_points += 20
            factors.append(
                f"Missed promises recorded "
                f"({missed_rate:.2f}%)"
            )

        if partial_rate >= 50:
            outcome_points += 15
            factors.append(
                f"High partial-fulfillment rate "
                f"({partial_rate:.2f}%)"
            )
        elif partial_rate > 0:
            outcome_points += 5
            factors.append(
                f"Partial repayments recorded "
                f"({partial_rate:.2f}%)"
            )

        if fulfillment_rate >= 80:
            outcome_points -= 15
            factors.append(
                f"Strong promise fulfillment "
                f"({fulfillment_rate:.2f}%)"
            )

    score += outcome_points

    score = max(0, min(100, score))

    # ----------------------------------------
    # RISK CLASSIFICATION
    # ----------------------------------------
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

    # ----------------------------------------
    # DATA CONFIDENCE
    # ----------------------------------------
    if total_outcomes == 0:
        confidence = "🟡 LIMITED"
        confidence_reason = (
            "No repayment outcome records "
            "are available yet."
        )
    elif total_outcomes < 3:
        confidence = "🟡 MODERATE"
        confidence_reason = (
            "Limited repayment outcome history."
        )
    else:
        confidence = "🟢 STRONG"
        confidence_reason = (
            "Sufficient repayment outcome "
            "history is available."
        )

    return {
        "score": score,
        "utilization": utilization,
        "utilization_points": utilization_points,
        "collection_points": collection_points,
        "outcome_points": outcome_points,
        "risk": risk,
        "action": action,
        "confidence": confidence,
        "confidence_reason": confidence_reason,
        "factors": factors,
    }


def explainable_risk(customer_id):
    conn = get_connection()
    cur = conn.cursor()

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
        print("Customer not found.")
        conn.close()
        input("\nPress Enter to continue...")
        return

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
    """, (customer_id,)).fetchone()

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
                ), 0
            ) AS fulfilled,

            COALESCE(
                SUM(
                    CASE
                        WHEN outcome =
                            'PARTIALLY FULFILLED'
                        THEN 1
                        ELSE 0
                    END
                ), 0
            ) AS partial,

            COALESCE(
                SUM(
                    CASE
                        WHEN outcome = 'MISSED'
                        THEN 1
                        ELSE 0
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
        total_paid / total_credit * 100
        if total_credit > 0
        else 0
    )

    credit_limit = float(
        customer["credit_limit"] or 0
    )

    result = explain_risk(
        outstanding,
        credit_limit,
        collection_rate,
        total_outcomes,
        fulfilled,
        partial,
        missed,
    )

    print("\n========================================")
    print("       POS LEDGER NG V21")
    print("   EXPLAINABLE CREDIT RISK")
    print("========================================")

    print("\n========================================")
    print("       CUSTOMER INFORMATION")
    print("========================================")

    print(
        f"Customer ID   : {customer['id']}"
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
        f"{result['utilization']:.2f}%"
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
    print("        RISK SCORE BREAKDOWN")
    print("========================================")

    print(
        f"Utilization Points : "
        f"+{result['utilization_points']}"
    )

    print(
        f"Collection Points  : "
        f"+{result['collection_points']}"
    )

    print(
        f"Outcome Points     : "
        f"{result['outcome_points']:+d}"
    )

    print("----------------------------------------")

    print(
        f"TOTAL RISK SCORE   : "
        f"{result['score']}/100"
    )

    print(
        f"RISK STATUS        : "
        f"{result['risk']}"
    )

    print("\n========================================")
    print("        WHY THIS SCORE?")
    print("========================================")

    for number, factor in enumerate(
        result["factors"],
        start=1
    ):
        print(
            f"{number}. {factor}"
        )

    print("\n========================================")
    print("        DATA CONFIDENCE")
    print("========================================")

    print(
        f"Confidence : "
        f"{result['confidence']}"
    )

    print(
        f"Reason     : "
        f"{result['confidence_reason']}"
    )

    print("\n========================================")
    print("       CREDIT DECISION SUPPORT")
    print("========================================")

    print(
        f"Recommendation : "
        f"{result['action']}"
    )

    print("\n========================================")
    print("       MANAGEMENT SUMMARY")
    print("========================================")

    print(
        f"• ₦{outstanding:,.2f} remains "
        "outstanding."
    )

    print(
        f"• Risk score is "
        f"{result['score']}/100."
    )

    print(
        f"• Risk status is "
        f"{result['risk']}."
    )

    print(
        f"• Data confidence is "
        f"{result['confidence']}."
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
    explainable_risk(1)
