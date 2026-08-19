"""
POS Ledger NG V47
Inventory Movement Intelligence

READ-ONLY.
Does not modify products, sales, inventory, balances,
customers, creditors, or expenses.
"""

from database.connection import get_connection


def inventory_movement_intelligence_v47():

    print("\n========================================")
    print("       POS LEDGER NG V47")
    print(" INVENTORY MOVEMENT INTELLIGENCE")
    print("========================================")

    conn = get_connection()
    conn.row_factory = None
    cur = conn.cursor()

    try:
        products = cur.execute("""
            SELECT
                id,
                product_name,
                sku,
                buying_price,
                selling_price,
                current_stock,
                unit
            FROM products
            ORDER BY product_name
        """).fetchall()

        if not products:
            print("\nNo products found.")
            return

        print("\nPRODUCT MOVEMENT")
        print("----------------------------------------")

        analyzed = 0
        fast = 0
        moderate = 0
        slow = 0
        no_sales = 0

        total_inventory_capital = 0.0
        total_revenue = 0.0
        total_profit = 0.0

        actions = []

        for product in products:

            (
                product_id,
                product_name,
                sku,
                buying_price,
                selling_price,
                current_stock,
                unit
            ) = product

            buying_price = float(buying_price or 0)
            selling_price = float(selling_price or 0)
            current_stock = float(current_stock or 0)

            inventory_capital = buying_price * current_stock

            sales = cur.execute("""
                SELECT
                    COALESCE(SUM(quantity), 0),
                    COUNT(*),
                    COALESCE(SUM(total_amount), 0),
                    COALESCE(SUM(total_profit), 0),
                    COUNT(DISTINCT substr(sale_date, 1, 10))
                FROM sales
                WHERE product_id = ?
                  AND status = 'COMPLETED'
            """, (product_id,)).fetchone()

            units_sold = float(sales[0] or 0)
            sales_count = int(sales[1] or 0)
            revenue = float(sales[2] or 0)
            profit = float(sales[3] or 0)
            active_days = int(sales[4] or 0)

            if active_days > 0:
                units_per_day = units_sold / active_days
            else:
                units_per_day = 0.0

            total_inventory_capital += inventory_capital
            total_revenue += revenue
            total_profit += profit

            analyzed += 1

            if units_sold == 0:
                movement = "⚪ NO RECORDED SALES"
                no_sales += 1

                if current_stock > 0:
                    actions.append({
                        "priority": "HIGH",
                        "product": product_name,
                        "action": (
                            "Review stock demand before purchasing more."
                        ),
                        "reason": (
                            f"{current_stock:g} {unit} currently in stock "
                            "with no recorded completed sales."
                        )
                    })

            elif units_per_day >= 2:
                movement = "🟢 FAST MOVING"
                fast += 1

            elif units_per_day >= 0.5:
                movement = "🟡 MODERATE"
                moderate += 1

            else:
                movement = "🟠 SLOW MOVING"
                slow += 1

                if current_stock > 0:
                    actions.append({
                        "priority": "MEDIUM",
                        "product": product_name,
                        "action": (
                            "Monitor stock and avoid unnecessary "
                            "additional purchases."
                        ),
                        "reason": (
                            f"Average movement is only "
                            f"{units_per_day:.2f} unit(s) per active day."
                        )
                    })

            print("\nProduct              :", product_name)
            print("SKU                  :", sku)
            print("Current Stock        :", f"{current_stock:g} {unit}")
            print(
                "Inventory Capital    :",
                f"₦{inventory_capital:,.2f}"
            )
            print("Units Sold           :", f"{units_sold:g}")
            print("Completed Sales      :", sales_count)
            print("Revenue              :", f"₦{revenue:,.2f}")
            print("Profit               :", f"₦{profit:,.2f}")
            print("Active Sales Days    :", active_days)
            print(
                "Units / Active Day  :",
                f"{units_per_day:.2f}"
            )
            print("Movement Status      :", movement)

        print("\n========================================")
        print("       PORTFOLIO MOVEMENT SUMMARY")
        print("========================================")

        print("Products Analyzed    :", analyzed)
        print("Fast Moving         :", fast)
        print("Moderate             :", moderate)
        print("Slow Moving          :", slow)
        print("No Recorded Sales    :", no_sales)

        print(
            "Inventory Capital    :",
            f"₦{total_inventory_capital:,.2f}"
        )

        print(
            "Recorded Revenue     :",
            f"₦{total_revenue:,.2f}"
        )

        print(
            "Recorded Profit      :",
            f"₦{total_profit:,.2f}"
        )

        print("\n========================================")
        print("       MANAGEMENT ACTIONS")
        print("========================================")

        if actions:

            for index, item in enumerate(actions, start=1):

                print(
                    f"\n{index}. "
                    f"[{item['priority']}] "
                    f"{item['product']}"
                )

                print(
                    "Action :",
                    item["action"]
                )

                print(
                    "Reason :",
                    item["reason"]
                )

        else:
            print(
                "\nNo immediate inventory movement "
                "actions detected."
            )

        print("\n========================================")
        print("       V47 MODULE STATUS")
        print("========================================")
        print("Mode                : READ-ONLY")
        print("Database modified   : NO")
        print("Products modified   : NO")
        print("Sales modified      : NO")
        print("Inventory modified  : NO")
        print("Balance modified    : NO")
        print("Credit modified     : NO")
        print("========================================")

    finally:
        conn.close()


if __name__ == "__main__":
    inventory_movement_intelligence_v47()
