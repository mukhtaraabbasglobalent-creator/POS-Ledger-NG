import sqlite3
from pathlib import Path


# ============================================================
# POS LEDGER NG V91
# BUSINESS RISK & HEALTH INTELLIGENCE
# READ-ONLY ANALYTICS
# ============================================================

DB_PATH = Path("data/posledger.db")

TARGET_MARGIN = 10.00
REFERENCE_SALES = 20.0


def money(value):
    return f"₦{value:,.2f}"


def percent(value):
    return f"{value:.2f}%"


def clamp(value, minimum=0.0, maximum=100.0):
    return max(minimum, min(maximum, value))


def get_columns(conn, table):
    try:
        rows = conn.execute(
            f"PRAGMA table_info({table})"
        ).fetchall()

        return {row[1] for row in rows}

    except Exception:
        return set()


def table_exists(conn, table):
    try:
        row = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            AND name=?
            """,
            (table,)
        ).fetchone()

        return row is not None

    except Exception:
        return False


def safe_sum(conn, table, column):
    if not table_exists(conn, table):
        return 0.0

    columns = get_columns(conn, table)

    if column not in columns:
        return 0.0

    try:
        row = conn.execute(
            f"""
            SELECT COALESCE(SUM({column}), 0)
            FROM {table}
            """
        ).fetchone()

        return float(row[0] or 0)

    except Exception:
        return 0.0


def safe_count(conn, table):
    if not table_exists(conn, table):
        return 0

    try:
        row = conn.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()

        return int(row[0] or 0)

    except Exception:
        return 0


def find_column(columns, candidates):
    for candidate in candidates:
        if candidate in columns:
            return candidate

    return None


def calculate_score(current, target):
    if target <= 0:
        return 100.0

    return clamp((current / target) * 100)


def main():

    print("=" * 60)
    print("POS LEDGER NG V91")
    print("BUSINESS RISK & HEALTH INTELLIGENCE")
    print("=" * 60)

    # ========================================================
    # DATABASE CHECK
    # ========================================================

    if not DB_PATH.exists():

        print()
        print("❌ DATABASE NOT FOUND")
        print(f"Expected database: {DB_PATH}")
        print()
        print("Check that you are inside ~/POS-Ledger-NG")
        return

    conn = sqlite3.connect(DB_PATH)

    # ========================================================
    # DISCOVER DATABASE STRUCTURE
    # ========================================================

    sales_cols = get_columns(conn, "sales")
    products_cols = get_columns(conn, "products")
    expenses_cols = get_columns(conn, "expenses")
    credit_cols = get_columns(conn, "customer_credit")
    supplier_cols = get_columns(conn, "suppliers")

    balance_tables = [
        "balances",
        "balance",
        "cash_balance",
        "business_balance"
    ]

    balance_table = None

    for table in balance_tables:

        if table_exists(conn, table):
            balance_table = table
            break

    # ========================================================
    # VERIFIED SALES
    # ========================================================

    sales_count = safe_count(conn, "sales")

    revenue = safe_sum(
        conn,
        "sales",
        "total_amount"
    )

    # ========================================================
    # VERIFIED COGS
    # ========================================================

    if "cogs" in sales_cols:

        cogs = safe_sum(
            conn,
            "sales",
            "cogs"
        )

        cogs_status = "VERIFIED"

    elif "buying_price" in sales_cols and "quantity" in sales_cols:

        try:

            row = conn.execute(
                """
                SELECT
                    COALESCE(SUM(quantity * buying_price), 0)
                FROM sales
                """
            ).fetchone()

            cogs = float(row[0] or 0)

            cogs_status = "DERIVED"

        except Exception:

            cogs = 0.0
            cogs_status = "UNAVAILABLE"

    else:

        cogs = 0.0
        cogs_status = "UNAVAILABLE"

    # ========================================================
    # GROSS PROFIT
    # ========================================================

    if "gross_profit" in sales_cols:

        gross_profit = safe_sum(
            conn,
            "sales",
            "gross_profit"
        )

        gross_profit_status = "VERIFIED"

    else:

        gross_profit = revenue - cogs
        gross_profit_status = "CALCULATED"

    # ========================================================
    # GROSS MARGIN
    # ========================================================

    if revenue > 0:

        gross_margin = (
            gross_profit / revenue
        ) * 100

    else:

        gross_margin = 0.0

    # ========================================================
    # OPERATING EXPENSES
    # ========================================================

    expense_column = find_column(
        expenses_cols,
        [
            "amount",
            "expense_amount",
            "total_amount",
            "cost"
        ]
    )

    if expense_column:

        operating_expenses = safe_sum(
            conn,
            "expenses",
            expense_column
        )

        expense_status = "VERIFIED"

    else:

        operating_expenses = 0.0
        expense_status = "NOT DETECTED"

    # ========================================================
    # TRUE NET OPERATING PROFIT
    # ========================================================

    net_profit = (
        gross_profit -
        operating_expenses
    )

    if revenue > 0:

        net_margin = (
            net_profit / revenue
        ) * 100

    else:

        net_margin = 0.0

    # ========================================================
    # LIQUID FUNDS
    # ========================================================

    liquid_funds = 0.0
    balance_status = "NOT DETECTED"

    if balance_table:

        balance_cols = get_columns(
            conn,
            balance_table
        )

        balance_column = find_column(
            balance_cols,
            [
                "balance",
                "amount",
                "current_balance",
                "liquid_funds",
                "cash_balance"
            ]
        )

        if balance_column:

            liquid_funds = safe_sum(
                conn,
                balance_table,
                balance_column
            )

            balance_status = "DETECTED"

    # ========================================================
    # CUSTOMER CREDIT
    # ========================================================

    credit_column = find_column(
        credit_cols,
        [
            "amount",
            "credit_amount",
            "balance",
            "outstanding",
            "outstanding_amount",
            "amount_due"
        ]
    )

    if credit_column:

        customer_credit = safe_sum(
            conn,
            "customer_credit",
            credit_column
        )

        credit_status = "VERIFIED"

    else:

        customer_credit = 0.0
        credit_status = "NOT DETECTED"

    # ========================================================
    # SUPPLIER LIABILITY
    # ========================================================

    supplier_column = find_column(
        supplier_cols,
        [
            "balance",
            "outstanding",
            "outstanding_balance",
            "amount_due",
            "payable",
            "liability"
        ]
    )

    if supplier_column:

        supplier_liability = safe_sum(
            conn,
            "suppliers",
            supplier_column
        )

        supplier_status = "VERIFIED"

    else:

        supplier_liability = 0.0
        supplier_status = "NOT DETECTED"

    # ========================================================
    # INVENTORY CAPITAL
    # ========================================================

    inventory_capital = 0.0
    inventory_status = "NOT DETECTED"

    if (
        "current_stock" in products_cols
        and "buying_price" in products_cols
    ):

        try:

            row = conn.execute(
                """
                SELECT
                    COALESCE(
                        SUM(
                            COALESCE(current_stock, 0)
                            *
                            COALESCE(buying_price, 0)
                        ),
                        0
                    )
                FROM products
                """
            ).fetchone()

            inventory_capital = float(
                row[0] or 0
            )

            inventory_status = "VERIFIED"

        except Exception:

            inventory_capital = 0.0

    # ========================================================
    # PROFITABILITY SCORE
    # ========================================================

    profitability_score = calculate_score(
        net_margin,
        TARGET_MARGIN
    )

    # ========================================================
    # LIQUIDITY SCORE
    # ========================================================

    if supplier_liability > 0:

        liquidity_coverage = (
            liquid_funds /
            supplier_liability
        ) * 100

    else:

        liquidity_coverage = 100.0

    liquidity_score = clamp(
        liquidity_coverage
    )

    # ========================================================
    # CREDIT EXPOSURE
    # ========================================================

    if revenue > 0:

        credit_exposure = (
            customer_credit /
            revenue
        ) * 100

    else:

        credit_exposure = 0.0

    # Target credit exposure = 20%

    if credit_exposure <= 20:

        credit_score = 100.0

    else:

        credit_score = clamp(
            100 -
            ((credit_exposure - 20) * 5)
        )

    # ========================================================
    # INVENTORY SCORE
    # ========================================================

    if revenue > 0:

        inventory_ratio = (
            inventory_capital /
            revenue
        ) * 100

    else:

        inventory_ratio = 0.0

    if inventory_ratio <= 80:

        inventory_score = 100.0

    elif inventory_ratio <= 100:

        inventory_score = (
            100 -
            ((inventory_ratio - 80) * 1.25)
        )

    else:

        inventory_score = (
            75 -
            ((inventory_ratio - 100) * 0.50)
        )

    inventory_score = clamp(
        inventory_score
    )

    # ========================================================
    # SALES DATA SCORE
    # ========================================================

    sales_data_score = clamp(
        (sales_count /
         REFERENCE_SALES) * 100
    )

    # ========================================================
    # EXPENSE DATA SCORE
    # ========================================================

    if expense_status == "VERIFIED":

        expense_data_score = 100.0

    else:

        expense_data_score = 70.0

    # ========================================================
    # OVERALL HEALTH SCORE
    # ========================================================

    overall_score = (

        profitability_score * 0.30

        + liquidity_score * 0.20

        + credit_score * 0.15

        + inventory_score * 0.15

        + sales_data_score * 0.10

        + expense_data_score * 0.10

    )

    overall_score = clamp(
        overall_score
    )

    # ========================================================
    # RISK SCORE
    # ========================================================

    risk_score = 100 - overall_score

    # ========================================================
    # HEALTH STATUS
    # ========================================================

    if overall_score >= 80:

        health_status = "🟢 STRONG"

    elif overall_score >= 65:

        health_status = "🟡 WATCH"

    elif overall_score >= 50:

        health_status = "🟠 AT RISK"

    else:

        health_status = "🔴 CRITICAL"

    # ========================================================
    # RISK CLASSIFICATION
    # ========================================================

    if risk_score <= 20:

        risk_status = "🟢 LOW RISK"

    elif risk_score <= 35:

        risk_status = "🟡 MODERATE RISK"

    elif risk_score <= 50:

        risk_status = "🟠 ELEVATED RISK"

    else:

        risk_status = "🔴 HIGH RISK"

    # ========================================================
    # RISK FINDINGS
    # ========================================================

    risks = []

    if net_margin < TARGET_MARGIN:

        margin_gap = (
            TARGET_MARGIN -
            net_margin
        )

        risks.append(
            (
                "HIGH",
                f"Net margin is "
                f"{percent(margin_gap)} "
                f"below the {TARGET_MARGIN:.2f}% target."
            )
        )

    if customer_credit > 0:

        risks.append(
            (
                "MEDIUM",
                f"Customer credit of "
                f"{money(customer_credit)} "
                f"represents potential recoverable liquidity."
            )
        )

    if inventory_ratio > 80:

        risks.append(
            (
                "MEDIUM",
                f"Inventory capital represents "
                f"{percent(inventory_ratio)} "
                f"of verified revenue."
            )
        )

    if supplier_liability > liquid_funds:

        gap = (
            supplier_liability -
            liquid_funds
        )

        risks.append(
            (
                "HIGH",
                f"Supplier obligations exceed liquid funds by "
                f"{money(gap)}."
            )
        )

    if sales_count < REFERENCE_SALES:

        risks.append(
            (
                "LOW",
                f"Only {sales_count} sales are available; "
                f"{int(REFERENCE_SALES - sales_count)} "
                f"more would strengthen the reference dataset."
            )
        )

    if expense_status != "VERIFIED":

        risks.append(
            (
                "MEDIUM",
                "Operating expense data is not fully detected."
            )
        )

    # ========================================================
    # MANAGEMENT PRIORITIES
    # ========================================================

    priorities = []

    if net_margin < TARGET_MARGIN:

        priorities.append(
            (
                "HIGH",
                "Improve profitability",
                f"Net margin is {percent(net_margin)} "
                f"against a {TARGET_MARGIN:.2f}% target."
            )
        )

    if customer_credit > 0:

        priorities.append(
            (
                "MEDIUM",
                "Collect customer credit",
                f"Potential recovery: "
                f"{money(customer_credit)}."
            )
        )

    if inventory_ratio > 80:

        priorities.append(
            (
                "MEDIUM",
                "Monitor inventory capital",
                f"Capital tied in inventory: "
                f"{money(inventory_capital)}."
            )
        )

    if supplier_liability > liquid_funds:

        priorities.append(
            (
                "HIGH",
                "Protect liquidity",
                "Supplier obligations exceed available liquid funds."
            )
        )

    if sales_count < REFERENCE_SALES:

        priorities.append(
            (
                "LOW",
                "Strengthen sales data",
                f"Reference gap: "
                f"{int(REFERENCE_SALES - sales_count)} sales."
            )
        )

    if not priorities:

        priorities.append(
            (
                "INFO",
                "Maintain financial discipline",
                "No immediate management priority detected."
            )
        )

    # ========================================================
    # VERIFIED FINANCIAL POSITION
    # ========================================================

    print()
    print("=" * 60)
    print("VERIFIED FINANCIAL POSITION")
    print("=" * 60)

    print(
        f"Verified Sales       : {sales_count}"
    )

    print(
        f"Verified Revenue     : {money(revenue)}"
    )

    print(
        f"Verified COGS        : {money(cogs)}"
    )

    print(
        f"Gross Profit         : {money(gross_profit)}"
    )

    print(
        f"Operating Expenses   : {money(operating_expenses)}"
    )

    print(
        f"Net Operating Profit : {money(net_profit)}"
    )

    print(
        f"Net Margin           : {percent(net_margin)}"
    )

    print(
        f"Liquid Funds         : {money(liquid_funds)}"
    )

    print(
        f"Customer Credit      : {money(customer_credit)}"
    )

    print(
        f"Supplier Liability   : {money(supplier_liability)}"
    )

    print(
        f"Inventory Capital    : {money(inventory_capital)}"
    )

    # ========================================================
    # KPI SCORECARD
    # ========================================================

    print()
    print("=" * 60)
    print("BUSINESS HEALTH SCORECARD")
    print("=" * 60)

    print("----------------------------------------")
    print("1. PROFITABILITY HEALTH")

    print(
        f"Net Margin           : {percent(net_margin)}"
    )

    print(
        f"Target Margin        : {percent(TARGET_MARGIN)}"
    )

    print(
        f"Score                : {profitability_score:.2f}/100"
    )

    print("----------------------------------------")
    print("2. LIQUIDITY HEALTH")

    print(
        f"Liquid Funds         : {money(liquid_funds)}"
    )

    print(
        f"Supplier Liability   : {money(supplier_liability)}"
    )

    print(
        f"Coverage             : {percent(liquidity_coverage)}"
    )

    print(
        f"Score                : {liquidity_score:.2f}/100"
    )

    print("----------------------------------------")
    print("3. CUSTOMER CREDIT HEALTH")

    print(
        f"Outstanding Credit   : {money(customer_credit)}"
    )

    print(
        f"Credit Exposure      : {percent(credit_exposure)}"
    )

    print(
        "Target Exposure      : 20.00%"
    )

    print(
        f"Score                : {credit_score:.2f}/100"
    )

    print("----------------------------------------")
    print("4. INVENTORY HEALTH")

    print(
        f"Inventory Capital    : {money(inventory_capital)}"
    )

    print(
        f"Inventory/Revenue    : {percent(inventory_ratio)}"
    )

    print(
        f"Score                : {inventory_score:.2f}/100"
    )

    print("----------------------------------------")
    print("5. SALES DATA HEALTH")

    print(
        f"Recorded Sales       : {sales_count}"
    )

    print(
        f"Reference Level      : {int(REFERENCE_SALES)}"
    )

    print(
        f"Score                : {sales_data_score:.2f}/100"
    )

    print("----------------------------------------")
    print("6. EXPENSE DATA HEALTH")

    print(
        f"Expense Records      : "
        f"{safe_count(conn, 'expenses')}"
    )

    print(
        f"Operating Expenses   : "
        f"{money(operating_expenses)}"
    )

    print(
        f"Data Score           : "
        f"{expense_data_score:.2f}/100"
    )

    # ========================================================
    # OVERALL HEALTH
    # ========================================================

    print()
    print("=" * 60)
    print("OVERALL BUSINESS HEALTH")
    print("=" * 60)

    print(
        f"Overall Health Score : "
        f"{overall_score:.2f}/100"
    )

    print(
        f"Risk Score           : "
        f"{risk_score:.2f}/100"
    )

    print(
        f"Business Status      : "
        f"{health_status}"
    )

    print(
        f"Risk Classification  : "
        f"{risk_status}"
    )

    # ========================================================
    # RISK FINDINGS
    # ========================================================

    print()
    print("=" * 60)
    print("RISK & HEALTH FINDINGS")
    print("=" * 60)

    if risks:

        for index, (level, message) in enumerate(
            risks,
            start=1
        ):

            print(
                f"{index}. [{level}] {message}"
            )

    else:

        print(
            "No major risk findings detected."
        )

    # ========================================================
    # MANAGEMENT PRIORITIES
    # ========================================================

    print()
    print("=" * 60)
    print("MANAGEMENT PRIORITIES")
    print("=" * 60)

    for index, (
        level,
        title,
        reason
    ) in enumerate(
        priorities,
        start=1
    ):

        print(
            f"{index}. [{level}] {title}"
        )

        print(
            f"   {reason}"
        )

    # ========================================================
    # EXECUTIVE DECISION
    # ========================================================

    print()
    print("=" * 60)
    print("V91 EXECUTIVE DECISION")
    print("=" * 60)

    if overall_score >= 80:

        decision = (
            "🟢 BUSINESS HEALTH STRONG — "
            "MAINTAIN DISCIPLINE"
        )

    elif overall_score >= 65:

        decision = (
            "🟡 BUSINESS REQUIRES ACTIVE "
            "MONITORING"
        )

    elif overall_score >= 50:

        decision = (
            "🟠 RISK REDUCTION REQUIRED"
        )

    else:

        decision = (
            "🔴 IMMEDIATE MANAGEMENT "
            "INTERVENTION REQUIRED"
        )

    print(decision)

    # ========================================================
    # MANAGEMENT INTERPRETATION
    # ========================================================

    print()
    print("=" * 60)
    print("V91 MANAGEMENT INTERPRETATION")
    print("=" * 60)

    print(
        "V91 combines verified profitability, "
        "liquidity, customer credit, inventory "
        "capital, sales activity and operating "
        "expenses into one business-health view."
    )

    print(
        "The health score is an analytical management "
        "indicator and is not a financial guarantee."
    )

    print(
        "Risk signals should support management "
        "decisions rather than automatically executing "
        "transactions."
    )

    # ========================================================
    # DATA INTEGRITY
    # ========================================================

    print()
    print("=" * 60)
    print("V91 DATA INTEGRITY STATUS")
    print("=" * 60)

    print(
        f"COGS source          : {cogs_status}"
    )

    print(
        f"Gross profit source  : {gross_profit_status}"
    )

    print(
        f"Expense source       : {expense_status}"
    )

    print(
        f"Balance source       : {balance_status}"
    )

    print(
        f"Credit source        : {credit_status}"
    )

    print(
        f"Supplier source      : {supplier_status}"
    )

    print(
        f"Inventory source     : {inventory_status}"
    )

    print(
        "Historical COGS      : V81/V82"
    )

    print(
        "Pricing intelligence : V83/V84"
    )

    print(
        "Demand intelligence  : V85"
    )

    print(
        "Inventory intelligence : V86"
    )

    print(
        "Working capital      : V87"
    )

    print(
        "Financial intelligence : V88"
    )

    print(
        "Expense intelligence : V89"
    )

    print(
        "Net profitability    : V90"
    )

    print(
        "Automatic changes    : NO"
    )

    # ========================================================
    # SAFETY
    # ========================================================

    print()
    print("=" * 60)
    print("V91 SAFETY STATUS")
    print("=" * 60)

    print(
        "Mode                : READ-ONLY"
    )

    print(
        "Database modified   : NO"
    )

    print(
        "Sales modified      : NO"
    )

    print(
        "Products modified   : NO"
    )

    print(
        "Inventory modified  : NO"
    )

    print(
        "Balance modified    : NO"
    )

    print(
        "Credit modified     : NO"
    )

    print(
        "Suppliers modified  : NO"
    )

    print(
        "Expenses modified   : NO"
    )

    print("=" * 60)

    conn.close()


if __name__ == "__main__":
    main()
