"""
POS LEDGER NG
PHASE 2.1 — REAL APPLICATION DASHBOARD

Read-only dashboard foundation.
Uses the existing SQLite database and safely detects available tables/columns.
"""

import sqlite3
from pathlib import Path
from datetime import datetime


DB_PATH = Path(__file__).resolve().parent.parent / "data" / "posledger.db"


def connect_db():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def table_exists(conn, table_name):
    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table' AND name=?
        """,
        (table_name,),
    ).fetchone()

    return row is not None


def columns(conn, table_name):
    if not table_exists(conn, table_name):
        return []

    return [
        row["name"]
        for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    ]


def first_column(conn, table_name, candidates):
    available = columns(conn, table_name)

    for candidate in candidates:
        if candidate in available:
            return candidate

    return None


def money(value):
    return f"₦{float(value or 0):,.2f}"


def number(value):
    return f"{float(value or 0):,.2f}"


def safe_sum(conn, table_name, value_column, where=None, params=()):
    if not table_exists(conn, table_name):
        return 0.0

    if value_column not in columns(conn, table_name):
        return 0.0

    sql = f"SELECT COALESCE(SUM({value_column}), 0) FROM {table_name}"

    if where:
        sql += f" WHERE {where}"

    return float(conn.execute(sql, params).fetchone()[0] or 0)


def safe_count(conn, table_name, where=None, params=()):
    if not table_exists(conn, table_name):
        return 0

    sql = f"SELECT COUNT(*) FROM {table_name}"

    if where:
        sql += f" WHERE {where}"

    return int(conn.execute(sql, params).fetchone()[0] or 0)


def get_sales_position(conn):
    if not table_exists(conn, "sales"):
        return {
            "sales": 0,
            "units": 0,
            "revenue": 0,
            "cogs": 0,
            "profit": 0,
            "margin": 0,
        }

    sale_columns = columns(conn, "sales")

    sales_count = safe_count(conn, "sales")

    quantity_col = first_column(
        conn,
        "sales",
        ["quantity", "qty", "units"],
    )

    revenue_col = first_column(
        conn,
        "sales",
        ["total_amount", "total", "revenue", "amount"],
    )

    cogs_col = first_column(
        conn,
        "sales",
        ["cogs"],
    )

    profit_col = first_column(
        conn,
        "sales",
        ["gross_profit", "total_profit", "profit"],
    )

    units = (
        safe_sum(conn, "sales", quantity_col)
        if quantity_col
        else 0
    )

    revenue = (
        safe_sum(conn, "sales", revenue_col)
        if revenue_col
        else 0
    )

    cogs = (
        safe_sum(conn, "sales", cogs_col)
        if cogs_col
        else 0
    )

    profit = (
        safe_sum(conn, "sales", profit_col)
        if profit_col
        else 0
    )

    # If historical COGS exists but profit does not,
    # derive profit safely.
    if not profit and revenue and cogs:
        profit = revenue - cogs

    # If profit exists but COGS is unavailable,
    # derive COGS.
    if not cogs and revenue and profit:
        cogs = revenue - profit

    margin = (profit / revenue * 100) if revenue else 0

    return {
        "sales": sales_count,
        "units": units,
        "revenue": revenue,
        "cogs": cogs,
        "profit": profit,
        "margin": margin,
    }


def get_expenses(conn):
    if not table_exists(conn, "expenses"):
        return 0.0, 0

    expense_columns = columns(conn, "expenses")

    amount_col = first_column(
        conn,
        "expenses",
        ["amount", "expense_amount", "total_amount"],
    )

    if not amount_col:
        return 0.0, safe_count(conn, "expenses")

    return (
        safe_sum(conn, "expenses", amount_col),
        safe_count(conn, "expenses"),
    )


def get_inventory(conn):
    if not table_exists(conn, "products"):
        return {
            "products": 0,
            "units": 0,
            "capital": 0,
        }

    product_columns = columns(conn, "products")

    stock_col = first_column(
        conn,
        "products",
        ["current_stock", "stock", "quantity"],
    )

    cost_col = first_column(
        conn,
        "products",
        ["buying_price", "cost_price", "cost"],
    )

    products = safe_count(conn, "products")

    units = (
        safe_sum(conn, "products", stock_col)
        if stock_col
        else 0
    )

    capital = 0.0

    if stock_col and cost_col:
        capital = float(
            conn.execute(
                f"""
                SELECT COALESCE(
                    SUM(
                        COALESCE({stock_col}, 0) *
                        COALESCE({cost_col}, 0)
                    ),
                    0
                )
                FROM products
                """
            ).fetchone()[0]
            or 0
        )

    return {
        "products": products,
        "units": units,
        "capital": capital,
    }


def get_customer_credit(conn):
    if not table_exists(conn, "customer_credit"):
        return 0.0

    credit_columns = columns(conn, "customer_credit")

    amount_col = first_column(
        conn,
        "customer_credit",
        [
            "balance",
            "amount",
            "credit_amount",
            "outstanding_amount",
            "amount_due",
        ],
    )

    if not amount_col:
        return 0.0

    return safe_sum(conn, "customer_credit", amount_col)


def get_supplier_liability(conn):
    if not table_exists(conn, "suppliers"):
        return 0.0

    # Suppliers table may contain profiles rather than balances.
    supplier_columns = columns(conn, "suppliers")

    amount_col = first_column(
        conn,
        "suppliers",
        [
            "balance",
            "outstanding",
            "amount_due",
            "liability",
        ],
    )

    if not amount_col:
        return 0.0

    return safe_sum(conn, "suppliers", amount_col)


def get_product_alerts(conn):
    alerts = []

    if not table_exists(conn, "products"):
        return alerts

    cols = columns(conn, "products")

    name_col = first_column(
        conn,
        "products",
        ["product_name", "name"],
    )

    stock_col = first_column(
        conn,
        "products",
        ["current_stock", "stock", "quantity"],
    )

    minimum_col = first_column(
        conn,
        "products",
        ["minimum_stock", "min_stock"],
    )

    if not name_col or not stock_col:
        return alerts

    select_cols = f"{name_col}, {stock_col}"

    if minimum_col:
        select_cols += f", {minimum_col}"

    rows = conn.execute(
        f"SELECT {select_cols} FROM products"
    ).fetchall()

    for row in rows:
        name = row[0]
        stock = float(row[1] or 0)

        minimum = (
            float(row[2] or 0)
            if minimum_col
            else 5.0
        )

        if stock <= minimum:
            alerts.append(
                f"{name}: stock {number(stock)}"
            )

    return alerts


def print_dashboard(conn):
    sales = get_sales_position(conn)
    expenses, expense_records = get_expenses(conn)
    inventory = get_inventory(conn)
    customer_credit = get_customer_credit(conn)
    supplier_liability = get_supplier_liability(conn)

    net_profit = sales["profit"] - expenses
    net_margin = (
        net_profit / sales["revenue"] * 100
        if sales["revenue"]
        else 0
    )

    target_margin = 10.0
    margin_gap = max(target_margin - net_margin, 0)

    if net_margin >= target_margin:
        profitability_status = "🟢 TARGET MET"
    elif net_margin >= 7.5:
        profitability_status = "🟡 BELOW TARGET"
    else:
        profitability_status = "🟠 PROFITABILITY BELOW TARGET"

    print("=" * 60)
    print("POS LEDGER NG")
    print("PHASE 2.1 — REAL BUSINESS DASHBOARD")
    print("=" * 60)

    print()
    print("EXECUTIVE FINANCIAL POSITION")
    print("=" * 60)

    print(f"Verified Sales       : {sales['sales']}")
    print(f"Units Sold           : {number(sales['units'])}")
    print(f"Revenue              : {money(sales['revenue'])}")
    print(f"COGS                 : {money(sales['cogs'])}")
    print(f"Gross Profit         : {money(sales['profit'])}")
    print(f"Gross Margin         : {sales['margin']:.2f}%")
    print(f"Operating Expenses   : {money(expenses)}")
    print(f"Net Operating Profit : {money(net_profit)}")
    print(f"Net Margin           : {net_margin:.2f}%")

    print()
    print("PROFITABILITY")
    print("=" * 60)

    print(f"Management Target    : {target_margin:.2f}%")
    print(f"Margin Gap            : {margin_gap:.2f}%")
    print(f"Status                : {profitability_status}")

    print()
    print("WORKING CAPITAL")
    print("=" * 60)

    print(f"Customer Credit      : {money(customer_credit)}")
    print(f"Supplier Liability   : {money(supplier_liability)}")
    print(f"Inventory Units      : {number(inventory['units'])}")
    print(f"Inventory Capital    : {money(inventory['capital'])}")
    print(f"Products             : {inventory['products']}")

    print()
    print("MANAGEMENT ACTIONS")
    print("=" * 60)

    if margin_gap > 0:
        print(
            f"🟠 Improve gross margin "
            f"(gap {margin_gap:.2f}%)"
        )

    if customer_credit > 0:
        print(
            f"🟡 Collect customer credit "
            f"({money(customer_credit)})"
        )

    if inventory["capital"] > sales["revenue"] and sales["revenue"] > 0:
        print(
            "🟡 Monitor inventory capital concentration"
        )

    alerts = get_product_alerts(conn)

    for alert in alerts[:5]:
        print(f"🔴 Stock alert: {alert}")

    if not alerts and margin_gap <= 0 and customer_credit <= 0:
        print("🟢 No immediate management alerts")

    print()
    print("DATA STATUS")
    print("=" * 60)

    print("Database              : CONNECTED")
    print("Dashboard mode        : READ-ONLY")
    print("Database modified     : NO")
    print(f"Expense records       : {expense_records}")
    print("Historical COGS       : USED WHEN AVAILABLE")
    print("Automatic actions     : NO")

    print()
    print("=" * 60)
    print(
        "Generated:",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    print("=" * 60)


def main():
    try:
        conn = connect_db()

        try:
            print_dashboard(conn)
        finally:
            conn.close()

    except Exception as exc:
        print()
        print("❌ DASHBOARD ERROR")
        print("=" * 60)
        print(str(exc))
        print()
        print("Database expected at:")
        print(DB_PATH)


if __name__ == "__main__":
    main()
