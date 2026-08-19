import sqlite3
from datetime import datetime

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def daily_profit_loss():

    conn = get_connection()
    cur = conn.cursor()

    today = datetime.now().strftime("%Y-%m-%d")

    # Today's sales
    cur.execute("""
    SELECT
        COALESCE(SUM(total_amount),0) AS sales,
        COALESCE(SUM(total_profit),0) AS profit
    FROM sales
    WHERE DATE(sale_date)=?
    """, (today,))

    sales = cur.fetchone()

    # Today's expenses
    cur.execute("""
    SELECT
        COALESCE(SUM(amount),0) AS expenses
    FROM expenses
    WHERE DATE(expense_date)=?
    """, (today,))

    expense = cur.fetchone()

    total_sales = sales["sales"]
    gross_profit = sales["profit"]
    total_expenses = expense["expenses"]
    net_profit = gross_profit - total_expenses

    print("\n========== DAILY PROFIT & LOSS ==========")
    print(f"Date          : {today}")
    print(f"Sales         : ₦{total_sales:,.2f}")
    print(f"Gross Profit  : ₦{gross_profit:,.2f}")
    print(f"Expenses      : ₦{total_expenses:,.2f}")
    print("-----------------------------------------")
    print(f"Net Profit    : ₦{net_profit:,.2f}")

    conn.close()
def monthly_profit_loss():

    conn = get_connection()
    cur = conn.cursor()

    month = datetime.now().strftime("%Y-%m")

    # Monthly sales
    cur.execute("""
    SELECT
        COALESCE(SUM(total_amount),0) AS sales,
        COALESCE(SUM(total_profit),0) AS profit
    FROM sales
    WHERE substr(sale_date,1,7)=?
    """, (month,))

    sales = cur.fetchone()

    # Monthly expenses
    cur.execute("""
    SELECT
        COALESCE(SUM(amount),0) AS expenses
    FROM expenses
    WHERE substr(expense_date,1,7)=?
    """, (month,))

    expense = cur.fetchone()

    total_sales = sales["sales"]
    gross_profit = sales["profit"]
    total_expenses = expense["expenses"]
    net_profit = gross_profit - total_expenses

    print("\n========== MONTHLY PROFIT & LOSS ==========")
    print(f"Month         : {month}")
    print(f"Sales         : ₦{total_sales:,.2f}")
    print(f"Gross Profit  : ₦{gross_profit:,.2f}")
    print(f"Expenses      : ₦{total_expenses:,.2f}")
    print("-------------------------------------------")
    print(f"Net Profit    : ₦{net_profit:,.2f}")

    conn.close()
def business_summary():

    conn = get_connection()
    cur = conn.cursor()

    # Total Sales
    cur.execute("""
    SELECT
        COALESCE(SUM(total_amount),0) AS sales,
        COALESCE(SUM(total_profit),0) AS profit
    FROM sales
    """)
    sales = cur.fetchone()

    # Total Expenses
    cur.execute("""
    SELECT
        COALESCE(SUM(amount),0) AS expenses
    FROM expenses
    """)
    expense = cur.fetchone()

    # Total Purchases
    try:
        cur.execute("""
        SELECT
            COALESCE(SUM(total_amount),0) AS purchases
        FROM purchases
        """)
        purchase = cur.fetchone()
        total_purchases = purchase["purchases"]
    except sqlite3.OperationalError:
        total_purchases = 0

    total_sales = sales["sales"]
    gross_profit = sales["profit"]
    total_expenses = expense["expenses"]
    net_profit = gross_profit - total_expenses

    print("\n========== BUSINESS SUMMARY ==========")
    print(f"Total Sales      : ₦{total_sales:,.2f}")
    print(f"Total Purchases  : ₦{total_purchases:,.2f}")
    print(f"Gross Profit     : ₦{gross_profit:,.2f}")
    print(f"Total Expenses   : ₦{total_expenses:,.2f}")
    print("--------------------------------------")
    print(f"Net Profit       : ₦{net_profit:,.2f}")
    print("======================================")

    conn.close()
def profit_loss_menu():
    while True:
        print("""
========== PROFIT & LOSS ==========
1. Daily Profit & Loss
2. Monthly Profit & Loss
3. Business Summary
0. Back
===================================
""")

        choice = input("Select option: ").strip()

        if choice == "1":
            daily_profit_loss()

        elif choice == "2":
            monthly_profit_loss()

        elif choice == "3":
            business_summary()

        elif choice == "0":
            break

        else:
            print("Invalid option.")


if __name__ == "__main__":
    profit_loss_menu()
