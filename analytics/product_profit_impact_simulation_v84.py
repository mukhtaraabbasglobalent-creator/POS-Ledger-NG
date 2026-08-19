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
    print("POS LEDGER NG V84")
    print("PRODUCT PROFIT IMPACT & PRICING SIMULATION INTELLIGENCE")
    print("=" * 60)

    conn = get_connection()
    conn.row_factory = sqlite3.Row

    try:
        rows = conn.execute("""
            SELECT
                s.id,
                s.product_id,
                s.quantity,
                s.total_amount,
                s.cost_snapshot,
                s.cogs,
                s.gross_profit,
                s.gross_margin,
                p.product_name,
                p.sku
            FROM sales s
            LEFT JOIN products p
                ON p.id = s.product_id
            WHERE UPPER(COALESCE(s.status, 'COMPLETED')) = 'COMPLETED'
              AND s.cogs IS NOT NULL
              AND s.cost_snapshot IS NOT NULL
            ORDER BY s.product_id, s.id
        """).fetchall()

        if not rows:
            print("\nNo verified profitability records found.")
            return

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

            quantity = float(row["quantity"] or 0)
            revenue = float(row["total_amount"] or 0)
            cogs = float(row["cogs"] or 0)

            products[pid]["units"] += quantity
            products[pid]["revenue"] += revenue
            products[pid]["cogs"] += cogs
            products[pid]["sales"] += 1

        print("\n" + "=" * 60)
        print("VERIFIED BUSINESS BASELINE")
        print("=" * 60)

        total_revenue = sum(x["revenue"] for x in products.values())
        total_cogs = sum(x["cogs"] for x in products.values())
        total_profit = total_revenue - total_cogs

        baseline_margin = (
            total_profit / total_revenue
            if total_revenue else 0
        )

        print(f"Verified Revenue      : {money(total_revenue)}")
        print(f"Verified COGS         : {money(total_cogs)}")
        print(f"Verified Gross Profit : {money(total_profit)}")
        print(f"Verified Gross Margin : {pct(baseline_margin)}")
        print(f"Target Margin         : {pct(TARGET_MARGIN)}")

        print("\n" + "=" * 60)
        print("PRODUCT PROFIT IMPACT SIMULATION")
        print("=" * 60)

        overall_current_profit = 0.0
        overall_target_profit = 0.0

        for index, data in enumerate(products.values(), 1):

            units = data["units"]
            revenue = data["revenue"]
            cogs = data["cogs"]

            if units <= 0:
                continue

            cost_per_unit = cogs / units
            current_price = revenue / units

            current_profit_unit = current_price - cost_per_unit
            current_margin = (
                current_profit_unit / current_price
                if current_price else 0
            )

            target_price = (
                cost_per_unit / (1 - TARGET_MARGIN)
                if TARGET_MARGIN < 1
                else current_price
            )

            conservative_price = current_price

            if current_margin < TARGET_MARGIN:
                conservative_price = current_price + (
                    target_price - current_price
                ) * 0.50

            target_profit_unit = target_price - cost_per_unit
            conservative_profit_unit = (
                conservative_price - cost_per_unit
            )

            current_total_profit = current_profit_unit * units
            conservative_total_profit = (
                conservative_profit_unit * units
            )
            target_total_profit = target_profit_unit * units

            overall_current_profit += current_total_profit
            overall_target_profit += target_total_profit

            print("-" * 40)
            print(f"{index}. {data['name']}")
            print(f"SKU                    : {data['sku']}")
            print(f"Verified Sales         : {data['sales']}")
            print(f"Units Sold             : {units:.2f}")
            print(f"Verified Revenue       : {money(revenue)}")
            print(f"Verified COGS          : {money(cogs)}")
            print(f"Cost/Unit              : {money(cost_per_unit)}")

            print("\nCURRENT SCENARIO")
            print(f"Price/Unit             : {money(current_price)}")
            print(f"Profit/Unit            : {money(current_profit_unit)}")
            print(f"Margin                 : {pct(current_margin)}")
            print(f"Profit on Sold Units   : {money(current_total_profit)}")

            print("\nCONSERVATIVE SCENARIO")
            print(f"Simulated Price/Unit   : {money(conservative_price)}")
            print(
                f"Simulated Profit/Unit : "
                f"{money(conservative_profit_unit)}"
            )
            print(
                f"Simulated Margin      : "
                f"{pct(conservative_profit_unit / conservative_price)}"
            )
            print(
                f"Projected Profit      : "
                f"{money(conservative_total_profit)}"
            )
            print(
                f"Profit Improvement    : "
                f"{money(conservative_total_profit - current_total_profit)}"
            )

            print("\nTARGET SCENARIO")
            print(f"Target Price/Unit      : {money(target_price)}")
            print(f"Target Profit/Unit     : {money(target_profit_unit)}")
            print(f"Target Margin          : {pct(TARGET_MARGIN)}")
            print(
                f"Projected Profit       : "
                f"{money(target_total_profit)}"
            )
            print(
                f"Profit Improvement     : "
                f"{money(target_total_profit - current_total_profit)}"
            )

            print("\nVOLUME IMPACT")
            for volume in (10, 50, 100):
                current_volume_profit = current_profit_unit * volume
                target_volume_profit = target_profit_unit * volume
                impact = target_volume_profit - current_volume_profit

                print(
                    f"{volume:>3} units -> "
                    f"Current: {money(current_volume_profit)} | "
                    f"Target: {money(target_volume_profit)} | "
                    f"Impact: {money(impact)}"
                )

        print("\n" + "=" * 60)
        print("PORTFOLIO PROFITABILITY IMPACT")
        print("=" * 60)

        current_portfolio_profit = total_profit
        target_portfolio_profit = overall_target_profit

        portfolio_gain = (
            target_portfolio_profit -
            current_portfolio_profit
        )

        print(
            f"Current Verified Profit : "
            f"{money(current_portfolio_profit)}"
        )
        print(
            f"Target Simulated Profit : "
            f"{money(target_portfolio_profit)}"
        )
        print(
            f"Potential Profit Gain   : "
            f"{money(portfolio_gain)}"
        )

        print("\n" + "=" * 60)
        print("V84 MANAGEMENT DECISION")
        print("=" * 60)

        if baseline_margin < TARGET_MARGIN:
            print("🟠 PROFITABILITY IMPROVEMENT AVAILABLE")
            print(
                f"Current portfolio margin: "
                f"{pct(baseline_margin)}"
            )
            print(
                f"Target portfolio margin : "
                f"{pct(TARGET_MARGIN)}"
            )
        else:
            print("🟢 PORTFOLIO TARGET ACHIEVED")

        print("\nRecommended approach:")
        print("1. Review products below the target margin.")
        print("2. Consider conservative price adjustments first.")
        print("3. Compare proposed prices with market conditions.")
        print("4. Monitor customer demand after any real price change.")
        print("5. Never change live prices automatically from analytics.")

        print("\n" + "=" * 60)
        print("V84 MANAGEMENT INTERPRETATION")
        print("=" * 60)

        print(
            "V84 simulates the financial effect of pricing changes "
            "using verified historical profitability."
        )

        print(
            "The simulation separates current performance from "
            "conservative and target pricing scenarios."
        )

        print(
            "Projected gains are analytical scenarios, not guaranteed "
            "future profit, because customer demand and sales volume "
            "may change after a price adjustment."
        )

        print("\n" + "=" * 60)
        print("V84 DATA INTEGRITY STATUS")
        print("=" * 60)
        print("Verified profitability source : V81/V82")
        print("Historical COGS required      : YES")
        print("Verified sales used           : YES")
        print("Automatic price changes       : NO")

        print("\n" + "=" * 60)
        print("V84 SAFETY STATUS")
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
