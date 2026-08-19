import sqlite3

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def money(value):
    return f"₦{float(value or 0):,.2f}"


def print_receipt(receipt_no):

    conn = get_connection()
    cur = conn.cursor()

    # ==========================================
    # RECEIPT
    # ==========================================

    cur.execute("""
        SELECT *
        FROM receipts
        WHERE receipt_no = ?
        LIMIT 1
    """, (receipt_no,))

    receipt = cur.fetchone()

    if receipt is None:
        print("\n❌ Receipt not found.")
        conn.close()
        return False

    # ==========================================
    # ITEMS
    # ==========================================

    cur.execute("""
        SELECT
            product_name,
            quantity,
            unit_price,
            line_total
        FROM receipt_items
        WHERE receipt_no = ?
        ORDER BY id
    """, (receipt_no,))

    items = cur.fetchall()

    # ==========================================
    # SALE INFORMATION
    # ==========================================

    cur.execute("""
        SELECT
            staff_name,
            payment_method,
            discount,
            vat,
            total_profit
        FROM sales
        WHERE receipt_no = ?
        LIMIT 1
    """, (receipt_no,))

    sale = cur.fetchone()

    if sale:
        staff_name = sale["staff_name"] or "Unknown"
        payment_method = sale["payment_method"] or "N/A"
        discount = sale["discount"] or 0
        vat = sale["vat"] or 0
        total_profit = sale["total_profit"] or 0
    else:
        staff_name = "Unknown"
        payment_method = "N/A"
        discount = 0
        vat = 0
        total_profit = 0

    customer_name = (
        receipt["customer_name"]
        or "Walk-in Customer"
    )

    subtotal = receipt["amount"] or 0
    total = receipt["total"] or 0

    # ==========================================
    # RECEIPT WIDTH
    # ==========================================

    W = 40

    print()
    print("=" * W)

    print("POS LEDGER NG".center(W))
    print("SMART BUSINESS MANAGEMENT".center(W))

    print("=" * W)

    print("SALES RECEIPT".center(W))

    print("-" * W)

    print(f"Receipt No : {receipt['receipt_no']}")
    print(f"Date       : {receipt['receipt_date']}")
    print(f"Customer   : {customer_name}")
    print(f"Staff      : {staff_name}")
    print(f"Payment    : {payment_method}")

    print("-" * W)

    # ==========================================
    # ITEMS
    # ==========================================

    print(
        f"{'ITEM':<18}"
        f"{'QTY':>4}"
        f"{'PRICE':>8}"
        f"{'TOTAL':>10}"
    )

    print("-" * W)

    for item in items:

        name = item["product_name"] or "Item"

        if len(name) > 18:
            name = name[:18]

        qty = float(item["quantity"] or 0)
        price = float(item["unit_price"] or 0)
        line_total = float(item["line_total"] or 0)

        print(
            f"{name:<18}"
            f"{qty:>4.0f}"
            f"{price:>8,.2f}"
            f"{line_total:>10,.2f}"
        )

    print("-" * W)

    # ==========================================
    # TOTALS
    # ==========================================

    print(f"{'Subtotal':<25}{money(subtotal):>15}")
    print(f"{'Discount':<25}{money(discount):>15}")
    print(f"{'VAT':<25}{money(vat):>15}")

    print("-" * W)

    print(f"{'TOTAL':<25}{money(total):>15}")

    print("-" * W)

    print(f"{'Profit':<25}{money(total_profit):>15}")

    print("=" * W)

    print("Thank you for your patronage!".center(W))
    print("POS Ledger NG - Nigeria".center(W))

    print("=" * W)

    conn.close()

    return True


if __name__ == "__main__":

    receipt_no = input(
        "Enter Receipt Number: "
    ).strip()

    print_receipt(receipt_no)
