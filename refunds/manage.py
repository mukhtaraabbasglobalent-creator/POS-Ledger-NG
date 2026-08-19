import sqlite3
from datetime import datetime

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def list_completed_sales():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            s.id,
            s.product_id,
            p.product_name,
            s.quantity,
            s.selling_price,
            s.total_amount,
            s.total_profit,
            s.sale_date,
            s.staff_name,
            s.receipt_no,
            s.payment_method
        FROM sales s
        LEFT JOIN products p
            ON s.product_id = p.id
        WHERE s.status = 'COMPLETED'
        ORDER BY s.id DESC
    """)

    rows = cur.fetchall()

    print("\n====================================")
    print("        COMPLETED SALES")
    print("====================================")

    if not rows:
        print("No completed sales found.")
        conn.close()
        input("\nPress Enter to continue...")
        return

    for row in rows:
        print("------------------------------------")
        print(f"Sale ID       : {row['id']}")
        print(f"Product       : {row['product_name'] or 'Unknown'}")
        print(f"Quantity      : {row['quantity']}")
        print(f"Selling Price : ₦{row['selling_price']:,.2f}")
        print(f"Amount        : ₦{row['total_amount']:,.2f}")
        print(f"Profit        : ₦{row['total_profit']:,.2f}")
        print(f"Date          : {row['sale_date']}")
        print(f"Staff         : {row['staff_name'] or 'Unknown'}")
        print(f"Receipt       : {row['receipt_no'] or 'N/A'}")
        print(f"Payment       : {row['payment_method'] or 'N/A'}")

    print("====================================")

    conn.close()
    input("\nPress Enter to continue...")


def refund_sale():
    conn = get_connection()
    cur = conn.cursor()

    try:
        sale_id = int(input("\nEnter Sale ID to refund: ").strip())
    except ValueError:
        print("\n❌ Invalid Sale ID.")
        conn.close()
        input("\nPress Enter to continue...")
        return

    cur.execute("""
        SELECT
            s.id,
            s.product_id,
            s.quantity,
            s.buying_price,
            s.selling_price,
            s.total_amount,
            s.total_profit,
            s.sale_date,
            s.staff_name,
            s.receipt_no,
            s.payment_method,
            s.status,
            p.product_name
        FROM sales s
        LEFT JOIN products p
            ON s.product_id = p.id
        WHERE s.id = ?
    """, (sale_id,))

    sale = cur.fetchone()

    if sale is None:
        print("\n❌ Sale not found.")
        conn.close()
        input("\nPress Enter to continue...")
        return

    if sale["status"] != "COMPLETED":
        print(f"\n❌ This sale cannot be refunded.")
        print(f"Current status: {sale['status']}")
        conn.close()
        input("\nPress Enter to continue...")
        return

    print("\n====================================")
    print("          REFUND SALE")
    print("====================================")
    print(f"Sale ID       : {sale['id']}")
    print(f"Product       : {sale['product_name'] or 'Unknown'}")
    print(f"Quantity      : {sale['quantity']}")
    print(f"Amount        : ₦{sale['total_amount']:,.2f}")
    print(f"Profit        : ₦{sale['total_profit']:,.2f}")
    print(f"Date          : {sale['sale_date']}")
    print("====================================")

    confirm = input("Confirm full refund? (Y/N): ").strip().upper()

    if confirm != "Y":
        print("\nRefund cancelled.")
        conn.close()
        input("\nPress Enter to continue...")
        return

    try:
        conn.execute("BEGIN")

        # Restore stock
        cur.execute("""
            UPDATE products
            SET current_stock = current_stock + ?
            WHERE id = ?
        """, (
            sale["quantity"],
            sale["product_id"]
        ))

        if cur.rowcount == 0:
            raise Exception("Product not found while restoring stock.")

        # Mark sale as refunded
        cur.execute("""
            UPDATE sales
            SET status = 'REFUNDED'
            WHERE id = ?
              AND status = 'COMPLETED'
        """, (sale_id,))

        if cur.rowcount != 1:
            raise Exception("Sale status could not be updated.")

        conn.commit()

        print("\n====================================")
        print("       REFUND SUCCESSFUL")
        print("====================================")
        print(f"Sale ID       : {sale['id']}")
        print(f"Product       : {sale['product_name'] or 'Unknown'}")
        print(f"Stock Restored: {sale['quantity']}")
        print(f"Refund Amount : ₦{sale['total_amount']:,.2f}")
        print(f"Profit Reversed: ₦{sale['total_profit']:,.2f}")
        print(f"Date          : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("====================================")

    except Exception as e:
        conn.rollback()
        print("\n❌ Refund failed.")
        print(f"Reason: {e}")

    finally:
        conn.close()

    input("\nPress Enter to continue...")


def refund_menu():

    while True:

        print("""
====================================
          REFUND MANAGEMENT
====================================
1. View Completed Sales
2. Refund Sale
0. Back
====================================
""")

        choice = input("Select option: ").strip()

        if choice == "1":
            list_completed_sales()

        elif choice == "2":
            refund_sale()

        elif choice == "0":
            break

        else:
            print("\n❌ Invalid option.")


if __name__ == "__main__":
    refund_menu()
