from sales.new_sale import new_sale
from sales.cart import cart_menu
from receipts.history import receipt_history


def sales_menu():

    while True:

        print("""
====================================
            SALES MENU
====================================
1. New Sale
2. Cart
3. Receipt History
0. Back
====================================
""")

        choice = input("Select option: ").strip()

        if choice == "1":
            new_sale()

        elif choice == "2":
            cart_menu()

        elif choice == "3":
            receipt_history()

        elif choice == "0":
            break

        else:
            print("\n❌ Invalid option.")
