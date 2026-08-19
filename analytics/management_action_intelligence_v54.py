import sqlite3

DB = "data/posledger.db"


def money(value):
    return f"₦{value:,.2f}"


def get_one(conn, query, params=()):
    row = conn.execute(query, params).fetchone()
    return float(row[0] or 0) if row else 0.0


def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    # =========================================================
    # SALES
    # =========================================================
    revenue = get_one(conn, """
        SELECT COALESCE(SUM(total_amount), 0)
        FROM sales
        WHERE status = 'COMPLETED'
    """)

    profit = get_one(conn, """
        SELECT COALESCE(SUM(total_profit), 0)
        FROM sales
        WHERE status = 'COMPLETED'
    """)

    sales_count = get_one(conn, """
        SELECT COUNT(*)
        FROM sales
        WHERE status = 'COMPLETED'
    """)

    units_sold = get_one(conn, """
        SELECT COALESCE(SUM(quantity), 0)
        FROM sales
        WHERE status = 'COMPLETED'
    """)

    margin = (profit / revenue * 100) if revenue else 0

    # =========================================================
    # LIQUID FUNDS
    # =========================================================
    cash = get_one(conn, """
        SELECT cash_balance
        FROM balance
        ORDER BY id DESC
        LIMIT 1
    """)

    wallet = get_one(conn, """
        SELECT wallet_balance
        FROM balance
        ORDER BY id DESC
        LIMIT 1
    """)

    liquid = cash + wallet

    # =========================================================
    # CUSTOMER CREDIT
    # =========================================================
    credit_created = get_one(conn, """
        SELECT COALESCE(SUM(total_amount), 0)
        FROM customer_credit
    """)

    credit_paid = get_one(conn, """
        SELECT COALESCE(SUM(amount), 0)
        FROM credit_payments
    """)

    credit_outstanding = max(
        credit_created - credit_paid,
        0
    )

    # =========================================================
    # SUPPLIER LIABILITY
    # =========================================================
    supplier_liability = get_one(conn, """
        SELECT COALESCE(SUM(balance), 0)
        FROM creditors
    """)

    # =========================================================
    # INVENTORY
    # =========================================================
    inventory_capital = get_one(conn, """
        SELECT COALESCE(
            SUM(buying_price * current_stock), 0
        )
        FROM products
    """)

    product_count = int(get_one(conn, """
        SELECT COUNT(*)
        FROM products
    """))

    # =========================================================
    # ACTIVE SALES DAYS
    # =========================================================
    active_days = get_one(conn, """
        SELECT COUNT(DISTINCT substr(sale_date, 1, 10))
        FROM sales
        WHERE status = 'COMPLETED'
    """)

    # =========================================================
    # 10% MARGIN SCENARIO
    # =========================================================
    target_margin = 10.0

    target_profit = revenue * (target_margin / 100)

    additional_profit_needed = max(
        target_profit - profit,
        0
    )

    # =========================================================
    # CREDIT COLLECTION SCENARIO
    # =========================================================
    credit_collection_target = min(
        credit_outstanding,
        max(supplier_liability - liquid, 0)
    )

    liquidity_after_collection = (
        liquid + credit_collection_target
    )

    supplier_gap_before = max(
        supplier_liability - liquid,
        0
    )

    supplier_gap_after = max(
        supplier_liability - liquidity_after_collection,
        0
    )

    # =========================================================
    # PRODUCT INTELLIGENCE
    # =========================================================
    products = conn.execute("""
        SELECT
            p.id,
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
            ), 0) AS units_sold,
            COALESCE(SUM(
                CASE
                    WHEN s.status = 'COMPLETED'
                    THEN s.total_amount
                    ELSE 0
                END
            ), 0) AS revenue,
            COALESCE(SUM(
                CASE
                    WHEN s.status = 'COMPLETED'
                    THEN s.total_profit
                    ELSE 0
                END
            ), 0) AS profit
        FROM products p
        LEFT JOIN sales s
            ON s.product_id = p.id
        GROUP BY p.id
        ORDER BY profit DESC
    """).fetchall()

    # =========================================================
    # PRODUCT SCENARIOS
    # =========================================================
    product_scenarios = []

    for p in products:
        buying = float(p["buying_price"] or 0)
        selling = float(p["selling_price"] or 0)
        units = float(p["units_sold"] or 0)
        stock = float(p["current_stock"] or 0)
        product_profit = float(p["profit"] or 0)

        current_unit_profit = selling - buying

        current_margin = (
            current_unit_profit / selling * 100
            if selling > 0 else 0
        )

        target_price = (
            buying / (1 - target_margin / 100)
            if buying > 0 else 0
        )

        extra_profit_if_target_price = (
            max(target_price - selling, 0) * units
        )

        product_scenarios.append({
            "name": p["product_name"],
            "sku": p["sku"],
            "buying": buying,
            "selling": selling,
            "units": units,
            "stock": stock,
            "profit": product_profit,
            "margin": current_margin,
            "target_price": target_price,
            "extra_profit": extra_profit_if_target_price
        })

    # =========================================================
    # PRIORITY ENGINE
    # =========================================================
    actions = []

    if margin < target_margin:
        actions.append({
            "priority": "HIGH",
            "action": (
                "Improve overall gross margin toward "
                "the 10% management target."
            )
        })

    if supplier_gap_before > 0:
        actions.append({
            "priority": "HIGH",
            "action": (
                f"Address supplier liquidity gap of "
                f"{money(supplier_gap_before)}."
            )
        })

    if credit_outstanding > 0:
        actions.append({
            "priority": "HIGH",
            "action": (
                f"Prioritize customer credit collection "
                f"of {money(credit_outstanding)}."
            )
        })

    if inventory_capital > liquid * 3:
        actions.append({
            "priority": "MEDIUM",
            "action": (
                "Avoid excessive additional inventory "
                "capital until sales data improves."
            )
        })

    if active_days < 14:
        actions.append({
            "priority": "MEDIUM",
            "action": (
                "Continue collecting transaction history "
                "before making aggressive forecasts."
            )
        })

    # =========================================================
    # HEALTH SCENARIO
    # =========================================================
    scenario_score = 50

    if additional_profit_needed == 0:
        scenario_score += 10

    if supplier_gap_before == 0:
        scenario_score += 10

    if credit_outstanding <= liquid:
        scenario_score += 10

    if active_days >= 14:
        scenario_score += 10

    scenario_score = min(scenario_score, 100)

    if scenario_score >= 80:
        scenario_status = "🟢 HEALTHY"
    elif scenario_score >= 60:
        scenario_status = "🟡 DEVELOPING"
    elif scenario_score >= 40:
        scenario_status = "🟠 MANAGEMENT ATTENTION"
    else:
        scenario_status = "🔴 HIGH RISK"

    # =========================================================
    # REPORT
    # =========================================================
    print("=" * 40)
    print("       POS LEDGER NG V54")
    print(" MANAGEMENT ACTION & SCENARIO INTELLIGENCE")
    print("=" * 40)

    print("\n" + "=" * 40)
    print("       CURRENT BUSINESS POSITION")
    print("=" * 40)

    print(f"Revenue               : {money(revenue)}")
    print(f"Gross Profit          : {money(profit)}")
    print(f"Gross Margin          : {margin:.2f}%")
    print(f"Completed Sales       : {int(sales_count)}")
    print(f"Units Sold            : {units_sold:.2f}")
    print(f"Active Sales Days     : {int(active_days)}")

    print("\n" + "=" * 40)
    print("       MANAGEMENT SCENARIOS")
    print("=" * 40)

    print(f"Current Margin        : {margin:.2f}%")
    print(f"Target Margin         : {target_margin:.2f}%")
    print(f"Target Profit         : {money(target_profit)}")
    print(
        f"Additional Profit Needed: "
        f"{money(additional_profit_needed)}"
    )

    print("\n" + "=" * 40)
    print("       LIQUIDITY SCENARIO")
    print("=" * 40)

    print(f"Liquid Funds          : {money(liquid)}")
    print(f"Supplier Liability    : {money(supplier_liability)}")
    print(
        f"Supplier Gap Before   : "
        f"{money(supplier_gap_before)}"
    )

    print(
        f"Suggested Collection  : "
        f"{money(credit_collection_target)}"
    )

    print(
        f"Liquid After Collection: "
        f"{money(liquidity_after_collection)}"
    )

    print(
        f"Supplier Gap After    : "
        f"{money(supplier_gap_after)}"
    )

    print("\n" + "=" * 40)
    print("       CUSTOMER CREDIT SCENARIO")
    print("=" * 40)

    print(f"Credit Outstanding    : {money(credit_outstanding)}")
    print(
        f"Collection Capacity   : "
        f"{money(liquid + credit_outstanding)}"
    )

    if credit_outstanding > liquid:
        print(
            "Credit Recommendation : "
            "🟠 PRIORITIZE COLLECTION"
        )
    else:
        print(
            "Credit Recommendation : "
            "🟢 WITHIN LIQUID CAPACITY"
        )

    print("\n" + "=" * 40)
    print("       PRODUCT PRICING SCENARIOS")
    print("=" * 40)

    for p in product_scenarios:
        print("\n----------------------------------------")
        print(f"Product               : {p['name']}")
        print(f"SKU                   : {p['sku']}")
        print(f"Buying Price          : {money(p['buying'])}")
        print(f"Selling Price         : {money(p['selling'])}")
        print(f"Current Margin        : {p['margin']:.2f}%")
        print(f"Units Sold            : {p['units']:.2f}")
        print(f"Current Stock         : {p['stock']:.2f}")

        if p["margin"] < target_margin:
            print(
                f"Target Selling Price  : "
                f"{money(p['target_price'])}"
            )
            print(
                f"Potential Extra Profit: "
                f"{money(p['extra_profit'])}"
            )
            print(
                "Decision              : "
                "🟠 REVIEW PRICING"
            )
        else:
            print(
                "Decision              : "
                "🟢 MAINTAIN"
            )

    print("\n" + "=" * 40)
    print("       PRIORITIZED MANAGEMENT ACTIONS")
    print("=" * 40)

    if actions:
        for i, item in enumerate(actions, 1):
            print(
                f"{i}. [{item['priority']}] "
                f"{item['action']}"
            )
    else:
        print("No immediate management action detected.")

    print("\n" + "=" * 40)
    print("       SCENARIO HEALTH")
    print("=" * 40)

    print(f"Scenario Score        : {scenario_score}/100")
    print(f"Scenario Status       : {scenario_status}")

    print("\n" + "=" * 40)
    print("       V54 MODULE STATUS")
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

    conn.close()


if __name__ == "__main__":
    main()
