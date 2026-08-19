import sqlite3
from datetime import datetime, timedelta


DB_PATH = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


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


def get_daily_trend():
    """
    V38 Part 2
    Daily sales, revenue and profit trend.

    READ-ONLY.
    """

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            DATE(sale_date) AS sale_day,
            COUNT(*) AS sales_count,
            COALESCE(SUM(total_amount), 0) AS revenue,
            COALESCE(SUM(total_profit), 0) AS profit
        FROM sales
        WHERE status != 'CANCELLED'
        GROUP BY DATE(sale_date)
        ORDER BY sale_day
    """)

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

def get_product_trend():
    """
    V38 Part 3
    Product-level sales, revenue and profit intelligence.

    READ-ONLY.
    """

    conn = get_connection()
    cur = conn.cursor()

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
        GROUP BY p.id, p.product_name
        ORDER BY revenue DESC
    """)

    rows = cur.fetchall()
    conn.close()

    results = []

    for row in rows:
        results.append({
            "product_id": row["product_id"],
            "product_name": row["product_name"],
            "units_sold": float(row["units_sold"] or 0),
            "revenue": float(row["revenue"] or 0),
            "profit": float(row["profit"] or 0)
        })

    return results
    # ----------------------------------------
    # PART 3 — PRODUCT TREND INTELLIGENCE
    # ----------------------------------------

    products = get_product_trend()

    print("\n========================================")
    print("       PRODUCT TREND INTELLIGENCE")
    print("========================================")

    if not products:

        print("No product data available.")

    else:

        for index, product in enumerate(products, start=1):

            print("----------------------------------------")
            print(f"#{index} {product['product_name']}")
            print(f"Units Sold : {product['units_sold']:.2f}")
            print(f"Revenue    : ₦{product['revenue']:,.2f}")
            print(f"Profit     : ₦{product['profit']:,.2f}")

        active_products = [
            p for p in products
            if p["units_sold"] > 0
        ]

        if active_products:

            best_product = max(
                active_products,
                key=lambda x: x["revenue"]
            )

            best_profit_product = max(
                active_products,
                key=lambda x: x["profit"]
            )

            print("\n========================================")
            print("        PRODUCT HIGHLIGHTS")
            print("========================================")

            print(
                f"Top Revenue Product : "
                f"{best_product['product_name']}"
            )

            print(
                f"Revenue             : "
                f"₦{best_product['revenue']:,.2f}"
            )

            print(
                f"Top Profit Product  : "
                f"{best_profit_product['product_name']}"
            )

            print(
                f"Profit              : "
                f"₦{best_profit_product['profit']:,.2f}"
            )

        else:

            print("\nNo product has recorded sales.")


def business_trend_forecast_v38():

    data = get_business_trend()

    print("\n========================================")
    print("       POS LEDGER NG V38")
    print(" BUSINESS TREND & FORECAST INTELLIGENCE")
    print("========================================")

    # ----------------------------------------
    # PART 1
    # ----------------------------------------

    print("\n========================================")
    print("        30-DAY BUSINESS TREND")
    print("========================================")

    print(f"Sales             : {data['sales']}")
    print(f"Revenue           : ₦{data['revenue']:,.2f}")
    print(f"Gross Profit      : ₦{data['profit']:,.2f}")
    print(f"Gross Margin      : {data['margin']:.2f}%")

    # ----------------------------------------
    # PART 2
    # ----------------------------------------

    daily = get_daily_trend()

    print("\n========================================")
    print("          DAILY SALES TREND")
    print("========================================")

    if not daily:
        print("No daily sales data available.")

    else:

        for row in daily:

            print("----------------------------------------")
            print(f"Date       : {row['sale_day']}")
            print(f"Sales      : {row['sales_count']}")
            print(f"Revenue    : ₦{row['revenue']:,.2f}")
            print(f"Profit     : ₦{row['profit']:,.2f}")

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

        print(f"Best Revenue Day   : {best_day['sale_day']}")
        print(f"Best Day Revenue   : ₦{best_day['revenue']:,.2f}")

        print(f"Lowest Revenue Day : {lowest_day['sale_day']}")
        print(f"Lowest Day Revenue : ₦{lowest_day['revenue']:,.2f}")

        print(f"Active Sales Days  : {len(daily)}")

    # ----------------------------------------
    # V38 STATUS
    # ----------------------------------------

    print("\n========================================")
    print("             V38 STATUS")
    print("========================================")
    print("Parts               : 1 + 2 + 3")
    print("Mode                : READ-ONLY")
    print("Database modified   : NO")
    print("Sales modified      : NO")
    print("Inventory modified  : NO")
    print("========================================")


if __name__ == "__main__":
    business_trend_forecast_v38()
