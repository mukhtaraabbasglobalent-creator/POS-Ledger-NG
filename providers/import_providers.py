import sqlite3

DB_NAME = "data/posledger.db"

PROVIDERS = [

    ("Moniepoint", "POS Company"),
    ("OPay", "Fintech"),
    ("PalmPay", "Fintech"),
    ("FirstMonie", "POS Company"),

    ("Access Bank", "Commercial Bank"),
    ("First Bank of Nigeria", "Commercial Bank"),
    ("United Bank for Africa", "Commercial Bank"),
    ("Zenith Bank", "Commercial Bank"),
    ("Guaranty Trust Bank", "Commercial Bank"),
    ("Fidelity Bank", "Commercial Bank"),
    ("Union Bank", "Commercial Bank"),
    ("Sterling Bank", "Commercial Bank"),
    ("Keystone Bank", "Commercial Bank"),
    ("Wema Bank", "Commercial Bank"),
    ("Polaris Bank", "Commercial Bank"),
    ("Ecobank", "Commercial Bank"),
    ("Stanbic IBTC", "Commercial Bank"),
    ("FCMB", "Commercial Bank"),
    ("Jaiz Bank", "Commercial Bank"),
    ("Lotus Bank", "Non-Interest Bank"),
    ("TAJ Bank", "Non-Interest Bank"),
    ("Kuda", "Digital Bank")
]


def import_providers():

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    count = 0

    for provider_name, provider_type in PROVIDERS:

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

            count += 1

        except sqlite3.IntegrityError:
            pass

    conn.commit()
    conn.close()

    print(f"\n✅ {count} providers imported successfully.")
