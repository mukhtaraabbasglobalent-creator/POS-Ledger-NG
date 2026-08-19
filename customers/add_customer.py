from database.connection import get_connection


def add_customer():

    conn = get_connection()
    cur = conn.cursor()

    print("\n====================================")
    print("          ADD CUSTOMER")
    print("====================================")

    fullname = input("Full Name : ").strip()
    phone = input("Phone     : ").strip()
    email = input("Email     : ").strip()
    address = input("Address   : ").strip()

    if fullname == "":
        print("\n❌ Customer name is required.")
        conn.close()
        return

    cur.execute("""
        INSERT INTO customers(
            fullname,
            phone,
            email,
            address
        )
        VALUES(?,?,?,?)
    """, (
        fullname,
        phone,
        email,
        address
    ))

    conn.commit()

    print("\n✅ Customer added successfully.")

    conn.close()

    input("\nPress Enter to continue...")
