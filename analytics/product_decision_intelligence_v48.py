"""
POS Ledger NG V48
Product Decision Intelligence

READ-ONLY.
Combines:
- Product profitability
- Sales movement
- Inventory exposure
- Management recommendation
"""

from database.connection import get_connection


TARGET_MARGIN = 0.10


def product_decision_intelligence_v48():

    print("\n========================================")
    print("       POS LEDGER NG V48")
    print("   PRODUCT DECISION INTELLIGENCE")
    print("========================================")

    conn = get_connection()

    try:
        cur = conn.cursor()

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

        strong = 0
        pricing = 0
        growth = 0
        high_risk = 0

        total_inventory = 0.0
        total_profit = 0.0
        total_revenue = 0.0

        decisions = []

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

            profit_per_unit = selling_price - buying_price

            if selling_price > 0:
                margin = profit_per_unit / selling_price
            else:
                margin = 0.0

            inventory_capital = buying_price * current_stock

            sales = cur.execute("""
                SELECT
                    COALESCE(SUM(quantity), 0),
                    COALESCE(SUM(total_amount), 0),
                    COALESCE(SUM(total_profit), 0),
                    COUNT(DISTINCT substr(sale_date, 1, 10))
                FROM sales
                WHERE product_id = ?
                  AND status = 'COMPLETED'
            """, (product_id,)).fetchone()

            units_sold = float(sales[0] or 0)
            revenue = float(sales[1] or 0)
            profit = float(sales[2] or 0)
            active_days = int(sales[3] or 0)

            if active_days > 0:
                units_per_day = units_sold / active_days
            else:
                units_per_day = 0.0

            total_inventory += inventory_capital
            total_revenue += revenue
            total_profit += profit

            margin_ok = margin >= TARGET_MARGIN
            movement_ok = units_per_day >= 2.0

            if margin_ok and movement_ok:
                decision = "🟢 STRONG PRODUCT"
                action = "Maintain pricing and stock availability."
                strong += 1

            elif margin_ok and not movement_ok:
                decision = "🟡 GROWTH OPPORTUNITY"
                action = (
                    "Maintain margin but improve product sales activity."
                )
                growth += 1

            elif not margin_ok and movement_ok:
                decision = "🟠 PRICING OPPORTUNITY"
                action = (
                    "Review selling price or buying cost. "
                    "Demand is strong but margin is below target."
                )
                pricing += 1

                decisions.append({
                    "priority": "HIGH",
                    "product": product_name,
                    "decision": decision,
                    "action": action
                })

            else:
                decision = "🔴 HIGH RISK"
                action = (
                    "Review price, demand and stock level "
                    "before additional purchasing."
                )
                high_risk += 1

                decisions.append({
                    "priority": "HIGH",
                    "product": product_name,
                    "decision": decision,
                    "action": action
                })

            print("\n----------------------------------------")
            print("Product              :", product_name)
            print("SKU                  :", sku)
            print("Buying Price         :", f"₦{buying_price:,.2f}")
            print("Selling Price        :", f"₦{selling_price:,.2f}")
            print("Profit / Unit        :", f"₦{profit_per_unit:,.2f}")
            print("Gross Margin         :", f"{margin * 100:.2f}%")
            print("Units Sold           :", f"{units_sold:g}")
            print("Units / Active Day   :", f"{units_per_day:.2f}")
            print("Current Stock        :", f"{current_stock:g} {unit}")
            print(
                "Inventory Capital    :",
                f"₦{inventory_capital:,.2f}"
            )
            print("Revenue              :", f"₦{revenue:,.2f}")
            print("Profit               :", f"₦{profit:,.2f}")
            print("Decision             :", decision)
            print("Management Action    :", action)

        print("\n========================================")
        print("       PORTFOLIO DECISION SUMMARY")
        print("========================================")

        print("Products Analyzed    :", len(products))
        print("Strong Products      :", strong)
        print("Pricing Opportunities:", pricing)
        print("Growth Opportunities :", growth)
        print("High Risk Products   :", high_risk)

        print(
            "Inventory Capital    :",
            f"₦{total_inventory:,.2f}"
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
        print("       PRIORITIZED DECISIONS")
        print("========================================")

        if decisions:

            for index, item in enumerate(decisions, start=1):

                print(
                    f"\n{index}. "
                    f"[{item['priority']}] "
                    f"{item['product']}"
                )

                print(
                    "Decision :",
                    item["decision"]
                )

                print(
                    "Action   :",
                    item["action"]
                )

        else:
            print("\nNo immediate product decisions required.")

        print("\n========================================")
        print("       V48 MODULE STATUS")
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
    product_decision_intelligence_v48()
