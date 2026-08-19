import sqlite3
from datetime import datetime

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def create_table():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS debtors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_name TEXT NOT NULL,
        phone TEXT,
        amount REAL NOT NULL,
        paid REAL DEFAULT 0,
        balance REAL DEFAULT 0,
        sale_date TEXT
    )
    """)

    conn.commit()
    conn.close()


create_table()


def record_credit_sale():
    conn = get_connection()
    cur = conn.cursor()

    print("\n========== RECORD CREDIT SALE ==========")

    customer_name = input("Customer Name: ").strip()
    phone = input("Phone Number: ").strip()

    try:
        amount = float(input("Credit Amount (₦): "))
    except ValueError:
        print("Invalid amount.")
        conn.close()
        return

    sale_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("""
        INSERT INTO debtors
        (customer_name, phone, amount, paid, balance, sale_date)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        customer_name,
        phone,
        amount,
        0,
        amount,
        sale_date
    ))

    conn.commit()
    conn.close()

    print("Credit sale recorded successfully.")
def view_debtors():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            id,
            customer_name,
            phone,
            amount,
            paid,
            balance,
            sale_date
        FROM debtors
        ORDER BY id DESC
    """)

    rows = cur.fetchall()

    print("\n========== DEBTORS ==========")

    if not rows:
        print("No debtors found.")
    else:
        for row in rows:
            print("-" * 40)
            print(f"ID        : {row['id']}")
            print(f"Customer  : {row['customer_name']}")
            print(f"Phone     : {row['phone']}")
            print(f"Amount    : ₦{row['amount']:,.2f}")
            print(f"Paid      : ₦{row['paid']:,.2f}")
            print(f"Balance   : ₦{row['balance']:,.2f}")
            print(f"Date      : {row['sale_date']}")

    conn.close()


def record_payment():
    conn = get_connection()
    cur = conn.cursor()

    view_debtors()

    debtor_id = input("\nEnter Debtor ID: ").strip()

    cur.execute("""
        SELECT paid, balance
        FROM debtors
        WHERE id = ?
    """, (debtor_id,))

    row = cur.fetchone()

    if row is None:
        print("Debtor not found.")
        conn.close()
        return

    try:
        payment = float(input("Payment Amount (₦): "))
    except ValueError:
        print("Invalid amount.")
        conn.close()
        return

    if payment <= 0:
        print("Payment must be greater than zero.")
        conn.close()
        return

    if payment > row["balance"]:
        print("Payment exceeds outstanding balance.")
        conn.close()
        return

    new_paid = row["paid"] + payment
    new_balance = row["balance"] - payment

    cur.execute("""
        UPDATE debtors
        SET paid = ?, balance = ?
        WHERE id = ?
    """, (
        new_paid,
        new_balance,
        debtor_id
    ))

    conn.commit()
    conn.close()

    print("Payment recorded successfully.")
    print(f"Remaining Balance: ₦{new_balance:,.2f}")
def debtor_menu():
    while True:
        print("""
========== DEBTORS ==========
1. Record Credit Sale
2. Record Payment
3. View Debtors
0. Back
=============================
""")

        choice = input("Select option: ").strip()

        if choice == "1":
            record_credit_sale()

        elif choice == "2":
            record_payment()

        elif choice == "3":
            view_debtors()

        elif choice == "0":
            break

        else:
            print("Invalid option.")


if __name__ == "__main__":
    debtor_menu()
