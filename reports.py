import sqlite3

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def view_report():

    conn = get_connection()
    cur = conn.cursor()

    print("\n========== TRANSACTION REPORT ==========\n")

    cur.execute("""
        SELECT
            transaction_type,
            amount,
            charge,
            profit,
            transaction_date
        FROM transactions
        ORDER BY transaction_date DESC
    """)

    rows = cur.fetchall()

    if not rows:
        print("No transactions found.")
    else:
        for row in rows:

            print("----------------------------------------")
            print(f"Type    : {row['transaction_type']}")
            print(f"Amount  : ₦{row['amount']:,.2f}")
            print(f"Charge  : ₦{row['charge']:,.2f}")
            print(f"Profit  : ₦{row['profit']:,.2f}")
            print(f"Date    : {row['transaction_date']}")

    conn.close()
def financial_report():

    conn = get_connection()
    cur = conn.cursor()

    print("\n========== FINANCIAL REPORT ==========\n")

    # Transactions
    cur.execute("""
        SELECT
            IFNULL(SUM(amount),0),
            IFNULL(SUM(profit),0)
        FROM transactions
    """)

    total_transactions, total_profit = cur.fetchone()

    # Expenses
    cur.execute("""
        SELECT IFNULL(SUM(amount),0)
        FROM expenses
    """)

    total_expenses = cur.fetchone()[0]

    # Sales
    cur.execute("""
        SELECT IFNULL(SUM(total_amount),0)
        FROM sales
    """)

    total_sales = cur.fetchone()[0]

    net_profit = total_profit - total_expenses

    print("----------------------------------------")
    print(f"Total Sales        : ₦{total_sales:,.2f}")
    print(f"Transactions       : ₦{total_transactions:,.2f}")
    print(f"Gross Profit       : ₦{total_profit:,.2f}")
    print(f"Expenses           : ₦{total_expenses:,.2f}")
    print("----------------------------------------")
    print(f"Net Profit         : ₦{net_profit:,.2f}")
    print("----------------------------------------")

    conn.close()
def daily_closing_report():

    conn = get_connection()
    cur = conn.cursor()

    # Today's sales and profit
    cur.execute("""
        SELECT
            IFNULL(SUM(total_amount),0),
            IFNULL(SUM(total_profit),0),
            COUNT(*)
        FROM sales
        WHERE DATE(sale_date)=DATE('now','localtime')
    """)

    today_sales, today_profit, transactions = cur.fetchone()

    # Today's expenses
    cur.execute("""
        SELECT IFNULL(SUM(amount),0)
        FROM expenses
        WHERE DATE(expense_date)=DATE('now','localtime')
    """)

    today_expenses = cur.fetchone()[0]

    # Balance
    cur.execute("""
        SELECT
            opening_balance,
            cash_balance,
            wallet_balance
        FROM balance
        WHERE id=1
    """)

    row = cur.fetchone()

    if row:
        opening = row["opening_balance"]
        cash = row["cash_balance"]
        wallet = row["wallet_balance"]
    else:
        opening = cash = wallet = 0

    expected_cash = opening + today_sales - today_expenses

    print("\n====================================")
    print("      DAILY CLOSING REPORT")
    print("====================================")

    cur.execute("SELECT DATE('now','localtime')")
    report_date = cur.fetchone()[0]

    print(f"Date                : {report_date}")

    print("------------------------------------")

    print(f"Opening Balance     : ₦{opening:,.2f}")

    print("------------------------------------")

    print(f"Today's Sales       : ₦{today_sales:,.2f}")
    print(f"Today's Profit      : ₦{today_profit:,.2f}")
    print(f"Today's Expenses    : ₦{today_expenses:,.2f}")

    print("------------------------------------")

    print(f"Cash Box            : ₦{cash:,.2f}")
    print(f"Wallet Balance      : ₦{wallet:,.2f}")

    print("------------------------------------")

    print(f"Expected Cash       : ₦{expected_cash:,.2f}")
    print(f"Transactions Today  : {transactions}")

    print("====================================")

    conn.close()
