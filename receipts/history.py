import sqlite3

DB_NAME = "data/posledger.db"


def receipt_history():

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT
            receipt_no,
            sale_date,
            staff_name,
            total_amount,
            payment_method,
            status
        FROM sales
        ORDER BY id DESC
        LIMIT 20
    """)

    rows = cur.fetchall()

    print("\n====================================")
    print("        RECEIPT HISTORY")
    print("====================================")

    if not rows:
        print("No receipts found.")
    else:
        for row in rows:
            print("------------------------------------")
            print(f"Receipt : {row['receipt_no']}")
            print(f"Amount  : ₦{row['total_amount']:,.2f}")
            print(f"Payment : {row['payment_method']}")
            print(f"Status  : {row['status']}")
            print(f"Staff   : {row['staff_name']}")
            print(f"Date    : {row['sale_date']}")

    print("====================================")

    conn.close()

    input("\nPress Enter to continue...")
