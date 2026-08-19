from database.connection import get_connection


def delete_customer():

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

    print("\nCustomer Found")
    print("----------------------------")
    print(f"Name : {customer['fullname']}")
    print(f"Phone: {customer['phone']}")

    confirm = input("\nDelete this customer? (Y/N): ").strip().upper()

    if confirm != "Y":
        print("\nCancelled.")
        conn.close()
        return

    cur.execute(
        "DELETE FROM customers WHERE id = ?",
        (customer_id,)
    )

    conn.commit()

    print("\n✅ Customer deleted successfully.")

    conn.close()

    input("\nPress Enter to continue...")
