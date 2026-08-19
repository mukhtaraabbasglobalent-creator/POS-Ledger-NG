import sqlite3
from pathlib import Path

DB_PATH = Path("data/posledger.db")
TARGET_MARGIN = 0.10


def money(value):
    return f"₦{value:,.2f}"


def pct(value):
    return f"{value * 100:.2f}%"


def scenario_price(cost, margin):
    if margin >= 1:
        return cost
    return cost / (1 - margin)


def get_sales_data(conn):
    rows = conn.execute("""
        SELECT
            s.product_id,
            s.quantity,
            s.total_amount,
            s.cost_snapshot,
            s.cogs,
            p.product_name,
            p.sku
        FROM sales s
        LEFT JOIN products p
            ON p.id = s.product_id
        WHERE UPPER(COALESCE(s.status, 'COMPLETED')) = 'COMPLETED'
          AND s.cost_snapshot IS NOT NULL
          AND s.cogs IS NOT NULL
    """).fetchall()

    products = {}

    for row in rows:
        pid = row["product_id"]

        if pid not in products:
            products[pid] = {
                "name": row["product_name"] or "Unknown Product",
                "sku": row["sku"] or "N/A",
                "units": 0.0,
                "revenue": 0.0,
                "cogs": 0.0,
                "sales": 0
            }

        products[pid]["units"] += float(row["quantity"] or 0)
        products[pid]["revenue"] += float(row["total_amount"] or 0)
        products[pid]["cogs"] += float(row["cogs"] or 0)
        products[pid]["sales"] += 1

    return products


