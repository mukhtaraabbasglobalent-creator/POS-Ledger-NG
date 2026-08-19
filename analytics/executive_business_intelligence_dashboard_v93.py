"""
POS LEDGER NG V93
EXECUTIVE BUSINESS INTELLIGENCE DASHBOARD

READ-ONLY executive integration of V81-V92 intelligence.

Safety:
- No database writes
- No price changes
- No sales changes
- No inventory changes
- No credit collection
- No supplier payments
"""

import sqlite3
from pathlib import Path
from datetime import datetime


DB_PATH = Path("data/posledger.db")

TARGET_MARGIN = 0.10


def money(value):
    return f"₦{value:,.2f}"


def pct(value):
    return f"{value * 100:.2f}%"


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def table_exists(conn, table):
    row = conn.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None


def columns(conn, table):
    if not table_exists(conn, table):
        return set()

    return {
        row["name"]
        for row in conn.execute(
            f'PRAGMA table_info("{table}")'
        ).fetchall()
    }


def safe_sum(conn, table, column):
    if not table_exists(conn, table):
        return 0.0

    cols = columns(conn, table)

    if column not in cols:
        return 0.0

    row = conn.execute(
        f'SELECT COALESCE(SUM("{column}"), 0) AS total '
        f'FROM "{table}"'
    ).fetchone()

    return float(row["total"] or 0)


def get_sales(conn):
    if not table_exists(conn, "sales"):
        return []

    cols = columns(conn, "sales")

    required = {
        "id",
        "quantity",
        "total_amount",
        "sale_date",
    }

    if not required.issubset(cols):
        return []

    query = """
        SELECT *
        FROM sales
        WHERE status IS NULL
           OR status = 'COMPLETED'
        ORDER BY id
    """

    return conn.execute(query).fetchall()


def get_financial_position(conn):
    sales = get_sales(conn)

    revenue = sum(
        float(row["total_amount"] or 0)
        for row in sales
    )

    units = sum(
        float(row["quantity"] or 0)
        for row in sales
    )

    cogs = 0.0
    gross_profit = 0.0
    verified_sales = 0

    sales_cols = columns(conn, "sales")

    has_snapshot = "cost_snapshot" in sales_cols
    has_cogs = "cogs" in sales_cols
    has_gross_profit = "gross_profit" in sales_cols

    for row in sales:

        sale_cogs = None
        sale_profit = None

        if has_cogs and row["cogs"] is not None:
            sale_cogs = float(row["cogs"])

        if (
            has_gross_profit
            and row["gross_profit"] is not None
        ):
            sale_profit = float(row["gross_profit"])

        if sale_cogs is not None:
            cogs += sale_cogs

            if sale_profit is not None:
                gross_profit += sale_profit
            else:
                gross_profit += (
                    float(row["total_amount"] or 0)
                    - sale_cogs
                )

            verified_sales += 1

        elif has_snapshot and row["cost_snapshot"] is not None:
            cost = float(row["cost_snapshot"])
            quantity = float(row["quantity"] or 0)

            calculated_cogs = cost * quantity
            cogs += calculated_cogs
            gross_profit += (
                float(row["total_amount"] or 0)
                - calculated_cogs
            )

            verified_sales += 1

    if revenue > 0:
        margin = gross_profit / revenue
    else:
        margin = 0.0

    return {
        "sales": len(sales),
        "verified_sales": verified_sales,
        "units": units,
        "revenue": revenue,
        "cogs": cogs,
        "gross_profit": gross_profit,
        "margin": margin,
    }


def get_expenses(conn):
    if not table_exists(conn, "expenses"):
        return 0.0

    cols = columns(conn, "expenses")

    if "amount" not in cols:
        return 0.0

    return safe_sum(conn, "expenses", "amount")


def get_credit(conn):
    if not table_exists(conn, "customer_credit"):
        return 0.0

    cols = columns(conn, "customer_credit")

    candidates = [
        "amount_due",
        "outstanding_amount",
        "balance",
        "amount",
        "credit_amount",
    ]

    for column in candidates:
        if column in cols:
            return safe_sum(
                conn,
                "customer_credit",
                column,
            )

    return 0.0


def get_supplier_liability(conn):
    if not table_exists(conn, "suppliers"):
        return 0.0

    cols = columns(conn, "suppliers")

    candidates = [
        "balance",
        "amount_due",
        "outstanding",
        "credit_balance",
        "liability",
    ]

    for column in candidates:
        if column in cols:
            return safe_sum(
                conn,
                "suppliers",
                column,
            )

    return 0.0


def get_inventory(conn):
    if not table_exists(conn, "products"):
        return {
            "capital": 0.0,
            "units": 0.0,
            "products": 0,
        }

    cols = columns(conn, "products")

    stock_col = None

    for candidate in [
        "current_stock",
        "stock",
        "quantity",
    ]:
        if candidate in cols:
            stock_col = candidate
            break

    if stock_col is None or "buying_price" not in cols:
        return {
            "capital": 0.0,
            "units": 0.0,
            "products": 0,
        }

    rows = conn.execute(
        f'''
        SELECT
            COALESCE("{stock_col}", 0) AS stock,
            COALESCE(buying_price, 0) AS cost
        FROM products
        '''
    ).fetchall()

    capital = 0.0
    units = 0.0

    for row in rows:
        stock = float(row["stock"] or 0)
        cost = float(row["cost"] or 0)

        units += stock
        capital += stock * cost

    return {
        "capital": capital,
        "units": units,
        "products": len(rows),
    }


