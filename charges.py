import sqlite3

DB_NAME = "data/posledger.db"

def add_charge():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    min_amount = float(input("Minimum Amount (₦): "))
    max_amount = float(input("Maximum Amount (₦): "))
    charge = float(input("Charge (₦): "))

    cur.execute("""
        INSERT INTO charge_settings
        (min_amount, max_amount, charge)
        VALUES (?, ?, ?)
    """, (min_amount, max_amount, charge))

    conn.commit()
    conn.close()

    print("Charge setting saved successfully.")

def view_charges():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, min_amount, max_amount, charge
        FROM charge_settings
        ORDER BY min_amount
    """)

    rows = cur.fetchall()

    print("\n===== CHARGE SETTINGS =====")

    if not rows:
        print("No charge settings found.")
    else:
        for row in rows:
            print(f"ID:{row[0]} | ₦{row[1]:,.0f} - ₦{row[2]:,.0f} = ₦{row[3]:,.0f}")

    conn.close()

def edit_charge():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    view_charges()

    charge_id = int(input("\nEnter Charge ID to edit: "))
    new_charge = float(input("New Charge (₦): "))

    cur.execute("""
        UPDATE charge_settings
        SET charge = ?
        WHERE id = ?
    """, (new_charge, charge_id))

    conn.commit()
    conn.close()

    print("Charge updated successfully.")

def delete_charge():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    view_charges()

    charge_id = int(input("\nEnter Charge ID to delete: "))

    cur.execute("""
        DELETE FROM charge_settings
        WHERE id = ?
    """, (charge_id,))

    conn.commit()
    conn.close()

    print("Charge deleted successfully.")
