import sqlite3

from deposit import deposit_money
from withdraw import withdraw_money
from engine.charge_engine import calculate_charge


DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def save_transaction(
    customer_id,
    transaction_type,
    amount,
    charge,
    provider_fee,
    profit,
    provider
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO transactions(
            customer_id,
            transaction_type,
            amount,
            charge,
            provider_fee,
            profit,
            provider
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        customer_id,
        transaction_type,
        amount,
        charge,
        provider_fee,
        profit,
        provider
    ))

    conn.commit()
    transaction_id = cur.lastrowid
    conn.close()

    return transaction_id


def select_customer():
    conn = get_connection()
    cur = conn.cursor()

    print("\n========== CUSTOMER ==========")
    print("Enter customer phone or name.")
    print("Leave blank for walk-in customer.")

    keyword = input("Customer: ").strip()

    if keyword == "":
        conn.close()
        return None

    cur.execute("""
        SELECT *
        FROM customers
        WHERE LOWER(fullname) LIKE LOWER(?)
           OR phone LIKE ?
        ORDER BY id DESC
    """, (
        f"%{keyword}%",
        f"%{keyword}%"
    ))

    rows = cur.fetchall()
    conn.close()

    if not rows:
        print("\n❌ Customer not found.")
        return None

    if len(rows) == 1:
        customer = rows[0]

        print(
            f"\n✅ Customer selected: "
            f"{customer['fullname']}"
        )

        return customer["id"]

    print("\n========== CUSTOMERS FOUND ==========")

    for row in rows:
        print(
            f"{row['id']}. "
            f"{row['fullname']} - "
            f"{row['phone']}"
        )

    try:
        customer_id = int(
            input("\nEnter Customer ID: ").strip()
        )
    except ValueError:
        print("❌ Invalid customer ID.")
        return None

    valid_ids = [row["id"] for row in rows]

    if customer_id not in valid_ids:
        print("❌ Invalid customer selection.")
        return None

    return customer_id


def charge_calculator():

    print("\n========== CHARGE CALCULATOR ==========")

    provider = input("Provider: ").strip()

    if provider == "":
        print("❌ Provider is required.")
        return

    transaction_type = input(
        "Transaction Type "
        "(Withdrawal/Deposit/Transfer): "
    ).strip()

    if transaction_type == "":
        print("❌ Transaction type is required.")
        return

    try:
        amount = float(
            input("Amount (₦): ").strip()
        )
    except ValueError:
        print("❌ Invalid amount.")
        return

    if amount <= 0:
        print("❌ Amount must be greater than zero.")
        return

    customer_id = select_customer()

    result = calculate_charge(
        provider,
        transaction_type,
        amount
    )

    if result["source"] == "CANCELLED":

        print("\n❌ Transaction cancelled.")
        print("No transaction was recorded.")

        return

    transaction_id = save_transaction(
        customer_id,
        transaction_type,
        amount,
        result["customer_charge"],
        result["provider_fee"],
        result["profit"],
        provider
    )

    print("\n========== TRANSACTION SAVED ==========")

    print(
        f"Transaction ID : {transaction_id}"
    )

    print(
        f"Customer ID    : "
        f"{customer_id if customer_id else 'Walk-in'}"
    )

    print(
        f"Provider       : {provider}"
    )

    print(
        f"Type           : {transaction_type}"
    )

    print(
        f"Amount         : ₦{amount:,.2f}"
    )

    print(
        f"Customer Charge: "
        f"₦{result['customer_charge']:,.2f}"
    )

    print(
        f"Provider Fee   : "
        f"₦{result['provider_fee']:,.2f}"
    )

    print(
        f"Profit         : "
        f"₦{result['profit']:,.2f}"
    )

    print(
        f"Source         : "
        f"{result['source']}"
    )

    print("========================================")


def transaction_menu():

    while True:

        print("""
====================================
      RECORD TRANSACTION
====================================
1. Cash Deposit
2. Cash Withdrawal
3. Charge Calculator
4. Back
====================================
""")

        choice = input("Select option: ").strip()

        if choice == "1":

            deposit_money()

        elif choice == "2":

            withdraw_money()

        elif choice == "3":

            charge_calculator()

            input("\nPress Enter to continue...")

        elif choice == "4":

            break

        else:

            print("❌ Invalid option.")
