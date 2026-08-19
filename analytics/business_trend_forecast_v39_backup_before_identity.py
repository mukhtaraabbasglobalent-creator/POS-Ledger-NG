
import sqlite3
from datetime import datetime, timedelta


DB_PATH = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ============================================================
# PART 1 — 30-DAY BUSINESS TREND
# ============================================================

def get_business_trend():
    """
    V38 Part 1
    30-day business performance.

    READ-ONLY.
    """

    conn = get_connection()
    cur = conn.cursor()

    start_date = (
        datetime.now() - timedelta(days=30)
    ).strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("""
        SELECT
            COUNT(*) AS sales_count,
            COALESCE(SUM(total_amount), 0) AS revenue,
            COALESCE(SUM(total_profit), 0) AS profit
        FROM sales
        WHERE status != 'CANCELLED'
          AND sale_date >= ?
    """, (start_date,))

    row = cur.fetchone()
    conn.close()

    sales = int(row["sales_count"] or 0)
    revenue = float(row["revenue"] or 0)
    profit = float(row["profit"] or 0)

    margin = 0.0

    if revenue > 0:
        margin = (profit / revenue) * 100

    return {
        "sales": sales,
        "revenue": revenue,
        "profit": profit,
        "margin": margin
    }


# ============================================================
# PART 2 — DAILY SALES TREND
# ============================================================

def get_daily_trend():
    """
    V38 Part 2
    Daily sales, revenue and profit trend.

    READ-ONLY.
    """

    conn = get_connection()
    cur = conn.cursor()

    start_date = (
        datetime.now() - timedelta(days=30)
    ).strftime("%Y-%m-%d")

    cur.execute("""
        SELECT
            DATE(sale_date) AS sale_day,
            COUNT(*) AS sales_count,
            COALESCE(SUM(total_amount), 0) AS revenue,
            COALESCE(SUM(total_profit), 0) AS profit
        FROM sales
        WHERE status != 'CANCELLED'
          AND DATE(sale_date) >= ?
        GROUP BY DATE(sale_date)
        ORDER BY sale_day
    """, (start_date,))

    rows = cur.fetchall()
    conn.close()

    results = []

    for row in rows:
        results.append({
            "sale_day": row["sale_day"],
            "sales_count": int(row["sales_count"] or 0),
            "revenue": float(row["revenue"] or 0),
            "profit": float(row["profit"] or 0)
        })

    return results


# ============================================================
# PART 3 — PRODUCT TREND INTELLIGENCE
# ============================================================

def get_product_trend():
    """
    V38 Part 3

    Product-level intelligence is calculated from the
    reconciled sale records.

    READ-ONLY.
    """

    conn = get_connection()
    cur = conn.cursor()

    start_date = (
        datetime.now() - timedelta(days=30)
    ).strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("""
        SELECT
            p.id AS product_id,
            p.product_name AS product_name,

            COALESCE(SUM(s.quantity), 0) AS units_sold,

            COALESCE(SUM(s.total_amount), 0) AS revenue,

            COALESCE(SUM(s.total_profit), 0) AS profit

        FROM products p

        LEFT JOIN sales s
            ON p.id = s.product_id
           AND s.status != 'CANCELLED'
           AND s.sale_date >= ?

        GROUP BY
            p.id,
            p.product_name

        ORDER BY revenue DESC
    """, (start_date,))

    rows = cur.fetchall()
    conn.close()

    results = []

    for row in rows:

        units_sold = float(row["units_sold"] or 0)
        revenue = float(row["revenue"] or 0)
        profit = float(row["profit"] or 0)

        margin = 0.0

        if revenue > 0:
            margin = (profit / revenue) * 100

        results.append({
            "product_id": row["product_id"],
            "product_name": row["product_name"],
            "units_sold": units_sold,
            "revenue": revenue,
            "profit": profit,
            "margin": margin
        })

    return results


def print_product_trend():

    products = get_product_trend()

    print("\n========================================")
    print("       PRODUCT TREND INTELLIGENCE")
    print("========================================")

    if not products:

        print("No product data available.")

        return

    for index, product in enumerate(products, start=1):

        print("----------------------------------------")

        print(
            f"#{index} "
            f"{product['product_name']}"
        )

        print(
            f"Units Sold : "
            f"{product['units_sold']:.2f}"
        )

        print(
            f"Revenue    : "
            f"₦{product['revenue']:,.2f}"
        )

        print(
            f"Profit     : "
            f"₦{product['profit']:,.2f}"
        )

        print(
            f"Margin     : "
            f"{product['margin']:.2f}%"
        )

    active_products = [
        p for p in products
        if p["units_sold"] > 0
    ]

    inactive_products = [
        p for p in products
        if p["units_sold"] <= 0
    ]

    print("\n========================================")
    print("        PRODUCT HIGHLIGHTS")
    print("========================================")

    if active_products:

        best_revenue = max(
            active_products,
            key=lambda x: x["revenue"]
        )

        best_profit = max(
            active_products,
            key=lambda x: x["profit"]
        )

        best_units = max(
            active_products,
            key=lambda x: x["units_sold"]
        )

        print(
            f"Top Revenue Product : "
            f"{best_revenue['product_name']}"
        )

        print(
            f"Revenue             : "
            f"₦{best_revenue['revenue']:,.2f}"
        )

        print(
            f"Top Profit Product  : "
            f"{best_profit['product_name']}"
        )

        print(
            f"Profit              : "
            f"₦{best_profit['profit']:,.2f}"
        )

        print(
            f"Top Volume Product  : "
            f"{best_units['product_name']}"
        )

        print(
            f"Units Sold          : "
            f"{best_units['units_sold']:.2f}"
        )

    else:

        print("No product has recorded sales.")

    print("\n========================================")
    print("       PRODUCTS WITHOUT SALES")
    print("========================================")

    if inactive_products:

        for product in inactive_products:

            print(
                f"• {product['product_name']}"
            )

    else:

        print("All products have recorded sales.")

