from database.connection import get_connection


def view_customers():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            id,
            fullname,
            phone,
            email,
            address
        FROM customers
        ORDER BY fullname ASC
    """)

    rows = cur.fetchall()

    print("\n====================================")
    print("         CUSTOMER LIST")
    print("====================================")

    if not rows:
        print("No customers found.")
    else:
        for row in rows:
            print("------------------------------------")
            print(f"ID      : {row['id']}")
            print(f"Name    : {row['fullname']}")
            print(f"Phone   : {row['phone']}")
            print(f"Email   : {row['email']}")
            print(f"Address : {row['address']}")

    print("====================================")

    conn.close()

    input("\nPress Enter to continue...")
