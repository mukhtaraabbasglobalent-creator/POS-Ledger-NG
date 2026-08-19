import sqlite3
from datetime import datetime

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def create_followup_table():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS collection_followups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            credit_id INTEGER,
            staff_name TEXT,
            contact_date TEXT NOT NULL,
            contact_method TEXT,
            promised_amount REAL DEFAULT 0,
            promised_date TEXT,
            status TEXT DEFAULT 'CONTACTED',
            notes TEXT,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def record_followup():
    create_followup_table()

    conn = get_connection()
    cur = conn.cursor()

    print("\n========================================")
    print("       POS LEDGER NG V11")
    print("   COLLECTION FOLLOW-UP")
    print("========================================")

    customer_input = input(
        "\nCustomer ID: "
    ).strip()

    if not customer_input.isdigit():
        print("\n❌ Invalid Customer ID.")
        conn.close()
        input("\nPress Enter to continue...")
        return

    customer_id = int(customer_input)

    cur.execute("""
        SELECT *
        FROM customers
        WHERE id = ?
    """, (customer_id,))

    customer = cur.fetchone()

    if not customer:
        print("\n❌ Customer not found.")
        conn.close()
        input("\nPress Enter to continue...")
        return

    cur.execute("""
        SELECT
            id,
            balance,
            created_date
        FROM customer_credit
        WHERE customer_id = ?
          AND balance > 0
        ORDER BY created_date ASC
    """, (customer_id,))

    credits = cur.fetchall()

    if not credits:
        print(
            "\n✅ This customer has no "
            "outstanding credit."
        )

        conn.close()
        input("\nPress Enter to continue...")
        return

    print("\n----------------------------------------")
    print("CUSTOMER")
    print("----------------------------------------")

    print(
        f"Name        : "
        f"{customer['fullname']}"
    )

    print(
        f"Phone       : "
        f"{customer['phone'] or 'N/A'}"
    )

    total_outstanding = sum(
        float(row["balance"] or 0)
        for row in credits
    )

    print(
        f"Outstanding : "
        f"₦{total_outstanding:,.2f}"
    )

    credit_input = input(
        "\nCredit ID (Enter for oldest): "
    ).strip()

    if credit_input == "":
        credit_id = credits[0]["id"]
    elif credit_input.isdigit():
        credit_id = int(credit_input)
    else:
        print("\n❌ Invalid Credit ID.")
        conn.close()
        input("\nPress Enter to continue...")
        return

    valid_credit = any(
        row["id"] == credit_id
        for row in credits
    )

    if not valid_credit:
        print(
            "\n❌ Credit ID is not an "
            "outstanding account for this customer."
        )

        conn.close()
        input("\nPress Enter to continue...")
        return

    staff_name = input(
        "Staff Name: "
    ).strip() or "System"

    contact_method = input(
        "Contact Method "
        "(Phone/Visit/SMS/WhatsApp/Other): "
    ).strip() or "Other"

    promised_amount_input = input(
        "Promised Payment Amount "
        "(0 if none): "
    ).strip()

    try:
        promised_amount = float(
            promised_amount_input or 0
        )

        if promised_amount < 0:
            raise ValueError

    except ValueError:
        print("\n❌ Invalid promised amount.")
        conn.close()
        input("\nPress Enter to continue...")
        return

    promised_date = input(
        "Promised Payment Date "
        "(YYYY-MM-DD, optional): "
    ).strip()

    status = input(
        "Status "
        "(CONTACTED/PROMISED/FOLLOW_UP/DISPUTED): "
    ).strip().upper()

    if not status:
        status = (
            "PROMISED"
            if promised_amount > 0
            else "CONTACTED"
        )

    notes = input(
        "Collection Notes: "
    ).strip()

    contact_date = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    created_at = contact_date

    cur.execute("""
        INSERT INTO collection_followups (
            customer_id,
            credit_id,
            staff_name,
            contact_date,
            contact_method,
            promised_amount,
            promised_date,
            status,
            notes,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        customer_id,
        credit_id,
        staff_name,
        contact_date,
        contact_method,
        promised_amount,
        promised_date or None,
        status,
        notes,
        created_at
    ))

    conn.commit()

    print("\n========================================")
    print("       FOLLOW-UP RECORDED")
    print("========================================")

    print(
        f"Customer        : "
        f"{customer['fullname']}"
    )

    print(
        f"Credit ID       : "
        f"{credit_id}"
    )

    print(
        f"Staff           : "
        f"{staff_name}"
    )

    print(
        f"Method          : "
        f"{contact_method}"
    )

    print(
        f"Promised Amount : "
        f"₦{promised_amount:,.2f}"
    )

    print(
        f"Promised Date   : "
        f"{promised_date or 'N/A'}"
    )

    print(
        f"Status          : "
        f"{status}"
    )

    print("----------------------------------------")
    print(
        "Credit balance/payment records "
        "were NOT modified."
    )
    print("========================================")

    conn.close()

    input("\nPress Enter to continue...")


if __name__ == "__main__":
    record_followup()
