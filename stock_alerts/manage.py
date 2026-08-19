import sqlite3

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_min_stock_column():
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            "ALTER TABLE products ADD COLUMN min_stock REAL DEFAULT 5"
        )
        conn.commit()
    except sqlite3.OperationalError:
        pass

    conn.close()


ensure_min_stock_column()


def view_low_stock():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            id,
            product_name,
            barcode,
            current_stock,
            min_stock
        FROM products
        WHERE current_stock <= min_stock
        ORDER BY current_stock ASC
    """)

    rows = cur.fetchall()

    print("\n========== LOW STOCK ALERTS ==========")

    if not rows:
        print("No low-stock products.")
        conn.close()
        return

    for row in rows:
        print("--------------------------------------")
        print(f"ID         : {row['id']}")
        print(f"Product    : {row['product_name']}")
        print(f"Barcode    : {row['barcode']}")
        print(f"Stock Left : {row['current_stock']}")
        print(f"Minimum    : {row['min_stock']}")

    conn.close()


def update_min_stock():
    conn = get_connection()
    cur = conn.cursor()

    try:
        product_id = int(input("\nProduct ID: "))
        min_stock = float(input("New Minimum Stock: "))
    except ValueError:
        print("Invalid input.")
        conn.close()
        return

    cur.execute(
        "SELECT product_name FROM products WHERE id=?",
        (product_id,)
    )

    product = cur.fetchone()

    if product is None:
        print("Product not found.")
        conn.close()
        return

    cur.execute("""
        UPDATE products
        SET min_stock=?
        WHERE id=?
    """, (min_stock, product_id))

    conn.commit()

    print(f"\nMinimum stock updated for {product['product_name']}.")

    conn.close()


def check_low_stock():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            product_name,
            current_stock,
            min_stock
        FROM products
        WHERE current_stock <= min_stock
        ORDER BY current_stock ASC
    """)

    rows = cur.fetchall()

    if rows:
        print("\n========== LOW STOCK WARNING ==========")

        for row in rows:
            print("--------------------------------------")
            print(f"⚠ Product : {row['product_name']}")
            print(f"Stock Left: {row['current_stock']}")
            print(f"Minimum   : {row['min_stock']}")
            print("STATUS    : RESTOCK REQUIRED")

        print("=======================================")

    conn.close()


def stock_alert_menu():
    while True:

        print("""
========== STOCK ALERTS ==========
1. View Low Stock
2. Update Minimum Stock
0. Back
==================================
""")

        choice = input("Select option: ").strip()

        if choice == "1":
            view_low_stock()

        elif choice == "2":
            update_min_stock()

        elif choice == "0":
            break

        else:
            print("Invalid option.")


if __name__ == "__main__":
    stock_alert_menu()
