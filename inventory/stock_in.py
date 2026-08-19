from database.connection import get_connection


def stock_in():
    conn = get_connection()
    cur = conn.cursor()

    print("\n========== STOCK IN ==========\n")

    keyword = input("Enter Product Name, SKU or Barcode: ").strip()

    cur.execute("""
        SELECT *
        FROM products
        WHERE product_name LIKE ?
           OR sku LIKE ?
           OR barcode LIKE ?
    """, (
        f"%{keyword}%",
        f"%{keyword}%",
        f"%{keyword}%"
    ))

    product = cur.fetchone()

    if not product:
        print("❌ Product not found.")
        conn.close()
        return

    print(f"""
Product : {product['product_name']}
Current Stock : {product['current_stock']}
Current Buying Price : ₦{product['buying_price']:.2f}
Current Selling Price : ₦{product['selling_price']:.2f}
""")

    qty = float(input("Quantity Purchased: "))

    if qty <= 0:
        print("❌ Quantity must be greater than zero.")
        conn.close()
        return

    buying_price = float(input("Buying Price (₦): "))

    if buying_price <= 0:
        print("❌ Buying price must be greater than zero.")
        conn.close()
        return

    supplier = input("Supplier: ").strip()

    # Warning only (does not stop the transaction)
    if buying_price > product["selling_price"]:
        print("\n⚠️ WARNING!")
        print("Buying price is greater than the current selling price.")
        print("Selling at the current price may result in a loss.\n")

    old_stock = float(product["current_stock"])
    old_buying = float(product["buying_price"])

    new_stock = old_stock + qty

    # Weighted Average Cost
    if old_stock == 0:
        average_buying_price = buying_price
    else:
        average_buying_price = (
            (old_stock * old_buying) + (qty * buying_price)
        ) / new_stock

    cur.execute("""
        UPDATE products
        SET
            current_stock = ?,
            buying_price = ?
        WHERE id = ?
    """, (
        new_stock,
        average_buying_price,
        product["id"]
    ))

    cur.execute("""
        INSERT INTO inventory_movements
        (product_id, movement_type, quantity, reason)
        VALUES (?, 'IN', ?, ?)
    """, (
        product["id"],
        qty,
        f"Purchase from {supplier}"
    ))

    conn.commit()
    conn.close()

    print("\n========== STOCK UPDATED ==========")
    print(f"Previous Stock      : {old_stock}")
    print(f"Purchased Quantity  : {qty}")
    print(f"New Stock           : {new_stock}")
    print(f"Average Cost Price  : ₦{average_buying_price:.2f}")
    print("✅ Stock added successfully.")


if __name__ == "__main__":
    stock_in()
