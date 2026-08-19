from database.connection import get_connection


def low_stock_report():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            product_name,
            sku,
            barcode,
            current_stock,
            minimum_stock
        FROM products
        WHERE current_stock <= minimum_stock
        ORDER BY current_stock ASC
    """)

    rows = cur.fetchall()

    print("\n========== LOW STOCK ALERTS ==========")

    if not rows:
        print("\n✅ Great! No products are below the minimum stock level.")
        conn.close()
        return

    for row in rows:
        shortage = row["minimum_stock"] - row["current_stock"]

        print("----------------------------------------")
        print(f"Product       : {row['product_name']}")
        print(f"SKU           : {row['sku']}")
        print(f"Barcode       : {row['barcode']}")
        print(f"Current Stock : {row['current_stock']}")
        print(f"Minimum Stock : {row['minimum_stock']}")
        print(f"Restock Qty   : {shortage}")

    print("----------------------------------------")
    print(f"⚠ Total Low Stock Products: {len(rows)}")

    conn.close()


if __name__ == "__main__":
    low_stock_report()
