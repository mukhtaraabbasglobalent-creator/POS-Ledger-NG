import sqlite3
from datetime import datetime

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def calculate_priority(
    outstanding,
    debt_age,
    collection_rate,
    credit_used,
    active_promised,
    overdue_promised,
    risk_score,
    followups,
):
    score = 0
    reasons = []

    # Outstanding balance
    if outstanding >= 50000:
        score += 30
        reasons.append(
            f"Very high outstanding balance (₦{outstanding:,.2f})"
        )
    elif outstanding >= 20000:
        score += 25
        reasons.append(
            f"High outstanding balance (₦{outstanding:,.2f})"
        )
    elif outstanding >= 10000:
        score += 18
        reasons.append(
            f"Significant outstanding balance (₦{outstanding:,.2f})"
        )
    elif outstanding >= 5000:
        score += 12
        reasons.append(
            f"Outstanding balance (₦{outstanding:,.2f})"
        )
    elif outstanding > 0:
        score += 6
        reasons.append(
            f"Outstanding balance (₦{outstanding:,.2f})"
        )

    # Debt age
    if debt_age >= 30:
        score += 25
        reasons.append(f"Debt is {debt_age} days old")
    elif debt_age >= 14:
        score += 18
        reasons.append(f"Debt is {debt_age} days old")
    elif debt_age >= 7:
        score += 10
        reasons.append(f"Debt is {debt_age} days old")
    elif debt_age >= 3:
        score += 5
        reasons.append(f"Debt is {debt_age} days old")

    # Collection rate
    if collection_rate < 25:
        score += 20
        reasons.append(
            f"Very low collection rate ({collection_rate:.2f}%)"
        )
    elif collection_rate < 50:
        score += 12
        reasons.append(
            f"Collection rate needs attention ({collection_rate:.2f}%)"
        )
    elif collection_rate < 75:
        score += 5
        reasons.append(
            f"Moderate collection rate ({collection_rate:.2f}%)"
        )

    # Credit utilization
    if credit_used >= 80:
        score += 15
        reasons.append(
            f"Very high credit utilization ({credit_used:.2f}%)"
        )
    elif credit_used >= 60:
        score += 10
        reasons.append(
            f"High credit utilization ({credit_used:.2f}%)"
        )
    elif credit_used >= 40:
        score += 6
        reasons.append(
            f"Moderate credit utilization ({credit_used:.2f}%)"
        )

    # Overdue promises
    if overdue_promised > 0:
        score += 20
        reasons.append(
            f"{overdue_promised} overdue promise(s)"
        )

    # Active promises
    if active_promised > 0:
        score += 3
        reasons.append(
            f"₦{active_promised:,.2f} currently promised"
        )

    # Risk score
    if risk_score >= 75:
        score += 20
        reasons.append(
            f"Critical credit risk ({risk_score}/100)"
        )
    elif risk_score >= 50:
        score += 15
        reasons.append(
            f"High credit risk ({risk_score}/100)"
        )
    elif risk_score >= 25:
        score += 8
        reasons.append(
            f"Moderate credit risk ({risk_score}/100)"
        )

    # Follow-up history
    if followups == 0 and outstanding > 0:
        score += 5
        reasons.append(
            "No collection follow-up recorded"
        )

    score = max(0, min(100, score))

    if score >= 60:
        priority = "🔴 HIGH"
        action = "CONTACT CUSTOMER / ESCALATE"
    elif score >= 30:
        priority = "🟡 MEDIUM"
        action = "SCHEDULE COLLECTION FOLLOW-UP"
    else:
        priority = "🟢 LOW"
        action = "NORMAL MONITORING"

    return score, priority, action, reasons


def get_risk_score(cur, customer_id):
    customer = cur.execute("""
        SELECT credit_limit
        FROM customers
        WHERE id = ?
    """, (customer_id,)).fetchone()

    if not customer:
        return 0

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

    total_credit = float(credit["total_credit"] or 0)
    total_paid = float(credit["total_paid"] or 0)
    outstanding = float(credit["outstanding"] or 0)
    credit_limit = float(customer["credit_limit"] or 0)

    collection_rate = (
        total_paid / total_credit * 100
        if total_credit > 0
        else 0
    )

    utilization = (
        outstanding / credit_limit * 100
        if credit_limit > 0
        else 0
    )

    score = 0

    if utilization >= 80:
        score += 30
    elif utilization >= 60:
        score += 20
    elif utilization >= 40:
        score += 10
    elif utilization >= 20:
        score += 5

    if collection_rate < 25:
        score += 25
    elif collection_rate < 50:
        score += 15
    elif collection_rate < 75:
        score += 5

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

    return max(0, min(100, score))