def main():
    print("=" * 60)
    print("POS LEDGER NG V85")
    print("DEMAND & VOLUME IMPACT INTELLIGENCE")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        products = get_sales_data(conn)

        if not products:
            print("\nNo verified profitability data available.")
            return

        total_current_profit = 0.0
        total_target_profit = 0.0
        total_target_revenue = 0.0

        print("\n" + "=" * 60)
        print("VERIFIED BUSINESS BASELINE")
        print("=" * 60)

        total_revenue = sum(x["revenue"] for x in products.values())
        total_cogs = sum(x["cogs"] for x in products.values())
        total_profit = total_revenue - total_cogs

        print(f"Verified Revenue      : {money(total_revenue)}")
        print(f"Verified COGS         : {money(total_cogs)}")
        print(f"Verified Gross Profit : {money(total_profit)}")
        print(
            f"Verified Gross Margin : "
            f"{pct(total_profit / total_revenue if total_revenue else 0)}"
        )

        print("\n" + "=" * 60)
        print("DEMAND / VOLUME SCENARIO ANALYSIS")
        print("=" * 60)

        for index, data in enumerate(products.values(), 1):

            units = data["units"]
            revenue = data["revenue"]
            cogs = data["cogs"]

            if units <= 0:
                continue

            cost = cogs / units
            current_price = revenue / units

            current_profit_unit = current_price - cost
            current_margin = (
                current_profit_unit / current_price
                if current_price else 0
            )

            target_price = scenario_price(cost, TARGET_MARGIN)

            price_gap = target_price - current_price

            if price_gap <= 0:
                conservative_price = current_price
            else:
                conservative_price = (
                    current_price + price_gap * 0.50
                )

            print("-" * 40)
            print(f"{index}. {data['name']}")
            print(f"SKU                  : {data['sku']}")
            print(f"Historical Units     : {units:.2f}")
            print(f"Current Price/Unit   : {money(current_price)}")
            print(f"Verified Cost/Unit   : {money(cost)}")
            print(f"Current Margin       : {pct(current_margin)}")
            print(f"Target Price/Unit    : {money(target_price)}")
            print(
                f"Conservative Price   : "
                f"{money(conservative_price)}"
            )

            scenarios = [
                ("CURRENT", current_price, 1.00),
                ("MILD VOLUME LOSS", conservative_price, 0.90),
                ("MODERATE VOLUME LOSS", target_price, 0.75),
                ("HIGH VOLUME LOSS", target_price, 0.60),
                ("SEVERE VOLUME LOSS", target_price, 0.50),
            ]

            print("\nSCENARIOS")

            scenario_results = []

            for name, price, volume_factor in scenarios:

                projected_units = units * volume_factor
                profit_unit = price - cost
                projected_profit = profit_unit * projected_units
                projected_revenue = price * projected_units
                margin = (
                    profit_unit / price
                    if price else 0
                )

                scenario_results.append({
                    "name": name,
                    "price": price,
                    "units": projected_units,
                    "profit": projected_profit,
                    "revenue": projected_revenue,
                    "margin": margin
                })

                print(
                    f"{name:<22} "
                    f"Price {money(price)} | "
                    f"Units {projected_units:.2f} | "
                    f"Profit {money(projected_profit)} | "
                    f"Margin {pct(margin)}"
                )

            current_profit = scenario_results[0]["profit"]
            target_scenario = scenario_results[2]

            total_current_profit += current_profit
            total_target_profit += target_scenario["profit"]
            total_target_revenue += target_scenario["revenue"]

            print("\nBREAK-EVEN VOLUME ANALYSIS")

            target_profit_unit = target_price - cost

            if target_profit_unit > 0:
                break_even_units = (
                    current_profit / target_profit_unit
                )
            else:
                break_even_units = units

            required_volume_retention = (
                break_even_units / units
                if units else 0
            )

            volume_loss_tolerance = (
                1 - required_volume_retention
            )

            print(
                f"Target Profit/Unit      : "
                f"{money(target_profit_unit)}"
            )
            print(
                f"Current Profit Baseline : "
                f"{money(current_profit)}"
            )
            print(
                f"Minimum Target Units    : "
                f"{break_even_units:.2f}"
            )
            print(
                f"Required Volume Retention: "
                f"{pct(required_volume_retention)}"
            )
            print(
                f"Maximum Volume Loss     : "
                f"{pct(volume_loss_tolerance)}"
            )

            if volume_loss_tolerance >= 0.25:
                risk = "🟢 LOW"
            elif volume_loss_tolerance >= 0.10:
                risk = "🟡 MODERATE"
            else:
                risk = "🔴 HIGH"

            print(f"Pricing Demand Risk      : {risk}")

        print("\n" + "=" * 60)
        print("PORTFOLIO DEMAND IMPACT")
        print("=" * 60)

        profit_gain = total_target_profit - total_current_profit

        print(
            f"Current Profit Baseline : "
            f"{money(total_current_profit)}"
        )
        print(
            f"Target Scenario Profit  : "
            f"{money(total_target_profit)}"
        )
        print(
            f"Potential Profit Change : "
            f"{money(profit_gain)}"
        )
        print(
            f"Target Scenario Revenue : "
            f"{money(total_target_revenue)}"
        )

        print("\n" + "=" * 60)
        print("V85 MANAGEMENT DECISION")
        print("=" * 60)

        if profit_gain > 0:
            print("🟢 TARGET PRICING CAN REMAIN PROFITABLE")
            print(
                "The business may tolerate some volume reduction "
                "while preserving or improving profit."
            )
        else:
            print("🔴 TARGET PRICING REQUIRES CAUTION")
            print(
                "The simulated volume reduction may eliminate "
                "the expected pricing benefit."
            )

        print("\nRecommended management process:")
        print("1. Test customer demand before major price changes.")
        print("2. Prefer gradual price adjustments.")
        print("3. Monitor units sold after each adjustment.")
        print("4. Compare actual volume against simulated volume.")
        print("5. Do not assume historical demand will remain constant.")
        print("6. Never automatically change live product prices.")

        print("\n" + "=" * 60)
        print("V85 MANAGEMENT INTERPRETATION")
        print("=" * 60)

        print(
            "V85 evaluates the relationship between price changes, "
            "sales volume and profitability."
        )

        print(
            "The module calculates the minimum sales volume required "
            "for a target price to preserve the current profit level."
        )

        print(
            "Demand scenarios are simulations only. Actual customer "
            "behavior must be measured after any real price change."
        )

        print("\n" + "=" * 60)
        print("V85 DATA INTEGRITY STATUS")
        print("=" * 60)
        print("Profitability source    : VERIFIED V81/V82")
        print("Pricing source          : V83/V84")
        print("Historical COGS         : VERIFIED")
        print("Demand observations     : SIMULATED")
        print("Automatic price change  : NO")

        print("\n" + "=" * 60)
        print("V85 SAFETY STATUS")
        print("=" * 60)
        print("Mode                : READ-ONLY")
        print("Database modified   : NO")
        print("Sales modified      : NO")
        print("Products modified   : NO")
        print("Inventory modified  : NO")
        print("Balance modified    : NO")
        print("Credit modified     : NO")
        print("Suppliers modified  : NO")
        print("Expenses modified   : NO")
        print("=" * 60)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
