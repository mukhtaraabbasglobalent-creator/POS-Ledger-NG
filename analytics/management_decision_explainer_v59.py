import sqlite3
from pathlib import Path
from dataclasses import dataclass


DB_PATH = Path("data/posledger.db")
TARGET_MARGIN = 0.10


@dataclass
class Scenario:
    name: str
    revenue: float
    profit: float
    margin: float
    liquidity: float
    credit: float
    supplier_gap: float

    score: float = 0.0
    confidence: float = 0.0
    risk: str = "UNKNOWN"
    risk_score: float = 0.0
    reason: str = ""


def money(value):
    return f"₦{value:,.2f}"


def get_connection():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    return sqlite3.connect(DB_PATH)


def table_exists(conn, table):
    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        AND name = ?
        """,
        (table,),
    ).fetchone()

    return row is not None


def column_exists(conn, table, column):
    if not table_exists(conn, table):
        return False

    rows = conn.execute(
        f"PRAGMA table_info({table})"
    ).fetchall()

    return any(row[1] == column for row in rows)


def safe_sum(conn, table, column):
    if not column_exists(conn, table, column):
        return 0.0

    try:
        row = conn.execute(
            f"""
            SELECT COALESCE(SUM({column}), 0)
            FROM {table}
            """
        ).fetchone()

        return float(row[0] or 0)

    except sqlite3.Error:
        return 0.0


def get_latest_balance(conn):
    cash = 0.0
    wallet = 0.0

    if not table_exists(conn, "balance"):
        return 0.0

    try:
        columns = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(balance)"
            ).fetchall()
        }

        if "cash_balance" not in columns:
            return 0.0

        if "wallet_balance" not in columns:
            return 0.0

        order_column = "id" if "id" in columns else None

        if order_column:
            query = """
                SELECT
                    COALESCE(cash_balance, 0),
                    COALESCE(wallet_balance, 0)
                FROM balance
                ORDER BY id DESC
                LIMIT 1
            """
        else:
            query = """
                SELECT
                    COALESCE(cash_balance, 0),
                    COALESCE(wallet_balance, 0)
                FROM balance
                LIMIT 1
            """

        row = conn.execute(query).fetchone()

        if row:
            cash = float(row[0] or 0)
            wallet = float(row[1] or 0)

    except sqlite3.Error:
        pass

    return cash + wallet


def get_inventory_capital(conn):
    if not table_exists(conn, "products"):
        return 0.0

    required = {
        "buying_price",
        "current_stock",
    }

    columns = {
        row[1]
        for row in conn.execute(
            "PRAGMA table_info(products)"
        ).fetchall()
    }

    if not required.issubset(columns):
        return 0.0

    try:
        row = conn.execute(
            """
            SELECT COALESCE(
                SUM(buying_price * current_stock),
                0
            )
            FROM products
            """
        ).fetchone()

        return float(row[0] or 0)

    except sqlite3.Error:
        return 0.0


def get_baseline(conn):
    revenue = safe_sum(
        conn,
        "sales",
        "total_amount",
    )

    profit = safe_sum(
        conn,
        "sales",
        "total_profit",
    )

    # Fallback to transactions if sales data is unavailable.
    if revenue <= 0:
        revenue = safe_sum(
            conn,
            "transactions",
            "amount",
        )

    if profit <= 0:
        profit = safe_sum(
            conn,
            "transactions",
            "profit",
        )

    margin = (
        profit / revenue
        if revenue > 0
        else 0.0
    )

    liquid = get_latest_balance(conn)

    credit = safe_sum(
        conn,
        "customer_credit",
        "balance",
    )

    if credit <= 0:
        credit = safe_sum(
            conn,
            "customer_credit",
            "remaining_balance",
        )

    supplier = safe_sum(
        conn,
        "creditors",
        "balance",
    )

    if supplier <= 0:
        supplier = safe_sum(
            conn,
            "creditors",
            "amount_due",
        )

    inventory = get_inventory_capital(conn)

    expenses = safe_sum(
        conn,
        "expenses",
        "amount",
    )

    return {
        "revenue": revenue,
        "profit": profit,
        "margin": margin,
        "liquid": liquid,
        "credit": credit,
        "supplier": supplier,
        "inventory": inventory,
        "expenses": expenses,
    }


def build_scenarios(base):
    revenue = base["revenue"]
    profit = base["profit"]
    margin = base["margin"]
    liquid = base["liquid"]
    credit = base["credit"]
    supplier = base["supplier"]

    scenarios = []

    # -------------------------------------------------
    # CURRENT STRATEGY
    # -------------------------------------------------

    scenarios.append(
        Scenario(
            name="CURRENT STRATEGY",
            revenue=revenue,
            profit=profit,
            margin=margin,
            liquidity=liquid,
            credit=credit,
            supplier_gap=max(
                supplier - liquid,
                0,
            ),
        )
    )

    # -------------------------------------------------
    # SALES GROWTH SCENARIOS
    # -------------------------------------------------

    for pct in (0.10, 0.20, 0.30):
        new_revenue = revenue * (1 + pct)
        new_profit = profit * (1 + pct)

        # Conservative assumption:
        # only a percentage of outstanding credit
        # is collected.
        collection = credit * pct

        new_credit = max(
            credit - collection,
            0,
        )

        new_liquid = liquid + collection

        supplier_gap = max(
            supplier - new_liquid,
            0,
        )

        scenarios.append(
            Scenario(
                name=f"+{int(pct * 100)}% SALES",
                revenue=new_revenue,
                profit=new_profit,
                margin=margin,
                liquidity=new_liquid,
                credit=new_credit,
                supplier_gap=supplier_gap,
            )
        )

    # -------------------------------------------------
    # PRICING OPTIMIZATION
    # -------------------------------------------------

    pricing_profit = revenue * TARGET_MARGIN

    pricing_extra = max(
        pricing_profit - profit,
        0,
    )

    pricing_liquid = (
        liquid + credit * 0.50
    )

    pricing_credit = credit * 0.50

    pricing_gap = max(
        supplier - pricing_liquid,
        0,
    )

    scenarios.append(
        Scenario(
            name="PRICING OPTIMIZATION",
            revenue=revenue,
            profit=profit + pricing_extra,
            margin=TARGET_MARGIN,
            liquidity=pricing_liquid,
            credit=pricing_credit,
            supplier_gap=pricing_gap,
        )
    )

    # -------------------------------------------------
    # PRICING + 20% SALES
    # -------------------------------------------------

    p20_revenue = revenue * 1.20
    p20_profit = p20_revenue * TARGET_MARGIN

    p20_collection = credit * 0.50
    p20_credit = max(
        credit - p20_collection,
        0,
    )

    p20_liquid = (
        liquid + p20_collection
    )

    p20_gap = max(
        supplier - p20_liquid,
        0,
    )

    scenarios.append(
        Scenario(
            name="PRICING +20% SALES",
            revenue=p20_revenue,
            profit=p20_profit,
            margin=TARGET_MARGIN,
            liquidity=p20_liquid,
            credit=p20_credit,
            supplier_gap=p20_gap,
        )
    )

    # -------------------------------------------------
    # PRICING + CREDIT COLLECTION
    # -------------------------------------------------

    collection_liquid = (
        liquid + credit
    )

    collection_gap = max(
        supplier - collection_liquid,
        0,
    )

    scenarios.append(
        Scenario(
            name="PRICING + CREDIT COLLECTION",
            revenue=revenue,
            profit=profit + pricing_extra,
            margin=TARGET_MARGIN,
            liquidity=collection_liquid,
            credit=0.0,
            supplier_gap=collection_gap,
        )
    )

    # -------------------------------------------------
    # FULL OPTIMIZATION
    # -------------------------------------------------

    full_revenue = revenue * 1.20
    full_profit = (
        full_revenue * TARGET_MARGIN
    )

    full_liquid = liquid + credit

    full_gap = max(
        supplier - full_liquid,
        0,
    )

    scenarios.append(
        Scenario(
            name="FULL OPTIMIZATION",
            revenue=full_revenue,
            profit=full_profit,
            margin=TARGET_MARGIN,
            liquidity=full_liquid,
            credit=0.0,
            supplier_gap=full_gap,
        )
    )

    return scenarios


def score_scenario(s, base):
    # -------------------------------------------------
    # MARGIN SCORE
    # Maximum: 30
    # -------------------------------------------------

    if TARGET_MARGIN > 0:
        margin_ratio = (
            s.margin / TARGET_MARGIN
        )
    else:
        margin_ratio = 0.0

    margin_score = min(
        max(margin_ratio, 0.0),
        1.0,
    ) * 30

    # -------------------------------------------------
    # LIQUIDITY SCORE
    # Maximum: 25
    # -------------------------------------------------

    if base["supplier"] > 0:
        liquidity_ratio = (
            s.liquidity
            / base["supplier"]
        )
    else:
        liquidity_ratio = 1.0

    liquidity_score = min(
        max(liquidity_ratio, 0.0),
        1.0,
    ) * 25

    # -------------------------------------------------
    # CREDIT SCORE
    # Maximum: 20
    # -------------------------------------------------

    if base["credit"] > 0:
        remaining_credit_ratio = (
            s.credit
            / base["credit"]
        )

        credit_score = (
            1
            - min(
                max(
                    remaining_credit_ratio,
                    0.0,
                ),
                1.0,
            )
        ) * 20
    else:
        credit_score = 20.0

    # -------------------------------------------------
    # SUPPLIER SCORE
    # Maximum: 15
    # -------------------------------------------------

    if base["supplier"] > 0:
        supplier_ratio = (
            s.supplier_gap
            / base["supplier"]
        )

        supplier_score = (
            1
            - min(
                max(
                    supplier_ratio,
                    0.0,
                ),
                1.0,
            )
        ) * 15
    else:
        supplier_score = 15.0

    # -------------------------------------------------
    # PROFIT SCORE
    # Maximum: 10
    # -------------------------------------------------

    if base["profit"] > 0:
        profit_ratio = (
            s.profit
            / (base["profit"] * 2)
        )

        profit_score = min(
            max(profit_ratio, 0.0),
            1.0,
        ) * 10
    else:
        profit_score = 10.0

    s.score = min(
        margin_score
        + liquidity_score
        + credit_score
        + supplier_score
        + profit_score,
        100.0,
    )


def confidence_and_risk(s, base):
    confidence = 100.0
    risk_factors = []

    # -------------------------------------------------
    # DATA QUALITY
    # -------------------------------------------------

    if base["revenue"] < 50000:
        confidence -= 15
        risk_factors.append(
            "LIMITED SALES DATA"
        )

    # -------------------------------------------------
    # MARGIN
    # -------------------------------------------------

    if s.margin < TARGET_MARGIN:
        confidence -= 10
        risk_factors.append(
            "LOW MARGIN"
        )

    # -------------------------------------------------
    # AGGRESSIVE GROWTH
    # -------------------------------------------------

    if s.name in (
        "+30% SALES",
        "FULL OPTIMIZATION",
    ):
        confidence -= 15
        risk_factors.append(
            "AGGRESSIVE GROWTH ASSUMPTION"
        )

    # -------------------------------------------------
    # PRICING DEPENDENCY
    # -------------------------------------------------

    if "PRICING" in s.name:
        confidence -= 5
        risk_factors.append(
            "PRICE CHANGE REQUIRED"
        )

    # -------------------------------------------------
    # CREDIT COLLECTION
    # -------------------------------------------------

    if (
        "CREDIT" in s.name
        or s.credit < base["credit"]
    ):
        confidence -= 5
        risk_factors.append(
            "COLLECTION EXECUTION REQUIRED"
        )

    # -------------------------------------------------
    # SUPPLIER EXPOSURE
    # -------------------------------------------------

    if s.supplier_gap > 0:
        confidence -= 10
        risk_factors.append(
            "SUPPLIER GAP REMAINS"
        )

    confidence = max(
        0.0,
        min(confidence, 100.0),
    )

    # -------------------------------------------------
    # RISK SCORE
    #
    # Base risk comes from lack of confidence.
    # -------------------------------------------------

    risk_score = (
        100.0 - confidence
    )

    # Additional financial risk.
    if s.supplier_gap > 0:
        risk_score += 5

    if s.margin < 0.05:
        risk_score += 10

    risk_score = max(
        0.0,
        min(risk_score, 100.0),
    )

    if risk_score <= 20:
        risk_level = "🟢 LOW"
    elif risk_score <= 40:
        risk_level = "🟡 MODERATE"
    elif risk_score <= 60:
        risk_level = "🟠 HIGH"
    else:
        risk_level = "🔴 VERY HIGH"

    s.confidence = confidence
    s.risk_score = risk_score
    s.risk = risk_level

    if risk_factors:
        s.reason = ", ".join(
            risk_factors
        )
    else:
        s.reason = "LOW ASSUMPTION RISK"


def tie_break_key(s):
    return (
        round(s.score, 4),
        round(s.profit, 2),
        round(s.liquidity, 2),
        -round(s.credit, 2),
        -round(s.supplier_gap, 2),
    )


def print_report(base, scenarios):
    for scenario in scenarios:
        score_scenario(
            scenario,
            base,
        )

        confidence_and_risk(
            scenario,
            base,
        )

    ranked = sorted(
        scenarios,
        key=tie_break_key,
        reverse=True,
    )

    best = ranked[0]

    print("=" * 60)
    print("POS LEDGER NG V59")
    print("MANAGEMENT DECISION EXPLAINER")
    print("=" * 60)

    print("\n" + "=" * 60)
    print("CURRENT BUSINESS POSITION")
    print("=" * 60)

    print(
        f"Revenue              : "
        f"{money(base['revenue'])}"
    )

    print(
        f"Gross Profit         : "
        f"{money(base['profit'])}"
    )

    print(
        f"Gross Margin         : "
        f"{base['margin'] * 100:.2f}%"
    )

    print(
        f"Liquid Funds         : "
        f"{money(base['liquid'])}"
    )

    print(
        f"Customer Credit      : "
        f"{money(base['credit'])}"
    )

    print(
        f"Supplier Liability   : "
        f"{money(base['supplier'])}"
    )

    print(
        f"Inventory Capital    : "
        f"{money(base['inventory'])}"
    )

    print(
        f"Recorded Expenses    : "
        f"{money(base['expenses'])}"
    )

    print("\n" + "=" * 60)
    print("DECISION RANKING")
    print("=" * 60)

    for index, scenario in enumerate(
        ranked,
        1,
    ):
        print(
            f"{index}. "
            f"{scenario.name:<30} "
            f"{scenario.score:>6.2f}/100"
        )

    print("\n" + "=" * 60)
    print("CONFIDENCE & RISK ANALYSIS")
    print("=" * 60)

    for scenario in ranked:
        print("-" * 40)

        print(
            f"Scenario          : "
            f"{scenario.name}"
        )

        print(
            f"Decision Score    : "
            f"{scenario.score:.2f}/100"
        )

        print(
            f"Confidence        : "
            f"{scenario.confidence:.2f}%"
        )

        print(
            f"Risk              : "
            f"{scenario.risk}"
        )

        print(
            f"Risk Score        : "
            f"{scenario.risk_score:.2f}/100"
        )

        print(
            f"Projected Profit  : "
            f"{money(scenario.profit)}"
        )

        print(
            f"Projected Margin  : "
            f"{scenario.margin * 100:.2f}%"
        )

        print(
            f"Projected Liquidity: "
            f"{money(scenario.liquidity)}"
        )

        print(
            f"Remaining Credit  : "
            f"{money(scenario.credit)}"
        )

        print(
            f"Supplier Gap      : "
            f"{money(scenario.supplier_gap)}"
        )

        print(
            f"Risk Factors      : "
            f"{scenario.reason}"
        )

    print("\n" + "=" * 60)
    print("RECOMMENDED DECISION")
    print("=" * 60)

    print(
        f"Strategy           : "
        f"{best.name}"
    )

    print(
        f"Decision Score     : "
        f"{best.score:.2f}/100"
    )

    print(
        f"Confidence         : "
        f"{best.confidence:.2f}%"
    )

    print(
        f"Risk               : "
        f"{best.risk}"
    )

    print(
        f"Projected Revenue  : "
        f"{money(best.revenue)}"
    )

    print(
        f"Projected Profit   : "
        f"{money(best.profit)}"
    )

    print(
        f"Projected Margin   : "
        f"{best.margin * 100:.2f}%"
    )

    print(
        f"Projected Liquidity: "
        f"{money(best.liquidity)}"
    )

    print(
        f"Remaining Credit   : "
        f"{money(best.credit)}"
    )

    print(
        f"Supplier Gap       : "
        f"{money(best.supplier_gap)}"
    )

    print("\n" + "=" * 60)
    print("DECISION EXPLANATION")
    print("=" * 60)

    if best.name == "FULL OPTIMIZATION":
        print(
            "The model prefers FULL OPTIMIZATION "
            "because it combines margin improvement, "
            "controlled sales growth and credit "
            "collection."
        )

    elif best.name == "PRICING + CREDIT COLLECTION":
        print(
            "The model prefers pricing improvement "
            "and credit collection because these "
            "improve profitability and liquidity "
            "without requiring aggressive sales "
            "growth."
        )

    elif best.name == "PRICING OPTIMIZATION":
        print(
            "The model prefers pricing optimization "
            "because the current margin is below the "
            "target margin."
        )

    else:
        print(
            "The model selected the highest-scoring "
            "scenario after considering profitability, "
            "liquidity, customer credit and supplier "
            "exposure."
        )

    print("\n" + "=" * 60)
    print("V59 SAFETY STATUS")
    print("=" * 60)

    print("Mode                : READ-ONLY")
    print("Database modified   : NO")
    print("Sales modified      : NO")
    print("Products modified   : NO")
    print("Inventory modified  : NO")
    print("Balance modified    : NO")
    print("Credit modified     : NO")
    print("Suppliers modified  : NO")
    print("Expenses modified   : NO")

    print("=" * 60)


def main():
    conn = None

    try:
        conn = get_connection()

        base = get_baseline(conn)
        scenarios = build_scenarios(base)

        print_report(
            base,
            scenarios,
        )

    except Exception as exc:
        print("=" * 60)
        print("V59 ERROR")
        print("=" * 60)
        print(str(exc))

    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    main()
