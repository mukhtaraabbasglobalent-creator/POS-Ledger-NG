import sqlite3
from datetime import datetime

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def repayment_trend(customer_id):
    conn = get_connection()
    cur = conn.cursor()

    customer = cur.execute("""
        SELECT id, fullname, phone, credit_limit
        FROM customers
        WHERE id = ?
    """, (customer_id,)).fetchone()

    if not customer:
        print(f"Customer ID {customer_id} was not found.")
        conn.close()
        return

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

    collection_rate = (
        total_paid / total_credit * 100
        if total_credit > 0 else 0
    )

    outcome_count = len(outcomes)

    fulfilled = 0
    partial = 0
    missed = 0
    cancelled = 0

    promised_total = 0.0
    matched_total = 0.0

    timeline = []

    for row in outcomes:
        promised = float(row["promised_amount"] or 0)
        matched = float(row["matched_amount"] or 0)

        promised_total += promised
        matched_total += matched

        status = (row["outcome"] or "").strip().upper()

        if status == "FULFILLED":
            fulfilled += 1
        elif status in (
            "PARTIALLY FULFILLED",
            "PARTIALLY FILLED",
            "PARTIAL"
        ):
            partial += 1
        elif status == "MISSED":
            missed += 1
        elif status == "CANCELLED":
            cancelled += 1

        timeline.append({
            "id": row["id"],
            "date": row["outcome_date"],
            "outcome": status,
            "promised": promised,
            "matched": matched,
        })

    amount_fulfillment = (
        matched_total / promised_total * 100
        if promised_total > 0 else 0
    )

    # ----------------------------------------
    # RECENT PERFORMANCE
    # ----------------------------------------
    recent = timeline[-3:]

    recent_promised = sum(
        item["promised"] for item in recent
    )

    recent_matched = sum(
        item["matched"] for item in recent
    )

    recent_rate = (
        recent_matched / recent_promised * 100
        if recent_promised > 0 else 0
    )

    # ----------------------------------------
    # EARLY PERFORMANCE
    # ----------------------------------------
    early = timeline[:3]

    early_promised = sum(
        item["promised"] for item in early
    )

    early_matched = sum(
        item["matched"] for item in early
    )

    early_rate = (
        early_matched / early_promised * 100
        if early_promised > 0 else 0
    )

    # ----------------------------------------
    # TREND
    # ----------------------------------------
    if outcome_count < 2:
        trend = "🟡 INSUFFICIENT TREND DATA"
        trend_score = None
        trend_reason = (
            "At least two repayment outcomes "
            "are required to establish a trend."
        )

    else:
        difference = recent_rate - early_rate

        if difference >= 20:
            trend = "🟢 STRONGLY IMPROVING"
            trend_score = 90
            trend_reason = (
                "Recent repayment performance is "
                "substantially better than earlier performance."
            )

        elif difference >= 5:
            trend = "🟢 IMPROVING"
            trend_score = 75
            trend_reason = (
                "Recent repayment performance has improved."
            )

        elif difference > -5:
            trend = "🟡 STABLE"
            trend_score = 60
            trend_reason = (
                "Repayment performance is relatively stable."
            )

        elif difference > -20:
            trend = "🟠 DECLINING"
            trend_score = 40
            trend_reason = (
                "Recent repayment performance is weaker "
                "than earlier performance."
            )

        else:
            trend = "🔴 STRONGLY DECLINING"
            trend_score = 20
            trend_reason = (
                "Recent repayment performance has "
                "declined substantially."
            )

    # ----------------------------------------
    # RELIABILITY SCORE
    # ----------------------------------------
    if outcome_count == 0:
        reliability_score = 0
        reliability_status = "🔴 NO REPAYMENT EVIDENCE"

    else:
        reliability_score = 0

        reliability_score += min(
            50,
            int(amount_fulfillment * 0.5)
        )

        reliability_score += min(
            20,
            fulfilled * 10
        )

        reliability_score += min(
            10,
            partial * 5
        )

        reliability_score -= min(
            20,
            missed * 10
        )

        reliability_score -= min(
            10,
            cancelled * 5
        )

        reliability_score = max(
            0,
            min(100, reliability_score)
        )

        if reliability_score >= 80:
            reliability_status = "🟢 HIGH RELIABILITY"

        elif reliability_score >= 60:
            reliability_status = "🟢 GOOD RELIABILITY"

        elif reliability_score >= 40:
            reliability_status = "🟡 MODERATE RELIABILITY"

        elif reliability_score >= 20:
            reliability_status = "🟠 LOW RELIABILITY"

        else:
            reliability_status = "🔴 VERY LOW RELIABILITY"

    # ----------------------------------------
    # CONFIDENCE
    # ----------------------------------------
    if outcome_count >= 5:
        confidence = "🟢 HIGH"
        confidence_reason = (
            "Five or more repayment outcomes are available."
        )

    elif outcome_count >= 3:
        confidence = "🟡 MODERATE"
        confidence_reason = (
            "Several repayment outcomes are available."
        )

    elif outcome_count >= 2:
        confidence = "🟠 LIMITED"
        confidence_reason = (
            "Only two repayment outcomes are available."
        )

    elif outcome_count == 1:
        confidence = "🟠 VERY LIMITED"
        confidence_reason = (
            "Only one repayment outcome is available."
        )

    else:
        confidence = "🔴 VERY LIMITED"
        confidence_reason = (
            "No repayment outcome records are available."
        )

    # ----------------------------------------
    # MANAGEMENT RECOMMENDATION
    # ----------------------------------------
    if outcome_count == 0:
        recommendation = (
            "COLLECT MORE REPAYMENT EVIDENCE"
        )

    elif trend_score is not None and trend_score <= 20:
        recommendation = (
            "INCREASE COLLECTION MONITORING"
        )

    elif reliability_score < 30:
        recommendation = (
            "USE CAUTIOUS CREDIT MONITORING"
        )

    elif trend_score is not None and trend_score >= 75:
        recommendation = (
            "CONTINUE MONITORING — REPAYMENT TREND IMPROVING"
        )

    elif reliability_score >= 60:
        recommendation = (
            "NORMAL CREDIT MONITORING"
        )

    else:
        recommendation = (
            "MONITOR FUTURE REPAYMENT PERFORMANCE"
        )

    # ----------------------------------------
    # REPORT
    # ----------------------------------------
    print("\n========================================")
    print("       POS LEDGER NG V28")
    print("      REPAYMENT TREND ANALYSIS")
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
        f"₦{float(customer['credit_limit'] or 0):,.2f}"
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
        f"Collection Rate  : {collection_rate:.2f}%"
    )

    print("\n========================================")
    print("        OUTCOME HISTORY")
    print("========================================")

    print(
        f"Outcome Records   : {outcome_count}"
    )

    print(
        f"Fulfilled         : {fulfilled}"
    )

    print(
        f"Partially Filled  : {partial}"
    )

    print(
        f"Missed            : {missed}"
    )

    print(
        f"Cancelled         : {cancelled}"
    )

    print("\n========================================")
    print("       REPAYMENT PERFORMANCE")
    print("========================================")

    print(
        f"Promised Amount   : "
        f"₦{promised_total:,.2f}"
    )

    print(
        f"Matched Amount    : "
        f"₦{matched_total:,.2f}"
    )

    print(
        f"Overall Fulfillment : "
        f"{amount_fulfillment:.2f}%"
    )

    print(
        f"Early Performance  : "
        f"{early_rate:.2f}%"
    )

    print(
        f"Recent Performance : "
        f"{recent_rate:.2f}%"
    )

    print("\n========================================")
    print("          REPAYMENT TREND")
    print("========================================")

    print(
        f"Trend Status  : {trend}"
    )

    if trend_score is not None:
        print(
            f"Trend Score   : "
            f"{trend_score}/100"
        )

    print(
        f"Reason        : "
        f"{trend_reason}"
    )

    print("\n========================================")
    print("       RELIABILITY ASSESSMENT")
    print("========================================")

    print(
        f"Reliability Score  : "
        f"{reliability_score}/100"
    )

    print(
        f"Reliability Status : "
        f"{reliability_status}"
    )

    print("\n========================================")
    print("        DATA CONFIDENCE")
    print("========================================")

    print(
        f"Confidence : {confidence}"
    )

    print(
        f"Reason     : {confidence_reason}"
    )

    print("\n========================================")
    print("       MANAGEMENT RECOMMENDATION")
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
        "are available."
    )

    print(
        f"• Overall fulfillment is "
        f"{amount_fulfillment:.2f}%."
    )

    print(
        f"• Reliability score is "
        f"{reliability_score}/100."
    )

    print(
        f"• Trend status is "
        f"{trend}."
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

        repayment_trend(customer_id)

    except ValueError:
        print("Invalid Customer ID.")
