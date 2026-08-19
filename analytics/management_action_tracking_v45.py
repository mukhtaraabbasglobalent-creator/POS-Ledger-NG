"""
POS Ledger NG V45
Management Action Tracking & Progress Intelligence

READ-ONLY.
Does not modify sales, balances, inventory, customers, creditors, or expenses.
"""

from datetime import datetime

try:
    from database.connection import get_connection
except ModuleNotFoundError:
    from connection import get_connection


def management_action_tracking_v45():
    conn = get_connection()
    cur = conn.cursor()

    # ========================================================
    # SALES
    # ========================================================

    sales = cur.execute("""
        SELECT
            COUNT(*) AS sales_count,
            COALESCE(SUM(total_amount), 0) AS revenue,
            COALESCE(SUM(total_profit), 0) AS profit,
            MAX(sale_date) AS latest_sale_date
        FROM sales
        WHERE status != 'CANCELLED'
    """).fetchone()

    sales_count = int(sales["sales_count"] or 0)
    revenue = float(sales["revenue"] or 0)
    profit = float(sales["profit"] or 0)

    if revenue > 0:
        gross_margin = (profit / revenue) * 100
    else:
        gross_margin = 0.0

    # ========================================================
    # ACTIVE SALES DAYS
    # ========================================================

    active_days_row = cur.execute("""
        SELECT COUNT(DISTINCT DATE(sale_date)) AS active_days
        FROM sales
        WHERE status != 'CANCELLED'
    """).fetchone()

    active_days = int(active_days_row["active_days"] or 0)

    if active_days > 0:
        sales_per_day = sales_count / active_days
        revenue_per_day = revenue / active_days
    else:
        sales_per_day = 0.0
        revenue_per_day = 0.0

    # ========================================================
    # BALANCE
    # ========================================================

    balance = cur.execute("""
        SELECT
            cash_balance,
            wallet_balance,
            updated_at
        FROM balance
        ORDER BY id DESC
        LIMIT 1
    """).fetchone()

    if balance:
        cash_balance = float(balance["cash_balance"] or 0)
        wallet_balance = float(balance["wallet_balance"] or 0)
        balance_updated = balance["updated_at"]
    else:
        cash_balance = 0.0
        wallet_balance = 0.0
        balance_updated = None

    liquid_funds = cash_balance + wallet_balance

    # ========================================================
    # CUSTOMER CREDIT
    # ========================================================

    credit = cur.execute("""
        SELECT COALESCE(SUM(balance), 0) AS outstanding
        FROM customer_credit
        WHERE balance > 0
    """).fetchone()

    customer_credit = float(credit["outstanding"] or 0)

    # ========================================================
    # SUPPLIER LIABILITY
    # ========================================================

    supplier = cur.execute("""
        SELECT COALESCE(SUM(balance), 0) AS liability
        FROM creditors
        WHERE balance > 0
    """).fetchone()

    supplier_liability = float(supplier["liability"] or 0)

    supplier_liquidity_gap = supplier_liability - liquid_funds

    # ========================================================
    # INVENTORY
    # ========================================================

    inventory = cur.execute("""
        SELECT COALESCE(
            SUM(current_stock * buying_price),
            0
        ) AS inventory_capital
        FROM products
    """).fetchone()

    inventory_capital = float(
        inventory["inventory_capital"] or 0
    )

    if liquid_funds > 0:
        inventory_liquidity_ratio = (
            inventory_capital / liquid_funds
        )
    else:
        inventory_liquidity_ratio = 0.0

    # ========================================================
    # CUSTOMER INTELLIGENCE
    # ========================================================

    customers = cur.execute("""
        SELECT COUNT(*) AS total_customers
        FROM customers
    """).fetchone()

    registered_customers = int(
        customers["total_customers"] or 0
    )

    revenue_customers_row = cur.execute("""
        SELECT COUNT(DISTINCT customer_id) AS revenue_customers
        FROM sales
        WHERE status != 'CANCELLED'
        AND customer_id IS NOT NULL
    """).fetchone()

    revenue_customers = int(
        revenue_customers_row["revenue_customers"] or 0
    )

    # ========================================================
    # ACTION TARGETS
    # ========================================================

    target_margin = 10.0

    margin_gap = max(
        target_margin - gross_margin,
        0.0
    )

    liquidity_target_met = (
        supplier_liability < liquid_funds
    )

    inventory_exposure_high = (
        inventory_liquidity_ratio > 2.0
    )

    sales_activity_low = (
        sales_count < 30
    )

    customer_data_limited = (
        revenue_customers < 5
    )

    # ========================================================
    # ACTION STATUS
    # ========================================================

    profitability_met = gross_margin >= target_margin

    if profitability_met:
        profitability_status = "🟢 ACHIEVED"
    elif gross_margin >= 8:
        profitability_status = "🟡 IMPROVING"
    else:
        profitability_status = "🔴 NOT ACHIEVED"

    if liquidity_target_met:
        liquidity_status = "🟢 ACHIEVED"
    else:
        liquidity_status = "🔴 NOT ACHIEVED"

    if inventory_exposure_high:
        inventory_status = "🟠 HIGH EXPOSURE"
    else:
        inventory_status = "🟢 CONTROLLED"

    if sales_activity_low:
        sales_status = "🟠 LIMITED DATA"
    else:
        sales_status = "🟢 ADEQUATE DATA"

    if customer_data_limited:
        customer_status = "🟠 LIMITED DATA"
    else:
        customer_status = "🟢 DEVELOPING"

    # ========================================================
    # PROGRESS SCORE
    # ========================================================

    score = 0

    if profitability_met:
        score += 30
    elif gross_margin >= 8:
        score += 15

    if liquidity_target_met:
        score += 25

    if not inventory_exposure_high:
        score += 20

    if not sales_activity_low:
        score += 15

    if not customer_data_limited:
        score += 10

    if score >= 80:
        overall_status = "🟢 STRONG PROGRESS"
    elif score >= 50:
        overall_status = "🟡 MODERATE PROGRESS"
    else:
        overall_status = "🔴 ACTION REQUIRED"

    # ========================================================
    # OUTPUT
    # ========================================================

    print("\n========================================")
    print("       POS LEDGER NG V45")
    print(" MANAGEMENT ACTION TRACKING INTELLIGENCE")
    print("========================================")

    print("\nBUSINESS BASELINE")
    print("----------------------------------------")
    print(f"Revenue              : ₦{revenue:,.2f}")
    print(f"Gross Profit         : ₦{profit:,.2f}")
    print(f"Gross Margin         : {gross_margin:.2f}%")
    print(f"Completed Sales      : {sales_count}")
    print(f"Active Sales Days    : {active_days}")

    print("\n1. PROFITABILITY ACTION")
    print("----------------------------------------")
    print(f"Current Margin       : {gross_margin:.2f}%")
    print(f"Target Margin        : {target_margin:.2f}%")
    print(f"Margin Gap           : {margin_gap:.2f} percentage points")
    print(f"Status               : {profitability_status}")

    print("\n2. LIQUIDITY ACTION")
    print("----------------------------------------")
    print(f"Liquid Funds         : ₦{liquid_funds:,.2f}")
    print(f"Supplier Liability   : ₦{supplier_liability:,.2f}")
    print(f"Liquidity Gap        : ₦{supplier_liquidity_gap:,.2f}")
    print(f"Status               : {liquidity_status}")

    print("\n3. INVENTORY ACTION")
    print("----------------------------------------")
    print(f"Inventory Capital    : ₦{inventory_capital:,.2f}")
    print(f"Liquid Funds         : ₦{liquid_funds:,.2f}")
    print(
        f"Inventory/Liquid Ratio: "
        f"{inventory_liquidity_ratio:.2f}x"
    )
    print(f"Status               : {inventory_status}")

    print("\n4. SALES ACTIVITY ACTION")
    print("----------------------------------------")
    print(f"Completed Sales      : {sales_count}")
    print(f"Active Sales Days    : {active_days}")
    print(f"Sales / Active Day   : {sales_per_day:.2f}")
    print(f"Revenue / Active Day : ₦{revenue_per_day:,.2f}")
    print(f"Status               : {sales_status}")

    print("\n5. CUSTOMER DATA ACTION")
    print("----------------------------------------")
    print(f"Registered Customers : {registered_customers}")
    print(f"Revenue Customers    : {revenue_customers}")
    print(f"Status               : {customer_status}")

    print("\n========================================")
    print("       MANAGEMENT PROGRESS SCORE")
    print("========================================")
    print(f"Progress Score       : {score}/100")
    print(f"Overall Status       : {overall_status}")

    print("\nMANAGEMENT NEXT ACTIONS")
    print("----------------------------------------")

    if not profitability_met:
        print(
            "1. Improve product margins toward the "
            "10% management target."
        )

    if not liquidity_target_met:
        print(
            "2. Reduce supplier liability and protect "
            "minimum operating cash."
        )

    if inventory_exposure_high:
        print(
            "3. Control new stock purchases until sales "
            "demand supports additional inventory."
        )

    if sales_activity_low:
        print(
            "4. Continue collecting sales data before "
            "making strong long-term forecasts."
        )

    if customer_data_limited:
        print(
            "5. Increase customer registration and "
            "repeat-customer tracking."
        )

    print("\n========================================")
    print("       V45 MODULE STATUS")
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
    management_action_tracking_v45()
