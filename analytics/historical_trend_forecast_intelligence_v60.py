import sqlite3
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, timedelta


DB_PATH = Path("data/posledger.db")

FORECAST_DAYS = 30
MIN_DATA_POINTS = 3


@dataclass
class Forecast:
    metric: str
    current: float
    average: float
    trend: float
    forecast: float
    confidence: float
    risk: str
    explanation: str


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


def get_columns(conn, table):
    if not table_exists(conn, table):
        return []

    rows = conn.execute(
        f"PRAGMA table_info({table})"
    ).fetchall()

    return [row[1] for row in rows]


def find_column(conn, table, candidates):
    columns = get_columns(conn, table)

    for candidate in candidates:
        if candidate in columns:
            return candidate

    return None


def safe_sum(conn, table, column):
    if not table_exists(conn, table):
        return 0.0

    if column not in get_columns(conn, table):
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


def get_sales_history(conn):
    """
    Reads sales history without modifying the database.

    Tries several possible column names so the analytics
    module remains compatible with the evolving POS Ledger NG
    database schema.
    """

    if not table_exists(conn, "sales"):
        return []

    date_col = find_column(
        conn,
        "sales",
        [
            "sale_date",
            "created_at",
            "transaction_date",
            "date",
        ],
    )

    amount_col = find_column(
        conn,
        "sales",
        [
            "total_amount",
            "total",
            "amount",
            "grand_total",
        ],
    )

    profit_col = find_column(
        conn,
        "sales",
        [
            "total_profit",
            "profit",
        ],
    )

    if not date_col or not amount_col:
        return []

    profit_expression = (
        profit_col if profit_col else "0"
    )

    try:
        rows = conn.execute(
            f"""
            SELECT
                {date_col},
                COALESCE({amount_col}, 0),
                COALESCE({profit_expression}, 0)
            FROM sales
            WHERE {date_col} IS NOT NULL
            ORDER BY {date_col}
            """
        ).fetchall()

    except sqlite3.Error:
        return []

    history = []

    for date_value, amount, profit in rows:
        try:
            if isinstance(date_value, str):
                date_text = date_value[:10]
                date_obj = datetime.strptime(
                    date_text,
                    "%Y-%m-%d",
                ).date()
            else:
                date_obj = date_value

            history.append(
                {
                    "date": date_obj,
                    "revenue": float(amount or 0),
                    "profit": float(profit or 0),
                }
            )

        except Exception:
            continue

    return history


def aggregate_daily(history):
    daily = {}

    for item in history:
        key = item["date"]

        if key not in daily:
            daily[key] = {
                "revenue": 0.0,
                "profit": 0.0,
                "sales": 0,
            }

        daily[key]["revenue"] += item["revenue"]
        daily[key]["profit"] += item["profit"]
        daily[key]["sales"] += 1

    return daily


def calculate_trend(values):
    if len(values) < 2:
        return 0.0

    first = values[0]
    last = values[-1]

    if first == 0:
        return 0.0

    return ((last - first) / abs(first)) * 100


def average(values):
    if not values:
        return 0.0

    return sum(values) / len(values)


def risk_from_confidence(confidence):
    if confidence >= 80:
        return "🟢 LOW"

    if confidence >= 60:
        return "🟡 MODERATE"

    if confidence >= 40:
        return "🟠 HIGH"

    return "🔴 VERY HIGH"


def forecast_metric(
    name,
    values,
    days=FORECAST_DAYS,
):
    if not values:
        return Forecast(
            name,
            0,
            0,
            0,
            0,
            0,
            "🔴 VERY HIGH",
            "No historical data available.",
        )

    avg = average(values)
    trend = calculate_trend(values)

    current = values[-1]

    if len(values) < MIN_DATA_POINTS:
        confidence = 35.0
        explanation = (
            "Limited historical observations."
        )

    elif len(values) < 7:
        confidence = 50.0
        explanation = (
            "Short historical period; forecast "
            "should be treated cautiously."
        )

    elif len(values) < 30:
        confidence = 65.0
        explanation = (
            "Moderate historical evidence available."
        )

    else:
        confidence = 80.0
        explanation = (
            "Strong historical data available."
        )

    # Conservative trend projection.
    #
    # The model does not blindly assume that the
    # latest growth rate will continue forever.
    capped_trend = max(
        min(trend, 30.0),
        -30.0,
    )

    projected = avg * (
        1 + capped_trend / 100
    )

    risk = risk_from_confidence(confidence)

    return Forecast(
        name,
        current,
        avg,
        trend,
        projected,
        confidence,
        risk,
        explanation,
    )


def build_forecast(conn):
    history = get_sales_history(conn)

    daily = aggregate_daily(history)

    if not daily:
        return None, [], daily

    ordered_dates = sorted(daily.keys())

    revenues = [
        daily[d]["revenue"]
        for d in ordered_dates
    ]

    profits = [
        daily[d]["profit"]
        for d in ordered_dates
    ]

    sales_count = [
        daily[d]["sales"]
        for d in ordered_dates
    ]

    revenue_forecast = forecast_metric(
        "REVENUE",
        revenues,
    )

    profit_forecast = forecast_metric(
        "PROFIT",
        profits,
    )

    sales_forecast = forecast_metric(
        "SALES COUNT",
        sales_count,
    )

    forecasts = [
        revenue_forecast,
        profit_forecast,
        sales_forecast,
    ]

    return history, forecasts, daily


def get_current_position(conn):
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

    return {
        "revenue": revenue,
        "profit": profit,
        "margin": margin,
    }


def print_header():
    print("=" * 60)
    print("POS LEDGER NG V60")
    print("HISTORICAL TREND & FORECAST INTELLIGENCE")
    print("=" * 60)


