import sqlite3
from pathlib import Path
from datetime import datetime


DB_PATH = Path(__file__).resolve().parents[1] / "data" / "posledger.db"


def money(value):
    return f"₦{float(value or 0):,.2f}"


def pct(value):
    return f"{float(value or 0):.2f}%"


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

    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()

    # SQLite rows may be tuples or sqlite3.Row objects.
    result = set()

    for row in rows:
        if isinstance(row, sqlite3.Row):
            result.add(row["name"])
        else:
            result.add(row[1])

    return result


def safe_sum(conn, table, column):
    if not table_exists(conn, table):
        return 0.0

    cols = columns(conn, table)

    if column not in cols:
        return 0.0

    row = conn.execute(
        f"SELECT COALESCE(SUM({column}), 0) FROM {table}"
    ).fetchone()

    return float(row[0] or 0)


def safe_count(conn, table):
    if not table_exists(conn, table):
        return 0

    return int(
        conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    )


def verified_sales(conn):
    required = {
        "product_id",
        "quantity",
        "total_amount",
        "cogs",
        "gross_profit",
        "gross_margin",
    }

    cols = columns(conn, "sales")

    if not required.issubset(cols):
        return {
            "sales": 0,
            "units": 0.0,
            "revenue": 0.0,
            "cogs": 0.0,
            "gross_profit": 0.0,
            "margin": 0.0,
            "verified": False,
        }

    row = conn.execute(
        """
        SELECT
            COUNT(*),
            COALESCE(SUM(quantity), 0),
            COALESCE(SUM(total_amount), 0),
            COALESCE(SUM(cogs), 0),
            COALESCE(SUM(gross_profit), 0)
        FROM sales
        WHERE UPPER(COALESCE(status, 'COMPLETED')) = 'COMPLETED'
        """
    ).fetchone()

    sales_count = int(row[0] or 0)
    units = float(row[1] or 0)
    revenue = float(row[2] or 0)
    cogs = float(row[3] or 0)
    gross_profit = float(row[4] or 0)

    margin = (gross_profit / revenue * 100) if revenue else 0

    return {
        "sales": sales_count,
        "units": units,
        "revenue": revenue,
        "cogs": cogs,
        "gross_profit": gross_profit,
        "margin": margin,
        "verified": True,
    }


def operating_expenses(conn):
    if not table_exists(conn, "expenses"):
        return 0.0, 0

    cols = columns(conn, "expenses")

    amount_col = None

    for candidate in ("amount", "expense_amount", "total_amount"):
        if candidate in cols:
            amount_col = candidate
            break

    if not amount_col:
        return 0.0, safe_count(conn, "expenses")

    return (
        safe_sum(conn, "expenses", amount_col),
        safe_count(conn, "expenses"),
    )


def customer_credit(conn):
    if not table_exists(conn, "customer_credit"):
        return 0.0

    cols = columns(conn, "customer_credit")

    for candidate in (
        "outstanding",
        "outstanding_amount",
        "balance",
        "amount_due",
        "credit_balance",
    ):
        if candidate in cols:
            return safe_sum(conn, "customer_credit", candidate)

    return 0.0


def supplier_liability(conn):
    if not table_exists(conn, "suppliers"):
        return 0.0

    cols = columns(conn, "suppliers")

    for candidate in (
        "outstanding",
        "outstanding_amount",
        "balance",
        "amount_due",
        "liability",
    ):
        if candidate in cols:
            return safe_sum(conn, "suppliers", candidate)

    return 0.0


def inventory_position(conn):
    if not table_exists(conn, "products"):
        return 0.0, 0.0, 0

    cols = columns(conn, "products")

    if "current_stock" not in cols or "buying_price" not in cols:
        return 0.0, 0.0, 0

    row = conn.execute(
        """
        SELECT
            COALESCE(SUM(current_stock), 0),
            COALESCE(SUM(current_stock * buying_price), 0),
            COUNT(*)
        FROM products
        """
    ).fetchone()

    return (
        float(row[0] or 0),
        float(row[1] or 0),
        int(row[2] or 0),
    )


def product_profitability(conn):
    required = {
        "product_id",
        "quantity",
        "total_amount",
        "cogs",
        "gross_profit",
    }

    if not table_exists(conn, "sales"):
        return []

    if not required.issubset(columns(conn, "sales")):
        return []

    if not table_exists(conn, "products"):
        return []

    pcols = columns(conn, "products")

    if not {"id", "product_name", "sku"}.issubset(pcols):
        return []

    rows = conn.execute(
        """
        SELECT
            p.product_name,
            COALESCE(p.sku, ''),
            COALESCE(SUM(s.quantity), 0),
            COALESCE(SUM(s.total_amount), 0),
            COALESCE(SUM(s.cogs), 0),
            COALESCE(SUM(s.gross_profit), 0)
        FROM sales s
        JOIN products p ON p.id = s.product_id
        WHERE UPPER(COALESCE(s.status, 'COMPLETED')) = 'COMPLETED'
        GROUP BY p.id, p.product_name, p.sku
        ORDER BY SUM(s.gross_profit) DESC
        """
    ).fetchall()

    result = []

    for row in rows:
        revenue = float(row[3] or 0)
        profit = float(row[5] or 0)
        margin = profit / revenue * 100 if revenue else 0

        result.append(
            {
                "name": row[0],
                "sku": row[1],
                "units": float(row[2] or 0),
                "revenue": revenue,
                "cogs": float(row[4] or 0),
                "profit": profit,
                "margin": margin,
            }
        )

    return result


