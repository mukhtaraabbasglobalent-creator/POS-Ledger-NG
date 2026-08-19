import sqlite3
from pathlib import Path


DB_PATH = Path("data/posledger.db")

TARGET_MARGIN = 0.10
TARGET_LIQUIDITY_COVERAGE = 1.00
MIN_SALES_FOR_STRONG_CONFIDENCE = 30


def money(value):
    return f"₦{value:,.2f}"


def pct(value):
    return f"{value * 100:.2f}%"


def connect():
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


def columns(conn, table):
    if not table_exists(conn, table):
        return set()

    rows = conn.execute(
        f"PRAGMA table_info({table})"
    ).fetchall()

    return {row[1] for row in rows}


def safe_sum(conn, table, column):
    if column not in columns(conn, table):
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


def safe_count(conn, table):
    if not table_exists(conn, table):
        return 0

    try:
        row = conn.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()

        return int(row[0] or 0)

    except sqlite3.Error:
        return 0


def get_latest_balance(conn):
    if not table_exists(conn, "balance"):
        return 0.0

    cols = columns(conn, "balance")

    cash_column = (
        "cash_balance"
        if "cash_balance" in cols
        else None
    )

    wallet_column = (
        "wallet_balance"
        if "wallet_balance" in cols
        else None
    )

    if not cash_column and not wallet_column:
        return 0.0

    expressions = []

    if cash_column:
        expressions.append(
            "COALESCE(cash_balance, 0)"
        )

    if wallet_column:
        expressions.append(
            "COALESCE(wallet_balance, 0)"
        )

    total_expression = " + ".join(expressions)

    order_clause = ""

    if "id" in cols:
        order_clause = "ORDER BY id DESC"

    try:
        row = conn.execute(
            f"""
            SELECT {total_expression}
            FROM balance
            {order_clause}
            LIMIT 1
            """
        ).fetchone()

        return float(row[0] or 0) if row else 0.0

    except sqlite3.Error:
        return 0.0


def get_sales_metrics(conn):
    revenue = 0.0
    profit = 0.0
    sales_count = 0

    if table_exists(conn, "sales"):
        sales_cols = columns(conn, "sales")

        if "total_amount" in sales_cols:
            revenue = safe_sum(
                conn,
                "sales",
                "total_amount",
            )

        if "total_profit" in sales_cols:
            profit = safe_sum(
                conn,
                "sales",
                "total_profit",
            )

        sales_count = safe_count(
            conn,
            "sales",
        )

    if revenue <= 0 and table_exists(
        conn,
        "transactions",
    ):
        revenue = safe_sum(
            conn,
            "transactions",
            "amount",
        )

    if profit <= 0 and table_exists(
        conn,
        "transactions",
    ):
        profit = safe_sum(
            conn,
            "transactions",
            "profit",
        )

    if sales_count <= 0:
        sales_count = safe_count(
            conn,
            "transactions",
        )

    return revenue, profit, sales_count


def get_customer_credit(conn):
    possible_tables = [
        "customer_credit",
        "customer_credits",
        "credits",
    ]

    possible_columns = [
        "balance",
        "amount",
        "credit_amount",
        "outstanding",
    ]

    for table in possible_tables:
        if not table_exists(conn, table):
            continue

        table_cols = columns(conn, table)

        for column in possible_columns:
            if column in table_cols:
                return safe_sum(
                    conn,
                    table,
                    column,
                )

    return 0.0


def get_supplier_liability(conn):
    possible_tables = [
        "creditors",
        "suppliers",
        "supplier_credit",
        "supplier_liabilities",
    ]

    possible_columns = [
        "balance",
        "amount",
        "credit_amount",
        "outstanding",
        "liability",
    ]

    for table in possible_tables:
        if not table_exists(conn, table):
            continue

        table_cols = columns(conn, table)

        for column in possible_columns:
            if column in table_cols:
                return safe_sum(
                    conn,
                    table,
                    column,
                )

    return 0.0


