"""
POS LEDGER NG V44
MANAGEMENT DECISION & ACTION PLAN INTELLIGENCE

READ-ONLY.
Converts business KPIs into prioritized management decisions.
"""

from database.connection import get_connection


def management_decision_v44():

    conn = get_connection()
    cur = conn.cursor()

    # ============================================================
    # CORE BUSINESS DATA
    # ============================================================

    sales = cur.execute("""
        SELECT
            COUNT(*) AS sales_count,
            COALESCE(SUM(total_amount), 0) AS revenue,
            COALESCE(SUM(total_profit), 0) AS profit
        FROM sales
        WHERE status != 'CANCELLED'
    """).fetchone()

    sales_count = int(sales["sales_count"] or 0)
    revenue = float(sales["revenue"] or 0)
    profit = float(sales["profit"] or 0)

    gross_margin = (
        (profit / revenue) * 100
        if revenue > 0 else 0
    )

    # ============================================================
    # SALES ACTIVITY
    # ============================================================

    active_days_row = cur.execute("""
        SELECT COUNT(DISTINCT DATE(sale_date)) AS active_days
        FROM sales
        WHERE status != 'CANCELLED'
    """).fetchone()

    active_days = int(active_days_row["active_days"] or 0)

    sales_per_day = (
        sales_count / active_days
        if active_days > 0 else 0
    )

    # ============================================================
    # LIQUID FUNDS
    # ============================================================

    balance = cur.execute("""
        SELECT cash_balance, wallet_balance
        FROM balance
        ORDER BY id DESC
        LIMIT 1
    """).fetchone()

    if balance:
        cash = float(balance["cash_balance"] or 0)
        wallet = float(balance["wallet_balance"] or 0)
    else:
        cash = 0
        wallet = 0

    liquid_funds = cash + wallet

    # ============================================================
    # CUSTOMER CREDIT
    # ============================================================

    credit = cur.execute("""
        SELECT COALESCE(SUM(balance), 0) AS balance
        FROM customer_credit
        WHERE balance > 0
    """).fetchone()

    customer_credit = float(credit["balance"] or 0)

    # ============================================================
    # SUPPLIER LIABILITY
    # ============================================================

    supplier = cur.execute("""
        SELECT COALESCE(SUM(balance), 0) AS balance
        FROM creditors
        WHERE balance > 0
    """).fetchone()

    supplier_liability = float(supplier["balance"] or 0)

    liquidity_gap = max(
        supplier_liability - liquid_funds,
        0
    )

    # ============================================================
    # INVENTORY
    # ============================================================

    inventory = cur.execute("""
        SELECT COALESCE(
            SUM(current_stock * buying_price),
            0
        ) AS value
        FROM products
    """).fetchone()

    inventory_capital = float(
        inventory["value"] or 0
    )

    # ============================================================
    # CUSTOMER SAMPLE
    # ============================================================

    registered = cur.execute("""
        SELECT COUNT(*) AS total
        FROM customers
    """).fetchone()

    registered_customers = int(
        registered["total"] or 0
    )

    revenue_customers = cur.execute("""
        SELECT COUNT(DISTINCT customer_id) AS total
        FROM sales
        WHERE status != 'CANCELLED'
        AND customer_id IS NOT NULL
    """).fetchone()

    revenue_customer_count = int(
        revenue_customers["total"] or 0
    )

    # ============================================================
    # ACTION ENGINE
    # ============================================================

    actions = []

    # ------------------------------------------------------------
    # PROFITABILITY
    # ------------------------------------------------------------

    if gross_margin < 10:

        actions.append({
            "priority": "CRITICAL",
            "area": "PROFITABILITY",
            "action": (
                "Review selling prices and buying costs "
                "to improve gross margin."
            ),
            "reason": (
                f"Current gross margin is {gross_margin:.2f}%, "
                "below the 10% minimum management threshold."
            ),
            "target": "Reach at least 10% gross margin."
        })

    elif gross_margin < 20:

        actions.append({
            "priority": "HIGH",
            "area": "PROFITABILITY",
            "action": (
                "Improve product margins and negotiate "
                "better purchasing costs."
            ),
            "reason": (
                f"Gross margin is {gross_margin:.2f}%."
            ),
            "target": "Move toward 20% gross margin."
        })

    # ------------------------------------------------------------
    # LIQUIDITY
    # ------------------------------------------------------------

    if supplier_liability > liquid_funds:

        actions.append({
            "priority": "CRITICAL",
            "area": "LIQUIDITY",
            "action": (
                "Reduce supplier liability while protecting "
                "minimum operating cash."
            ),
            "reason": (
                f"Supplier liability exceeds liquid funds "
                f"by ₦{liquidity_gap:,.2f}."
            ),
            "target": (
                "Bring supplier liability below liquid funds."
            )
        })

    # ------------------------------------------------------------
    # INVENTORY
    # ------------------------------------------------------------

    if inventory_capital > liquid_funds:

        actions.append({
            "priority": "HIGH",
            "area": "INVENTORY",
            "action": (
                "Monitor stock purchases and avoid locking "
                "excessive capital in inventory."
            ),
            "reason": (
                f"₦{inventory_capital:,.2f} is tied up in "
                f"inventory versus ₦{liquid_funds:,.2f} "
                "in liquid funds."
            ),
            "target": (
                "Maintain inventory at a level supported "
                "by sales demand."
            )
        })

    # ------------------------------------------------------------
    # SALES ACTIVITY
    # ------------------------------------------------------------

    if sales_count < 20:

        actions.append({
            "priority": "MEDIUM",
            "area": "SALES ACTIVITY",
            "action": (
                "Increase sales activity and continue "
                "collecting transaction data."
            ),
            "reason": (
                f"Only {sales_count} completed sales are "
                "currently available."
            ),
            "target": (
                "Build a larger transaction history "
                "before relying heavily on forecasts."
            )
        })

    # ------------------------------------------------------------
    # CUSTOMER SAMPLE
    # ------------------------------------------------------------

    if revenue_customer_count < 5:

        actions.append({
            "priority": "MEDIUM",
            "area": "CUSTOMER DATA",
            "action": (
                "Register and retain more customers "
                "to strengthen customer intelligence."
            ),
            "reason": (
                f"Only {revenue_customer_count} customers "
                "currently generate recorded sales."
            ),
            "target": (
                "Build a broader customer dataset."
            )
        })

    # ------------------------------------------------------------
    # CREDIT EXPOSURE
    # ------------------------------------------------------------

    if customer_credit > liquid_funds:

        actions.append({
            "priority": "HIGH",
            "area": "CREDIT RISK",
            "action": (
                "Monitor customer credit and accelerate "
                "collection of outstanding balances."
            ),
            "reason": (
                "Customer credit exceeds available "
                "liquid funds."
            ),
            "target": (
                "Keep outstanding customer credit "
                "within manageable cash-flow limits."
            )
        })

    # ============================================================
    # PRIORITY ORDER
    # ============================================================

    priority_order = {
        "CRITICAL": 1,
        "HIGH": 2,
        "MEDIUM": 3,
        "LOW": 4
    }

    actions.sort(
        key=lambda item: priority_order[
            item["priority"]
        ]
    )

    # ============================================================
    # MANAGEMENT STATUS
    # ============================================================

    critical_count = sum(
        1 for action in actions
        if action["priority"] == "CRITICAL"
    )

    high_count = sum(
        1 for action in actions
        if action["priority"] == "HIGH"
    )

    if critical_count >= 2:
        management_status = "🔴 URGENT MANAGEMENT ATTENTION"

    elif critical_count == 1:
        management_status = "🟠 MANAGEMENT ATTENTION REQUIRED"

    elif high_count > 0:
        management_status = "🟡 MANAGEMENT MONITORING"

    else:
        management_status = "🟢 NORMAL MANAGEMENT"

    # ============================================================
    # OUTPUT
    # ============================================================

    print("\n========================================")
    print("       POS LEDGER NG V44")
    print(" MANAGEMENT DECISION & ACTION PLAN")
    print("========================================")

    print("\nCURRENT BUSINESS POSITION")
    print("----------------------------------------")
    print(f"Revenue              : ₦{revenue:,.2f}")
    print(f"Gross Profit         : ₦{profit:,.2f}")
    print(f"Gross Margin         : {gross_margin:.2f}%")
    print(f"Completed Sales      : {sales_count}")
    print(f"Sales / Active Day   : {sales_per_day:.2f}")
    print(f"Liquid Funds         : ₦{liquid_funds:,.2f}")
    print(f"Customer Credit      : ₦{customer_credit:,.2f}")
    print(
        f"Supplier Liability   : "
        f"₦{supplier_liability:,.2f}"
    )
    print(
        f"Inventory Capital    : "
        f"₦{inventory_capital:,.2f}"
    )

    print("\nMANAGEMENT STATUS")
    print("----------------------------------------")
    print(
        f"Status               : "
        f"{management_status}"
    )
    print(
        f"Critical Actions     : "
        f"{critical_count}"
    )
    print(
        f"High Priority        : "
        f"{high_count}"
    )

    print("\nPRIORITIZED MANAGEMENT ACTIONS")
    print("----------------------------------------")

    if actions:

        for index, action in enumerate(
            actions,
            start=1
        ):

            print(
                f"\n{index}. "
                f"[{action['priority']}] "
                f"{action['area']}"
            )

            print(
                f"Action : {action['action']}"
            )

            print(
                f"Reason : {action['reason']}"
            )

            print(
                f"Target : {action['target']}"
            )

    else:

        print(
            "No immediate management actions "
            "were triggered."
        )

    print("\n========================================")
    print("       V44 MODULE STATUS")
    print("========================================")
    print("Mode                : READ-ONLY")
    print("Database modified   : NO")
    print("Sales modified      : NO")
    print("Balance modified    : NO")
    print("Credit modified     : NO")
    print("Inventory modified  : NO")
    print("========================================")

    conn.close()


if __name__ == "__main__":
    management_decision_v44()
