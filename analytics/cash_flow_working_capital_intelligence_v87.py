import sqlite3
from pathlib import Path

DB_PATH = Path("data/posledger.db")


def money(value):
    return f"₦{value:,.2f}"


def pct(value):
    return f"{value * 100:.2f}%"


def safe_float(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def table_exists(conn, table):
    row = conn.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' AND name=?",
        (table,)
    ).fetchone()
    return row is not None


def column_exists(conn, table, column):
    if not table_exists(conn, table):
        return False

    columns = conn.execute(
        f"PRAGMA table_info({table})"
    ).fetchall()

    return any(row["name"] == column for row in columns)


def get_balance(conn):
    """
    Try to detect the current liquid balance from common POS Ledger NG
    balance structures without modifying anything.
    """

    candidates = [
        ("balances", ["balance", "current_balance", "amount"]),
        ("business_balance", ["balance", "current_balance", "amount"]),
        ("cash_balance", ["balance", "current_balance", "amount"]),
    ]

    for table, columns in candidates:
        if not table_exists(conn, table):
            continue

        for column in columns:
            if column_exists(conn, table, column):
                try:
                    row = conn.execute(
                        f"SELECT {column} FROM {table} "
                        f"ORDER BY rowid DESC LIMIT 1"
                    ).fetchone()

                    if row:
                        return safe_float(row[0]), table, column
                except sqlite3.Error:
                    pass

    return None, None, None


def get_customer_credit(conn):
    if not table_exists(conn, "customer_credit"):
        return 0.0

    possible_columns = [
        "amount",
        "credit_amount",
        "outstanding_amount",
        "balance",
        "amount_due",
    ]

    for column in possible_columns:
        if column_exists(conn, "customer_credit", column):
            try:
                row = conn.execute(
                    f"""
                    SELECT COALESCE(SUM({column}), 0)
                    FROM customer_credit
                    """
                ).fetchone()

                return safe_float(row[0])
            except sqlite3.Error:
                pass

    return 0.0


def get_supplier_liability(conn):
    if not table_exists(conn, "suppliers"):
        return 0.0

    possible_columns = [
        "balance",
        "outstanding",
        "outstanding_balance",
        "amount_due",
        "credit_balance",
        "liability",
    ]

    for column in possible_columns:
        if column_exists(conn, "suppliers", column):
            try:
                row = conn.execute(
                    f"""
                    SELECT COALESCE(SUM({column}), 0)
                    FROM suppliers
                    """
                ).fetchone()

                return safe_float(row[0])
            except sqlite3.Error:
                pass

    return 0.0


def get_inventory_capital(conn):
    if not table_exists(conn, "products"):
        return 0.0

    if not column_exists(conn, "products", "current_stock"):
        return 0.0

    if not column_exists(conn, "products", "buying_price"):
        return 0.0

    row = conn.execute("""
        SELECT COALESCE(
            SUM(
                COALESCE(current_stock, 0) *
                COALESCE(buying_price, 0)
            ),
            0
        )
        FROM products
    """).fetchone()

    return safe_float(row[0])


def get_verified_sales(conn):
    if not table_exists(conn, "sales"):
        return 0.0, 0.0, 0.0

    revenue = 0.0
    cogs = 0.0
    profit = 0.0

    try:
        row = conn.execute("""
            SELECT
                COALESCE(SUM(total_amount), 0),
                COALESCE(SUM(cogs), 0),
                COALESCE(SUM(gross_profit), 0)
            FROM sales
            WHERE UPPER(COALESCE(status, 'COMPLETED')) = 'COMPLETED'
        """).fetchone()

        revenue = safe_float(row[0])
        cogs = safe_float(row[1])
        profit = safe_float(row[2])

    except sqlite3.Error:
        pass

    return revenue, cogs, profit


def get_expenses(conn):
    if not table_exists(conn, "expenses"):
        return 0.0

    possible_columns = [
        "amount",
        "expense_amount",
        "total_amount",
    ]

    for column in possible_columns:
        if column_exists(conn, "expenses", column):
            try:
                row = conn.execute(
                    f"""
                    SELECT COALESCE(SUM({column}), 0)
                    FROM expenses
                    """
                ).fetchone()

                return safe_float(row[0])
            except sqlite3.Error:
                pass

    return 0.0


