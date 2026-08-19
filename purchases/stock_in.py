from datetime import datetime
from database.connection import get_connection


def stock_in():
    conn = get_connection()
    cur = conn.cursor()

    barcode = input("\nBarcode / SKU / Product Name: ").strip()

    cur.execute("""
        SELECT *
        FROM products
        WHERE barcode = ?
           OR sku = ?
           OR LOWER(product_name) = LOWER(?)
    """, (barcode, barcode, barcode))

    product = cur.fetchone()

    if not product:
        print("\n❌ Product not found.")
        conn.close()
        return

    print("\n========== PRODUCT ==========")
    print(f"Product : {product['product_name']}")
    print(f"Current Stock : {product['current_stock']}")
    print(f"Buying Price  : ₦{product['buying_price']:.2f}")

    qty = float(input("\nQuantity Purchased: "))
    buying_price = float(
        input("New Buying Price (ENTER same value if unchanged): ")
    )
    supplier = input("Supplier Name: ").strip()

    new_stock = product["current_stock"] + qty

    # Update product
    cur.execute("""
        UPDATE products
        SET current_stock = ?,
            buying_price = ?
        WHERE id = ?
    """, (
        new_stock,
        buying_price,
        product["id"]
    ))

    # Inventory movement
    cur.execute("""
        INSERT INTO inventory_movements(
            product_id,
            movement_type,
            quantity,
            balance_after,
            reference,
            remarks
        )
        VALUES(?,?,?,?,?,?)
    """, (
        product["id"],
        "STOCK_IN",
        qty,
        new_stock,
        supplier,
        "Stock Purchase"
    ))

    # Purchase history
    purchase_no = "PUR-" + datetime.now().strftime("%Y%m%d%H%M%S")
    total_cost = qty * buying_price

    cur.execute("""
        INSERT INTO purchases(
            purchase_no,
            supplier_name,
            product_id,
            quantity,
            buying_price,
            total_cost
        )
        VALUES(?,?,?,?,?,?)
    """, (
        purchase_no,
        supplier,
        product["id"],
        qty,
        buying_price,
        total_cost
    ))

    conn.commit()

    print("\n========== STOCK PURCHASED ==========")
    print(f"Product  : {product['product_name']}")
    print(f"Supplier : {supplier}")
    print(f"Quantity : {qty}")
    print(f"New Stock: {new_stock}")
    print(f"Cost     : ₦{buying_price:.2f}")
    print(f"Total Cost: ₦{total_cost:.2f}")
    print("✅ Stock updated successfully.")

    conn.close()


if __name__ == "__main__":
    stock_in()
