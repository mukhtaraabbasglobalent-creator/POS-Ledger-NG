import sqlite3
from datetime import datetime, timedelta

DB_PATH = "data/posledger.db"

TARGET_MARGIN = 0.10
FORECAST_DAYS = 30


def money(value):
    return f"₦{value:,.2f}"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def scalar(conn, query, params=()):
    row = conn.execute(query, params).fetchone()
    if row is None:
        return 0.0
    value = row[0]
    return float(value or 0)


def load_data(conn):
    revenue = scalar(
        conn,
        """
        SELECT COALESCE(SUM(total_amount), 0)
        FROM sales
        WHERE status = 'COMPLETED'
        """
    )

    profit = scalar(
        conn,
        """
        SELECT COALESCE(SUM(total_profit), 0)
        FROM sales
        WHERE status = 'COMPLETED'
        """
    )

    completed_sales = int(
        scalar(
            conn,
            """
            SELECT COUNT(*)
            FROM sales
            WHERE status = 'COMPLETED'
            """
        )
    )

    units_sold = scalar(
        conn,
        """
        SELECT COALESCE(SUM(quantity), 0)
        FROM sales
        WHERE status = 'COMPLETED'
        """
    )

    active_days = int(
        scalar(
            conn,
            """
            SELECT COUNT(DISTINCT date(sale_date))
            FROM sales
            WHERE status = 'COMPLETED'
            """
        )
    )

    liquid_funds = scalar(
        conn,
        """
        SELECT COALESCE(cash_balance, 0) +
               COALESCE(wallet_balance, 0)
        FROM balance
        LIMIT 1
        """
    )

    customer_credit = scalar(
        conn,
        """
        SELECT COALESCE(SUM(balance), 0)
        FROM customer_credit
        WHERE balance > 0
        """
    )

    supplier_liability = scalar(
        conn,
        """
        SELECT COALESCE(SUM(balance), 0)
        FROM creditors
        WHERE balance > 0
        """
    )

    inventory_capital = scalar(
        conn,
        """
        SELECT COALESCE(SUM(current_stock * buying_price), 0)
        FROM products
        """
    )

    return {
        "revenue": revenue,
        "profit": profit,
        "completed_sales": completed_sales,
        "units_sold": units_sold,
        "active_days": active_days,
        "liquid_funds": liquid_funds,
        "customer_credit": customer_credit,
        "supplier_liability": supplier_liability,
        "inventory_capital": inventory_capital,
    }


def forecast(data):
    revenue = data["revenue"]
    profit = data["profit"]
    units = data["units_sold"]
    days = data["active_days"]

    if days <= 0:
        return {
            "daily_revenue": 0,
            "daily_profit": 0,
            "daily_units": 0,
            "forecast_revenue": 0,
            "forecast_profit": 0,
            "forecast_units": 0,
            "confidence": "VERY LOW",
        }

    daily_revenue = revenue / days
    daily_profit = profit / days
    daily_units = units / days

    return {
        "daily_revenue": daily_revenue,
        "daily_profit": daily_profit,
        "daily_units": daily_units,
        "forecast_revenue": daily_revenue * FORECAST_DAYS,
        "forecast_profit": daily_profit * FORECAST_DAYS,
        "forecast_units": daily_units * FORECAST_DAYS,
        "confidence": (
            "LOW" if days < 14
            else "MODERATE" if days < 30
            else "GOOD"
        ),
    }


def margin_scenario(data):
    revenue = data["revenue"]

    target_profit = revenue * TARGET_MARGIN
    additional_profit = max(0, target_profit - data["profit"])

    projected_30_day_profit = (
        revenue / data["active_days"] * FORECAST_DAYS
        * TARGET_MARGIN
        if data["active_days"] > 0
        else 0
    )

    return target_profit, additional_profit, projected_30_day_profit


def product_scenarios(conn):
    rows = conn.execute(
        """
        SELECT
            p.product_name,
            p.sku,
            p.buying_price,
            p.selling_price,
            p.current_stock,
            COALESCE(SUM(
                CASE
                    WHEN s.status = 'COMPLETED'
                    THEN s.quantity
                    ELSE 0
                END
            ), 0) AS units_sold
        FROM products p
        LEFT JOIN sales s
            ON s.product_id = p.id
        GROUP BY
            p.id,
            p.product_name,
            p.sku,
            p.buying_price,
            p.selling_price,
            p.current_stock
        ORDER BY units_sold DESC
        """
    ).fetchall()

    results = []

    for row in rows:
        buying = float(row["buying_price"] or 0)
        selling = float(row["selling_price"] or 0)
        units = float(row["units_sold"] or 0)

        if buying <= 0 or selling <= 0:
            continue

        current_margin = (selling - buying) / selling

        if current_margin < TARGET_MARGIN:
            target_price = buying / (1 - TARGET_MARGIN)
            extra_profit = max(
                0,
                (target_price - selling) * units
            )

            decision = "🟠 REVIEW PRICING"
        else:
            target_price = selling
            extra_profit = 0
            decision = "🟢 MAINTAIN"

        results.append({
            "name": row["product_name"],
            "sku": row["sku"],
            "buying": buying,
            "selling": selling,
            "margin": current_margin,
            "units": units,
            "stock": float(row["current_stock"] or 0),
            "target_price": target_price,
            "extra_profit": extra_profit,
            "decision": decision,
        })

    return results


