import sqlite3
from datetime import datetime
from balance import transfer_between_cash_and_wallet

DB_NAME = "data/posledger.db"


def deposit_money():

    try:
        amount = float(input("Deposit Amount (₦): "))
    except ValueError:
        print("Invalid amount.")
        return

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
    "Deposit",
    amount,
    0,
    0,
    date
))

    conn.commit()
    conn.close()

    # Increase balance
    transfer_between_cash_and_wallet(
    -amount,
    amount
)

    print("\nDeposit recorded successfully!")