def product_analysis(conn):
    result = []

    if not table_exists(conn, "sales"):
        return result

    if not table_exists(conn, "products"):
        return result

    sales_cols = columns(conn, "sales")
    product_cols = columns(conn, "products")

    required_sales = {
        "product_id",
        "quantity",
        "total_amount",
    }

    required_products = {
        "id",
        "product_name",
        "buying_price",
        "selling_price",
    }

    if not required_sales.issubset(sales_cols):
        return result

    if not required_products.issubset(product_cols):
        return result

    sales_rows = conn.execute(
        """
        SELECT
            s.product_id,
            SUM(s.quantity) AS units,
            SUM(s.total_amount) AS revenue
        FROM sales s
        WHERE s.status IS NULL
           OR s.status = 'COMPLETED'
        GROUP BY s.product_id
        """
    ).fetchall()

    for sale in sales_rows:

        product = conn.execute(
            """
            SELECT *
            FROM products
            WHERE id = ?
            """,
            (sale["product_id"],),
        ).fetchone()

        if product is None:
            continue

        units = float(sale["units"] or 0)
        revenue = float(sale["revenue"] or 0)
        cost = float(product["buying_price"] or 0)
        price = float(product["selling_price"] or 0)

        product_cogs = units * cost
        profit = revenue - product_cogs

        margin = (
            profit / revenue
            if revenue > 0
            else 0
        )

        result.append({
            "name": product["product_name"],
            "sku": (
                product["sku"]
                if "sku" in product_cols
                else "-"
            ),
            "units": units,
            "revenue": revenue,
            "cost": product_cogs,
            "profit": profit,
            "margin": margin,
            "price": price,
        })

    return result


def print_header(title):
    print("=" * 60)
    print(f"POS LEDGER NG V93")
    print(title)
    print("=" * 60)