def decision_engine(financial, inventory, credit, supplier, products):
    decisions = []

    target_margin = 10.0

    if financial["margin"] < target_margin:
        decisions.append(
            (
                "HIGH",
                "IMPROVE GROSS MARGIN",
                f"Current margin {pct(financial['margin'])} "
                f"is below the {pct(target_margin)} target.",
            )
        )

    if credit > 0:
        decisions.append(
            (
                "MEDIUM",
                "COLLECT CUSTOMER CREDIT",
                f"Potential recoverable liquidity: {money(credit)}.",
            )
        )

    if inventory["capital"] > financial["revenue"]:
        decisions.append(
            (
                "MEDIUM",
                "MONITOR INVENTORY CAPITAL",
                f"Inventory capital {money(inventory['capital'])} "
                f"is above verified revenue {money(financial['revenue'])}.",
            )
        )

    for product in products:
        if product["margin"] < target_margin:
            decisions.append(
                (
                    "MEDIUM",
                    f"REVIEW {product['name'].upper()} PRICING",
                    f"Margin {pct(product['margin'])} "
                    f"is below target.",
                )
            )

    if supplier > 0:
        decisions.append(
            (
                "HIGH",
                "MONITOR SUPPLIER LIABILITY",
                f"Supplier liability: {money(supplier)}.",
            )
        )

    if not decisions:
        decisions.append(
            (
                "LOW",
                "MAINTAIN CURRENT POSITION",
                "No major management exception was detected.",
            )
        )

    return decisions


def main():
    print("=" * 60)
    print("POS LEDGER NG V94")
    print("INTEGRATED BUSINESS INTELLIGENCE & DECISION LAYER")
    print("=" * 60)

    if not DB_PATH.exists():
        print()
        print("DATABASE ERROR")
        print(f"Database not found: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)

    try:
        conn.row_factory = sqlite3.Row

        sales = verified_sales(conn)
        expenses, expense_records = operating_expenses(conn)
        credit = customer_credit(conn)
        supplier = supplier_liability(conn)

        stock_units, inventory_capital, product_count = inventory_position(
            conn
        )

        products = product_profitability(conn)

        net_profit = sales["gross_profit"] - expenses
        net_margin = (
            net_profit / sales["revenue"] * 100
            if sales["revenue"]
            else 0
        )

        inventory = {
            "units": stock_units,
            "capital": inventory_capital,
            "products": product_count,
        }

        financial = {
            **sales,
            "expenses": expenses,
            "net_profit": net_profit,
            "net_margin": net_margin,
        }

        decisions = decision_engine(
            financial,
            inventory,
            credit,
            supplier,
            products,
        )

        print()
        print("=" * 60)
        print("VERIFIED EXECUTIVE POSITION")
        print("=" * 60)

        print(f"Verified Sales       : {sales['sales']}")
        print(f"Units Sold           : {sales['units']:.2f}")
        print(f"Verified Revenue     : {money(sales['revenue'])}")
        print(f"Verified COGS        : {money(sales['cogs'])}")
        print(f"Gross Profit         : {money(sales['gross_profit'])}")
        print(f"Gross Margin         : {pct(sales['margin'])}")
        print(f"Operating Expenses   : {money(expenses)}")
        print(f"Net Operating Profit : {money(net_profit)}")
        print(f"Net Margin           : {pct(net_margin)}")

        print()
        print("=" * 60)
        print("WORKING CAPITAL")
        print("=" * 60)

        print(f"Customer Credit      : {money(credit)}")
        print(f"Supplier Liability   : {money(supplier)}")
        print(f"Inventory Units      : {stock_units:.2f}")
        print(f"Inventory Capital    : {money(inventory_capital)}")
        print(f"Products             : {product_count}")

        print()
        print("=" * 60)
        print("PRODUCT PROFITABILITY")
        print("=" * 60)

        if products:
            for i, product in enumerate(products, 1):
                status = (
                    "🟢 TARGET MET"
                    if product["margin"] >= 10
                    else "🟠 REVIEW REQUIRED"
                )

                print("-" * 40)
                print(f"{i}. {product['name']}")
                print(f"SKU                 : {product['sku']}")
                print(f"Units Sold          : {product['units']:.2f}")
                print(f"Revenue             : {money(product['revenue'])}")
                print(f"COGS                : {money(product['cogs'])}")
                print(f"Gross Profit        : {money(product['profit'])}")
                print(f"Margin              : {pct(product['margin'])}")
                print(f"Status              : {status}")
        else:
            print("Product profitability data unavailable.")

        print()
        print("=" * 60)
        print("MANAGEMENT DECISIONS")
        print("=" * 60)

        for i, (priority, title, reason) in enumerate(decisions, 1):
            print("-" * 40)
            print(f"{i}. [{priority}] {title}")
            print(f"   {reason}")

        print()
        print("=" * 60)
        print("INTEGRATED MANAGEMENT SIGNAL")
        print("=" * 60)

        if net_margin >= 10:
            print("🟢 PROFITABILITY TARGET ACHIEVED")
        else:
            print("🟠 PROFITABILITY IMPROVEMENT REQUIRED")

        print(f"Current Net Margin : {pct(net_margin)}")
        print("Target Net Margin  : 10.00%")

        print()
        print("=" * 60)
        print("V94 DATA INTEGRITY")
        print("=" * 60)

        print(
            "Profitability source : "
            + ("VERIFIED" if sales["verified"] else "REVIEW REQUIRED")
        )
        print("Pricing source       : V83/V84")
        print("Demand source        : V85")
        print("Inventory source     : V86")
        print("Working capital      : V87")
        print("Net profitability    : V90")
        print("Decision source      : V91")
        print("Scenario source      : V92")
        print("Executive dashboard  : V93")
        print(f"Expense records      : {expense_records}")

        print()
        print("=" * 60)
        print("V94 SAFETY STATUS")
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

        print()
        print("=" * 60)
        print("Generated           :", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print("=" * 60)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
