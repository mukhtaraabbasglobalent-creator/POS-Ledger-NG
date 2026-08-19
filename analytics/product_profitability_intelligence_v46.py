"""
POS Ledger NG V46
Product Profitability & Management Action Intelligence

READ-ONLY MODULE
Does not modify products, sales, inventory, balances,
customers, creditors, or expenses.
"""

from database.connection import get_connection


TARGET_MARGIN = 10.0


def money(value):
    return f"₦{value:,.2f}"


def calculate_margin(buying_price, selling_price):
    if selling_price <= 0:
        return 0.0

    return ((selling_price - buying_price) / selling_price) * 100


def minimum_price_for_margin(buying_price, target_margin):
    """
    Calculates the selling price required to achieve
    the requested gross margin.

    Example:
    Buying price = ₦100
    Target margin = 10%

    Required selling price = 100 / 0.90
    """

    if target_margin >= 100:
        return buying_price

    return buying_price / (1 - target_margin / 100)


def product_profitability_v46():

    conn = get_connection()
    cur = conn.cursor()

    products = cur.execute("""
        SELECT
            id,
            product_name,
            sku,
            category,
            buying_price,
            selling_price,
            current_stock,
            minimum_stock,
            min_stock,
            unit
        FROM products
        ORDER BY product_name
    """).fetchall()

    actions = []
    total_inventory_capital = 0.0

    print("\n========================================")
    print("       POS LEDGER NG V46")
    print(" PRODUCT PROFITABILITY INTELLIGENCE")
    print("========================================")

    print("\nMANAGEMENT TARGET")
    print("----------------------------------------")
    print(f"Target Gross Margin : {TARGET_MARGIN:.2f}%")
    print("Mode                : READ-ONLY")

    if not products:
        print("\nNo products found.")
        conn.close()
        return

    print("\nPRODUCT PROFITABILITY")
    print("----------------------------------------")

    for product in products:

        name = product["product_name"]
        sku = product["sku"] or "-"
        buying = float(product["buying_price"] or 0)
        selling = float(product["selling_price"] or 0)
        stock = float(product["current_stock"] or 0)
        unit = product["unit"] or "EA"

        unit_profit = selling - buying
        margin = calculate_margin(buying, selling)

        inventory_capital = buying * stock
        total_inventory_capital += inventory_capital

        target_price = minimum_price_for_margin(
            buying,
            TARGET_MARGIN
        )

        if selling <= 0:
            status = "🔴 INVALID SELLING PRICE"
            actions.append(
                (
                    "CRITICAL",
                    name,
                    "Set a valid selling price before further sales."
                )
            )

        elif selling < buying:
            status = "🔴 SELLING BELOW COST"
            actions.append(
                (
                    "CRITICAL",
                    name,
                    f"Increase selling price above {money(buying)}."
                )
            )

        elif margin < TARGET_MARGIN:
            status = "🟠 BELOW TARGET"
            actions.append(
                (
                    "HIGH",
                    name,
                    f"Review price. Suggested minimum for "
                    f"{TARGET_MARGIN:.0f}% margin: "
                    f"{money(target_price)}."
                )
            )

        else:
            status = "🟢 TARGET ACHIEVED"

        print(f"\nProduct              : {name}")
        print(f"SKU                  : {sku}")
        print(f"Buying Price         : {money(buying)}")
        print(f"Selling Price        : {money(selling)}")
        print(f"Profit / Unit        : {money(unit_profit)}")
        print(f"Gross Margin         : {margin:.2f}%")
        print(f"Target Selling Price : {money(target_price)}")
        print(f"Current Stock        : {stock:g} {unit}")
        print(f"Inventory Capital    : {money(inventory_capital)}")
        print(f"Status               : {status}")

    print("\n========================================")
    print("       PORTFOLIO PROFITABILITY")
    print("========================================")

    below_target = 0
    target_achieved = 0

    for product in products:

        buying = float(product["buying_price"] or 0)
        selling = float(product["selling_price"] or 0)

        margin = calculate_margin(
            buying,
            selling
        )

        if selling > 0 and selling >= buying:

            if margin < TARGET_MARGIN:
                below_target += 1
            else:
                target_achieved += 1

    print(f"Products Analyzed    : {len(products)}")
    print(f"Target Achieved      : {target_achieved}")
    print(f"Below Target         : {below_target}")
    print(
        f"Inventory Capital    : "
        f"{money(total_inventory_capital)}"
    )

    print("\n========================================")
    print("       MANAGEMENT ACTIONS")
    print("========================================")

    if actions:

        for index, action in enumerate(
            actions,
            start=1
        ):

            priority, product_name, action_text = action

            print(f"\n{index}. [{priority}] {product_name}")
            print(f"Action : {action_text}")

    else:

        print("\nAll products currently meet the")
        print(
            f"{TARGET_MARGIN:.0f}% gross-margin target."
        )

    print("\n========================================")
    print("       V46 MODULE STATUS")
    print("========================================")
    print("Mode                : READ-ONLY")
    print("Database modified   : NO")
    print("Products modified   : NO")
    print("Sales modified      : NO")
    print("Inventory modified  : NO")
    print("Balance modified    : NO")
    print("Credit modified     : NO")
    print("========================================")

    conn.close()


if __name__ == "__main__":
    product_profitability_v46()
