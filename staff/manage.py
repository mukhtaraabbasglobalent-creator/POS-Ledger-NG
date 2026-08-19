import sqlite3
import hashlib

DB_NAME = "data/posledger.db"

current_staff = None


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def hash_pin(pin):
    return hashlib.sha256(pin.encode()).hexdigest()


def create_staff_table():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS staff(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fullname TEXT NOT NULL,
        username TEXT UNIQUE NOT NULL,
        pin TEXT NOT NULL,
        role TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()


def current_user():
    return current_staff


def is_admin():

    if current_staff is None:
        return False

    return current_staff["role"].lower() == "admin"


def logout_staff():

    global current_staff
    current_staff = None
def add_staff():

    create_staff_table()

    print("\n========== ADD STAFF ==========")

    fullname = input("Full Name : ").strip()
    username = input("Username  : ").strip()
    pin = input("4-digit PIN: ").strip()

    if len(pin) != 4 or not pin.isdigit():
        print("❌ PIN must be exactly 4 digits.")
        return

    print("\nRole")
    print("1. Admin")
    print("2. Cashier")

    role_choice = input("Select: ").strip()

    if role_choice == "1":
        role = "Admin"
    else:
        role = "Cashier"

    conn = get_connection()
    cur = conn.cursor()

    try:

        cur.execute(
            """
            INSERT INTO staff(fullname, username, pin, role)
            VALUES (?, ?, ?, ?)
            """,
            (
                fullname,
                username,
                hash_pin(pin),
                role
            )
        )

        conn.commit()

        print("\n✅ Staff created successfully.")

    except sqlite3.IntegrityError:
        print("\n❌ Username already exists.")

    conn.close()


def view_staff():

    create_staff_table()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT id, fullname, username, role
    FROM staff
    ORDER BY fullname
    """)

    rows = cur.fetchall()

    conn.close()

    print("\n========== STAFF LIST ==========")

    if not rows:
        print("No staff found.")
        return

    for row in rows:

        print("-----------------------------------")
        print(f"ID       : {row['id']}")
        print(f"Name     : {row['fullname']}")
        print(f"Username : {row['username']}")
        print(f"Role     : {row['role']}")
def login_staff():

    global current_staff

    create_staff_table()

    print("\n========== STAFF LOGIN ==========")

    username = input("Username : ").strip()
    pin = input("PIN (4 digits): ").strip()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT *
        FROM staff
        WHERE username = ?
        """,
        (username,)
    )

    row = cur.fetchone()

    conn.close()

    if row is None:
        print("\n❌ Invalid username or PIN.")
        return False

    if hash_pin(pin) != row["pin"]:
        print("\n❌ Invalid username or PIN.")
        return False

    current_staff = {
        "id": row["id"],
        "fullname": row["fullname"],
        "username": row["username"],
        "role": row["role"]
    }

    print("\n✅ Login successful.")
    print(f"Welcome: {row['fullname']}")
    print(f"Role   : {row['role']}")

    return True
def staff_menu():

    create_staff_table()

    while True:

        print("""
====================================
        STAFF MANAGEMENT
====================================
1. Add Staff
2. View Staff
3. Staff Login
4. Logout
0. Back
====================================
""")

        choice = input("Select option: ").strip()

        if choice == "1":

            if is_admin() or current_user() is None:
                add_staff()
            else:
                print("\n❌ Only Admin can add staff.")

        elif choice == "2":
            view_staff()

        elif choice == "3":
            login_staff()

        elif choice == "4":
            logout_staff()
            print("\n✅ Staff logged out.")

        elif choice == "0":
            break

        else:
            print("\n❌ Invalid option.")


if __name__ == "__main__":

    create_staff_table()
    staff_menu()
