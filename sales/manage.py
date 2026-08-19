from .new_sale import new_sale
from .cart import cart_menu
from sales.receipt_history import search_receipts


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
            search_receipts()

        elif choice == "0":
            break

        else:
            print("❌ Invalid option.")
