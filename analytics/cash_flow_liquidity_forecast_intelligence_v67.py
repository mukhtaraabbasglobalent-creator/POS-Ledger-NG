import sqlite3
from pathlib import Path
from dataclasses import dataclass


DB_PATH = Path("data/posledger.db")


@dataclass
class CashFlow:
    liquid: float = 0.0
    customer_credit: float = 0.0
    supplier_liability: float = 0.0
    inventory: float = 0.0
    daily_revenue: float = 0.0
    daily_profit: float = 0.0
    daily_expenses: float = 0.0
    projected_inflow: float = 0.0
    projected_outflow: float = 0.0
    projected_liquidity: float = 0.0
    supplier_gap: float = 0.0
    risk_score: float = 0.0
    risk: str = "UNKNOWN"
    confidence: float = 0.0


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


def get_liquid_funds(conn):
    if not table_exists(conn, "balance"):
        return 0.0

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
            return float(row[0] or 0) + float(row[1] or 0)

    except sqlite3.Error:
        pass

    return 0.0


def get_inventory(conn):
    if not table_exists(conn, "products"):
        return 0.0

    if not column_exists(conn, "products", "buying_price"):
        return 0.0

    if not column_exists(conn, "products", "current_stock"):
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


def get_sales_history(conn):
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

    sales_count = 0

    if table_exists(conn, "sales"):
        try:
            sales_count = conn.execute(
                "SELECT COUNT(*) FROM sales"
            ).fetchone()[0]
        except sqlite3.Error:
            sales_count = 0

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

    transaction_count = 0

    if table_exists(conn, "transactions"):
        try:
            transaction_count = conn.execute(
                "SELECT COUNT(*) FROM transactions"
            ).fetchone()[0]
        except sqlite3.Error:
            transaction_count = 0

    count = max(sales_count, transaction_count)

    if count <= 0:
        return 0.0, 0.0, 0

    daily_revenue = revenue / 7
    daily_profit = profit / 7

    return daily_revenue, daily_profit, count


def get_baseline(conn):
    liquid = get_liquid_funds(conn)

    credit = safe_sum(
        conn,
        "customer_credit",
        "balance",
    )

    if credit <= 0:
        credit = safe_sum(
            conn,
            "customer_credit",
            "amount",
        )

    supplier = 0.0

    for column in (
        "balance",
        "amount",
        "outstanding",
        "remaining_balance",
    ):
        value = safe_sum(
            conn,
            "creditors",
            column,
        )

        if value > supplier:
            supplier = value

    inventory = get_inventory(conn)

    expenses = safe_sum(
        conn,
        "expenses",
        "amount",
    )

    daily_revenue, daily_profit, sales_count = (
        get_sales_history(conn)
    )

    daily_expenses = expenses / 7

    return {
        "liquid": liquid,
        "credit": credit,
        "supplier": supplier,
        "inventory": inventory,
        "daily_revenue": daily_revenue,
        "daily_profit": daily_profit,
        "daily_expenses": daily_expenses,
        "sales_count": sales_count,
    }


def calculate_forecast(base):
    liquid = base["liquid"]
    credit = base["credit"]
    supplier = base["supplier"]

    daily_revenue = base["daily_revenue"]
    daily_profit = base["daily_profit"]
    daily_expenses = base["daily_expenses"]

    # Conservative 7-day forecast
    forecast_days = 7

    expected_sales_inflow = (
        daily_revenue * forecast_days
    )

    expected_profit = (
        daily_profit * forecast_days
    )

    expected_expenses = (
        daily_expenses * forecast_days
    )

    # Assume 50% of customer credit can realistically
    # be collected during the forecast period.
    expected_credit_collection = credit * 0.50

    projected_inflow = (
        expected_sales_inflow
        + expected_credit_collection
    )

    projected_outflow = expected_expenses

    projected_liquidity = (
        liquid
        + projected_inflow
        - projected_outflow
    )

    supplier_gap = max(
        supplier - projected_liquidity,
        0,
    )

    return {
        "days": forecast_days,
        "sales_inflow": expected_sales_inflow,
        "profit": expected_profit,
        "expenses": expected_expenses,
        "credit_collection": expected_credit_collection,
        "inflow": projected_inflow,
        "outflow": projected_outflow,
        "liquidity": projected_liquidity,
        "supplier_gap": supplier_gap,
    }


def assess_risk(base, forecast):
    risk_score = 0.0
    confidence = 100.0
    reasons = []

    liquid = base["liquid"]
    supplier = base["supplier"]
    credit = base["credit"]
    daily_profit = base["daily_profit"]

    projected_liquidity = forecast["liquidity"]

    if liquid < supplier:
        risk_score += 20
        reasons.append(
            "CURRENT LIQUIDITY BELOW SUPPLIER LIABILITY"
        )

    if forecast["supplier_gap"] > 0:
        risk_score += 20
        reasons.append(
            "PROJECTED SUPPLIER GAP REMAINS"
        )

    if credit > liquid:
        risk_score += 10
        reasons.append(
            "CUSTOMER CREDIT EXCEEDS LIQUID FUNDS"
        )

    if daily_profit <= 0:
        risk_score += 20
        reasons.append(
            "LOW OR NEGATIVE DAILY PROFIT"
        )

    if base["sales_count"] < 14:
        confidence -= 15
        reasons.append(
            "LIMITED SALES HISTORY"
        )

    if credit > 0:
        confidence -= 5
        reasons.append(
            "CREDIT COLLECTION ASSUMPTION"
        )

    if daily_revenue_is_low(base):
        confidence -= 5

    risk_score = min(
        risk_score,
        100,
    )

    confidence = max(
        min(confidence, 100),
        0,
    )

    if risk_score <= 20:
        risk = "🟢 LOW"
    elif risk_score <= 40:
        risk = "🟡 MODERATE"
    elif risk_score <= 60:
        risk = "🟠 HIGH"
    else:
        risk = "🔴 VERY HIGH"

    return risk_score, confidence, risk, reasons


