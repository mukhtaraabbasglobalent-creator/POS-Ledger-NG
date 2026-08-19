"""
POS LEDGER NG V76
MANAGEMENT PERFORMANCE & DATA INTEGRITY INTELLIGENCE

READ-ONLY.
This module does not modify sales, products, inventory, balances,
credit, suppliers, or expenses.
"""

from pathlib import Path
import sqlite3


DB_PATH = Path("data/posledger.db")

TARGET_MARGIN = 10.0
TARGET_CREDIT_EXPOSURE = 20.0
REFERENCE_SALES = 20


def money(value):
    return f"₦{value:,.2f}"


def pct(value):
    return f"{value:.2f}%"


def score(value):
    return f"{max(0.0, min(100.0, value)):.2f}/100"


def table_exists(conn, table):
    return conn.execute(
        "SELECT 1 FROM sqlite_master "
        "WHERE type='table' AND name=?",
        (table,),
    ).fetchone() is not None


def columns(conn, table):
    return {
        row[1]
        for row in conn.execute(
            f"PRAGMA table_info({table})"
        ).fetchall()
    }


def find_column(conn, table, names):
    if not table_exists(conn, table):
        return None

    available = columns(conn, table)

    for name in names:
        if name in available:
            return name

    return None


def sum_column(conn, table, names):
    column = find_column(conn, table, names)

    if not column:
        return 0.0

    row = conn.execute(
        f"SELECT COALESCE(SUM({column}),0) FROM {table}"
    ).fetchone()

    return float(row[0] or 0)


def count_rows(conn, table):
    if not table_exists(conn, table):
        return 0

    return int(
        conn.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]
    )


def get_revenue(conn):
    return sum_column(
        conn,
        "sales",
        [
            "total_amount",
            "grand_total",
            "sale_amount",
            "amount",
            "total",
        ],
    )


def get_sales_cost(conn):
    return sum_column(
        conn,
        "sales",
        [
            "cost_amount",
            "total_cost",
            "cost",
            "buying_cost",
            "cost_price",
        ],
    )


def get_liquid_funds(conn):
    possible_tables = [
        "balance",
        "balances",
        "cash_balance",
        "financial_balance",
    ]

    possible_columns = [
        "balance",
        "amount",
        "liquid_funds",
        "cash_balance",
        "current_balance",
        "available_balance",
    ]

    for table in possible_tables:
        column = find_column(conn, table, possible_columns)

        if column:
            row = conn.execute(
                f"SELECT {column} FROM {table} "
                f"ORDER BY rowid DESC LIMIT 1"
            ).fetchone()

            if row:
                return float(row[0] or 0)

    return 0.0


def get_customer_credit(conn):
    for table in [
        "customer_credit",
        "customer_credits",
        "credits",
    ]:
        value = sum_column(
            conn,
            table,
            [
                "outstanding",
                "outstanding_credit",
                "balance",
                "credit_amount",
                "amount",
            ],
        )

        if value:
            return value

    return 0.0


def get_supplier_liability(conn):
    for table in [
        "suppliers",
        "supplier_credit",
        "supplier_liabilities",
        "purchases",
    ]:
        value = sum_column(
            conn,
            table,
            [
                "outstanding",
                "outstanding_balance",
                "balance",
                "amount_due",
                "liability",
            ],
        )

        if value:
            return value

    return 0.0


def get_inventory_capital(conn):
    if not table_exists(conn, "products"):
        return 0.0

    cost_column = find_column(
        conn,
        "products",
        [
            "buying_price",
            "cost_price",
            "purchase_price",
            "buying_cost",
        ],
    )

    stock_column = find_column(
        conn,
        "products",
        [
            "stock",
            "current_stock",
            "quantity",
            "opening_stock",
        ],
    )

    if not cost_column or not stock_column:
        return 0.0

    row = conn.execute(
        f"""
        SELECT COALESCE(
            SUM({cost_column} * {stock_column}),
            0
        )
        FROM products
        """
    ).fetchone()

    return float(row[0] or 0)


def calculate_health(
    margin_score,
    liquidity_score,
    credit_score,
    inventory_score,
    sales_score,
):
    return (
        margin_score
        + liquidity_score
        + credit_score
        + inventory_score
        + sales_score
    ) / 5


