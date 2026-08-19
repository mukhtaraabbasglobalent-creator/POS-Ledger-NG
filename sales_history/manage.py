import sqlite3

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def view_sales():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT
        sales.id,
        products.product_name,
        sales.quantity,
        sales.selling_price,
        sales.total_amount,
        sales.total_profit,
        sales.sale_date
    FROM sales
    LEFT JOIN products
        ON sales.product_id = products.id
    ORDER BY sales.id DESC
    """)

    rows = cur.fetchall()

    print("\n========== SALES HISTORY ==========")

    if not rows:
        print("No sales found.")
        conn.close()
        return

    for row in rows:
        print("----------------------------------------")
        print(f"ID        : {row['id']}")
        print(f"Product   : {row['product_name']}")
        print(f"Quantity  : {row['quantity']}")
        print(f"Unit Price: ₦{row['selling_price']:,.2f}")
        print(f"Total     : ₦{row['total_amount']:,.2f}")
        print(f"Profit    : ₦{row['total_profit']:,.2f}")
        print(f"Date      : {row['sale_date']}")

def view_transaction_history():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            t.id,
            t.transaction_type,
            t.amount,
            t.charge,
            t.provider_fee,
            t.profit,
            t.provider,
            t.transaction_date,
            c.fullname AS customer_name
        FROM transactions t
        LEFT JOIN customers c
            ON t.customer_id = c.id
        ORDER BY t.id DESC
    """)

    rows = cur.fetchall()

    print("\n========================================")
    print("       GLOBAL TRANSACTION HISTORY")
    print("========================================")

    if not rows:
        print("No financial transactions found.")
        conn.close()
        input("\nPress Enter to continue...")
        return

    total_amount = 0
    total_charge = 0
    total_fee = 0
    total_profit = 0

    for row in rows:

        amount = row["amount"] or 0
        charge = row["charge"] or 0
        fee = row["provider_fee"] or 0
        profit = row["profit"] or 0

        total_amount += amount
        total_charge += charge
        total_fee += fee
        total_profit += profit

        customer = row["customer_name"] or "Walk-in"
        provider = row["provider"] or "N/A"

        print("----------------------------------------")
        print(f"Transaction ID : {row['id']}")
        print(f"Customer       : {customer}")
        print(f"Provider       : {provider}")
        print(f"Type           : {row['transaction_type']}")
        print(f"Amount         : ₦{amount:,.2f}")
        print(f"Customer Charge: ₦{charge:,.2f}")
        print(f"Provider Fee   : ₦{fee:,.2f}")
        print(f"Profit         : ₦{profit:,.2f}")
        print(f"Date           : {row['transaction_date']}")

    print("----------------------------------------")
    print("             HISTORY TOTALS")
    print("----------------------------------------")
    print(f"Total Amount   : ₦{total_amount:,.2f}")
    print(f"Total Charges  : ₦{total_charge:,.2f}")
    print(f"Total Fees     : ₦{total_fee:,.2f}")
    print(f"Total Profit   : ₦{total_profit:,.2f}")
    print("========================================")

    conn.close()
    input("\nPress Enter to continue...")

    conn.close()
def search_sales():
    conn = get_connection()
    cur = conn.cursor()

    keyword = input("\nProduct Name: ").strip().lower()

    cur.execute("""
    SELECT
        sales.id,
        products.product_name,
        sales.quantity,
        sales.selling_price,
        sales.total_amount,
        sales.total_profit,
        sales.sale_date
    FROM sales
    LEFT JOIN products
        ON sales.product_id = products.id
    WHERE LOWER(products.product_name) LIKE ?
    ORDER BY sales.id DESC
    """, (f"%{keyword}%",))

    rows = cur.fetchall()

    print("\n========== SEARCH RESULT ==========")

    if not rows:
        print("No matching sales found.")
        conn.close()
        return

    for row in rows:
        print("----------------------------------------")
        print(f"ID        : {row['id']}")
        print(f"Product   : {row['product_name']}")
        print(f"Quantity  : {row['quantity']}")
        print(f"Total     : ₦{row['total_amount']:,.2f}")
        print(f"Profit    : ₦{row['total_profit']:,.2f}")
        print(f"Date      : {row['sale_date']}")

    conn.close()


def daily_summary():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT
        IFNULL(SUM(total_amount),0),
        IFNULL(SUM(total_profit),0),
        COUNT(*)
    FROM sales
    WHERE DATE(sale_date)=DATE('now')
    """)

    total_sales, total_profit, total_transactions = cur.fetchone()

    print("\n========== TODAY'S SALES ==========")
    print(f"Transactions : {total_transactions}")
    print(f"Sales        : ₦{total_sales:,.2f}")
    print(f"Profit       : ₦{total_profit:,.2f}")

    conn.close()
def sales_history_menu():
    while True:
        print("""
========== SALES HISTORY ==========
1. View product Sales
2. Search product sales
3. Today sale  Summary
4. Global transaction history
0. Back
===================================
""")

        choice = input("Select option: ").strip()

        if choice == "1":
            view_sales()

        elif choice == "2":
            search_sales()

        elif choice == "3":
            daily_summary()

        elif choice == "4":
            view_transaction_history()

        elif choice == "0":
            break

        else:
            print("Invalid option.")


if __name__ == "__main__":
    sales_history_menu()
