import sqlite3

DB_NAME = "data/posledger.db"


def connect():
    return sqlite3.connect(DB_NAME)


def stock_purchase():
    conn = connect()
    cur = conn.cursor()

    print("\n====== STOCK PURCHASE ======\n")

    # Show products
    cur.execute("""
        SELECT id, product_name, current_stock, buying_price
        FROM products
        ORDER BY product_name
    """)

    products = cur.fetchall()

    if not products:
        print("No products found.")
        conn.close()
        return

    print("Available Products")
    print("-" * 50)

    for p in products:
        print(f"{p[0]}. {p[1]} | Stock: {p[2]} | Cost: ₦{p[3]:.2f}")

    print("-" * 50)

    product_id = int(input("Enter Product ID: "))
    quantity = float(input("Quantity Purchased: "))
    buying_price = float(input("Buying Price (₦): "))
    supplier = input("Supplier: ")

    # Save purchase
    cur.execute("""
        INSERT INTO stock_purchases
        (product_id, quantity, buying_price, purchase_date)
        VALUES (?, ?, ?, datetime('now'))
    """, (
        product_id,
        quantity,
        buying_price
    ))

    # Update stock
    cur.execute("""
        UPDATE products
        SET current_stock = current_stock + ?,
            buying_price = ?
        WHERE id = ?
    """, (
        quantity,
        buying_price,
        product_id
    ))

    # Inventory movement
    cur.execute("""
        INSERT INTO inventory_movements
        (product_id, movement_type, quantity, reason)
        VALUES (?, 'IN', ?, 'Purchase')
    """, (
        product_id,
        quantity
    ))

    conn.commit()
    conn.close()

    print("\n✅ Stock updated successfully.")
    print(f"Added {quantity} units to stock.")


if __name__ == "__main__":
    stock_purchase()