def main():

    print("=" * 60)
    print("POS LEDGER NG V76")
    print("MANAGEMENT PERFORMANCE & DATA INTEGRITY INTELLIGENCE")
    print("=" * 60)

    if not DB_PATH.exists():
        print()
        print("DATABASE ERROR")
        print("=" * 60)
        print(f"Database not found: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)

    try:

        # =====================================================
        # SOURCE DATA
        # =====================================================

        revenue = get_revenue(conn)
        recorded_sales = count_rows(conn, "sales")

        sales_cost = get_sales_cost(conn)

        if sales_cost > revenue:
            sales_cost = revenue

        gross_profit = max(0.0, revenue - sales_cost)

        gross_margin = (
            gross_profit / revenue * 100
            if revenue > 0
            else 0.0
        )

        liquid_funds = get_liquid_funds(conn)
        customer_credit = get_customer_credit(conn)
        supplier_liability = get_supplier_liability(conn)
        inventory_capital = get_inventory_capital(conn)

        supplier_gap = max(
            0.0,
            supplier_liability - liquid_funds,
        )

        liquidity_coverage = (
            min(
                100.0,
                liquid_funds / supplier_liability * 100,
            )
            if supplier_liability > 0
            else 100.0
        )

        credit_exposure = (
            customer_credit / revenue * 100
            if revenue > 0
            else 0.0
        )

        inventory_ratio = (
            inventory_capital / revenue * 100
            if revenue > 0
            else 0.0
        )

        # =====================================================
        # KPI SCORES
        # =====================================================

        margin_score = min(
            100.0,
            max(
                0.0,
                gross_margin / TARGET_MARGIN * 100,
            ),
        )

        liquidity_score = liquidity_coverage

        if credit_exposure <= TARGET_CREDIT_EXPOSURE:
            credit_score = 100.0
        else:
            credit_score = max(
                0.0,
                100.0
                - (
                    (
                        credit_exposure
                        - TARGET_CREDIT_EXPOSURE
                    )
                    / TARGET_CREDIT_EXPOSURE
                    * 100
                ),
            )

        if inventory_ratio <= 50:
            inventory_score = 100.0
        elif inventory_ratio >= 150:
            inventory_score = 40.0
        else:
            inventory_score = (
                100.0
                - (
                    (inventory_ratio - 50)
                    / 100
                    * 60
                )
            )

        sales_score = min(
            100.0,
            recorded_sales
            / REFERENCE_SALES
            * 100,
        )

        overall_score = calculate_health(
            margin_score,
            liquidity_score,
            credit_score,
            inventory_score,
            sales_score,
        )

        # =====================================================
        # DATA INTEGRITY CHECKS
        # =====================================================

        integrity_flags = []

        if revenue > 0 and sales_cost == 0:
            integrity_flags.append(
                "SALES COST DATA NOT AVAILABLE"
            )

        if revenue > 0 and gross_profit == 0:
            integrity_flags.append(
                "GROSS PROFIT CALCULATED AS ZERO"
            )

        if revenue > 0 and inventory_capital > revenue:
            integrity_flags.append(
                "INVENTORY CAPITAL EXCEEDS REVENUE"
            )

        if supplier_gap > 0:
            integrity_flags.append(
                "SUPPLIER LIABILITY EXCEEDS LIQUID FUNDS"
            )

        if recorded_sales < REFERENCE_SALES:
            integrity_flags.append(
                "LIMITED SALES HISTORY"
            )

        # =====================================================
        # STATUS
        # =====================================================

        if overall_score >= 85:
            status = "🟢 STRONG"
        elif overall_score >= 70:
            status = "🟡 WATCH"
        elif overall_score >= 50:
            status = "🟠 AT RISK"
        else:
            status = "🔴 CRITICAL"

        # =====================================================
        # OUTPUT
        # =====================================================

        print()
        print("=" * 60)
        print("CURRENT BUSINESS POSITION")
        print("=" * 60)

        print(f"Revenue              : {money(revenue)}")
        print(f"Sales Cost           : {money(sales_cost)}")
        print(f"Gross Profit         : {money(gross_profit)}")
        print(f"Gross Margin         : {pct(gross_margin)}")
        print(f"Liquid Funds         : {money(liquid_funds)}")
        print(f"Customer Credit      : {money(customer_credit)}")
        print(f"Supplier Liability   : {money(supplier_liability)}")
        print(f"Supplier Gap         : {money(supplier_gap)}")
        print(f"Inventory Capital    : {money(inventory_capital)}")
        print(f"Recorded Sales       : {recorded_sales}")

        print()
        print("=" * 60)
        print("MANAGEMENT KPI SCORECARD")
        print("=" * 60)

        print("----------------------------------------")
        print("1. GROSS MARGIN KPI")
        print(f"Current              : {pct(gross_margin)}")
        print(f"Target               : {pct(TARGET_MARGIN)}")
        print(
            f"Gap                  : "
            f"{pct(max(0, TARGET_MARGIN - gross_margin))}"
        )
        print(f"Score                : {score(margin_score)}")

        print("----------------------------------------")
        print("2. LIQUIDITY COVERAGE KPI")
        print(f"Coverage             : {pct(liquidity_coverage)}")
        print(f"Supplier Gap         : {money(supplier_gap)}")
        print(f"Score                : {score(liquidity_score)}")

        print("----------------------------------------")
        print("3. CUSTOMER CREDIT KPI")
        print(f"Outstanding Credit   : {money(customer_credit)}")
        print(f"Exposure             : {pct(credit_exposure)}")
        print(
            f"Target Exposure      : "
            f"{pct(TARGET_CREDIT_EXPOSURE)}"
        )
        print(f"Score                : {score(credit_score)}")

        print("----------------------------------------")
        print("4. INVENTORY EFFICIENCY KPI")
        print(f"Inventory Capital    : {money(inventory_capital)}")
        print(f"Inventory/Revenue    : {pct(inventory_ratio)}")
        print(f"Score                : {score(inventory_score)}")

        print("----------------------------------------")
        print("5. SALES DATA KPI")
        print(f"Recorded Sales       : {recorded_sales}")
        print(f"Reference Level      : {REFERENCE_SALES}")
        print(f"Score                : {score(sales_score)}")

        print()
        print("=" * 60)
        print("OVERALL MANAGEMENT PERFORMANCE")
        print("=" * 60)

        print(f"Overall Score        : {score(overall_score)}")
        print(f"Business Status      : {status}")

        print()
        print("=" * 60)
        print("DATA INTEGRITY CHECK")
        print("=" * 60)

        if integrity_flags:
            print("Integrity Status      : 🟡 REVIEW REQUIRED")
            for flag in integrity_flags:
                print(f"- {flag}")
        else:
            print(
                "Integrity Status      : 🟢 NO MAJOR FLAGS"
            )

        print()
        print("=" * 60)
        print("TOP MANAGEMENT ACTIONS")
        print("=" * 60)

        rank = 1

        if supplier_gap > 0:
            print(
                f"{rank}. PROTECT LIQUIDITY"
            )
            print(
                f"   Supplier gap: {money(supplier_gap)}"
            )
            rank += 1

        if gross_margin < TARGET_MARGIN:
            print(
                f"{rank}. IMPROVE GROSS MARGIN"
            )
            print(
                f"   Margin gap: "
                f"{pct(TARGET_MARGIN - gross_margin)}"
            )
            rank += 1

        if customer_credit > 0:
            print(
                f"{rank}. COLLECT CUSTOMER CREDIT"
            )
            print(
                f"   Recoverable credit: "
                f"{money(customer_credit)}"
            )
            rank += 1

        if inventory_ratio > 80:
            print(
                f"{rank}. CONTROL INVENTORY CAPITAL"
            )
            print(
                f"   Inventory capital: "
                f"{money(inventory_capital)}"
            )
            rank += 1

        if recorded_sales < REFERENCE_SALES:
            print(
                f"{rank}. STRENGTHEN SALES DATA"
            )
            print(
                f"   Additional reference sales: "
                f"{REFERENCE_SALES - recorded_sales}"
            )

        print()
        print("=" * 60)
        print("V76 EXECUTIVE INTERPRETATION")
        print("=" * 60)

        print(
            "V76 independently evaluates the underlying "
            "POS Ledger NG database rather than trusting "
            "previous analytics output."
        )

        if gross_margin < TARGET_MARGIN:
            print(
                f"Profitability is below target: "
                f"{pct(gross_margin)} versus "
                f"{pct(TARGET_MARGIN)}."
            )

        if supplier_gap > 0:
            print(
                f"Liquidity pressure exists because supplier "
                f"obligations exceed liquid funds by "
                f"{money(supplier_gap)}."
            )

        if customer_credit > 0:
            print(
                f"Customer credit of {money(customer_credit)} "
                "represents potential recoverable liquidity."
            )

        if inventory_ratio > 80:
            print(
                f"Inventory represents {pct(inventory_ratio)} "
                "of revenue and should be monitored for turnover."
            )

        print()
        print("=" * 60)
        print("V76 SAFETY STATUS")
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

    finally:
        conn.close()


if __name__ == "__main__":
    main()