def daily_revenue_is_low(base):
    return base["daily_revenue"] < 5000


def management_action(base, forecast):
    if forecast["supplier_gap"] > 0:
        return (
            "URGENT",
            "PROTECT LIQUIDITY",
            (
                "Projected liquidity does not fully cover "
                "supplier obligations. Prioritize cash "
                "preservation, customer collections and "
                "controlled supplier payments."
            ),
        )

    if base["credit"] > 0:
        return (
            "HIGH",
            "COLLECT CUSTOMER CREDIT",
            (
                "Customer credit represents recoverable "
                "liquidity. Collection can strengthen "
                "cash availability."
            ),
        )

    if base["daily_profit"] <= 0:
        return (
            "HIGH",
            "IMPROVE PROFITABILITY",
            (
                "Daily profitability is weak. Review "
                "pricing, product margins and expenses."
            ),
        )

    return (
        "MEDIUM",
        "MAINTAIN LIQUIDITY DISCIPLINE",
        (
            "Liquidity appears manageable. Continue "
            "monitoring daily inflows, outflows and "
            "supplier obligations."
        ),
    )


def print_report(base, forecast):
    risk_score, confidence, risk, reasons = (
        assess_risk(base, forecast)
    )

    priority, action, recommendation = (
        management_action(base, forecast)
    )

    print("=" * 60)
    print("POS LEDGER NG V67")
    print("CASH FLOW & LIQUIDITY FORECAST INTELLIGENCE")
    print("=" * 60)

    print("\n" + "=" * 60)
    print("CURRENT LIQUIDITY POSITION")
    print("=" * 60)

    print(
        f"Liquid Funds             : "
        f"{money(base['liquid'])}"
    )

    print(
        f"Customer Credit          : "
        f"{money(base['credit'])}"
    )

    print(
        f"Supplier Liability       : "
        f"{money(base['supplier'])}"
    )

    print(
        f"Inventory Capital        : "
        f"{money(base['inventory'])}"
    )

    print(
        f"Daily Revenue            : "
        f"{money(base['daily_revenue'])}"
    )

    print(
        f"Daily Profit             : "
        f"{money(base['daily_profit'])}"
    )

    print(
        f"Recorded Sales           : "
        f"{base['sales_count']}"
    )

    print("\n" + "=" * 60)
    print("7-DAY CASH FLOW FORECAST")
    print("=" * 60)

    print(
        f"Expected Sales Inflow    : "
        f"{money(forecast['sales_inflow'])}"
    )

    print(
        f"Expected Credit Recovery : "
        f"{money(forecast['credit_collection'])}"
    )

    print(
        f"Projected Total Inflow   : "
        f"{money(forecast['inflow'])}"
    )

    print(
        f"Projected Expenses       : "
        f"{money(forecast['expenses'])}"
    )

    print(
        f"Projected Liquidity      : "
        f"{money(forecast['liquidity'])}"
    )

    print(
        f"Projected Supplier Gap   : "
        f"{money(forecast['supplier_gap'])}"
    )

    print("\n" + "=" * 60)
    print("LIQUIDITY RISK")
    print("=" * 60)

    print(
        f"Risk Score               : "
        f"{risk_score:.2f}/100"
    )

    print(
        f"Risk Status              : {risk}"
    )

    print(
        f"Forecast Confidence      : "
        f"{confidence:.2f}%"
    )

    print("\nRisk Factors:")

    if reasons:
        for reason in reasons:
            print(f"- {reason}")
    else:
        print("- No major liquidity risk detected.")

    print("\n" + "=" * 60)
    print("TOP MANAGEMENT ACTION")
    print("=" * 60)

    print(
        f"Priority                 : {priority}"
    )

    print(
        f"Action                   : {action}"
    )

    print(
        f"Recommendation           : {recommendation}"
    )

    print("\n" + "=" * 60)
    print("MANAGEMENT INTERPRETATION")
    print("=" * 60)

    if forecast["supplier_gap"] > 0:
        print(
            "The business is projected to remain under "
            "liquidity pressure against supplier "
            "obligations."
        )
        print(
            "Management should prioritize collections, "
            "protect cash and avoid unnecessary "
            "withdrawals or aggressive expansion."
        )

    elif base["credit"] > 0:
        print(
            "Projected liquidity is improving, but "
            "customer credit remains an important "
            "source of recoverable cash."
        )

    else:
        print(
            "Projected liquidity appears manageable "
            "under the current assumptions."
        )

    print("\n" + "=" * 60)
    print("FORECAST LIMITATIONS")
    print("=" * 60)

    print(
        "Forecasts are estimates, not guarantees."
    )

    print(
        "The model uses recorded POS Ledger NG "
        "historical data and conservative assumptions."
    )

    print(
        "Seasonality, competition, price changes, "
        "unexpected expenses and economic conditions "
        "are not fully modeled."
    )

    print("\n" + "=" * 60)
    print("V67 SAFETY STATUS")
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
        forecast = calculate_forecast(base)

        print_report(
            base,
            forecast,
        )

    except Exception as exc:
        print("=" * 60)
        print("V67 ERROR")
        print("=" * 60)
        print(str(exc))

    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    main()
