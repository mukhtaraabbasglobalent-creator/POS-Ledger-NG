"""
POS Ledger NG
V42 Management Action Intelligence

READ-ONLY

Converts V39/V40/V41 business findings into
prioritized management actions.
"""

from database.connection import get_connection


def management_action_intelligence_v42():
    conn = get_connection()

    try:
        cur = conn.cursor()

        # ====================================================
        # SALES
        # ====================================================

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
            if revenue > 0
            else 0
        )

        # ====================================================
        # BALANCE
        # ====================================================

        balance = cur.execute("""
            SELECT
                cash_balance,
                wallet_balance
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

        # ====================================================
        # CUSTOMER CREDIT
        # ====================================================

        credit = cur.execute("""
            SELECT
                COALESCE(SUM(balance), 0) AS amount
            FROM customer_credit
            WHERE balance > 0
        """).fetchone()

        customer_credit = float(
            credit["amount"] or 0
        )

        # ====================================================
        # SUPPLIER LIABILITY
        # ====================================================

        supplier = cur.execute("""
            SELECT
                COALESCE(SUM(balance), 0) AS amount
            FROM creditors
            WHERE balance > 0
        """).fetchone()

        supplier_liability = float(
            supplier["amount"] or 0
        )

        # ====================================================
        # INVENTORY
        # ====================================================

        inventory = cur.execute("""
            SELECT
                COALESCE(
                    SUM(
                        current_stock * buying_price
                    ),
                    0
                ) AS capital
            FROM products
        """).fetchone()

        inventory_capital = float(
            inventory["capital"] or 0
        )

        # ====================================================
        # ACTION ENGINE
        # ====================================================

        actions = []

        # Margin
        if gross_margin < 10:
            actions.append({
                "priority": 1,
                "severity": "CRITICAL",
                "area": "PROFITABILITY",
                "action": (
                    "Review selling prices and "
                    "buying costs to improve "
                    "gross profit margin."
                ),
                "reason": (
                    f"Gross margin is only "
                    f"{gross_margin:.2f}%."
                )
            })

        # Supplier liability
        if supplier_liability > liquid_funds:
            gap = supplier_liability - liquid_funds

            actions.append({
                "priority": 2,
                "severity": "HIGH",
                "area": "LIQUIDITY",
                "action": (
                    "Reduce supplier liability "
                    "and protect available cash."
                ),
                "reason": (
                    f"Supplier liability exceeds "
                    f"liquid funds by ₦{gap:,.2f}."
                )
            })

        # Customer credit
        if customer_credit > liquid_funds:
            actions.append({
                "priority": 3,
                "severity": "HIGH",
                "area": "CREDIT",
                "action": (
                    "Prioritize collection of "
                    "outstanding customer credit."
                ),
                "reason": (
                    "Customer credit exceeds "
                    "available liquid funds."
                )
            })

        # Inventory
        if inventory_capital > liquid_funds:
            actions.append({
                "priority": 4,
                "severity": "MEDIUM",
                "area": "INVENTORY",
                "action": (
                    "Monitor inventory capital and "
                    "avoid excessive capital being "
                    "locked in stock."
                ),
                "reason": (
                    "Inventory capital is greater "
                    "than available liquid funds."
                )
            })

        # Sales activity
        if sales_count < 30:
            actions.append({
                "priority": 5,
                "severity": "MEDIUM",
                "area": "SALES ACTIVITY",
                "action": (
                    "Continue collecting sales data "
                    "and increase sales activity."
                ),
                "reason": (
                    f"Only {sales_count} completed "
                    "sales are currently available "
                    "for analysis."
                )
            })

        # ====================================================
        # OUTPUT
        # ====================================================

        print()
        print("========================================")
        print("       POS LEDGER NG V42")
        print(" MANAGEMENT ACTION INTELLIGENCE")
        print("========================================")

        print()
        print("CURRENT BUSINESS POSITION")
        print("----------------------------------------")

        print(
            f"Revenue              : ₦{revenue:,.2f}"
        )

        print(
            f"Gross Profit         : ₦{profit:,.2f}"
        )

        print(
            f"Gross Margin         : "
            f"{gross_margin:.2f}%"
        )

        print(
            f"Liquid Funds         : "
            f"₦{liquid_funds:,.2f}"
        )

        print(
            f"Customer Credit      : "
            f"₦{customer_credit:,.2f}"
        )

        print(
            f"Supplier Liability   : "
            f"₦{supplier_liability:,.2f}"
        )

        print(
            f"Inventory Capital    : "
            f"₦{inventory_capital:,.2f}"
        )

        print()
        print("PRIORITIZED MANAGEMENT ACTIONS")
        print("----------------------------------------")

    if actions:
        for index, item in enumerate(actions, start=1):
            print()

            print(
                f"{index}. "
                f"[{item['severity']}] "
                f"{item['area']}"
            )

            print(
                f"Action : {item['action']}"
            )

            print(
                f"Reason : {item['reason']}"
            )

    else:
        print()
        print("No immediate management actions identified.")

    print()
    print("========================================")
    print("       V42 MODULE STATUS")
    print("========================================")
    print("Mode                : READ-ONLY")
    print("Database modified   : NO")
    print("Sales modified      : NO")
    print("Credit modified     : NO")
    print("Inventory modified  : NO")
    print("========================================")

    finally:
        conn.close()


if __name__ == "__main__":
    management_action_intelligence_v42()
