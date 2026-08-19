import sqlite3
from pathlib import Path
from dataclasses import dataclass


DB_PATH = Path("data/posledger.db")
TARGET_MARGIN = 0.10


@dataclass
class Action:
    rank: int
    priority: str
    action: str
    reason: str
    current_value: float
    target_value: float
    expected_impact: float
    confidence: float
    risk: str
    risk_score: float


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


def safe_sum(conn, table, column):
    if not table_exists(conn, table):
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


def safe_count(conn, table):
    if not table_exists(conn, table):
        return 0

    try:
        row = conn.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()

        return int(row[0] or 0)

    except sqlite3.Error:
        return 0


def get_balance(conn):
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


def get_inventory(conn):
    if not table_exists(conn, "products"):
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


def get_business_position(conn):
    revenue = safe_sum(
        conn, "sales", "total_amount"
    )

    profit = safe_sum(
        conn, "sales", "total_profit"
    )

    sales_count = safe_count(conn, "sales")

    if revenue <= 0:
        revenue = safe_sum(
            conn, "transactions", "amount"
        )

    if profit <= 0:
        profit = safe_sum(
            conn, "transactions", "profit"
        )

    if sales_count <= 0:
        sales_count = safe_count(
            conn, "transactions"
        )

    margin = (
        profit / revenue
        if revenue > 0
        else 0.0
    )

    liquid = get_balance(conn)

    credit = safe_sum(
        conn,
        "customer_credit",
        "balance"
    )

    supplier = safe_sum(
        conn,
        "creditors",
        "balance"
    )

    inventory = get_inventory(conn)

    expenses = safe_sum(
        conn,
        "expenses",
        "amount"
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
        "sales_count": sales_count,
    }


def build_actions(base):
    actions = []

    supplier_gap = max(
        base["supplier"] - base["liquid"],
        0
    )

    margin_gap = max(
        TARGET_MARGIN - base["margin"],
        0
    )

    margin_profit_opportunity = max(
        base["revenue"] * TARGET_MARGIN
        - base["profit"],
        0
    )

    # 1. Liquidity protection
    if supplier_gap > 0:
        actions.append(
            Action(
                0,
                "URGENT",
                "PROTECT LIQUIDITY",
                (
                    "Supplier obligations exceed "
                    "available liquid funds."
                ),
                supplier_gap,
                0,
                supplier_gap,
                90,
                "🟠 HIGH",
                60,
            )
        )

    # 2. Credit collection
    if base["credit"] > 0:
        actions.append(
            Action(
                0,
                "HIGH",
                "COLLECT CUSTOMER CREDIT",
                (
                    "Outstanding customer credit "
                    "represents recoverable liquidity."
                ),
                base["credit"],
                0,
                base["credit"],
                90,
                "🟡 MODERATE",
                35,
            )
        )

    # 3. Margin improvement
    if margin_gap > 0:
        actions.append(
            Action(
                0,
                "HIGH",
                "IMPROVE GROSS MARGIN",
                (
                    "Current margin is below the "
                    "10% management target."
                ),
                base["margin"] * 100,
                TARGET_MARGIN * 100,
                margin_profit_opportunity,
                90,
                "🟡 MODERATE",
                35,
            )
        )

    # 4. Inventory control
    if base["inventory"] > 0:
        actions.append(
            Action(
                0,
                "MEDIUM",
                "CONTROL INVENTORY CAPITAL",
                (
                    "Capital is tied up in inventory. "
                    "Monitor turnover and slow-moving stock."
                ),
                base["inventory"],
                0,
                base["inventory"],
                80,
                "🟡 MODERATE",
                40,
            )
        )

    # 5. Sales data
    if base["sales_count"] < 30:
        actions.append(
            Action(
                0,
                "MONITOR",
                "STRENGTHEN SALES DATA",
                (
                    "More historical sales data will "
                    "improve forecast reliability."
                ),
                base["sales_count"],
                30,
                0,
                65,
                "🟡 MODERATE",
                35,
            )
        )

    priority_order = {
        "URGENT": 1,
        "HIGH": 2,
        "MEDIUM": 3,
        "MONITOR": 4,
    }

    actions.sort(
        key=lambda x: (
            priority_order.get(x.priority, 9),
            -x.expected_impact,
        )
    )

    for index, action in enumerate(actions, 1):
        action.rank = index

    return actions


