import sqlite3
from pathlib import Path
from dataclasses import dataclass


DB_PATH = Path("data/posledger.db")
TARGET_MARGIN = 0.10


@dataclass
class Action:
    priority: str
    level: int
    title: str
    message: str
    value: float = 0.0
    target: float = 0.0


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
        WHERE type = 'table'
        AND name = ?
        """,
        (table,),
    ).fetchone()

    return row is not None


def column_exists(conn, table, column):
    if not table_exists(conn, table):
        return False

    rows = conn.execute(
        f"PRAGMA table_info({table})"
    ).fetchall()

    return any(row[1] == column for row in rows)


def safe_sum(conn, table, column):
    if not column_exists(conn, table, column):
        return 0.0

    try:
        row = conn.execute(
            f"""
            SELECT COALESCE(SUM({column}), 0)
            FROM {table}
            """
        ).fetchone()

        return float(row[0] or 0)

    except sqlite3.Error:
        return 0.0


def get_latest_balance(conn):
    cash = 0.0
    wallet = 0.0

    if not table_exists(conn, "balance"):
        return 0.0

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

    return cash + wallet


def get_inventory_capital(conn):
    if not table_exists(conn, "products"):
        return 0.0

    if not column_exists(conn, "products", "buying_price"):
        return 0.0

    if not column_exists(conn, "products", "current_stock"):
        return 0.0

    try:
        row = conn.execute(
            """
            SELECT COALESCE(
                SUM(buying_price * current_stock),
                0
            )
            FROM products
            """
        ).fetchone()

        return float(row[0] or 0)

    except sqlite3.Error:
        return 0.0


def get_sales_count(conn):
    if not table_exists(conn, "sales"):
        return 0

    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM sales"
        ).fetchone()

        return int(row[0] or 0)

    except sqlite3.Error:
        return 0


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

    liquid = get_latest_balance(conn)

    credit = safe_sum(
        conn,
        "customer_credit",
        "balance",
    )

    supplier = safe_sum(
        conn,
        "creditors",
        "balance",
    )

    inventory = get_inventory_capital(conn)

    sales_count = get_sales_count(conn)

    return {
        "revenue": revenue,
        "profit": profit,
        "margin": margin,
        "liquid": liquid,
        "credit": credit,
        "supplier": supplier,
        "inventory": inventory,
        "sales_count": sales_count,
    }


def build_actions(base):
    actions = []

    revenue = base["revenue"]
    profit = base["profit"]
    margin = base["margin"]
    liquid = base["liquid"]
    credit = base["credit"]
    supplier = base["supplier"]
    inventory = base["inventory"]

    # --------------------------------------------------
    # URGENT: SUPPLIER PRESSURE
    # --------------------------------------------------

    supplier_gap = max(
        supplier - liquid,
        0,
    )

    if supplier_gap > 0:
        actions.append(
            Action(
                priority="URGENT",
                level=1,
                title="REDUCE SUPPLIER PRESSURE",
                message=(
                    "Supplier liabilities exceed "
                    "available liquid funds. "
                    "Protect cash flow before "
                    "aggressive expansion."
                ),
                value=supplier_gap,
                target=0.0,
            )
        )

    # --------------------------------------------------
    # URGENT: CUSTOMER CREDIT
    # --------------------------------------------------

    if credit > 0:
        actions.append(
            Action(
                priority="URGENT",
                level=1,
                title="COLLECT CUSTOMER CREDIT",
                message=(
                    "Outstanding customer credit "
                    "is tying up business liquidity. "
                    "Prioritize collection."
                ),
                value=credit,
                target=0.0,
            )
        )

    # --------------------------------------------------
    # HIGH: MARGIN
    # --------------------------------------------------

    margin_gap = max(
        TARGET_MARGIN - margin,
        0,
    )

    if margin_gap > 0:
        actions.append(
            Action(
                priority="HIGH",
                level=2,
                title="IMPROVE GROSS MARGIN",
                message=(
                    "Current gross margin is below "
                    "the 10% management target. "
                    "Review product pricing and "
                    "low-margin products."
                ),
                value=margin * 100,
                target=TARGET_MARGIN * 100,
            )
        )

    # --------------------------------------------------
    # HIGH: PROFITABILITY
    # --------------------------------------------------

    if revenue > 0 and profit <= 0:
        actions.append(
            Action(
                priority="HIGH",
                level=2,
                title="RESTORE PROFITABILITY",
                message=(
                    "Revenue is being recorded without "
                    "sufficient gross profit. Review "
                    "selling prices and product costs."
                ),
                value=profit,
                target=0.0,
            )
        )

    # --------------------------------------------------
    # MEDIUM: LIQUIDITY
    # --------------------------------------------------

    if supplier > 0:
        liquidity_ratio = liquid / supplier

        if liquidity_ratio < 1:
            actions.append(
                Action(
                    priority="MEDIUM",
                    level=3,
                    title="STRENGTHEN LIQUIDITY",
                    message=(
                        "Available liquid funds do not "
                        "fully cover supplier obligations. "
                        "Avoid unnecessary cash withdrawals "
                        "and monitor daily cash flow."
                    ),
                    value=liquid,
                    target=supplier,
                )
            )

    # --------------------------------------------------
    # MEDIUM: INVENTORY
    # --------------------------------------------------

    if inventory > 0:
        actions.append(
            Action(
                priority="MEDIUM",
                level=3,
                title="MONITOR INVENTORY CAPITAL",
                message=(
                    "A significant amount of capital "
                    "is tied up in inventory. Monitor "
                    "stock turnover and slow-moving items."
                ),
                value=inventory,
                target=0.0,
            )
        )

    # --------------------------------------------------
    # LOW: GROWTH
    # --------------------------------------------------

    if (
        margin >= TARGET_MARGIN
        and credit == 0
        and supplier_gap == 0
    ):
        actions.append(
            Action(
                priority="LOW",
                level=4,
                title="CONSIDER CONTROLLED GROWTH",
                message=(
                    "Core financial pressures are "
                    "controlled. Controlled sales growth "
                    "may now be considered."
                ),
                value=revenue,
                target=revenue * 1.10,
            )
        )

    # --------------------------------------------------
    # MONITOR
    # --------------------------------------------------

    if base["sales_count"] > 0:
        actions.append(
            Action(
                priority="MONITOR",
                level=5,
                title="MONITOR SALES PERFORMANCE",
                message=(
                    "Continue monitoring revenue, "
                    "profit and sales activity before "
                    "making aggressive growth decisions."
                ),
                value=base["sales_count"],
                target=0.0,
            )
        )

    return actions


def print_report(base, actions):
    actions.sort(key=lambda x: x.level)

    print("=" * 60)
    print("POS LEDGER NG V62")
    print("MANAGEMENT ACTION & PRIORITY INTELLIGENCE")
    print("=" * 60)

    print("\n" + "=" * 60)
    print("CURRENT BUSINESS POSITION")
    print("=" * 60)

    print(
        f"Revenue              : "
        f"{money(base['revenue'])}"
    )

    print(
        f"Gross Profit         : "
        f"{money(base['profit'])}"
    )

    print(
        f"Gross Margin         : "
        f"{base['margin'] * 100:.2f}%"
    )

    print(
        f"Liquid Funds         : "
        f"{money(base['liquid'])}"
    )

    print(
        f"Customer Credit      : "
        f"{money(base['credit'])}"
    )

    print(
        f"Supplier Liability   : "
        f"{money(base['supplier'])}"
    )

    print(
        f"Inventory Capital    : "
        f"{money(base['inventory'])}"
    )

    print(
        f"Recorded Sales       : "
        f"{base['sales_count']}"
    )

    print("\n" + "=" * 60)
    print("MANAGEMENT ACTIONS")
    print("=" * 60)

    if not actions:
        print(
            "\nNo immediate management actions "
            "were detected."
        )

    for number, action in enumerate(actions, 1):
        print("-" * 40)

        print(
            f"{number}. "
            f"[{action.priority}] "
            f"{action.title}"
        )

        print(
            f"Message             : "
            f"{action.message}"
        )

        if action.title == "IMPROVE GROSS MARGIN":
            print(
                f"Current Margin      : "
                f"{action.value:.2f}%"
            )
            print(
                f"Target Margin       : "
                f"{action.target:.2f}%"
            )
        else:
            print(
                f"Current Value       : "
                f"{money(action.value)}"
            )

            if action.target > 0:
                print(
                    f"Target              : "
                    f"{money(action.target)}"
                )

    # --------------------------------------------------
    # TOP ACTION
    # --------------------------------------------------

    print("\n" + "=" * 60)
    print("TOP MANAGEMENT ACTION")
    print("=" * 60)

    if actions:
        top = actions[0]

        print(
            f"Priority            : "
            f"{top.priority}"
        )

        print(
            f"Action              : "
            f"{top.title}"
        )

        print(
            f"Recommendation      : "
            f"{top.message}"
        )
    else:
        print("No immediate action required.")

    # --------------------------------------------------
    # DECISION LOGIC
    # --------------------------------------------------

    print("\n" + "=" * 60)
    print("MANAGEMENT LOGIC")
    print("=" * 60)

    if base["margin"] < TARGET_MARGIN:
        print(
            "1. Margin improvement comes before "
            "aggressive sales growth."
        )

    if base["credit"] > 0:
        print(
            "2. Customer credit collection should "
            "improve available liquidity."
        )

    if base["supplier"] > base["liquid"]:
        print(
            "3. Supplier obligations currently "
            "exceed liquid funds."
        )

    if base["inventory"] > 0:
        print(
            "4. Inventory capital should be monitored "
            "for turnover efficiency."
        )

    print("\n" + "=" * 60)
    print("V62 SAFETY STATUS")
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
            base = get_business_position(conn)
            actions = build_actions(base)
            print_report(base, actions)

        finally:
            conn.close()

    except Exception as exc:
        print("=" * 60)
        print("V62 ERROR")
        print("=" * 60)
        print(str(exc))


if __name__ == "__main__":
    main()