def print_current_position(position):
    print("\n" + "=" * 60)
    print("CURRENT BUSINESS POSITION")
    print("=" * 60)

    print(
        f"Revenue              : "
        f"{money(position['revenue'])}"
    )

    print(
        f"Gross Profit         : "
        f"{money(position['profit'])}"
    )

    print(
        f"Gross Margin         : "
        f"{position['margin'] * 100:.2f}%"
    )


def print_history_summary(history, daily):
    print("\n" + "=" * 60)
    print("HISTORICAL DATA SUMMARY")
    print("=" * 60)

    print(
        f"Recorded Transactions: {len(history)}"
    )

    print(
        f"Recorded Days        : {len(daily)}"
    )

    if history:
        print(
            f"First Recorded Date  : "
            f"{min(x['date'] for x in history)}"
        )

        print(
            f"Latest Recorded Date : "
            f"{max(x['date'] for x in history)}"
        )


def print_forecasts(forecasts):
    print("\n" + "=" * 60)
    print("FORECAST ANALYSIS")
    print("=" * 60)

    for forecast in forecasts:
        print("-" * 40)

        print(
            f"Metric             : "
            f"{forecast.metric}"
        )

        print(
            f"Current            : "
            f"{money(forecast.current)}"
            if forecast.metric != "SALES COUNT"
            else
            f"Current            : "
            f"{forecast.current:.2f}"
        )

        print(
            f"Historical Average : "
            f"{money(forecast.average)}"
            if forecast.metric != "SALES COUNT"
            else
            f"Historical Average : "
            f"{forecast.average:.2f}"
        )

        print(
            f"Trend              : "
            f"{forecast.trend:+.2f}%"
        )

        print(
            f"Forecast           : "
            f"{money(forecast.forecast)}"
            if forecast.metric != "SALES COUNT"
            else
            f"Forecast           : "
            f"{forecast.forecast:.2f}"
        )

        print(
            f"Confidence         : "
            f"{forecast.confidence:.2f}%"
        )

        print(
            f"Risk               : "
            f"{forecast.risk}"
        )

        print(
            f"Explanation        : "
            f"{forecast.explanation}"
        )


def print_management_interpretation(
    forecasts,
):
    print("\n" + "=" * 60)
    print("MANAGEMENT INTERPRETATION")
    print("=" * 60)

    revenue = next(
        x for x in forecasts
        if x.metric == "REVENUE"
    )

    profit = next(
        x for x in forecasts
        if x.metric == "PROFIT"
    )

    sales = next(
        x for x in forecasts
        if x.metric == "SALES COUNT"
    )

    if revenue.trend > 5:
        print(
            "Revenue Trend      : POSITIVE"
        )
    elif revenue.trend < -5:
        print(
            "Revenue Trend      : NEGATIVE"
        )
    else:
        print(
            "Revenue Trend      : STABLE"
        )

    if profit.trend > 5:
        print(
            "Profit Trend       : POSITIVE"
        )
    elif profit.trend < -5:
        print(
            "Profit Trend       : NEGATIVE"
        )
    else:
        print(
            "Profit Trend       : STABLE"
        )

    if sales.trend > 5:
        print(
            "Sales Activity     : INCREASING"
        )
    elif sales.trend < -5:
        print(
            "Sales Activity     : DECLINING"
        )
    else:
        print(
            "Sales Activity     : STABLE"
        )

    print("\nKey Management Signal:")

    if (
        revenue.trend > 0
        and profit.trend > 0
    ):
        print(
            "Business is showing "
            "simultaneous revenue and "
            "profit improvement."
        )

    elif (
        revenue.trend > 0
        and profit.trend <= 0
    ):
        print(
            "Revenue is increasing but "
            "profit is not keeping pace. "
            "Margin pressure should be investigated."
        )

    elif (
        revenue.trend <= 0
        and profit.trend > 0
    ):
        print(
            "Profit is improving despite "
            "weak revenue movement. "
            "Pricing or cost control may be helping."
        )

    else:
        print(
            "Current historical data does not "
            "show strong simultaneous growth."
        )


def print_forecast_warning(history):
    print("\n" + "=" * 60)
    print("FORECAST LIMITATIONS")
    print("=" * 60)

    if len(history) < MIN_DATA_POINTS:
        print(
            "⚠ Forecast confidence is LOW because "
            "there are fewer than 3 historical "
            "observations."
        )
    else:
        print(
            "Forecasts are estimates, not guarantees."
        )

    print(
        "The model uses recorded POS Ledger NG "
        "history and conservative trend limits."
    )

    print(
        "External factors such as seasonality, "
        "competition, price changes and economic "
        "conditions are not fully modeled."
    )


def print_safety_status():
    print("\n" + "=" * 60)
    print("V60 SAFETY STATUS")
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
    print_header()

    conn = None

    try:
        conn = get_connection()

        position = get_current_position(
            conn
        )

        history, forecasts, daily = (
            build_forecast(conn)
        )

        print_current_position(
            position
        )

        if not history:
            print("\n" + "=" * 60)
            print("V60 STATUS")
            print("=" * 60)
            print(
                "No usable sales history was found."
            )
            print(
                "Record more sales before relying "
                "on historical forecasting."
            )

            print_safety_status()
            return

        print_history_summary(
            history,
            daily,
        )

        print_forecasts(
            forecasts
        )

        print_management_interpretation(
            forecasts
        )

        print_forecast_warning(
            history
        )

        print_safety_status()

    except Exception as exc:
        print("\n" + "=" * 60)
        print("V60 ERROR")
        print("=" * 60)
        print(str(exc))

    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    main()
