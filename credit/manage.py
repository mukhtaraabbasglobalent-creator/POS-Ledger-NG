from .new_credit_sale import new_credit_sale
from .receive_payment import receive_payment
from .customer_statement import customer_statement
from .overdue_accounts import overdue_accounts
from .report import credit_report


def credit_menu():

    while True:

        print("""
====================================
      CUSTOMER CREDIT
====================================
1. New Credit Sale
2. Receive Payment
3. Customer Statement
4. Overdue Accounts
5. Credit Report
0. Back
====================================
""")

        choice = input("Select option: ").strip()

        if choice == "1":
            new_credit_sale()

        elif choice == "2":
            receive_payment()

        elif choice == "3":
            customer_statement()

        elif choice == "4":
            overdue_accounts()

        elif choice == "5":
            credit_report()

        elif choice == "0":
            break

        else:
            print("❌ Invalid option.")
