"""
POS LEDGER NG V92
MANAGEMENT SCENARIO & FORECAST INTELLIGENCE

Purpose:
- Build management scenarios from verified historical financial data.
- Compare current performance against target performance.
- Simulate gradual margin improvement.
- Estimate future revenue/profit using historical sales data.
- Estimate the effect of customer-credit recovery.
- Estimate inventory-capital release scenarios.
- Never modify database records.

READ-ONLY MODULE.
"""

import sqlite3
from pathlib import Path
from datetime import datetime


DB_PATH = Path("data/posledger.db")

TARGET_MARGIN = 0.10
TARGET_NET_MARGIN = 0.10


def money(value):
    return f"₦{value:,.2f}"


def pct(value):
    return f"{value:.2f}%"


def table_exists(conn, table):
    rows = conn.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' AND name=?",
        (table,),
    ).fetchall()

    return len(rows) > 0


def columns(conn, table):
    if not table_exists(conn, table):
        return []

    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()

    result = []

    for row in rows:
        if hasattr(row, "keys"):
            result.append(row["name"])
        else:
            result.append(row[1])

    return result


def column_exists(conn, table, column):
    return column in columns(conn, table)


def safe_sum(conn, table, column):
    if not column_exists(conn, table, column):
        return 0.0

    row = conn.execute(
        f"SELECT COALESCE(SUM({column}), 0) FROM {table}"
    ).fetchone()

    return float(row[0] or 0)


def get_verified_sales(conn):
    required = [
        "id",
        "quantity",
        "total_amount",
        "cost_snapshot",
        "cogs",
        "gross_profit",
    ]

    sales_columns = columns(conn, "sales")

    if not table_exists(conn, "sales"):
        return []

    if not all(c in sales_columns for c in required):
        return []

    return conn.execute(
        """
        SELECT
            id,
            quantity,
            total_amount,
            cost_snapshot,
            cogs,
            gross_profit
        FROM sales
        WHERE UPPER(COALESCE(status, 'COMPLETED')) = 'COMPLETED'
        ORDER BY id
        """
    ).fetchall()


def get_verified_financials(conn):
    sales = get_verified_sales(conn)

    revenue = 0.0
    cogs = 0.0
    gross_profit = 0.0
    units = 0.0

    verified_sales = 0

    for row in sales:
        quantity = float(row[1] or 0)
        amount = float(row[2] or 0)
        sale_cogs = float(row[4] or 0)
        sale_profit = float(row[5] or 0)

        if quantity < 0 or amount < 0 or sale_cogs < 0:
            continue

        verified_sales += 1
        units += quantity
        revenue += amount
        cogs += sale_cogs
        gross_profit += sale_profit

    expenses = safe_sum(conn, "expenses", "amount")

    net_profit = gross_profit - expenses

    gross_margin = (
        gross_profit / revenue
        if revenue > 0
        else 0
    )

    net_margin = (
        net_profit / revenue
        if revenue > 0
        else 0
    )

    return {
        "sales": verified_sales,
        "units": units,
        "revenue": revenue,
        "cogs": cogs,
        "gross_profit": gross_profit,
        "expenses": expenses,
        "net_profit": net_profit,
        "gross_margin": gross_margin,
        "net_margin": net_margin,
    }


def get_customer_credit(conn):
    if not table_exists(conn, "customer_credit"):
        return 0.0

    cols = columns(conn, "customer_credit")

    candidates = [
        "amount",
        "credit_amount",
        "balance",
        "outstanding",
        "remaining_amount",
    ]

    for field in candidates:
        if field in cols:
            try:
                return safe_sum(conn, "customer_credit", field)
            except Exception:
                pass

    return 0.0


def get_inventory_capital(conn):
    if not table_exists(conn, "products"):
        return 0.0

    cols = columns(conn, "products")

    if "current_stock" not in cols:
        return 0.0

    if "buying_price" not in cols:
        return 0.0

    row = conn.execute(
        """
        SELECT COALESCE(
            SUM(
                COALESCE(current_stock, 0)
                * COALESCE(buying_price, 0)
            ),
            0
        )
        FROM products
        """
    ).fetchone()

    return float(row[0] or 0)


