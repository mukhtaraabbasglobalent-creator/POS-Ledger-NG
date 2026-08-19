"""
POS Ledger NG V49
Sales & Revenue Intelligence

READ-ONLY.
Analyzes completed sales and produces:
- Revenue
- Profit
- Units sold
- Average transaction
- Product performance
- Sales-day activity
- Revenue/profit concentration
- Management recommendations
"""

from database.connection import get_connection


def sales_revenue_intelligence_v49():

    print("\n========================================")
    print("       POS LEDGER NG V49")
    print("     SALES & REVENUE INTELLIGENCE")
    print("========================================")

    conn = get_connection()

    try:
        cur = conn.cursor()

        summary = cur.execute("""
            SELECT
                COUNT(*) AS completed_sales,
                COALESCE(SUM(total_amount), 0),
                COALESCE(SUM(total_profit), 0),
                COALESCE(SUM(quantity), 0),
                COUNT(DISTINCT substr(sale_date, 1, 10))
            FROM sales
            WHERE status = 'COMPLETED'
        """).fetchone()

        completed_sales = int(summary[0] or 0)
        revenue = float(summary[1] or 0)
        profit = float(summary[2] or 0)
        units_sold = float(summary[3] or 0)
        active_days = int(summary[4] or 0)

        if completed_sales > 0:
            average_transaction = revenue / completed_sales
        else:
            average_transaction = 0.0

        if revenue > 0:
            overall_margin = profit / revenue * 100
        else:
            overall_margin = 0.0

        if active_days > 0:
            revenue_per_day = revenue / active_days
            profit_per_day = profit / active_days
            units_per_day = units_sold / active_days
        else:
            revenue_per_day = 0.0
            profit_per_day = 0.0
            units_per_day = 0.0

        print("\n========================================")
        print("       SALES PERFORMANCE")
        print("========================================")

        print("Completed Sales      :", completed_sales)
        print("Units Sold           :", f"{units_sold:g}")
        print("Revenue              :", f"₦{revenue:,.2f}")
        print("Gross Profit         :", f"₦{profit:,.2f}")
        print("Gross Margin         :", f"{overall_margin:.2f}%")
        print("Average Transaction  :", f"₦{average_transaction:,.2f}")

        print("\n========================================")
        print("       SALES ACTIVITY")
        print("========================================")

        print("Active Sales Days    :", active_days)
        print("Revenue / Active Day :", f"₦{revenue_per_day:,.2f}")
        print("Profit / Active Day  :", f"₦{profit_per_day:,.2f}")
        print("Units / Active Day   :", f"{units_per_day:.2f}")

        if active_days >= 10:
            activity_status = "🟢 STRONG DATA"
        elif active_days >= 5:
            activity_status = "🟡 DEVELOPING DATA"
        else:
            activity_status = "🟠 LIMITED DATA"

        print("Activity Status      :", activity_status)

        print("\n========================================")
        print("       PRODUCT SALES PERFORMANCE")
        print("========================================")

        products = cur.execute("""
            SELECT
                p.product_name,
                p.sku,
                COALESCE(SUM(s.quantity), 0),
                COALESCE(SUM(s.total_amount), 0),
                COALESCE(SUM(s.total_profit), 0),
                COUNT(s.id)
            FROM products p
            LEFT JOIN sales s
                ON p.id = s.product_id
                AND s.status = 'COMPLETED'
            GROUP BY p.id, p.product_name, p.sku
            ORDER BY COALESCE(SUM(s.total_amount), 0) DESC
        """).fetchall()

        if not products:
            print("\nNo product sales data found.")
        else:

            for row in products:

                name = row[0]
                sku = row[1]
                product_units = float(row[2] or 0)
                product_revenue = float(row[3] or 0)
                product_profit = float(row[4] or 0)
                product_sales = int(row[5] or 0)

                if revenue > 0:
                    revenue_share = (
                        product_revenue / revenue * 100
                    )
                else:
                    revenue_share = 0.0

                if product_revenue > 0:
                    product_margin = (
                        product_profit /
                        product_revenue *
                        100
                    )
                else:
                    product_margin = 0.0

                print("\n----------------------------------------")
                print("Product              :", name)
                print("SKU                  :", sku)
                print("Units Sold           :", f"{product_units:g}")
                print("Completed Sales      :", product_sales)
                print(
                    "Revenue              :",
                    f"₦{product_revenue:,.2f}"
                )
                print(
                    "Profit               :",
                    f"₦{product_profit:,.2f}"
                )
                print(
                    "Gross Margin         :",
                    f"{product_margin:.2f}%"
                )
                print(
                    "Revenue Contribution:",
                    f"{revenue_share:.2f}%"
                )

        print("\n========================================")
        print("       TOP PRODUCT ANALYSIS")
        print("========================================")

        top_revenue = cur.execute("""
            SELECT
                p.product_name,
                COALESCE(SUM(s.total_amount), 0)
            FROM sales s
            JOIN products p
                ON p.id = s.product_id
            WHERE s.status = 'COMPLETED'
            GROUP BY s.product_id
            ORDER BY SUM(s.total_amount) DESC
            LIMIT 1
        """).fetchone()

        top_profit = cur.execute("""
            SELECT
                p.product_name,
                COALESCE(SUM(s.total_profit), 0)
            FROM sales s
            JOIN products p
                ON p.id = s.product_id
            WHERE s.status = 'COMPLETED'
            GROUP BY s.product_id
            ORDER BY SUM(s.total_profit) DESC
            LIMIT 1
        """).fetchone()

        top_units = cur.execute("""
            SELECT
                p.product_name,
                COALESCE(SUM(s.quantity), 0)
            FROM sales s
            JOIN products p
                ON p.id = s.product_id
            WHERE s.status = 'COMPLETED'
            GROUP BY s.product_id
            ORDER BY SUM(s.quantity) DESC
            LIMIT 1
        """).fetchone()

        print(
            "Top Revenue Product  :",
            top_revenue[0] if top_revenue else "N/A"
        )

        print(
            "Top Profit Product   :",
            top_profit[0] if top_profit else "N/A"
        )

        print(
            "Top Units Product    :",
            top_units[0] if top_units else "N/A"
        )

        print("\n========================================")
        print("       MANAGEMENT INSIGHTS")
        print("========================================")

        insights = []

        if overall_margin < 10:
            insights.append(
                "Overall gross margin is below the 10% management target."
            )

        if average_transaction < 2000:
            insights.append(
                "Average transaction value is relatively low; "
                "consider suitable cross-selling or higher-value sales."
            )

        if active_days < 10:
            insights.append(
                "Sales history is still limited; collect more data "
                "before relying heavily on long-term forecasts."
            )

        if revenue > 0 and profit > 0:
            insights.append(
                "Continue monitoring products that generate revenue "
                "but contribute weak profit margins."
            )

        if insights:
            for index, insight in enumerate(insights, start=1):
                print(f"{index}. {insight}")
        else:
            print("No immediate sales management warnings detected.")

        print("\n========================================")
        print("       V49 MODULE STATUS")
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
    sales_revenue_intelligence_v49()
