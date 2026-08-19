import sqlite3
from datetime import datetime, timedelta

DB_PATH = "data/posledger.db"


def money(value):
    return f"₦{value:,.2f}"


def executive_business_intelligence():
    print("\n========================================")
    print("       POS LEDGER NG V37")
    print("  EXECUTIVE BUSINESS INTELLIGENCE")
    print("========================================")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # ========================================
    # SALES INTELLIGENCE
    # ========================================

    total_sales = 0
    total_revenue = 0.0
    total_profit = 0.0
    today_sales = 0
    today_revenue = 0.0
    sales_30 = 0
    revenue_30 = 0.0

    try:
        cur.execute("""
            SELECT
                COUNT(*) AS count,
                COALESCE(SUM(total_amount), 0) AS revenue,
                COALESCE(SUM(total_profit), 0) AS profit
            FROM sales
            WHERE status IS NULL
               OR status != 'CANCELLED'
        """)

        row = cur.fetchone()

        if row:
            total_sales = row["count"] or 0
            total_revenue = row["revenue"] or 0.0
            total_profit = row["profit"] or 0.0

        today = datetime.now().strftime("%Y-%m-%d")

        cur.execute("""
            SELECT
                COUNT(*) AS count,
                COALESCE(SUM(total_amount), 0) AS revenue
            FROM sales
            WHERE DATE(sale_date) = ?
              AND (
                    status IS NULL
                    OR status != 'CANCELLED'
              )
        """, (today,))

        row = cur.fetchone()

        if row:
            today_sales = row["count"] or 0
            today_revenue = row["revenue"] or 0.0

        since_30 = (
            datetime.now() - timedelta(days=30)
        ).strftime("%Y-%m-%d")

        cur.execute("""
            SELECT
                COUNT(*) AS count,
                COALESCE(SUM(total_amount), 0) AS revenue
            FROM sales
            WHERE DATE(sale_date) >= ?
              AND (
                    status IS NULL
                    OR status != 'CANCELLED'
              )
        """, (since_30,))

        row = cur.fetchone()

        if row:
            sales_30 = row["count"] or 0
            revenue_30 = row["revenue"] or 0.0

    except sqlite3.Error as e:
        print(f"\nSales intelligence warning: {e}")

    # ========================================
    # PROFIT INTELLIGENCE
    # ========================================

    gross_profit = total_profit
    gross_margin = 0.0

    if total_revenue > 0:
        gross_margin = (
            gross_profit / total_revenue
        ) * 100

    # ========================================
    # INVENTORY INTELLIGENCE
    # ========================================

    products_count = 0
    stock_units = 0.0
    inventory_cost = 0.0
    retail_value = 0.0
    low_stock = 0
    out_of_stock = 0

    try:
        cur.execute("""
            SELECT
                COUNT(*) AS products,
                COALESCE(SUM(current_stock), 0)
                    AS units,
                COALESCE(
                    SUM(
                        current_stock * buying_price
                    ),
                    0
                ) AS cost,
                COALESCE(
                    SUM(
                        current_stock * selling_price
                    ),
                    0
                ) AS retail
            FROM products
        """)

        row = cur.fetchone()

        if row:
            products_count = row["products"] or 0
            stock_units = row["units"] or 0.0
            inventory_cost = row["cost"] or 0.0
            retail_value = row["retail"] or 0.0

        cur.execute("""
            SELECT COUNT(*)
            FROM products
            WHERE current_stock <= min_stock
              AND current_stock > 0
        """)

        low_stock = cur.fetchone()[0] or 0

        cur.execute("""
            SELECT COUNT(*)
            FROM products
            WHERE current_stock <= 0
        """)

        out_of_stock = cur.fetchone()[0] or 0

    except sqlite3.Error as e:
        print(f"\nInventory intelligence warning: {e}")

    # ========================================
    # CREDIT INTELLIGENCE
    # ========================================
    #
    # V37 does NOT invent a credits table.
    # Credit intelligence will be integrated
    # from the existing V30 credit module later.
    #

    outstanding = None
    credit_status = "🟡 CREDIT DATA NOT INTEGRATED"

    # ========================================
    # INVENTORY HEALTH
    # ========================================

    if out_of_stock > 0:
        inventory_health = "🔴 CRITICAL INVENTORY"

    elif low_stock > 0:
        inventory_health = "🟡 ATTENTION REQUIRED"

    else:
        inventory_health = "🟢 HEALTHY INVENTORY"

    # ========================================
    # SALES HEALTH
    # ========================================

    if revenue_30 <= 0:
        sales_health = "🔴 NO RECORDED SALES"

    elif today_sales > 0:
        sales_health = "🟢 ACTIVE SALES"

    else:
        sales_health = "🟡 SALES NEED MONITORING"

    # ========================================
    # PROFIT HEALTH
    # ========================================

    if gross_profit < 0:
        profit_health = "🔴 LOSS"

    elif gross_margin < 10:
        profit_health = "🟠 WEAK PROFITABILITY"

    elif gross_margin < 20:
        profit_health = "🟡 MODERATE PROFITABILITY"

    else:
        profit_health = "🟢 HEALTHY PROFITABILITY"

    # ========================================
    # BUSINESS HEALTH SCORE
    # ========================================

    score = 0

    if revenue_30 > 0:
        score += 25

    if gross_profit > 0:
        score += 25

    if inventory_health == "🟢 HEALTHY INVENTORY":
        score += 20

    elif inventory_health == "🟡 ATTENTION REQUIRED":
        score += 10

    # Credit is not scored until V30
    # is properly integrated.
    score += 15

    if today_sales > 0:
        score += 15

    if score >= 80:
        business_health = "🟢 STRONG BUSINESS HEALTH"

    elif score >= 60:
        business_health = "🟡 STABLE BUSINESS"

    elif score >= 40:
        business_health = "🟠 NEEDS ATTENTION"

    else:
        business_health = "🔴 HIGH ATTENTION REQUIRED"

    # ========================================
    # MANAGEMENT DECISION
    # ========================================

    if gross_profit < 0:
        recommendation = (
            "URGENTLY REVIEW PRICING, COSTS "
            "AND LOSS-MAKING PRODUCTS"
        )

    elif out_of_stock > 0:
        recommendation = (
            "PRIORITIZE REPLENISHMENT "
            "OF OUT-OF-STOCK PRODUCTS"
        )

    elif low_stock > 0:
        recommendation = (
            "MONITOR LOW-STOCK PRODUCTS "
            "AND PLAN REPLENISHMENT"
        )

    elif gross_margin < 10:
        recommendation = (
            "REVIEW LOW-MARGIN PRODUCTS "
            "AND IMPROVE PRICING"
        )

    else:
        recommendation = (
            "MAINTAIN BUSINESS MOMENTUM "
            "AND CONTINUE MONITORING PERFORMANCE"
        )

    # ========================================
    # DATA CONFIDENCE
    # ========================================

    confidence_points = 0

    if total_sales >= 20:
        confidence_points += 2

    elif total_sales > 0:
        confidence_points += 1

    if products_count >= 5:
        confidence_points += 2

    elif products_count > 0:
        confidence_points += 1

    if confidence_points >= 4:
        confidence = "🟢 HIGH"

    elif confidence_points >= 2:
        confidence = "🟡 MODERATE"

    elif confidence_points > 0:
        confidence = "🟠 LIMITED"

    else:
        confidence = "🔴 VERY LIMITED"

    # ========================================
    # OUTPUT
    # ========================================

    print("\n========================================")
    print("       BUSINESS POSITION")
    print("========================================")
    print(f"Total Sales       : {total_sales}")
    print(f"30-Day Revenue    : {money(revenue_30)}")
    print(f"Gross Profit      : {money(gross_profit)}")
    print(f"Gross Margin      : {gross_margin:.2f}%")
    print(f"Inventory Units   : {stock_units:.2f}")
    print(f"Inventory Cost    : {money(inventory_cost)}")
    print(f"Inventory Value   : {money(retail_value)}")

    if outstanding is None:
        print(
            "Credit Outstanding: NOT INTEGRATED"
        )
    else:
        print(
            f"Credit Outstanding: {money(outstanding)}"
        )

    print("\n========================================")
    print("       BUSINESS INTELLIGENCE")
    print("========================================")
    print(f"Sales Health      : {sales_health}")
    print(f"Profit Health     : {profit_health}")
    print(f"Inventory Health  : {inventory_health}")
    print(f"Credit Health     : {credit_status}")

    print("\n========================================")
    print("       BUSINESS HEALTH")
    print("========================================")
    print(f"Health Score      : {score}/100")
    print(f"Business Status   : {business_health}")

    print("\n========================================")
    print("       MANAGEMENT DECISION")
    print("========================================")
    print(
        f"Recommendation    : {recommendation}"
    )

    print("\n========================================")
    print("       DATA CONFIDENCE")
    print("========================================")
    print(f"Confidence        : {confidence}")

    print("\n========================================")
    print("       MANAGEMENT SUMMARY")
    print("========================================")
    print(
        f"• Total sales are {total_sales}."
    )
    print(
        f"• 30-day revenue is {money(revenue_30)}."
    )
    print(
        f"• Gross profit is {money(gross_profit)}."
    )
    print(
        f"• Gross margin is {gross_margin:.2f}%."
    )
    print(
        f"• Inventory cost is {money(inventory_cost)}."
    )
    print(
        f"• Inventory retail value is "
        f"{money(retail_value)}."
    )
    print(
        "• Credit intelligence is "
        "not yet integrated into V37."
    )
    print(
        f"• Overall business health is "
        f"{business_health}."
    )
    print(
        f"• Data confidence is {confidence}."
    )
    print(
        f"• Recommendation: {recommendation}."
    )

    print("----------------------------------------")
    print("V37 STATUS : READ-ONLY")
    print(
        "Sales, inventory, profit and credit "
        "records were NOT modified."
    )
    print("========================================")

    conn.close()

    input("\nPress Enter to continue...")


if __name__ == "__main__":
    executive_business_intelligence()
