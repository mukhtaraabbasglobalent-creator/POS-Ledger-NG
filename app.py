import datetime
from database import create_tables, add_transaction
from calculations import calculate_charge, calculate_profit, calculate_total_money
from reports import daily_summary, monthly_summary
from export_reports import export_daily_csv, export_monthly_csv

def main():
    create_tables()
    print("=== POS Agent Tracker ===")

    while True:
        print("\n=== Main Menu ===")
        print("1. Add Transaction")
        print("2. Show Daily Summary")
        print("3. Show Monthly Summary")
        print("4. Export Daily Report (CSV)")
        print("5. Export Monthly Report (CSV)")
        print("6. Exit")

        choice = input("Choose option: ")

        if choice == "1":
            t_type = input("Transaction Type (Deposit/Withdrawal): ")
            amount = float(input("Amount: "))
            cash_box = float(input("Cash in Box: "))
            cash_wallet = float(input("Cash in Wallet: "))
            desc = input("Description: ")

            charge = calculate_charge(amount)
            profit = calculate_profit(amount, charge)
            total_money = calculate_total_money(cash_box, cash_wallet)
            date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            add_transaction((date, t_type, amount, charge, profit, cash_box, cash_wallet, total_money, desc))

            print("\nTransaction Saved!")
            print(f"Charge: ₦{charge}")
            print(f"Profit: ₦{profit}")
            print(f"Total Business Money: ₦{total_money}")

        elif choice == "2":
            daily_summary()

        elif choice == "3":
            monthly_summary()

        elif choice == "4":
            export_daily_csv()

        elif choice == "5":
            export_monthly_csv()

        elif choice == "6":
            print("Goodbye!")
            break

        else:
            print("Invalid choice. Please select a valid option.")

if __name__ == "__main__":
    main()
