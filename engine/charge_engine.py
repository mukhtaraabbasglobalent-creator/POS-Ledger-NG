import sqlite3

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def calculate_charge(provider, transaction_type, amount):
    """
    POS Ledger NG charge engine.

    Priority:
    1. Matching charge profile
    2. Manual charge fallback

    Includes:
    - High-value transaction warning
    - Negative-profit protection
    """

    # ------------------------------------
    # BASIC VALIDATION
    # ------------------------------------

    if amount <= 0:
        return {
            "customer_charge": 0.0,
            "provider_fee": 0.0,
            "profit": 0.0,
            "source": "INVALID"
        }

    # ------------------------------------
    # HIGH-VALUE WARNING
    # ------------------------------------

    high_value = amount >= 1_000_000

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM charge_profiles
        WHERE LOWER(provider) = LOWER(?)
          AND LOWER(transaction_type) = LOWER(?)
          AND ? BETWEEN min_amount AND max_amount
        ORDER BY min_amount DESC
        LIMIT 1
    """, (
        provider.strip(),
        transaction_type.strip(),
        amount
    ))

    row = cur.fetchone()
    conn.close()

    # ------------------------------------
    # PROFILE FOUND
    # ------------------------------------

    if row is not None:

        customer_charge = float(row["customer_charge"])
        provider_fee = float(row["provider_fee"])

        profit = customer_charge - provider_fee

        return {
            "customer_charge": customer_charge,
            "provider_fee": provider_fee,
            "profit": profit,
            "source": "PROFILE",
            "high_value": high_value
        }

    # ------------------------------------
    # PROFILE NOT FOUND
    # ------------------------------------

    print("\n⚠️ No charge profile found.")
    print("Manual charge entry is required.")

    if high_value:
        print("\n⚠️ HIGH-VALUE TRANSACTION")
        print(f"Transaction Amount: ₦{amount:,.2f}")
        print("Please verify the charge carefully.")

    # ------------------------------------
    # MANUAL CUSTOMER CHARGE
    # ------------------------------------

    while True:

        try:
            customer_charge = float(
                input("Manual Customer Charge (₦): ").strip()
            )

            if customer_charge < 0:
                print("❌ Charge cannot be negative.")
                continue

            break

        except ValueError:
            print("❌ Invalid customer charge.")

    # ------------------------------------
    # MANUAL PROVIDER FEE
    # ------------------------------------

    while True:

        try:
            provider_fee = float(
                input("Provider Fee (₦): ").strip()
            )

            if provider_fee < 0:
                print("❌ Provider fee cannot be negative.")
                continue

            break

        except ValueError:
            print("❌ Invalid provider fee.")

    # ------------------------------------
    # PROFIT CALCULATION
    # ------------------------------------

    profit = customer_charge - provider_fee

    # ------------------------------------
    # NEGATIVE PROFIT PROTECTION
    # ------------------------------------

    if profit < 0:

        print("\n⚠️ WARNING: NEGATIVE PROFIT")
        print(f"Customer Charge: ₦{customer_charge:,.2f}")
        print(f"Provider Fee   : ₦{provider_fee:,.2f}")
        print(f"Loss           : ₦{abs(profit):,.2f}")

        while True:

            confirm = input(
                "\nContinue with this loss? (yes/no): "
            ).strip().lower()

            if confirm == "yes":
                break

            if confirm == "no":
                return {
                    "customer_charge": 0.0,
                    "provider_fee": 0.0,
                    "profit": 0.0,
                    "source": "CANCELLED",
                    "high_value": high_value
                }

            print("Please enter yes or no.")

    # ------------------------------------
    # RETURN MANUAL RESULT
    # ------------------------------------

    return {
        "customer_charge": customer_charge,
        "provider_fee": provider_fee,
        "profit": profit,
        "source": "MANUAL",
        "high_value": high_value
    }
