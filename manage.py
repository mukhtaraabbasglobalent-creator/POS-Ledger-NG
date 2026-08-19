import sqlite3
from datetime import datetime

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def show_dashboard():
    conn = get_connection()
    cur = conn.cursor()

    today = datetime.now().strftime("%Y-%m-%d")

    try:
        cur.execute("""
        SELECT
            COALESCE(SUM(total_amount),0),
            COALESCE(SUM(total_profit),0)
        FROM sales
        WHERE DATE(sale_date)=?
        """, (today,))
        row = cur.fetchone()
        today_sales = row[0]
        today_profit = row[1]
    except:
        today_sales = 0
        today_profit = 0

    try:
        cur.execute("""
        SELECT opening_balance
        FROM opening_balance
        ORDER BY id DESC
        LIMIT 1
        """)
        row = cur.fetchone()
        opening = row[0] if row else 0
    except:
        opening = 0

    try:
        cur.execute("SELECT COUNT(*) FROM products")
        products = cur.fetchone()[0]
    except:
        products = 0

    try:
        cur.execute("SELECT COUNT(*) FROM customers")
        customers = cur.fetchone()[0]
    except:
        customers = 0

    try:
        cur.execute("SELECT COUNT(*) FROM suppliers")
        suppliers = cur.fetchone()[0]
    except:
        suppliers = 0

    try:
        cur.execute("""
        SELECT COUNT(*)
        FROM products
        WHERE current_stock<=min_stock
        """)
        low_stock = cur.fetchone()[0]
    except:
        low_stock = 0

    print("\n====================================")
    print("       POS LEDGER NG DASHBOARD")
    print("====================================")
    print(f"Today's Sales   : ₦{today_sales:,.2f}")
    print(f"Today's Profit  : ₦{today_profit:,.2f}")
    print(f"Opening Balance : ₦{opening:,.2f}")
    print("------------------------------------")
    print(f"Products        : {products}")
    print(f"Customers       : {customers}")
    print(f"Suppliers       : {suppliers}")
    print(f"Low Stock Items : {low_stock}")
    print("====================================")

    conn.close()


def dashboard_menu():
    while True:
        show_dashboard()

        print("""
1. Refresh Dashboard
0. Continue to Main Menu
""")

        choice = input("Select option: ").strip()

        if choice == "1":
            continue

        elif choice == "0":
            break

        else:
            print("Invalid option.")


if __name__ == "__main__":
    dashboard_menu()
