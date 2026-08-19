import sqlite3

DB_NAME = "data/posledger.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


def view_charges():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, min_amount, max_amount, charge
        FROM charge_settings
        ORDER BY min_amount
    """)
def add_charge():
    conn = get_connection()
    cur = conn.cursor()

    print("\n========== ADD CHARGE ==========")

    min_amount = float(input("Minimum Amount: ₦"))
    max_amount = float(input("Maximum Amount: ₦"))
    charge = float(input("Charge: ₦"))

    cur.execute("""
        INSERT INTO charge_settings(
            min_amount,
            max_amount,
            charge
        )
        VALUES(?,?,?)
    """, (
        min_amount,
        max_amount,
        charge
    ))

    conn.commit()
    conn.close()

    print("✅ Charge added successfully.")

    rows = cur.fetchall()

    print("\n========== CHARGE SETTINGS ==========")

    if not rows:
        print("No charge settings found.")
    else:
        for row in rows:
            print("-" * 40)
            print(f"ID         : {row[0]}")
            print(f"Min Amount : ₦{row[1]:,.2f}")
            print(f"Max Amount : ₦{row[2]:,.2f}")
            print(f"Charge     : ₦{row[3]:,.2f}")

    conn.close()


def delete_charge():
    view_charges()

    charge_id = input("\nEnter ID to delete: ").strip()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM charge_settings WHERE id=?",
        (charge_id,)
    )

    conn.commit()
    conn.close()
def edit_charge():
    view_charges()

    charge_id = input("\nEnter Charge ID to edit: ").strip()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT min_amount, max_amount, charge
        FROM charge_settings
        WHERE id=?
    """, (charge_id,))

    row = cur.fetchone()

    if not row:
        print("❌ Charge not found.")
        conn.close()
        return

    print("\nPress ENTER to keep the current value.\n")

    min_amount = input(f"Minimum Amount [{row[0]}]: ").strip()
    max_amount = input(f"Maximum Amount [{row[1]}]: ").strip()
    charge = input(f"Charge [{row[2]}]: ").strip()

    min_amount = float(min_amount) if min_amount else row[0]
    max_amount = float(max_amount) if max_amount else row[1]
    charge = float(charge) if charge else row[2]

    cur.execute("""
        UPDATE charge_settings
        SET
            min_amount=?,
            max_amount=?,
            charge=?
        WHERE id=?
    """, (
        min_amount,
        max_amount,
        charge,
        charge_id
    ))

    conn.commit()
    conn.close()

    print("✅ Charge updated successfully.")

    print("✅ Charge deleted successfully.")


def charge_menu():
    while True:
        print("""
========== CHARGE SETTINGS ==========
1. Add Charge
2. View Charges
3. Edit Charge
4. Delete Charge
0. Back
=====================================
""")

        choice = input("Select option: ").strip()

        if choice == "1":
            add_charge()

        elif choice == "2":
            view_charges()

        elif choice == "3":
            edit_charge()

        elif choice == "4":
            delete_charge()

        elif choice == "0":
            break

        else:
            print("❌ Invalid option.")
  



if __name__ == "__main__":
    charge_menu()
