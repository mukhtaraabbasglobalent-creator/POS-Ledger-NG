import sqlite3
import hashlib
import re

DB_NAME = "data/posledger.db"


def create_auth_table():

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fullname TEXT NOT NULL,
        password TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def check_first_time():

    create_auth_table()

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM users")
    count = cur.fetchone()[0]

    conn.close()

    return count == 0


def validate_password(password):

    if len(password) < 8:
        print("❌ Password must be at least 8 characters.")
        return False

    if not any(c.isupper() for c in password):
        print("❌ Password must contain an uppercase letter.")
        return False

    if not any(c.islower() for c in password):
        print("❌ Password must contain a lowercase letter.")
        return False

    if not any(c.isdigit() for c in password):
        print("❌ Password must contain a number.")
        return False

    special = "!@#$%^&*()-_=+[]{};:,.?/<>"

    if not any(c in special for c in password):
        print("❌ Password must contain a special character.")
        return False

    return True

def create_pin():

    create_auth_table()

    # Skip setup if a user already exists
    if not check_first_time():
        return True

    print("\n========== FIRST TIME SETUP ==========")

    fullname = input("Enter your full name: ").strip()

    if fullname == "":
        print("❌ Full name cannot be empty.")
        return False

    password = input("Create Password: ").strip()

    if not validate_password(password):
        return False

    confirm = input("Confirm Password: ").strip()

    if password != confirm:
        print("❌ Passwords do not match.")
        return False

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO users(fullname, password)
        VALUES (?, ?)
        """,
        (
            fullname,
            hash_password(password)
        )
    )

    conn.commit()
    conn.close()

    print("\n✅ Account created successfully!")
    return True
def login():

    attempts = 5

    while attempts > 0:

        password = input("Enter Password: ").strip()

        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()

        cur.execute(
            """
            SELECT fullname, password
            FROM users
            LIMIT 1
            """
        )

        user = cur.fetchone()

        conn.close()

        if user is None:
            print("❌ No account found.")
            return False

        fullname = user[0]
        stored_password = user[1]

        if hash_password(password) == stored_password:

            print("\n✅ Login successful!")
            print(f"Welcome, {fullname}")
            return True

        attempts -= 1

        print(f"❌ Incorrect password. Attempts left: {attempts}")

    print("\n🔒 Too many failed attempts.")
    return False
def change_password():

    print("\n========== CHANGE PASSWORD ==========")

    old_password = input("Current Password: ").strip()

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, password
        FROM users
        LIMIT 1
        """
    )

    user = cur.fetchone()

    if user is None:
        conn.close()
        print("❌ No user found.")
        return False

    user_id = user[0]
    stored_password = user[1]

    if hash_password(old_password) != stored_password:
        conn.close()
        print("❌ Current password is incorrect.")
        return False

    new_password = input("New Password: ").strip()

    if not validate_password(new_password):
        conn.close()
        return False

    confirm = input("Confirm New Password: ").strip()

    if new_password != confirm:
        conn.close()
        print("❌ Passwords do not match.")
        return False

    cur.execute(
        """
        UPDATE users
        SET password = ?
        WHERE id = ?
        """,
        (
            hash_password(new_password),
            user_id
        )
    )

    conn.commit()
    conn.close()

    print("✅ Password changed successfully.")
    return True


if __name__ == "__main__":

    while not create_pin():
        pass

    while not login():
        pass

    print("\nAuthentication test completed successfully.")
