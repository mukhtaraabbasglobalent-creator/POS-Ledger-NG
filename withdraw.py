import sqlite3
from datetime import datetime
from balance import transfer_between_cash_and_wallet
from audit import log_action
from staff.manage import current_user

DB_NAME = "data/posledger.db"


def withdraw_money():

    try:
        amount = float(input("Withdrawal Amount (₦): "))
    except ValueError:
        print("❌ Invalid amount.")
        return

    try:
        charge = float(input("Service Charge (₦): "))
    except ValueError:
        charge = 0

    profit = charge
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO transactions
        (
            transaction_type,
            amount,
            charge,
            profit,
            transaction_date
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        "Withdrawal",
        amount,
        charge,
        profit,
        date
    ))

    conn.commit()
    conn.close()

    transfer_between_cash_and_wallet(
    amount,
    -amount
)

    staff = current_user()

    staff = current_user()

    staff_name = "Unknown"

    if staff:
        staff_name = staff["fullname"]

    log_action(
        staff_name,
        "Withdrawal",
        f"Withdrawal - ₦{amount:,.2f}"
    )

    print("\n✅ Withdrawal recorded successfully.")
