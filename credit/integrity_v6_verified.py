import sqlite3

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def validate_credit_integrity(conn=None):
    """
    Validate that every customer credit's recorded payment
    agrees with normal payment history plus historical reconciliation.
    """

    own_connection = conn is None

    if own_connection:
        conn = get_connection()

    cur = conn.cursor()

    credits = cur.execute("""
        SELECT
            id,
            total_amount,
            amount_paid,
            balance,
            status
        FROM customer_credit
        ORDER BY id
    """).fetchall()

    errors = []

    for credit in credits:
        credit_id = credit["id"]

        total_amount = float(credit["total_amount"] or 0)
        recorded_paid = float(credit["amount_paid"] or 0)
        balance = float(credit["balance"] or 0)

        normal_payments = float(
            cur.execute("""
                SELECT COALESCE(SUM(amount), 0)
                FROM credit_payments
                WHERE credit_id = ?
            """, (credit_id,)).fetchone()[0]
            or 0
        )

        historical_payments = float(
            cur.execute("""
                SELECT COALESCE(SUM(amount), 0)
                FROM credit_reconciliations
                WHERE credit_id = ?
            """, (credit_id,)).fetchone()[0]
            or 0
        )

        expected_paid = normal_payments + historical_payments
        expected_balance = total_amount - expected_paid

        # Payment cannot be negative.
        if recorded_paid < -0.000001:
            errors.append(
                f"Credit #{credit_id}: negative recorded payment."
            )

        # Balance cannot be negative.
        if balance < -0.000001:
            errors.append(
                f"Credit #{credit_id}: negative balance."
            )

        # Recorded payment must agree with history.
        if abs(recorded_paid - expected_paid) > 0.000001:
            errors.append(
                f"Credit #{credit_id}: payment mismatch. "
                f"Recorded={recorded_paid:.2f}, "
                f"History={expected_paid:.2f}."
            )

        # Balance must agree with original amount minus payments.
        if abs(balance - expected_balance) > 0.000001:
            errors.append(
                f"Credit #{credit_id}: balance mismatch. "
                f"Recorded={balance:.2f}, "
                f"Expected={expected_balance:.2f}."
            )

        # Payment cannot exceed original credit.
        if recorded_paid - total_amount > 0.000001:
            errors.append(
                f"Credit #{credit_id}: payment exceeds original credit."
            )

        # Validate status.
        if abs(balance) <= 0.000001:
            expected_status = "PAID"
        elif recorded_paid > 0:
            expected_status = "PARTLY PAID"
        else:
            expected_status = "UNPAID"

        if credit["status"] != expected_status:
            errors.append(
                f"Credit #{credit_id}: status mismatch. "
                f"Recorded={credit['status']}, "
                f"Expected={expected_status}."
            )

    if own_connection:
        conn.close()

    return len(errors) == 0, errors


def assert_credit_integrity(conn):
    """
    Raise an exception if credit accounting is inconsistent.
    """

    valid, errors = validate_credit_integrity(conn)

    if not valid:
        message = "Credit integrity check failed:\n"
        message += "\n".join(
            f"- {error}"
            for error in errors
        )
        raise RuntimeError(message)

    return True


if __name__ == "__main__":
    conn = get_connection()

    valid, errors = validate_credit_integrity(conn)

    print("\n========================================")
    print("       CREDIT INTEGRITY VALIDATOR")
    print("========================================")

    if valid:
        print("✅ CREDIT INTEGRITY PASSED")
    else:
        print("❌ CREDIT INTEGRITY FAILED")

        for error in errors:
            print(f"- {error}")

    print("========================================")

    conn.close()
