import sqlite3

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def business_setup():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS business_profile (
        id INTEGER PRIMARY KEY,
        business_name TEXT,
        owner_name TEXT,
        phone TEXT,
        email TEXT,
        state TEXT,
        lga TEXT,
        address TEXT
    )
    """)

    print("\n========== BUSINESS SETUP ==========")

    business_name = input("Business Name: ").strip()
    owner_name = input("Owner Name: ").strip()
    phone = input("Phone Number: ").strip()
    email = input("Email: ").strip()
    state = input("State: ").strip()
    lga = input("LGA: ").strip()
    address = input("Business Address: ").strip()
    cur.execute("SELECT id FROM business_profile LIMIT 1")
    row = cur.fetchone()

    if row is None:

        cur.execute("""
        INSERT INTO business_profile
        (
            business_name,
            owner_name,
            phone,
            email,
            state,
            lga,
            address
        )
        VALUES (?,?,?,?,?,?,?)
        """, (
            business_name,
            owner_name,
            phone,
            email,
            state,
            lga,
            address
        ))

    else:

        cur.execute("""
        UPDATE business_profile
        SET
            business_name=?,
            owner_name=?,
            phone=?,
            email=?,
            state=?,
            lga=?,
            address=?
        WHERE id=?
        """, (
            business_name,
            owner_name,
            phone,
            email,
            state,
            lga,
            address,
            row["id"]
        ))

    conn.commit()
    conn.close()

    print("\n✅ Business profile saved successfully.")
