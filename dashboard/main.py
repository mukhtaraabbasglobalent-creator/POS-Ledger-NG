import sqlite3

DB_NAME = "data/posledger.db"


def dashboard():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    # Current Balance
    try:
        cur.execute("SELECT amount FROM balance WHERE id = 1")
        row = cur.fetchone()
        balance = row[0] if row else 0
    except Exception:
        balance = 0

    # Total Expenses
    try:
        cur.execute("SELECT IFNULL(SUM(amount), 0) FROM expenses")
        expenses = cur.fetchone()[0]
    except Exception:
        expenses = 0

    # Outstanding Debts
    try:
        cur.execute("SELECT IFNULL(SUM(balance), 0) FROM debtors")
        debtors = cur.fetchone()[0]
    except Exception:
        debtors = 0

    # Total Products
    try:
        cur.execute("SELECT COUNT(*) FROM products")
        products = cur.fetchone()[0]
    except Exception:
        products = 0

    print("\n====================================")
    print("         POS LEDGER NG")
    print("            DASHBOARD")
    print("====================================")
    print(f"Current Balance : ₦{balance:,.2f}")
    print(f"Expenses        : ₦{expenses:,.2f}")
    print(f"Outstanding Debt: ₦{debtors:,.2f}")
    print(f"Products        : {products}")
    print("====================================")

    conn.close()


if __name__ == "__main__":
    dashboard()
