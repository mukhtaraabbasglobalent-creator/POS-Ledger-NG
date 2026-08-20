import sqlite3
from datetime import datetime

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

    print("----------------------------------------")
    conn.close()


def financial_report():
    conn = get_connection()
    cur = conn.cursor()

    print("\n========== FINANCIAL REPORT ==========\n")

    cur.execute("""
        SELECT
            IFNULL(SUM(amount), 0),
            IFNULL(SUM(profit), 0)
        FROM transactions
    """)
    total_transactions, total_profit = cur.fetchone()

    cur.execute("""
        SELECT IFNULL(SUM(amount), 0)
        FROM expenses
    """)
    total_expenses = cur.fetchone()[0]

    cur.execute("""
        SELECT IFNULL(SUM(total_amount), 0),
               IFNULL(SUM(total_profit), 0)
        FROM sales
    """)
    total_sales, sales_profit = cur.fetchone()

    net_profit = total_profit + sales_profit - total_expenses

    print("----------------------------------------")
    print(f"Total Sales        : ₦{total_sales:,.2f}")
    print(f"Transactions       : ₦{total_transactions:,.2f}")
    print(f"Gross Profit       : ₦{total_profit + sales_profit:,.2f}")
    print(f"Expenses           : ₦{total_expenses:,.2f}")
    print("----------------------------------------")
    print(f"Net Profit         : ₦{net_profit:,.2f}")
    print("----------------------------------------")

    conn.close()


def daily_closing_report():
    conn = get_connection()
    cur = conn.cursor()

    today = datetime.now().strftime("%Y-%m-%d")

    cur.execute("""
        SELECT
            IFNULL(SUM(total_amount), 0),
            IFNULL(SUM(total_profit), 0),
            COUNT(*)
        FROM sales
        WHERE DATE(sale_date) = ?
    """, (today,))

    today_sales, today_profit, sale_count = cur.fetchone()

    cur.execute("""
        SELECT IFNULL(SUM(amount), 0)
        FROM expenses
        WHERE DATE(expense_date) = ?
    """, (today,))

    today_expenses = cur.fetchone()[0]

    cur.execute("""
        SELECT
            opening_balance,
            cash_balance,
            wallet_balance
        FROM balance
        WHERE id = 1
    """)

    row = cur.fetchone()

    if row:
        opening = row["opening_balance"] or 0
        cash = row["cash_balance"] or 0
        wallet = row["wallet_balance"] or 0
    else:
        opening = cash = wallet = 0

    expected_cash = opening + today_sales - today_expenses

    print("\n====================================")
    print("       DAILY CLOSING REPORT")
    print("====================================")
    print(f"Date                : {today}")
    print("------------------------------------")
    print(f"Opening Balance     : ₦{opening:,.2f}")
    print(f"Today's Sales       : ₦{today_sales:,.2f}")
    print(f"Today's Profit      : ₦{today_profit:,.2f}")
    print(f"Today's Expenses    : ₦{today_expenses:,.2f}")
    print("------------------------------------")
    print(f"Cash Box            : ₦{cash:,.2f}")
    print(f"Wallet Balance      : ₦{wallet:,.2f}")
    print("------------------------------------")
    print(f"Expected Cash       : ₦{expected_cash:,.2f}")
    print(f"Sales Today         : {sale_count}")
    print("====================================")

    conn.close()


def daily_summary():
    conn = get_connection()
    cur = conn.cursor()

    today = datetime.now().strftime("%Y-%m-%d")

    cur.execute("""
        SELECT
            COUNT(*),
            IFNULL(SUM(amount), 0),
            IFNULL(SUM(charge), 0),
            IFNULL(SUM(profit), 0)
        FROM transactions
        WHERE DATE(transaction_date) = ?
    """, (today,))

    count, amount, charges, profit = cur.fetchone()

    cur.execute("""
        SELECT IFNULL(SUM(amount), 0)
        FROM expenses
        WHERE DATE(expense_date) = ?
    """, (today,))

    expenses = cur.fetchone()[0]

    print("\n========== DAILY SUMMARY ==========")
    print(f"Date              : {today}")
    print(f"Transactions      : {count}")
    print(f"Transaction Value : ₦{amount:,.2f}")
    print(f"Charges           : ₦{charges:,.2f}")
    print(f"Profit            : ₦{profit:,.2f}")
    print(f"Expenses          : ₦{expenses:,.2f}")
    print(f"Net Profit        : ₦{profit - expenses:,.2f}")
    print("===================================")

    conn.close()


def monthly_summary():
    conn = get_connection()
    cur = conn.cursor()

    month = datetime.now().strftime("%Y-%m")

    cur.execute("""
        SELECT
            COUNT(*),
            IFNULL(SUM(amount), 0),
            IFNULL(SUM(charge), 0),
            IFNULL(SUM(profit), 0)
        FROM transactions
        WHERE strftime('%Y-%m', transaction_date) = ?
    """, (month,))

    count, amount, charges, profit = cur.fetchone()

    cur.execute("""
        SELECT IFNULL(SUM(amount), 0)
        FROM expenses
        WHERE strftime('%Y-%m', expense_date) = ?
    """, (month,))

    expenses = cur.fetchone()[0]

    print("\n========== MONTHLY SUMMARY ==========")
    print(f"Month             : {month}")
    print(f"Transactions      : {count}")
    print(f"Transaction Value : ₦{amount:,.2f}")
    print(f"Charges           : ₦{charges:,.2f}")
    print(f"Profit            : ₦{profit:,.2f}")
    print(f"Expenses          : ₦{expenses:,.2f}")
    print(f"Net Profit        : ₦{profit - expenses:,.2f}")
    print("=====================================")

    conn.close()
