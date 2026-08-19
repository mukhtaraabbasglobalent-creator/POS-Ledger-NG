import sqlite3
from pathlib import Path

DB_PATH = Path("data/posledger.db")


def money(value):
    return f"₦{value:,.2f}"


def get_db():
    return sqlite3.connect(DB_PATH)


def fetch_one(cur, sql, params=()):
    cur.execute(sql, params)
    row = cur.fetchone()
    return row[0] if row and row[0] is not None else 0.0


def main():
    conn = get_db()
    cur = conn.cursor()

    # ==================================================
    # CURRENT BUSINESS POSITION
    # ==================================================

    cash = fetch_one(
        cur,
        "SELECT COALESCE(cash_balance, 0) FROM balance ORDER BY id DESC LIMIT 1"
    )

    wallet = fetch_one(
        cur,
        "SELECT COALESCE(wallet_balance, 0) FROM balance ORDER BY id DESC LIMIT 1"
    )

    liquid = cash + wallet

    revenue = fetch_one(
        cur,
        """
        SELECT COALESCE(SUM(total_amount), 0)
        FROM sales
        WHERE LOWER(COALESCE(status, '')) IN
        ('completed', 'complete', 'paid', 'success', 'successful')
        OR status IS NULL
        """
    )

    # If status filtering produces no result, use all sales.
    if revenue == 0:
        revenue = fetch_one(
            cur,
            "SELECT COALESCE(SUM(total_amount), 0) FROM sales"
        )

    profit = fetch_one(
        cur,
        """
        SELECT COALESCE(SUM(total_profit), 0)
        FROM sales
        WHERE LOWER(COALESCE(status, '')) IN
        ('completed', 'complete', 'paid', 'success', 'successful')
        OR status IS NULL
        """
    )

    if profit == 0:
        profit = fetch_one(
            cur,
            "SELECT COALESCE(SUM(total_profit), 0) FROM sales"
        )

    margin = (profit / revenue * 100) if revenue > 0 else 0.0

    customer_credit = fetch_one(
        cur,
        """
        SELECT COALESCE(SUM(balance), 0)
        FROM customer_credit
        WHERE LOWER(COALESCE(status, '')) NOT IN
        ('paid', 'closed', 'settled')
        """
    )

    if customer_credit == 0:
        customer_credit = fetch_one(
            cur,
            "SELECT COALESCE(SUM(balance), 0) FROM customer_credit"
        )

    supplier_liability = fetch_one(
        cur,
        "SELECT COALESCE(SUM(balance), 0) FROM creditors"
    )

    inventory_capital = fetch_one(
        cur,
        """
        SELECT COALESCE(SUM(current_stock * buying_price), 0)
        FROM products
        """
    )

    expenses = fetch_one(
        cur,
        "SELECT COALESCE(SUM(amount), 0) FROM expenses"
    )

    net_position = (
        liquid
        + customer_credit
        + inventory_capital
        - supplier_liability
    )

    # ==================================================
    # PRODUCT OPTIMIZATION
    # ==================================================

    products = cur.execute(
        """
        SELECT
            id,
            product_name,
            sku,
            buying_price,
            selling_price,
            current_stock
        FROM products
        ORDER BY product_name
        """
    ).fetchall()

    product_data = []

    for row in products:
        (
            product_id,
            product_name,
            sku,
            buying_price,
            selling_price,
            current_stock,
        ) = row

        buying_price = float(buying_price or 0)
        selling_price = float(selling_price or 0)
        current_stock = float(current_stock or 0)

        current_margin = (
            (selling_price - buying_price) / selling_price * 100
            if selling_price > 0
            else 0
        )

        # Units sold from sale_items
        units_sold = fetch_one(
            cur,
            """
            SELECT COALESCE(SUM(quantity), 0)
            FROM sale_items
            WHERE product_id = ?
            """,
            (product_id,)
        )

        # Price required for 10% margin:
        # selling_price - buying_price = 10% of selling_price
        target_price = (
            buying_price / 0.90
            if buying_price > 0
            else selling_price
        )

        extra_profit = max(
            0,
            (target_price - selling_price) * units_sold
        )

        if current_margin < 10:
            decision = "🟠 OPTIMIZE"
        else:
            decision = "🟢 MAINTAIN"

        product_data.append({
            "name": product_name,
            "sku": sku or "-",
            "buying": buying_price,
            "selling": selling_price,
            "margin": current_margin,
            "units": units_sold,
            "stock": current_stock,
            "target": target_price,
            "extra_profit": extra_profit,
            "decision": decision,
        })

    # ==================================================
    # SCENARIO ENGINE
    # ==================================================

    target_margin = 10.0

    def scenario(
        name,
        revenue_s,
        profit_s,
        margin_s,
        liquid_s,
        credit_s,
        supplier_s,
    ):
        supplier_gap = max(0, supplier_s - liquid_s)

        # Score components
        margin_score = min(30, (margin_s / target_margin) * 30)

        liquidity_score = min(
            25,
            (liquid_s / max(supplier_s, 1)) * 25
        )

        credit_score = 20 if credit_s <= 0 else max(
            0,
            20 - (credit_s / max(revenue_s, 1) * 20)
        )

        profit_score = min(
            25,
            (profit_s / max(revenue_s * 0.10, 1)) * 25
        )

        score = min(
            100,
            margin_score
            + liquidity_score
            + credit_score
            + profit_score
        )

        return {
            "name": name,
            "revenue": revenue_s,
            "profit": profit_s,
            "margin": margin_s,
            "liquid": liquid_s,
            "credit": credit_s,
            "supplier": supplier_s,
            "gap": supplier_gap,
            "net": (
                liquid_s
                + credit_s
                + inventory_capital
                - supplier_s
            ),
            "score": score,
        }

    scenarios = []

    # Current
    scenarios.append(
        scenario(
            "CURRENT STRATEGY",
            revenue,
            profit,
            margin,
            liquid,
            customer_credit,
            supplier_liability,
        )
    )

    # Sales scenarios
    for pct in (10, 20, 30):
        factor = 1 + pct / 100

        revenue_s = revenue * factor
        profit_s = profit * factor

        # Conservative credit collection assumptions
        credit_collected = min(
            customer_credit,
            customer_credit * pct / 40
        )

        liquid_s = liquid + credit_collected
        credit_s = customer_credit - credit_collected

        scenarios.append(
            scenario(
                f"+{pct}% SALES",
                revenue_s,
                profit_s,
                margin,
                liquid_s,
                credit_s,
                supplier_liability,
            )
        )

    # ==================================================
    # PRICING OPTIMIZATION
    # ==================================================

    pricing_profit = profit

    for p in product_data:
        if p["units"] > 0 and p["margin"] < target_margin:
            pricing_profit += p["extra_profit"]

    pricing_margin = (
        pricing_profit / revenue * 100
        if revenue > 0
        else 0
    )

    # Conservative liquidity assumption:
    # collect 50% of outstanding credit
    credit_collection = customer_credit * 0.50

    pricing_liquid = liquid + credit_collection
    pricing_credit = customer_credit - credit_collection

    scenarios.append(
        scenario(
            "PRICING OPTIMIZATION",
            revenue,
            pricing_profit,
            pricing_margin,
            pricing_liquid,
            pricing_credit,
            supplier_liability,
        )
    )

    # Pricing + 20% sales
    revenue_p20 = revenue * 1.20
    profit_p20 = pricing_profit * 1.20

    scenarios.append(
        scenario(
            "PRICING +20% SALES",
            revenue_p20,
            profit_p20,
            (
                profit_p20 / revenue_p20 * 100
                if revenue_p20 > 0
                else 0
            ),
            pricing_liquid,
            pricing_credit,
            supplier_liability,
        )
    )

    # Pricing + full credit collection
    full_credit_liquid = liquid + customer_credit

    scenarios.append(
        scenario(
            "PRICING + CREDIT COLLECTION",
            revenue,
            pricing_profit,
            pricing_margin,
            full_credit_liquid,
            0,
            supplier_liability,
        )
    )

    # Full optimization
    scenarios.append(
        scenario(
            "FULL OPTIMIZATION",
            revenue_p20,
            profit_p20,
            (
                profit_p20 / revenue_p20 * 100
                if revenue_p20 > 0
                else 0
            ),
            full_credit_liquid,
            0,
            supplier_liability,
        )
    )

    scenarios.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    best = scenarios[0]

    # ==================================================
    # DISPLAY
    # ==================================================

    print("=" * 56)
    print("       POS LEDGER NG V57")
    print("       MANAGEMENT OPTIMIZATION INTELLIGENCE")
    print("=" * 56)

    print("\n" + "=" * 56)
    print("       CURRENT BUSINESS POSITION")
    print("=" * 56)

    print(f"Revenue              : {money(revenue)}")
    print(f"Gross Profit         : {money(profit)}")
    print(f"Gross Margin         : {margin:.2f}%")
    print(f"Liquid Funds         : {money(liquid)}")
    print(f"Customer Credit      : {money(customer_credit)}")
    print(f"Supplier Liability   : {money(supplier_liability)}")
    print(f"Inventory Capital    : {money(inventory_capital)}")
    print(f"Recorded Expenses    : {money(expenses)}")

    print("\n" + "=" * 56)
    print("       SCENARIO RANKING")
    print("=" * 56)

    for i, s in enumerate(scenarios, 1):
        print(
            f"{i}. {s['name']:<30} "
            f"{s['score']:.2f}/100"
        )

    print("\n" + "=" * 56)
    print("       OPTIMIZATION SCENARIOS")
    print("=" * 56)

    for s in scenarios:
        print("\n" + "-" * 40)
        print(f"Scenario             : {s['name']}")
        print(f"Revenue              : {money(s['revenue'])}")
        print(f"Profit               : {money(s['profit'])}")
        print(f"Margin               : {s['margin']:.2f}%")
        print(f"Liquid Funds         : {money(s['liquid'])}")
        print(f"Customer Credit      : {money(s['credit'])}")
        print(f"Supplier Liability   : {money(s['supplier'])}")
        print(f"Supplier Gap         : {money(s['gap'])}")
        print(f"Net Position         : {money(s['net'])}")
        print(f"Decision Score       : {s['score']:.2f}/100")

    print("\n" + "=" * 56)
    print("       PRODUCT OPTIMIZATION")
    print("=" * 56)

    if product_data:
        for p in product_data:
            print("\n" + "-" * 40)
            print(f"Product              : {p['name']}")
            print(f"SKU                  : {p['sku']}")
            print(f"Buying Price         : {money(p['buying'])}")
            print(f"Selling Price        : {money(p['selling'])}")
            print(f"Current Margin       : {p['margin']:.2f}%")
            print(f"Units Sold           : {p['units']:.2f}")
            print(f"Current Stock        : {p['stock']:.2f}")

            if p["margin"] < target_margin:
                print(
                    f"Target Selling Price : "
                    f"{money(p['target'])}"
                )
                print(
                    f"Potential Extra Profit: "
                    f"{money(p['extra_profit'])}"
                )

            print(f"Decision              : {p['decision']}")
    else:
        print("No products found.")

    print("\n" + "=" * 56)
    print("       OPTIMAL MANAGEMENT STRATEGY")
    print("=" * 56)

    print(f"Recommended Strategy : {best['name']}")
    print(f"Optimization Score   : {best['score']:.2f}/100")
    print(f"Projected Revenue    : {money(best['revenue'])}")
    print(f"Projected Profit     : {money(best['profit'])}")
    print(f"Projected Margin     : {best['margin']:.2f}%")
    print(f"Projected Liquidity  : {money(best['liquid'])}")
    print(f"Remaining Credit     : {money(best['credit'])}")
    print(f"Supplier Gap         : {money(best['gap'])}")
    print(f"Projected Net Position: {money(best['net'])}")

    print("\n" + "=" * 56)
    print("       MANAGEMENT ACTION PLAN")
    print("=" * 56)

    actions = []

    if margin < target_margin:
        actions.append(
            "[HIGH] Improve low-margin product pricing."
        )

    if customer_credit > 0:
        actions.append(
            "[HIGH] Prioritize customer credit collection."
        )

    if supplier_liability > liquid:
        actions.append(
            "[HIGH] Protect liquidity before supplier settlement."
        )

    actions.append(
        "[MEDIUM] Increase sales volume gradually."
    )

    actions.append(
        "[MEDIUM] Continue collecting transaction history."
    )

    for i, action in enumerate(actions, 1):
        print(f"{i}. {action}")

    print("\n" + "=" * 56)
    print("       V57 MODULE STATUS")
    print("=" * 56)
    print("Mode                : READ-ONLY")
    print("Database modified   : NO")
    print("Sales modified      : NO")
    print("Products modified   : NO")
    print("Inventory modified  : NO")
    print("Balance modified    : NO")
    print("Credit modified     : NO")
    print("Suppliers modified  : NO")
    print("Expenses modified   : NO")
    print("=" * 56)

    conn.close()


if __name__ == "__main__":
    main()
