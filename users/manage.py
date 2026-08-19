from database.connection import get_connection


def list_users():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, fullname,
               COALESCE(role,'Cashier') AS role,
               created_at
        FROM users
        ORDER BY id
    """)

    rows = cur.fetchall()

    print("\n========== USERS ==========")

    if not rows:
        print("No users found.")
        conn.close()
        return

    for row in rows:
        print("-" * 40)
        print(f"ID      : {row['id']}")
        print(f"Name    : {row['fullname']}")
        print(f"Role    : {row['role']}")
        print(f"Created : {row['created_at']}")

    conn.close()


def change_role():
    conn = get_connection()
    cur = conn.cursor()

    user_id = input("\nUser ID: ").strip()

    print("\nRoles")
    print("1. Administrator")
    print("2. Manager")
    print("3. Cashier")

    choice = input("\nSelect Role: ").strip()

    roles = {
        "1": "Administrator",
        "2": "Manager",
        "3": "Cashier"
    }

    if choice not in roles:
        print("Invalid role.")
        conn.close()
        return

    cur.execute(
        "UPDATE users SET role=? WHERE id=?",
        (roles[choice], user_id)
    )

    conn.commit()

    if cur.rowcount == 0:
        print("User not found.")
    else:
        print("\n✅ Role updated successfully.")

    conn.close()


def user_menu():
    while True:
        print("\n========== USER MANAGEMENT ==========")
        print("1. View Users")
        print("2. Change User Role")
        print("0. Back")

        choice = input("\nSelect: ").strip()

        if choice == "1":
            list_users()

        elif choice == "2":
            change_role()

        elif choice == "0":
            break

        else:
            print("Invalid choice.")


if __name__ == "__main__":
    user_menu()
