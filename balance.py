import sqlite3

DB_NAME = "data/posledger.db"


def initialize_balance():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS balance(
            id INTEGER PRIMARY KEY,
            cash_balance REAL DEFAULT 0,
            wallet_balance REAL DEFAULT 0,
            opening_balance REAL DEFAULT 0
        )
    """)

    cur.execute("SELECT id FROM balance WHERE id = 1")

    if cur.fetchone() is None:
        cur.execute("""
            INSERT INTO balance(
                id,
                cash_balance,
                wallet_balance,
                opening_balance
            )
            VALUES (1,0,0,0)
        """)

    conn.commit()
    conn.close()


def get_balance():
    initialize_balance()

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT
            cash_balance,
            wallet_balance,
            opening_balance
        FROM balance
        WHERE id = 1
    """)

    row = cur.fetchone()

    conn.close()
    return row


def update_cash_balance(amount):
    initialize_balance()

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        UPDATE balance
        SET cash_balance = cash_balance + ?
        WHERE id = 1
    """, (amount,))

    conn.commit()
    conn.close()


# Compatibility for older modules
def update_balance(amount):
    update_cash_balance(amount)


def update_wallet_balance(amount):
    initialize_balance()

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        UPDATE balance
        SET wallet_balance = wallet_balance + ?
        WHERE id = 1
    """, (amount,))

    conn.commit()
    conn.close()


def transfer_between_cash_and_wallet(cash_change, wallet_change):
    initialize_balance()

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        UPDATE balance
        SET
            cash_balance = cash_balance + ?,
            wallet_balance = wallet_balance + ?
        WHERE id = 1
    """, (
        cash_change,
        wallet_change
    ))

    conn.commit()
    conn.close()


def set_opening_balance():
    initialize_balance()

    amount = float(input("Opening Balance (₦): "))

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        UPDATE balance
        SET
            opening_balance = ?,
            cash_balance = ?
        WHERE id = 1
    """, (
        amount,
        amount
    ))

    conn.commit()
    conn.close()

    print("✅ Opening Balance Updated.")


def show_balance():
    row = get_balance()

    print("\n========== BALANCE ==========")
    print(f"Cash Balance    : ₦{row['cash_balance']:,.2f}")
    print(f"Wallet Balance  : ₦{row['wallet_balance']:,.2f}")
    print(f"Opening Balance : ₦{row['opening_balance']:,.2f}")
    print("=============================")


if __name__ == "__main__":
    initialize_balance()

    balance = get_balance()

    print("=============================")
    print(f"Cash Balance: ₦{balance['cash_balance']:,.2f}")
    print(f"Wallet Balance: ₦{balance['wallet_balance']:,.2f}")
    print("=============================")
