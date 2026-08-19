import sqlite3
from collections import defaultdict


DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def staff_collection_effectiveness():
    conn = get_connection()
    cur = conn.cursor()

    # ----------------------------------------
    # LOAD STAFF FOLLOW-UP ACTIVITY
    # ----------------------------------------
    followups = cur.execute("""
        SELECT
            id,
            customer_id,
            credit_id,
            staff_name,
            contact_date,
            contact_method,
            promised_amount,
            promised_date,
            status
        FROM collection_followups
        ORDER BY contact_date ASC
    """).fetchall()

    # ----------------------------------------
    # LOAD OUTCOMES
    # ----------------------------------------
    outcomes = cur.execute("""
        SELECT
            id,
            followup_id,
            customer_id,
            credit_id,
            promised_amount,
            matched_amount,
            outcome,
            outcome_date,
            staff_name
        FROM collection_outcomes
        ORDER BY outcome_date ASC
    """).fetchall()

    # ----------------------------------------
    # STAFF PROFILE
    # ----------------------------------------
    staff = defaultdict(lambda: {
        "followups": 0,
        "promised": 0.0,
        "outcomes": 0,
        "fulfilled": 0,
        "partial": 0,
        "missed": 0,
        "cancelled": 0,
        "outcome_promised": 0.0,
        "matched": 0.0,
        "customers": set(),
    })

    # ----------------------------------------
    # FOLLOW-UP DATA
    # ----------------------------------------
    for row in followups:
        name = row["staff_name"] or "UNKNOWN STAFF"

        staff[name]["followups"] += 1

        staff[name]["promised"] += float(
            row["promised_amount"] or 0
        )

        if row["customer_id"] is not None:
            staff[name]["customers"].add(
                row["customer_id"]
            )

    # ----------------------------------------
    # OUTCOME DATA
    # ----------------------------------------
    for row in outcomes:
        name = row["staff_name"] or "UNKNOWN STAFF"

        staff[name]["outcomes"] += 1

        staff[name]["outcome_promised"] += float(
            row["promised_amount"] or 0
        )

        staff[name]["matched"] += float(
            row["matched_amount"] or 0
        )

        outcome = (
            row["outcome"] or ""
        ).strip().upper()

        if outcome == "FULFILLED":
            staff[name]["fulfilled"] += 1

        elif outcome in (
            "PARTIALLY FULFILLED",
            "PARTIALLY FILLED",
            "PARTIAL",
        ):
            staff[name]["partial"] += 1

        elif outcome == "MISSED":
            staff[name]["missed"] += 1

        elif outcome == "CANCELLED":
            staff[name]["cancelled"] += 1

        if row["customer_id"] is not None:
            staff[name]["customers"].add(
                row["customer_id"]
            )

    # ----------------------------------------
    # CALCULATE EFFECTIVENESS
    # ----------------------------------------
    results = []

    for name, data in staff.items():

        promised = data["outcome_promised"]
        matched = data["matched"]

        if promised > 0:
            fulfillment_rate = (
                matched / promised * 100
            )
        else:
            fulfillment_rate = 0.0

        outcomes_count = data["outcomes"]

        if outcomes_count > 0:
            success_rate = (
                data["fulfilled"]
                / outcomes_count
                * 100
            )
        else:
            success_rate = 0.0

        # ------------------------------------
        # EFFECTIVENESS SCORE
        # ------------------------------------
        score = 0

        # Follow-up activity
        if data["followups"] >= 10:
            score += 25
        elif data["followups"] >= 5:
            score += 18
        elif data["followups"] >= 2:
            score += 10
        elif data["followups"] >= 1:
            score += 5

        # Outcome history
        if outcomes_count >= 10:
            score += 20
        elif outcomes_count >= 5:
            score += 15
        elif outcomes_count >= 2:
            score += 10
        elif outcomes_count >= 1:
            score += 5

        # Fulfillment rate
        if fulfillment_rate >= 90:
            score += 35
        elif fulfillment_rate >= 75:
            score += 25
        elif fulfillment_rate >= 50:
            score += 15
        elif fulfillment_rate > 0:
            score += 5

        # Missed promises
        if data["missed"] == 0:
            score += 10
        elif data["missed"] >= 3:
            score -= 10

        # Partial outcomes
        if data["partial"] > 0:
            score += 2

        score = max(
            0,
            min(100, score)
        )

        # ------------------------------------
        # STATUS
        # ------------------------------------
        if outcomes_count == 0:
            status = "🟡 LIMITED DATA"
            recommendation = (
                "CONTINUE FOLLOW-UP AND RECORD OUTCOMES"
            )

        elif score >= 80:
            status = "🟢 HIGHLY EFFECTIVE"
            recommendation = (
                "MAINTAIN COLLECTION APPROACH"
            )

        elif score >= 60:
            status = "🟢 EFFECTIVE"
            recommendation = (
                "CONTINUE CURRENT COLLECTION APPROACH"
            )

        elif score >= 40:
            status = "🟡 MODERATE EFFECTIVENESS"
            recommendation = (
                "IMPROVE FOLLOW-UP CONSISTENCY"
            )

        else:
            status = "🟠 NEEDS IMPROVEMENT"
            recommendation = (
                "REVIEW COLLECTION STRATEGY"
            )

        results.append({
            "staff": name,
            "followups": data["followups"],
            "promised": data["promised"],
            "customers": len(data["customers"]),
            "outcomes": outcomes_count,
            "fulfilled": data["fulfilled"],
            "partial": data["partial"],
            "missed": data["missed"],
            "cancelled": data["cancelled"],
            "outcome_promised": promised,
            "matched": matched,
            "fulfillment_rate": fulfillment_rate,
            "success_rate": success_rate,
            "score": score,
            "status": status,
            "recommendation": recommendation,
        })

    results.sort(
        key=lambda x: (
            -x["score"],
            -x["matched"],
            -x["followups"],
        )
    )

    # ----------------------------------------
    # PORTFOLIO TOTALS
    # ----------------------------------------
    total_followups = len(followups)

    total_promised = sum(
        float(r["promised_amount"] or 0)
        for r in followups
    )

    total_outcomes = len(outcomes)

    total_outcome_promised = sum(
        float(r["promised_amount"] or 0)
        for r in outcomes
    )

    total_matched = sum(
        float(r["matched_amount"] or 0)
        for r in outcomes
    )

    if total_outcome_promised > 0:
        portfolio_fulfillment = (
            total_matched
            / total_outcome_promised
            * 100
        )
    else:
        portfolio_fulfillment = 0.0

    # ----------------------------------------
    # REPORT
    # ----------------------------------------
    print("\n========================================")
    print("       POS LEDGER NG V25")
    print(" STAFF COLLECTION EFFECTIVENESS")
    print("========================================")

    print("\n========================================")
    print("        COLLECTION ACTIVITY")
    print("========================================")

    print(
        f"Staff Members       : {len(results)}"
    )

    print(
        f"Follow-ups Recorded : {total_followups}"
    )

    print(
        f"Promises Recorded   : "
        f"₦{total_promised:,.2f}"
    )

    print(
        f"Outcome Records     : {total_outcomes}"
    )

    print(
        f"Outcome Promised    : "
        f"₦{total_outcome_promised:,.2f}"
    )

    print(
        f"Matched Payments    : "
        f"₦{total_matched:,.2f}"
    )

    print(
        f"Portfolio Fulfillment: "
        f"{portfolio_fulfillment:.2f}%"
    )

    print("\n========================================")
    print("       STAFF PERFORMANCE")
    print("========================================")

    if not results:
        print(
            "No collection staff activity recorded."
        )

    for index, result in enumerate(
        results,
        start=1
    ):
        print("----------------------------------------")

        print(
            f"#{index} {result['staff']}"
        )

        print(
            f"Customers Handled   : "
            f"{result['customers']}"
        )

        print(
            f"Follow-ups          : "
            f"{result['followups']}"
        )

        print(
            f"Promises Recorded   : "
            f"₦{result['promised']:,.2f}"
        )

        print(
            f"Outcome Records     : "
            f"{result['outcomes']}"
        )

        print(
            f"Fulfilled           : "
            f"{result['fulfilled']}"
        )

        print(
            f"Partially Fulfilled : "
            f"{result['partial']}"
        )

        print(
            f"Missed              : "
            f"{result['missed']}"
        )

        print(
            f"Cancelled           : "
            f"{result['cancelled']}"
        )

        print(
            f"Outcome Promised    : "
            f"₦{result['outcome_promised']:,.2f}"
        )

        print(
            f"Matched Payments    : "
            f"₦{result['matched']:,.2f}"
        )

        print(
            f"Fulfillment Rate    : "
            f"{result['fulfillment_rate']:.2f}%"
        )

        print(
            f"Success Rate        : "
            f"{result['success_rate']:.2f}%"
        )

        print(
            f"Effectiveness Score : "
            f"{result['score']}/100"
        )

        print(
            f"Status              : "
            f"{result['status']}"
        )

        print(
            f"Recommendation      : "
            f"{result['recommendation']}"
        )

    print("\n========================================")
    print("       TOP COLLECTION STAFF")
    print("========================================")

    if results:
        top = results[0]

        print(
            f"Staff  : {top['staff']}"
        )

        print(
            f"Score  : {top['score']}/100"
        )

        print(
            f"Status : {top['status']}"
        )

        print(
            f"Action : {top['recommendation']}"
        )

    else:
        print(
            "No staff performance data available."
        )

    print("\n========================================")
    print("       MANAGEMENT SUMMARY")
    print("========================================")

    if not results:
        print(
            "STATUS : 🟡 NO COLLECTION ACTIVITY"
        )

        print(
            "• No staff collection activity has "
            "been recorded."
        )

    elif total_outcomes == 0:
        print(
            "STATUS : 🟡 OUTCOME DATA NEEDED"
        )

        print(
            "• Staff follow-up activity exists."
        )

        print(
            "• Collection outcomes have not yet "
            "been recorded."
        )

        print(
            "• Record whether promises were "
            "fulfilled, partially fulfilled, "
            "missed, or cancelled."
        )

    elif portfolio_fulfillment >= 80:
        print(
            "STATUS : 🟢 STRONG COLLECTION PERFORMANCE"
        )

        print(
            "• Collection outcomes show strong "
            "fulfillment."
        )

    elif portfolio_fulfillment >= 50:
        print(
            "STATUS : 🟡 MODERATE COLLECTION PERFORMANCE"
        )

        print(
            "• Collection performance requires "
            "continued monitoring."
        )

    else:
        print(
            "STATUS : 🟠 COLLECTION PERFORMANCE "
            "NEEDS ATTENTION"
        )

        print(
            "• Promise fulfillment is currently "
            "below target."
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
    staff_collection_effectiveness()