def scenario_margin(financials, target_margin):
    revenue = financials["revenue"]
    cogs = financials["cogs"]

    if revenue <= 0:
        return {
            "target_profit": 0.0,
            "required_revenue": 0.0,
            "profit_gap": 0.0,
        }

    target_profit = revenue * target_margin

    profit_gap = max(
        0.0,
        target_profit - financials["net_profit"]
    )

    return {
        "target_profit": target_profit,
        "required_revenue": revenue,
        "profit_gap": profit_gap,
    }


def gradual_margin_scenarios(financials):
    revenue = financials["revenue"]
    cogs = financials["cogs"]

    if revenue <= 0:
        return []

    current_profit = financials["net_profit"]

    margins = [
        ("CURRENT", financials["gross_margin"]),
        ("STEP 1", 0.075),
        ("STEP 2", 0.085),
        ("STEP 3", 0.095),
        ("TARGET", 0.10),
    ]

    results = []

    for name, margin in margins:
        projected_profit = revenue * margin

        results.append(
            {
                "name": name,
                "margin": margin,
                "profit": projected_profit,
                "gain": projected_profit - current_profit,
            }
        )

    return results


def forecast_sales(financials):
    sales = financials["sales"]
    units = financials["units"]
    revenue = financials["revenue"]
    profit = financials["net_profit"]

    if sales <= 0:
        return []

    avg_revenue = revenue / sales
    avg_profit = profit / sales

    periods = [
        ("NEXT 10 SALES", 10),
        ("NEXT 20 SALES", 20),
        ("NEXT 50 SALES", 50),
    ]

    results = []

    for name, number in periods:
        projected_revenue = avg_revenue * number
        projected_profit = avg_profit * number

        results.append(
            {
                "name": name,
                "sales": number,
                "revenue": projected_revenue,
                "profit": projected_profit,
            }
        )

    return results


def inventory_scenarios(inventory_capital):
    return [
        ("10% INVENTORY RELEASE", inventory_capital * 0.10),
        ("25% INVENTORY RELEASE", inventory_capital * 0.25),
        ("50% INVENTORY RELEASE", inventory_capital * 0.50),
    ]


def print_header(title):
    print("=" * 60)
    print(title)
    print("=" * 60)


