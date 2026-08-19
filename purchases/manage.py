import sqlite3
from datetime import datetime

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def create_table():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        supplier_id INTEGER,
        quantity REAL NOT NULL,
        unit_cost REAL NOT NULL,
        total_cost REAL NOT NULL,
        purchase_date TEXT
    )
    """)

    conn.commit()
    conn.close()


create_table()


def record_purchase():

    conn = get_connection()
    cur = conn.cursor()

    print("\n========== RECORD PURCHASE ==========")

    cur.execute("""
    SELECT id, product_name
    FROM products
    ORDER BY product_name
    """)

    products = cur.fetchall()

    if not products:
        print("No products found.")
        conn.close()
        return

    print("\nAvailable Products")
    print("---------------------------")

    for row in products:
        print(f"{row['id']}. {row['product_name']}")

    try:
        product_id = int(input("\nProduct ID: "))
    except ValueError:
        print("Invalid Product ID.")
        conn.close()
        return

    cur.execute("""
    SELECT id, supplier_name
    FROM suppliers
    ORDER BY supplier_name
    """)

    suppliers = cur.fetchall()

    if not suppliers:
        print("No suppliers found.")
        conn.close()
        return

    print("\nAvailable Suppliers")
    print("---------------------------")

    for row in suppliers:
        print(f"{row['id']}. {row['supplier_name']}")

    try:
        supplier_id = int(input("\nSupplier ID: "))
        quantity = float(input("Quantity: "))
        unit_cost = float(input("Unit Cost (₦): "))
    except ValueError:
        print("Invalid input.")
        conn.close()
        return

    total_cost = quantity * unit_cost
    purchase_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
    INSERT INTO purchases(
        product_id,
        supplier_id,
        quantity,
        unit_cost,
        total_cost,
        purchase_date
    )
    VALUES(?,?,?,?,?,?)
    """, (
        product_id,
        supplier_id,
        quantity,
        unit_cost,
        total_cost,
        purchase_date
    ))

    cur.execute("""
    UPDATE products
    SET current_stock = current_stock + ?
    WHERE id = ?
    """, (
        quantity,
        product_id
    ))

    conn.commit()

    print("\nPurchase recorded successfully.")
    print(f"Total Cost: ₦{total_cost:,.2f}")

    conn.close()


def view_purchases():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT
        purchases.id,
        products.product_name,
        suppliers.supplier_name,
        purchases.quantity,
        purchases.unit_cost,
        purchases.total_cost,
        purchases.purchase_date
    FROM purchases
    LEFT JOIN products
        ON purchases.product_id = products.id
    LEFT JOIN suppliers
        ON purchases.supplier_id = suppliers.id
    ORDER BY purchases.id DESC
    """)

    rows = cur.fetchall()

    print("\n========== PURCHASES ==========")

    if not rows:
        print("No purchases found.")
        conn.close()
        return

    for row in rows:
        print("----------------------------------------")
        print(f"ID        : {row['id']}")
        print(f"Product   : {row['product_name']}")
        print(f"Supplier  : {row['supplier_name']}")
        print(f"Quantity  : {row['quantity']}")
        print(f"Unit Cost : ₦{row['unit_cost']:,.2f}")
        print(f"Total     : ₦{row['total_cost']:,.2f}")
        print(f"Date      : {row['purchase_date']}")

    conn.close()
def purchase_menu():
    while True:
        print("""
========== PURCHASES ==========
1. Record Purchase
2. View Purchases
0. Back
===============================
""")

        choice = input("Select option: ").strip()

        if choice == "1":
            record_purchase()

        elif choice == "2":
            view_purchases()

        elif choice == "0":
            break

        else:
            print("Invalid option.")


if __name__ == "__main__":
    purchase_menu()