def get_inventory_value(conn):
    if not table_exists(conn, "products"):
        return 0.0

    cols = columns(conn, "products")

    stock_columns = [
        "current_stock",
        "stock",
        "quantity",
        "opening_stock",
    ]

    cost_columns = [
        "buying_price",
        "buy_price",
        "cost_price",
        "purchase_price",
    ]

    stock_column = next(
        (
            c
            for c in stock_columns
            if c in cols
        ),
        None,
    )

    cost_column = next(
        (
            c
            for c in cost_columns
            if c in cols
        ),
        None,
    )

    if not stock_column or not cost_column:
        return 0.0

    try:
        row = conn.execute(
            f"""
            SELECT COALESCE(
                SUM(
                    {stock_column} *
                    {cost_column}
                ),
                0
            )
            FROM products
            """
        ).fetchone()

        return float(row[0] or 0)

    except sqlite3.Error:
        return 0.0


def build_position(conn):
    revenue, profit, sales_count = (
        get_sales_metrics(conn)
    )

    liquid = get_latest_balance(conn)

    credit = get_customer_credit(conn)

    supplier = get_supplier_liability(conn)

    inventory = get_inventory_value(conn)

    margin = (
        profit / revenue
        if revenue > 0
        else 0.0
    )

    average_sale = (
        revenue / sales_count
        if sales_count > 0
        else 0.0
    )

    profit_per_sale = (
        profit / sales_count
        if sales_count > 0
        else 0.0
    )

    credit_ratio = (
        credit / revenue
        if revenue > 0
        else 0.0
    )

    supplier_ratio = (
        supplier / revenue
        if revenue > 0
        else 0.0
    )

    liquidity_coverage = (
        liquid / supplier
        if supplier > 0
        else 1.0
    )

    inventory_ratio = (
        inventory / revenue
        if revenue > 0
        else 0.0
    )

    return {
        "revenue": revenue,
        "profit": profit,
        "sales_count": sales_count,
        "liquid": liquid,
        "credit": credit,
        "supplier": supplier,
        "inventory": inventory,
        "margin": margin,
        "average_sale": average_sale,
        "profit_per_sale": profit_per_sale,
        "credit_ratio": credit_ratio,
        "supplier_ratio": supplier_ratio,
        "liquidity_coverage": liquidity_coverage,
        "inventory_ratio": inventory_ratio,
    }


def calculate_health(position):
    score = 100.0

    if position["margin"] < TARGET_MARGIN:
        score -= 20

    if position["credit"] > 0:
        score -= 10

    if (
        position["supplier"]
        > position["liquid"]
    ):
        score -= 20

    if position["inventory"] > 0:
        score -= 10

    if (
        position["sales_count"]
        < MIN_SALES_FOR_STRONG_CONFIDENCE
    ):
        score -= 10

    if position["liquidity_coverage"] < 0.75:
        score -= 10

    return max(0.0, min(100.0, score))


def health_status(score):
    if score >= 80:
        return "🟢 HEALTHY"

    if score >= 65:
        return "🟡 WATCH"

    if score >= 45:
        return "🟠 AT RISK"

    return "🔴 CRITICAL"


def confidence(position):
    sales = position["sales_count"]

    if sales >= 100:
        return 95.0

    if sales >= 50:
        return 90.0

    if sales >= 30:
        return 80.0

    if sales >= 14:
        return 70.0

    if sales >= 7:
        return 60.0

    return 45.0


def build_kpis(position):
    margin_score = min(
        position["margin"]
        / TARGET_MARGIN
        * 100,
        100,
    )

    liquidity_score = min(
        position["liquidity_coverage"]
        * 100,
        100,
    )

    credit_score = max(
        0,
        100
        - position["credit_ratio"] * 100,
    )

    supplier_score = max(
        0,
        100
        - position["supplier_ratio"] * 100,
    )

    sales_data_score = min(
        position["sales_count"]
        / MIN_SALES_FOR_STRONG_CONFIDENCE
        * 100,
        100,
    )

    inventory_score = (
        100
        if position["inventory"] == 0
        else max(
            0,
            100
            - min(
                position["inventory_ratio"]
                * 20,
                80,
            ),
        )
    )

    return {
        "margin_score": margin_score,
        "liquidity_score": liquidity_score,
        "credit_score": credit_score,
        "supplier_score": supplier_score,
        "sales_data_score": sales_data_score,
        "inventory_score": inventory_score,
    }


