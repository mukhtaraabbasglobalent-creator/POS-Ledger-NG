import sqlite3
from pathlib import Path
from dataclasses import dataclass


DB_PATH = Path("data/posledger.db")

TARGET_MARGIN = 0.10


@dataclass
class Decision:
    priority: str
    action: str
    reason: str
    score: float
    confidence: float
    risk: str


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
        WHERE type='table'
        AND name=?
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


def get_balance(conn):
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
            return float(row[0] or 0) + float(row[1] or 0)

    except sqlite3.Error:
        pass

    return 0.0


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


def get_sales_count(conn):
    if not table_exists(conn, "sales"):
        return 0

    try:
        row = conn.execute(
            """
            SELECT COUNT(*)
            FROM sales
            """
        ).fetchone()

        return int(row[0] or 0)

    except sqlite3.Error:
        return 0


def get_position(conn):
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

    liquid = get_balance(conn)

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

    inventory = get_inventory(conn)

    expenses = safe_sum(
        conn,
        "expenses",
        "amount",
    )

    sales_count = get_sales_count(conn)

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


def calculate_decision(base):
    margin = base["margin"]
    liquid = base["liquid"]
    credit = base["credit"]
    supplier = base["supplier"]
    inventory = base["inventory"]
    revenue = base["revenue"]

    decisions = []

    # Supplier pressure
    if supplier > liquid:
        gap = supplier - liquid

        decisions.append(
            Decision(
                priority="URGENT",
                action="PROTECT LIQUIDITY",
                reason=(
                    "Supplier obligations exceed "
                    f"available liquid funds by {money(gap)}."
                ),
                score=95,
                confidence=90,
                risk="🟠 HIGH",
            )
        )

    # Credit collection
    if credit > 0:
        decisions.append(
            Decision(
                priority="HIGH",
                action="COLLECT CUSTOMER CREDIT",
                reason=(
                    "Outstanding customer credit represents "
                    f"{money(credit)} of potentially recoverable liquidity."
                ),
                score=90,
                confidence=90,
                risk="🟡 MODERATE",
            )
        )

    # Margin improvement
    if margin < TARGET_MARGIN:
        decisions.append(
            Decision(
                priority="HIGH",
                action="IMPROVE GROSS MARGIN",
                reason=(
                    f"Gross margin is {margin * 100:.2f}%, "
                    f"below the {TARGET_MARGIN * 100:.0f}% "
                    "management target."
                ),
                score=88,
                confidence=90,
                risk="🟡 MODERATE",
            )
        )

    # Inventory
    if inventory > 0:
        decisions.append(
            Decision(
                priority="MEDIUM",
                action="CONTROL INVENTORY CAPITAL",
                reason=(
                    f"{money(inventory)} is currently tied "
                    "up in inventory."
                ),
                score=75,
                confidence=80,
                risk="🟡 MODERATE",
            )
        )

    # Sales evidence
    if sales_count := base["sales_count"]:
        if sales_count < 20:
            decisions.append(
                Decision(
                    priority="MONITOR",
                    action="STRENGTHEN SALES DATA",
                    reason=(
                        f"Only {sales_count} recorded sales are "
                        "available for management analysis."
                    ),
                    score=60,
                    confidence=65,
                    risk="🟡 MODERATE",
                )
            )

    if not decisions:
        decisions.append(
            Decision(
                priority="MONITOR",
                action="MAINTAIN CURRENT STRATEGY",
                reason=(
                    "No major liquidity, margin or inventory "
                    "warning currently requires immediate action."
                ),
                score=70,
                confidence=70,
                risk="🟢 LOW",
            )
        )

    decisions.sort(
        key=lambda x: x.score,
        reverse=True,
    )

    return decisions


def overall_health(base):
    score = 100.0

    if base["margin"] < TARGET_MARGIN:
        score -= 20

    if base["supplier"] > base["liquid"]:
        score -= 20

    if base["credit"] > 0:
        score -= 10

    if base["inventory"] > base["revenue"]:
        score -= 10

    if base["sales_count"] < 20:
        score -= 10

    score = max(0, min(score, 100))

    if score >= 75:
        status = "🟢 HEALTHY"
    elif score >= 55:
        status = "🟡 WATCH"
    elif score >= 40:
        status = "🟠 AT RISK"
    else:
        status = "🔴 CRITICAL"

    return score, status


