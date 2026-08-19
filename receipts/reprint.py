from database.connection import get_connection


def reprint_receipt():

    conn = get_connection()
    conn.row_factory = None
    cur = conn.cursor()

    receipt_no = input("\nReceipt Number: ").strip()

    cur.execute("""
        SELECT
            receipt_no,
            transaction_type,
            total,
            receipt_date
        FROM receipts
        WHERE receipt_no = ?
    """, (receipt_no,))

    receipt = cur.fetchone()

    if not receipt:
        print("\n❌ Receipt not found.")
        conn.close()
        return

    cur.execute("""
        SELECT
            product_name,
            quantity,
            unit_price,
            line_total
        FROM receipt_items
        WHERE receipt_no = ?
    """, (receipt_no,))

    items = cur.fetchall()
    print("\n========================================")
    print("           POS LEDGER NG")
    print("========================================")
    print(f"Receipt No : {receipt[0]}")
    print(f"Type       : {receipt[1]}")
    print(f"Date       : {receipt[3]}")
    print("----------------------------------------")

    total_items = 0

    for item in items:

        print(item[0])
        print(
            f"  {item[1]} x ₦{item[2]:,.2f}"
            f" = ₦{item[3]:,.2f}"
        )

        total_items += item[1]

    print("----------------------------------------")
    print(f"Items      : {total_items}")
    print(f"TOTAL      : ₦{receipt[2]:,.2f}")
    print("========================================")
    print("Thank you for your patronage.")
    print("========================================")

    conn.close()


if __name__ == "__main__":
    reprint_receipt()
