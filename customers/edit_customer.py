from database.connection import get_connection


def edit_customer():

    conn = get_connection()
    cur = conn.cursor()

    customer_id = input("\nCustomer ID: ").strip()

    cur.execute(
        "SELECT * FROM customers WHERE id = ?",
        (customer_id,)
    )

    customer = cur.fetchone()

    if customer is None:
        print("\n❌ Customer not found.")
        conn.close()
        return

    print("\nLeave blank to keep current value.\n")

    fullname = input(f"Full Name [{customer['fullname']}]: ").strip()
    phone = input(f"Phone [{customer['phone']}]: ").strip()
    email = input(f"Email [{customer['email']}]: ").strip()
    address = input(f"Address [{customer['address']}]: ").strip()

    if fullname == "":
        fullname = customer["fullname"]

    if phone == "":
        phone = customer["phone"]

    if email == "":
        email = customer["email"]

    if address == "":
        address = customer["address"]

    cur.execute("""
        UPDATE customers
        SET
            fullname = ?,
            phone = ?,
            email = ?,
            address = ?
        WHERE id = ?
    """, (
        fullname,
        phone,
        email,
        address,
        customer_id
    ))

    conn.commit()

    print("\n✅ Customer updated successfully.")

    conn.close()

    input("\nPress Enter to continue...")
