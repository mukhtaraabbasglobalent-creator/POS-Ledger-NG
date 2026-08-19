import sqlite3

DB_PATH = "data/posledger.db"

TARGET_MARGIN = 0.10


def money(value):
    return f"₦{value:,.2f}"


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def scalar(conn, query, params=()):
    row = conn.execute(query, params).fetchone()
    return float(row[0] or 0) if row else 0.0


def load_position(conn):
    revenue = scalar(
        conn,
        """
        SELECT COALESCE(SUM(total_amount),0)
        FROM sales
        WHERE status='COMPLETED'
        """
    )

    profit = scalar(
        conn,
        """
        SELECT COALESCE(SUM(total_profit),0)
        FROM sales
        WHERE status='COMPLETED'
        """
    )

    units = scalar(
        conn,
        """
        SELECT COALESCE(SUM(quantity),0)
        FROM sales
        WHERE status='COMPLETED'
        """
    )

    active_days = scalar(
        conn,
        """
        SELECT COUNT(DISTINCT date(sale_date))
        FROM sales
        WHERE status='COMPLETED'
        """
    )

    liquid = scalar(
        conn,
        """
        SELECT COALESCE(cash_balance,0)
             + COALESCE(wallet_balance,0)
        FROM balance
        LIMIT 1
        """
    )

    credit = scalar(
        conn,
        """
        SELECT COALESCE(SUM(balance),0)
        FROM customer_credit
        WHERE balance > 0
        """
    )

    supplier = scalar(
        conn,
        """
        SELECT COALESCE(SUM(balance),0)
        FROM creditors
        WHERE balance > 0
        """
    )

    return {
        "revenue": revenue,
        "profit": profit,
        "units": units,
        "active_days": active_days,
        "liquid": liquid,
        "credit": credit,
        "supplier": supplier,
    }


