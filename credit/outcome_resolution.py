import sqlite3
from datetime import datetime


DB_NAME = "data/posledger.db"


VALID_OUTCOMES = {
    "1": "FULFILLED",
    "2": "PARTIALLY FULFILLED",
    "3": "MISSED",
    "4": "CANCELLED",
}


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def get_customer(cur, customer_id):
    return cur.execute("""
        SELECT
            id,
            fullname,
            phone,
            credit_limit
        FROM customers
        WHERE id = ?
    """, (customer_id,)).fetchone()


def get_followups(cur, customer_id):
    return cur.execute("""
        SELECT
            id,
            customer_id,
            credit_id,
            staff_name,
            contact_date,
            contact_method,
            promised_amount,
            promised_date,
            status,
            notes
        FROM collection_followups
        WHERE customer_id = ?
        ORDER BY id ASC
    """, (customer_id,)).fetchall()


def get_existing_outcome(cur, followup_id):
    return cur.execute("""
        SELECT
            id,
            followup_id,
            customer_id,
            credit_id,
            promised_amount,
            matched_amount,
            outcome,
            outcome_date,
            staff_name,
            notes
        FROM collection_outcomes
        WHERE followup_id = ?
        LIMIT 1
    """, (followup_id,)).fetchone()


def record_collection_outcome(
    customer_id,
    followup_id,
    outcome,
    matched_amount,
    outcome_date=None,
    staff_name=None,
    notes=None,
):
    conn = get_connection()
    cur = conn.cursor()

    try:
        # ----------------------------------------
        # VALIDATE CUSTOMER
        # ----------------------------------------
        customer = get_customer(
            cur,
            customer_id
        )

        if not customer:
            print(
                f"Customer ID {customer_id} "
                "was not found."
            )
            return False

        # ----------------------------------------
        # VALIDATE FOLLOW-UP
        # ----------------------------------------
        followup = cur.execute("""
            SELECT
                id,
                customer_id,
                credit_id,
                staff_name,
                promised_amount,
                promised_date,
                status
            FROM collection_followups
            WHERE id = ?
            AND customer_id = ?
        """, (
            followup_id,
            customer_id,
        )).fetchone()

        if not followup:
            print(
                "The selected follow-up does not "
                "belong to this customer."
            )
            return False

        # ----------------------------------------
        # PREVENT DUPLICATE OUTCOME
        # ----------------------------------------
        existing = get_existing_outcome(
            cur,
            followup_id
        )

        if existing:
            print(
                "An outcome has already been recorded "
                "for this follow-up."
            )

            print(
                f"Existing Outcome : "
                f"{existing['outcome']}"
            )

            print(
                f"Matched Amount   : "
                f"₦{float(existing['matched_amount'] or 0):,.2f}"
            )

            return False

        # ----------------------------------------
        # NORMALIZE OUTCOME
        # ----------------------------------------
        outcome = (
            outcome or ""
        ).strip().upper()

        allowed = {
            "FULFILLED",
            "PARTIALLY FULFILLED",
            "PARTIALLY FILLED",
            "MISSED",
            "CANCELLED",
        }

        if outcome == "PARTIALLY FILLED":
            outcome = "PARTIALLY FULFILLED"

        if outcome not in allowed:
            print(
                "Invalid outcome."
            )
            return False

        # ----------------------------------------
        # VALIDATE AMOUNT
        # ----------------------------------------
        try:
            matched_amount = float(
                matched_amount
            )
        except (
            ValueError,
            TypeError,
        ):
            print(
                "Matched amount must be numeric."
            )
            return False

        if matched_amount < 0:
            print(
                "Matched amount cannot be negative."
            )
            return False

        promised_amount = float(
            followup["promised_amount"] or 0
        )

        # ----------------------------------------
        # OUTCOME-SPECIFIC VALIDATION
        # ----------------------------------------
        if outcome == "FULFILLED":
            if matched_amount < promised_amount:
                print(
                    "A FULFILLED outcome requires "
                    "matched amount to cover the "
                    "promised amount."
                )
                return False

        elif outcome == "PARTIALLY FULFILLED":
            if matched_amount <= 0:
                print(
                    "A PARTIALLY FULFILLED outcome "
                    "requires a positive matched amount."
                )
                return False

            if matched_amount >= promised_amount:
                print(
                    "Use FULFILLED when the full "
                    "promised amount was matched."
                )
                return False

        elif outcome in (
            "MISSED",
            "CANCELLED",
        ):
            if matched_amount != 0:
                print(
                    f"{outcome} outcome must have "
                    "matched amount of ₦0.00."
                )
                return False

        # ----------------------------------------
        # DATE
        # ----------------------------------------
        if outcome_date is None:
            outcome_date = datetime.now().strftime(
                "%Y-%m-%d"
            )

        try:
            datetime.strptime(
                outcome_date,
                "%Y-%m-%d"
            )
        except ValueError:
            print(
                "Invalid outcome date. "
                "Use YYYY-MM-DD."
            )
            return False

        # ----------------------------------------
        # STAFF
        # ----------------------------------------
        if not staff_name:
            staff_name = (
                followup["staff_name"]
                or "System"
            )

        # ----------------------------------------
        # NOTES
        # ----------------------------------------
        notes = (
            notes.strip()
            if isinstance(notes, str)
            else None
        )

        # ----------------------------------------
        # INSERT ONLY OUTCOME RECORD
        # ----------------------------------------
        cur.execute("""
            INSERT INTO collection_outcomes (
                followup_id,
                customer_id,
                credit_id,
                promised_amount,
                matched_amount,
                outcome,
                outcome_date,
                staff_name,
                notes,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            followup_id,
            customer_id,
            followup["credit_id"],
            promised_amount,
            matched_amount,
            outcome,
            outcome_date,
            staff_name,
            notes,
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        ))

        conn.commit()

        print("\n========================================")
        print("       COLLECTION OUTCOME SAVED")
        print("========================================")

        print(
            f"Customer       : "
            f"{customer['fullname']}"
        )

        print(
            f"Follow-up ID   : "
            f"{followup_id}"
        )

        print(
            f"Promised       : "
            f"₦{promised_amount:,.2f}"
        )

        print(
            f"Matched        : "
            f"₦{matched_amount:,.2f}"
        )

        print(
            f"Outcome        : "
            f"{outcome}"
        )

        print(
            f"Outcome Date   : "
            f"{outcome_date}"
        )

        print(
            f"Staff          : "
            f"{staff_name}"
        )

        print("----------------------------------------")
        print(
            "Credit/payment records were NOT modified."
        )
        print(
            "Only the collection outcome was recorded."
        )
        print("========================================")

        return True

    except sqlite3.Error as error:
        conn.rollback()

        print(
            f"Database error: {error}"
        )

        return False

    finally:
        conn.close()


def outcome_resolution():
    print("\n========================================")
    print("       POS LEDGER NG V26")
    print("    COLLECTION OUTCOME RESOLUTION")
    print("========================================")

    try:
        customer_id = int(
            input("Customer ID: ").strip()
        )
    except ValueError:
        print(
            "Invalid Customer ID."
        )
        return

    conn = get_connection()
    cur = conn.cursor()

    customer = get_customer(
        cur,
        customer_id
    )

    if not customer:
        print(
            f"Customer ID {customer_id} "
            "was not found."
        )
        conn.close()
        return

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

    followups = get_followups(
        cur,
        customer_id
    )

    if not followups:
        print("\nNo collection follow-ups found.")
        conn.close()
        return

    print("\n========================================")
    print("       COLLECTION FOLLOW-UPS")
    print("========================================")

    available = []

    for row in followups:
        existing = get_existing_outcome(
            cur,
            row["id"]
        )

        print("----------------------------------------")

        print(
            f"Follow-up ID : {row['id']}"
        )

        print(
            f"Credit ID    : "
            f"{row['credit_id']}"
        )

        print(
            f"Staff        : "
            f"{row['staff_name'] or 'UNKNOWN'}"
        )

        print(
            f"Contact Date : "
            f"{row['contact_date']}"
        )

        print(
            f"Promised     : "
            f"₦{float(row['promised_amount'] or 0):,.2f}"
        )

        print(
            f"Promise Date : "
            f"{row['promised_date'] or 'N/A'}"
        )

        print(
            f"Status       : "
            f"{row['status']}"
        )

        if existing:
            print(
                f"Outcome      : "
                f"{existing['outcome']}"
            )
        else:
            print(
                "Outcome      : NOT RECORDED"
            )

            available.append(row)

    conn.close()

    if not available:
        print("\n========================================")
        print("        NO PENDING OUTCOMES")
        print("========================================")
        print(
            "Every follow-up already has an "
            "outcome recorded."
        )
        return

    print("\n========================================")
    print("       RECORD NEW OUTCOME")
    print("========================================")

    try:
        followup_id = int(
            input("Follow-up ID: ").strip()
        )
    except ValueError:
        print(
            "Invalid Follow-up ID."
        )
        return

    selected = None

    for row in available:
        if row["id"] == followup_id:
            selected = row
            break

    if not selected:
        print(
            "That follow-up is not available "
            "for a new outcome."
        )
        return

    print("\nOutcome:")
    print("1. FULFILLED")
    print("2. PARTIALLY FULFILLED")
    print("3. MISSED")
    print("4. CANCELLED")

    choice = input(
        "Select outcome: "
    ).strip()

    outcome = VALID_OUTCOMES.get(
        choice
    )

    if not outcome:
        print(
            "Invalid outcome selection."
        )
        return

    try:
        matched_amount = float(
            input(
                "Matched amount: ₦"
            ).strip()
        )
    except ValueError:
        print(
            "Invalid matched amount."
        )
        return

    outcome_date = input(
        "Outcome date "
        "(YYYY-MM-DD, Enter=today): "
    ).strip()

    if not outcome_date:
        outcome_date = datetime.now().strftime(
            "%Y-%m-%d"
        )

    staff_name = input(
        "Staff name "
        f"(Enter={selected['staff_name'] or 'System'}): "
    ).strip()

    if not staff_name:
        staff_name = (
            selected["staff_name"]
            or "System"
        )

    notes = input(
        "Notes (optional): "
    ).strip()

    # ----------------------------------------
    # CONFIRM BEFORE WRITE
    # ----------------------------------------
    print("\n========================================")
    print("       CONFIRM OUTCOME")
    print("========================================")

    print(
        f"Customer       : "
        f"{customer_id}"
    )

    print(
        f"Follow-up ID   : "
        f"{followup_id}"
    )

    print(
        f"Promised       : "
        f"₦{float(selected['promised_amount'] or 0):,.2f}"
    )

    print(
        f"Matched        : "
        f"₦{matched_amount:,.2f}"
    )

    print(
        f"Outcome        : "
        f"{outcome}"
    )

    print(
        f"Date           : "
        f"{outcome_date}"
    )

    print(
        f"Staff          : "
        f"{staff_name}"
    )

    confirm = input(
        "\nSave this collection outcome? "
        "(y/n): "
    ).strip().lower()

    if confirm != "y":
        print(
            "Operation cancelled."
        )
        return

    record_collection_outcome(
        customer_id=customer_id,
        followup_id=followup_id,
        outcome=outcome,
        matched_amount=matched_amount,
        outcome_date=outcome_date,
        staff_name=staff_name,
        notes=notes,
    )


if __name__ == "__main__":
    outcome_resolution()
