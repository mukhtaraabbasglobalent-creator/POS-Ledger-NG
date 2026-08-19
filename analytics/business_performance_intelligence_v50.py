"""
POS Ledger NG V50
BUSINESS PERFORMANCE INTELLIGENCE

READ-ONLY executive intelligence layer.

Combines:
- Sales
- Products
- Inventory
- Customer credit
- Supplier liability
- Liquid funds

Does NOT modify the database.
"""

from database.connection import get_connection


TARGET_MARGIN = 10.0


def business_performance_intelligence_v50():

    print("\n========================================")
    print("       POS LEDGER NG V50")
    print(" BUSINESS PERFORMANCE INTELLIGENCE")
    print("========================================")

    conn = get_connection()

    try:
        cur = conn.cursor()

        # ============================================================
        # SALES PERFORMANCE
        # ============================================================

        sales = cur.execute("""
            SELECT
                COUNT(*) AS completed_sales,
                COALESCE(SUM(quantity), 0),
                COALESCE(SUM(total_amount), 0),
                COALESCE(SUM(total_profit), 0),
                COUNT(DISTINCT substr(sale_date, 1, 10))
            FROM sales
            WHERE status = 'COMPLETED'
        """).fetchone()

        completed_sales = int(sales[0] or 0)
        units_sold = float(sales[1] or 0)
        revenue = float(sales[2] or 0)
        gross_profit = float(sales[3] or 0)
        active_days = int(sales[4] or 0)

        gross_margin = (
            gross_profit / revenue * 100
            if revenue > 0 else 0
        )

        average_transaction = (
            revenue / completed_sales
            if completed_sales > 0 else 0
        )

        revenue_per_day = (
            revenue / active_days
            if active_days > 0 else 0
        )

        profit_per_day = (
            gross_profit / active_days
            if active_days > 0 else 0
        )

        # ============================================================
        # LIQUID FUNDS
        # ============================================================

        cash_balance = 0.0
        wallet_balance = 0.0
        opening_balance = 0.0

        try:
            balance = cur.execute("""
                SELECT
                    COALESCE(opening_balance, 0),
                    COALESCE(cash_balance, 0),
                    COALESCE(wallet_balance, 0)
                FROM balances
                ORDER BY id DESC
                LIMIT 1
            """).fetchone()

            if balance:
                opening_balance = float(balance[0] or 0)
                cash_balance = float(balance[1] or 0)
                wallet_balance = float(balance[2] or 0)

        except Exception:
            # Some database versions may use a different balance schema.
            pass

        liquid_funds = cash_balance + wallet_balance

        # ============================================================
        # INVENTORY
        # ============================================================

        inventory = cur.execute("""
            SELECT
                COALESCE(SUM(buying_price * current_stock), 0),
                COUNT(*)
            FROM products
        """).fetchone()

        inventory_capital = float(inventory[0] or 0)
        products_analyzed = int(inventory[1] or 0)

        # ============================================================
        # CUSTOMER CREDIT
        # ============================================================

        customer_credit = 0.0

        for table_name in ("customer_credit", "customer_credits", "credits"):

            try:
                row = cur.execute(
                    f"""
                    SELECT COALESCE(SUM(amount), 0)
                    FROM {table_name}
                    WHERE status NOT IN ('PAID', 'CLOSED')
                    """
                ).fetchone()

                if row:
                    customer_credit = float(row[0] or 0)
                    break

            except Exception:
                continue

        # ============================================================
        # SUPPLIER LIABILITY
        # ============================================================

        supplier_liability = 0.0

        for table_name in (
            "supplier_credit",
            "supplier_credits",
            "creditors"
        ):

            try:
                row = cur.execute(
                    f"""
                    SELECT COALESCE(SUM(amount), 0)
                    FROM {table_name}
                    WHERE status NOT IN ('PAID', 'CLOSED')
                    """
                ).fetchone()

                if row:
                    supplier_liability = float(row[0] or 0)
                    break

            except Exception:
                continue

        # ============================================================
        # FINANCIAL POSITION
        # ============================================================

        total_assets = (
            liquid_funds
            + customer_credit
            + inventory_capital
        )

        net_position = total_assets - supplier_liability

        liquidity_gap = supplier_liability - liquid_funds

        inventory_liquid_ratio = (
            inventory_capital / liquid_funds
            if liquid_funds > 0 else 0
        )

        # ============================================================
        # PRODUCT INTELLIGENCE
        # ============================================================

        product_rows = cur.execute("""
            SELECT
                p.product_name,
                p.sku,
                p.buying_price,
                p.selling_price,
                p.current_stock,
                COALESCE(SUM(s.quantity), 0),
                COALESCE(SUM(s.total_amount), 0),
                COALESCE(SUM(s.total_profit), 0)
            FROM products p
            LEFT JOIN sales s
                ON p.id = s.product_id
                AND s.status = 'COMPLETED'
            GROUP BY
                p.id,
                p.product_name,
                p.sku,
                p.buying_price,
                p.selling_price,
                p.current_stock
            ORDER BY COALESCE(SUM(s.total_amount), 0) DESC
        """).fetchall()

        product_decisions = []

        for row in product_rows:

            name = row[0]
            sku = row[1]
            buying_price = float(row[2] or 0)
            selling_price = float(row[3] or 0)
            stock = float(row[4] or 0)
            units = float(row[5] or 0)
            product_revenue = float(row[6] or 0)
            product_profit = float(row[7] or 0)

            margin = (
                product_profit / product_revenue * 100
                if product_revenue > 0 else 0
            )

            units_per_day = (
                units / active_days
                if active_days > 0 else 0
            )

            if margin >= TARGET_MARGIN and units_per_day >= 2:
                decision = "STRONG PRODUCT"

            elif margin < TARGET_MARGIN and units_per_day >= 2:
                decision = "PRICING OPPORTUNITY"

            elif units_per_day < 1 and stock > 0:
                decision = "SLOW MOVEMENT"

            else:
                decision = "MONITOR"

            product_decisions.append({
                "name": name,
                "sku": sku,
                "buying": buying_price,
                "selling": selling_price,
                "stock": stock,
                "units": units,
                "revenue": product_revenue,
                "profit": product_profit,
                "margin": margin,
                "units_per_day": units_per_day,
                "decision": decision,
            })

        # ============================================================
        # EXECUTIVE RISK
        # ============================================================

        critical_actions = []
        high_actions = []
        medium_actions = []

        if gross_margin < TARGET_MARGIN:
            critical_actions.append(
                "Improve product margins toward the 10% target."
            )

        if supplier_liability > liquid_funds:
            critical_actions.append(
                "Reduce supplier liability and protect operating cash."
            )

        if inventory_liquid_ratio > 2:
            high_actions.append(
                "Control inventory purchases because stock capital "
                "is more than twice available liquid funds."
            )

        if active_days < 10:
            medium_actions.append(
                "Continue collecting sales data before relying heavily "
                "on long-term forecasts."
            )

        if completed_sales < 30:
            medium_actions.append(
                "Increase transaction volume to strengthen business analytics."
            )

        if len(product_rows) < 5:
            medium_actions.append(
                "Expand product and customer data to improve intelligence."
            )

        # ============================================================
        # OVERALL STATUS
        # ============================================================

        if len(critical_actions) >= 2:
            overall_status = "🔴 AT RISK"

        elif len(critical_actions) == 1:
            overall_status = "🟠 MANAGEMENT ATTENTION"

        elif len(high_actions) > 0:
            overall_status = "🟡 MONITOR"

        else:
            overall_status = "🟢 HEALTHY"

        # ============================================================
        # OUTPUT
        # ============================================================

        print("\n========================================")
        print("       EXECUTIVE BUSINESS POSITION")
        print("========================================")

        print("Revenue              :", f"₦{revenue:,.2f}")
        print("Gross Profit         :", f"₦{gross_profit:,.2f}")
        print("Gross Margin         :", f"{gross_margin:.2f}%")
        print("Completed Sales      :", completed_sales)
        print("Units Sold           :", f"{units_sold:g}")
        print("Average Transaction  :", f"₦{average_transaction:,.2f}")
        print("Active Sales Days    :", active_days)
        print("Revenue / Active Day :", f"₦{revenue_per_day:,.2f}")
        print("Profit / Active Day  :", f"₦{profit_per_day:,.2f}")

        print("\n========================================")
        print("       FINANCIAL POSITION")
        print("========================================")

        print("Opening Balance      :", f"₦{opening_balance:,.2f}")
        print("Cash Balance         :", f"₦{cash_balance:,.2f}")
        print("Wallet Balance       :", f"₦{wallet_balance:,.2f}")
        print("Liquid Funds         :", f"₦{liquid_funds:,.2f}")
        print("Customer Credit      :", f"₦{customer_credit:,.2f}")
        print("Supplier Liability   :", f"₦{supplier_liability:,.2f}")
        print("Inventory Capital    :", f"₦{inventory_capital:,.2f}")
        print("Total Assets         :", f"₦{total_assets:,.2f}")
        print("Net Position         :", f"₦{net_position:,.2f}")

        print("\n========================================")
        print("       PRODUCT INTELLIGENCE")
        print("========================================")

        for product in product_decisions:

            print("\n----------------------------------------")
            print("Product              :", product["name"])
            print("SKU                  :", product["sku"])
            print("Units Sold           :", f"{product['units']:g}")
            print("Revenue              :", f"₦{product['revenue']:,.2f}")
            print("Profit               :", f"₦{product['profit']:,.2f}")
            print("Gross Margin         :", f"{product['margin']:.2f}%")
            print("Units / Active Day   :", f"{product['units_per_day']:.2f}")
            print("Current Stock        :", f"{product['stock']:g}")
            print("Decision             :", product["decision"])

        print("\n========================================")
        print("       EXECUTIVE RISK")
        print("========================================")

        print("Liquidity Gap        :", f"₦{max(liquidity_gap, 0):,.2f}")
        print(
            "Inventory/Liquid Ratio:",
            f"{inventory_liquid_ratio:.2f}x"
        )
        print("Overall Status       :", overall_status)

        print("\n========================================")
        print("       PRIORITIZED ACTIONS")
        print("========================================")

        action_number = 1

        for action in critical_actions:
            print(
                f"{action_number}. [CRITICAL] {action}"
            )
            action_number += 1

        for action in high_actions:
            print(
                f"{action_number}. [HIGH] {action}"
            )
            action_number += 1

        for action in medium_actions:
            print(
                f"{action_number}. [MEDIUM] {action}"
            )
            action_number += 1

        if action_number == 1:
            print("No immediate management actions detected.")

        print("\n========================================")
        print("       V50 MODULE STATUS")
        print("========================================")
        print("Mode                : READ-ONLY")
        print("Database modified   : NO")
        print("Sales modified      : NO")
        print("Products modified   : NO")
        print("Inventory modified  : NO")
        print("Balance modified    : NO")
        print("Credit modified     : NO")
        print("========================================")

    finally:
        conn.close()


if __name__ == "__main__":
    business_performance_intelligence_v50()
