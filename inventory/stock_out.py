from database.connection import get_connection


def stock_out():
    conn = get_connection()
    cur = conn.cursor()

    print("\n========== STOCK OUT (SALE) ==========\n")

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
Available Stock : {product['current_stock']}
Selling Price : ₦{product['selling_price']:.2f}
Average Cost : ₦{product['buying_price']:.2f}
""")

    qty = float(input("Quantity Sold: "))

    if qty <= 0:
        print("❌ Invalid quantity.")
        conn.close()
        return

    if qty > product["current_stock"]:
        print("❌ Not enough stock.")
        conn.close()
        return


    total_sale = qty * product["selling_price"]
    total_cost = qty * product["buying_price"]
    profit = total_sale - total_cost

    new_stock = product["current_stock"] - qty


    cur.execute("""
        UPDATE products
        SET current_stock = ?
        WHERE id = ?
    """, (
        new_stock,
        product["id"]
    ))


    cur.execute("""
        INSERT INTO inventory_movements
        (product_id, movement_type, quantity, reason)
        VALUES (?, 'OUT', ?, 'Product Sale')
    """, (
        product["id"],
        qty
    ))


    conn.commit()
    conn.close()


    print("\n========== SALE COMPLETED ==========")
    print(f"Product : {product['product_name']}")
    print(f"Quantity Sold : {qty}")
    print(f"Sales Amount : ₦{total_sale:.2f}")
    print(f"Cost Amount : ₦{total_cost:.2f}")
    print(f"Profit : ₦{profit:.2f}")
    print(f"Remaining Stock : {new_stock}")


if __name__ == "__main__":
    stock_out()
