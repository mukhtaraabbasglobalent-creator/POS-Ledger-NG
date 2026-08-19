def profit_calculator():

    print("\n========== PROFIT CALCULATOR ==========")

    try:
        buying_price = float(input("Buying Price (₦): "))
        selling_price = float(input("Selling Price (₦): "))
        quantity = int(input("Quantity: "))

    except ValueError:
        print("\n❌ Invalid input.")
        return

    profit_per_item = selling_price - buying_price
    total_profit = profit_per_item * quantity
    total_cost = buying_price * quantity
    total_sales = selling_price * quantity

    print("\n========== RESULT ==========")
    print(f"Buying Total     : ₦{total_cost:,.2f}")
    print(f"Selling Total    : ₦{total_sales:,.2f}")
    print(f"Profit Per Item  : ₦{profit_per_item:,.2f}")
    print(f"Total Profit     : ₦{total_profit:,.2f}")
