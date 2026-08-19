import sqlite3

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


DEFAULT_CHARGES = [

    ("Moniepoint", "Withdrawal", 1000, 9999, 100, 25),
    ("Moniepoint", "Withdrawal", 10000, 19999, 200, 25),
    ("Moniepoint", "Withdrawal", 20000, 49999, 500, 25),
    ("Moniepoint", "Withdrawal", 50000, 1000000, 1000, 25),

    ("OPay", "Withdrawal", 1000, 9999, 100, 20),
    ("OPay", "Withdrawal", 10000, 19999, 200, 20),
    ("OPay", "Withdrawal", 20000, 49999, 500, 20),
    ("OPay", "Withdrawal", 50000, 1000000, 1000, 20),

    ("PalmPay", "Withdrawal", 1000, 9999, 100, 15),
    ("PalmPay", "Withdrawal", 10000, 19999, 200, 15),
    ("PalmPay", "Withdrawal", 20000, 49999, 500, 15),
    ("PalmPay", "Withdrawal", 50000, 1000000, 1000, 15),

]
def import_default_charges():

    conn = get_connection()
    cur = conn.cursor()

    imported = 0

    for charge in DEFAULT_CHARGES:

        provider = charge[0]

        cur.execute(
            "SELECT id FROM providers WHERE provider_name=?",
            (provider,)
        )

        row = cur.fetchone()

        if row is None:
            continue

        profile_name = f"{provider} Standard"

        try:

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
                charge[0],
                charge[1],
                charge[2],
                charge[3],
                charge[4],
                charge[5]
            ))

            imported += 1

        except sqlite3.IntegrityError:
            pass

    conn.commit()
    conn.close()

    print(f"\n✅ {imported} default charge profiles imported successfully.")