def main():
    print("=" * 60)
    print("POS LEDGER NG V92")
    print("MANAGEMENT SCENARIO & FORECAST INTELLIGENCE")
    print("=" * 60)

    if not DB_PATH.exists():
        print()
        print("DATABASE STATUS : NOT FOUND")
        print("Expected:", DB_PATH)
        return

    conn = sqlite3.connect(DB_PATH)

    try:
        financials = get_verified_financials(conn)
        customer_credit = get_customer_credit(conn)
        inventory_capital = get_inventory_capital(conn)

        print_header("VERIFIED BUSINESS BASELINE")

        print(f"Verified Sales        : {financials['sales']}")
        print(f"Units Sold            : {financials['units']:.2f}")
        print(f"Verified Revenue      : {money(financials['revenue'])}")
        print(f"Verified COGS         : {money(financials['cogs'])}")
        print(f"Gross Profit          : {money(financials['gross_profit'])}")
        print(f"Operating Expenses    : {money(financials['expenses'])}")
        print(f"Net Operating Profit  : {money(financials['net_profit'])}")
        print(f"Gross Margin          : {pct(financials['gross_margin'] * 100)}")
        print(f"Net Margin            : {pct(financials['net_margin'] * 100)}")

        print_header("TARGET PROFIT SCENARIO")

        target = scenario_margin(
            financials,
            TARGET_NET_MARGIN
        )

        print(
            f"Target Revenue Base   : "
            f"{money(financials['revenue'])}"
        )
        print(
            f"Target Net Margin     : "
            f"{pct(TARGET_NET_MARGIN * 100)}"
        )
        print(
            f"Target Net Profit     : "
            f"{money(target['target_profit'])}"
        )
        print(
            f"Current Net Profit    : "
            f"{money(financials['net_profit'])}"
        )
        print(
            f"Additional Profit     : "
            f"{money(target['profit_gap'])}"
        )

        print_header("GRADUAL MARGIN IMPROVEMENT")

        for scenario in gradual_margin_scenarios(financials):
            print("----------------------------------------")
            print(
                f"{scenario['name']}"
            )
            print(
                f"Simulated Margin     : "
                f"{pct(scenario['margin'] * 100)}"
            )
            print(
                f"Projected Profit     : "
                f"{money(scenario['profit'])}"
            )
            print(
                f"Profit Improvement   : "
                f"{money(scenario['gain'])}"
            )

        print_header("SALES VOLUME FORECAST")

        forecasts = forecast_sales(financials)

        if not forecasts:
            print("Insufficient verified sales data.")
        else:
            for forecast in forecasts:
                print("----------------------------------------")
                print(
                    f"{forecast['name']}"
                )
                print(
                    f"Projected Sales      : "
                    f"{forecast['sales']}"
                )
                print(
                    f"Projected Revenue    : "
                    f"{money(forecast['revenue'])}"
                )
                print(
                    f"Projected Profit     : "
                    f"{money(forecast['profit'])}"
                )

        print_header("CUSTOMER CREDIT SCENARIO")

        print(
            f"Outstanding Credit   : "
            f"{money(customer_credit)}"
        )

        if customer_credit > 0:
            print(
                f"Potential Liquidity  : "
                f"{money(customer_credit)}"
            )
            print(
                "Scenario             : "
                "CREDIT COLLECTION OPPORTUNITY"
            )
        else:
            print(
                "Scenario             : "
                "NO CREDIT RECOVERY DETECTED"
            )

        print_header("INVENTORY CAPITAL SCENARIOS")

        print(
            f"Inventory Capital    : "
            f"{money(inventory_capital)}"
        )

        for name, amount in inventory_scenarios(
            inventory_capital
        ):
            print("----------------------------------------")
            print(name)
            print(
                f"Potential Capital    : "
                f"{money(amount)}"
            )

        print_header("V92 MANAGEMENT DECISION")

        current_margin = financials["net_margin"]

        if current_margin >= TARGET_NET_MARGIN:
            print("🟢 TARGET NET MARGIN ACHIEVED")
        elif current_margin >= 0.08:
            print("🟡 GRADUAL PROFITABILITY IMPROVEMENT")
        else:
            print("🟠 PROFITABILITY IMPROVEMENT REQUIRED")

        print(
            f"Current Net Margin   : "
            f"{pct(current_margin * 100)}"
        )

        print(
            f"Target Net Margin    : "
            f"{pct(TARGET_NET_MARGIN * 100)}"
        )

        print(
            f"Profit Gap           : "
            f"{money(target['profit_gap'])}"
        )

        print()
        print("Recommended Strategy :")
        print("1. Improve low-margin products gradually.")
        print("2. Monitor actual sales volume after pricing changes.")
        print("3. Collect outstanding customer credit.")
        print("4. Monitor inventory capital concentration.")
        print("5. Increase verified sales history.")
        print("6. Compare forecast against actual results.")

        print_header("V92 MANAGEMENT INTERPRETATION")

        print(
            "V92 converts verified historical financial "
            "data into controlled management scenarios."
        )

        print(
            "Forecast values are analytical estimates and "
            "are not guaranteed future results."
        )

        print(
            "V92 does not automatically change prices, "
            "collect credit, sell inventory, or modify "
            "financial records."
        )

        print_header("V92 DATA INTEGRITY STATUS")

        print(
            "Profitability source : V81/V82/V90"
        )
        print(
            "Pricing source       : V83/V84"
        )
        print(
            "Demand source        : V85"
        )
        print(
            "Inventory source     : V86"
        )
        print(
            "Working capital      : V87"
        )
        print(
            "Decision source      : V91"
        )
        print(
            "Forecast source      : VERIFIED DATABASE"
        )
        print(
            "Automatic changes    : NO"
        )

        print_header("V92 SAFETY STATUS")

        print("Mode                : READ-ONLY")
        print("Database modified   : NO")
        print("Sales modified      : NO")
        print("Products modified   : NO")
        print("Inventory modified  : NO")
        print("Balance modified    : NO")
        print("Credit modified     : NO")
        print("Suppliers modified  : NO")
        print("Expenses modified   : NO")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