def print_report(base, actions):
    supplier_gap = max(
        base["supplier"] - base["liquid"],
        0
    )

    total_recoverable = (
        base["credit"]
        + supplier_gap
    )

    margin_opportunity = max(
        base["revenue"] * TARGET_MARGIN
        - base["profit"],
        0
    )

    print("=" * 60)
    print("POS LEDGER NG V70")
    print("DECISION ACTION PLANNER INTELLIGENCE")
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
    print("EXECUTIVE ACTION PLAN")
    print("=" * 60)

    if not actions:
        print("No management actions detected.")
    else:
        for action in actions:
            print("-" * 40)

            print(
                f"{action.rank}. "
                f"[{action.priority}] "
                f"{action.action}"
            )

            print(
                f"Reason            : "
                f"{action.reason}"
            )

            print(
                f"Current Value     : "
                f"{money(action.current_value)}"
            )

            print(
                f"Target Value      : "
                f"{money(action.target_value)}"
            )

            print(
                f"Expected Impact   : "
                f"{money(action.expected_impact)}"
            )

            print(
                f"Confidence        : "
                f"{action.confidence:.2f}%"
            )

            print(
                f"Risk              : "
                f"{action.risk}"
            )

            print(
                f"Risk Score        : "
                f"{action.risk_score:.2f}/100"
            )

    print("\n" + "=" * 60)
    print("FINANCIAL OPPORTUNITIES")
    print("=" * 60)

    print(
        f"Recoverable Credit       : "
        f"{money(base['credit'])}"
    )

    print(
        f"Supplier Liquidity Gap   : "
        f"{money(supplier_gap)}"
    )

    print(
        f"Margin Improvement Value : "
        f"{money(margin_opportunity)}"
    )

    print(
        f"Total Immediate Signals  : "
        f"{money(total_recoverable)}"
    )

    print("\n" + "=" * 60)
    print("TOP MANAGEMENT ACTION")
    print("=" * 60)

    if actions:
        top = actions[0]

        print(
            f"Priority          : "
            f"{top.priority}"
        )

        print(
            f"Action            : "
            f"{top.action}"
        )

        print(
            f"Confidence        : "
            f"{top.confidence:.2f}%"
        )

        print(
            f"Risk              : "
            f"{top.risk}"
        )

        print(
            f"Expected Impact   : "
            f"{money(top.expected_impact)}"
        )

        print(
            f"Reason            : "
            f"{top.reason}"
        )

    print("\n" + "=" * 60)
    print("7-DAY MANAGEMENT EXECUTION PLAN")
    print("=" * 60)

    print("DAY 1-2 : Protect liquidity and review supplier obligations.")

    print("DAY 2-3 : Begin customer credit collection.")

    print("DAY 3-4 : Review products below the 10% margin target.")

    print("DAY 4-5 : Identify slow-moving inventory.")

    print("DAY 5-7 : Monitor sales, liquidity and margin changes.")

    print("\n" + "=" * 60)
    print("MANAGEMENT INTERPRETATION")
    print("=" * 60)

    if supplier_gap > 0:
        print(
            "Immediate priority is liquidity protection "
            "because supplier obligations exceed available "
            "liquid funds."
        )

    if base["credit"] > 0:
        print(
            "Customer credit should be actively monitored "
            "because collection can strengthen liquidity."
        )

    if base["margin"] < TARGET_MARGIN:
        print(
            "Pricing and product margins should be reviewed "
            "before aggressive sales expansion."
        )

    if base["inventory"] > 0:
        print(
            "Inventory capital should be monitored for "
            "turnover efficiency."
        )

    print("\n" + "=" * 60)
    print("V70 DECISION LOGIC")
    print("=" * 60)

    print("1. Protect liquidity before expansion.")
    print("2. Recover outstanding customer credit.")
    print("3. Improve gross margin toward 10%.")
    print("4. Reduce capital tied up in slow inventory.")
    print("5. Increase historical data before relying heavily on forecasts.")

    print("\n" + "=" * 60)
    print("V70 SAFETY STATUS")
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
        print("V70 ERROR")
        print("=" * 60)
        print(str(exc))


if __name__ == "__main__":
    main()