def main():
    conn = get_connection()

    try:
        data = load_data(conn)
        products = product_scenarios(conn)
    finally:
        conn.close()

    f = forecast(data)

    target_profit, additional_profit, target_30_day_profit = (
        margin_scenario(data)
    )

    print("=" * 40)
    print("       POS LEDGER NG V55")
    print(" BUSINESS FORECAST & DECISION INTELLIGENCE")
    print("=" * 40)

    print()
    print("=" * 40)
    print("       CURRENT BUSINESS BASELINE")
    print("=" * 40)
    print(f"Revenue              : {money(data['revenue'])}")
    print(f"Gross Profit         : {money(data['profit'])}")

    margin = (
        data["profit"] / data["revenue"]
        if data["revenue"] > 0
        else 0
    )

    print(f"Gross Margin         : {margin * 100:.2f}%")
    print(f"Completed Sales      : {data['completed_sales']}")
    print(f"Units Sold           : {data['units_sold']:.2f}")
    print(f"Active Sales Days    : {data['active_days']}")

    print()
    print("=" * 40)
    print("       30-DAY BASELINE FORECAST")
    print("=" * 40)
    print(f"Daily Revenue        : {money(f['daily_revenue'])}")
    print(f"Daily Profit         : {money(f['daily_profit'])}")
    print(f"Daily Units          : {f['daily_units']:.2f}")
    print(f"Projected Revenue    : {money(f['forecast_revenue'])}")
    print(f"Projected Profit     : {money(f['forecast_profit'])}")
    print(f"Projected Units      : {f['forecast_units']:.2f}")
    print(f"Forecast Confidence  : 🟡 {f['confidence']}")

    print()
    print("=" * 40)
    print("       10% MARGIN SCENARIO")
    print("=" * 40)
    print(f"Current Profit       : {money(data['profit'])}")
    print(f"Target Profit        : {money(target_profit)}")
    print(f"Additional Profit    : {money(additional_profit)}")
    print(
        f"30-Day Target Profit : "
        f"{money(target_30_day_profit)}"
    )

    print()
    print("=" * 40)
    print("       LIQUIDITY OUTLOOK")
    print("=" * 40)
    print(f"Actual Liquid Funds  : {money(data['liquid_funds'])}")
    print(f"Customer Receivable  : {money(data['customer_credit'])}")
    print(
        f"Potential After Collection: "
        f"{money(data['liquid_funds'] + data['customer_credit'])}"
    )
    print(
        f"Supplier Liability   : "
        f"{money(data['supplier_liability'])}"
    )

    liquidity_gap = max(
        0,
        data["supplier_liability"] - data["liquid_funds"]
    )

    print(f"Current Supplier Gap : {money(liquidity_gap)}")

    print()
    print("=" * 40)
    print("       PRODUCT FORECAST SCENARIOS")
    print("=" * 40)

    for p in products:
        print()
        print("-" * 40)
        print(f"Product              : {p['name']}")
        print(f"SKU                  : {p['sku']}")
        print(f"Buying Price         : {money(p['buying'])}")
        print(f"Selling Price        : {money(p['selling'])}")
        print(f"Current Margin       : {p['margin'] * 100:.2f}%")
        print(f"Units Sold           : {p['units']:.2f}")
        print(f"Current Stock        : {p['stock']:.2f}")

        if p["decision"] == "🟠 REVIEW PRICING":
            print(
                f"Target Selling Price : "
                f"{money(p['target_price'])}"
            )
            print(
                f"Potential Extra Profit: "
                f"{money(p['extra_profit'])}"
            )

        print(f"Decision             : {p['decision']}")

    print()
    print("=" * 40)
    print("       BUSINESS TRAJECTORY")
    print("=" * 40)

    if data["active_days"] < 14:
        trajectory = "🟡 DEVELOPING — MORE DATA REQUIRED"
    elif margin >= TARGET_MARGIN and liquidity_gap == 0:
        trajectory = "🟢 IMPROVING"
    elif margin < TARGET_MARGIN or liquidity_gap > 0:
        trajectory = "🟠 NEEDS ATTENTION"
    else:
        trajectory = "🟡 STABLE"

    print(f"Trajectory            : {trajectory}")

    print()
    print("=" * 40)
    print("       MANAGEMENT PRIORITIES")
    print("=" * 40)

    priority = 1

    if margin < TARGET_MARGIN:
        print(
            f"{priority}. [HIGH] Improve gross margin "
            f"toward the 10% target."
        )
        priority += 1

    if liquidity_gap > 0:
        print(
            f"{priority}. [HIGH] Address supplier liquidity "
            f"gap of {money(liquidity_gap)}."
        )
        priority += 1

    if data["customer_credit"] > data["liquid_funds"]:
        print(
            f"{priority}. [HIGH] Prioritize customer credit "
            f"collection."
        )
        priority += 1

    if data["active_days"] < 14:
        print(
            f"{priority}. [MEDIUM] Continue collecting sales "
            f"history before relying on long-term forecasts."
        )
        priority += 1

    print()
    print("=" * 40)
    print("       V55 MODULE STATUS")
    print("=" * 40)
    print("Mode                : READ-ONLY")
    print("Database modified   : NO")
    print("Sales modified      : NO")
    print("Products modified   : NO")
    print("Inventory modified  : NO")
    print("Balance modified    : NO")
    print("Credit modified     : NO")
    print("Suppliers modified  : NO")
    print("Expenses modified   : NO")
    print("=" * 40)


if __name__ == "__main__":
    main()
