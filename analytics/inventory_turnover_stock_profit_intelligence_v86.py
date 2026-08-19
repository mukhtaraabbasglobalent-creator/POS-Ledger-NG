import sqlite3
from pathlib import Path

DB_PATH = Path("data/posledger.db")


def money(value):
    return f"₦{value:,.2f}"


def pct(value):
    return f"{value * 100:.2f}%"


def main():
    print("=" * 60)
    print("POS LEDGER NG V86")
    print("INVENTORY TURNOVER & STOCK-PROFIT INTELLIGENCE")
    print("=" * 60)

    if not DB_PATH.exists():
        print("\nDatabase not found:", DB_PATH)
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        products = conn.execute("""
            SELECT
                id,
                product_name,
                sku,
                buying_price,
                selling_price,
                current_stock
            FROM products
            ORDER BY product_name
        """).fetchall()

        sales = conn.execute("""
            SELECT
                s.product_id,
                SUM(s.quantity) AS units_sold,
                SUM(s.total_amount) AS revenue,
                SUM(COALESCE(s.cogs, 0)) AS cogs,
                SUM(
                    COALESCE(
                        s.gross_profit,
                        s.total_amount - COALESCE(s.cogs, 0)
                    )
                ) AS gross_profit
            FROM sales s
            WHERE UPPER(COALESCE(s.status, 'COMPLETED')) = 'COMPLETED'
            GROUP BY s.product_id
        """).fetchall()

        sales_map = {row["product_id"]: row for row in sales}

        print("\n" + "=" * 60)
        print("VERIFIED INVENTORY POSITION")
        print("=" * 60)

        total_inventory_capital = 0.0
        total_units_stock = 0.0
        total_units_sold = 0.0
        total_revenue = 0.0
        total_profit = 0.0

        analysis = []

        for product in products:
            stock = float(product["current_stock"] or 0)
            cost = float(product["buying_price"] or 0)
            selling = float(product["selling_price"] or 0)

            capital = stock * cost

            sale = sales_map.get(product["id"])

            units_sold = float(sale["units_sold"] or 0) if sale else 0.0
            revenue = float(sale["revenue"] or 0) if sale else 0.0
            profit = float(sale["gross_profit"] or 0) if sale else 0.0

            margin = profit / revenue if revenue > 0 else 0.0

            total_inventory_capital += capital
            total_units_stock += stock
            total_units_sold += units_sold
            total_revenue += revenue
            total_profit += profit

            analysis.append({
                "name": product["product_name"],
                "sku": product["sku"] or "N/A",
                "stock": stock,
                "cost": cost,
                "selling": selling,
                "capital": capital,
                "units_sold": units_sold,
                "revenue": revenue,
                "profit": profit,
                "margin": margin
            })

        print(f"Products analyzed       : {len(products)}")
        print(f"Units currently in stock : {total_units_stock:.2f}")
        print(f"Inventory capital        : {money(total_inventory_capital)}")
        print(f"Verified units sold      : {total_units_sold:.2f}")
        print(f"Verified sales revenue   : {money(total_revenue)}")
        print(f"Verified gross profit    : {money(total_profit)}")

        print("\n" + "=" * 60)
        print("PRODUCT INVENTORY & PROFIT ANALYSIS")
        print("=" * 60)

        for index, item in enumerate(analysis, 1):
            stock = item["stock"]
            units_sold = item["units_sold"]
            capital = item["capital"]
            profit = item["profit"]

            if stock > 0 and units_sold > 0:
                stock_to_sales = units_sold / stock
            else:
                stock_to_sales = 0.0

            profit_per_stock_capital = (
                profit / capital
                if capital > 0 else 0.0
            )

            print("-" * 40)
            print(f"{index}. {item['name']}")
            print(f"SKU                  : {item['sku']}")
            print(f"Current Stock        : {stock:.2f}")
            print(f"Buying Cost/Unit     : {money(item['cost'])}")
            print(f"Selling Price/Unit   : {money(item['selling'])}")
            print(f"Inventory Capital    : {money(capital)}")
            print(f"Verified Units Sold  : {units_sold:.2f}")
            print(f"Revenue              : {money(item['revenue'])}")
            print(f"Gross Profit         : {money(profit)}")
            print(f"Gross Margin         : {pct(item['margin'])}")
            print(f"Stock/Sales Activity : {stock_to_sales:.2f}")
            print(
                "Profit / Stock Capital: "
                f"{pct(profit_per_stock_capital)}"
            )

            if stock == 0:
                status = "🟡 NO CURRENT STOCK"
            elif units_sold == 0:
                status = "🔴 NO RECORDED SALES"
            elif stock_to_sales < 1:
                status = "🟢 STRONG TURNOVER"
            elif stock_to_sales < 3:
                status = "🟡 MONITOR TURNOVER"
            else:
                status = "🟠 HIGH STOCK RELATIVE TO SALES"

            print(f"Inventory Status     : {status}")

        print("\n" + "=" * 60)
        print("CAPITAL CONCENTRATION")
        print("=" * 60)

        if total_inventory_capital > 0:
            for item in sorted(
                analysis,
                key=lambda x: x["capital"],
                reverse=True
            ):
                share = item["capital"] / total_inventory_capital
                if share > 0:
                    print(
                        f"{item['name']:<25} "
                        f"{money(item['capital']):>14} | "
                        f"{pct(share)}"
                    )

        print("\n" + "=" * 60)
        print("PROFIT CONTRIBUTION")
        print("=" * 60)

        if total_profit > 0:
            for item in sorted(
                analysis,
                key=lambda x: x["profit"],
                reverse=True
            ):
                share = item["profit"] / total_profit
                if item["profit"] > 0:
                    print(
                        f"{item['name']:<25} "
                        f"{money(item['profit']):>14} | "
                        f"{pct(share)}"
                    )

        print("\n" + "=" * 60)
        print("INVENTORY MANAGEMENT PRIORITIES")
        print("=" * 60)

        priorities = []

        for item in analysis:
            if item["stock"] > 0 and item["units_sold"] == 0:
                priorities.append(
                    (
                        "URGENT",
                        item["name"],
                        "Stock exists but no verified sales are recorded."
                    )
                )

            elif item["capital"] > 0 and item["profit"] <= 0:
                priorities.append(
                    (
                        "HIGH",
                        item["name"],
                        "Inventory capital is tied up without verified profit."
                    )
                )

            elif item["margin"] < 0.10 and item["units_sold"] > 0:
                priorities.append(
                    (
                        "HIGH",
                        item["name"],
                        "Product is selling below the 10% margin target."
                    )
                )

            elif item["stock"] > item["units_sold"] * 2:
                priorities.append(
                    (
                        "MEDIUM",
                        item["name"],
                        "Current stock is high relative to recorded sales."
                    )
                )

        if not priorities:
            print("No critical inventory exceptions detected.")
        else:
            for number, (level, name, reason) in enumerate(
                priorities, 1
            ):
                print("-" * 40)
                print(f"{number}. [{level}] {name}")
                print(f"Reason : {reason}")

        print("\n" + "=" * 60)
        print("V86 MANAGEMENT SIGNAL")
        print("=" * 60)

        if total_inventory_capital > total_revenue:
            print("🟠 HIGH INVENTORY CAPITAL EXPOSURE")
            print(
                "Inventory capital exceeds verified sales revenue. "
                "Turnover should be monitored before aggressive replenishment."
            )
        else:
            print("🟢 INVENTORY CAPITAL WITHIN REVENUE SCALE")
            print(
                "Current inventory capital is below verified sales revenue."
            )

        print("\n" + "=" * 60)
        print("V86 MANAGEMENT INTERPRETATION")
        print("=" * 60)

        print(
            "V86 connects verified profitability with current inventory "
            "capital and recorded sales activity."
        )

        print(
            "The module identifies products where capital is tied up, "
            "sales activity is weak, or profitability requires attention."
        )

        print(
            "Inventory recommendations are analytical only. "
            "V86 does not automatically purchase, remove, or reprice stock."
        )

        print("\n" + "=" * 60)
        print("V86 DATA INTEGRITY STATUS")
        print("=" * 60)
        print("Profitability source : VERIFIED V81/V82")
        print("Pricing source       : V83/V84")
        print("Demand source        : V85")
        print("Inventory source     : products.current_stock")
        print("Automatic stock change: NO")

        print("\n" + "=" * 60)
        print("V86 SAFETY STATUS")
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
