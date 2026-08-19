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

    # ==============================
    # SALES
    # ==============================
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

    margin = (profit / revenue * 100) if revenue > 0 else 0

    # ==============================
    # SALES ACTIVITY
    # ==============================
    active_days = get_one(conn, """
        SELECT COUNT(DISTINCT substr(sale_date, 1, 10))
        FROM sales
        WHERE status = 'COMPLETED'
    """)

    revenue_per_day = (
        revenue / active_days
        if active_days > 0 else 0
    )

    profit_per_day = (
        profit / active_days
        if active_days > 0 else 0
    )

    # ==============================
    # BALANCE
    # ==============================
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

    liquid_funds = cash + wallet

    # ==============================
    # CUSTOMER CREDIT
    # ==============================
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

    # ==============================
    # SUPPLIER LIABILITY
    # ==============================
    supplier_debt = get_one(conn, """
        SELECT COALESCE(SUM(balance), 0)
        FROM creditors
    """)

    # ==============================
    # INVENTORY
    # ==============================
    inventory_capital = get_one(conn, """
        SELECT COALESCE(SUM(
            buying_price * current_stock
        ), 0)
        FROM products
    """)

    products = int(get_one(conn, """
        SELECT COUNT(*)
        FROM products
    """))

    stock_units = get_one(conn, """
        SELECT COALESCE(SUM(current_stock), 0)
        FROM products
    """)

    # ==============================
    # EXPENSES
    # ==============================
    expenses = get_one(conn, """
        SELECT COALESCE(SUM(amount), 0)
        FROM expenses
    """)

    # ==============================
    # CAPITAL POSITION
    # ==============================
    current_assets = (
        liquid_funds
        + credit_outstanding
        + inventory_capital
    )

    net_position = current_assets - supplier_debt

    # ==============================
    # HEALTH SIGNALS
    # ==============================

    # Profitability
    if margin >= 10:
        profitability_status = "🟢 STRONG"
        profitability_score = 20
    elif margin >= 7:
        profitability_status = "🟡 DEVELOPING"
        profitability_score = 12
    else:
        profitability_status = "🔴 WEAK"
        profitability_score = 5

    # Liquidity
    if liquid_funds >= credit_outstanding:
        liquidity_status = "🟢 STABLE"
        liquidity_score = 20
    elif liquid_funds >= credit_outstanding * 0.5:
        liquidity_status = "🟡 WATCH"
        liquidity_score = 12
    else:
        liquidity_status = "🔴 RISK"
        liquidity_score = 5

    # Credit risk
    if credit_outstanding == 0:
        credit_status = "🟢 LOW"
        credit_score = 20
    elif credit_outstanding <= liquid_funds:
        credit_status = "🟡 MODERATE"
        credit_score = 12
    else:
        credit_status = "🔴 HIGH"
        credit_score = 5

    # Supplier risk
    if supplier_debt == 0:
        supplier_status = "🟢 LOW"
        supplier_score = 20
    elif supplier_debt <= liquid_funds:
        supplier_status = "🟡 MODERATE"
        supplier_score = 12
    else:
        supplier_status = "🔴 HIGH"
        supplier_score = 5

    # Sales activity
    if active_days >= 30:
        activity_status = "🟢 ESTABLISHED"
        activity_score = 20
    elif active_days >= 14:
        activity_status = "🟡 DEVELOPING"
        activity_score = 14
    else:
        activity_status = "🟠 LIMITED DATA"
        activity_score = 8

    health_score = (
        profitability_score
        + liquidity_score
        + credit_score
        + supplier_score
        + activity_score
    )

    if health_score >= 80:
        health_status = "🟢 HEALTHY"
    elif health_score >= 60:
        health_status = "🟡 DEVELOPING"
    elif health_score >= 40:
        health_status = "🟠 MANAGEMENT ATTENTION"
    else:
        health_status = "🔴 HIGH RISK"

    # ==============================
    # REPORT
    # ==============================

    print("=" * 40)
    print("       POS LEDGER NG V53")
    print(" BUSINESS HEALTH & EARLY-WARNING INTELLIGENCE")
    print("=" * 40)

    print("\n" + "=" * 40)
    print("       EXECUTIVE HEALTH SCORE")
    print("=" * 40)

    print(f"Health Score          : {health_score}/100")
    print(f"Overall Health        : {health_status}")

    print("\n" + "=" * 40)
    print("       BUSINESS HEALTH")
    print("=" * 40)

    print(
        f"Profitability         : "
        f"{profitability_status} ({margin:.2f}%)"
    )

    print(
        f"Liquidity             : "
        f"{liquidity_status} ({money(liquid_funds)})"
    )

    print(
        f"Customer Credit      : "
        f"{credit_status} ({money(credit_outstanding)})"
    )

    print(
        f"Supplier Risk         : "
        f"{supplier_status} ({money(supplier_debt)})"
    )

    print(
        f"Sales Activity        : "
        f"{activity_status} ({int(active_days)} days)"
    )

    print("\n" + "=" * 40)
    print("       EXECUTIVE POSITION")
    print("=" * 40)

    print(f"Revenue               : {money(revenue)}")
    print(f"Gross Profit          : {money(profit)}")
    print(f"Gross Margin          : {margin:.2f}%")
    print(f"Completed Sales       : {int(sales_count)}")
    print(f"Units Sold            : {units_sold:.2f}")
    print(f"Revenue / Active Day  : {money(revenue_per_day)}")
    print(f"Profit / Active Day   : {money(profit_per_day)}")

    print("\n" + "=" * 40)
    print("       CAPITAL POSITION")
    print("=" * 40)

    print(f"Liquid Funds          : {money(liquid_funds)}")
    print(f"Customer Credit       : {money(credit_outstanding)}")
    print(f"Inventory Capital     : {money(inventory_capital)}")
    print(f"Supplier Liability    : {money(supplier_debt)}")
    print(f"Net Position          : {money(net_position)}")

    print("\n" + "=" * 40)
    print("       INVENTORY POSITION")
    print("=" * 40)

    print(f"Products              : {products}")
    print(f"Stock Units           : {stock_units:.2f}")
    print(f"Inventory Capital     : {money(inventory_capital)}")

    print("\n" + "=" * 40)
    print("       EARLY WARNING SIGNALS")
    print("=" * 40)

    warnings = []

    if margin < 10:
        warnings.append(
            "[HIGH] Gross margin is below the 10% management target."
        )

    if credit_outstanding > liquid_funds:
        warnings.append(
            "[HIGH] Customer credit exceeds liquid funds."
        )

    if supplier_debt > liquid_funds:
        warnings.append(
            "[MEDIUM] Supplier liability exceeds liquid funds."
        )

    if inventory_capital > liquid_funds * 3:
        warnings.append(
            "[MEDIUM] Significant capital is tied up in inventory."
        )

    if active_days < 14:
        warnings.append(
            "[MEDIUM] Sales history is still limited."
        )

    if expenses == 0:
        warnings.append(
            "[INFO] No recorded business expenses detected."
        )

    if not warnings:
        warnings.append(
            "[INFO] No major early-warning conditions detected."
        )

    for i, warning in enumerate(warnings, 1):
        print(f"{i}. {warning}")

    print("\n" + "=" * 40)
    print("       MANAGEMENT PRIORITIES")
    print("=" * 40)

    priority = 1

    if margin < 10:
        print(
            f"{priority}. [HIGH] Improve product margins "
            "toward the management target."
        )
        priority += 1

    if credit_outstanding > 0:
        print(
            f"{priority}. [HIGH] Monitor and collect "
            "customer credit."
        )
        priority += 1

    if supplier_debt > 0:
        print(
            f"{priority}. [MEDIUM] Track supplier "
            "payment obligations."
        )
        priority += 1

    print(
        f"{priority}. [MEDIUM] Continue collecting "
        "sales history for stronger analytics."
    )

    print("\n" + "=" * 40)
    print("       V53 MODULE STATUS")
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
