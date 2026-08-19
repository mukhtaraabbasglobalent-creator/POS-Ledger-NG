import sqlite3

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def show_payment(row, number=None):
    print("----------------------------------------")

    if number is not None:
        print(f"{number}. Payment No : {row['payment_no']}")
    else:
        print(f"Payment No : {row['payment_no']}")

    print(f"Type       : {row['payment_type']}")
    print(f"Customer   : {row['customer_name']}")
    print(f"Phone      : {row['phone'] or 'N/A'}")
    print(f"Credit ID  : {row['credit_id']}")
    print(f"Amount     : ₦{float(row['amount'] or 0):,.2f}")
    print(f"Date       : {row['payment_date']}")
    print(f"Staff      : {row['staff_name'] or 'System'}")

    if row["reference"]:
        print(f"Reference  : {row['reference']}")

    if row["notes"]:
        print(f"Notes      : {row['notes']}")

    print("----------------------------------------")


def get_payment_query():
    """
    Combine:
      1. Normal payments from credit_payments
      2. Historical/reconciled payments from credit_reconciliations
    """

    return """
        SELECT
            cp.id AS record_id,
            cp.payment_no AS payment_no,
            cp.customer_id,
            cp.credit_id,
            cp.amount,
            cp.payment_date,
            cp.staff_name,
            'PAYMENT' AS payment_type,
            NULL AS reference,
            NULL AS notes,
            c.fullname AS customer_name,
            c.phone
        FROM credit_payments cp
        LEFT JOIN customers c
            ON c.id = cp.customer_id

        UNION ALL

        SELECT
            cr.id AS record_id,
            cr.reference AS payment_no,
            cr.customer_id,
            cr.credit_id,
            cr.amount,
            cr.reconciliation_date AS payment_date,
            cr.staff_name,
            'HISTORICAL PAYMENT' AS payment_type,
            cr.reference,
            cr.notes,
            c.fullname AS customer_name,
            c.phone
        FROM credit_reconciliations cr
        LEFT JOIN customers c
            ON c.id = cr.customer_id
    """


def view_recent_payments():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        get_payment_query()
        + """
        ORDER BY payment_date DESC
        LIMIT 20
        """
    )

    rows = cur.fetchall()

    print("\n========================================")
    print("          PAYMENT HISTORY")
    print("========================================")

    if not rows:
        print("No payment records found.")
    else:
        total = 0

        for index, row in enumerate(rows, start=1):
            show_payment(row, index)
            total += float(row["amount"] or 0)

        print("----------------------------------------")
        print(f"TOTAL SHOWN : ₦{total:,.2f}")

    print("========================================")

    conn.close()
    input("\nPress Enter to continue...")


def search_payment_number():
    conn = get_connection()
    cur = conn.cursor()

    search = input(
        "\nEnter Payment Number / Reference: "
    ).strip()

    if not search:
        print("❌ Payment number cannot be empty.")
        conn.close()
        input("\nPress Enter to continue...")
        return

    cur.execute(
        get_payment_query()
        + """
        WHERE LOWER(payment_no) LIKE LOWER(?)
           OR LOWER(COALESCE(reference, '')) LIKE LOWER(?)
        ORDER BY payment_date DESC
        """,
        (f"%{search}%", f"%{search}%")
    )

    rows = cur.fetchall()

    print("\n========================================")
    print("          SEARCH RESULTS")
    print("========================================")

    if not rows:
        print("❌ No payment found.")
    else:
        total = 0

        for index, row in enumerate(rows, start=1):
            show_payment(row, index)
            total += float(row["amount"] or 0)

        print("----------------------------------------")
        print(f"TOTAL FOUND : ₦{total:,.2f}")

    print("========================================")

    conn.close()
    input("\nPress Enter to continue...")


def search_customer_payments():
    conn = get_connection()
    cur = conn.cursor()

    search = input(
        "\nEnter Customer Name: "
    ).strip()

    if not search:
        print("❌ Customer name cannot be empty.")
        conn.close()
        input("\nPress Enter to continue...")
        return

    cur.execute(
        get_payment_query()
        + """
        WHERE LOWER(customer_name) LIKE LOWER(?)
        ORDER BY payment_date DESC
        """,
        (f"%{search}%",)
    )

    rows = cur.fetchall()

    print("\n========================================")
    print("       CUSTOMER PAYMENT HISTORY")
    print("========================================")

    if not rows:
        print("❌ No payments found.")
    else:
        total = 0

        for index, row in enumerate(rows, start=1):
            show_payment(row, index)
            total += float(row["amount"] or 0)

        print("----------------------------------------")
        print(f"TOTAL PAYMENTS : ₦{total:,.2f}")

    print("========================================")

    conn.close()
    input("\nPress Enter to continue...")


