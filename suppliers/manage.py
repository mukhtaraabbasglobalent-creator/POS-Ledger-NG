import sqlite3

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def create_table():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS suppliers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        supplier_name TEXT NOT NULL,
        phone TEXT,
        email TEXT,
        address TEXT
    )
    """)

    conn.commit()
    conn.close()


create_table()


def add_supplier():
    conn = get_connection()
    cur = conn.cursor()

    print("\n========== ADD SUPPLIER ==========")

    supplier_name = input("Supplier Name : ").strip()
    phone = input("Phone         : ").strip()
    email = input("Email         : ").strip()
    address = input("Address       : ").strip()

    if supplier_name == "":
        print("Supplier name cannot be empty.")
        conn.close()
        return

    cur.execute("""
    INSERT INTO suppliers(
        supplier_name,
        phone,
        email,
        address
    )
    VALUES(?,?,?,?)
    """, (
        supplier_name,
        phone,
        email,
        address
    ))

    conn.commit()
    conn.close()

    print("Supplier added successfully.")
def view_suppliers():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT
        id,
        supplier_name,
        phone,
        email,
        address
    FROM suppliers
    ORDER BY id DESC
    """)

    rows = cur.fetchall()

    print("\n========== SUPPLIERS ==========")

    if not rows:
        print("No suppliers found.")
        conn.close()
        return

    for row in rows:
        print("----------------------------------------")
        print(f"ID        : {row['id']}")
        print(f"Supplier  : {row['supplier_name']}")
        print(f"Phone     : {row['phone']}")
        print(f"Email     : {row['email']}")
        print(f"Address   : {row['address']}")

    conn.close()


def search_supplier():
    conn = get_connection()
    cur = conn.cursor()

    keyword = input("\nSupplier Name/Phone: ").strip().lower()

    cur.execute("""
    SELECT *
    FROM suppliers
    WHERE LOWER(supplier_name) LIKE ?
       OR phone LIKE ?
    """, (
        f"%{keyword}%",
        f"%{keyword}%"
    ))

    rows = cur.fetchall()

    print("\n========== SEARCH RESULT ==========")

    if not rows:
        print("Supplier not found.")
        conn.close()
        return

    for row in rows:
        print("----------------------------------------")
        print(f"ID        : {row['id']}")
        print(f"Supplier  : {row['supplier_name']}")
        print(f"Phone     : {row['phone']}")
        print(f"Email     : {row['email']}")
        print(f"Address   : {row['address']}")

    conn.close()
def supplier_menu():
    while True:
        print("""
========== SUPPLIERS ==========
1. Add Supplier
2. View Suppliers
3. Search Supplier
0. Back
===============================
""")

        choice = input("Select option: ").strip()

        if choice == "1":
            add_supplier()

        elif choice == "2":
            view_suppliers()

        elif choice == "3":
            search_supplier()

        elif choice == "0":
            break

        else:
            print("Invalid option.")


if __name__ == "__main__":
    supplier_menu()
