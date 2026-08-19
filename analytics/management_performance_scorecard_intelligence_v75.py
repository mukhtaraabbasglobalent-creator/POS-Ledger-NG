"""
POS LEDGER NG V75
MANAGEMENT PERFORMANCE SCORECARD INTELLIGENCE

READ-ONLY MANAGEMENT INTELLIGENCE
Does not modify database records.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


DB_PATH = Path("data/posledger.db")

TARGET_MARGIN = 10.0
TARGET_LIQUIDITY_COVERAGE = 100.0
TARGET_CREDIT_EXPOSURE = 20.0
REFERENCE_SALES = 20


def money(value):
    return f"₦{value:,.2f}"


def percent(value):
    return f"{value:.2f}%"


def connect():
    return sqlite3.connect(DB_PATH)


def table_exists(conn, table):
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None


def table_columns(conn, table):
    return {
        row[1]
        for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
    }


def first_column(columns, candidates):
    for candidate in candidates:
        if candidate in columns:
            return candidate
    return None


def get_sum(conn, table, amount_candidates):
    if not table_exists(conn, table):
        return 0.0

    columns = table_columns(conn, table)
    amount_column = first_column(columns, amount_candidates)

    if not amount_column:
        return 0.0

    row = conn.execute(
        f"SELECT COALESCE(SUM({amount_column}), 0) FROM {table}"
    ).fetchone()

    return float(row[0] or 0)


def get_count(conn, table):
    if not table_exists(conn, table):
        return 0

    return int(
        conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    )


def get_business_position(conn):
    revenue = get_sum(
        conn,
        "sales",
        ["total_amount", "amount", "sale_amount", "grand_total", "total"],
    )

    cost = get_sum(
        conn,
        "sales",
        ["cost_amount", "total_cost", "cost", "buying_cost"],
    )

    gross_profit = revenue - cost

    # If sales cost is not stored, use the known product/inventory
    # structure where possible.
    if revenue > 0 and gross_profit == revenue:
        gross_profit = 0.0

    margin = (gross_profit / revenue * 100) if revenue else 0.0

    liquid_funds = 0.0

    for table in ["balance", "balances", "cash_balance"]:
        if table_exists(conn, table):
            columns = table_columns(conn, table)

            amount_column = first_column(
                columns,
                [
                    "balance",
                    "amount",
                    "liquid_funds",
                    "cash_balance",
                    "current_balance",
                ],
            )

            if amount_column:
                row = conn.execute(
                    f"SELECT {amount_column} "
                    f"FROM {table} "
                    f"ORDER BY rowid DESC LIMIT 1"
                ).fetchone()

                if row:
                    liquid_funds = float(row[0] or 0)
                    break

    customer_credit = get_sum(
        conn,
        "customer_credit",
        ["amount", "balance", "outstanding", "credit_amount"],
    )

    if customer_credit == 0:
        customer_credit = get_sum(
            conn,
            "credits",
            ["amount", "balance", "outstanding", "credit_amount"],
        )

    supplier_liability = get_sum(
        conn,
        "suppliers",
        ["balance", "outstanding", "liability", "amount_due"],
    )

    inventory_capital = 0.0

    if table_exists(conn, "products"):
        columns = table_columns(conn, "products")

        cost_column = first_column(
            columns,
            ["buying_price", "cost_price", "purchase_price", "buying_cost"],
        )

        stock_column = first_column(
            columns,
            ["stock", "quantity", "opening_stock", "current_stock"],
        )

        if cost_column and stock_column:
            row = conn.execute(
                f"SELECT COALESCE(SUM({cost_column} * {stock_column}), 0) "
                f"FROM products"
            ).fetchone()

            inventory_capital = float(row[0] or 0)

    sales_count = get_count(conn, "sales")

    return {
        "revenue": revenue,
        "gross_profit": gross_profit,
        "margin": margin,
        "liquid_funds": liquid_funds,
        "customer_credit": customer_credit,
        "supplier_liability": supplier_liability,
        "inventory_capital": inventory_capital,
        "sales_count": sales_count,
    }


def score_margin(margin):
    return min(100.0, max(0.0, (margin / TARGET_MARGIN) * 100))


def score_liquidity(liquid, supplier):
    if supplier <= 0:
        return 100.0
    return min(100.0, max(0.0, liquid / supplier * 100))


def score_credit(credit, revenue):
    if revenue <= 0:
        return 0.0

    exposure = credit / revenue * 100

    if exposure <= TARGET_CREDIT_EXPOSURE:
        return 100.0

    excess = exposure - TARGET_CREDIT_EXPOSURE

    return max(
        0.0,
        100.0 - (excess / TARGET_CREDIT_EXPOSURE * 100),
    )


def score_inventory(inventory, revenue):
    if revenue <= 0:
        return 0.0

    ratio = inventory / revenue * 100

    if ratio <= 50:
        return 100.0

    if ratio >= 150:
        return 40.0

    return 100.0 - ((ratio - 50) / 100 * 60)


def score_sales(sales_count):
    return min(100.0, sales_count / REFERENCE_SALES * 100)


def health_status(score):
    if score >= 85:
        return "🟢 STRONG"
    if score >= 70:
        return "🟡 WATCH"
    if score >= 50:
        return "🟠 AT RISK"
    return "🔴 CRITICAL"


def main():
    print("=" * 60)
    print("POS LEDGER NG V75")
    print("MANAGEMENT PERFORMANCE SCORECARD INTELLIGENCE")
    print("=" * 60)

    if not DB_PATH.exists():
        print("\nDatabase not found:", DB_PATH)
        return

    conn = connect()

    try:
        data = get_business_position(conn)

        revenue = data["revenue"]
        gross_profit = data["gross_profit"]
        margin = data["margin"]
        liquid = data["liquid_funds"]
        credit = data["customer_credit"]
        supplier = data["supplier_liability"]
        inventory = data["inventory_capital"]
        sales_count = data["sales_count"]

        supplier_gap = max(0.0, supplier - liquid)

        credit_exposure = (
            credit / revenue * 100 if revenue else 0.0
        )

        inventory_ratio = (
            inventory / revenue * 100 if revenue else 0.0
        )

        margin_score = score_margin(margin)
        liquidity_score = score_liquidity(liquid, supplier)
        credit_score = score_credit(credit, revenue)
        inventory_score = score_inventory(inventory, revenue)
        sales_score = score_sales(sales_count)

        overall_score = (
            margin_score
            + liquidity_score
            + credit_score
            + inventory_score
            + sales_score
        ) / 5

        print("\n" + "=" * 60)
        print("CURRENT BUSINESS POSITION")
        print("=" * 60)

        print(f"Revenue              : {money(revenue)}")
        print(f"Gross Profit         : {money(gross_profit)}")
        print(f"Gross Margin         : {percent(margin)}")
        print(f"Liquid Funds         : {money(liquid)}")
        print(f"Customer Credit      : {money(credit)}")
        print(f"Supplier Liability   : {money(supplier)}")
        print(f"Supplier Gap         : {money(supplier_gap)}")
        print(f"Inventory Capital    : {money(inventory)}")
        print(f"Recorded Sales       : {sales_count}")

        print("\n" + "=" * 60)
        print("MANAGEMENT PERFORMANCE SCORECARD")
        print("=" * 60)

        print("----------------------------------------")
        print("1. PROFITABILITY")
        print(f"Gross Margin         : {percent(margin)}")
        print(f"Target Margin        : {percent(TARGET_MARGIN)}")
        print(f"Margin Gap           : {percent(max(0, TARGET_MARGIN - margin))}")
        print(f"Score                : {margin_score:.2f}/100")
        print(f"Status               : {health_status(margin_score)}")

        print("----------------------------------------")
        print("2. LIQUIDITY")
        print(f"Liquid Funds         : {money(liquid)}")
        print(f"Supplier Liability   : {money(supplier)}")
        print(f"Coverage             : {percent(liquidity_score)}")
        print(f"Payment Gap          : {money(supplier_gap)}")
        print(f"Score                : {liquidity_score:.2f}/100")
        print(f"Status               : {health_status(liquidity_score)}")

        print("----------------------------------------")
        print("3. CUSTOMER CREDIT")
        print(f"Outstanding Credit   : {money(credit)}")
        print(f"Credit Exposure      : {percent(credit_exposure)}")
        print(f"Target Exposure      : {percent(TARGET_CREDIT_EXPOSURE)}")
        print(f"Score                : {credit_score:.2f}/100")
        print(f"Status               : {health_status(credit_score)}")

        print("----------------------------------------")
        print("4. INVENTORY EFFICIENCY")
        print(f"Inventory Capital    : {money(inventory)}")
        print(f"Inventory/Revenue    : {percent(inventory_ratio)}")
        print(f"Score                : {inventory_score:.2f}/100")
        print(f"Status               : {health_status(inventory_score)}")

        print("----------------------------------------")
        print("5. SALES DATA")
        print(f"Recorded Sales       : {sales_count}")
        print(f"Reference Level      : {REFERENCE_SALES}")
        print(f"Score                : {sales_score:.2f}/100")
        print(f"Status               : {health_status(sales_score)}")

        print("\n" + "=" * 60)
        print("OVERALL MANAGEMENT SCORE")
        print("=" * 60)

        print(f"Overall Score        : {overall_score:.2f}/100")
        print(f"Business Status      : {health_status(overall_score)}")

        actions = []

        if supplier_gap > 0:
            actions.append(
                (
                    1,
                    "PROTECT LIQUIDITY",
                    supplier_gap,
                    f"Supplier payment gap is {money(supplier_gap)}."
                )
            )

        if margin < TARGET_MARGIN:
            actions.append(
                (
                    2,
                    "IMPROVE GROSS MARGIN",
                    TARGET_MARGIN - margin,
                    f"Margin is {percent(TARGET_MARGIN - margin)} below target."
                )
            )

        if credit > 0:
            actions.append(
                (
                    3,
                    "COLLECT CUSTOMER CREDIT",
                    credit,
                    f"{money(credit)} may be recovered."
                )
            )

        if inventory_ratio > 80:
            actions.append(
                (
                    4,
                    "CONTROL INVENTORY CAPITAL",
                    inventory,
                    f"{money(inventory)} is tied up in inventory."
                )
            )

        if sales_count < REFERENCE_SALES:
            actions.append(
                (
                    5,
                    "STRENGTHEN SALES DATA",
                    REFERENCE_SALES - sales_count,
                    f"{REFERENCE_SALES - sales_count} more recorded sales are needed."
                )
            )

        print("\n" + "=" * 60)
        print("TOP MANAGEMENT ACTIONS")
        print("=" * 60)

        actions.sort(key=lambda x: x[2], reverse=True)

        for rank, action, value, reason in actions[:5]:
            print(f"{rank}. {action}")
            print(f"   {reason}")

        print("\n" + "=" * 60)
        print("EXECUTIVE INTERPRETATION")
        print("=" * 60)

        if supplier_gap > 0:
            print(
                f"Liquidity protection remains important because "
                f"supplier obligations exceed liquid funds by "
                f"{money(supplier_gap)}."
            )

        if margin < TARGET_MARGIN:
            print(
                f"Profitability requires attention because gross margin "
                f"is {percent(margin)}, below the {percent(TARGET_MARGIN)} target."
            )

        if credit > 0:
            print(
                f"Customer credit of {money(credit)} represents "
                f"potential recoverable liquidity."
            )

        if inventory_ratio > 80:
            print(
                f"Inventory represents {percent(inventory_ratio)} of revenue, "
                f"so stock turnover should be monitored carefully."
            )

        print("\n" + "=" * 60)
        print("V75 SAFETY STATUS")
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

    finally:
        conn.close()


if __name__ == "__main__":
    main()
