import sqlite3
from datetime import datetime

from balance import update_cash_balance
from audit import log_action

DB_NAME = "data/posledger.db"


def add_expense():

    try:
        title = input("Expense Name: ").strip()
        amount = float(input("Amount (₦): "))
    except ValueError:
        print("❌ Invalid amount.")
        return

    expense_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO expenses
        (
            title,
            amount,
            expense_date
        )
        VALUES (?, ?, ?)
    """, (
        title,
        amount,
        expense_date
    ))

    conn.commit()
    conn.close()

    update_cash_balance(-amount)

    log_action(
        "Mukhtar Aliyu",
        "Expense",
        f"{title} - ₦{amount:,.2f}"
    )

    print("\n✅ Expense recorded successfully.")


if __name__ == "__main__":
    expense_menu()
def expense_menu():

    while True:

        print("""
====================================
           EXPENSE MENU
====================================
1. Add Expense
0. Back
====================================
""")

        choice = input("Select option: ").strip()

        if choice == "1":
            add_expense()

        elif choice == "0":
            break

        else:
            print("❌ Invalid option.")
