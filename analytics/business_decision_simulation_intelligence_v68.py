import sqlite3
from pathlib import Path
from dataclasses import dataclass


DB_PATH = Path("data/posledger.db")

TARGET_MARGIN = 0.10


@dataclass
class Scenario:
    name: str
    sales_change: float
    credit_collection: float
    expense_change: float
    revenue: float = 0.0
    profit: float = 0.0
    liquidity: float = 0.0
    credit_remaining: float = 0.0
    supplier_gap: float = 0.0
    score: float = 0.0
    risk_score: float = 0.0
    risk: str = "UNKNOWN"
    confidence: float = 0.0
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
        WHERE type='table' AND name=?
        """,
        (table,),
    ).fetchone()

    return row is not None


def safe_sum(conn, table, column):
    if not table_exists(conn, table):
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

    cash = 0.0
    wallet = 0.0

    if table_exists(conn, "balance"):
        try:
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

        except sqlite3.Error:
            pass

    liquid = cash + wallet

    credit = safe_sum(
        conn,
        "customer_credit",
        "balance",
    )

    supplier = safe_sum(
        conn,
        "creditors",
        "balance",
    )

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
        "expenses": expenses,
    }


def build_scenarios(base):
    revenue = base["revenue"]
    profit = base["profit"]
    liquid = base["liquid"]
    credit = base["credit"]
    supplier = base["supplier"]

    scenarios = [
        Scenario(
            "SEVERE DOWNTURN",
            -0.20,
            0.00,
            0.10,
        ),
        Scenario(
            "CONSERVATIVE",
            -0.10,
            0.25,
            0.05,
        ),
        Scenario(
            "BASE CASE",
            0.00,
            0.50,
            0.00,
        ),
        Scenario(
            "MODERATE GROWTH",
            0.10,
            0.75,
            0.00,
        ),
        Scenario(
            "STRONG GROWTH",
            0.20,
            1.00,
            0.05,
        ),
        Scenario(
            "FULL OPTIMIZATION",
            0.20,
            1.00,
            -0.05,
        ),
    ]

    for scenario in scenarios:
        scenario.revenue = revenue * (
            1 + scenario.sales_change
        )

        projected_margin = max(
            base["margin"],
            TARGET_MARGIN,
        )

        scenario.profit = (
            scenario.revenue
            * projected_margin
        )

        collected_credit = (
            credit
            * scenario.credit_collection
        )

        scenario.credit_remaining = max(
            credit - collected_credit,
            0,
        )

        expense = (
            base["expenses"]
            * (1 + scenario.expense_change)
        )

        scenario.liquidity = (
            liquid
            + collected_credit
            + max(
                scenario.profit - profit,
                0,
            )
            - expense
        )

        scenario.supplier_gap = max(
            supplier - scenario.liquidity,
            0,
        )

    return scenarios


def score_scenario(scenario, base):
    score = 0.0

    # Liquidity coverage: 30 points
    if base["supplier"] > 0:
        coverage = min(
            scenario.liquidity
            / base["supplier"],
            1.0,
        )
        score += coverage * 30
    else:
        score += 30

    # Profit performance: 25 points
    if base["profit"] > 0:
        profit_ratio = min(
            scenario.profit
            / (base["profit"] * 2),
            1.0,
        )
        score += profit_ratio * 25
    else:
        score += 25

    # Margin: 20 points
    if TARGET_MARGIN > 0:
        margin_ratio = min(
            max(
                base["margin"],
                scenario.profit
                / scenario.revenue
                if scenario.revenue > 0
                else 0,
            )
            / TARGET_MARGIN,
            1.0,
        )
        score += margin_ratio * 20

    # Credit recovery: 15 points
    if base["credit"] > 0:
        recovery = (
            1
            - scenario.credit_remaining
            / base["credit"]
        )
        score += max(
            0,
            min(recovery, 1),
        ) * 15
    else:
        score += 15

    # Supplier gap: 10 points
    if base["supplier"] > 0:
        supplier_score = (
            1
            - min(
                scenario.supplier_gap
                / base["supplier"],
                1,
            )
        )
        score += supplier_score * 10
    else:
        score += 10

    scenario.score = min(
        max(score, 0),
        100,
    )


def assess_risk(scenario, base):
    risk_score = 0.0
    reasons = []

    if scenario.sales_change <= -0.20:
        risk_score += 30
        reasons.append(
            "SEVERE SALES DECLINE ASSUMPTION"
        )

    elif scenario.sales_change < 0:
        risk_score += 15
        reasons.append(
            "SALES DECLINE ASSUMPTION"
        )

    if scenario.credit_collection < 0.50:
        risk_score += 15
        reasons.append(
            "LOW CREDIT COLLECTION"
        )

    if scenario.expense_change > 0:
        risk_score += 10
        reasons.append(
            "EXPENSE INCREASE ASSUMPTION"
        )

    if scenario.supplier_gap > 0:
        risk_score += 20
        reasons.append(
            "SUPPLIER GAP REMAINS"
        )

    if scenario.liquidity < base["supplier"]:
        risk_score += 15
        reasons.append(
            "LIQUIDITY BELOW SUPPLIER LIABILITY"
        )

    if base["revenue"] < 50000:
        risk_score += 10
        reasons.append(
            "LIMITED HISTORICAL DATA"
        )

    risk_score = min(
        risk_score,
        100,
    )

    if risk_score <= 20:
        risk = "🟢 LOW"
    elif risk_score <= 40:
        risk = "🟡 MODERATE"
    elif risk_score <= 60:
        risk = "🟠 HIGH"
    else:
        risk = "🔴 VERY HIGH"

    confidence = max(
        0,
        min(
            100 - risk_score,
            100,
        ),
    )

    scenario.risk_score = risk_score
    scenario.risk = risk
    scenario.confidence = confidence

    if reasons:
        scenario.reason = ", ".join(
            reasons
        )
    else:
        scenario.reason = (
            "LOW ASSUMPTION RISK"
        )


def print_report(base, scenarios):
    for scenario in scenarios:
        score_scenario(
            scenario,
            base,
        )

        assess_risk(
            scenario,
            base,
        )

    ranked = sorted(
        scenarios,
        key=lambda s: (
            s.score,
            s.liquidity,
            s.profit,
        ),
        reverse=True,
    )

    best = ranked[0]
    worst = min(
        scenarios,
        key=lambda s: s.liquidity,
    )

    print("=" * 60)
    print("POS LEDGER NG V68")
    print("BUSINESS DECISION SIMULATION INTELLIGENCE")
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
        f"Recorded Expenses    : "
        f"{money(base['expenses'])}"
    )

    print("\n" + "=" * 60)
    print("SCENARIO SIMULATION")
    print("=" * 60)

    for scenario in scenarios:
        print("-" * 40)

        print(
            f"Scenario              : "
            f"{scenario.name}"
        )

        print(
            f"Sales Change          : "
            f"{scenario.sales_change * 100:+.0f}%"
        )

        print(
            f"Credit Collection     : "
            f"{scenario.credit_collection * 100:.0f}%"
        )

        print(
            f"Projected Revenue     : "
            f"{money(scenario.revenue)}"
        )

        print(
            f"Projected Profit      : "
            f"{money(scenario.profit)}"
        )

        print(
            f"Projected Liquidity   : "
            f"{money(scenario.liquidity)}"
        )

        print(
            f"Credit Remaining      : "
            f"{money(scenario.credit_remaining)}"
        )

        print(
            f"Supplier Gap          : "
            f"{money(scenario.supplier_gap)}"
        )

        print(
            f"Decision Score        : "
            f"{scenario.score:.2f}/100"
        )

        print(
            f"Confidence            : "
            f"{scenario.confidence:.2f}%"
        )

        print(
            f"Risk                  : "
            f"{scenario.risk}"
        )

        print(
            f"Risk Score            : "
            f"{scenario.risk_score:.2f}/100"
        )

        print(
            f"Risk Factors          : "
            f"{scenario.reason}"
        )

    print("\n" + "=" * 60)
    print("SCENARIO RANKING")
    print("=" * 60)

    for index, scenario in enumerate(
        ranked,
        1,
    ):
        print(
            f"{index}. "
            f"{scenario.name:<25} "
            f"{scenario.score:>6.2f}/100"
        )

    print("\n" + "=" * 60)
    print("BEST CASE")
    print("=" * 60)

    print(
        f"Scenario              : "
        f"{best.name}"
    )

    print(
        f"Projected Revenue     : "
        f"{money(best.revenue)}"
    )

    print(
        f"Projected Profit      : "
        f"{money(best.profit)}"
    )

    print(
        f"Projected Liquidity   : "
        f"{money(best.liquidity)}"
    )

    print(
        f"Risk                  : "
        f"{best.risk}"
    )

    print("\n" + "=" * 60)
    print("DOWNSIDE SCENARIO")
    print("=" * 60)

    print(
        f"Scenario              : "
        f"{worst.name}"
    )

    print(
        f"Projected Revenue     : "
        f"{money(worst.revenue)}"
    )

    print(
        f"Projected Profit      : "
        f"{money(worst.profit)}"
    )

    print(
        f"Projected Liquidity   : "
        f"{money(worst.liquidity)}"
    )

    print(
        f"Supplier Gap          : "
        f"{money(worst.supplier_gap)}"
    )

    print(
        f"Risk                  : "
        f"{worst.risk}"
    )

    print("\n" + "=" * 60)
    print("MANAGEMENT DECISION")
    print("=" * 60)

    if worst.supplier_gap > 0:
        print(
            "Protect liquidity before aggressive "
            "business expansion."
        )

    if base["credit"] > 0:
        print(
            "Prioritize customer credit collection "
            "to strengthen available cash."
        )

    if base["margin"] < TARGET_MARGIN:
        print(
            "Improve product margins toward the "
            "10% management target."
        )

    print(
        "Use the BASE CASE as the normal planning "
        "reference and the DOWNSIDE SCENARIO as "
        "the minimum safety test."
    )

    print("\n" + "=" * 60)
    print("V68 DECISION EXPLANATION")
    print("=" * 60)

    print(
        "V68 compares multiple possible business "
        "futures instead of relying on one forecast."
    )

    print(
        "The simulation evaluates sales movement, "
        "credit collection, expenses, profit, "
        "liquidity and supplier pressure."
    )

    print(
        f"Highest-scoring scenario: {best.name}"
    )

    print(
        "Management should not treat the highest "
        "score as a guarantee. The scenario should "
        "be compared with the downside case before "
        "making major financial decisions."
    )

    print("\n" + "=" * 60)
    print("V68 SAFETY STATUS")
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

        scenarios = build_scenarios(
            base
        )

        print_report(
            base,
            scenarios,
        )

    except Exception as exc:
        print("=" * 60)
        print("V68 ERROR")
        print("=" * 60)
        print(str(exc))

    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    main()
