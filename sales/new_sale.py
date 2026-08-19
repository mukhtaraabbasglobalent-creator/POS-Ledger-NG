import sqlite3
from datetime import datetime

from balance import update_cash_balance, update_wallet_balance
from audit import log_action
from staff.manage import current_user
from sales.checkout import checkout

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def select_customer(conn):
    print("\n====================================")
    print("             CUSTOMER")
    print("====================================")
    print("0. Walk-in Customer")
    print("1. Select Customer")
    print("====================================")

    choice = input("Select: ").strip()

    if choice == "0" or choice == "":
        return None

    if choice != "1":
        print("❌ Invalid choice.")
        return None

    cur = conn.cursor()

    cur.execute("""
        SELECT id, fullname, phone
        FROM customers
        ORDER BY fullname
    """)

    customers = cur.fetchall()

    if not customers:
        print("\nNo customers registered.")
        return None

    print("\n====================================")
    print("          CUSTOMER LIST")
    print("====================================")

    for customer in customers:
        print(
            f"{customer['id']}. "
            f"{customer['fullname']} "
            f"({customer['phone'] or 'No phone'})"
        )

    print("0. Walk-in Customer")
    print("====================================")

    customer_id = input("Customer ID: ").strip()

    if customer_id == "0" or customer_id == "":
        return None

    try:
        customer_id = int(customer_id)
    except ValueError:
        print("❌ Invalid customer ID.")
        return None

    cur.execute("""
        SELECT id, fullname, phone
        FROM customers
        WHERE id = ?
    """, (customer_id,))

    customer = cur.fetchone()

    if customer is None:
        print("❌ Customer not found.")
        return None

    print("\nCustomer selected:")
    print(f"Name  : {customer['fullname']}")
    print(f"Phone : {customer['phone'] or 'N/A'}")

    return customer["id"]


def new_sale():

    conn = get_connection()
    cur = conn.cursor()

    print("\n====================================")
    print("             NEW SALE")
    print("====================================")

    code = input(
        "Barcode / Product ID / Product Name: "
    ).strip()

    if not code:
        print("❌ Product code cannot be empty.")
        conn.close()
        return

    cur.execute("""
        SELECT
            id,
            product_name,
            sku,
            barcode,
            current_stock,
            buying_price,
            selling_price
        FROM products
        WHERE CAST(id AS TEXT) = ?
           OR sku = ?
           OR barcode = ?
           OR LOWER(product_name) LIKE LOWER(?)
        ORDER BY id
        LIMIT 1
    """, (
        code,
        code,
        code,
        f"%{code}%"
    ))

    product = cur.fetchone()

    if product is None:
        print("\n❌ Product not found.")
        conn.close()
        return

    print("\n====================================")
    print("          PRODUCT FOUND")
    print("====================================")
    print(f"Product : {product['product_name']}")
    print(f"SKU     : {product['sku']}")
    print(f"Stock   : {product['current_stock']}")
    print(f"Price   : ₦{product['selling_price']:,.2f}")
    print("====================================")

    try:
        qty = float(input("Quantity: ").strip())
    except ValueError:
        print("❌ Invalid quantity.")
        conn.close()
        return

    if qty <= 0:
        print("❌ Quantity must be greater than zero.")
        conn.close()
        return

    if qty > product["current_stock"]:
        print("\n❌ Not enough stock.")
        print(
            f"Available Stock: "
            f"{product['current_stock']}"
        )
        conn.close()
        return

    total = qty * product["selling_price"]

    profit = qty * (
        product["selling_price"] -
        product["buying_price"]
    )

    print("\n====================================")
    print(f"Total  : ₦{total:,.2f}")
    print(f"Profit : ₦{profit:,.2f}")
    print("====================================")

    customer_id = select_customer(conn)

    staff = current_user()

    if staff is None:
        print("\n❌ No staff is currently logged in.")
        conn.close()
        return

    staff_name = staff["fullname"]

    # Build cart for checkout
    cart = [{
        "product_id": product["id"],
        "product_name": product["product_name"],
        "quantity": qty,
        "buying_price": product["buying_price"],
        "selling_price": product["selling_price"],
        "customer_id": customer_id,
        "staff_name": staff_name
    }]

    conn.close()

    # Send sale to the centralized checkout system
    result = checkout(cart)

    if result:
        print("\n✅ Sale completed successfully.")

    else:
        print("\n❌ Sale was not completed.")


if __name__ == "__main__":
    new_sale()
