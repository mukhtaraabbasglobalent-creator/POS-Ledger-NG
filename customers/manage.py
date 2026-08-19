def customer_menu():

    while True:

        print("""
====================================
       CUSTOMER MANAGEMENT
====================================
1. Add Customer
2. View Customers
3. Search Customer
4. Edit Customer
5. Delete Customer
6. Customer Statement
0. Back
====================================
""")

        choice = input("Select option: ").strip()

        if choice == "1":
            from customers.add_customer import add_customer
            add_customer()

        elif choice == "2":
            from customers.view_customers import view_customers
            view_customers()

        elif choice == "3":
            from customers.search_customer import search_customer
            search_customer()

        elif choice == "4":
            from customers.edit_customer import edit_customer
            edit_customer()

        elif choice == "5":
            from customers.delete_customer import delete_customer
            delete_customer()

        elif choice == "6":
            from customers.statement import customer_statement
            customer_statement()

        elif choice == "0":
            break

        else:
            print("\n❌ Invalid option.")
