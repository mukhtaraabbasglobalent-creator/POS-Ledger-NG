import sqlite3

DB_NAME = "data/posledger.db"

cart = []


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def find_cart_item(product_id):
    for item in cart:
        if item["product_id"] == product_id:
            return item
    return None


def add_to_cart():

    conn = get_connection()
    cur = conn.cursor()

    code = input("\nBarcode / Product ID: ").strip()

    cur.execute("""
        SELECT
            id,
            product_name,
            barcode,
            current_stock,
            buying_price,
            selling_price
        FROM products
        WHERE id = ?
           OR barcode = ?
    """, (code, code))

    product = cur.fetchone()

    if product is None:
        print("❌ Product not found.")
        conn.close()
        return

    print(f"\nProduct : {product['product_name']}")
    print(f"Stock   : {product['current_stock']}")
    print(f"Price   : ₦{product['selling_price']:,.2f}")

    try:
        qty = int(input("Quantity: "))
    except ValueError:
        print("❌ Invalid quantity.")
        conn.close()
        return

    if qty <= 0:
        print("❌ Quantity must be greater than zero.")
        conn.close()
        return

    if qty > product["current_stock"]:
        print("❌ Not enough stock.")
        conn.close()
        return

    existing = find_cart_item(product["id"])

    if existing:
        existing["quantity"] += qty
    else:
        cart.append({
            "product_id": product["id"],
            "product_name": product["product_name"],
            "sku": product["sku"],
            "buying_price": product["buying_price"],
            "selling_price": product["selling_price"],
            "quantity": qty
        })

    conn.close()

    print("✅ Added to cart.")
def remove_from_cart():

    if not cart:
        print("\n🛒 Cart is empty.")
        return

    view_cart()

    try:
        product_id = int(input("\nProduct ID to remove: "))
    except ValueError:
        print("❌ Invalid Product ID.")
        return

    item = find_cart_item(product_id)

    if item is None:
        print("❌ Product not found in cart.")
        return

    cart.remove(item)

    print("✅ Item removed from cart.")


def cart_total():

    total = 0
    profit = 0

    for item in cart:

        total += item["selling_price"] * item["quantity"]

        profit += (
            item["selling_price"] -
            item["buying_price"]
        ) * item["quantity"]

    return total, profit


def view_cart():

    if not cart:
        print("\n🛒 Cart is empty.")
        return

    print("\n========================================")
    print("              SHOPPING CART")
    print("========================================")

    for item in cart:

        subtotal = (
            item["selling_price"] *
            item["quantity"]
        )

        print(
            f"{item['product_id']} | "
            f"{item['product_name']}"
        )

        print(
            f"Qty : {item['quantity']}   "
            f"Price : ₦{item['selling_price']:,.2f}"
        )

        print(
            f"Subtotal : ₦{subtotal:,.2f}"
        )

        print("----------------------------------------")

    total, profit = cart_total()

    print(f"TOTAL  : ₦{total:,.2f}")
    print(f"PROFIT : ₦{profit:,.2f}")

    print("========================================")
from sales.checkout import checkout


def clear_cart():
    cart.clear()
    print("🗑️ Cart cleared.")


def cart_menu():

    while True:

        print("""
====================================
          SHOPPING CART
====================================
1. Add Product
2. View Cart
3. Remove Product
4. Checkout
5. Clear Cart
0. Back
====================================
""")

        choice = input("Select option: ").strip()

        if choice == "1":
            add_to_cart()

        elif choice == "2":
            view_cart()

        elif choice == "3":
            remove_from_cart()

        elif choice == "4":

            if not cart:
                print("🛒 Cart is empty.")
            else:
                checkout(cart)
                clear_cart()

        elif choice == "5":
            clear_cart()

        elif choice == "0":
            break

        else:
            print("❌ Invalid option.")


if __name__ == "__main__":
    cart_menu()
