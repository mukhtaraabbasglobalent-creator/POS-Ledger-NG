"""
POS Ledger NG V42
Management Action Intelligence

READ-ONLY management decision module.
Does not modify the database.
"""

from database.connection import get_connection


def management_action_intelligence_v42():
    conn = get_connection()

    try:
        cur = conn.cursor()

        # ----------------------------------------------------
        # CURRENT BUSINESS POSITION
        # ----------------------------------------------------

        sales = cur.execute("""
            SELECT
                COALESCE(SUM(total_amount), 0) AS revenue,
                COALESCE(SUM(total_profit), 0) AS profit,
                COUNT(*) AS sales_count
            FROM sales
            WHERE status != 'CANCELLED'
        """).fetchone()

        revenue = float(sales["revenue"] or 0)
        gross_profit = float(sales["profit"] or 0)
        sales_count = int(sales["sales_count"] or 0)

        if revenue > 0:
            gross_margin = (gross_profit / revenue) * 100
        else:
            gross_margin = 0.0

        # ----------------------------------------------------
        # LIQUID FUNDS
        # ----------------------------------------------------

        balance = cur.execute("""
            SELECT
                cash_balance,
                wallet_balance
            FROM balance
            ORDER BY id DESC
            LIMIT 1
        """).fetchone()

        if balance:
            cash_balance = float(balance["cash_balance"] or 0)
            wallet_balance = float(balance["wallet_balance"] or 0)
        else:
            cash_balance = 0.0
            wallet_balance = 0.0

        liquid_funds = cash_balance + wallet_balance

        # ----------------------------------------------------
        # CUSTOMER CREDIT
        # ----------------------------------------------------

        credit = cur.execute("""
            SELECT
                COALESCE(SUM(balance), 0) AS outstanding
            FROM customer_credit
            WHERE balance > 0
        """).fetchone()

        customer_credit = float(
            credit["outstanding"] or 0
        )

        # ----------------------------------------------------
        # SUPPLIER LIABILITY
        # ----------------------------------------------------

        supplier = cur.execute("""
            SELECT
                COALESCE(SUM(balance), 0) AS liability
            FROM creditors
            WHERE balance > 0
        """).fetchone()

        supplier_liability = float(
            supplier["liability"] or 0
        )

        # ----------------------------------------------------
        # INVENTORY CAPITAL
        # ----------------------------------------------------

        inventory = cur.execute("""
            SELECT
                COALESCE(
                    SUM(current_stock * buying_price),
                    0
                ) AS inventory_capital
            FROM products
        """).fetchone()

        inventory_capital = float(
            inventory["inventory_capital"] or 0
        )

        # ----------------------------------------------------
        # MANAGEMENT ACTIONS
        # ----------------------------------------------------

        actions = []

        # Profitability
        if gross_margin < 10:
            actions.append({
                "severity": "CRITICAL",
                "area": "PROFITABILITY",
                "action": (
                    "Review selling prices and buying costs "
                    "to improve gross profit margin."
                ),
                "reason": (
                    f"Gross margin is only "
                    f"{gross_margin:.2f}%."
                )
            })

        # Liquidity
        supplier_gap = supplier_liability - liquid_funds

        if supplier_gap > 0:
            actions.append({
                "severity": "HIGH",
                "area": "LIQUIDITY",
                "action": (
                    "Reduce supplier liability and protect "
                    "available cash."
                ),
                "reason": (
                    "Supplier liability exceeds liquid "
                    f"funds by ₦{supplier_gap:,.2f}."
                )
            })

        # Inventory
        if inventory_capital > liquid_funds:
            actions.append({
                "severity": "MEDIUM",
                "area": "INVENTORY",
                "action": (
                    "Monitor inventory capital and avoid "
                    "excessive capital being locked in stock."
                ),
                "reason": (
                    "Inventory capital is greater than "
                    "available liquid funds."
                )
            })

        # Sales activity
        if sales_count < 30:
            actions.append({
                "severity": "MEDIUM",
                "area": "SALES ACTIVITY",
                "action": (
                    "Continue collecting sales data and "
                    "increase sales activity."
                ),
                "reason": (
                    f"Only {sales_count} completed sales "
                    "are currently available for analysis."
                )
            })

        # ----------------------------------------------------
        # OUTPUT
        # ----------------------------------------------------

        print()
        print("========================================")
        print("       POS LEDGER NG V42")
        print(" MANAGEMENT ACTION INTELLIGENCE")
        print("========================================")

        print()
        print("CURRENT BUSINESS POSITION")
        print("----------------------------------------")
        print(f"Revenue              : ₦{revenue:,.2f}")
        print(f"Gross Profit         : ₦{gross_profit:,.2f}")
        print(f"Gross Margin         : {gross_margin:.2f}%")
        print(f"Liquid Funds         : ₦{liquid_funds:,.2f}")
        print(f"Customer Credit      : ₦{customer_credit:,.2f}")
        print(f"Supplier Liability   : ₦{supplier_liability:,.2f}")
        print(f"Inventory Capital    : ₦{inventory_capital:,.2f}")

        print()
        print("PRIORITIZED MANAGEMENT ACTIONS")
        print("----------------------------------------")

        if actions:
            for index, item in enumerate(actions, start=1):
                print()
                print(
                    f"{index}. [{item['severity']}] "
                    f"{item['area']}"
                )
                print(f"Action : {item['action']}")
                print(f"Reason : {item['reason']}")
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
