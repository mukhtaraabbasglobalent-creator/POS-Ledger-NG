import sqlite3
from datetime import datetime

from staff.manage import current_user

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def generate_receipt_no(conn):

    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM receipts")

    count = cur.fetchone()[0] + 1

    return f"RCP{count:06d}"


def sell_product():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT
        id,
        product_name,
        selling_price,
        buying_price,
        current_stock
    FROM products
    ORDER BY product_name
    """)

    products = cur.fetchall()

    if not products:
        print("\n❌ No products available.")
        conn.close()
        return

    print("\n========== PRODUCTS ==========")

    for product in products:

        print(
            f"{product['id']}. "
            f"{product['product_name']} "
            f"(Stock: {product['current_stock']}) "
            f"₦{product['selling_price']:,.2f}"
        )

    try:

        product_id = int(input("\nProduct ID: "))
        qty = int(input("Quantity : "))

    except ValueError:

        print("❌ Invalid input.")
        conn.close()
        return

    cur.execute("""
    SELECT *
    FROM products
    WHERE id = ?
    """, (product_id,))

    product = cur.fetchone()

    if product is None:
        print("❌ Product not found.")
        conn.close()
        return

    if qty <= 0:
        print("❌ Quantity must be greater than zero.")
        conn.close()
        return

    if qty > product["current_stock"]:
        print("❌ Insufficient stock.")
        conn.close()
        return

    name = product["product_name"]
    buying = product["buying_price"]
    selling = product["selling_price"]

    total_amount = selling * qty
    total_profit = (selling - buying) * qty

    sale_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    user = current_user()

    if user:
        staff_name = user["fullname"]
    else:
        staff_name = "System"
    # Save sale
    cur.execute("""
    INSERT INTO sales(
        product_id,
        quantity,
        buying_price,
        selling_price,
        total_amount,
        total_profit,
        sale_date,
        staff_name
    )
    VALUES(?,?,?,?,?,?,?,?)
    """, (
        product_id,
        qty,
        buying,
        selling,
        total_amount,
        total_profit,
        sale_date,
        staff_name
    ))

    sale_id = cur.lastrowid

    # Generate receipt number
    receipt_no = generate_receipt_no(conn)

    # Save receipt
    cur.execute("""
    INSERT INTO receipts(
        receipt_no,
        sale_id,
        product_name,
        quantity,
        unit_price,
        total_amount,
        total_profit,
        receipt_date
    )
    VALUES(?,?,?,?,?,?,?,?)
    """, (
        receipt_no,
        sale_id,
        name,
        qty,
        selling,
        total_amount,
        total_profit,
        sale_date
    ))

    conn.commit()
    # Reduce stock
    cur.execute("""
    UPDATE products
    SET current_stock = current_stock - ?
    WHERE id = ?
    """, (
        qty,
        product_id
    ))

    # Record inventory movement (if table exists)
    try:

        cur.execute("""
        INSERT INTO inventory_movements(
            product_id,
            movement_type,
            quantity,
            reason,
            movement_date
        )
        VALUES (?, 'OUT', ?, 'Sale', ?)
        """, (
            product_id,
            qty,
            sale_date
        ))

    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()

    print("\n========== RECEIPT ==========")
    print(f"Receipt No : {receipt_no}")
    print(f"Cashier    : {staff_name}")
    print(f"Product    : {name}")
    print(f"Quantity   : {qty}")
    print(f"Unit Price : ₦{selling:,.2f}")
    print(f"Total      : ₦{total_amount:,.2f}")
    print(f"Profit     : ₦{total_profit:,.2f}")
    print(f"Date       : {sale_date}")
    print("=============================")
    print("✅ Sale completed successfully.")
def sales_menu():

    while True:

        print("""
====================================
            SALES MENU
====================================
1. Sell Product
2. Back
====================================
""")

        choice = input("Select option: ").strip()

        if choice == "1":
            sell_product()

        elif choice == "2":
            break

        else:
            print("❌ Invalid option.")


if __name__ == "__main__":
    sales_menu()
