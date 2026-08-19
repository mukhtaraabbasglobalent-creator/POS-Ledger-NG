import sqlite3

from charges.add_charge_profile import add_charge_profile
from charges.delete_charge_profile import delete_charge_profile
from charges.charge_setup_guide import charge_setup_guide

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn
def view_charge_profiles():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM charge_profiles
        ORDER BY provider, min_amount
    """)

    rows = cur.fetchall()

    print("\n========== CHARGE PROFILES ==========")

    if not rows:
        print("No charge profiles found.")
        conn.close()
        return

    for row in rows:

        profit = row["customer_charge"] - row["provider_fee"]

        print("----------------------------------------")
        print(f"ID                : {row['id']}")
        print(f"Profile           : {row['profile_name']}")
        print(f"Provider          : {row['provider']}")
        print(f"Transaction Type  : {row['transaction_type']}")
        print(f"Range             : ₦{row['min_amount']:,.0f} - ₦{row['max_amount']:,.0f}")
        print(f"Customer Charge   : ₦{row['customer_charge']:,.2f}")
        print(f"Provider Fee      : ₦{row['provider_fee']:,.2f}")
        print(f"Profit            : ₦{profit:,.2f}")

    conn.close()
def charge_profile_menu():

    while True:

        print("""
========== CHARGE PROFILE ==========
1. View Charge Profiles
2. Add Charge Profile
3. Edit Charge Profile
4. Delete Charge Profile
5. Import Default Charges
0. Back
====================================
""")

        choice = input("Select option: ").strip()

        if choice == "1":
            view_charge_profiles()

        elif choice == "2":
            add_charge_profile()

        elif choice == "3":
            print("\n🚧 Edit Charge Profile - Coming Next")

        elif choice == "4":
            delete_charge_profile()

        elif choice == "5":
            charge_setup_guide()

        elif choice == "0":
            break

        else:
            print("\n❌ Invalid option.")
