import sqlite3

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def charge_calculator():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, provider_name
        FROM providers
        ORDER BY provider_name
    """)

    providers = cur.fetchall()

    if not providers:
        print("\n❌ No providers found.")
        conn.close()
        return

    print("\n========== POS CHARGE CALCULATOR ==========")

    for row in providers:
        print(f"{row['id']}. {row['provider_name']}")

    provider_id = input("\nSelect Provider ID: ").strip()

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

    transaction_map = {
        "1": "Withdrawal",
        "2": "Deposit",
        "3": "Transfer",
        "4": "Airtime",
        "5": "Data"
    }

    if t not in transaction_map:
        print("❌ Invalid Transaction Type.")
        conn.close()
        return

    transaction_type = transaction_map[t]

    try:
        amount = float(input("Amount (₦): "))
    except ValueError:
        print("❌ Invalid amount.")
        conn.close()
        return

    cur.execute("""
        SELECT *
        FROM charge_profiles
        WHERE provider=?
        AND transaction_type=?
        AND ? BETWEEN min_amount AND max_amount
        LIMIT 1
    """, (
        provider,
        transaction_type,
        amount
    ))

    row = cur.fetchone()

    conn.close()

    if row is None:
        print("\n❌ No matching charge profile found.")
        return

    profit = row["customer_charge"] - row["provider_fee"]

    print("\n========== RESULT ==========")
    print(f"Provider         : {provider}")
    print(f"Transaction      : {transaction_type}")
    print(f"Amount           : ₦{amount:,.2f}")
    print(f"Customer Charge  : ₦{row['customer_charge']:,.2f}")
    print(f"Provider Fee     : ₦{row['provider_fee']:,.2f}")
    print(f"Profit           : ₦{profit:,.2f}")
