import sqlite3
from datetime import datetime

DB_NAME = "data/posledger.db"

def view_report():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    today = datetime.now().strftime("%Y-%m-%d")

    cur.execute("""
        SELECT trans_type, amount, charge, profit, trans_date
        FROM transactions
        WHERE trans_date LIKE ?
    """, (today + "%",))

    rows = cur.fetchall()

    if not rows:
        print("\nNo transactions found for today.")
        conn.close()
        return

    total_cash_in = 0
    total_cash_out = 0
    total_charge = 0
    total_profit = 0

    print("\n========== TODAY'S REPORT ==========")

    for row in rows:
        trans_type = row[0]
        amount = row[1]
        charge = row[2]
        profit = row[3]
        date = row[4]

        print(f"\nType   : {trans_type}")
        print(f"Amount : ₦{amount:,.2f}")
        print(f"Charge : ₦{charge:,.2f}")
        print(f"Profit : ₦{profit:,.2f}")
        print(f"Date   : {date}")

        if trans_type.lower() == "cash in":
            total_cash_in += amount
        elif trans_type.lower() == "cash out":
            total_cash_out += amount

        total_charge += charge
        total_profit += profit

    print("\n==============================")
    print("DAILY TOTALS")
    print("==============================")
    print(f"Cash In : ₦{total_cash_in:,.2f}")
    print(f"Cash Out: ₦{total_cash_out:,.2f}")
    print(f"Charges : ₦{total_charge:,.2f}")
    print(f"Profit  : ₦{total_profit:,.2f}")

    conn.close()