def main():

    print_header(
        "EXECUTIVE BUSINESS INTELLIGENCE DASHBOARD"
    )

    if not DB_PATH.exists():
        print()
        print("DATABASE STATUS")
        print("=" * 60)
        print("❌ Database not found:")
        print(DB_PATH)
        print("=" * 60)
        return

    conn = connect()

    try:

        financial = get_financial_position(conn)
        expenses = get_expenses(conn)
        credit = get_credit(conn)
        supplier = get_supplier_liability(conn)
        inventory = get_inventory(conn)
        products = product_analysis(conn)

        revenue = financial["revenue"]
        cogs = financial["cogs"]
        gross_profit = financial["gross_profit"]

        if revenue > 0:
            gross_margin = gross_profit / revenue
        else:
            gross_margin = 0.0

        net_profit = gross_profit - expenses

        if revenue > 0:
            net_margin = net_profit / revenue
        else:
            net_margin = 0.0

        target_profit = revenue * TARGET_MARGIN
        profit_gap = max(
            target_profit - net_profit,
            0,
        )

        margin_gap = max(
            TARGET_MARGIN - net_margin,
            0,
        )

        print()
        print("=" * 60)
        print("EXECUTIVE FINANCIAL POSITION")
        print("=" * 60)

        print(
            f"Verified Sales       : "
            f"{financial['verified_sales']}"
        )

        print(
            f"Units Sold           : "
            f"{financial['units']:.2f}"
        )

        print(
            f"Verified Revenue     : "
            f"{money(revenue)}"
        )

        print(
            f"Verified COGS        : "
            f"{money(cogs)}"
        )

        print(
            f"Gross Profit         : "
            f"{money(gross_profit)}"
        )

        print(
            f"Gross Margin         : "
            f"{pct(gross_margin)}"
        )

        print(
            f"Operating Expenses   : "
            f"{money(expenses)}"
        )

        print(
            f"NET OPERATING PROFIT : "
            f"{money(net_profit)}"
        )

        print(
            f"NET MARGIN           : "
            f"{pct(net_margin)}"
        )

        print()
        print("=" * 60)
        print("TARGET & PERFORMANCE GAP")
        print("=" * 60)

        print(
            f"Target Net Margin    : "
            f"{pct(TARGET_MARGIN)}"
        )

        print(
            f"Target Net Profit    : "
            f"{money(target_profit)}"
        )

        print(
            f"Additional Profit    : "
            f"{money(profit_gap)}"
        )

        print(
            f"Margin Gap           : "
            f"{pct(margin_gap)}"
        )

        if net_margin >= TARGET_MARGIN:
            status = "🟢 TARGET ACHIEVED"
        elif net_margin >= 0.075:
            status = "🟡 IMPROVEMENT NEEDED"
        else:
            status = "🟠 PROFITABILITY BELOW TARGET"

        print(
            f"Business Profitability: {status}"
        )

        print()
        print("=" * 60)
        print("LIQUIDITY & WORKING CAPITAL")
        print("=" * 60)

        print(
            f"Customer Credit      : "
            f"{money(credit)}"
        )

        print(
            f"Supplier Liability   : "
            f"{money(supplier)}"
        )

        print(
            f"Inventory Capital    : "
            f"{money(inventory['capital'])}"
        )

        print(
            f"Inventory Units      : "
            f"{inventory['units']:.2f}"
        )

        potential_resources = credit

        print(
            f"Potential Credit     : "
            f"{money(potential_resources)}"
        )

        print()
        print("=" * 60)
        print("PRODUCT PROFITABILITY")
        print("=" * 60)

        if not products:
            print("No product profitability data available.")
        else:

            for index, product in enumerate(
                products,
                start=1,
            ):

                print("-" * 40)

                print(
                    f"{index}. "
                    f"{product['name']}"
                )

                print(
                    f"SKU                 : "
                    f"{product['sku']}"
                )

                print(
                    f"Units Sold          : "
                    f"{product['units']:.2f}"
                )

                print(
                    f"Revenue             : "
                    f"{money(product['revenue'])}"
                )

                print(
                    f"COGS                : "
                    f"{money(product['cost'])}"
                )

                print(
                    f"Gross Profit        : "
                    f"{money(product['profit'])}"
                )

                print(
                    f"Margin              : "
                    f"{pct(product['margin'])}"
                )

                gap = max(
                    TARGET_MARGIN
                    - product["margin"],
                    0,
                )

                print(
                    f"Margin Gap          : "
                    f"{pct(gap)}"
                )

                if product["margin"] >= TARGET_MARGIN:
                    print(
                        "Status              : "
                        "🟢 TARGET MET"
                    )
                else:
                    print(
                        "Status              : "
                        "🟠 REVIEW REQUIRED"
                    )

        print()
        print("=" * 60)
        print("TOP MANAGEMENT PRIORITIES")
        print("=" * 60)

        priorities = []

        if margin_gap > 0:
            priorities.append(
                (
                    "HIGH",
                    "Improve gross margin",
                    f"Gap: {pct(margin_gap)}",
                )
            )

        if credit > 0:
            priorities.append(
                (
                    "MEDIUM",
                    "Collect customer credit",
                    money(credit),
                )
            )

        if inventory["capital"] > revenue:
            priorities.append(
                (
                    "MEDIUM",
                    "Monitor inventory capital",
                    money(inventory["capital"]),
                )
            )

        if financial["verified_sales"] < 20:
            priorities.append(
                (
                    "LOW",
                    "Strengthen verified sales history",
                    f"{financial['verified_sales']}/20",
                )
            )

        if not priorities:
            priorities.append(
                (
                    "LOW",
                    "Maintain current controls",
                    "No major warning",
                )
            )

        for index, item in enumerate(
            priorities,
            start=1,
        ):

            level, action, impact = item

            print(
                f"{index}. [{level}] {action}"
            )

            print(
                f"   Signal: {impact}"
            )

        print()
        print("=" * 60)
        print("EXECUTIVE DECISION")
        print("=" * 60)

        if net_margin >= TARGET_MARGIN:
            decision = (
                "🟢 MAINTAIN CURRENT PERFORMANCE"
            )
        elif margin_gap <= 0.02:
            decision = (
                "🟡 GRADUAL PROFITABILITY IMPROVEMENT"
            )
        else:
            decision = (
                "🟠 PROFITABILITY IMPROVEMENT REQUIRED"
            )

        print(decision)

        print(
            f"Current Net Margin : "
            f"{pct(net_margin)}"
        )

        print(
            f"Target Net Margin  : "
            f"{pct(TARGET_MARGIN)}"
        )

        print(
            f"Profit Gap          : "
            f"{money(profit_gap)}"
        )

        print()
        print("=" * 60)
        print("V93 EXECUTIVE INTERPRETATION")
        print("=" * 60)

        print(
            "V93 consolidates the verified financial, "
            "profitability, pricing, inventory and "
            "working-capital intelligence generated "
            "by earlier POS Ledger NG modules."
        )

        print(
            "The dashboard is READ-ONLY and provides "
            "management information without changing "
            "business records."
        )

        print(
            "Recommendations are analytical signals, "
            "not automatic financial actions."
        )

        print()
        print("=" * 60)
        print("V93 DATA INTEGRITY STATUS")
        print("=" * 60)

        print(
            f"Financial data       : "
            f"{'VERIFIED' if financial['verified_sales'] else 'REVIEW'}"
        )

        print(
            f"COGS data            : "
            f"{'VERIFIED' if cogs > 0 else 'UNAVAILABLE'}"
        )

        print(
            f"Profitability        : "
            f"{'VERIFIED' if revenue > 0 else 'REVIEW'}"
        )

        print(
            f"Product intelligence : "
            f"{'AVAILABLE' if products else 'LIMITED'}"
        )

        print(
            "Automatic changes    : NO"
        )

        print()
        print("=" * 60)
        print("V93 SAFETY STATUS")
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

        print(
            f"Generated           : "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        print("=" * 60)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
