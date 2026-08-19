import sqlite3
from datetime import datetime

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def credit_intelligence_dashboard(customer_id):
    conn = get_connection()
    cur = conn.cursor()

    # ========================================
    # CUSTOMER
    # ========================================
    customer = cur.execute("""
        SELECT id, fullname, phone, credit_limit
        FROM customers
        WHERE id = ?
    """, (customer_id,)).fetchone()

    if not customer:
        print(f"Customer ID {customer_id} not found.")
        conn.close()
        return

    # ========================================
    # CREDIT POSITION
    # ========================================
    credit = cur.execute("""
        SELECT
            COALESCE(SUM(total_amount), 0) AS total_credit,
            COALESCE(SUM(amount_paid), 0) AS total_paid,
            COALESCE(SUM(balance), 0) AS outstanding,
            COUNT(*) AS accounts
        FROM customer_credit
        WHERE customer_id = ?
    """, (customer_id,)).fetchone()

    total_credit = float(credit["total_credit"] or 0)
    total_paid = float(credit["total_paid"] or 0)
    outstanding = float(credit["outstanding"] or 0)
    accounts = int(credit["accounts"] or 0)

    credit_limit = float(customer["credit_limit"] or 0)

    credit_used = (
        outstanding / credit_limit * 100
        if credit_limit > 0 else 0
    )

    collection_rate = (
        total_paid / total_credit * 100
        if total_credit > 0 else 0
    )

    # ========================================
    # OUTCOME HISTORY
    # ========================================
    outcomes = cur.execute("""
        SELECT
            id,
            promised_amount,
            matched_amount,
            outcome,
            outcome_date
        FROM collection_outcomes
        WHERE customer_id = ?
        ORDER BY outcome_date ASC, id ASC
    """, (customer_id,)).fetchall()

    outcome_count = len(outcomes)

    fulfilled = 0
    partial = 0
    missed = 0
    cancelled = 0

    promised_total = 0.0
    matched_total = 0.0

    for row in outcomes:
        promised = float(row["promised_amount"] or 0)
        matched = float(row["matched_amount"] or 0)

        promised_total += promised
        matched_total += matched

        outcome = (row["outcome"] or "").upper()

        if outcome == "FULFILLED":
            fulfilled += 1

        elif outcome in (
            "PARTIALLY FULFILLED",
            "PARTIALLY FILLED",
            "PARTIAL"
        ):
            partial += 1

        elif outcome == "MISSED":
            missed += 1

        elif outcome == "CANCELLED":
            cancelled += 1

    fulfillment_rate = (
        matched_total / promised_total * 100
        if promised_total > 0 else 0
    )

    # ========================================
    # BEHAVIOR SCORE
    # ========================================
    if outcome_count == 0:
        behavior_score = 0
        behavior_status = "INSUFFICIENT DATA"

    else:
        behavior_score = 0

        if fulfillment_rate >= 90:
            behavior_score += 60

        elif fulfillment_rate >= 75:
            behavior_score += 50

        elif fulfillment_rate >= 50:
            behavior_score += 35

        elif fulfillment_rate >= 25:
            behavior_score += 20

        else:
            behavior_score += 5

        behavior_score -= min(30, missed * 15)
        behavior_score -= min(20, cancelled * 5)

        behavior_score = max(0, min(100, behavior_score))

        if behavior_score >= 70:
            behavior_status = "STRONG"

        elif behavior_score >= 50:
            behavior_status = "GOOD"

        elif behavior_score >= 30:
            behavior_status = "MODERATE"

        else:
            behavior_status = "WEAK"

    # ========================================
    # TREND
    # ========================================
    trend_status = "INSUFFICIENT TREND DATA"

    if outcome_count >= 3:
        midpoint = outcome_count // 2

        first = outcomes[:midpoint]
        recent = outcomes[midpoint:]

        def rate(rows):
            promised = sum(
                float(r["promised_amount"] or 0)
                for r in rows
            )

            matched = sum(
                float(r["matched_amount"] or 0)
                for r in rows
            )

            return (
                matched / promised * 100
                if promised > 0 else 0
            )

        first_rate = rate(first)
        recent_rate = rate(recent)

        difference = recent_rate - first_rate

        if difference >= 15:
            trend_status = "🟢 IMPROVING"

        elif difference <= -15:
            trend_status = "🔴 DECLINING"

        else:
            trend_status = "🟡 STABLE"

    # ========================================
    # RISK SCORE
    # ========================================
    risk_score = 0

    if credit_used >= 80:
        risk_score += 40

    elif credit_used >= 60:
        risk_score += 30

    elif credit_used >= 40:
        risk_score += 20

    elif credit_used >= 20:
        risk_score += 10

    if collection_rate < 20:
        risk_score += 20

    elif collection_rate < 40:
        risk_score += 15

    elif collection_rate < 60:
        risk_score += 10

    elif collection_rate < 80:
        risk_score += 5

    if missed > 0:
        risk_score += min(20, missed * 10)

    if partial > 0:
        risk_score += min(10, partial * 5)

    risk_score = min(100, risk_score)

    if risk_score >= 70:
        risk_status = "🔴 CRITICAL"

    elif risk_score >= 50:
        risk_status = "🟠 HIGH"

    elif risk_score >= 30:
        risk_status = "🟡 MODERATE"

    else:
        risk_status = "🟢 LOW"

    # ========================================
    # ACTIVE PROMISES
    # ========================================
    today = datetime.now().strftime("%Y-%m-%d")

    promise = cur.execute("""
        SELECT
            COALESCE(SUM(promised_amount), 0) AS amount,
            COUNT(*) AS count
        FROM collection_followups
        WHERE customer_id = ?
          AND status = 'PROMISE'
          AND promised_date >= ?
    """, (customer_id, today)).fetchone()

    active_promises = float(promise["amount"] or 0)
    promise_count = int(promise["count"] or 0)

    # ========================================
    # COLLECTION PRIORITY
    # ========================================
    priority_score = 0

    if outstanding >= 100000:
        priority_score += 35

    elif outstanding >= 50000:
        priority_score += 30

    elif outstanding >= 20000:
        priority_score += 20

    elif outstanding >= 10000:
        priority_score += 15

    elif outstanding > 0:
        priority_score += 10

    if collection_rate < 20:
        priority_score += 20

    elif collection_rate < 40:
        priority_score += 15

    elif collection_rate < 60:
        priority_score += 10

    if risk_score >= 70:
        priority_score += 30

    elif risk_score >= 50:
        priority_score += 20

    elif risk_score >= 30:
        priority_score += 10

    if active_promises > 0:
        priority_score -= 5

    priority_score = max(0, min(100, priority_score))

    if priority_score >= 70:
        priority_status = "🔴 URGENT"

    elif priority_score >= 50:
        priority_status = "🟠 HIGH"

    elif priority_score >= 30:
        priority_status = "🟡 MEDIUM"

    else:
        priority_status = "🟢 MONITOR"

    # ========================================
    # CREDIT DECISION
    # ========================================
    if risk_score >= 70:
        decision = "🔴 DECLINE / INTENSIVE REVIEW"
        action = "Do not increase credit exposure."

    elif risk_score >= 50:
        decision = "🟠 REDUCE CREDIT EXPOSURE"
        action = "Collect existing debt before increasing credit."

    elif risk_score >= 30:
        decision = "🟡 APPROVE WITH CAUTION"
        action = "Maintain close repayment monitoring."

    elif outcome_count == 0:
        decision = "🟡 MONITOR — LIMITED EVIDENCE"
        action = "Collect repayment history before increasing exposure."

    elif fulfillment_rate < 50:
        decision = "🟡 APPROVE WITH CAUTION"
        action = "Monitor future repayment closely."

    else:
        decision = "🟢 NORMAL CREDIT MONITORING"
        action = "Current evidence supports normal monitoring."

    # ========================================
    # DATA CONFIDENCE
    # ========================================
    if outcome_count >= 5:
        confidence = "🟢 HIGH"

    elif outcome_count >= 3:
        confidence = "🟡 MODERATE"

    elif outcome_count >= 1:
        confidence = "🟠 LIMITED"

    else:
        confidence = "🔴 VERY LIMITED"

    # ========================================
    # EXPLANATION
    # ========================================
    reasons = []

    if credit_used < 20:
        reasons.append(
            f"Low credit utilization ({credit_used:.2f}%)."
        )

    elif credit_used >= 60:
        reasons.append(
            f"High credit utilization ({credit_used:.2f}%)."
        )

    if collection_rate < 40:
        reasons.append(
            f"Collection rate needs attention ({collection_rate:.2f}%)."
        )

    elif collection_rate >= 70:
        reasons.append(
            f"Strong collection rate ({collection_rate:.2f}%)."
        )

    if outcome_count == 0:
        reasons.append(
            "No repayment outcome history is available."
        )

    elif fulfillment_rate >= 70:
        reasons.append(
            "Repayment fulfillment evidence is positive."
        )

    else:
        reasons.append(
            "Repayment evidence is still limited or mixed."
        )

    if missed > 0:
        reasons.append(
            f"{missed} repayment promise(s) were missed."
        )

    if active_promises > 0:
        reasons.append(
            f"₦{active_promises:,.2f} is covered by active payment promise(s)."
        )

    # ========================================
    # FINAL DASHBOARD
    # ========================================
    print("\n========================================")
    print("       POS LEDGER NG V30")
    print("  CREDIT INTELLIGENCE DASHBOARD")
    print("========================================")

    print("\n========================================")
    print("       CUSTOMER INFORMATION")
    print("========================================")
    print(f"Customer ID   : {customer['id']}")
    print(f"Customer Name : {customer['fullname']}")
    print(f"Phone         : {customer['phone']}")
    print(f"Credit Limit  : ₦{credit_limit:,.2f}")

    print("\n========================================")
    print("        CREDIT POSITION")
    print("========================================")
    print(f"Total Credit     : ₦{total_credit:,.2f}")
    print(f"Total Paid       : ₦{total_paid:,.2f}")
    print(f"Outstanding      : ₦{outstanding:,.2f}")
    print(f"Credit Accounts  : {accounts}")
    print(f"Credit Used      : {credit_used:.2f}%")
    print(f"Collection Rate  : {collection_rate:.2f}%")

    print("\n========================================")
    print("        RISK INTELLIGENCE")
    print("========================================")
    print(f"Risk Score       : {risk_score}/100")
    print(f"Risk Status      : {risk_status}")
    print(f"Priority Score   : {priority_score}/100")
    print(f"Priority         : {priority_status}")

    print("\n========================================")
    print("       REPAYMENT INTELLIGENCE")
    print("========================================")
    print(f"Outcome Records  : {outcome_count}")
    print(f"Fulfilled        : {fulfilled}")
    print(f"Partially Filled : {partial}")
    print(f"Missed           : {missed}")
    print(f"Cancelled        : {cancelled}")
    print(f"Promised Total   : ₦{promised_total:,.2f}")
    print(f"Matched Total    : ₦{matched_total:,.2f}")
    print(f"Fulfillment Rate : {fulfillment_rate:.2f}%")
    print(f"Behavior Score   : {behavior_score}/100")
    print(f"Behavior Status  : {behavior_status}")
    print(f"Trend Status     : {trend_status}")

    print("\n========================================")
    print("       COLLECTION INTELLIGENCE")
    print("========================================")
    print(f"Active Promises  : {promise_count}")
    print(f"Promised Amount  : ₦{active_promises:,.2f}")

    print("\n========================================")
    print("        CREDIT DECISION")
    print("========================================")
    print(f"Decision         : {decision}")
    print(f"Action           : {action}")

    print("\n========================================")
    print("        DATA CONFIDENCE")
    print("========================================")
    print(f"Confidence       : {confidence}")

    print("\n========================================")
    print("       WHY THIS RESULT?")
    print("========================================")

    for number, reason in enumerate(reasons, 1):
        print(f"{number}. {reason}")

    print("\n========================================")
    print("       MANAGEMENT SUMMARY")
    print("========================================")
    print(f"• ₦{outstanding:,.2f} remains outstanding.")
    print(f"• Risk score is {risk_score}/100.")
    print(f"• Collection priority is {priority_status}.")
    print(f"• Repayment behavior is {behavior_status}.")
    print(f"• Trend status is {trend_status}.")
    print(f"• Data confidence is {confidence}.")
    print(f"• Final decision: {decision}.")

    print("----------------------------------------")
    print("V30 INTEGRATION STATUS : READ-ONLY")
    print("Credit/payment records were NOT modified.")
    print("========================================")

    conn.close()

    input("\nPress Enter to continue...")


if __name__ == "__main__":
    try:
        customer_id = int(input("Customer ID: ").strip())
        credit_intelligence_dashboard(customer_id)

    except ValueError:
        print("Invalid Customer ID.")
