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
    CREATE TABLE IF NOT EXISTS creditors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        supplier_name TEXT NOT NULL,
        phone TEXT,
        amount REAL NOT NULL,
        paid REAL DEFAULT 0,
        balance REAL NOT NULL,
        purchase_date TEXT
    )
    """)

    conn.commit()
    conn.close()


create_table()


def record_credit_purchase():
    conn = get_connection()
    cur = conn.cursor()

    print("\n========== RECORD CREDIT PURCHASE ==========")

    supplier_name = input("Supplier Name: ").strip()
    phone = input("Phone Number: ").strip()

    try:
        amount = float(input("Purchase Amount (₦): "))
    except ValueError:
        print("Invalid amount.")
        conn.close()
        return

    purchase_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("""
        INSERT INTO creditors
        (supplier_name, phone, amount, paid, balance, purchase_date)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        supplier_name,
        phone,
        amount,
        0,
        amount,
        purchase_date
    ))

    conn.commit()
    conn.close()

    print("Credit purchase recorded successfully.")
def view_creditors():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            id,
            supplier_name,
            phone,
            amount,
            paid,
            balance,
            purchase_date
        FROM creditors
        ORDER BY id DESC
    """)

    rows = cur.fetchall()

    print("\n========== CREDITORS ==========")

    if not rows:
        print("No creditors found.")
    else:
        for row in rows:
            print("-" * 40)
            print(f"ID        : {row['id']}")
            print(f"Supplier  : {row['supplier_name']}")
            print(f"Phone     : {row['phone']}")
            print(f"Amount    : ₦{row['amount']:,.2f}")
            print(f"Paid      : ₦{row['paid']:,.2f}")
            print(f"Balance   : ₦{row['balance']:,.2f}")
            print(f"Date      : {row['purchase_date']}")

    conn.close()


def record_payment():
    conn = get_connection()
    cur = conn.cursor()

    view_creditors()

    creditor_id = input("\nEnter Creditor ID: ").strip()

    cur.execute("""
        SELECT paid, balance
        FROM creditors
        WHERE id = ?
    """, (creditor_id,))

    row = cur.fetchone()

    if row is None:
        print("Creditor not found.")
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
        UPDATE creditors
        SET paid = ?, balance = ?
        WHERE id = ?
    """, (
        new_paid,
        new_balance,
        creditor_id
    ))

    conn.commit()
    conn.close()

    print("Payment recorded successfully.")
    print(f"Remaining Balance: ₦{new_balance:,.2f}")
def creditor_menu():
    while True:
        print("""
========== CREDITORS ==========
1. Record Credit Purchase
2. Record Payment
3. View Creditors
0. Back
=============================
""")

        choice = input("Select option: ").strip()

        if choice == "1":
            record_credit_purchase()

        elif choice == "2":
            record_payment()

        elif choice == "3":
            view_creditors()

        elif choice == "0":
            break

        else:
            print("Invalid option.")


if __name__ == "__main__":
    creditor_menu()