def get_evidence_level(total_sales, active_days):
    """
    V38 Data Confidence Layer.
    """

    if total_sales >= 50 and active_days >= 20:
        return {
            "level": "🟢 STRONGER",
            "status": "STRONGER EVIDENCE",
            "limited": False
        }

    elif total_sales >= 20 and active_days >= 10:
        return {
            "level": "🟡 MODERATE",
            "status": "MODERATE EVIDENCE",
            "limited": True
        }

    else:
        return {
            "level": "🟠 LIMITED",
            "status": "LIMITED EVIDENCE / EARLY WARNING",
            "limited": True
        }


# ============================================================
# MAIN V38 ENGINE
# ============================================================

def business_trend_forecast_v38():

    data = get_business_trend()

    # V38 Part 2 data
    daily = get_daily_trend()

    # V38 Data Confidence Layer
    evidence = get_evidence_level(
        data["sales"],
        len(daily)
    )

    print("\n========================================")
    print("       POS LEDGER NG V38")
    print(" BUSINESS TREND & FORECAST INTELLIGENCE")
    print("========================================")

    # ========================================================
    # PART 1
    # ========================================================

    print("\n========================================")
    print("        30-DAY BUSINESS TREND")
    print("========================================")

    print(
        f"Sales             : "
        f"{data['sales']}"
    )

    print(
        f"Revenue           : "
        f"₦{data['revenue']:,.2f}"
    )

    print(
        f"Gross Profit      : "
        f"₦{data['profit']:,.2f}"
    )

    print(
        f"Gross Margin      : "
        f"{data['margin']:.2f}%"
    )

    # ========================================================
    # PART 2
    # ========================================================

    daily = get_daily_trend()

    evidence = get_evidence_level(
        data["sales"],
        len(daily)
    )

    print("\n========================================")
    print("          DAILY SALES TREND")
    print("========================================")

    if not daily:

        print("No daily sales data available.")

    else:

        for row in daily:

            print("----------------------------------------")

            print(
                f"Date       : "
                f"{row['sale_day']}"
            )

            print(
                f"Sales      : "
                f"{row['sales_count']}"
            )

            print(
                f"Revenue    : "
                f"₦{row['revenue']:,.2f}"
            )

            print(
                f"Profit     : "
                f"₦{row['profit']:,.2f}"
            )

        best_day = max(
            daily,
            key=lambda x: x["revenue"]
        )

        lowest_day = min(
            daily,
            key=lambda x: x["revenue"]
        )

        print("\n========================================")
        print("          TREND HIGHLIGHTS")
        print("========================================")

        print(
            f"Best Revenue Day   : "
            f"{best_day['sale_day']}"
        )

        print(
            f"Best Day Revenue   : "
            f"₦{best_day['revenue']:,.2f}"
        )

        print(
            f"Lowest Revenue Day : "
            f"{lowest_day['sale_day']}"
        )

        print(
            f"Lowest Day Revenue : "
            f"₦{lowest_day['revenue']:,.2f}"
        )

        print(
            f"Active Sales Days  : "
            f"{len(daily)}"
        )

    # PART 4 — FORECAST INTELLIGENCE
    # ----------------------------------------

    if daily:

        total_revenue = sum(
            row["revenue"] for row in daily
        )

        total_profit = sum(
            row["profit"] for row in daily
        )

        total_sales = sum(
            row["sales_count"] for row in daily
        )

        active_days = len(daily)

        average_daily_revenue = (
            total_revenue / active_days
            if active_days > 0 else 0
        )

        average_daily_profit = (
            total_profit / active_days
            if active_days > 0 else 0
        )

        average_sales_per_day = (
            total_sales / active_days
            if active_days > 0 else 0
        )

        forecast_7_revenue = average_daily_revenue * 7
        forecast_30_revenue = average_daily_revenue * 30

        forecast_7_profit = average_daily_profit * 7
        forecast_30_profit = average_daily_profit * 30

        print("\n========================================")
        print("       FORECAST INTELLIGENCE")
        print("========================================")

        print(
            f"Average Daily Revenue : "
            f"₦{average_daily_revenue:,.2f}"
        )

        print(
            f"Average Daily Profit  : "
            f"₦{average_daily_profit:,.2f}"
        )

        print(
            f"Average Sales/Day     : "
            f"{average_sales_per_day:.2f}"
        )

        print("\n----------------------------------------")
        print("REVENUE FORECAST")
        print("----------------------------------------")

        print(
            f"7-Day Revenue Forecast  : "
            f"₦{forecast_7_revenue:,.2f}"
        )

        print(
            f"30-Day Revenue Forecast : "
            f"₦{forecast_30_revenue:,.2f}"
        )

        print("\n----------------------------------------")
        print("PROFIT FORECAST")
        print("----------------------------------------")

        print(
            f"7-Day Profit Forecast   : "
            f"₦{forecast_7_profit:,.2f}"
        )

        print(
            f"30-Day Profit Forecast  : "
            f"₦{forecast_30_profit:,.2f}"
        )

        # ----------------------------------------
        # REVENUE TREND DIRECTION
        # V38 EVIDENCE-AWARE TREND LOGIC
        # ----------------------------------------

        if len(daily) >= 2:

            first_revenue = daily[0]["revenue"]
            last_revenue = daily[-1]["revenue"]

            if last_revenue > first_revenue:
                raw_trend = "POSITIVE"
            elif last_revenue < first_revenue:
                raw_trend = "NEGATIVE"
            else:
                raw_trend = "STABLE"

            # Limited evidence must not produce a strong conclusion.
            if evidence["limited"]:

                if raw_trend == "NEGATIVE":
                    trend_direction = "🟠 EARLY WARNING"
                elif raw_trend == "POSITIVE":
                    trend_direction = "🟡 POSSIBLE POSITIVE TREND"
                else:
                    trend_direction = "🟡 POSSIBLY STABLE"

            else:

                if raw_trend == "POSITIVE":
                    trend_direction = "🟢 POSITIVE"
                elif raw_trend == "NEGATIVE":
                    trend_direction = "🔴 NEGATIVE"
                else:
                    trend_direction = "🟡 STABLE"

        else:

            trend_direction = "🟡 INSUFFICIENT DATA"

        print("\n----------------------------------------")
        print("TREND DIRECTION")
        print("----------------------------------------")

        print(
            f"Revenue Trend : {trend_direction}"
        )

        print(
            f"Trend Evidence: {evidence['status']}"
        )

        print(
            f"Sample        : {data['sales']} sales / "
            f"{len(daily)} active days"
        )

        # ----------------------------------------
        # FORECAST CONFIDENCE
        # ----------------------------------------

        if active_days >= 30:
            confidence = "🟢 HIGH"
        elif active_days >= 14:
            confidence = "🟡 MODERATE"
        elif active_days >= 7:
            confidence = "🟠 LIMITED"
        else:
            confidence = "🔴 VERY LIMITED"

        print("\n----------------------------------------")
        print("FORECAST CONFIDENCE")
        print("----------------------------------------")

        print(
            f"Confidence : {confidence}"
        )

        # ----------------------------------------
        # MANAGEMENT RECOMMENDATION
        # ----------------------------------------

        if average_daily_profit <= 0:

            recommendation = (
                "IMPROVE PRICING AND PROFITABILITY "
                "BEFORE EXPANDING SALES"
            )

        elif data["margin"] < 10:

            recommendation = (
                "IMPROVE PRODUCT MARGINS AND "
                "MONITOR OPERATING COSTS"
            )

        elif trend_direction == "🟢 POSITIVE":

            recommendation = (
                "MAINTAIN SALES MOMENTUM AND "
                "PLAN INVENTORY REPLENISHMENT"
            )

        else:

            recommendation = (
                "MONITOR SALES PERFORMANCE AND "
                "IMPROVE CUSTOMER CONVERSION"
            )

        print("\n========================================")
        print("      MANAGEMENT FORECAST DECISION")
        print("========================================")

        print(
            f"Recommendation : {recommendation}"
        )

        print("\n----------------------------------------")
        print("FORECAST NOTE")
        print("----------------------------------------")

        print(
            "Forecasts are based on observed historical "
            "sales activity and are estimates, not guarantees."
        )

        print(
            f"Forecast uses {active_days} active sales day(s)."
        )

    else:

        print("\n========================================")
        print("       FORECAST INTELLIGENCE")
        print("========================================")

        print("Forecast unavailable.")
        print("Reason : No sales history available.")

    # ----------------------------------------
    # PART 5 — BUSINESS HEALTH & RISK INTELLIGENCE
    # ----------------------------------------

    products = get_product_trend()

    print("\n========================================")
    print("      BUSINESS HEALTH & RISK INTELLIGENCE")
    print("========================================")

    revenue = data["revenue"]
    profit = data["profit"]
    margin = data["margin"]

    active_days = len(daily)
    total_sales = data["sales"]

    # ----------------------------------------
    # MARGIN HEALTH
    # ----------------------------------------

    print("\n----------------------------------------")
    print("MARGIN HEALTH")
    print("----------------------------------------")

    print(f"Gross Margin       : {margin:.2f}%")

    if margin >= 20:
        margin_status = "🟢 HEALTHY"
    elif margin >= 10:
        margin_status = "🟠 MODERATE"
    else:
        margin_status = "🔴 LOW"

    print(f"Margin Status      : {margin_status}")

    # ----------------------------------------
    # SALES ACTIVITY
    # ----------------------------------------

    print("\n----------------------------------------")
    print("SALES ACTIVITY")
    print("----------------------------------------")

    print(f"Active Sales Days  : {active_days}")
    print(f"Total Sales        : {total_sales}")

    if active_days >= 20:
        activity_status = "🟢 HIGH"
    elif active_days >= 10:
        activity_status = "🟠 MODERATE"
    else:
        activity_status = "🔴 LOW"

    print(f"Activity Status    : {activity_status}")

    # ----------------------------------------
    # REVENUE CONCENTRATION
    # ----------------------------------------

    print("\n----------------------------------------")
    print("REVENUE CONCENTRATION")
    print("----------------------------------------")

    if products:
        active_products = [
            p for p in products
            if p["revenue"] > 0
        ]

        if active_products and revenue > 0:

            top_product = max(
                active_products,
                key=lambda x: x["revenue"]
            )

            concentration = (
                top_product["revenue"] / revenue
            ) * 100

            print(
                f"Top Product        : "
                f"{top_product['product_name']}"
            )

            print(
                f"Top Product Revenue: "
                f"₦{top_product['revenue']:,.2f}"
            )

            print(
                f"Revenue Concentration: "
                f"{concentration:.2f}%"
            )

            if concentration >= 70:
                concentration_status = "🔴 HIGH RISK"
            elif concentration >= 50:
                concentration_status = "🟠 MODERATE RISK"
            else:
                concentration_status = "🟢 DIVERSIFIED"

            print(
                f"Concentration Status : "
                f"{concentration_status}"
            )

        else:
            print("No product revenue concentration available.")

    else:
        print("No product data available.")

    # ----------------------------------------
    # BUSINESS HEALTH SCORE
    # ----------------------------------------

    print("\n========================================")
    print("          BUSINESS HEALTH SUMMARY")
    print("========================================")

    risk_points = 0

    if margin < 10:
        risk_points += 1

    if active_days < 10:
        risk_points += 1

    if products and revenue > 0:

        active_products = [
            p for p in products
            if p["revenue"] > 0
        ]

        if active_products:
            top_product = max(
                active_products,
                key=lambda x: x["revenue"]
            )

            concentration = (
                top_product["revenue"] / revenue
            ) * 100

            if concentration >= 70:
                risk_points += 1

    if risk_points == 0:
        health_status = "🟢 HEALTHY"
    elif risk_points == 1:
        health_status = "🟠 WATCH"
    else:
        health_status = "🔴 AT RISK"

    print(f"Risk Indicators    : {risk_points}")
    print(f"Business Health    : {health_status}")

    # ----------------------------------------
    # V38 STATUS
    # ----------------------------------------

    print("\n========================================")
    print("             V38 STATUS")
    print("========================================")
    print("Parts               : 1 + 2 + 3 + 4 + 5")
    print("Mode                : READ-ONLY")
    print("Database modified   : NO")
    print("Sales modified      : NO")
    print("Inventory modified  : NO")
    print("========================================")


    # ----------------------------------------
    # PART 6 — ACTIONABLE BUSINESS RECOMMENDATIONS
    # ----------------------------------------

    print("\n========================================")
    print("     ACTIONABLE BUSINESS RECOMMENDATIONS")
    print("========================================")

    recommendations = []

    # Margin recommendation
    if margin < 10:
        recommendations.append(
            "Review product selling prices and buying costs "
            "because gross margin is below 10%."
        )
    elif margin < 20:
        recommendations.append(
            "Consider improving product margins before increasing expenses."
        )

    # Sales activity recommendation
    if active_days < 10:
        recommendations.append(
            "Increase sales activity and monitor inactive business days."
        )

    # Revenue concentration recommendation
    if products:
        total_revenue = sum(
            p["revenue"] for p in products
            if p["revenue"] > 0
        )

        if total_revenue > 0:

            top_product = max(
                products,
                key=lambda p: p["revenue"]
            )

            concentration = (
                top_product["revenue"]
                / total_revenue
            ) * 100

            if concentration >= 70:
                recommendations.append(
                    f"Reduce dependence on {top_product['product_name']} "
                    "by promoting additional products."
                )

    # Forecast confidence recommendation
    if active_days < 14:
        recommendations.append(
            "Continue collecting sales data because the forecast "
            "confidence is currently limited."
        )

    # Profit recommendation
    if profit > 0 and margin < 10:
        recommendations.append(
            "Protect profitability by controlling operating costs "
            "and improving high-volume product margins."
        )

    if not recommendations:
        recommendations.append(
            "Continue monitoring sales, margins, inventory and cash flow."
        )

    for index, recommendation in enumerate(
        recommendations,
        start=1
    ):
        print("----------------------------------------")
        print(f"{index}. {recommendation}")

    print("\n========================================")
    print("       MANAGEMENT PRIORITY")
    print("========================================")

    if margin < 10:
        print("Priority : 🔴 IMPROVE PROFIT MARGIN")
    elif active_days < 10:
        print("Priority : 🟠 INCREASE SALES ACTIVITY")
    else:
        print("Priority : 🟢 MAINTAIN BUSINESS PERFORMANCE")

    print("\n========================================")
    print("             V38 STATUS")
    print("========================================")
    print("Parts               : 1 + 2 + 3 + 4 + 5 + 6")
    print("Mode                : READ-ONLY")
    print("Database modified   : NO")
    print("Sales modified      : NO")
    print("Inventory modified  : NO")
    print("========================================")


    # ----------------------------------------
    # PART 7 — CUSTOMER & SALES INTELLIGENCE
    # ----------------------------------------

    conn = get_connection()
    cur = conn.cursor()

    print("\n========================================")
    print("       CUSTOMER & SALES INTELLIGENCE")
    print("========================================")

    # Check whether customers table exists
    cur.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type='table'
          AND name='customers'
    """)

    customers_table = cur.fetchone()

    if not customers_table:

        print("----------------------------------------")
        print("Customer intelligence unavailable.")
        print("Reason : customers table not found.")

    else:

        # Total customers
        cur.execute("""
            SELECT COUNT(*)
            FROM customers
        """)

        total_customers = cur.fetchone()[0] or 0

        # Customers with completed sales
        cur.execute("""
            SELECT COUNT(DISTINCT customer_id)
            FROM sales
            WHERE status != 'CANCELLED'
              AND customer_id IS NOT NULL
        """)

        active_customers = cur.fetchone()[0] or 0

        print("----------------------------------------")
        print(f"Total Customers       : {total_customers}")
        print(f"Active Customers      : {active_customers}")

        inactive_customers = (
            total_customers - active_customers
        )

        if inactive_customers < 0:
            inactive_customers = 0

        print(f"Inactive Customers    : {inactive_customers}")

        # ------------------------------------
        # CUSTOMER SALES SUMMARY
        # ------------------------------------

        cur.execute("""
            SELECT
                customer_id,
                COUNT(*) AS purchase_count,
                COALESCE(SUM(total_amount), 0) AS revenue,
                COALESCE(SUM(total_profit), 0) AS profit
            FROM sales
            WHERE status != 'CANCELLED'
              AND customer_id IS NOT NULL
            GROUP BY customer_id
            ORDER BY revenue DESC
        """)

        customer_rows = cur.fetchall()

        if customer_rows:

            highest_customer = customer_rows[0]

            total_customer_revenue = sum(
                float(row["revenue"] or 0)
                for row in customer_rows
            )

            repeat_customers = sum(
                1
                for row in customer_rows
                if int(row["purchase_count"] or 0) > 1
            )

            one_time_customers = sum(
                1
                for row in customer_rows
                if int(row["purchase_count"] or 0) == 1
            )

            print("\n========================================")
            print("       CUSTOMER PURCHASE BEHAVIOUR")
            print("========================================")

            print(f"Repeat Customers     : {repeat_customers}")
            print(f"One-Time Customers   : {one_time_customers}")

            # --------------------------------
            # CUSTOMER REVENUE CONCENTRATION
            # --------------------------------

            top_customer_revenue = float(
                highest_customer["revenue"] or 0
            )

            customer_concentration = 0.0

            if total_customer_revenue > 0:
                customer_concentration = (
                    top_customer_revenue
                    / total_customer_revenue
                ) * 100

            print("\n========================================")
            print("      CUSTOMER REVENUE CONCENTRATION")
            print("========================================")

            print(
                f"Top Customer Revenue : "
                f"₦{top_customer_revenue:,.2f}"
            )

            print(
                f"Revenue Concentration: "
                f"{customer_concentration:.2f}%"
            )

            # V38 evidence-aware customer concentration
            # A mathematically high concentration is not automatically
            # a confirmed business risk when the customer sample is small.

            customer_sample = len(customer_rows)

            if customer_sample < 5:
                if customer_concentration >= 70:
                    concentration_status = "🟠 EARLY WARNING"
                elif customer_concentration >= 50:
                    concentration_status = "🟡 POSSIBLE CONCENTRATION"
                else:
                    concentration_status = "🟢 HEALTHY"

                concentration_evidence = "LIMITED SAMPLE"

            elif customer_sample < 10:
                if customer_concentration >= 70:
                    concentration_status = "🟠 MODERATE RISK"
                elif customer_concentration >= 50:
                    concentration_status = "🟡 MODERATE"
                else:
                    concentration_status = "🟢 HEALTHY"

                concentration_evidence = "MODERATE SAMPLE"

            else:
                if customer_concentration >= 70:
                    concentration_status = "🔴 HIGH RISK"
                elif customer_concentration >= 50:
                    concentration_status = "🟠 MODERATE"
                else:
                    concentration_status = "🟢 HEALTHY"

                concentration_evidence = "STRONGER SAMPLE"

            print(
                f"Concentration Status : "
                f"{concentration_status}"
            )

            print(
                f"Evidence Status      : "
                f"{concentration_evidence}"
            )

            print(
                f"Revenue-Generating Customers : "
                f"{customer_sample}"
            )

            print(
                f"Registered Customers         : "
                f"{total_customers}"
            )

            # --------------------------------
            # AVERAGE TRANSACTION VALUE
            # --------------------------------

            average_transaction = 0.0

            if data["sales"] > 0:
                average_transaction = (
                    data["revenue"]
                    / data["sales"]
                )

            print("\n========================================")
            print("       CUSTOMER SALES METRICS")
            print("========================================")

            print(
                f"Average Transaction  : "
                f"₦{average_transaction:,.2f}"
            )

            print(
                f"Top Customer Sales   : "
                f"{highest_customer['purchase_count']}"
            )

            print(
                f"Top Customer Revenue : "
                f"₦{highest_customer['revenue']:,.2f}"
            )

            print(
                f"Top Customer Profit  : "
                f"₦{highest_customer['profit']:,.2f}"
            )

            # --------------------------------
            # CUSTOMER INTELLIGENCE DECISION
            # --------------------------------

            print("\n========================================")
            print("      CUSTOMER INTELLIGENCE DECISION")
            print("========================================")

            if repeat_customers == 0:
                print(
                    "Recommendation : BUILD CUSTOMER RETENTION "
                    "AND REPEAT-PURCHASE STRATEGIES"
                )

            elif customer_concentration >= 70:
                print(
                    "Recommendation : DIVERSIFY CUSTOMER BASE "
                    "TO REDUCE REVENUE DEPENDENCY"
                )

            elif customer_concentration >= 50:
                print(
                    "Recommendation : MONITOR CUSTOMER "
                    "REVENUE CONCENTRATION"
                )

            else:
                print(
                    "Recommendation : CUSTOMER BASE "
                    "SHOWS HEALTHY DIVERSIFICATION"
                )

        else:

            print("\nNo customer sales history available.")

    conn.close()


    # ----------------------------------------
    # PART 8 — INVENTORY & STOCK RISK INTELLIGENCE
    # ----------------------------------------

    print("\n========================================")
    print("     INVENTORY & STOCK RISK INTELLIGENCE")
    print("========================================")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            id,
            product_name,
            sku,
            category,
            buying_price,
            selling_price,
            current_stock,
            minimum_stock,
            min_stock,
            unit
        FROM products
        ORDER BY product_name
    """)

    inventory_rows = cur.fetchall()

    total_products = len(inventory_rows)

    zero_stock = []
    low_stock = []
    healthy_stock = []

    for row in inventory_rows:

        current_stock = float(row["current_stock"] or 0)

        minimum_stock = row["minimum_stock"]

        if minimum_stock is None:
            minimum_stock = row["min_stock"]

        minimum_stock = float(minimum_stock or 0)

        product = {
            "id": row["id"],
            "product_name": row["product_name"],
            "sku": row["sku"],
            "category": row["category"],
            "buying_price": float(row["buying_price"] or 0),
            "selling_price": float(row["selling_price"] or 0),
            "current_stock": current_stock,
            "minimum_stock": minimum_stock,
            "unit": row["unit"]
        }

        if current_stock <= 0:

            zero_stock.append(product)

        elif current_stock <= minimum_stock:

            low_stock.append(product)

        else:

            healthy_stock.append(product)

    # ----------------------------------------
    # INVENTORY SUMMARY
    # ----------------------------------------

    print("----------------------------------------")
    print(f"Total Products      : {total_products}")
    print(f"Zero Stock Products : {len(zero_stock)}")
    print(f"Low Stock Products  : {len(low_stock)}")
    print(f"Healthy Stock       : {len(healthy_stock)}")

    # ----------------------------------------
    # TOTAL INVENTORY VALUE
    # ----------------------------------------

    inventory_cost_value = sum(
        p["current_stock"] * p["buying_price"]
        for p in inventory_rows
    )

    inventory_sales_value = sum(
        p["current_stock"] * p["selling_price"]
        for p in inventory_rows
    )

    potential_inventory_profit = (
        inventory_sales_value -
        inventory_cost_value
    )

    print("\n========================================")
    print("          INVENTORY VALUE")
    print("========================================")

    print(
        f"Inventory Cost Value      : "
        f"₦{inventory_cost_value:,.2f}"
    )

    print(
        f"Potential Sales Value     : "
        f"₦{inventory_sales_value:,.2f}"
    )

    print(
        f"Potential Gross Profit    : "
        f"₦{potential_inventory_profit:,.2f}"
    )

    # ----------------------------------------
    # ZERO STOCK
    # ----------------------------------------

    print("\n========================================")
    print("          ZERO STOCK PRODUCTS")
    print("========================================")

    if zero_stock:

        for product in zero_stock:

            print("----------------------------------------")
            print(
                f"Product : {product['product_name']}"
            )
            print(
                f"SKU     : {product['sku'] or 'N/A'}"
            )
            print("Stock   : 0")

    else:

        print("No products are currently out of stock.")

    # ----------------------------------------
    # LOW STOCK
    # ----------------------------------------

    print("\n========================================")
    print("           LOW STOCK PRODUCTS")
    print("========================================")

    if low_stock:

        for product in low_stock:

            print("----------------------------------------")
            print(
                f"Product       : "
                f"{product['product_name']}"
            )
            print(
                f"Current Stock : "
                f"{product['current_stock']:.2f}"
            )
            print(
                f"Minimum Stock : "
                f"{product['minimum_stock']:.2f}"
            )

    else:

        print("No products currently require restocking.")

    # ----------------------------------------
    # INVENTORY MOVEMENT
    # ----------------------------------------

    cur.execute("""
        SELECT
            p.id AS product_id,
            p.product_name AS product_name,
            p.current_stock AS current_stock,
            COALESCE(SUM(s.quantity), 0) AS units_sold,
            COALESCE(SUM(s.total_amount), 0) AS revenue,
            COALESCE(SUM(s.total_profit), 0) AS profit
        FROM products p
        LEFT JOIN sales s
            ON p.id = s.product_id
           AND s.status != 'CANCELLED'
        GROUP BY
            p.id,
            p.product_name,
            p.current_stock
        ORDER BY units_sold DESC
    """)

    movement_rows = cur.fetchall()

    active_movement = [
        row
        for row in movement_rows
        if float(row["units_sold"] or 0) > 0
    ]

    print("\n========================================")
    print("        INVENTORY MOVEMENT INTELLIGENCE")
    print("========================================")

    if active_movement:

        fastest = active_movement[0]

        print("----------------------------------------")
        print(
            f"Fastest Moving Product : "
            f"{fastest['product_name']}"
        )
        print(
            f"Units Sold            : "
            f"{float(fastest['units_sold'] or 0):.2f}"
        )
        print(
            f"Current Stock          : "
            f"{float(fastest['current_stock'] or 0):.2f}"
        )

    else:

        print("No product movement recorded.")

    # ----------------------------------------
    # STOCK CONCENTRATION
    # ----------------------------------------

    total_stock_units = sum(
        float(row["current_stock"] or 0)
        for row in inventory_rows
    )

    if total_stock_units > 0 and inventory_rows:

        highest_stock_product = max(
            inventory_rows,
            key=lambda x: float(x["current_stock"] or 0)
        )

        highest_stock = float(
            highest_stock_product["current_stock"] or 0
        )

        stock_concentration = (
            highest_stock /
            total_stock_units
        ) * 100

        print("\n========================================")
        print("         STOCK CONCENTRATION")
        print("========================================")

        print(
            f"Top Stock Product     : "
            f"{highest_stock_product['product_name']}"
        )

        print(
            f"Stock Concentration   : "
            f"{stock_concentration:.2f}%"
        )

    # ----------------------------------------
    # INVENTORY RISK DECISION
    # ----------------------------------------

    print("\n========================================")
    print("          INVENTORY RISK SUMMARY")
    print("========================================")

    stock_risk_count = (
        len(zero_stock) +
        len(low_stock)
    )

    print(
        f"Stock Risk Products : "
        f"{stock_risk_count}"
    )

    if zero_stock:

        inventory_status = "🔴 CRITICAL"

        recommendation = (
            "RESTOCK ZERO-STOCK PRODUCTS "
            "AND PROTECT FAST-MOVING ITEMS"
        )

    elif low_stock:

        inventory_status = "🟠 WARNING"

        recommendation = (
            "MONITOR LOW-STOCK PRODUCTS "
            "AND PLAN REPLENISHMENT"
        )

    else:

        inventory_status = "🟢 HEALTHY"

        recommendation = (
            "INVENTORY LEVELS ARE CURRENTLY "
            "WITHIN THE MONITORED RANGE"
        )

    print(
        f"Inventory Status    : "
        f"{inventory_status}"
    )

    print("\n========================================")
    print("       INVENTORY MANAGEMENT DECISION")
    print("========================================")

    print(
        f"Recommendation : "
        f"{recommendation}"
    )

    conn.close()


