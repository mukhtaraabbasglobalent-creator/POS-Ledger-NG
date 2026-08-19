import sqlite3

DB_NAME = "data/posledger.db"


def add_provider():

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    print("\n========== ADD PROVIDER ==========")

    provider_name = input("Provider Name: ").strip()

    print("""
Provider Type
1. Commercial Bank
2. POS Company
3. Fintech
4. Digital Bank
5. Microfinance Bank
""")

    choice = input("Select Type: ").strip()

    if choice == "1":
        provider_type = "Commercial Bank"

    elif choice == "2":
        provider_type = "POS Company"

    elif choice == "3":
        provider_type = "Fintech"

    elif choice == "4":
        provider_type = "Digital Bank"

    elif choice == "5":
        provider_type = "Microfinance Bank"

    else:
        provider_type = "Other"

    try:

        cur.execute("""
        INSERT INTO providers
        (
            provider_name,
            provider_type
        )
        VALUES (?,?)
        """, (
            provider_name,
            provider_type
        ))

        conn.commit()

        print("\n✅ Provider added successfully.")

    except sqlite3.IntegrityError:

        print("\n❌ Provider already exists.")

    conn.close()
