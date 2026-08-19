from receipts.manage import (
    view_today_receipts,
    search_receipt,
    reprint_receipt,
    refund_sale,
    delete_receipt,
)


def receipt_menu():

    while True:

        print("""
====================================
         RECEIPTS MENU
====================================
1. View Today's Receipts
2. Search Receipt
3. Reprint Receipt
4. Refund Sale
5. Delete Receipt
0. Back
====================================
""")

        choice = input("Select option: ").strip()

        if choice == "1":
            view_today_receipts()

        elif choice == "2":
            search_receipt()

        elif choice == "3":
            reprint_receipt()

        elif choice == "4":
            refund_sale()

        elif choice == "5":
            delete_receipt()

        elif choice == "0":
            break

        else:
            print("\n❌ Invalid option.")
