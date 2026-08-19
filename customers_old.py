import sqlite3

DB_NAME = "data/posledger.db"


def add_customer():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    print("\n========== ADD CUSTOMER ==========")

    fullname = input("Full Name: ")
    phone = input("Phone Number: ")
    email = input("Email: ")
    address = input("Address: ")
    next_of_kin = input("Next of Kin: ")

    try:
        cur.execute("""
        INSERT INTO customers(
            fullname,
            phone,
            email,
            address,
            next_of_kin
        )
        VALUES(?,?,?,?,?)
        """, (
            fullname,
            phone,
            email,
            address,
            next_of_kin
        ))

        conn.commit()
        print("\nCustomer added successfully!")

    except sqlite3.IntegrityError:
        print("\nPhone number already exists!")

    conn.close()


def view_customers():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
    SELECT
        id,
        fullname,
        phone,
        email,
        address
    FROM customers
    ORDER BY fullname
    """)

    rows = cur.fetchall()

    print("\n========== CUSTOMER LIST ==========")

    if not rows:
        print("No customers found.")
    else:
        for row in rows:
            print(f"""
ID: {row[0]}
Name: {row[1]}
Phone: {row[2]}
Email: {row[3]}
Address: {row[4]}
----------------------------------------
""")

    conn.close()


def search_customer():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    keyword = input("\nEnter Name or Phone: ")

    cur.execute("""
    SELECT
        id,
        fullname,
        phone,
        email,
        address
    FROM customers
    WHERE fullname LIKE ?
       OR phone LIKE ?
    """, (
        "%" + keyword + "%",
        "%" + keyword + "%"
    ))

    rows = cur.fetchall()

    if not rows:
        print("\nCustomer not found.")
    else:
        for row in rows:
            print(f"""
ID: {row[0]}
Name: {row[1]}
Phone: {row[2]}
Email: {row[3]}
Address: {row[4]}
----------------------------------------
""")

    conn.close()


def edit_customer():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    customer_id = input("Customer ID: ")

    cur.execute(
        "SELECT * FROM customers WHERE id=?",
        (customer_id,)
    )

    row = cur.fetchone()

    if not row:
        print("Customer not found.")
        conn.close()
        return

    fullname = input(f"Full Name [{row[1]}]: ") or row[1]
    phone = input(f"Phone [{row[2]}]: ") or row[2]
    email = input(f"Email [{row[3]}]: ") or row[3]
    address = input(f"Address [{row[4]}]: ") or row[4]
    next_of_kin = input(f"Next of Kin [{row[5]}]: ") or row[5]

    cur.execute("""
    UPDATE customers
    SET
        fullname=?,
        phone=?,
        email=?,
        address=?,
        next_of_kin=?
    WHERE id=?
    """, (
        fullname,
        phone,
        email,
        address,
        next_of_kin,
        customer_id
    ))

    conn.commit()
    conn.close()

    print("\nCustomer updated successfully!")


def delete_customer():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    customer_id = input("Customer ID: ")

    cur.execute(
        "DELETE FROM customers WHERE id=?",
        (customer_id,)
    )

    conn.commit()
    conn.close()

    print("\nCustomer deleted successfully!")


def customer_menu():

    while True:

        print("""
====================================
        CUSTOMER MENU
====================================
1. Add Customer
2. View Customers
3. Search Customer
4. Edit Customer
5. Delete Customer
6. Back
====================================
""")

        choice = input("Select option: ")

        if choice == "1":
            add_customer()

        elif choice == "2":
            view_customers()

        elif choice == "3":
            search_customer()

        elif choice == "4":
            edit_customer()

        elif choice == "5":
            delete_customer()

        elif choice == "6":
            break

        else:
            print("Invalid option.")
