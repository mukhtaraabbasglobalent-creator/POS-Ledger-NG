import sqlite3
from datetime import datetime

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def credit_decision(customer_id):
    conn = get_connection()
    cur = conn.cursor()

    # ----------------------------------------
    # CUSTOMER
    # ----------------------------------------
    customer = cur.execute("""
        SELECT id, fullname, phone, credit_limit
        FROM customers
        WHERE id = ?
    """, (customer_id,)).fetchone()

    if not customer:
        print(f"Customer ID {customer_id} was not found.")
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

    # ----------------------------------------
    # OUTCOME HISTORY
    # ----------------------------------------
    outcomes = cur.execute("""
        SELECT
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

    # ----------------------------------------
    # ACTIVE PROMISES
    # ----------------------------------------
    today = datetime.now().strftime("%Y-%m-%d")

    promises = cur.execute("""
        SELECT
            COALESCE(SUM(promised_amount), 0) AS promised_total,
            COUNT(*) AS promise_count
        FROM collection_followups
        WHERE customer_id = ?
          AND status = 'PROMISE'
          AND promised_date >= ?
    """, (customer_id, today)).fetchone()

    active_promises = float(promises["promised_total"] or 0)
    promise_count = int(promises["promise_count"] or 0)

    # ----------------------------------------
    # RISK SCORE
    # ----------------------------------------
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

    # ----------------------------------------
    # DATA CONFIDENCE
    # ----------------------------------------
    if outcome_count >= 5:
        confidence = "🟢 HIGH"

    elif outcome_count >= 3:
        confidence = "🟡 MODERATE"

    elif outcome_count >= 1:
        confidence = "🟠 LIMITED"

    else:
        confidence = "🔴 VERY LIMITED"

    # ----------------------------------------
    # REPAYMENT BEHAVIOR
    # ----------------------------------------
    if outcome_count == 0:
        behavior = "INSUFFICIENT EVIDENCE"

    elif fulfillment_rate >= 80:
        behavior = "STRONG"

    elif fulfillment_rate >= 60:
        behavior = "GOOD"

    elif fulfillment_rate >= 40:
        behavior = "MODERATE"

    else:
        behavior = "WEAK"

    # ----------------------------------------
    # DECISION ENGINE
    # ----------------------------------------
    decision_score = 100 - risk_score

    reasons = []

    if credit_used < 20:
        reasons.append(
            "Credit utilization is low."
        )

    elif credit_used >= 60:
        reasons.append(
            "Credit utilization is high."
        )

    if collection_rate < 40:
        reasons.append(
            "Collection rate needs attention."
        )

    elif collection_rate >= 70:
        reasons.append(
            "Collection performance is strong."
        )

    if outcome_count == 0:
        reasons.append(
            "No repayment outcome history is available."
        )

    elif fulfillment_rate >= 80:
        reasons.append(
            "Repayment fulfillment performance is strong."
        )

    elif fulfillment_rate >= 40:
        reasons.append(
            "Repayment performance is mixed."
        )

    else:
        reasons.append(
            "Repayment performance is weak."
        )

    if active_promises > 0:
        reasons.append(
            f"₦{active_promises:,.2f} is covered by active "
            "future collection promise(s)."
        )

    if missed > 0:
        reasons.append(
            f"{missed} repayment promise(s) were missed."
        )

    # ----------------------------------------
    # FINAL DECISION
    # ----------------------------------------
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

    # ----------------------------------------
    # REPORT
    # ----------------------------------------
    print("\n========================================")
    print("       POS LEDGER NG V29")
    print("      CREDIT DECISION ENGINE")
    print("========================================")

    print("\n========================================")
    print("       CUSTOMER INFORMATION")
    print("========================================")

    print(f"Customer ID   : {customer['id']}")
    print(f"Customer Name : {customer['fullname']}")
    print(f"Phone         : {customer['phone']}")
    print(
        f"Credit Limit  : "
        f"₦{credit_limit:,.2f}"
    )

    print("\n========================================")
    print("        CREDIT POSITION")
    print("========================================")

    print(
        f"Total Credit     : ₦{total_credit:,.2f}"
    )

    print(
        f"Total Paid       : ₦{total_paid:,.2f}"
    )

    print(
        f"Outstanding      : ₦{outstanding:,.2f}"
    )

    print(
        f"Credit Accounts  : {accounts}"
    )

    print(
        f"Credit Used      : {credit_used:.2f}%"
    )

    print(
        f"Collection Rate  : {collection_rate:.2f}%"
    )

    print("\n========================================")
    print("       REPAYMENT EVIDENCE")
    print("========================================")

    print(
        f"Outcome Records  : {outcome_count}"
    )

    print(
        f"Fulfilled        : {fulfilled}"
    )

    print(
        f"Partially Filled : {partial}"
    )

    print(
        f"Missed           : {missed}"
    )

    print(
        f"Cancelled        : {cancelled}"
    )

    print(
        f"Fulfillment Rate : {fulfillment_rate:.2f}%"
    )

    print(
        f"Behavior         : {behavior}"
    )

    print("\n========================================")
    print("        ACTIVE COLLECTION")
    print("========================================")

    print(
        f"Active Promises  : {promise_count}"
    )

    print(
        f"Promised Amount  : "
        f"₦{active_promises:,.2f}"
    )

    print("\n========================================")
    print("          RISK ASSESSMENT")
    print("========================================")

    print(
        f"Risk Score       : "
        f"{risk_score}/100"
    )

    print(
        f"Risk Status      : "
        f"{risk_status}"
    )

    print(
        f"Decision Score   : "
        f"{decision_score}/100"
    )

    print("\n========================================")
    print("          DATA CONFIDENCE")
    print("========================================")

    print(
        f"Confidence       : "
        f"{confidence}"
    )

    print("\n========================================")
    print("       CREDIT DECISION")
    print("========================================")

    print(
        f"DECISION : {decision}"
    )

    print(
        f"ACTION   : {action}"
    )

    print("\n========================================")
    print("        WHY THIS DECISION?")
    print("========================================")

    for index, reason in enumerate(reasons, 1):
        print(f"{index}. {reason}")

    print("\n========================================")
    print("       MANAGEMENT SUMMARY")
    print("========================================")

    print(
        f"• ₦{outstanding:,.2f} remains outstanding."
    )

    print(
        f"• Risk score is {risk_score}/100."
    )

    print(
        f"• Risk status is {risk_status}."
    )

    print(
        f"• Repayment behavior is {behavior}."
    )

    print(
        f"• Data confidence is {confidence}."
    )

    print(
        f"• Final decision: {decision}."
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

        credit_decision(customer_id)

    except ValueError:
        print("Invalid Customer ID.")
