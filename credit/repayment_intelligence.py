import sqlite3
from datetime import datetime

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def repayment_intelligence(customer_id=None):
    conn = get_connection()
    cur = conn.cursor()

    if customer_id is None:
        customers = cur.execute("""
            SELECT id, fullname, phone, credit_limit
            FROM customers
            ORDER BY id
        """).fetchall()
    else:
        customers = cur.execute("""
            SELECT id, fullname, phone, credit_limit
            FROM customers
            WHERE id = ?
        """, (customer_id,)).fetchall()

    print("\n========================================")
    print("       POS LEDGER NG V19")
    print(" REPAYMENT BEHAVIOR INTELLIGENCE")
    print("========================================")

    if not customers:
        print("\nNo customer found.")
        conn.close()
        input("\nPress Enter to continue...")
        return

    for customer in customers:

        cid = customer["id"]

        credits = cur.execute("""
            SELECT
                COALESCE(SUM(total_amount), 0) AS total_credit,
                COALESCE(SUM(amount_paid), 0) AS total_paid,
                COALESCE(SUM(balance), 0) AS outstanding,
                COUNT(*) AS credit_accounts
            FROM customer_credit
            WHERE customer_id = ?
        """, (cid,)).fetchone()

        followups = cur.execute("""
            SELECT
                COUNT(*) AS total_followups,
                COALESCE(SUM(promised_amount), 0) AS total_promised
            FROM collection_followups
            WHERE customer_id = ?
        """, (cid,)).fetchone()

        outcomes = cur.execute("""
            SELECT
                COUNT(*) AS total_outcomes,
                SUM(
                    CASE
                        WHEN outcome = 'FULFILLED'
                        THEN 1 ELSE 0
                    END
                ) AS fulfilled,
                SUM(
                    CASE
                        WHEN outcome = 'PARTIALLY FULFILLED'
                        THEN 1 ELSE 0
                    END
                ) AS partial,
                SUM(
                    CASE
                        WHEN outcome = 'MISSED'
                        THEN 1 ELSE 0
                    END
                ) AS missed,
                SUM(
                    CASE
                        WHEN outcome = 'CANCELLED'
                        THEN 1 ELSE 0
                    END
                ) AS cancelled,
                COALESCE(SUM(promised_amount), 0)
                    AS outcome_promised,
                COALESCE(SUM(matched_amount), 0)
                    AS outcome_matched
            FROM collection_outcomes
            WHERE customer_id = ?
        """, (cid,)).fetchone()

        total_credit = float(credits["total_credit"] or 0)
        total_paid = float(credits["total_paid"] or 0)
        outstanding = float(credits["outstanding"] or 0)

        credit_accounts = int(
            credits["credit_accounts"] or 0
        )

        total_followups = int(
            followups["total_followups"] or 0
        )

        total_promised = float(
            followups["total_promised"] or 0
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

        cancelled = int(
            outcomes["cancelled"] or 0
        )

        outcome_promised = float(
            outcomes["outcome_promised"] or 0
        )

        outcome_matched = float(
            outcomes["outcome_matched"] or 0
        )

        collection_rate = (
            total_paid / total_credit * 100
            if total_credit > 0 else 0
        )

        promise_fulfillment_rate = (
            outcome_matched /
            outcome_promised * 100
            if outcome_promised > 0 else 0
        )

        promise_success_rate = (
            fulfilled /
            total_outcomes * 100
            if total_outcomes > 0 else 0
        )

        credit_limit = float(
            customer["credit_limit"] or 0
        )

        credit_used = (
            outstanding /
            credit_limit * 100
            if credit_limit > 0 else 0
        )

        print("\n========================================")
        print("       CUSTOMER REPAYMENT PROFILE")
        print("========================================")
        print(f"Customer ID   : {cid}")
        print(f"Customer Name : {customer['fullname']}")
        print(f"Phone         : {customer['phone']}")
        print("----------------------------------------")

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
            f"Collection Rate  : "
            f"{collection_rate:.2f}%"
        )

        print(
            f"Credit Accounts  : "
            f"{credit_accounts}"
        )

        print(
            f"Credit Used      : "
            f"{credit_used:.2f}%"
        )

        print("\n========================================")
        print("       FOLLOW-UP BEHAVIOR")
        print("========================================")

        print(
            f"Follow-ups       : "
            f"{total_followups}"
        )

        print(
            f"Promises Recorded: "
            f"₦{total_promised:,.2f}"
        )

        print("\n========================================")
        print("       PROMISE OUTCOMES")
        print("========================================")

        print(
            f"Outcome Records  : "
            f"{total_outcomes}"
        )

        print(
            f"Fulfilled        : "
            f"{fulfilled}"
        )

        print(
            f"Partially Filled : "
            f"{partial}"
        )

        print(
            f"Missed           : "
            f"{missed}"
        )

        print(
            f"Cancelled        : "
            f"{cancelled}"
        )

        print(
            f"Outcome Promised : "
            f"₦{outcome_promised:,.2f}"
        )

        print(
            f"Outcome Matched  : "
            f"₦{outcome_matched:,.2f}"
        )

        print(
            f"Fulfillment Rate : "
            f"{promise_fulfillment_rate:.2f}%"
        )

        print("\n========================================")
        print("       REPAYMENT BEHAVIOR")
        print("========================================")

        if total_outcomes == 0:
            behavior = "🟡 INSUFFICIENT OUTCOME DATA"
        elif missed > 0 and promise_success_rate < 50:
            behavior = "🔴 HIGH REPAYMENT RISK"
        elif partial > 0:
            behavior = "🟠 INCONSISTENT REPAYMENT"
        elif promise_success_rate >= 80:
            behavior = "🟢 RELIABLE REPAYMENT"
        else:
            behavior = "🟡 DEVELOPING REPAYMENT HISTORY"

        print(f"Behavior Status : {behavior}")

        print("\n========================================")
        print("       CREDIT DECISION SUPPORT")
        print("========================================")

        if outstanding <= 0:
            recommendation = "CUSTOMER CLEAR — NORMAL CREDIT REVIEW"

        elif missed > 0:
            recommendation = "REVIEW BEFORE ADDITIONAL CREDIT"

        elif partial > 0:
            recommendation = "MONITOR REPAYMENT BEFORE INCREASING CREDIT"

        elif total_outcomes == 0:
            recommendation = "MONITOR — INSUFFICIENT REPAYMENT HISTORY"

        elif promise_success_rate >= 80:
            recommendation = "POSITIVE REPAYMENT HISTORY"

        else:
            recommendation = "CONTINUE NORMAL COLLECTION MONITORING"

        print(f"Recommendation : {recommendation}")

        print("\n========================================")
        print("       MANAGEMENT SUMMARY")
        print("========================================")

        print(
            f"• ₦{outstanding:,.2f} remains outstanding."
        )

        print(
            f"• Collection rate is "
            f"{collection_rate:.2f}%."
        )

        print(
            f"• {total_followups} collection "
            f"follow-up(s) recorded."
        )

        print(
            f"• {total_outcomes} promise "
            f"outcome(s) recorded."
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
    repayment_intelligence()
