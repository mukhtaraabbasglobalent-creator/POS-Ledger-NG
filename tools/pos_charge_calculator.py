from engine.charge_engine import calculate_charge


def pos_charge_calculator():

    print("\n========== POS CHARGE CALCULATOR ==========")

    print("""
Select Provider
1. Moniepoint
2. OPay
3. PalmPay
4. FirstMonie
5. Other
""")

    provider_choice = input("Select Provider: ").strip()

    if provider_choice == "1":
        provider = "Moniepoint"

    elif provider_choice == "2":
        provider = "OPay"

    elif provider_choice == "3":
        provider = "PalmPay"

    elif provider_choice == "4":
        provider = "FirstMonie"

    else:
        provider = input("Enter Provider Name: ").strip()

    print("""
Transaction Type
1. Withdrawal
2. Deposit
3. Transfer
""")

    transaction_choice = input("Select Transaction Type: ").strip()

    if transaction_choice == "1":
        transaction_type = "Withdrawal"

    elif transaction_choice == "2":
        transaction_type = "Deposit"

    elif transaction_choice == "3":
        transaction_type = "Transfer"

    else:
        print("❌ Invalid transaction type.")
        return

    try:
        amount = float(input("Amount (₦): "))
    except ValueError:
        print("❌ Invalid amount.")
        return

    result = calculate_charge(provider, transaction_type, amount)

    if result is None:
        print("\n❌ No matching charge profile found.")
        return

    print("\n========== RESULT ==========")
    print(f"Provider         : {provider}")
    print(f"Transaction      : {transaction_type}")
    print(f"Amount           : ₦{amount:,.2f}")
    print(f"Customer Charge  : ₦{result['customer_charge']:,.2f}")
    print(f"Provider Fee     : ₦{result['provider_fee']:,.2f}")
    print(f"Your Profit      : ₦{result['profit']:,.2f}")
