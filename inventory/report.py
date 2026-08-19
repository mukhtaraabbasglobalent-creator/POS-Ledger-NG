from database.connection import get_connection


def inventory_report():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            product_name,
            sku,
            barcode,
            current_stock,
            minimum_stock,
            buying_price,
            selling_price
        FROM products
        ORDER BY product_name
    """)

    rows = cur.fetchall()

    print("\n========== INVENTORY REPORT ==========")

    if not rows:
        print("No products found.")
        conn.close()
        return

    total_value = 0

    for row in rows:
        stock_value = row["current_stock"] * row["buying_price"]
        total_value += stock_value

        if row["current_stock"] <= row["minimum_stock"]:
            status = "⚠ LOW STOCK"
        else:
            status = "OK"

        print("-" * 50)
        print(f"Product       : {row['product_name']}")
        print(f"SKU           : {row['sku']}")
        print(f"Barcode       : {row['barcode']}")
        print(f"Current Stock : {row['current_stock']}")
        print(f"Minimum Stock : {row['minimum_stock']}")
        print(f"Buying Price  : ₦{row['buying_price']:.2f}")
        print(f"Selling Price : ₦{row['selling_price']:.2f}")
        print(f"Stock Value   : ₦{stock_value:.2f}")
        print(f"Status        : {status}")

    print("-" * 50)
    print(f"TOTAL INVENTORY VALUE : ₦{total_value:.2f}")

    conn.close()


if __name__ == "__main__":
    inventory_report()
