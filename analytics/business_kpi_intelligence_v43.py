"""
POS LEDGER NG V43
BUSINESS KPI INTELLIGENCE

READ-ONLY BUSINESS INTELLIGENCE MODULE.

Does not modify:
- sales
- transactions
- balances
- inventory
- customers
- creditors
- expenses
"""

from database.connection import get_connection


def business_kpi_intelligence_v43():

    conn = get_connection()
    cur = conn.cursor()

    # ============================================================
    # SALES
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

    # ============================================================
    # GROSS MARGIN
    # ============================================================

    if revenue > 0:
        gross_margin = (profit / revenue) * 100
    else:
        gross_margin = 0.0

    # ============================================================
    # AVERAGE TRANSACTION VALUE
    # ============================================================

    if sales_count > 0:
        average_transaction = revenue / sales_count
    else:
        average_transaction = 0.0

    # ============================================================
    # SALES ACTIVITY
    # ============================================================

    active_sales_days = cur.execute("""
        SELECT COUNT(DISTINCT DATE(sale_date)) AS active_days
        FROM sales
        WHERE status != 'CANCELLED'
    """).fetchone()

    active_days = int(active_sales_days["active_days"] or 0)

    if active_days > 0:
        average_sales_per_active_day = sales_count / active_days
        average_revenue_per_active_day = revenue / active_days
    else:
        average_sales_per_active_day = 0.0
        average_revenue_per_active_day = 0.0

    # ============================================================
    # CUSTOMERS
    # ============================================================

    customer_count = cur.execute("""
        SELECT COUNT(*) AS total
        FROM customers
    """).fetchone()

    total_customers = int(customer_count["total"] or 0)

    active_customers = cur.execute("""
        SELECT COUNT(DISTINCT customer_id) AS total
        FROM sales
        WHERE status != 'CANCELLED'
        AND customer_id IS NOT NULL
    """).fetchone()

    revenue_customers = int(active_customers["total"] or 0)

    # ============================================================
    # CUSTOMER REPEAT RATE
    # ============================================================

    repeat_data = cur.execute("""
        SELECT COUNT(*) AS repeat_customers
        FROM (
            SELECT customer_id
            FROM sales
            WHERE status != 'CANCELLED'
            AND customer_id IS NOT NULL
            GROUP BY customer_id
            HAVING COUNT(*) > 1
        )
    """).fetchone()

    repeat_customers = int(repeat_data["repeat_customers"] or 0)

    if revenue_customers > 0:
        repeat_rate = (
            repeat_customers / revenue_customers
        ) * 100
    else:
        repeat_rate = 0.0

    # ============================================================
    # CUSTOMER REVENUE CONCENTRATION
    # ============================================================

    top_customer = cur.execute("""
        SELECT
            customer_id,
            COALESCE(SUM(total_amount), 0) AS revenue
        FROM sales
        WHERE status != 'CANCELLED'
        AND customer_id IS NOT NULL
        GROUP BY customer_id
        ORDER BY revenue DESC
        LIMIT 1
    """).fetchone()

    if top_customer and revenue > 0:
        top_customer_revenue = float(
            top_customer["revenue"] or 0
        )

        customer_concentration = (
            top_customer_revenue / revenue
        ) * 100
    else:
        top_customer_revenue = 0.0
        customer_concentration = 0.0

    # ============================================================
    # INVENTORY
    # ============================================================

    inventory = cur.execute("""
        SELECT
            COUNT(*) AS products,
            COALESCE(
                SUM(current_stock * buying_price),
                0
            ) AS inventory_value
        FROM products
    """).fetchone()

    total_products = int(inventory["products"] or 0)
    inventory_value = float(
        inventory["inventory_value"] or 0
    )

    # ============================================================
    # LIQUID FUNDS
    # ============================================================

    balance = cur.execute("""
        SELECT
            cash_balance,
            wallet_balance
        FROM balance
        ORDER BY id DESC
        LIMIT 1
    """).fetchone()

    if balance:
        cash_balance = float(
            balance["cash_balance"] or 0
        )

        wallet_balance = float(
            balance["wallet_balance"] or 0
        )
    else:
        cash_balance = 0.0
        wallet_balance = 0.0

    liquid_funds = cash_balance + wallet_balance

    # ============================================================
    # CUSTOMER CREDIT
    # ============================================================

    credit = cur.execute("""
        SELECT
            COALESCE(SUM(balance), 0) AS balance
        FROM customer_credit
        WHERE balance > 0
    """).fetchone()

    customer_credit = float(
        credit["balance"] or 0
    )

    # ============================================================
    # SUPPLIER LIABILITY
    # ============================================================

    supplier = cur.execute("""
        SELECT
            COALESCE(SUM(balance), 0) AS balance
        FROM creditors
        WHERE balance > 0
    """).fetchone()

    supplier_liability = float(
        supplier["balance"] or 0
    )

    # ============================================================
    # LIQUIDITY COVERAGE
    # ============================================================

    if supplier_liability > 0:
        liquidity_coverage = (
            liquid_funds / supplier_liability
        ) * 100
    else:
        liquidity_coverage = 100.0

    # ============================================================
    # KPI STATUS
    # ============================================================

    margin_status = (
        "CRITICAL"
        if gross_margin < 10
        else "WATCH"
        if gross_margin < 20
        else "HEALTHY"
    )

    activity_status = (
        "LOW"
        if sales_count < 20
        else "MODERATE"
        if sales_count < 50
        else "HEALTHY"
    )

    customer_status = (
        "HIGH RISK"
        if customer_concentration >= 70
        else "WATCH"
        if customer_concentration >= 50
        else "DIVERSIFIED"
    )

    liquidity_status = (
        "CRITICAL"
        if supplier_liability > liquid_funds
        else "HEALTHY"
    )

    # ============================================================
    # KPI SCORE
    # ============================================================

    score = 100

    if gross_margin < 10:
        score -= 30
    elif gross_margin < 20:
        score -= 15

    if sales_count < 20:
        score -= 15
    elif sales_count < 50:
        score -= 5

    if customer_concentration >= 70:
        score -= 20
    elif customer_concentration >= 50:
        score -= 10

    if supplier_liability > liquid_funds:
        score -= 20

    if inventory_value > liquid_funds:
        score -= 10

    score = max(0, score)

    if score < 40:
        overall_status = "🔴 AT RISK"
    elif score < 70:
        overall_status = "🟠 WATCH"
    else:
        overall_status = "🟢 HEALTHY"

    # ============================================================
    # OUTPUT
    # ============================================================

    print("\n========================================")
    print("       POS LEDGER NG V43")
    print("       BUSINESS KPI INTELLIGENCE")
    print("========================================")

    print("\nCORE BUSINESS KPIs")
    print("----------------------------------------")
    print(f"Revenue              : ₦{revenue:,.2f}")
    print(f"Gross Profit         : ₦{profit:,.2f}")
    print(f"Gross Margin         : {gross_margin:.2f}%")
    print(f"Completed Sales      : {sales_count}")
    print(f"Average Transaction  : ₦{average_transaction:,.2f}")

    print("\nSALES ACTIVITY KPIs")
    print("----------------------------------------")
    print(f"Active Sales Days    : {active_days}")
    print(
        f"Sales / Active Day   : "
        f"{average_sales_per_active_day:.2f}"
    )
    print(
        f"Revenue / Active Day : "
        f"₦{average_revenue_per_active_day:,.2f}"
    )
    print(f"Activity Status      : {activity_status}")

    print("\nCUSTOMER KPIs")
    print("----------------------------------------")
    print(f"Registered Customers : {total_customers}")
    print(f"Revenue Customers    : {revenue_customers}")
    print(f"Repeat Customers     : {repeat_customers}")
    print(f"Repeat Rate          : {repeat_rate:.2f}%")
    print(
        f"Customer Concentration: "
        f"{customer_concentration:.2f}%"
    )
    print(f"Customer Risk        : {customer_status}")

    print("\nINVENTORY KPIs")
    print("----------------------------------------")
    print(f"Products             : {total_products}")
    print(
        f"Inventory Capital    : "
        f"₦{inventory_value:,.2f}"
    )

    print("\nFINANCIAL KPIs")
    print("----------------------------------------")
    print(f"Liquid Funds         : ₦{liquid_funds:,.2f}")
    print(f"Customer Credit      : ₦{customer_credit:,.2f}")
    print(
        f"Supplier Liability   : "
        f"₦{supplier_liability:,.2f}"
    )
    print(
        f"Liquidity Coverage   : "
        f"{liquidity_coverage:.2f}%"
    )
    print(f"Margin Status        : {margin_status}")
    print(f"Liquidity Status     : {liquidity_status}")

    print("\nOVERALL KPI SCORE")
    print("----------------------------------------")
    print(f"KPI Score            : {score}/100")
    print(f"Business Status      : {overall_status}")

    print("\n========================================")
    print("       V43 MODULE STATUS")
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
    business_kpi_intelligence_v43()