def print_report(base, decisions):

    health_score, health_status = overall_health(base)

    top = decisions[0]

    confidence = min(
        sum(d.confidence for d in decisions) /
        len(decisions),
        100,
    )

    if top.priority == "URGENT":
        overall_risk = "🟠 HIGH"
    elif top.priority == "HIGH":
        overall_risk = "🟡 MODERATE"
    else:
        overall_risk = top.risk

    print("=" * 60)
    print("POS LEDGER NG V69")
    print("EXECUTIVE MANAGEMENT DECISION INTELLIGENCE")
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
        f"Recorded Expenses    : "
        f"{money(base['expenses'])}"
    )

    print(
        f"Recorded Sales       : "
        f"{base['sales_count']}"
    )

    print("\n" + "=" * 60)
    print("EXECUTIVE HEALTH")
    print("=" * 60)

    print(
        f"Overall Health Score : "
        f"{health_score:.2f}/100"
    )

    print(
        f"Health Status        : "
        f"{health_status}"
    )

    print(
        f"Decision Confidence  : "
        f"{confidence:.2f}%"
    )

    print(
        f"Overall Risk         : "
        f"{overall_risk}"
    )

    print("\n" + "=" * 60)
    print("MANAGEMENT DECISION PRIORITIES")
    print("=" * 60)

    for i, decision in enumerate(decisions, 1):

        print("-" * 40)

        print(
            f"{i}. [{decision.priority}] "
            f"{decision.action}"
        )

        print(
            f"Reason       : "
            f"{decision.reason}"
        )

        print(
            f"Decision Score : "
            f"{decision.score:.2f}/100"
        )

        print(
            f"Confidence   : "
            f"{decision.confidence:.2f}%"
        )

        print(
            f"Risk         : "
            f"{decision.risk}"
        )

    print("\n" + "=" * 60)
    print("TOP MANAGEMENT DECISION")
    print("=" * 60)

    print(
        f"Priority            : "
        f"{top.priority}"
    )

    print(
        f"Decision            : "
        f"{top.action}"
    )

    print(
        f"Decision Score      : "
        f"{top.score:.2f}/100"
    )

    print(
        f"Confidence          : "
        f"{top.confidence:.2f}%"
    )

    print(
        f"Risk                : "
        f"{top.risk}"
    )

    print(
        f"Reason              : "
        f"{top.reason}"
    )

    print("\n" + "=" * 60)
    print("EXECUTIVE ACTION PLAN")
    print("=" * 60)

    action_number = 1

    if base["credit"] > 0:
        print(
            f"{action_number}. COLLECT CUSTOMER CREDIT"
        )
        print(
            f"   Recoverable liquidity: "
            f"{money(base['credit'])}"
        )
        action_number += 1

    if base["supplier"] > base["liquid"]:
        gap = base["supplier"] - base["liquid"]

        print(
            f"{action_number}. PROTECT LIQUIDITY"
        )
        print(
            f"   Supplier liquidity gap: "
            f"{money(gap)}"
        )
        action_number += 1

    if base["margin"] < TARGET_MARGIN:
        print(
            f"{action_number}. IMPROVE PRODUCT MARGINS"
        )
        print(
            f"   Current margin: "
            f"{base['margin'] * 100:.2f}%"
        )
        print(
            f"   Target margin : "
            f"{TARGET_MARGIN * 100:.2f}%"
        )
        action_number += 1

    if base["inventory"] > 0:
        print(
            f"{action_number}. CONTROL INVENTORY CAPITAL"
        )
        print(
            f"   Inventory capital: "
            f"{money(base['inventory'])}"
        )
        action_number += 1

    print(
        f"{action_number}. AVOID UNCONTROLLED EXPANSION"
    )
    print(
        "   Improve liquidity and margins before "
        "aggressive growth."
    )

    print("\n" + "=" * 60)
    print("EXECUTIVE INTERPRETATION")
    print("=" * 60)

    if base["supplier"] > base["liquid"]:
        print(
            "The business should prioritize liquidity protection "
            "before aggressive expansion."
        )

    if base["credit"] > 0:
        print(
            "Customer credit represents recoverable liquidity "
            "that can strengthen cash availability."
        )

    if base["margin"] < TARGET_MARGIN:
        print(
            "Profitability should be improved by reviewing "
            "product pricing and low-margin products."
        )

    if base["inventory"] > 0:
        print(
            "Inventory capital should be monitored for "
            "turnover efficiency and slow-moving stock."
        )

    print("\n" + "=" * 60)
    print("DECISION LIMITATIONS")
    print("=" * 60)

    print(
        "This system provides management intelligence, "
        "not guaranteed financial outcomes."
    )

    print(
        "Recommendations are based on recorded POS Ledger NG "
        "data and predefined decision rules."
    )

    print(
        "Market conditions, competition, seasonality and "
        "unexpected expenses are not fully modeled."
    )

    print("\n" + "=" * 60)
    print("V69 SAFETY STATUS")
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

            base = get_position(conn)

            decisions = calculate_decision(base)

            print_report(
                base,
                decisions,
            )

        finally:
            conn.close()

    except Exception as exc:

        print("=" * 60)
        print("V69 ERROR")
        print("=" * 60)

        print(str(exc))


if __name__ == "__main__":
    main()
