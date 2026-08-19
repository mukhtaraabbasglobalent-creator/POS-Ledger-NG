import sqlite3

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def show_receipt(row):
    print("\n========================================")
    print("              RECEIPT FOUND")
    print("========================================")
    print(f"Receipt No : {row['receipt_no']}")
    print(f"Date       : {row['sale_date']}")
    print(f"Customer   : {row['customer_name'] or 'Walk-in Customer'}")
    print(f"Staff      : {row['staff_name'] or 'Unknown'}")
    print(f"Payment    : {row['payment_method'] or 'N/A'}")
    print("----------------------------------------")
    print(f"Amount     : ₦{row['total_amount']:,.2f}")
    print(f"Profit     : ₦{row['total_profit']:,.2f}")
    print(f"Status     : {row['status']}")
    print("========================================")


def search_receipts():
    conn = get_connection()
    cur = conn.cursor()

    while True:

        print("\n========================================")
        print("          RECEIPT SEARCH & HISTORY")
        print("========================================")
        print("1. Search Receipt Number")
        print("2. Search Product Name")
        print("3. Search Customer Name")
        print("4. Show Recent Receipts")
        print("0. Back")
        print("========================================")

        choice = input("Select option: ").strip()

        # ======================================
        # BACK
        # ======================================

        if choice == "0":
            break

        # ======================================
        # RECEIPT NUMBER
        # ======================================

        elif choice == "1":

            keyword = input(
                "\nEnter Receipt Number: "
            ).strip()

            if not keyword:
                continue

            cur.execute("""
                SELECT
                    s.id,
                    s.receipt_no,
                    s.sale_date,
                    s.staff_name,
                    s.payment_method,
                    s.total_amount,
                    s.total_profit,
                    s.status,
                    c.fullname AS customer_name
                FROM sales s
                LEFT JOIN customers c
                    ON s.customer_id = c.id
                WHERE LOWER(s.receipt_no) LIKE LOWER(?)
                ORDER BY s.id DESC
            """, (f"%{keyword}%",))

            rows = cur.fetchall()

            display_results(rows)

        # ======================================
        # PRODUCT NAME
        # ======================================

        elif choice == "2":

            keyword = input(
                "\nEnter Product Name: "
            ).strip()

            if not keyword:
                continue

            cur.execute("""
                SELECT DISTINCT
                    s.id,
                    s.receipt_no,
                    s.sale_date,
                    s.staff_name,
                    s.payment_method,
                    s.total_amount,
                    s.total_profit,
                    s.status,
                    c.fullname AS customer_name
                FROM sales s
                JOIN sale_items si
                    ON s.id = si.sale_id
                JOIN products p
                    ON si.product_id = p.id
                LEFT JOIN customers c
                    ON s.customer_id = c.id
                WHERE LOWER(p.product_name) LIKE LOWER(?)
                ORDER BY s.id DESC
            """, (f"%{keyword}%",))

            rows = cur.fetchall()

            display_results(rows)

        # ======================================
        # CUSTOMER NAME
        # ======================================

        elif choice == "3":

            keyword = input(
                "\nEnter Customer Name: "
            ).strip()

            if not keyword:
                continue

            cur.execute("""
                SELECT
                    s.id,
                    s.receipt_no,
                    s.sale_date,
                    s.staff_name,
                    s.payment_method,
                    s.total_amount,
                    s.total_profit,
                    s.status,
                    c.fullname AS customer_name
                FROM sales s
                LEFT JOIN customers c
                    ON s.customer_id = c.id
                WHERE LOWER(c.fullname) LIKE LOWER(?)
                ORDER BY s.id DESC
            """, (f"%{keyword}%",))

            rows = cur.fetchall()

            display_results(rows)

        # ======================================
        # RECENT RECEIPTS
        # ======================================

        elif choice == "4":

            cur.execute("""
                SELECT
                    s.id,
                    s.receipt_no,
                    s.sale_date,
                    s.staff_name,
                    s.payment_method,
                    s.total_amount,
                    s.total_profit,
                    s.status,
                    c.fullname AS customer_name
                FROM sales s
                LEFT JOIN customers c
                    ON s.customer_id = c.id
                ORDER BY s.id DESC
                LIMIT 20
            """)

            rows = cur.fetchall()

            display_results(rows)

        else:

            print("\n❌ Invalid option.")

    conn.close()


def display_results(rows):

    print("\n========================================")
    print("             SEARCH RESULTS")
    print("========================================")

    if not rows:
        print("No receipts found.")
        print("========================================")
        input("\nPress Enter to continue...")
        return

    for index, row in enumerate(rows, start=1):

        print("----------------------------------------")
        print(f"{index}. Receipt : {row['receipt_no']}")
        print(f"   Date       : {row['sale_date']}")
        print(
            f"   Customer   : "
            f"{row['customer_name'] or 'Walk-in Customer'}"
        )
        print(
            f"   Amount     : "
            f"₦{(row['total_amount'] or 0):,.2f}"
        )
        print(
            f"   Profit     : "
            f"₦{(row['total_profit'] or 0):,.2f}"
        )
        print(
            f"   Payment    : "
            f"{row['payment_method'] or 'N/A'}"
        )
        print(f"   Status     : {row['status']}")

    print("========================================")

    selection = input(
        "\nEnter result number to view receipt "
        "(0 to return): "
    ).strip()

    if selection == "0" or not selection:
        return

    try:
        number = int(selection)

        if number < 1 or number > len(rows):
            print("\n❌ Invalid result number.")
            return

        selected = rows[number - 1]

        show_receipt(selected)

        # ==================================
        # PRINT RECEIPT AGAIN
        # ==================================

        print("\n1. Print Receipt")
        print("0. Back")

        option = input("Select: ").strip()

        if option == "1":

            try:
                from sales.receipt import print_receipt

                print_receipt(
                    selected["receipt_no"]
                )

            except Exception as e:

                print(
                    f"\n❌ Unable to print receipt: {e}"
                )

    except ValueError:

        print("\n❌ Invalid selection.")


if __name__ == "__main__":
    search_receipts()
