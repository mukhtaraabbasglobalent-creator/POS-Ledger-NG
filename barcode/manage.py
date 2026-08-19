import sqlite3

DB_NAME = "data/posledger.db"


def generate_barcode():

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT id
        FROM products
        WHERE barcode IS NULL
           OR barcode = ''
        ORDER BY id
    """)

    rows = cur.fetchall()

    if not rows:
        print("\n✅ All products already have barcodes.")
        conn.close()
        input("\nPress Enter to continue...")
        return

    for row in rows:
        barcode = f"PLN-{row['id']:08d}"

        cur.execute("""
            UPDATE products
            SET barcode = ?
            WHERE id = ?
        """, (barcode, row["id"]))

    conn.commit()

    print(f"\n✅ {len(rows)} barcode(s) generated successfully.")

    conn.close()

    input("\nPress Enter to continue...")


def search_barcode():
    print("\n🚧 Search by Barcode (Coming Soon)")
    input("\nPress Enter to continue...")


def search_barcode():

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    barcode = input("\nEnter Barcode: ").strip()

    cur.execute("""
        SELECT *
        FROM products
        WHERE barcode = ?
    """, (barcode,))

    row = cur.fetchone()

    if row is None:
        print("\n❌ Product not found.")

    else:
        print("\n====================================")
        print("         PRODUCT FOUND")
        print("====================================")
        print(f"Name      : {row['product_name']}")
        print(f"SKU       : {row['sku']}")
        print(f"Barcode   : {row['barcode']}")
        print(f"Category  : {row['category']}")
        print(f"Buying    : ₦{row['buying_price']:,.2f}")
        print(f"Selling   : ₦{row['selling_price']:,.2f}")
        print(f"Stock     : {row['current_stock']}")
        print("====================================")

    conn.close()

    input("\nPress Enter to continue...")


def barcode_settings():
    print("\n🚧 Barcode Settings (Coming Soon)")
    input("\nPress Enter to continue...")


def barcode_menu():

    while True:

        print("""
====================================
       BARCODE MANAGEMENT
====================================
1. Generate Barcode
2. Search by Barcode
3. Print Barcode
4. Barcode Settings
0. Back
====================================
""")

        choice = input("Select option: ").strip()

        if choice == "1":
            generate_barcode()

        elif choice == "2":
            search_barcode()

        elif choice == "3":
            print_barcode()

        elif choice == "4":
            barcode_settings()

        elif choice == "0":
            break

        else:
            print("\n❌ Invalid option.")


if __name__ == "__main__":
    barcode_menu()
