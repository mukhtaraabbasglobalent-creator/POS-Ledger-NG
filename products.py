import sqlite3

DB_NAME = "data/posledger.db"


def add_product():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    print("\n========== ADD PRODUCT ==========\n")

    product_name = input("Product Name: ")
    sku = input("SKU: ")
    barcode = input("Barcode: ")
    category = input("Category: ")

    try:
        buying_price = float(input("Buying Price (₦): "))
        selling_price = float(input("Selling Price (₦): "))
        stock = float(input("Opening Stock: "))
        minimum_stock = float(input("Minimum Stock: "))
    except ValueError:
        print("Invalid number entered.")
        conn.close()
        return

    unit = input("Unit (EA, KG, PCS, LTR): ").upper()
    if unit == "":
        unit = "EA"

    try:
        cur.execute("""
        INSERT INTO products
        (
            product_name,
            sku,
            barcode,
            category,
            buying_price,
            selling_price,
            current_stock,
            minimum_stock,
            unit
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            product_name,
            sku,
            barcode,
            category,
            buying_price,
            selling_price,
            stock,
            minimum_stock,
            unit
        ))

        conn.commit()
        print("\nProduct added successfully!")

    except sqlite3.IntegrityError:
        print("\nSKU or Barcode already exists.")

    conn.close()


def view_products():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
    SELECT
        id,
        product_name,
        sku,
        category,
        selling_price,
        current_stock,
        unit
    FROM products
    ORDER BY product_name
    """)

    rows = cur.fetchall()

    print("\n========== PRODUCT LIST ==========\n")

    if not rows:
        print("No products found.")
        conn.close()
        return

    for row in rows:
        print(f"""
ID       : {row[0]}
Name     : {row[1]}
SKU      : {row[2]}
Category : {row[3]}
Price    : ₦{row[4]:,.2f}
Stock    : {row[5]} {row[6]}
----------------------------------------
""")

    conn.close()


def search_product():
    keyword = input("Enter Product Name or SKU: ")

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
    SELECT
        product_name,
        sku,
        category,
        selling_price,
        current_stock
    FROM products
    WHERE product_name LIKE ?
       OR sku LIKE ?
    """, (f"%{keyword}%", f"%{keyword}%"))

    rows = cur.fetchall()

    if not rows:
        print("Product not found.")
    else:
        for row in rows:
            print(row)

    conn.close()


def delete_product():
    product_id = input("Enter Product ID: ")

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("DELETE FROM products WHERE id=?", (product_id,))
    conn.commit()

    if cur.rowcount:
        print("Product deleted successfully.")
    else:
        print("Product not found.")

    conn.close()


def product_menu():
    while True:
        print("""
====================================
          PRODUCTS MENU
====================================
1. Add Product
2. View Products
3. Search Product
4. Delete Product
5. Back
====================================
""")

        choice = input("Select option: ")

        if choice == "1":
            add_product()
        elif choice == "2":
            view_products()
        elif choice == "3":
            search_product()
        elif choice == "4":
            delete_product()
        elif choice == "5":
            break
        else:
            print("Invalid option.")
