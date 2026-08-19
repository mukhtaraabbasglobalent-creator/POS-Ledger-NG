from tools.charge_calculator import charge_calculator
from tools.pos_charge_calculator import pos_charge_calculator
from tools.profit_calculator import profit_calculator
def financial_tools_menu():

    while True:

        print("""
====================================
        FINANCIAL TOOLS
====================================
1. POS Charge Calculator
2. Profit Calculator
3. Discount Calculator
4. VAT Calculator
5. Loan Calculator
6. Currency Converter
7. Savings Calculator
0. Back
====================================
""")

        choice = input("Select option: ").strip()

        if choice == "1":
           charge_calculator()

        elif choice == "2":
            profit_calculator()

        elif choice == "3":
            print("\n🚧 Discount Calculator (Next Step)")

        elif choice == "4":
            print("\n🚧 VAT Calculator (Next Step)")

        elif choice == "5":
            print("\n🚧 Loan Calculator (Next Step)")

        elif choice == "6":
            print("\n🚧 Currency Converter (Future)")

        elif choice == "7":
            print("\n🚧 Savings Calculator (Future)")

        elif choice == "0":
            break

        else:
            print("\n❌ Invalid option.")
