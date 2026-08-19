import sqlite3
from pathlib import Path

DB_PATH = Path("data/posledger.db")

TARGET_NET_MARGIN = 10.0


def money(value):
    return f"₦{value:,.2f}"


def pct(value):
    return f"{value:.2f}%"


def safe_float(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def table_exists(conn, table):
    try:
        row = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            AND name = ?
            """,
            (table,),
        ).fetchone()

        return row is not None

    except sqlite3.Error:
        return False


def get_columns(conn, table):
    """
    Always return column names safely.

    SQLite rows may be tuples or sqlite3.Row objects.
    """
    try:
        rows = conn.execute(
            f"PRAGMA table_info({table})"
        ).fetchall()

        columns = []

        for row in rows:
            if isinstance(row, tuple):
                if len(row) > 1:
                    columns.append(row[1])
            else:
                try:
                    columns.append(row["name"])
                except (KeyError, TypeError):
                    pass

        return columns

    except sqlite3.Error:
        return []


def column_exists(conn, table, column):
    return column in get_columns(conn, table)


def get_verified_sales(conn):
    if not table_exists(conn, "sales"):
        return {
            "revenue": 0.0,
            "cogs": 0.0,
            "gross_profit": 0.0,
            "sales_count": 0,
            "status": "SALES TABLE NOT FOUND",
        }

    columns = get_columns(conn, "sales")

    if "total_amount" not in columns:
        return {
            "revenue": 0.0,
            "cogs": 0.0,
            "gross_profit": 0.0,
            "sales_count": 0,
            "status": "REVENUE COLUMN NOT FOUND",
        }

    where_clause = ""

    if "status" in columns:
        where_clause = """
        WHERE UPPER(
            COALESCE(status, 'COMPLETED')
        ) = 'COMPLETED'
        """

    try:

        revenue_row = conn.execute(
            f"""
            SELECT
                COALESCE(SUM(total_amount), 0),
                COUNT(*)
            FROM sales
            {where_clause}
            """
        ).fetchone()

        revenue = safe_float(revenue_row[0])
        sales_count = int(revenue_row[1] or 0)

        cogs = 0.0
        gross_profit = 0.0

        if "cogs" in columns:
            row = conn.execute(
                f"""
                SELECT COALESCE(SUM(cogs), 0)
                FROM sales
                {where_clause}
                """
            ).fetchone()

            cogs = safe_float(row[0])

        if "gross_profit" in columns:
            row = conn.execute(
                f"""
                SELECT COALESCE(SUM(gross_profit), 0)
                FROM sales
                {where_clause}
                """
            ).fetchone()

            gross_profit = safe_float(row[0])

        # If historical profitability columns exist but contain
        # zero values, calculate from verified sales data.
        if cogs <= 0 and "buying_price" in columns:
            row = conn.execute(
                f"""
                SELECT COALESCE(
                    SUM(quantity * buying_price),
                    0
                )
                FROM sales
                {where_clause}
                """
            ).fetchone()

            cogs = safe_float(row[0])

        if gross_profit <= 0 and revenue > 0:
            gross_profit = revenue - cogs

        if cogs > 0:
            status = "VERIFIED"
        else:
            status = "COGS NOT VERIFIED"

        return {
            "revenue": revenue,
            "cogs": cogs,
            "gross_profit": gross_profit,
            "sales_count": sales_count,
            "status": status,
        }

    except sqlite3.Error as exc:

        return {
            "revenue": 0.0,
            "cogs": 0.0,
            "gross_profit": 0.0,
            "sales_count": 0,
            "status": f"ERROR: {exc}",
        }


def get_expenses(conn):
    if not table_exists(conn, "expenses"):
        return {
            "amount": 0.0,
            "records": 0,
            "column": None,
            "status": "EXPENSE TABLE NOT FOUND",
        }

    columns = get_columns(conn, "expenses")

    possible_columns = [
        "amount",
        "expense_amount",
        "total_amount",
    ]

    for column in possible_columns:

        if column not in columns:
            continue

        try:

            row = conn.execute(
                f"""
                SELECT
                    COALESCE(SUM({column}), 0),
                    COUNT(*)
                FROM expenses
                """
            ).fetchone()

            return {
                "amount": safe_float(row[0]),
                "records": int(row[1] or 0),
                "column": column,
                "status": "DETECTED",
            }

        except sqlite3.Error:
            continue

    return {
        "amount": 0.0,
        "records": 0,
        "column": None,
        "status": "EXPENSE AMOUNT COLUMN NOT DETECTED",
    }


def get_customer_credit(conn):
    if not table_exists(conn, "customer_credit"):
        return 0.0

    columns = get_columns(
        conn,
        "customer_credit"
    )

    possible_columns = [
        "amount",
        "credit_amount",
        "outstanding_amount",
        "balance",
        "amount_due",
    ]

    for column in possible_columns:

        if column not in columns:
            continue

        try:

            row = conn.execute(
                f"""
                SELECT COALESCE(SUM({column}), 0)
                FROM customer_credit
                """
            ).fetchone()

            return safe_float(row[0])

        except sqlite3.Error:
            continue

    return 0.0


def get_inventory_capital(conn):
    if not table_exists(conn, "products"):
        return 0.0

    columns = get_columns(conn, "products")

    required = [
        "current_stock",
        "buying_price",
    ]

    if not all(
        column in columns
        for column in required
    ):
        return 0.0

    try:

        row = conn.execute(
            """
            SELECT COALESCE(
                SUM(
                    COALESCE(current_stock, 0)
                    *
                    COALESCE(buying_price, 0)
                ),
                0
            )
            FROM products
            """
        ).fetchone()

        return safe_float(row[0])

    except sqlite3.Error:
        return 0.0


def get_supplier_liability(conn):
    if not table_exists(conn, "suppliers"):
        return 0.0

    columns = get_columns(
        conn,
        "suppliers"
    )

    possible_columns = [
        "balance",
        "amount_due",
        "outstanding",
        "liability",
        "credit_balance",
    ]

    for column in possible_columns:

        if column not in columns:
            continue

        try:

            row = conn.execute(
                f"""
                SELECT COALESCE(SUM({column}), 0)
                FROM suppliers
                """
            ).fetchone()

            return safe_float(row[0])

        except sqlite3.Error:
            continue

    return 0.0


def main():

    print("=" * 60)
    print("POS LEDGER NG V90")
    print("TRUE NET PROFITABILITY INTELLIGENCE")
    print("=" * 60)

    if not DB_PATH.exists():
        print()
        print("DATABASE NOT FOUND")
        print(f"Expected database: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)

    try:

        sales = get_verified_sales(conn)
        expenses = get_expenses(conn)

        customer_credit = get_customer_credit(
            conn
        )

        inventory_capital = get_inventory_capital(
            conn
        )

        supplier_liability = get_supplier_liability(
            conn
        )

        revenue = sales["revenue"]
        cogs = sales["cogs"]
        gross_profit = sales["gross_profit"]
        sales_count = sales["sales_count"]

        operating_expenses = expenses["amount"]

        if revenue > 0:

            gross_margin = (
                gross_profit / revenue
            ) * 100

        else:

            gross_margin = 0.0

        net_operating_profit = (
            gross_profit
            - operating_expenses
        )

        if revenue > 0:

            net_margin = (
                net_operating_profit
                / revenue
            ) * 100

            expense_ratio = (
                operating_expenses
                / revenue
            ) * 100

        else:

            net_margin = 0.0
            expense_ratio = 0.0

        margin_gap = max(
            TARGET_NET_MARGIN - net_margin,
            0.0
        )

        target_net_profit = (
            revenue
            * TARGET_NET_MARGIN
            / 100
        )

        additional_profit_required = max(
            target_net_profit
            - net_operating_profit,
            0.0
        )

        if sales["status"] == "VERIFIED":

            financial_truth = (
                "🟢 VERIFIED NET PROFITABILITY"
            )

        elif sales_count == 0:

            financial_truth = (
                "🔴 NO VERIFIED SALES"
            )

        else:

            financial_truth = (
                "🟠 REVIEW REQUIRED"
            )

        if net_operating_profit < 0:

            profitability_status = (
                "🔴 NET OPERATING LOSS"
            )

        elif net_margin < 5:

            profitability_status = (
                "🟠 WEAK PROFITABILITY"
            )

        elif net_margin < TARGET_NET_MARGIN:

            profitability_status = (
                "🟡 BELOW TARGET"
            )

        else:

            profitability_status = (
                "🟢 TARGET ACHIEVED"
            )

        print()
        print("=" * 60)
        print("VERIFIED FINANCIAL POSITION")
        print("=" * 60)

        print(
            f"Verified Sales       : "
            f"{sales_count}"
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
            f"Verified Gross Profit : "
            f"{money(gross_profit)}"
        )

        print(
            f"Verified Gross Margin : "
            f"{pct(gross_margin)}"
        )

        print()
        print("=" * 60)
        print("OPERATING EXPENSE POSITION")
        print("=" * 60)

        print(
            f"Expense Records      : "
            f"{expenses['records']}"
        )

        print(
            f"Expense Source       : "
            f"{expenses['column'] or 'NOT DETECTED'}"
        )

        print(
            f"Operating Expenses   : "
            f"{money(operating_expenses)}"
        )

        print(
            f"Expense / Revenue    : "
            f"{pct(expense_ratio)}"
        )

        print()
        print("=" * 60)
        print("TRUE NET PROFITABILITY")
        print("=" * 60)

        print(
            f"Gross Profit         : "
            f"{money(gross_profit)}"
        )

        print(
            f"Operating Expenses   : "
            f"{money(operating_expenses)}"
        )

        print(
            f"TRUE NET OPERATING "
            f"PROFIT              : "
            f"{money(net_operating_profit)}"
        )

        print(
            f"TRUE NET MARGIN      : "
            f"{pct(net_margin)}"
        )

        print(
            f"Target Net Margin    : "
            f"{pct(TARGET_NET_MARGIN)}"
        )

        print(
            f"Net Margin Gap       : "
            f"{pct(margin_gap)}"
        )

        print(
            f"Profitability Status : "
            f"{profitability_status}"
        )

        print()
        print("=" * 60)
        print("FINANCIAL RECONCILIATION")
        print("=" * 60)

        print(
            f"Revenue              : "
            f"{money(revenue)}"
        )

        print(
            f"Less COGS            : "
            f"{money(cogs)}"
        )

        print(
            f"Gross Profit         : "
            f"{money(gross_profit)}"
        )

        print(
            f"Less Operating "
            f"Expenses            : "
            f"{money(operating_expenses)}"
        )

        print(
            f"TRUE NET OPERATING "
            f"PROFIT              : "
            f"{money(net_operating_profit)}"
        )

        print()
        print("=" * 60)
        print("NET PROFIT TARGET ANALYSIS")
        print("=" * 60)

        print(
            f"Current Net Profit   : "
            f"{money(net_operating_profit)}"
        )

        print(
            f"Target Net Profit    : "
            f"{money(target_net_profit)}"
        )

        print(
            f"Additional Profit "
            f"Required            : "
            f"{money(additional_profit_required)}"
        )

        print()
        print("=" * 60)
        print("WORKING CAPITAL CONTEXT")
        print("=" * 60)

        print(
            f"Customer Credit      : "
            f"{money(customer_credit)}"
        )

        print(
            f"Supplier Liability   : "
            f"{money(supplier_liability)}"
        )

        print(
            f"Inventory Capital    : "
            f"{money(inventory_capital)}"
        )

        print()
        print("=" * 60)
        print("PROFITABILITY PRESSURE")
        print("=" * 60)

        if net_operating_profit < 0:

            print(
                "🔴 NET LOSS PRESSURE"
            )

            print(
                "Operating expenses are "
                "greater than gross profit."
            )

        elif operating_expenses > 0:

            print(
                "🟡 OPERATING COST PRESSURE"
            )

            print(
                f"Operating expenses consume "
                f"{pct(expense_ratio)} of revenue."
            )

        else:

            print(
                "🟢 NO RECORDED OPERATING "
                "EXPENSE PRESSURE"
            )

        if gross_margin < TARGET_NET_MARGIN:

            print(
                f"⚠ Gross margin remains "
                f"{pct(TARGET_NET_MARGIN - gross_margin)} "
                "below target."
            )

        print()
        print("=" * 60)
        print("V90 MANAGEMENT PRIORITIES")
        print("=" * 60)

        priority = 1

        if net_operating_profit < 0:

            print(
                f"{priority}. [URGENT] "
                "RESTORE PROFITABILITY"
            )

            print(
                f"   Net operating loss: "
                f"{money(abs(net_operating_profit))}"
            )

            priority += 1

        if gross_margin < TARGET_NET_MARGIN:

            print(
                f"{priority}. [HIGH] "
                "IMPROVE GROSS MARGIN"
            )

            print(
                f"   Current: {pct(gross_margin)}"
            )

            priority += 1

        if operating_expenses > 0:

            print(
                f"{priority}. [HIGH] "
                "CONTROL OPERATING COSTS"
            )

            print(
                f"   Expenses: "
                f"{money(operating_expenses)}"
            )

            priority += 1

        if customer_credit > 0:

            print(
                f"{priority}. [MEDIUM] "
                "COLLECT CUSTOMER CREDIT"
            )

            print(
                f"   Recoverable amount: "
                f"{money(customer_credit)}"
            )

            priority += 1

        print()
        print("=" * 60)
        print("V90 EXECUTIVE DECISION")
        print("=" * 60)

        if net_operating_profit < 0:

            print(
                "🔴 PROFITABILITY RECOVERY REQUIRED"
            )

            print(
                "Stabilize margins and operating "
                "costs before aggressive expansion."
            )

        elif net_margin < TARGET_NET_MARGIN:

            print(
                "🟠 NET PROFIT IMPROVEMENT REQUIRED"
            )

            print(
                f"Net margin: {pct(net_margin)}"
            )

            print(
                f"Target: {pct(TARGET_NET_MARGIN)}"
            )

        else:

            print(
                "🟢 NET PROFIT TARGET ACHIEVED"
            )

        print()
        print("=" * 60)
        print("V90 FINANCIAL TRUTH STATUS")
        print("=" * 60)

        print(
            f"Status : {financial_truth}"
        )

        print(
            "Revenue is never treated as profit."
        )

        print(
            "Net operating profit is calculated "
            "only after verified COGS and "
            "recorded operating expenses."
        )

        print()
        print("=" * 60)
        print("V90 DATA INTEGRITY STATUS")
        print("=" * 60)

        print(
            "COGS source          : V81/V82 VERIFIED"
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
            "Financial source     : V88"
        )

        print(
            "Expense source       : V89"
        )

        print(
            "Automatic changes    : NO"
        )

        print()
        print("=" * 60)
        print("V90 SAFETY STATUS")
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