def search_credit_payments():
    conn = get_connection()
    cur = conn.cursor()

    credit_input = input(
        "\nEnter Credit ID: "
    ).strip()

    try:
        credit_id = int(credit_input)
    except ValueError:
        print("❌ Invalid Credit ID.")
        conn.close()
        input("\nPress Enter to continue...")
        return

    cur.execute(
        get_payment_query()
        + """
        WHERE credit_id = ?
        ORDER BY payment_date ASC
        """,
        (credit_id,)
    )

    rows = cur.fetchall()

    print("\n========================================")
    print("        CREDIT PAYMENT HISTORY")
    print("========================================")

    if not rows:
        print("No payments found for this credit.")
    else:
        total = 0

        for index, row in enumerate(rows, start=1):
            show_payment(row, index)
            total += float(row["amount"] or 0)

        print("----------------------------------------")
        print(f"TOTAL PAID/HISTORY : ₦{total:,.2f}")

    print("========================================")

    conn.close()
    input("\nPress Enter to continue...")


def account_payment_summary():
    conn = get_connection()
    cur = conn.cursor()

    customer_input = input(
        "\nEnter Customer ID: "
    ).strip()

    try:
        customer_id = int(customer_input)
    except ValueError:
        print("❌ Invalid Customer ID.")
        conn.close()
        input("\nPress Enter to continue...")
        return

    customer = cur.execute(
        """
        SELECT id, fullname, phone, credit_limit
        FROM customers
        WHERE id = ?
        """,
        (customer_id,)
    ).fetchone()

    if not customer:
        print("❌ Customer not found.")
        conn.close()
        input("\nPress Enter to continue...")
        return

    credit_sales = cur.execute(
        """
        SELECT COALESCE(SUM(total_amount), 0)
        FROM customer_credit
        WHERE customer_id = ?
        """,
        (customer_id,)
    ).fetchone()[0]

    normal_payments = cur.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM credit_payments
        WHERE customer_id = ?
        """,
        (customer_id,)
    ).fetchone()[0]

    historical_payments = cur.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM credit_reconciliations
        WHERE customer_id = ?
        """,
        (customer_id,)
    ).fetchone()[0]

    outstanding = cur.execute(
        """
        SELECT COALESCE(SUM(balance), 0)
        FROM customer_credit
        WHERE customer_id = ?
        """,
        (customer_id,)
    ).fetchone()[0]

    total_paid = normal_payments + historical_payments
    credit_limit = float(customer["credit_limit"] or 0)
    available_credit = credit_limit - outstanding

    print("\n========================================")
    print("          ACCOUNT SUMMARY")
    print("========================================")
    print(f"Customer           : {customer['fullname']}")
    print(f"Phone              : {customer['phone'] or 'N/A'}")
    print("----------------------------------------")
    print(f"Total Credit Sales : ₦{credit_sales:,.2f}")
    print(f"Normal Payments    : ₦{normal_payments:,.2f}")
    print(f"Historical Payments: ₦{historical_payments:,.2f}")
    print(f"TOTAL PAID         : ₦{total_paid:,.2f}")
    print(f"Outstanding Debt    : ₦{outstanding:,.2f}")
    print(f"Credit Limit       : ₦{credit_limit:,.2f}")
    print(f"Available Credit   : ₦{available_credit:,.2f}")
    print("----------------------------------------")

    if outstanding <= 0:
        print("STATUS : 🟢 ACCOUNT CLEAR")
    else:
        print("STATUS : 🟡 ACCOUNT OUTSTANDING")

    print("========================================")

    conn.close()
    input("\nPress Enter to continue...")


def payment_history_menu():

    while True:

        print("""
========================================
        CREDIT PAYMENT HISTORY
========================================
1. Recent Payments
2. Search Payment Number
3. Search Customer Name
4. Search Credit ID
5. Account Payment Summary
0. Back
========================================
""")

        choice = input("Select option: ").strip()

        if choice == "1":
            view_recent_payments()

        elif choice == "2":
            search_payment_number()

        elif choice == "3":
            search_customer_payments()

        elif choice == "4":
            search_credit_payments()

        elif choice == "5":
            account_payment_summary()

        elif choice == "0":
            break

        else:
            print("❌ Invalid option.")


if __name__ == "__main__":
    payment_history_menu()