def get_customer_priority(cur, customer_id):
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

    # IMPORTANT:
    # Existing schema uses created_date,
    # NOT created_at.
    credit = cur.execute("""
        SELECT
            COALESCE(SUM(total_amount), 0) AS total_credit,
            COALESCE(SUM(amount_paid), 0) AS total_paid,
            COALESCE(SUM(balance), 0) AS outstanding,
            MIN(created_date) AS oldest_date
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
        return None

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

    # Follow-ups
    followup_row = cur.execute("""
        SELECT
            COUNT(*) AS total_followups,
            COALESCE(
                SUM(promised_amount),
                0
            ) AS promised
        FROM collection_followups
        WHERE customer_id = ?
    """, (customer_id,)).fetchone()

    followups = int(
        followup_row["total_followups"] or 0
    )

    # Active promises
    today = datetime.now().strftime(
        "%Y-%m-%d"
    )

    active_row = cur.execute("""
        SELECT
            COALESCE(
                SUM(promised_amount),
                0
            ) AS amount
        FROM collection_followups
        WHERE customer_id = ?
        AND status = 'PROMISE'
        AND promised_date >= ?
    """, (
        customer_id,
        today
    )).fetchone()

    active_promised = float(
        active_row["amount"] or 0
    )

    # Overdue promises
    overdue_row = cur.execute("""
        SELECT
            COUNT(*) AS count
        FROM collection_followups
        WHERE customer_id = ?
        AND status = 'PROMISE'
        AND promised_date < ?
    """, (
        customer_id,
        today
    )).fetchone()

    overdue_promised = int(
        overdue_row["count"] or 0
    )

    risk_score = get_risk_score(
        cur,
        customer_id
    )

    score, priority, action, reasons = (
        calculate_priority(
            outstanding,
            debt_age,
            collection_rate,
            credit_used,
            active_promised,
            overdue_promised,
            risk_score,
            followups,
        )
    )

    return {
        "id": customer["id"],
        "fullname": customer["fullname"],
        "phone": customer["phone"],
        "outstanding": outstanding,
        "total_credit": total_credit,
        "total_paid": total_paid,
        "collection_rate": collection_rate,
        "credit_used": credit_used,
        "debt_age": debt_age,
        "active_promised": active_promised,
        "overdue_promised": overdue_promised,
        "risk_score": risk_score,
        "followups": followups,
        "priority_score": score,
        "priority": priority,
        "action": action,
        "reasons": reasons,
    }


def collection_priority():
    conn = get_connection()
    cur = conn.cursor()

    customers = cur.execute("""
        SELECT id
        FROM customers
        ORDER BY id
    """).fetchall()

    records = []

    for customer in customers:
        result = get_customer_priority(
            cur,
            customer["id"]
        )

        if result:
            records.append(result)

    records.sort(
        key=lambda r: (
            -r["priority_score"],
            -r["outstanding"]
        )
    )

    print("\n========================================")
    print("       POS LEDGER NG V23")
    print("     COLLECTION PRIORITY ENGINE")
    print("========================================")

    print("\n========================================")
    print("        COLLECTION POSITION")
    print("========================================")

    total_credit = sum(
        r["total_credit"]
        for r in records
    )

    total_paid = sum(
        r["total_paid"]
        for r in records
    )

    outstanding = sum(
        r["outstanding"]
        for r in records
    )

    collection_rate = (
        total_paid / total_credit * 100
        if total_credit > 0
        else 0
    )

    print(
        f"Customers With Credit : {len(records)}"
    )

    print(
        f"Credit Issued         : ₦{total_credit:,.2f}"
    )

    print(
        f"Collected             : ₦{total_paid:,.2f}"
    )

    print(
        f"Outstanding           : ₦{outstanding:,.2f}"
    )

    print(
        f"Collection Rate       : {collection_rate:.2f}%"
    )

    print("\n========================================")
    print("       COLLECTION PRIORITY")
    print("========================================")

    if not records:
        print("No customer credit accounts found.")

    for index, customer in enumerate(
        records,
        start=1
    ):
        print("----------------------------------------")

        print(
            f"#{index} {customer['fullname']}"
        )

        print(
            f"Customer ID    : {customer['id']}"
        )

        print(
            f"Phone          : {customer['phone']}"
        )

        print(
            f"Outstanding    : ₦{customer['outstanding']:,.2f}"
        )

        print(
            f"Debt Age       : {customer['debt_age']} day(s)"
        )

        print(
            f"Collection     : {customer['collection_rate']:.2f}%"
        )

        print(
            f"Credit Used    : {customer['credit_used']:.2f}%"
        )

        print(
            f"Active Promise : ₦{customer['active_promised']:,.2f}"
        )

        print(
            f"Overdue Promise: {customer['overdue_promised']}"
        )

        print(
            f"Risk Score     : {customer['risk_score']}/100"
        )

        print(
            f"Priority Score : {customer['priority_score']}/100"
        )

        print(
            f"Priority       : {customer['priority']}"
        )

        print(
            f"Recommended    : {customer['action']}"
        )

        print("\nWHY:")

        if customer["reasons"]:
            for reason in customer["reasons"]:
                print(f"• {reason}")
        else:
            print("• No priority risk factors.")

    print("\n========================================")
    print("       MANAGEMENT ACTION PLAN")
    print("========================================")

    high_priority = [
        r for r in records
        if r["priority_score"] >= 60
    ]

    medium_priority = [
        r for r in records
        if 30 <= r["priority_score"] < 60
    ]

    if high_priority:
        print(
            "STATUS : 🔴 IMMEDIATE COLLECTION"
        )

        print(
            f"• {len(high_priority)} "
            "customer(s) require immediate attention."
        )

    elif medium_priority:
        print(
            "STATUS : 🟡 COLLECTION FOLLOW-UP"
        )

        print(
            f"• {len(medium_priority)} "
            "customer(s) should be contacted."
        )

    else:
        print(
            "STATUS : 🟢 NORMAL COLLECTION"
        )

        print(
            "• No urgent collection action "
            "is currently required."
        )

    if records:
        top = records[0]

        print(
            f"• Top priority: {top['fullname']} — "
            f"₦{top['outstanding']:,.2f}"
        )

        print(
            f"• Recommended action: {top['action']}"
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
    collection_priority()