def print_kpi(
    name,
    value,
    target,
    status,
):
    print("-" * 40)
    print(f"KPI                 : {name}")
    print(f"Current             : {value}")
    print(f"Target              : {target}")
    print(f"Status              : {status}")


def main():
    try:
        conn = connect()

        try:
            position = build_position(conn)

        finally:
            conn.close()

        scores = build_kpis(position)

        health = calculate_health(position)

        confidence_value = confidence(
            position
        )

        supplier_gap = max(
            position["supplier"]
            - position["liquid"],
            0,
        )

        print("=" * 60)
        print("POS LEDGER NG V71")
        print("BUSINESS KPI INTELLIGENCE")
        print("=" * 60)

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
            f"{pct(position['margin'])}"
        )

        print(
            f"Liquid Funds         : "
            f"{money(position['liquid'])}"
        )

        print(
            f"Customer Credit      : "
            f"{money(position['credit'])}"
        )

        print(
            f"Supplier Liability   : "
            f"{money(position['supplier'])}"
        )

        print(
            f"Inventory Capital    : "
            f"{money(position['inventory'])}"
        )

        print(
            f"Recorded Sales       : "
            f"{position['sales_count']}"
        )

        print("\n" + "=" * 60)
        print("EXECUTIVE KPI HEALTH")
        print("=" * 60)

        print(
            f"Overall KPI Score    : "
            f"{health:.2f}/100"
        )

        print(
            f"KPI Health Status    : "
            f"{health_status(health)}"
        )

        print(
            f"Decision Confidence  : "
            f"{confidence_value:.2f}%"
        )

        print("\n" + "=" * 60)
        print("CORE BUSINESS KPIs")
        print("=" * 60)

        margin_status = (
            "🟢 TARGET MET"
            if position["margin"]
            >= TARGET_MARGIN
            else "🟠 BELOW TARGET"
        )

        print_kpi(
            "GROSS MARGIN",
            pct(position["margin"]),
            pct(TARGET_MARGIN),
            margin_status,
        )

        liquidity_status = (
            "🟢 COVERED"
            if position["liquidity_coverage"]
            >= 1
            else "🔴 GAP"
        )

        print_kpi(
            "LIQUIDITY COVERAGE",
            pct(position["liquidity_coverage"]),
            "100.00%",
            liquidity_status,
        )

        credit_status = (
            "🟢 LOW"
            if position["credit_ratio"] < 0.10
            else "🟠 ELEVATED"
        )

        print_kpi(
            "CUSTOMER CREDIT RATIO",
            pct(position["credit_ratio"]),
            "< 10.00%",
            credit_status,
        )

        supplier_status = (
            "🟢 CONTROLLED"
            if position["supplier_ratio"] < 0.25
            else "🟠 ELEVATED"
        )

        print_kpi(
            "SUPPLIER LIABILITY RATIO",
            pct(position["supplier_ratio"]),
            "< 25.00%",
            supplier_status,
        )

        sales_status = (
            "🟢 STRONG DATA"
            if position["sales_count"]
            >= MIN_SALES_FOR_STRONG_CONFIDENCE
            else "🟡 BUILDING DATA"
        )

        print_kpi(
            "SALES DATA",
            str(position["sales_count"]),
            f">= {MIN_SALES_FOR_STRONG_CONFIDENCE}",
            sales_status,
        )

        print("\n" + "=" * 60)
        print("OPERATING KPIs")
        print("=" * 60)

        print(
            f"Average Sale Value   : "
            f"{money(position['average_sale'])}"
        )

        print(
            f"Profit / Sale        : "
            f"{money(position['profit_per_sale'])}"
        )

        print(
            f"Credit / Revenue     : "
            f"{pct(position['credit_ratio'])}"
        )

        print(
            f"Supplier / Revenue   : "
            f"{pct(position['supplier_ratio'])}"
        )

        print(
            f"Inventory / Revenue  : "
            f"{pct(position['inventory_ratio'])}"
        )

        print("\n" + "=" * 60)
        print("KPI SCORECARD")
        print("=" * 60)

        print(
            f"Margin KPI Score      : "
            f"{scores['margin_score']:.2f}/100"
        )

        print(
            f"Liquidity KPI Score   : "
            f"{scores['liquidity_score']:.2f}/100"
        )

        print(
            f"Credit KPI Score      : "
            f"{scores['credit_score']:.2f}/100"
        )

        print(
            f"Supplier KPI Score    : "
            f"{scores['supplier_score']:.2f}/100"
        )

        print(
            f"Sales Data Score      : "
            f"{scores['sales_data_score']:.2f}/100"
        )

        print(
            f"Inventory KPI Score   : "
            f"{scores['inventory_score']:.2f}/100"
        )

        print("\n" + "=" * 60)
        print("MANAGEMENT KPI SIGNALS")
        print("=" * 60)

        if position["margin"] < TARGET_MARGIN:
            print(
                "🟠 MARGIN SIGNAL: "
                "Gross margin is below the 10% target."
            )

        if supplier_gap > 0:
            print(
                "🔴 LIQUIDITY SIGNAL: "
                f"Supplier payment gap is "
                f"{money(supplier_gap)}."
            )

        if position["credit"] > 0:
            print(
                "🟠 CREDIT SIGNAL: "
                f"{money(position['credit'])} "
                "is tied up in customer credit."
            )

        if position["inventory"] > 0:
            print(
                "🟡 INVENTORY SIGNAL: "
                f"{money(position['inventory'])} "
                "is tied up in inventory."
            )

        if (
            position["sales_count"]
            < MIN_SALES_FOR_STRONG_CONFIDENCE
        ):
            print(
                "🟡 DATA SIGNAL: "
                "More sales history is required "
                "for stronger intelligence."
            )

        print("\n" + "=" * 60)
        print("TOP KPI MANAGEMENT PRIORITIES")
        print("=" * 60)

        priorities = []

        if supplier_gap > 0:
            priorities.append(
                (
                    1,
                    "PROTECT LIQUIDITY",
                    money(supplier_gap),
                )
            )

        if position["credit"] > 0:
            priorities.append(
                (
                    2,
                    "COLLECT CUSTOMER CREDIT",
                    money(position["credit"]),
                )
            )

        if position["margin"] < TARGET_MARGIN:
            priorities.append(
                (
                    3,
                    "IMPROVE GROSS MARGIN",
                    pct(position["margin"]),
                )
            )

        if position["inventory"] > 0:
            priorities.append(
                (
                    4,
                    "CONTROL INVENTORY CAPITAL",
                    money(position["inventory"]),
                )
            )

        if (
            position["sales_count"]
            < MIN_SALES_FOR_STRONG_CONFIDENCE
        ):
            priorities.append(
                (
                    5,
                    "STRENGTHEN SALES DATA",
                    str(position["sales_count"]),
                )
            )

        for rank, action, value in priorities:
            print(
                f"{rank}. {action:<32} "
                f"Signal: {value}"
            )

        print("\n" + "=" * 60)
        print("MANAGEMENT INTERPRETATION")
        print("=" * 60)

        if health < 65:
            print(
                "Overall KPI performance indicates "
                "that management attention is required."
            )
        else:
            print(
                "Overall KPI performance is within "
                "an acceptable management range."
            )

        if supplier_gap > 0:
            print(
                "Liquidity protection should remain "
                "the first financial priority."
            )

        if position["margin"] < TARGET_MARGIN:
            print(
                "Pricing and product profitability "
                "should be improved before aggressive expansion."
            )

        if position["credit"] > 0:
            print(
                "Customer credit collection can improve "
                "available operating liquidity."
            )

        print("\n" + "=" * 60)
        print("V71 SAFETY STATUS")
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

    except Exception as exc:
        print("=" * 60)
        print("V71 ERROR")
        print("=" * 60)
        print(str(exc))
        print("=" * 60)


if __name__ == "__main__":
    main()
