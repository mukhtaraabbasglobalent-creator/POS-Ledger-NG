import sqlite3
from datetime import datetime

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def create_outcome_table():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS collection_outcomes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            followup_id INTEGER NOT NULL,
            customer_id INTEGER NOT NULL,
            credit_id INTEGER NOT NULL,
            promised_amount REAL NOT NULL,
            matched_amount REAL NOT NULL DEFAULT 0,
            outcome TEXT NOT NULL,
            outcome_date TEXT NOT NULL,
            staff_name TEXT,
            notes TEXT,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def record_collection_outcome(
    followup_id,
    outcome,
    matched_amount=0,
    staff_name="System",
    notes=""
):
    create_outcome_table()

    conn = get_connection()
    cur = conn.cursor()

    followup = cur.execute(
        """
        SELECT *
        FROM collection_followups
        WHERE id = ?
        LIMIT 1
        """,
        (followup_id,)
    ).fetchone()

    if not followup:
        conn.close()
        raise ValueError("Follow-up record not found.")

    promised_amount = float(
        followup["promised_amount"] or 0
    )

    matched_amount = float(matched_amount or 0)

    if matched_amount < 0:
        conn.close()
        raise ValueError("Matched amount cannot be negative.")

    if matched_amount > promised_amount:
        matched_amount = promised_amount

    valid_outcomes = {
        "FULFILLED",
        "PARTIALLY FULFILLED",
        "MISSED",
        "CANCELLED"
    }

    outcome = outcome.strip().upper()

    if outcome not in valid_outcomes:
        conn.close()
        raise ValueError(
            "Invalid outcome. Use: "
            "FULFILLED, PARTIALLY FULFILLED, "
            "MISSED, or CANCELLED."
        )

    if outcome == "FULFILLED":
        matched_amount = promised_amount

    if outcome == "MISSED":
        matched_amount = 0

    now = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    cur.execute(
        """
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
        """,
        (
            followup["id"],
            followup["customer_id"],
            followup["credit_id"],
            promised_amount,
            matched_amount,
            outcome,
            now,
            staff_name,
            notes,
            now
        )
    )

    conn.commit()
    conn.close()


def collection_outcome_report(customer_id=None):
    create_outcome_table()

    conn = get_connection()
    cur = conn.cursor()

    if customer_id is None:
        rows = cur.execute(
            """
            SELECT *
            FROM collection_outcomes
            ORDER BY outcome_date DESC, id DESC
            """
        ).fetchall()
    else:
        rows = cur.execute(
            """
            SELECT *
            FROM collection_outcomes
            WHERE customer_id = ?
            ORDER BY outcome_date DESC, id DESC
            """,
            (customer_id,)
        ).fetchall()

    print("\n========================================")
    print("       POS LEDGER NG V18")
    print("    COLLECTION OUTCOME TRACKING")
    print("========================================")

    if not rows:
        print("\nNo collection outcomes recorded.")
        conn.close()
        input("\nPress Enter to continue...")
        return

    total_promised = 0
    total_matched = 0

    counts = {
        "FULFILLED": 0,
        "PARTIALLY FULFILLED": 0,
        "MISSED": 0,
        "CANCELLED": 0
    }

    for index, row in enumerate(rows, 1):
        total_promised += float(
            row["promised_amount"] or 0
        )

        total_matched += float(
            row["matched_amount"] or 0
        )

        outcome = row["outcome"]

        if outcome in counts:
            counts[outcome] += 1

        print("----------------------------------------")
        print(f"Outcome #{index}")
        print(f"Customer ID     : {row['customer_id']}")
        print(f"Credit ID       : {row['credit_id']}")
        print(f"Follow-up ID    : {row['followup_id']}")
        print(
            f"Promised Amount : "
            f"₦{float(row['promised_amount'] or 0):,.2f}"
        )
        print(
            f"Matched Amount  : "
            f"₦{float(row['matched_amount'] or 0):,.2f}"
        )
        print(f"Outcome         : {row['outcome']}")
        print(f"Date            : {row['outcome_date']}")
        print(f"Staff           : {row['staff_name']}")
        print(f"Notes           : {row['notes']}")

    fulfillment_rate = (
        total_matched / total_promised * 100
        if total_promised > 0 else 0
    )

    print("\n========================================")
    print("       OUTCOME SUMMARY")
    print("========================================")

    print(
        f"Total Promised : "
        f"₦{total_promised:,.2f}"
    )

    print(
        f"Total Matched  : "
        f"₦{total_matched:,.2f}"
    )

    print(
        f"Fulfillment    : "
        f"{fulfillment_rate:.2f}%"
    )

    print("----------------------------------------")
    print(f"Fulfilled           : {counts['FULFILLED']}")
    print(
        f"Partially Fulfilled : "
        f"{counts['PARTIALLY FULFILLED']}"
    )
    print(f"Missed              : {counts['MISSED']}")
    print(f"Cancelled           : {counts['CANCELLED']}")

    print("----------------------------------------")

    if counts["MISSED"] > 0:
        status = "🔴 PROMISE PERFORMANCE NEEDS ATTENTION"
    elif counts["PARTIALLY FULFILLED"] > 0:
        status = "🟠 PARTIAL COLLECTION PERFORMANCE"
    elif counts["FULFILLED"] > 0:
        status = "🟢 POSITIVE COLLECTION PERFORMANCE"
    else:
        status = "🟡 OUTCOME DATA DEVELOPING"

    print(f"STATUS : {status}")

    print("----------------------------------------")
    print(
        "READ-ONLY: Credit/payment financial "
        "records were NOT modified."
    )
    print("========================================")

    conn.close()

    input("\nPress Enter to continue...")


if __name__ == "__main__":
    create_outcome_table()
    print("Collection Outcome V18 table ready.")
