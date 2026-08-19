import sqlite3
from datetime import datetime

from balance import transfer_between_cash_and_wallet
from audit import log_action

DB_NAME = "data/posledger.db"


def record_transaction():

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    print("""
==============================
 TRANSACTION TYPE
==============================
1. Cash In
2. Cash Out
==============================
""")

    choice = input("Select transaction type: ").strip()

    if choice == "1":
        transaction_type = "Cash In"
    elif choice == "2":
        transaction_type = "Cash Out"
    else:
        print("❌ Invalid transaction type.")
        conn.close()
        return

    try:
        amount = float(input("Amount (₦): "))
    except ValueError:
        print("❌ Invalid amount.")
        conn.close()
        return

    try:
        charge = float(input("Charge (₦): "))
    except ValueError:
        charge = 0

    profit = charge
    transaction_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
        transaction_type,
        amount,
        charge,
        profit,
        transaction_date
    ))

    conn.commit()
    conn.close()

    if transaction_type == "Cash In":
        transfer_between_cash_and_wallet(
            -amount,
            amount
        )
    else:
        transfer_between_cash_and_wallet(
            amount,
            -amount
        )

    log_action(
        "Mukhtar Aliyu",
        "Transaction",
        f"{transaction_type} - ₦{amount:,.2f}"
    )

    print("\n✅ Transaction recorded successfully.")


if __name__ == "__main__":
    record_transaction()
