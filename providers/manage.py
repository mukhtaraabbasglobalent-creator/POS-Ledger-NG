from providers.add_provider import add_provider
from providers.view_providers import view_providers
from providers.edit_provider import edit_provider
from providers.delete_provider import delete_provider
from providers.import_providers import import_providers


def provider_menu():

    while True:

        print("""
====================================
          PROVIDERS
====================================
1. View Providers
2. Add Provider
3. Edit Provider
4. Delete Provider
5. Import Nigerian Providers
0. Back
====================================
""")

        choice = input("Select option: ").strip()

        if choice == "1":
            view_providers()

        elif choice == "2":
            add_provider()

        elif choice == "3":
            edit_provider()

        elif choice == "4":
            delete_provider()

        elif choice == "5":
            import_providers()

        elif choice == "0":
            break

        else:
            print("\n❌ Invalid option.")
