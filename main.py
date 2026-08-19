from auth import login

from staff.manage import (
    login_staff,
    current_user,
    is_admin,
    staff_menu,
)

from deposit import deposit_money
from withdraw import withdraw_money

from reports import (
    view_report,
    financial_report,
    daily_closing_report,
)

from manage_charges import charge_menu

from balance import (
    set_opening_balance,
    show_balance,
)

from expenses import expense_menu
from audit_logs import view_audit_logs

from customers.manage import customer_menu
from products import product_menu
from inventory_menu import inventory_menu
from sales.manage import sales_menu
from creditors.manage import creditor_menu
from suppliers.manage import supplier_menu
from purchases.manage import purchase_menu
from sales_history.manage import sales_history_menu
from credit.manage import credit_menu
from manage import dashboard_menu
from exports.manage import export_menu
from stock_alerts.manage import stock_alert_menu
from transactions.manage import transaction_menu
from charges.manage import charge_profile_menu
from tools.menu import financial_tools_menu
from providers.manage import provider_menu
from business.setup import business_setup
from analytics.manage import analytics_menu
from dashboard.real_dashboard import main as business_dashboard
def menu():

    if not login():
        return

    if not login_staff():
        return

    while True:

        staff = current_user()

        print(f"\nLogged in Staff: {staff['fullname']} ({staff['role']})")

        print("""
====================================
          POS LEDGER NG
====================================
1. Record Transaction
2. Deposit Money
3. Withdraw Money
4. View Reports
5. Charge Settings
6. Opening Balance
7. Expenses
8. Financial Reports
9. View Balance
10. View Audit Logs
11. Customers
12. Products
13. Inventory
14. Sales
15. Creditors
16. Suppliers
17. Purchases
18. Sale History
19. Customer Credit
20. Dashboard
21. Export
22. Staff
23. Stock Alerts
24. Providers
25. Charge Profiles
26. Business Tools
27. Business Profile
28. Business Analytics
29. Exit
====================================
""")

        choice = input("Select option: ").strip()
        if choice == "1":
            transaction_menu()

        elif choice == "2":
            deposit_money()

        elif choice == "3":
            withdraw_money()

        elif choice == "4":
            view_report()

        elif choice == "5":
            charge_menu()

        elif choice == "6":
            set_opening_balance()

        elif choice == "7":
            expense_menu()

        elif choice == "8":

            while True:

                print("""
====================================
          REPORTS MENU
====================================
1. Financial Report
2. Daily Closing Report
0. Back
====================================
""")

                report_choice = input("Select option: ").strip()

                if report_choice == "1":
                    financial_report()

                elif report_choice == "2":
                    daily_closing_report()

                elif report_choice == "0":
                    break

                else:
                    print("\n❌ Invalid option.")
        elif choice == "9":
            show_balance()

        elif choice == "10":
            view_audit_logs()

        elif choice == "11":
            customer_menu()

        elif choice == "12":
            product_menu()

        elif choice == "13":
            inventory_menu()

        elif choice == "14":
            sales_menu()

        elif choice == "15":
            creditor_menu()

        elif choice == "16":
            supplier_menu()

        elif choice == "17":
            purchase_menu()

        elif choice == "18":
            sales_history_menu()
        elif choice == "19":
            credit_menu()

        elif choice == "20":
            business_dashboard()

        elif choice == "21":
            export_menu()

        elif choice == "22":

            if is_admin():
                staff_menu()
            else:
                print("\n❌ Access denied. Admin only.")

        elif choice == "23":
            stock_alert_menu()

        elif choice == "24":
            provider_menu()

        elif choice == "25":
            charge_profile_menu()

        elif choice == "26":
            financial_tools_menu()

        elif choice == "27":
            business_setup()

        elif choice == "28":
            analytics_menu()

        elif choice == "29":
            print("\nThank you for using POS Ledger NG.")
            break

        else:
            print("\n❌ Invalid option.")


if __name__ == "__main__":
    menu()