def main():
    print("=" * 60)
    print("POS LEDGER NG V87")
    print("CASH FLOW & WORKING CAPITAL INTELLIGENCE")
    print("=" * 60)

    if not DB_PATH.exists():
        print(f"\nDatabase not found: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        liquid_funds, balance_table, balance_column = get_balance(conn)
        customer_credit = get_customer_credit(conn)
        supplier_liability = get_supplier_liability(conn)
        inventory_capital = get_inventory_capital(conn)
        revenue, cogs, gross_profit = get_verified_sales(conn)
        expenses = get_expenses(conn)

        if liquid_funds is None:
            liquid_funds = 0.0
            balance_status = "NOT DETECTED"
        else:
            balance_status = (
                f"{balance_table}.{balance_column}"
            )

        supplier_gap = max(
            supplier_liability - liquid_funds,
            0.0
        )

        working_capital_position = (
            liquid_funds
            + customer_credit
            - supplier_liability
        )

        recoverable_position = (
            liquid_funds
            + customer_credit
        )

        total_current_resources = (
            liquid_funds
            + customer_credit
            + inventory_capital
        )

        net_operating_position = (
            total_current_resources
            - supplier_liability
        )

        print("\n" + "=" * 60)
        print("VERIFIED WORKING CAPITAL POSITION")
        print("=" * 60)

        print(f"Liquid Funds          : {money(liquid_funds)}")
        print(f"Customer Credit       : {money(customer_credit)}")
        print(f"Supplier Liability    : {money(supplier_liability)}")
        print(f"Supplier Payment Gap  : {money(supplier_gap)}")
        print(f"Inventory Capital     : {money(inventory_capital)}")
        print(
            f"Working Capital Position: "
            f"{money(working_capital_position)}"
        )
        print(
            f"Net Operating Position: "
            f"{money(net_operating_position)}"
        )

        print("\n" + "=" * 60)
        print("CASH FLOW COMPONENTS")
        print("=" * 60)

        print(f"Verified Revenue      : {money(revenue)}")
        print(f"Verified COGS         : {money(cogs)}")
        print(f"Verified Gross Profit : {money(gross_profit)}")
        print(f"Recorded Expenses     : {money(expenses)}")

        operating_result = gross_profit - expenses

        print(
            f"Approx. Operating Result: "
            f"{money(operating_result)}"
        )

        print("\n" + "=" * 60)
        print("LIQUIDITY COVERAGE")
        print("=" * 60)

        if supplier_liability > 0:
            coverage = liquid_funds / supplier_liability
        else:
            coverage = 1.0

        print(f"Liquid Funds          : {money(liquid_funds)}")
        print(f"Supplier Liability    : {money(supplier_liability)}")
        print(f"Supplier Coverage     : {pct(coverage)}")

        if supplier_liability == 0:
            liquidity_status = "🟢 NO SUPPLIER PAYMENT PRESSURE"
        elif coverage >= 1:
            liquidity_status = "🟢 SUPPLIER OBLIGATIONS COVERED"
        elif coverage >= 0.75:
            liquidity_status = "🟡 MODERATE LIQUIDITY PRESSURE"
        else:
            liquidity_status = "🔴 HIGH LIQUIDITY PRESSURE"

        print(f"Liquidity Status      : {liquidity_status}")

        print("\n" + "=" * 60)
        print("RECOVERABLE LIQUIDITY")
        print("=" * 60)

        print(f"Current Liquid Funds  : {money(liquid_funds)}")
        print(f"Customer Credit       : {money(customer_credit)}")
        print(
            f"Potential Available Resources: "
            f"{money(recoverable_position)}"
        )

        if supplier_gap > 0:
            remaining_after_collection = (
                recoverable_position - supplier_liability
            )

            print(
                f"After Credit Collection: "
                f"{money(remaining_after_collection)}"
            )
        else:
            print(
                "Customer credit could increase liquidity "
                "without a current supplier funding gap."
            )

        print("\n" + "=" * 60)
        print("WORKING CAPITAL SCENARIOS")
        print("=" * 60)

        # Scenario 1: collect all customer credit
        scenario_collection = (
            liquid_funds
            + customer_credit
            - supplier_liability
        )

        # Scenario 2: pay suppliers with existing cash
        scenario_supplier_payment = (
            liquid_funds
            - supplier_liability
            + customer_credit
        )

        # Scenario 3: collect credit and pay suppliers
        scenario_both = (
            liquid_funds
            + customer_credit
            - supplier_liability
        )

        # Scenario 4: convert 25% of inventory into cash
        inventory_conversion = inventory_capital * 0.25

        scenario_inventory_conversion = (
            liquid_funds
            + inventory_conversion
            + customer_credit
            - supplier_liability
        )

        print(
            f"1. Collect customer credit : "
            f"{money(scenario_collection)}"
        )
        print(
            f"2. Pay supplier liabilities : "
            f"{money(scenario_supplier_payment)}"
        )
        print(
            f"3. Collect + pay suppliers  : "
            f"{money(scenario_both)}"
        )
        print(
            f"4. Convert 25% inventory    : "
            f"{money(scenario_inventory_conversion)}"
        )

        print("\n" + "=" * 60)
        print("WORKING CAPITAL RISK")
        print("=" * 60)

        if supplier_gap > 0:
            print("🔴 SUPPLIER FUNDING GAP DETECTED")
            print(
                f"Immediate gap: {money(supplier_gap)}"
            )
        elif customer_credit > liquid_funds:
            print("🟡 LIQUIDITY DEPENDS ON CREDIT COLLECTION")
            print(
                "Customer credit is larger than current liquid funds."
            )
        else:
            print("🟢 CURRENT WORKING CAPITAL POSITION IS STABLE")

        if inventory_capital > revenue and revenue > 0:
            inventory_exposure = inventory_capital / revenue
            print(
                f"Inventory / Revenue Exposure: "
                f"{pct(inventory_exposure)}"
            )
            print(
                "Inventory capital is significant relative "
                "to verified revenue."
            )

        print("\n" + "=" * 60)
        print("V87 MANAGEMENT PRIORITIES")
        print("=" * 60)

        priorities = []

        if supplier_gap > 0:
            priorities.append(
                (
                    "URGENT",
                    "PROTECT LIQUIDITY",
                    f"Supplier gap is {money(supplier_gap)}."
                )
            )

        if customer_credit > 0:
            priorities.append(
                (
                    "HIGH",
                    "COLLECT CUSTOMER CREDIT",
                    f"{money(customer_credit)} may be recoverable liquidity."
                )
            )

        if inventory_capital > revenue and revenue > 0:
            priorities.append(
                (
                    "MEDIUM",
                    "CONTROL INVENTORY CAPITAL",
                    f"{money(inventory_capital)} is tied up in stock."
                )
            )

        if expenses > gross_profit:
            priorities.append(
                (
                    "HIGH",
                    "CONTROL EXPENSES",
                    "Recorded expenses exceed verified gross profit."
                )
            )

        if not priorities:
            priorities.append(
                (
                    "MONITOR",
                    "MAINTAIN WORKING CAPITAL",
                    "No critical working-capital exception detected."
                )
            )

        for number, (level, decision, reason) in enumerate(
            priorities,
            1
        ):
            print("-" * 40)
            print(f"{number}. [{level}] {decision}")
            print(f"Reason : {reason}")

        print("\n" + "=" * 60)
        print("V87 EXECUTIVE DECISION")
        print("=" * 60)

        if supplier_gap > 0:
            print("🔴 PROTECT LIQUIDITY BEFORE EXPANSION")
            print(
                f"Required liquidity improvement: "
                f"{money(supplier_gap)}"
            )
        elif customer_credit > 0:
            print("🟡 STRENGTHEN LIQUIDITY THROUGH COLLECTION")
            print(
                f"Potential recoverable credit: "
                f"{money(customer_credit)}"
            )
        else:
            print("🟢 WORKING CAPITAL POSITION STABLE")

        print("\n" + "=" * 60)
        print("V87 MANAGEMENT INTERPRETATION")
        print("=" * 60)

        print(
            "V87 integrates liquid funds, customer credit, "
            "supplier obligations, inventory capital, verified "
            "profitability and expenses into one working-capital view."
        )

        print(
            "The module separates current liquidity from potential "
            "recoverable liquidity and inventory capital."
        )

        print(
            "Scenario values are analytical simulations only. "
            "V87 does not collect credit, pay suppliers, sell stock, "
            "or modify financial records automatically."
        )

        print("\n" + "=" * 60)
        print("V87 DATA INTEGRITY STATUS")
        print("=" * 60)
        print(
            f"Balance source        : {balance_status}"
        )
        print("Profitability source  : VERIFIED V81/V82")
        print("Pricing source        : V83/V84")
        print("Demand source         : V85")
        print("Inventory source      : products.current_stock")
        print("Customer credit source: customer_credit")
        print("Supplier source       : suppliers")
        print("Automatic transactions: NO")

        print("\n" + "=" * 60)
        print("V87 SAFETY STATUS")
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