# ----------------------------------------
# PART 9 — FINANCIAL INTELLIGENCE
# ----------------------------------------

def financial_intelligence_v39():

    conn = get_connection()
    cur = conn.cursor()

    print("\n========================================")
    print("       FINANCIAL INTELLIGENCE V39")
    print("========================================")

    # ----------------------------------------
    # REVENUE & PROFIT
    # ----------------------------------------

    cur.execute("""
        SELECT
            COALESCE(SUM(total_amount), 0) AS revenue,
            COALESCE(SUM(total_profit), 0) AS profit,
            COUNT(*) AS sales
        FROM sales
        WHERE status != 'CANCELLED'
    """)

    sales_data = cur.fetchone()

    revenue = float(sales_data["revenue"] or 0)
    gross_profit = float(sales_data["profit"] or 0)
    sales_count = int(sales_data["sales"] or 0)

    gross_margin = 0.0

    if revenue > 0:
        gross_margin = (gross_profit / revenue) * 100

    print("\n----------------------------------------")
    print("REVENUE & PROFIT")
    print("----------------------------------------")

    print(
        f"Total Revenue        : "
        f"₦{revenue:,.2f}"
    )

    print(
        f"Gross Profit         : "
        f"₦{gross_profit:,.2f}"
    )

    print(
        f"Gross Margin         : "
        f"{gross_margin:.2f}%"
    )

    print(
        f"Completed Sales      : "
        f"{sales_count}"
    )

    # ----------------------------------------
    # EXPENSE INTELLIGENCE
    # ----------------------------------------

    cur.execute("""
        SELECT
            COUNT(*) AS expense_count,
            COALESCE(SUM(amount), 0) AS total_expenses
        FROM expenses
    """)

    expense_data = cur.fetchone()

    expense_count = int(
        expense_data["expense_count"] or 0
    )

    total_expenses = float(
        expense_data["total_expenses"] or 0
    )

    operating_result = (
        gross_profit -
        total_expenses
    )

    print("\n----------------------------------------")
    print("EXPENSE INTELLIGENCE")
    print("----------------------------------------")

    print(
        f"Expense Count       : "
        f"{expense_count}"
    )

    print(
        f"Total Expenses      : "
        f"₦{total_expenses:,.2f}"
    )

    print(
        f"Operating Result    : "
        f"₦{operating_result:,.2f}"
    )

    # ----------------------------------------
    # TRANSACTION / WITHDRAWAL INTELLIGENCE
    # ----------------------------------------

    cur.execute("""
        SELECT
            COALESCE(
                SUM(
                    CASE
                        WHEN LOWER(transaction_type)
                        LIKE '%withdraw%'
                        THEN amount
                        ELSE 0
                    END
                ), 0
            ) AS withdrawals,

            COALESCE(
                SUM(
                    CASE
                        WHEN LOWER(transaction_type)
                        LIKE '%deposit%'
                        THEN amount
                        ELSE 0
                    END
                ), 0
            ) AS deposits,

            COALESCE(
                SUM(
                    CASE
                        WHEN LOWER(transaction_type)
                        LIKE '%withdraw%'
                        THEN profit
                        ELSE 0
                    END
                ), 0
            ) AS withdrawal_profit

        FROM transactions
    """)

    transaction_data = cur.fetchone()

    withdrawals = float(
        transaction_data["withdrawals"] or 0
    )

    deposits = float(
        transaction_data["deposits"] or 0
    )

    withdrawal_profit = float(
        transaction_data["withdrawal_profit"] or 0
    )

    print("\n----------------------------------------")
    print("TRANSACTION INTELLIGENCE")
    print("----------------------------------------")

    print(
        f"Deposits           : "
        f"₦{deposits:,.2f}"
    )

    print(
        f"Withdrawals        : "
        f"₦{withdrawals:,.2f}"
    )

    print(
        f"Transaction Profit : "
        f"₦{withdrawal_profit:,.2f}"
    )

    # ----------------------------------------
    # CURRENT BALANCE
    # ----------------------------------------

    cur.execute("""
        SELECT
            COALESCE(cash_balance, 0) AS cash_balance,
            COALESCE(wallet_balance, 0) AS wallet_balance,
            COALESCE(opening_balance, 0) AS opening_balance,
            updated_at
        FROM balance
        ORDER BY id DESC
        LIMIT 1
    """)

    balance_data = cur.fetchone()

    if balance_data:

        cash_balance = float(
            balance_data["cash_balance"] or 0
        )

        wallet_balance = float(
            balance_data["wallet_balance"] or 0
        )

        opening_balance = float(
            balance_data["opening_balance"] or 0
        )

        updated_at = balance_data["updated_at"]

    else:

        cash_balance = 0.0
        wallet_balance = 0.0
        opening_balance = 0.0
        updated_at = "N/A"

    total_liquid_balance = (
        cash_balance +
        wallet_balance
    )

    print("\n========================================")
    print("          LIQUID FUNDS POSITION")
    print("========================================")

    print(
        f"Opening Balance    : "
        f"₦{opening_balance:,.2f}"
    )

    print(
        f"Cash Balance       : "
        f"₦{cash_balance:,.2f}"
    )

    print(
        f"Wallet Balance     : "
        f"₦{wallet_balance:,.2f}"
    )

    print(
        f"Total Liquid Funds : "
        f"₦{total_liquid_balance:,.2f}"
    )

    print(
        f"Balance Updated    : "
        f"{updated_at}"
    )

    # ----------------------------------------
    # CUSTOMER CREDIT EXPOSURE
    # ----------------------------------------

    cur.execute("""
        SELECT
            COALESCE(SUM(balance), 0) AS outstanding_credit,
            COUNT(*) AS credit_accounts
        FROM customer_credit
        WHERE status NOT IN ('PAID', 'CANCELLED')
    """)

    credit_data = cur.fetchone()

    outstanding_credit = float(
        credit_data["outstanding_credit"] or 0
    )

    credit_accounts = int(
        credit_data["credit_accounts"] or 0
    )

    print("\n----------------------------------------")
    print("CUSTOMER CREDIT EXPOSURE")
    print("----------------------------------------")

    print(
        f"Outstanding Credit : "
        f"₦{outstanding_credit:,.2f}"
    )

    print(
        f"Credit Accounts    : "
        f"{credit_accounts}"
    )

    # ----------------------------------------
    # SUPPLIER LIABILITY
    # ----------------------------------------

    cur.execute("""
        SELECT
            COALESCE(SUM(balance), 0) AS supplier_debt,
            COUNT(*) AS supplier_accounts
        FROM creditors
        WHERE balance > 0
    """)

    creditor_data = cur.fetchone()

    supplier_debt = float(
        creditor_data["supplier_debt"] or 0
    )

    supplier_accounts = int(
        creditor_data["supplier_accounts"] or 0
    )

    print("\n----------------------------------------")
    print("SUPPLIER LIABILITY")
    print("----------------------------------------")

    print(
        f"Supplier Liability : "
        f"₦{supplier_debt:,.2f}"
    )

    print(
        f"Supplier Accounts  : "
        f"{supplier_accounts}"
    )

    # ----------------------------------------
    # INVENTORY CAPITAL
    # ----------------------------------------

    cur.execute("""
        SELECT
            COALESCE(
                SUM(current_stock * buying_price),
                0
            ) AS inventory_cost
        FROM products
    """)

    inventory_data = cur.fetchone()

    inventory_capital = float(
        inventory_data["inventory_cost"] or 0
    )

    print("\n----------------------------------------")
    print("INVENTORY CAPITAL")
    print("----------------------------------------")

    print(
        f"Inventory Capital  : "
        f"₦{inventory_capital:,.2f}"
    )

    # ----------------------------------------
    # NET FINANCIAL POSITION
    # ----------------------------------------

    total_assets = (
        total_liquid_balance +
        outstanding_credit +
        inventory_capital
    )

    total_liabilities = supplier_debt

    net_financial_position = (
        total_assets -
        total_liabilities
    )

    print("\n========================================")
    print("       NET FINANCIAL POSITION")
    print("========================================")

    print(
        f"Liquid Funds       : "
        f"₦{total_liquid_balance:,.2f}"
    )

    print(
        f"Customer Credit    : "
        f"₦{outstanding_credit:,.2f}"
    )

    print(
        f"Inventory Capital  : "
        f"₦{inventory_capital:,.2f}"
    )

    print(
        f"Total Assets       : "
        f"₦{total_assets:,.2f}"
    )

    print(
        f"Supplier Liability : "
        f"₦{total_liabilities:,.2f}"
    )

    print(
        f"Net Position       : "
        f"₦{net_financial_position:,.2f}"
    )

    # ----------------------------------------
    # FINANCIAL RISK INTELLIGENCE
    # ----------------------------------------

    financial_risk = 0

    if gross_margin < 10:
        financial_risk += 1

    if operating_result < 0:
        financial_risk += 1

    if supplier_debt > total_liquid_balance:
        financial_risk += 1

    if outstanding_credit > total_liquid_balance:
        financial_risk += 1

    if total_liquid_balance <= 0:
        financial_risk += 1

    if financial_risk == 0:
        financial_status = "🟢 FINANCIALLY STABLE"
    elif financial_risk <= 2:
        financial_status = "🟠 FINANCIAL WATCH"
    else:
        financial_status = "🔴 FINANCIAL RISK"

    print("\n========================================")
    print("       FINANCIAL RISK INTELLIGENCE")
    print("========================================")

    print(
        f"Financial Risk Indicators : "
        f"{financial_risk}"
    )

    print(
        f"Financial Status          : "
        f"{financial_status}"
    )

    # ----------------------------------------
    # MANAGEMENT FINANCIAL DECISION
    # ----------------------------------------

    print("\n========================================")
    print("     MANAGEMENT FINANCIAL DECISION")
    print("========================================")

    if operating_result < 0:

        financial_recommendation = (
            "CONTROL OPERATING EXPENSES "
            "AND IMPROVE PROFIT MARGINS"
        )

    elif supplier_debt > total_liquid_balance:

        financial_recommendation = (
            "REDUCE SUPPLIER LIABILITY "
            "AND PROTECT LIQUID CASH"
        )

    elif outstanding_credit > total_liquid_balance:

        financial_recommendation = (
            "ACCELERATE CUSTOMER CREDIT COLLECTION "
            "TO PROTECT LIQUIDITY"
        )

    elif gross_margin < 10:

        financial_recommendation = (
            "IMPROVE PRODUCT MARGINS "
            "BEFORE EXPANDING OPERATING COSTS"
        )

    else:

        financial_recommendation = (
            "MAINTAIN FINANCIAL DISCIPLINE "
            "AND CONTINUE MONITORING CASH FLOW"
        )

    print(
        f"Recommendation : "
        f"{financial_recommendation}"
    )

    print("\n========================================")
    print("          V39 FINANCIAL STATUS")
    print("========================================")

    print("Mode                : READ-ONLY")
    print("Database modified   : NO")
    print("Sales modified      : NO")
    print("Expenses modified   : NO")
    print("Balance modified    : NO")
    print("Credit modified     : NO")
    print("Inventory modified  : NO")
    print("========================================")

    conn.close()


if __name__ == "__main__":
    business_trend_forecast_v38()
    financial_intelligence_v39()