def product_data(conn):
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
                    WHEN s.status='COMPLETED'
                    THEN s.quantity
                    ELSE 0
                END
            ),0) AS units_sold
        FROM products p
        LEFT JOIN sales s
            ON s.product_id=p.id
        GROUP BY p.id
        ORDER BY units_sold DESC
        """
    ).fetchall()

    result = []

    for r in rows:
        buying = float(r["buying_price"] or 0)
        selling = float(r["selling_price"] or 0)
        units = float(r["units_sold"] or 0)

        if buying <= 0 or selling <= 0:
            continue

        margin = (selling - buying) / selling

        target_price = buying / (1 - TARGET_MARGIN)

        result.append({
            "name": r["product_name"],
            "sku": r["sku"],
            "buying": buying,
            "selling": selling,
            "units": units,
            "stock": float(r["current_stock"] or 0),
            "margin": margin,
            "target_price": target_price,
        })

    return result


def simulate(position, sales_growth, collection_rate, price_adjustment):
    revenue = position["revenue"]
    profit = position["profit"]

    # Sales volume/revenue scenario
    projected_revenue = revenue * (1 + sales_growth)

    # Existing profit margin
    current_margin = profit / revenue if revenue else 0

    # Pricing effect
    projected_margin = current_margin + price_adjustment

    # Keep margin within reasonable limits
    projected_margin = max(0, min(projected_margin, 0.50))

    projected_profit = projected_revenue * projected_margin

    # Customer-credit collection
    collected_credit = position["credit"] * collection_rate

    projected_liquid = position["liquid"] + collected_credit

    supplier_gap = max(
        0,
        position["supplier"] - projected_liquid
    )

    return {
        "revenue": projected_revenue,
        "margin": projected_margin,
        "profit": projected_profit,
        "credit_collected": collected_credit,
        "liquid": projected_liquid,
        "supplier_gap": supplier_gap,
    }


def score(s):
    score = 50

    if s["margin"] >= TARGET_MARGIN:
        score += 20
    elif s["margin"] >= 0.08:
        score += 10
    else:
        score -= 10

    if s["supplier_gap"] == 0:
        score += 15
    elif s["supplier_gap"] < 2000:
        score += 5
    else:
        score -= 10

    if s["credit_collected"] > 0:
        score += 5

    if s["profit"] > 0:
        score += 10

    return max(0, min(100, score))


def main():
    conn = db()

    try:
        position = load_position(conn)
        products = product_data(conn)
    finally:
        conn.close()

    print("=" * 40)
    print("       POS LEDGER NG V56")
    print(" BUSINESS DECISION & WHAT-IF SIMULATOR")
    print("=" * 40)

    print()
    print("=" * 40)
    print("       CURRENT BASELINE")
    print("=" * 40)

    current_margin = (
        position["profit"] / position["revenue"]
        if position["revenue"] else 0
    )

    print(f"Revenue              : {money(position['revenue'])}")
    print(f"Gross Profit         : {money(position['profit'])}")
    print(f"Gross Margin         : {current_margin * 100:.2f}%")
    print(f"Liquid Funds         : {money(position['liquid'])}")
    print(f"Customer Credit      : {money(position['credit'])}")
    print(f"Supplier Liability   : {money(position['supplier'])}")

    print()
    print("=" * 40)
    print("       SCENARIO A — +10% SALES")
    print("=" * 40)

    a = simulate(
        position,
        sales_growth=0.10,
        collection_rate=0.25,
        price_adjustment=0
    )

    print(f"Projected Revenue    : {money(a['revenue'])}")
    print(f"Projected Profit     : {money(a['profit'])}")
    print(f"Projected Margin     : {a['margin'] * 100:.2f}%")
    print(f"Credit Collected     : {money(a['credit_collected'])}")
    print(f"Projected Liquidity  : {money(a['liquid'])}")
    print(f"Supplier Gap         : {money(a['supplier_gap'])}")
    print(f"Scenario Score       : {score(a)}/100")

    print()
    print("=" * 40)
    print("       SCENARIO B — +20% SALES")
    print("=" * 40)

    b = simulate(
        position,
        sales_growth=0.20,
        collection_rate=0.50,
        price_adjustment=0
    )

    print(f"Projected Revenue    : {money(b['revenue'])}")
    print(f"Projected Profit     : {money(b['profit'])}")
    print(f"Projected Margin     : {b['margin'] * 100:.2f}%")
    print(f"Credit Collected     : {money(b['credit_collected'])}")
    print(f"Projected Liquidity  : {money(b['liquid'])}")
    print(f"Supplier Gap         : {money(b['supplier_gap'])}")
    print(f"Scenario Score       : {score(b)}/100")

    print()
    print("=" * 40)
    print("       SCENARIO C — +30% SALES")
    print("=" * 40)

    c = simulate(
        position,
        sales_growth=0.30,
        collection_rate=0.75,
        price_adjustment=0
    )

    print(f"Projected Revenue    : {money(c['revenue'])}")
    print(f"Projected Profit     : {money(c['profit'])}")
    print(f"Projected Margin     : {c['margin'] * 100:.2f}%")
    print(f"Credit Collected     : {money(c['credit_collected'])}")
    print(f"Projected Liquidity  : {money(c['liquid'])}")
    print(f"Supplier Gap         : {money(c['supplier_gap'])}")
    print(f"Scenario Score       : {score(c)}/100")

    print()
    print("=" * 40)
    print("       SCENARIO D — 10% MARGIN")
    print("=" * 40)

    target_profit = position["revenue"] * TARGET_MARGIN
    extra_profit = target_profit - position["profit"]

    d = simulate(
        position,
        sales_growth=0,
        collection_rate=0.50,
        price_adjustment=TARGET_MARGIN - current_margin
    )

    print(f"Target Margin        : {TARGET_MARGIN * 100:.2f}%")
    print(f"Target Profit        : {money(target_profit)}")
    print(f"Extra Profit Needed  : {money(max(0, extra_profit))}")
    print(f"Scenario Profit      : {money(d['profit'])}")
    print(f"Projected Liquidity  : {money(d['liquid'])}")
    print(f"Supplier Gap         : {money(d['supplier_gap'])}")
    print(f"Scenario Score       : {score(d)}/100")

    print()
    print("=" * 40)
    print("       PRODUCT DECISION ENGINE")
    print("=" * 40)

    for p in products:
        print()
        print("-" * 40)
        print(f"Product              : {p['name']}")
        print(f"SKU                  : {p['sku']}")
        print(f"Current Price        : {money(p['selling'])}")
        print(f"Current Margin       : {p['margin'] * 100:.2f}%")

        if p["margin"] < TARGET_MARGIN:
            print(
                f"Suggested Price      : "
                f"{money(p['target_price'])}"
            )
            print("Decision              : 🟠 PRICING REVIEW")
        else:
            print("Decision              : 🟢 MAINTAIN")

    print()
    print("=" * 40)
    print("       RECOMMENDED DECISION")
    print("=" * 40)

    scenarios = {
        "A +10% SALES": a,
        "B +20% SALES": b,
        "C +30% SALES": c,
        "D 10% MARGIN": d,
    }

    best_name = max(
        scenarios,
        key=lambda name: score(scenarios[name])
    )

    best = scenarios[best_name]

    print(f"Best Scenario       : {best_name}")
    print(f"Decision Score      : {score(best)}/100")
    print(f"Projected Revenue   : {money(best['revenue'])}")
    print(f"Projected Profit    : {money(best['profit'])}")
    print(f"Projected Liquidity : {money(best['liquid'])}")
    print(f"Supplier Gap        : {money(best['supplier_gap'])}")

    print()
    print("=" * 40)
    print("       MANAGEMENT RECOMMENDATION")
    print("=" * 40)

    if current_margin < TARGET_MARGIN:
        print("1. [HIGH] Improve low-margin product pricing.")

    if position["supplier"] > position["liquid"]:
        print("2. [HIGH] Increase liquidity before supplier settlement.")

    if position["credit"] > 0:
        print("3. [HIGH] Continue customer credit collection.")

    print("4. [MEDIUM] Increase sales volume gradually.")
    print("5. [MEDIUM] Avoid aggressive decisions while data is limited.")

    print()
    print("=" * 40)
    print("       V56 MODULE STATUS")
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
