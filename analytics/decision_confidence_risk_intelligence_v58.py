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
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    return sqlite3.connect(DB_PATH)


def table_exists(conn, table):
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None


def safe_sum(conn, table, column):
    if not table_exists(conn, table):
        return 0.0

    try:
        row = conn.execute(
            f"SELECT COALESCE(SUM({column}), 0) FROM {table}"
        ).fetchone()
        return float(row[0] or 0)
    except sqlite3.Error:
        return 0.0


def get_baseline(conn):
    revenue = safe_sum(conn, "sales", "total_amount")
    profit = safe_sum(conn, "sales", "total_profit")

    if revenue <= 0:
        revenue = safe_sum(conn, "transactions", "amount")

    if profit <= 0:
        profit = safe_sum(conn, "transactions", "profit")

    margin = profit / revenue if revenue > 0 else 0.0

    cash = 0.0
    wallet = 0.0

    if table_exists(conn, "balance"):
        row = conn.execute(
            """
            SELECT
                COALESCE(cash_balance, 0),
                COALESCE(wallet_balance, 0)
            FROM balance
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()

        if row:
            cash = float(row[0] or 0)
            wallet = float(row[1] or 0)

    liquid = cash + wallet

    credit = safe_sum(conn, "customer_credit", "balance")
    supplier_liability = safe_sum(conn, "creditors", "balance")

    inventory_capital = 0.0

    if table_exists(conn, "products"):
        try:
            row = conn.execute(
                """
                SELECT COALESCE(SUM(
                    buying_price * current_stock
                ), 0)
                FROM products
                """
            ).fetchone()

            inventory_capital = float(row[0] or 0)
        except sqlite3.Error:
            inventory_capital = 0.0

    expenses = safe_sum(conn, "expenses", "amount")

    return {
        "revenue": revenue,
        "profit": profit,
        "margin": margin,
        "liquid": liquid,
        "credit": credit,
        "supplier": supplier_liability,
        "inventory": inventory_capital,
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

    # Current
    scenarios.append(
        Scenario(
            "CURRENT STRATEGY",
            revenue,
            profit,
            margin,
            liquid,
            credit,
            max(supplier - liquid, 0),
        )
    )

    # Sales growth
    for pct in (0.10, 0.20, 0.30):
        new_revenue = revenue * (1 + pct)
        new_profit = profit * (1 + pct)

        collection = credit * pct
        new_credit = max(credit - collection, 0)
        new_liquid = liquid + collection

        gap = max(supplier - new_liquid, 0)

        scenarios.append(
            Scenario(
                f"+{int(pct * 100)}% SALES",
                new_revenue,
                new_profit,
                margin,
                new_liquid,
                new_credit,
                gap,
            )
        )

    # Pricing optimization
    pricing_profit = revenue * TARGET_MARGIN
    pricing_extra = max(pricing_profit - profit, 0)

    pricing_liquid = liquid + credit * 0.5
    pricing_credit = credit * 0.5
    pricing_gap = max(supplier - pricing_liquid, 0)

    scenarios.append(
        Scenario(
            "PRICING OPTIMIZATION",
            revenue,
            profit + pricing_extra,
            TARGET_MARGIN,
            pricing_liquid,
            pricing_credit,
            pricing_gap,
        )
    )

    # Pricing + 20% sales
    p20_revenue = revenue * 1.20
    p20_profit = p20_revenue * TARGET_MARGIN

    p20_collection = credit * 0.50
    p20_credit = max(credit - p20_collection, 0)
    p20_liquid = liquid + p20_collection
    p20_gap = max(supplier - p20_liquid, 0)

    scenarios.append(
        Scenario(
            "PRICING +20% SALES",
            p20_revenue,
            p20_profit,
            TARGET_MARGIN,
            p20_liquid,
            p20_credit,
            p20_gap,
        )
    )

    # Pricing + credit collection
    collection_liquid = liquid + credit
    collection_gap = max(supplier - collection_liquid, 0)

    scenarios.append(
        Scenario(
            "PRICING + CREDIT COLLECTION",
            revenue,
            profit + pricing_extra,
            TARGET_MARGIN,
            collection_liquid,
            0,
            collection_gap,
        )
    )

    # Full optimization
    full_revenue = revenue * 1.20
    full_profit = full_revenue * TARGET_MARGIN
    full_liquid = liquid + credit

    scenarios.append(
        Scenario(
            "FULL OPTIMIZATION",
            full_revenue,
            full_profit,
            TARGET_MARGIN,
            full_liquid,
            0,
            max(supplier - full_liquid, 0),
        )
    )

    return scenarios


def score_scenario(s, base):
    margin_score = min(s.margin / TARGET_MARGIN, 1.0) * 30

    liquidity_score = 0

    if base["liquid"] > 0:
        liquidity_score = min(
            s.liquidity / max(base["supplier"], 1),
            1.0
        ) * 25

    credit_score = 0

    if base["credit"] > 0:
        credit_score = (
            1 - min(s.credit / base["credit"], 1)
        ) * 20
    else:
        credit_score = 20

    supplier_score = 0

    if base["supplier"] > 0:
        supplier_score = (
            1 - min(s.supplier_gap / base["supplier"], 1)
        ) * 15
    else:
        supplier_score = 15

    profit_score = 0

    if base["profit"] > 0:
        profit_score = min(
            s.profit / (base["profit"] * 2),
            1.0
        ) * 10

    s.score = min(
        margin_score
        + liquidity_score
        + credit_score
        + supplier_score
        + profit_score,
        100,
    )


def confidence_and_risk(s, base):
    confidence = 100.0
    risk = []

    # Low historical revenue/data
    if base["revenue"] < 50000:
        confidence -= 15
        risk.append("LIMITED SALES DATA")

    # Low margin
    if s.margin < TARGET_MARGIN:
        confidence -= 10
        risk.append("LOW MARGIN")

    # Large sales assumption
    if s.name in ("+30% SALES", "FULL OPTIMIZATION"):
        confidence -= 15
        risk.append("AGGRESSIVE GROWTH ASSUMPTION")

    # Pricing dependency
    if "PRICING" in s.name:
        confidence -= 5
        risk.append("PRICE CHANGE REQUIRED")

    # Credit dependency
    if "CREDIT" in s.name or s.credit < base["credit"]:
        confidence -= 5
        risk.append("COLLECTION EXECUTION REQUIRED")

    # Supplier exposure
    if s.supplier_gap > 0:
        confidence -= 10
        risk.append("SUPPLIER GAP REMAINS")

    confidence = max(0, min(confidence, 100))

    risk_score = 100 - confidence

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

    if risk:
        s.reason = ", ".join(risk)
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
    for s in scenarios:
        score_scenario(s, base)
        confidence_and_risk(s, base)

    ranked = sorted(
        scenarios,
        key=tie_break_key,
        reverse=True,
    )

    best = ranked[0]

    print("=" * 60)
    print("POS LEDGER NG V58")
    print("DECISION CONFIDENCE & RISK INTELLIGENCE")
    print("=" * 60)

    print("\n" + "=" * 60)
    print("CURRENT BUSINESS POSITION")
    print("=" * 60)

    print(f"Revenue              : {money(base['revenue'])}")
    print(f"Gross Profit         : {money(base['profit'])}")
    print(f"Gross Margin         : {base['margin'] * 100:.2f}%")
    print(f"Liquid Funds         : {money(base['liquid'])}")
    print(f"Customer Credit      : {money(base['credit'])}")
    print(f"Supplier Liability   : {money(base['supplier'])}")
    print(f"Inventory Capital    : {money(base['inventory'])}")
    print(f"Recorded Expenses    : {money(base['expenses'])}")

    print("\n" + "=" * 60)
    print("DECISION RANKING")
    print("=" * 60)

    for i, s in enumerate(ranked, 1):
        print(
            f"{i}. {s.name:<30} "
            f"{s.score:>6.2f}/100"
        )

    print("\n" + "=" * 60)
    print("CONFIDENCE & RISK ANALYSIS")
    print("=" * 60)

    for s in ranked:
        print("-" * 40)
        print(f"Scenario          : {s.name}")
        print(f"Decision Score    : {s.score:.2f}/100")
        print(f"Confidence        : {s.confidence:.2f}%")
        print(f"Risk              : {s.risk}")
        print(f"Risk Score        : {s.risk_score:.2f}/100")
        print(f"Projected Profit  : {money(s.profit)}")
        print(f"Projected Margin  : {s.margin * 100:.2f}%")
        print(f"Projected Liquidity: {money(s.liquidity)}")
        print(f"Remaining Credit  : {money(s.credit)}")
        print(f"Supplier Gap      : {money(s.supplier_gap)}")
        print(f"Risk Factors      : {s.reason}")

    print("\n" + "=" * 60)
    print("RECOMMENDED DECISION")
    print("=" * 60)

    print(f"Strategy           : {best.name}")
    print(f"Decision Score     : {best.score:.2f}/100")
    print(f"Confidence         : {best.confidence:.2f}%")
    print(f"Risk               : {best.risk}")
    print(f"Projected Revenue  : {money(best.revenue)}")
    print(f"Projected Profit   : {money(best.profit)}")
    print(f"Projected Margin   : {best.margin * 100:.2f}%")
    print(f"Projected Liquidity: {money(best.liquidity)}")
    print(f"Remaining Credit   : {money(best.credit)}")
    print(f"Supplier Gap       : {money(best.supplier_gap)}")

    print("\n" + "=" * 60)
    print("DECISION EXPLANATION")
    print("=" * 60)

    if best.name == "FULL OPTIMIZATION":
        print(
            "The model prefers FULL OPTIMIZATION because it "
            "combines margin improvement, controlled sales growth "
            "and credit collection."
        )
    elif best.name == "PRICING + CREDIT COLLECTION":
        print(
            "The model prefers pricing improvement and credit "
            "collection because these improve profitability and "
            "liquidity without requiring aggressive sales growth."
        )
    else:
        print(
            "The model selected the highest-scoring scenario "
            "after applying profit, liquidity, credit, supplier "
            "and risk considerations."
        )

    print("\n" + "=" * 60)
    print("V58 SAFETY STATUS")
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
    try:
        conn = get_connection()

        try:
            base = get_baseline(conn)
            scenarios = build_scenarios(base)
            print_report(base, scenarios)
        finally:
            conn.close()

    except Exception as exc:
        print("=" * 60)
        print("V58 ERROR")
        print("=" * 60)
        print(str(exc))


if __name__ == "__main__":
    main()
