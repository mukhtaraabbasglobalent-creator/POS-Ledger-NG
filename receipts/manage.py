from receipts.history import receipt_history
from receipts.reprint import reprint_receipt
from balance import update_cash_balance, update_wallet_balance
from audit import log_action


def refund_sale():

    conn = get_connection()
    cur = conn.cursor()

    receipt_no = input("\nReceipt Number: ").strip()

    cur.execute("""
        SELECT *
        FROM sales
        WHERE receipt_no = ?
    """, (receipt_no,))

    sale = cur.fetchone()

    if not sale:
        print("\n❌ Receipt not found.")
        conn.close()
        return

    if sale["status"] == "REFUNDED":
        print("\n❌ This sale has already been refunded.")
        conn.close()
        return

    cur.execute("""
        UPDATE products
        SET current_stock = current_stock + ?
        WHERE id = ?
    """, (
        sale["quantity"],
        sale["product_id"]
    ))

    conn.commit()

    log_action(
        "SYSTEM",
        "Refund",
        f"{sale['receipt_no']} refunded (₦{sale['total_amount']:,.2f})"
    )

    print("\n====================================")
    print("      REFUND SUCCESSFUL")
    print("====================================")
    print(f"Receipt : {sale['receipt_no']}")
    print(f"Amount  : ₦{sale['total_amount']:,.2f}")
    print(f"Stock   : Restored")
    print(f"Status  : REFUNDED")
    print("====================================")

    conn.close()

def receipt_menu():

    while True:

        print("""
====================================
          RECEIPT CENTER
====================================
1. Receipt History
2. Reprint Receipt
3. Refund Sale
0. Back
====================================
""")

        choice = input("Select option: ").strip()

        if choice == "1":
           from receipts.history import receipt_history
           receipt_history()

        elif choice == "2":
            reprint_receipt()

        elif choice == "3":
            refund_sale()

        elif choice == "0":
            break

        else:
            print("\n❌ Invalid option.")
def view_today_receipts():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            receipt_no,
            sale_date,
            payment_method,
            total_amount,
            staff_name
        FROM sales
        WHERE DATE(sale_date)=DATE('now','localtime')
        ORDER BY sale_date DESC
    """)

    rows = cur.fetchall()

    print("\n========== TODAY'S RECEIPTS ==========\n")

    if not rows:
        print("No receipts found today.")
        conn.close()
        return

    for row in rows:

        print("----------------------------------------")
        print(f"Receipt : {row['receipt_no']}")
        print(f"Date    : {row['sale_date']}")
        print(f"Cashier : {row['staff_name']}")
        print(f"Payment : {row['payment_method']}")
        print(f"Total   : ₦{row['total_amount']:,.2f}")

    conn.close()


if __name__ == "__main__":
    receipt_menu()
