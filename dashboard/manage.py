import sqlite3

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def business_dashboard():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT cash_balance, wallet_balance, opening_balance
    FROM balance
    WHERE id=1
    """)
    row = cur.fetchone()

    cash = row["cash_balance"] if row else 0
    wallet = row["wallet_balance"] if row else 0
    opening = row["opening_balance"] if row else 0

    cur.execute("""
    SELECT IFNULL(SUM(total_amount),0)
    FROM sales
    WHERE DATE(sale_date)=DATE('now','localtime')
    """)
    today_sales = cur.fetchone()[0]

    cur.execute("""
    SELECT IFNULL(SUM(total_profit),0)
    FROM sales
    WHERE DATE(sale_date)=DATE('now','localtime')
    """)
    today_profit = cur.fetchone()[0]

    cur.execute("""
    SELECT IFNULL(SUM(amount),0)
    FROM expenses
    WHERE DATE(expense_date)=DATE('now','localtime')
    """)
    today_expenses = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM products")
    products = cur.fetchone()[0]

    cur.execute("""
    SELECT COUNT(*)
    FROM products
    WHERE current_stock <= 5
    """)
    low_stock = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM customers")
    customers = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM suppliers")
    suppliers = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM transactions")
    transactions = cur.fetchone()[0]

    conn.close()

    print("""
====================================
      POS LEDGER NG DASHBOARD
====================================
""")

    print(f"💵 Cash Box          : ₦{cash:,.2f}")
    print(f"🏦 Wallet Balance    : ₦{wallet:,.2f}")
    print(f"💼 Opening Balance   : ₦{opening:,.2f}")

    print("------------------------------------")

    print(f"📈 Today's Sales     : ₦{today_sales:,.2f}")
    print(f"💰 Today's Profit    : ₦{today_profit:,.2f}")
    print(f"💸 Today's Expenses  : ₦{today_expenses:,.2f}")

    print("------------------------------------")

    print(f"📦 Products          : {products}")
    print(f"⚠️ Low Stock Items   : {low_stock}")
    print(f"👥 Customers         : {customers}")
    print(f"🚚 Suppliers         : {suppliers}")
    print(f"📊 Transactions      : {transactions}")

    print("====================================")

    input("\nPress Enter to continue...")


def dashboard_menu():
    business_dashboard()
