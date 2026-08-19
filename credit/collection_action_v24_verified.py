import sqlite3
from datetime import datetime


DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def collection_action():
    conn = get_connection()
    cur = conn.cursor()

    customers = cur.execute("""
        SELECT
            id,
            fullname,
            phone,
            credit_limit
        FROM customers
        ORDER BY id
    """).fetchall()

    records = []

    for customer in customers:
        customer_id = customer["id"]

        credit = cur.execute("""
            SELECT
                COALESCE(SUM(total_amount), 0)
                    AS total_credit,
                COALESCE(SUM(amount_paid), 0)
                    AS total_paid,
                COALESCE(SUM(balance), 0)
                    AS outstanding,
                MIN(created_date)
                    AS oldest_date
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

        if total_credit <= 0 and outstanding <= 0:
            continue

        collection_rate = (
            total_paid / total_credit * 100
            if total_credit > 0
            else 0
        )

        credit_limit = float(
            customer["credit_limit"] or 0
        )

        credit_used = (
            outstanding / credit_limit * 100
            if credit_limit > 0
            else 0
        )

        # ----------------------------------------
        # DEBT AGE
        # ----------------------------------------
        debt_age = 0

        if credit["oldest_date"]:
            try:
                oldest = datetime.strptime(
                    credit["oldest_date"],
                    "%Y-%m-%d %H:%M:%S"
                )

                debt_age = max(
                    0,
                    (datetime.now() - oldest).days
                )

            except (ValueError, TypeError):
                debt_age = 0

        # ----------------------------------------
        # FOLLOW-UPS
        # ----------------------------------------
        followup = cur.execute("""
            SELECT
                COUNT(*) AS count,
                COALESCE(
                    SUM(promised_amount),
                    0
                ) AS promised
            FROM collection_followups
            WHERE customer_id = ?
        """, (customer_id,)).fetchone()

        followups = int(
            followup["count"] or 0
        )

        promised_total = float(
            followup["promised"] or 0
        )

        # ----------------------------------------
        # PROMISES
        # ----------------------------------------
        today = datetime.now().strftime(
            "%Y-%m-%d"
        )

        upcoming = cur.execute("""
            SELECT
                COALESCE(
                    SUM(promised_amount),
                    0
                ) AS amount,
                MIN(promised_date)
                    AS next_date
            FROM collection_followups
            WHERE customer_id = ?
            AND status = 'PROMISE'
            AND promised_date >= ?
        """, (
            customer_id,
            today
        )).fetchone()

        upcoming_amount = float(
            upcoming["amount"] or 0
        )

        next_promise_date = (
            upcoming["next_date"]
        )

        overdue = cur.execute("""
            SELECT
                COUNT(*) AS count,
                COALESCE(
                    SUM(promised_amount),
                    0
                ) AS amount
            FROM collection_followups
            WHERE customer_id = ?
            AND status = 'PROMISE'
            AND promised_date < ?
        """, (
            customer_id,
            today
        )).fetchone()

        overdue_count = int(
            overdue["count"] or 0
        )

        overdue_amount = float(
            overdue["amount"] or 0
        )

        # ----------------------------------------
        # OUTCOME HISTORY
        # ----------------------------------------
        outcomes = cur.execute("""
            SELECT
                COUNT(*) AS total,
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
        """, (customer_id,)).fetchone()

        outcome_total = int(
            outcomes["total"] or 0
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

        # ----------------------------------------
        # SIMPLE RISK SCORE
        # ----------------------------------------
        risk_score = 0

        if credit_used >= 80:
            risk_score += 30
        elif credit_used >= 60:
            risk_score += 20
        elif credit_used >= 40:
            risk_score += 10
        elif credit_used >= 20:
            risk_score += 5

        if collection_rate < 25:
            risk_score += 25
        elif collection_rate < 50:
            risk_score += 15
        elif collection_rate < 75:
            risk_score += 5

        if outcome_total > 0:
            missed_rate = (
                missed / outcome_total * 100
            )

            partial_rate = (
                partial / outcome_total * 100
            )

            if missed_rate >= 50:
                risk_score += 30
            elif missed_rate > 0:
                risk_score += 20

            if partial_rate >= 50:
                risk_score += 15
            elif partial_rate > 0:
                risk_score += 5

        risk_score = max(
            0,
            min(100, risk_score)
        )

        # ----------------------------------------
        # ACTION SCORE
        # ----------------------------------------
        action_score = 0

        if outstanding >= 20000:
            action_score += 25
        elif outstanding >= 10000:
            action_score += 18
        elif outstanding >= 5000:
            action_score += 12
        elif outstanding > 0:
            action_score += 6

        if debt_age >= 30:
            action_score += 25
        elif debt_age >= 14:
            action_score += 18
        elif debt_age >= 7:
            action_score += 10
        elif debt_age >= 3:
            action_score += 5

        if collection_rate < 25:
            action_score += 20
        elif collection_rate < 50:
            action_score += 12
        elif collection_rate < 75:
            action_score += 5

        if overdue_count > 0:
            action_score += 20

        if upcoming_amount > 0:
            action_score += 3

        if risk_score >= 75:
            action_score += 20
        elif risk_score >= 50:
            action_score += 15
        elif risk_score >= 25:
            action_score += 8

        if followups == 0 and outstanding > 0:
            action_score += 5

        action_score = max(
            0,
            min(100, action_score)
        )

        # ----------------------------------------
        # ACTION DECISION
        # ----------------------------------------
        if overdue_count > 0:
            priority = "🔴 URGENT"
            action = "CONTACT CUSTOMER IMMEDIATELY"
            reason = (
                "Customer has an overdue payment promise."
            )

        elif action_score >= 60:
            priority = "🔴 HIGH"
            action = "ACTIVE COLLECTION FOLLOW-UP"
            reason = (
                "Outstanding debt and collection "
                "indicators require attention."
            )

        elif action_score >= 30:
            priority = "🟡 MEDIUM"
            action = "SCHEDULE FOLLOW-UP"
            reason = (
                "Customer requires planned collection "
                "monitoring."
            )

        elif upcoming_amount > 0:
            priority = "🟢 MONITOR"
            action = "MONITOR PROMISED PAYMENT"
            reason = (
                "Customer has an active future payment promise."
            )

        else:
            priority = "🟢 LOW"
            action = "NORMAL MONITORING"
            reason = (
                "No urgent collection trigger detected."
            )

        records.append({
            "id": customer_id,
            "fullname": customer["fullname"],
            "phone": customer["phone"],
            "outstanding": outstanding,
            "collection_rate": collection_rate,
            "credit_used": credit_used,
            "debt_age": debt_age,
            "followups": followups,
            "promised_total": promised_total,
            "upcoming_amount": upcoming_amount,
            "next_promise_date": next_promise_date,
            "overdue_count": overdue_count,
            "overdue_amount": overdue_amount,
            "risk_score": risk_score,
            "action_score": action_score,
            "priority": priority,
            "action": action,
            "reason": reason,
        })

    records.sort(
        key=lambda r: (
            -r["action_score"],
            -r["outstanding"]
        )
    )

    # ----------------------------------------
    # REPORT
    # ----------------------------------------
    print("\n========================================")
    print("       POS LEDGER NG V24")
    print("      COLLECTION ACTION PLANNER")
    print("========================================")

    print("\n========================================")
    print("        ACTION OVERVIEW")
    print("========================================")

    print(
        f"Customers With Credit : {len(records)}"
    )

    urgent = sum(
        1 for r in records
        if r["priority"] == "🔴 URGENT"
    )

    high = sum(
        1 for r in records
        if r["priority"] == "🔴 HIGH"
    )

    medium = sum(
        1 for r in records
        if r["priority"] == "🟡 MEDIUM"
    )

    monitor = sum(
        1 for r in records
        if r["priority"] == "🟢 MONITOR"
    )

    low = sum(
        1 for r in records
        if r["priority"] == "🟢 LOW"
    )

    print(f"Urgent              : {urgent}")
    print(f"High                : {high}")
    print(f"Medium              : {medium}")
    print(f"Monitor             : {monitor}")
    print(f"Low                 : {low}")

    print("\n========================================")
    print("       CUSTOMER ACTION QUEUE")
    print("========================================")

    if not records:
        print(
            "No credit customers found."
        )

    for index, record in enumerate(
        records,
        start=1
    ):
        print("----------------------------------------")

        print(
            f"#{index} {record['fullname']}"
        )

        print(
            f"Customer ID    : {record['id']}"
        )

        print(
            f"Phone          : {record['phone']}"
        )

        print(
            f"Outstanding    : "
            f"₦{record['outstanding']:,.2f}"
        )

        print(
            f"Debt Age       : "
            f"{record['debt_age']} day(s)"
        )

        print(
            f"Collection     : "
            f"{record['collection_rate']:.2f}%"
        )

        print(
            f"Credit Used    : "
            f"{record['credit_used']:.2f}%"
        )

        print(
            f"Risk Score     : "
            f"{record['risk_score']}/100"
        )

        print(
            f"Action Score   : "
            f"{record['action_score']}/100"
        )

        print(
            f"Priority       : "
            f"{record['priority']}"
        )

        print(
            f"Recommended    : "
            f"{record['action']}"
        )

        print(
            f"Reason         : "
            f"{record['reason']}"
        )

        if record["upcoming_amount"] > 0:
            print(
                f"Upcoming Promise: "
                f"₦{record['upcoming_amount']:,.2f}"
            )

            print(
                f"Promise Date    : "
                f"{record['next_promise_date']}"
            )

        if record["overdue_count"] > 0:
            print(
                f"OVERDUE        : "
                f"{record['overdue_count']} "
                f"promise(s) — "
                f"₦{record['overdue_amount']:,.2f}"
            )

    print("\n========================================")
    print("       TOP COLLECTION ACTION")
    print("========================================")

    if records:
        top = records[0]

        print(
            f"Customer : {top['fullname']}"
        )

        print(
            f"Priority : {top['priority']}"
        )

        print(
            f"Action   : {top['action']}"
        )

        print(
            f"Reason   : {top['reason']}"
        )

    else:
        print(
            "No collection action required."
        )

    print("\n========================================")
    print("       MANAGEMENT SUMMARY")
    print("========================================")

    if urgent > 0:
        print(
            "STATUS : 🔴 URGENT COLLECTION ACTION"
        )
        print(
            f"• {urgent} customer(s) have overdue "
            "payment commitments."
        )

    elif high > 0:
        print(
            "STATUS : 🔴 HIGH COLLECTION ATTENTION"
        )
        print(
            f"• {high} customer(s) require active "
            "collection follow-up."
        )

    elif medium > 0:
        print(
            "STATUS : 🟡 PLANNED COLLECTION"
        )
        print(
            f"• {medium} customer(s) require "
            "scheduled follow-up."
        )

    else:
        print(
            "STATUS : 🟢 COLLECTION UNDER CONTROL"
        )

        print(
            "• No urgent collection action detected."
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
    collection_action()
