import sqlite3
from pathlib import Path
from dataclasses import dataclass


DB_PATH = Path("data/posledger.db")

TARGET_MARGIN = 0.10


@dataclass
class WarningSignal:
    level: str
    title: str
    message: str
    value: str = ""


def money(value):
    return f"₦{value:,.2f}"


def get_connection():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    return sqlite3.connect(DB_PATH)


def table_exists(conn, table):
    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table' AND name=?
        """,
        (table,),
    ).fetchone()

    return row is not None


def get_columns(conn, table):
    if not table_exists(conn, table):
        return set()

    rows = conn.execute(
        f"PRAGMA table_info({table})"
    ).fetchall()

    return {row[1] for row in rows}


def safe_sum(conn, table, column):
    if not table_exists(conn, table):
        return 0.0

    columns = get_columns(conn, table)

    if column not in columns:
        return 0.0

    try:
        row = conn.execute(
            f"""
            SELECT COALESCE(SUM("{column}"), 0)
            FROM "{table}"
            """
        ).fetchone()

        return float(row[0] or 0)

    except sqlite3.Error:
        return 0.0


def get_business_position(conn):
    revenue = safe_sum(
        conn,
        "sales",
        "total_amount",
    )

    profit = safe_sum(
        conn,
        "sales",
        "total_profit",
    )

    if revenue <= 0:
        revenue = safe_sum(
            conn,
            "transactions",
            "amount",
        )

    if profit <= 0:
        profit = safe_sum(
            conn,
            "transactions",
            "profit",
        )

    margin = (
        profit / revenue
        if revenue > 0
        else 0.0
    )

    cash = 0.0
    wallet = 0.0

    if table_exists(conn, "balance"):
        columns = get_columns(conn, "balance")

        if {
            "cash_balance",
            "wallet_balance",
        }.issubset(columns):

            try:
                row = conn.execute(
                    """
                    SELECT
                        COALESCE(cash_balance, 0),
                        COALESCE(wallet_balance, 0)
                    FROM balance
                    ORDER BY id DESC
                    LIMIT 1
                    """
                ).fetchone()

                if row:
                    cash = float(row[0] or 0)
                    wallet = float(row[1] or 0)

            except sqlite3.Error:
                pass

    liquid = cash + wallet

    credit = safe_sum(
        conn,
        "customer_credit",
        "balance",
    )

    supplier = 0.0

    creditor_columns = get_columns(
        conn,
        "creditors",
    )

    if "balance" in creditor_columns:
        supplier = safe_sum(
            conn,
            "creditors",
            "balance",
        )
    elif "amount" in creditor_columns:
        supplier = safe_sum(
            conn,
            "creditors",
            "amount",
        )

    inventory = 0.0

    if table_exists(conn, "products"):
        columns = get_columns(conn, "products")

        if {
            "buying_price",
            "current_stock",
        }.issubset(columns):

            try:
                row = conn.execute(
                    """
                    SELECT COALESCE(
                        SUM(
                            buying_price *
                            current_stock
                        ),
                        0
                    )
                    FROM products
                    """
                ).fetchone()

                inventory = float(
                    row[0] or 0
                )

            except sqlite3.Error:
                pass

    expenses = safe_sum(
        conn,
        "expenses",
        "amount",
    )

    return {
        "revenue": revenue,
        "profit": profit,
        "margin": margin,
        "liquid": liquid,
        "credit": credit,
        "supplier": supplier,
        "inventory": inventory,
        "expenses": expenses,
    }


def get_sales_activity(conn):
    count = 0

    if table_exists(conn, "sales"):
        try:
            row = conn.execute(
                "SELECT COUNT(*) FROM sales"
            ).fetchone()

            count = int(row[0] or 0)

        except sqlite3.Error:
            pass

    if count == 0 and table_exists(
        conn,
        "transactions",
    ):
        try:
            row = conn.execute(
                """
                SELECT COUNT(*)
                FROM transactions
                """
            ).fetchone()

            count = int(row[0] or 0)

        except sqlite3.Error:
            pass

    return count


def build_signals(position, sales_count):
    signals = []

    revenue = position["revenue"]
    profit = position["profit"]
    margin = position["margin"]
    liquid = position["liquid"]
    credit = position["credit"]
    supplier = position["supplier"]
    inventory = position["inventory"]

    # Profitability
    if revenue > 0 and profit <= 0:
        signals.append(
            WarningSignal(
                "🔴",
                "PROFIT LOSS",
                "The business is generating revenue "
                "without positive gross profit.",
                money(profit),
            )
        )

    elif margin < TARGET_MARGIN:
        signals.append(
            WarningSignal(
                "🟠",
                "LOW MARGIN",
                "Current gross margin is below the "
                "10% management target.",
                f"{margin * 100:.2f}%",
            )
        )
    else:
        signals.append(
            WarningSignal(
                "🟢",
                "HEALTHY MARGIN",
                "Gross margin is at or above the "
                "management target.",
                f"{margin * 100:.2f}%",
            )
        )

    # Customer credit
    if credit > 0:
        signals.append(
            WarningSignal(
                "🟠",
                "CREDIT EXPOSURE",
                "Outstanding customer credit is tying "
                "up business liquidity.",
                money(credit),
            )
        )
    else:
        signals.append(
            WarningSignal(
                "🟢",
                "CREDIT CONTROL",
                "No outstanding customer credit was "
                "detected.",
                money(credit),
            )
        )

    # Supplier liability
    if supplier > liquid:
        signals.append(
            WarningSignal(
                "🔴",
                "SUPPLIER PRESSURE",
                "Supplier liability is greater than "
                "current liquid funds.",
                money(supplier),
            )
        )
    elif supplier > 0:
        signals.append(
            WarningSignal(
                "🟠",
                "SUPPLIER LIABILITY",
                "The business has outstanding supplier "
                "obligations.",
                money(supplier),
            )
        )
    else:
        signals.append(
            WarningSignal(
                "🟢",
                "SUPPLIER CONTROL",
                "No supplier liability was detected.",
                money(supplier),
            )
        )

    # Liquidity
    if liquid <= 0:
        signals.append(
            WarningSignal(
                "🔴",
                "LIQUIDITY WARNING",
                "No liquid funds are currently available.",
                money(liquid),
            )
        )
    elif supplier > 0 and liquid < supplier:
        signals.append(
            WarningSignal(
                "🟠",
                "LIQUIDITY PRESSURE",
                "Liquid funds are insufficient to fully "
                "cover supplier liability.",
                money(liquid),
            )
        )
    else:
        signals.append(
            WarningSignal(
                "🟢",
                "LIQUIDITY POSITION",
                "Liquid funds can currently cover "
                "recorded supplier liability.",
                money(liquid),
            )
        )

    # Sales activity
    if sales_count == 0:
        signals.append(
            WarningSignal(
                "🔴",
                "NO SALES DATA",
                "No recorded sales activity is available "
                "for this analysis.",
                "0",
            )
        )
    elif sales_count < 5:
        signals.append(
            WarningSignal(
                "🟡",
                "LIMITED SALES HISTORY",
                "There are few recorded sales observations, "
                "so management conclusions should remain "
                "cautious.",
                str(sales_count),
            )
        )
    else:
        signals.append(
            WarningSignal(
                "🟢",
                "SALES HISTORY",
                "There is sufficient recorded sales activity "
                "for basic business monitoring.",
                str(sales_count),
            )
        )

    # Inventory
    if inventory > 0 and revenue > 0:
        inventory_ratio = inventory / revenue

        if inventory_ratio > 1.5:
            signals.append(
                WarningSignal(
                    "🟠",
                    "HIGH INVENTORY CAPITAL",
                    "A large amount of business capital is "
                    "currently tied up in inventory.",
                    money(inventory),
                )
            )
        else:
            signals.append(
                WarningSignal(
                    "🟢",
                    "INVENTORY POSITION",
                    "Inventory capital is being monitored.",
                    money(inventory),
                )
            )

    return signals


def calculate_health_score(position, signals):
    score = 100.0

    margin = position["margin"]
    liquid = position["liquid"]
    credit = position["credit"]
    supplier = position["supplier"]
    profit = position["profit"]

    # Margin
    if margin < 0:
        score -= 30
    elif margin < 0.05:
        score -= 25
    elif margin < 0.10:
        score -= 15

    # Profit
    if profit <= 0:
        score -= 25

    # Liquidity
    if liquid <= 0:
        score -= 25
    elif supplier > liquid:
        score -= 15

    # Credit
    if credit > 10000:
        score -= 15
    elif credit > 5000:
        score -= 10
    elif credit > 0:
        score -= 5

    # Supplier
    if supplier > 15000:
        score -= 15
    elif supplier > 5000:
        score -= 8
    elif supplier > 0:
        score -= 4

    return max(0.0, min(score, 100.0))


def health_level(score):
    if score >= 80:
        return "🟢 HEALTHY"
    elif score >= 60:
        return "🟡 WATCH"
    elif score >= 40:
        return "🟠 AT RISK"
    else:
        return "🔴 CRITICAL"


def determine_primary_problem(position):
    margin = position["margin"]
    profit = position["profit"]
    credit = position["credit"]
    supplier = position["supplier"]
    liquid = position["liquid"]

    if profit <= 0:
        return (
            "PROFITABILITY LOSS",
            "Restore positive gross profit before "
            "aggressive expansion."
        )

    if margin < TARGET_MARGIN:
        return (
            "LOW PROFIT MARGIN",
            "Improve product pricing and margins "
            "before pursuing aggressive sales growth."
        )

    if supplier > liquid:
        return (
            "LIQUIDITY PRESSURE",
            "Increase available liquidity and control "
            "supplier obligations."
        )

    if credit > 0:
        return (
            "CUSTOMER CREDIT EXPOSURE",
            "Collect outstanding customer balances "
            "to strengthen liquidity."
        )

    return (
        "NO CRITICAL PROBLEM DETECTED",
        "Continue monitoring profitability, liquidity "
        "and sales trends."
    )


def print_report(position, sales_count, signals):
    score = calculate_health_score(
        position,
        signals,
    )

    level = health_level(score)

    problem, action = determine_primary_problem(
        position
    )

    print("=" * 60)
    print("POS LEDGER NG V61")
    print("BUSINESS HEALTH & EARLY WARNING INTELLIGENCE")
    print("=" * 60)

    print("\n" + "=" * 60)
    print("CURRENT BUSINESS POSITION")
    print("=" * 60)

    print(
        f"Revenue              : "
        f"{money(position['revenue'])}"
    )

    print(
        f"Gross Profit         : "
        f"{money(position['profit'])}"
    )

    print(
        f"Gross Margin         : "
        f"{position['margin'] * 100:.2f}%"
    )

    print(
        f"Liquid Funds         : "
        f"{money(position['liquid'])}"
    )

    print(
        f"Customer Credit      : "
        f"{money(position['credit'])}"
    )

    print(
        f"Supplier Liability   : "
        f"{money(position['supplier'])}"
    )

    print(
        f"Inventory Capital    : "
        f"{money(position['inventory'])}"
    )

    print(
        f"Recorded Expenses    : "
        f"{money(position['expenses'])}"
    )

    print(
        f"Recorded Sales       : "
        f"{sales_count}"
    )

    print("\n" + "=" * 60)
    print("BUSINESS HEALTH")
    print("=" * 60)

    print(
        f"Health Score         : "
        f"{score:.2f}/100"
    )

    print(
        f"Health Status        : "
        f"{level}"
    )

    print("\n" + "=" * 60)
    print("EARLY WARNING SIGNALS")
    print("=" * 60)

    for signal in signals:
        print("-" * 40)
        print(
            f"{signal.level} {signal.title}"
        )
        print(
            f"Message             : "
            f"{signal.message}"
        )

        if signal.value:
            print(
                f"Value               : "
                f"{signal.value}"
            )

    print("\n" + "=" * 60)
    print("PRIMARY MANAGEMENT PROBLEM")
    print("=" * 60)

    print(
        f"Problem              : {problem}"
    )

    print(
        f"Recommended Action    : {action}"
    )

    print("\n" + "=" * 60)
    print("MANAGEMENT PRIORITIES")
    print("=" * 60)

    if position["margin"] < TARGET_MARGIN:
        print(
            "1. Improve gross margin toward 10%."
        )

    if position["credit"] > 0:
        print(
            "2. Collect outstanding customer credit."
        )

    if position["supplier"] > position["liquid"]:
        print(
            "3. Reduce supplier liquidity pressure."
        )

    if sales_count < 5:
        print(
            "4. Continue recording sales to build "
            "a stronger historical dataset."
        )

    if position["inventory"] > 0:
        print(
            "5. Monitor inventory capital and "
            "stock turnover."
        )

    print("\n" + "=" * 60)
    print("V61 SAFETY STATUS")
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


def main():
    try:
        conn = get_connection()

        try:
            position = get_business_position(conn)
            sales_count = get_sales_activity(conn)

            signals = build_signals(
                position,
                sales_count,
            )

            print_report(
                position,
                sales_count,
                signals,
            )

        finally:
            conn.close()

    except Exception as exc:
        print("=" * 60)
        print("V61 ERROR")
        print("=" * 60)
        print(str(exc))
        print("=" * 60)


if __name__ == "__main__":
    main()
