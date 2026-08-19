import sqlite3
from datetime import datetime

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def show_followup_history():
    conn = get_connection()
    cur = conn.cursor()

    print("\n========================================")
    print("       POS LEDGER NG V11.1")
    print("       FOLLOW-UP HISTORY")
    print("========================================")

    customer_input = input(
        "\nEnter Customer ID or Name: "
    ).strip()

    if not customer_input:
        print("\n❌ Customer is required.")
        conn.close()
        input("\nPress Enter to continue...")
        return

    # ------------------------------------
    # FIND CUSTOMER
    # ------------------------------------
    if customer_input.isdigit():

        cur.execute("""
            SELECT *
            FROM customers
            WHERE id = ?
        """, (int(customer_input),))

    else:

        cur.execute("""
            SELECT *
            FROM customers
            WHERE LOWER(fullname) LIKE LOWER(?)
            ORDER BY id
            LIMIT 1
        """, (f"%{customer_input}%",))

    customer = cur.fetchone()

    if not customer:
        print("\n❌ Customer not found.")
        conn.close()
        input("\nPress Enter to continue...")
        return

    customer_id = customer["id"]

    # ------------------------------------
    # CUSTOMER INFORMATION
    # ------------------------------------
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
        f"Phone         : "
        f"{customer['phone'] or 'N/A'}"
    )

    # ------------------------------------
    # OUTSTANDING BALANCE
    # ------------------------------------
    cur.execute("""
        SELECT
            COALESCE(SUM(balance), 0) AS outstanding
        FROM customer_credit
        WHERE customer_id = ?
          AND balance > 0
    """, (customer_id,))

    outstanding = float(
        cur.fetchone()["outstanding"] or 0
    )

    print(
        f"Outstanding   : ₦{outstanding:,.2f}"
    )

    # ------------------------------------
    # FOLLOW-UP HISTORY
    # ------------------------------------
    cur.execute("""
        SELECT
            f.*,
            c.balance AS current_credit_balance
        FROM collection_followups f
        LEFT JOIN customer_credit c
            ON c.id = f.credit_id
        WHERE f.customer_id = ?
        ORDER BY f.contact_date DESC, f.id DESC
    """, (customer_id,))

    followups = cur.fetchall()

    print("\n========================================")
    print("          FOLLOW-UP HISTORY")
    print("========================================")

    if not followups:
        print("----------------------------------------")
        print("No collection follow-ups recorded.")
        print("----------------------------------------")

    else:

        for index, row in enumerate(
            followups, start=1
        ):

            print("----------------------------------------")
            print(
                f"FOLLOW-UP #{index}"
            )
            print("----------------------------------------")

            print(
                f"Follow-up ID    : {row['id']}"
            )

            print(
                f"Credit ID       : "
                f"{row['credit_id']}"
            )

            print(
                f"Staff           : "
                f"{row['staff_name'] or 'System'}"
            )

            print(
                f"Contact Date    : "
                f"{row['contact_date']}"
            )

            print(
                f"Method          : "
                f"{row['contact_method'] or 'N/A'}"
            )

            print(
                f"Promised Amount : "
                f"₦{float(row['promised_amount'] or 0):,.2f}"
            )

            print(
                f"Promised Date   : "
                f"{row['promised_date'] or 'N/A'}"
            )

            print(
                f"Status          : "
                f"{row['status'] or 'N/A'}"
            )

            print(
                f"Notes           : "
                f"{row['notes'] or 'N/A'}"
            )

            if row["current_credit_balance"] is not None:

                print(
                    f"Current Credit Balance : "
                    f"₦{float(row['current_credit_balance']):,.2f}"
                )

    # ------------------------------------
    # FOLLOW-UP SUMMARY
    # ------------------------------------
    total_followups = len(followups)

    total_promised = sum(
        float(row["promised_amount"] or 0)
        for row in followups
    )

    promised_count = sum(
        1
        for row in followups
        if str(row["status"] or "").upper()
        in ("PROMISE", "PROMISED")
    )

    print("\n========================================")
    print("          FOLLOW-UP SUMMARY")
    print("========================================")

    print(
        f"Total Follow-ups : {total_followups}"
    )

    print(
        f"Total Promised   : ₦{total_promised:,.2f}"
    )

    print(
        f"Promise Records  : {promised_count}"
    )

    print(
        f"Outstanding Debt : ₦{outstanding:,.2f}"
    )

    print("----------------------------------------")
    print(
        "READ-ONLY: No credit/payment records "
        "were modified."
    )
    print("========================================")

    conn.close()

    input("\nPress Enter to continue...")


if __name__ == "__main__":
    show_followup_history()
