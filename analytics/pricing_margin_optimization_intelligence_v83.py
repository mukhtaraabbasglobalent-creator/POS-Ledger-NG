import sqlite3
from pathlib import Path

DB_PATH = Path("data/posledger.db")
TARGET_MARGIN = 0.10


def money(value):
    return f"₦{value:,.2f}"


def pct(value):
    return f"{value * 100:.2f}%"


def get_connection():
    return sqlite3.connect(DB_PATH)


def main():
    print("=" * 60)
    print("POS LEDGER NG V83")
    print("PRICING & MARGIN OPTIMIZATION INTELLIGENCE")
    print("=" * 60)

    conn = get_connection()
    conn.row_factory = sqlite3.Row

    try:
        sales = conn.execute("""
            SELECT
                s.product_id,
                s.quantity,
                s.total_amount,
                s.cost_snapshot,
                s.cogs,
                s.gross_profit,
                s.gross_margin,
                p.product_name,
                p.sku,
                p.selling_price,
                p.buying_price
            FROM sales s
            LEFT JOIN products p ON p.id = s.product_id
            WHERE UPPER(COALESCE(s.status, 'COMPLETED')) = 'COMPLETED'
            ORDER BY s.product_id, s.id
        """).fetchall()

        if not sales:
            print("\nNo completed sales found.")
            return

        products = {}

        for row in sales:
            product_id = row["product_id"]
            quantity = float(row["quantity"] or 0)
            revenue = float(row["total_amount"] or 0)
            cogs = row["cogs"]

            if cogs is None:
                continue

            cogs = float(cogs)

            if product_id not in products:
                products[product_id] = {
                    "name": row["product_name"] or "Unknown Product",
                    "sku": row["sku"] or "N/A",
                    "units": 0.0,
                    "revenue": 0.0,
                    "cogs": 0.0,
                    "sales": 0,
                    "current_price": float(row["selling_price"] or 0),
                    "current_cost": float(row["buying_price"] or 0),
                }

            products[product_id]["units"] += quantity
            products[product_id]["revenue"] += revenue
            products[product_id]["cogs"] += cogs
            products[product_id]["sales"] += 1

        print("\n" + "=" * 60)
        print("VERIFIED PRICING POSITION")
        print("=" * 60)

        if not products:
            print("No verified profitability records available.")
            return

        total_revenue = sum(x["revenue"] for x in products.values())
        total_cogs = sum(x["cogs"] for x in products.values())
        total_profit = total_revenue - total_cogs

        print(f"Verified Revenue     : {money(total_revenue)}")
        print(f"Verified COGS        : {money(total_cogs)}")
        print(f"Verified Gross Profit: {money(total_profit)}")
        print(
            f"Verified Gross Margin: "
            f"{pct(total_profit / total_revenue) if total_revenue else '0.00%'}"
        )
        print(f"Management Target    : {pct(TARGET_MARGIN)}")

        print("\n" + "=" * 60)
        print("PRODUCT PRICING ANALYSIS")
        print("=" * 60)

        optimization = []

        for i, data in enumerate(products.values(), 1):
            units = data["units"]
            revenue = data["revenue"]
            cogs = data["cogs"]
            profit = revenue - cogs

            if units <= 0:
                continue

            historical_cost_per_unit = cogs / units
            actual_price_per_unit = revenue / units

            current_margin = (
                profit / revenue if revenue > 0 else 0
            )

            # Price required for target gross margin:
            # margin = (price - cost) / price
            # price = cost / (1 - margin)
            target_price = (
                historical_cost_per_unit / (1 - TARGET_MARGIN)
                if TARGET_MARGIN < 1
                else 0
            )

            target_profit_per_unit = (
                target_price - historical_cost_per_unit
            )

            current_profit_per_unit = (
                actual_price_per_unit - historical_cost_per_unit
            )

            price_gap = target_price - actual_price_per_unit

            if current_margin < TARGET_MARGIN:
                status = "🟠 BELOW TARGET"
            else:
                status = "🟢 TARGET MET"

            print("-" * 40)
            print(f"{i}. {data['name']}")
            print(f"SKU                 : {data['sku']}")
            print(f"Sales               : {data['sales']}")
            print(f"Units Sold          : {units:.2f}")
            print(f"Revenue             : {money(revenue)}")
            print(f"Verified COGS       : {money(cogs)}")
            print(f"Cost/Unit           : {money(historical_cost_per_unit)}")
            print(f"Actual Price/Unit   : {money(actual_price_per_unit)}")
            print(f"Current Margin      : {pct(current_margin)}")
            print(f"Target Margin       : {pct(TARGET_MARGIN)}")
            print(f"Target Price/Unit   : {money(target_price)}")
            print(f"Price Gap           : {money(price_gap)}")
            print(f"Current Profit/Unit : {money(current_profit_per_unit)}")
            print(f"Target Profit/Unit  : {money(target_profit_per_unit)}")
            print(f"Status              : {status}")

            optimization.append({
                "name": data["name"],
                "margin": current_margin,
                "target_price": target_price,
                "actual_price": actual_price_per_unit,
                "gap": price_gap,
                "profit": profit,
                "units": units,
            })

        print("\n" + "=" * 60)
        print("PRICING OPTIMIZATION SUMMARY")
        print("=" * 60)

        below_target = [
            x for x in optimization
            if x["margin"] < TARGET_MARGIN
        ]

        target_met = [
            x for x in optimization
            if x["margin"] >= TARGET_MARGIN
        ]

        print(f"Products Analyzed    : {len(optimization)}")
        print(f"Below Target         : {len(below_target)}")
        print(f"Target Met           : {len(target_met)}")

        if below_target:
            print("\nPRODUCTS REQUIRING PRICING REVIEW")

            for item in sorted(
                below_target,
                key=lambda x: x["margin"]
            ):
                print("-" * 40)
                print(f"Product              : {item['name']}")
                print(f"Current Price/Unit   : {money(item['actual_price'])}")
                print(f"Target Price/Unit    : {money(item['target_price'])}")
                print(f"Required Price Gap   : {money(item['gap'])}")
                print(f"Current Margin       : {pct(item['margin'])}")
                print(f"Target Margin        : {pct(TARGET_MARGIN)}")

        print("\n" + "=" * 60)
        print("V83 MANAGEMENT SIGNAL")
        print("=" * 60)

        overall_margin = (
            total_profit / total_revenue
            if total_revenue else 0
        )

        margin_gap = max(TARGET_MARGIN - overall_margin, 0)

        if margin_gap > 0:
            print("🟠 MARGIN OPTIMIZATION REQUIRED")
            print(f"Overall Margin Gap   : {pct(margin_gap)}")
        else:
            print("🟢 TARGET MARGIN ACHIEVED")

        print("\n" + "=" * 60)
        print("V83 MANAGEMENT INTERPRETATION")
        print("=" * 60)

        print(
            "V83 uses verified historical profitability data from V81/V82 "
            "to identify products whose pricing is below the management target."
        )

        if below_target:
            print(
                f"{len(below_target)} product(s) require pricing review "
                f"to reach the {pct(TARGET_MARGIN)} gross-margin target."
            )
        else:
            print(
                "All analyzed products currently meet the management "
                "margin target."
            )

        print(
            "Target prices are analytical recommendations only and should "
            "be reviewed against market prices, competition, customer "
            "demand and business pricing policy before implementation."
        )

        print("\n" + "=" * 60)
        print("V83 SAFETY STATUS")
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
