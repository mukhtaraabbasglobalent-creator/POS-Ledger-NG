import sqlite3
from providers.provider_list import get_providers

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def add_charge_profile():

    conn = get_connection()
    cur = conn.cursor()

    print("\n========== ADD CHARGE PROFILE ==========")

    profile_name = input("Profile Name: ").strip()

    providers = get_providers()

    if not providers:
        print("\n❌ No providers found. Please add or import providers first.")
        conn.close()
        return

    print("\n========== SELECT PROVIDER ==========")

    for row in providers:
        print(f"{row['id']}. {row['provider_name']}")

    provider_id = input("Select Provider ID: ").strip()

    provider = None

    for row in providers:
        if str(row["id"]) == provider_id:
            provider = row["provider_name"]
            break

    if provider is None:
        print("❌ Invalid Provider.")
        conn.close()
        return

    print("""
Transaction Type
1. Withdrawal
2. Deposit
3. Transfer
4. Airtime
5. Data
""")

    t = input("Select Transaction Type: ").strip()

    if t == "1":
        transaction_type = "Withdrawal"
    elif t == "2":
        transaction_type = "Deposit"
    elif t == "3":
        transaction_type = "Transfer"
    elif t == "4":
        transaction_type = "Airtime"
    elif t == "5":
        transaction_type = "Data"
    else:
        transaction_type = input("Enter Transaction Type: ").strip()

    while True:
        try:
            min_amount = float(input("Minimum Amount: "))
            break
        except ValueError:
            print("❌ Please enter a valid number.")

    while True:
        try:
            max_amount = float(input("Maximum Amount: "))

            if max_amount < min_amount:
                print("❌ Maximum Amount cannot be less than Minimum Amount.")
                continue

            break

        except ValueError:
            print("❌ Please enter a valid number.")

    while True:
        try:
            customer_charge = float(input("Customer Charge: "))
            break
        except ValueError:
            print("❌ Please enter a valid number.")

    while True:
        try:
            provider_fee = float(input("Provider Fee: "))
            break
        except ValueError:
            print("❌ Please enter a valid number.")

    cur.execute("""
        INSERT INTO charge_profiles
        (
            profile_name,
            provider,
            transaction_type,
            min_amount,
            max_amount,
            customer_charge,
            provider_fee
        )
        VALUES (?,?,?,?,?,?,?)
    """, (
        profile_name,
        provider,
        transaction_type,
        min_amount,
        max_amount,
        customer_charge,
        provider_fee
    ))

    conn.commit()
    conn.close()

    print("\n✅ Charge profile added successfully.")
