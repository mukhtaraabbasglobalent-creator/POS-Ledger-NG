import sqlite3


DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def repayment_behavior(customer_id):
    conn = get_connection()
    cur = conn.cursor()

    # ----------------------------------------
    # CUSTOMER
    # ----------------------------------------
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
        print(
            f"Customer ID {customer_id} was not found."
        )
        conn.close()
        return

    # ----------------------------------------
    # CREDIT POSITION
    # ----------------------------------------
    credit = cur.execute("""
        SELECT
            COALESCE(SUM(total_amount), 0) AS total_credit,
            COALESCE(SUM(amount_paid), 0) AS total_paid,
            COALESCE(SUM(balance), 0) AS outstanding,
            COUNT(*) AS credit_accounts
        FROM customer_credit
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

    if total_credit > 0:
        collection_rate = (
            total_paid / total_credit * 100
        )
    else:
        collection_rate = 0.0

    credit_limit = float(
        customer["credit_limit"] or 0
    )

    if credit_limit > 0:
        credit_used = (
            outstanding / credit_limit * 100
        )
    else:
        credit_used = 0.0

    # ----------------------------------------
    # FOLLOW-UP COUNT
    # ----------------------------------------
    followup = cur.execute("""
        SELECT
            COUNT(*) AS followups,
            COALESCE(
                SUM(promised_amount),
                0
            ) AS promised_amount
        FROM collection_followups
        WHERE customer_id = ?
    """, (customer_id,)).fetchone()

    followups = int(
        followup["followups"] or 0
    )

    promised_followups = float(
        followup["promised_amount"] or 0
    )

    # ----------------------------------------
    # OUTCOME HISTORY
    # ----------------------------------------
    outcomes = cur.execute("""
        SELECT
            id,
            followup_id,
            credit_id,
            promised_amount,
            matched_amount,
            outcome,
            outcome_date,
            staff_name,
            notes
        FROM collection_outcomes
        WHERE customer_id = ?
        ORDER BY outcome_date ASC, id ASC
    """, (customer_id,)).fetchall()

    outcome_count = len(outcomes)

    fulfilled = 0
    partial = 0
    missed = 0
    cancelled = 0

    outcome_promised = 0.0
    outcome_matched = 0.0

    for row in outcomes:

        promised = float(
            row["promised_amount"] or 0
        )

        matched = float(
            row["matched_amount"] or 0
        )

        outcome_promised += promised
        outcome_matched += matched

        status = (
            row["outcome"] or ""
        ).strip().upper()

        if status == "FULFILLED":
            fulfilled += 1

        elif status in (
            "PARTIALLY FULFILLED",
            "PARTIALLY FILLED",
            "PARTIAL",
        ):
            partial += 1

        elif status == "MISSED":
            missed += 1

        elif status == "CANCELLED":
            cancelled += 1

    if outcome_promised > 0:
        fulfillment_rate = (
            outcome_matched
            / outcome_promised
            * 100
        )
    else:
        fulfillment_rate = 0.0

    # ----------------------------------------
    # OUTCOME SUCCESS RATE
    # ----------------------------------------
    if outcome_count > 0:
        success_rate = (
            (
                fulfilled
                + partial
            )
            / outcome_count
            * 100
        )
    else:
        success_rate = 0.0

    # ----------------------------------------
    # BEHAVIOR SCORE
    # ----------------------------------------
    behavior_score = 0

    reasons = []

    # Fulfillment performance
    if outcome_count == 0:
        reasons.append(
            "No repayment outcome history available."
        )

    elif fulfillment_rate >= 90:
        behavior_score += 45

        reasons.append(
            "Very strong promise fulfillment."
        )

    elif fulfillment_rate >= 75:
        behavior_score += 35

        reasons.append(
            "Strong promise fulfillment."
        )

    elif fulfillment_rate >= 50:
        behavior_score += 25

        reasons.append(
            "Moderate promise fulfillment."
        )

    elif fulfillment_rate > 0:
        behavior_score += 10

        reasons.append(
            "Repayment is occurring but "
            "fulfillment remains limited."
        )

    else:
        reasons.append(
            "No matched repayment amount recorded."
        )

    # Fulfilled outcomes
    if fulfilled > 0:
        behavior_score += min(
            20,
            fulfilled * 10
        )

    # Partial outcomes
    if partial > 0:
        behavior_score += min(
            10,
            partial * 5
        )

        reasons.append(
            f"{partial} partially fulfilled "
            "promise(s) recorded."
        )

    # Missed outcomes
    if missed > 0:
        behavior_score -= min(
            25,
            missed * 10
        )

        reasons.append(
            f"{missed} missed promise(s) recorded."
        )

    # Cancelled outcomes
    if cancelled > 0:
        behavior_score -= min(
            10,
            cancelled * 5
        )

        reasons.append(
            f"{cancelled} cancelled outcome(s) recorded."
        )

    # Collection position
    if collection_rate >= 80:
        behavior_score += 10

        reasons.append(
            "Overall credit collection is strong."
        )

    elif collection_rate >= 50:
        behavior_score += 5

    elif collection_rate < 30:
        reasons.append(
            "Overall credit collection needs attention."
        )

    # Credit utilization
    if credit_used <= 20:
        behavior_score += 5

        reasons.append(
            "Credit utilization is relatively low."
        )

    elif credit_used >= 80:
        behavior_score -= 10

        reasons.append(
            "Credit utilization is high."
        )

    behavior_score = max(
        0,
        min(100, behavior_score)
    )

    # ----------------------------------------
    # BEHAVIOR STATUS
    # ----------------------------------------
    if outcome_count == 0:
        behavior_status = (
            "🟡 INSUFFICIENT REPAYMENT DATA"
        )

        recommendation = (
            "MONITOR — RECORD MORE REPAYMENT OUTCOMES"
        )

    elif behavior_score >= 80:
        behavior_status = (
            "🟢 STRONG REPAYMENT BEHAVIOR"
        )

        recommendation = (
            "NORMAL CREDIT MONITORING"
        )

    elif behavior_score >= 60:
        behavior_status = (
            "🟢 GOOD REPAYMENT BEHAVIOR"
        )

        recommendation = (
            "CONTINUE NORMAL MONITORING"
        )

    elif behavior_score >= 40:
        behavior_status = (
            "🟡 MODERATE REPAYMENT BEHAVIOR"
        )

        recommendation = (
            "MONITOR FUTURE PROMISES CLOSELY"
        )

    else:
        behavior_status = (
            "🟠 WEAK REPAYMENT BEHAVIOR"
        )

        recommendation = (
            "INCREASE COLLECTION MONITORING"
        )

    # ----------------------------------------
    # DATA CONFIDENCE
    # ----------------------------------------
    if outcome_count >= 5:
        confidence = "🟢 HIGH"
        confidence_reason = (
            "Multiple repayment outcomes are available."
        )

    elif outcome_count >= 2:
        confidence = "🟡 MODERATE"
        confidence_reason = (
            "Some repayment outcome history is available."
        )

    elif outcome_count == 1:
        confidence = "🟠 LIMITED"
        confidence_reason = (
            "Only one repayment outcome is available."
        )

    else:
        confidence = "🔴 VERY LIMITED"
        confidence_reason = (
            "No repayment outcome records are available."
        )

    # ----------------------------------------
    # REPORT
    # ----------------------------------------
    print("\n========================================")
    print("       POS LEDGER NG V27")
    print("    REPAYMENT BEHAVIOR INTELLIGENCE")
    print("========================================")

    print("\n========================================")
    print("       CUSTOMER INFORMATION")
    print("========================================")

    print(
        f"Customer ID   : "
        f"{customer['id']}"
    )

    print(
        f"Customer Name : "
        f"{customer['fullname']}"
    )

    print(
        f"Phone         : "
        f"{customer['phone']}"
    )

    print(
        f"Credit Limit  : "
        f"₦{credit_limit:,.2f}"
    )

    print("\n========================================")
    print("        CREDIT POSITION")
    print("========================================")

    print(
        f"Total Credit     : "
        f"₦{total_credit:,.2f}"
    )

    print(
        f"Total Paid       : "
        f"₦{total_paid:,.2f}"
    )

    print(
        f"Outstanding      : "
        f"₦{outstanding:,.2f}"
    )

    print(
        f"Credit Accounts  : "
        f"{credit_accounts}"
    )

    print(
        f"Collection Rate  : "
        f"{collection_rate:.2f}%"
    )

    print(
        f"Credit Used      : "
        f"{credit_used:.2f}%"
    )

    print("\n========================================")
    print("        REPAYMENT HISTORY")
    print("========================================")

    print(
        f"Follow-ups        : "
        f"{followups}"
    )

    print(
        f"Promises Recorded : "
        f"₦{promised_followups:,.2f}"
    )

    print(
        f"Outcome Records   : "
        f"{outcome_count}"
    )

    print(
        f"Fulfilled         : "
        f"{fulfilled}"
    )

    print(
        f"Partially Filled  : "
        f"{partial}"
    )

    print(
        f"Missed            : "
        f"{missed}"
    )

    print(
        f"Cancelled         : "
        f"{cancelled}"
    )

    print("\n========================================")
    print("       REPAYMENT PERFORMANCE")
    print("========================================")

    print(
        f"Promised Amount   : "
        f"₦{outcome_promised:,.2f}"
    )

    print(
        f"Matched Amount    : "
        f"₦{outcome_matched:,.2f}"
    )

    print(
        f"Fulfillment Rate  : "
        f"{fulfillment_rate:.2f}%"
    )

    print(
        f"Success Rate      : "
        f"{success_rate:.2f}%"
    )

    print("\n========================================")
    print("       BEHAVIOR ASSESSMENT")
    print("========================================")

    print(
        f"Behavior Score    : "
        f"{behavior_score}/100"
    )

    print(
        f"Behavior Status   : "
        f"{behavior_status}"
    )

    print("\n========================================")
    print("          WHY THIS RESULT?")
    print("========================================")

    if not reasons:
        print(
            "No behavioral explanation available."
        )
    else:
        for index, reason in enumerate(
            reasons,
            start=1
        ):
            print(
                f"{index}. {reason}"
            )

    print("\n========================================")
    print("        DATA CONFIDENCE")
    print("========================================")

    print(
        f"Confidence        : "
        f"{confidence}"
    )

    print(
        f"Reason            : "
        f"{confidence_reason}"
    )

    print("\n========================================")
    print("       CREDIT DECISION SUPPORT")
    print("========================================")

    print(
        f"Recommendation : "
        f"{recommendation}"
    )

    print("\n========================================")
    print("       MANAGEMENT SUMMARY")
    print("========================================")

    print(
        f"• ₦{outstanding:,.2f} remains outstanding."
    )

    print(
        f"• {outcome_count} repayment outcome(s) "
        "have been recorded."
    )

    print(
        f"• Fulfillment rate is "
        f"{fulfillment_rate:.2f}%."
    )

    print(
        f"• Behavior score is "
        f"{behavior_score}/100."
    )

    print(
        f"• Data confidence is "
        f"{confidence}."
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
    try:
        customer_id = int(
            input("Customer ID: ").strip()
        )

        repayment_behavior(customer_id)

    except ValueError:
        print(
            "Invalid Customer ID."
        )
