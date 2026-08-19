import sqlite3

DB_NAME = "data/posledger.db"


def stock_in():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    print("\n========== STOCK IN ==========\n")

    sku = input("Enter Product SKU: ")

    cur.execute("""
        SELECT id, product_name, current_stock
        FROM products
        WHERE sku=?
    """, (sku,))

    product = cur.fetchone()

    if product is None:
        print("Product not found.")
        conn.close()
        return

    print(f"Product : {product[1]}")
    print(f"Current Stock : {product[2]}")

    try:
        qty = float(input("Quantity to Add: "))
    except ValueError:
        print("Invalid quantity.")
        conn.close()
        return

    new_stock = product[2] + qty

    cur.execute("""
        UPDATE products
        SET current_stock=?
        WHERE id=?
    """, (new_stock, product[0]))

    conn.commit()
    conn.close()

    print(f"\nStock updated successfully.")
    print(f"New Stock: {new_stock}")


def stock_out():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    print("\n========== STOCK OUT ==========\n")

    sku = input("Enter Product SKU: ")

    cur.execute("""
        SELECT id, product_name, current_stock
        FROM products
        WHERE sku=?
    """, (sku,))

    product = cur.fetchone()

    if product is None:
        print("Product not found.")
        conn.close()
        return

    print(f"Product : {product[1]}")
    print(f"Current Stock : {product[2]}")

    try:
        qty = float(input("Quantity to Remove: "))
    except ValueError:
        print("Invalid quantity.")
        conn.close()
        return

    if qty > product[2]:
        print("Insufficient stock.")
        conn.close()
        return

    new_stock = product[2] - qty

    cur.execute("""
        UPDATE products
        SET current_stock=?
        WHERE id=?
    """, (new_stock, product[0]))

    conn.commit()
    conn.close()

    print("\nStock updated successfully.")
    print(f"Remaining Stock: {new_stock}")


def view_inventory():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        SELECT
            product_name,
            sku,
            current_stock,
            minimum_stock,
            unit
        FROM products
        ORDER BY product_name
    """)

    rows = cur.fetchall()

    print("\n========== INVENTORY ==========\n")

    for row in rows:
        print(f"""
Product : {row[0]}
SKU     : {row[1]}
Stock   : {row[2]} {row[4]}
Minimum : {row[3]}
------------------------------
""")

    conn.close()


def inventory_menu():
    while True:
        print("""
====================================
        INVENTORY MENU
====================================
1. Stock In
2. Stock Out
3. View Inventory
4. Back
====================================
""")

        choice = input("Select option: ")

        if choice == "1":
            stock_in()

        elif choice == "2":
            stock_out()

        elif choice == "3":
            view_inventory()

        elif choice == "4":
            break

        else:
            print("Invalid option.")
