from database.connection import get_connection


def purchase_history():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            p.purchase_no,
            s.product_name,
            p.supplier_name,
            p.quantity,
            p.buying_price,
            p.total_cost,
            p.purchase_date
        FROM purchases p
        JOIN products s
            ON p.product_id = s.id
        ORDER BY p.id DESC
    """)

    rows = cur.fetchall()

    print("\n========== PURCHASE HISTORY ==========")

    if not rows:
        print("No purchase records found.")
        conn.close()
        return

    grand_total = 0

    for row in rows:
        print("-" * 45)
        print(f"Purchase No : {row['purchase_no']}")
        print(f"Product     : {row['product_name']}")
        print(f"Supplier    : {row['supplier_name']}")
        print(f"Quantity    : {row['quantity']}")
        print(f"Unit Cost   : ₦{row['buying_price']:.2f}")
        print(f"Total Cost  : ₦{row['total_cost']:.2f}")
        print(f"Date        : {row['purchase_date']}")

        grand_total += row["total_cost"]

    print("-" * 45)
    print(f"Total Purchases Value : ₦{grand_total:.2f}")

    conn.close()


if __name__ == "__main__":
    purchase_history()
