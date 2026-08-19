from database.connection import get_connection


def search_customer():

    conn = get_connection()
    cur = conn.cursor()

    keyword = input("\nCustomer Name or Phone: ").strip()

    cur.execute("""
        SELECT
            id,
            fullname,
            phone,
            email,
            address
        FROM customers
        WHERE LOWER(fullname) LIKE LOWER(?)
           OR phone LIKE ?
        ORDER BY fullname
    """, (
        f"%{keyword}%",
        f"%{keyword}%"
    ))

    rows = cur.fetchall()

    print("\n====================================")
    print("        SEARCH RESULTS")
    print("====================================")

    if not rows:
        print("No customer found.")
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
