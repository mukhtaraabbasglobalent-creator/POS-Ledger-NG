"""
POS LEDGER NG V77
FINANCIAL TRUTH & DATA RECONCILIATION INTELLIGENCE

READ-ONLY.
No database records are modified.
"""

import sqlite3
from pathlib import Path


DB = Path("data/posledger.db")


def money(x):
    return f"₦{float(x or 0):,.2f}"


def pct(x):
    return f"{float(x or 0):.2f}%"


def table_exists(con, table):
    return con.execute(
        "SELECT 1 FROM sqlite_master "
        "WHERE type='table' AND name=?",
        (table,),
    ).fetchone() is not None


def get_columns(con, table):
    if not table_exists(con, table):
        return []

    return [
        row[1]
        for row in con.execute(
            f"PRAGMA table_info({table})"
        ).fetchall()
    ]


def first_column(con, table, candidates):
    cols = get_columns(con, table)

    for candidate in candidates:
        if candidate in cols:
            return candidate

    return None


def sum_field(con, table, candidates):
    column = first_column(con, table, candidates)

    if not column:
        return None

    row = con.execute(
        f"SELECT COALESCE(SUM({column}),0) FROM {table}"
    ).fetchone()

    return float(row[0] or 0)


def count_rows(con, table):
    if not table_exists(con, table):
        return 0

    return con.execute(
        f"SELECT COUNT(*) FROM {table}"
    ).fetchone()[0]


def sales_revenue(con):
    return sum_field(
        con,
        "sales",
        [
            "total_amount",
            "grand_total",
            "sale_amount",
            "total",
            "amount",
        ],
    )


def sales_cost(con):
    return sum_field(
        con,
        "sales",
        [
            "total_cost",
            "cost_amount",
            "cost",
            "buying_cost",
            "cost_price",
            "cogs",
        ],
    )


def liquid_funds(con):
    for table in [
        "balance",
        "balances",
        "cash_balance",
        "financial_balance",
    ]:
        value = sum_field(
            con,
            table,
            [
                "balance",
                "liquid_funds",
                "cash_balance",
                "current_balance",
                "available_balance",
            ],
        )

        if value is not None:
            return value

    return None


def customer_credit(con):
    for table in [
        "customer_credit",
        "customer_credits",
        "credits",
    ]:
        value = sum_field(
            con,
            table,
            [
                "outstanding",
                "outstanding_credit",
                "balance",
                "credit_amount",
                "amount",
            ],
        )

        if value is not None:
            return value

    return 0.0


def supplier_liability(con):
    for table in [
        "supplier_credit",
        "supplier_liabilities",
        "suppliers",
    ]:
        value = sum_field(
            con,
            table,
            [
                "outstanding",
                "outstanding_balance",
                "balance",
                "amount_due",
                "liability",
            ],
        )

        if value is not None:
            return value

    return 0.0


def inventory_value(con):
    if not table_exists(con, "products"):
        return 0.0

    cost = first_column(
        con,
        "products",
        [
            "buying_price",
            "cost_price",
            "purchase_price",
            "buying_cost",
        ],
    )

    stock = first_column(
        con,
        "products",
        [
            "stock",
            "current_stock",
            "quantity",
            "opening_stock",
        ],
    )

    if not cost or not stock:
        return 0.0

    row = con.execute(
        f"""
        SELECT COALESCE(
            SUM({cost} * {stock}),
            0
        )
        FROM products
        """
    ).fetchone()

    return float(row[0] or 0)


def main():

    print("=" * 60)
    print("POS LEDGER NG V77")
    print("FINANCIAL TRUTH & DATA RECONCILIATION INTELLIGENCE")
    print("=" * 60)

    if not DB.exists():
        print()
        print("DATABASE ERROR")
        print(f"Database not found: {DB}")
        return

    con = sqlite3.connect(DB)

    try:
        revenue = sales_revenue(con)
        cost = sales_cost(con)

        sales_count = count_rows(con, "sales")

        cash = liquid_funds(con)
        credit = customer_credit(con)
        supplier = supplier_liability(con)
        inventory = inventory_value(con)

        print()
        print("=" * 60)
        print("SOURCE FINANCIAL DATA")
        print("=" * 60)

        print(
            f"Revenue              : "
            f"{money(revenue or 0)}"
        )

        if cost is None:
            print(
                "Sales Cost           : "
                "UNAVAILABLE"
            )
        else:
            print(
                f"Sales Cost           : "
                f"{money(cost)}"
            )

        print(
            f"Liquid Funds         : "
            f"{money(cash or 0)}"
        )

        print(
            f"Customer Credit      : "
            f"{money(credit)}"
        )

        print(
            f"Supplier Liability   : "
            f"{money(supplier)}"
        )

        print(
            f"Inventory Capital    : "
            f"{money(inventory)}"
        )

        print(
            f"Recorded Sales       : "
            f"{sales_count}"
        )

        print()
        print("=" * 60)
        print("FINANCIAL RECONCILIATION")
        print("=" * 60)

        flags = []

        if revenue is None:
            flags.append(
                "REVENUE DATA UNAVAILABLE"
            )

        if cost is None:
            flags.append(
                "COGS / SALES COST DATA UNAVAILABLE"
            )

        if revenue is not None and cost is not None:

            gross_profit = revenue - cost

            if revenue > 0:
                margin = (
                    gross_profit / revenue
                ) * 100
            else:
                margin = 0.0

            print(
                f"Gross Profit         : "
                f"{money(gross_profit)}"
            )

            print(
                f"Gross Margin         : "
                f"{pct(margin)}"
            )

            if cost > revenue:
                flags.append(
                    "SALES COST EXCEEDS REVENUE"
                )

        else:
            print(
                "Gross Profit         : "
                "NOT RELIABLY CALCULABLE"
            )

            print(
                "Gross Margin         : "
                "NOT RELIABLY CALCULABLE"
            )

            flags.append(
                "PROFITABILITY DATA INCOMPLETE"
            )

        gap = max(
            0.0,
            supplier - (cash or 0),
        )

        print(
            f"Supplier Liquidity Gap: "
            f"{money(gap)}"
        )

        if gap > 0:
            flags.append(
                "SUPPLIER LIABILITY EXCEEDS LIQUID FUNDS"
            )

        if revenue and inventory > revenue:
            flags.append(
                "INVENTORY CAPITAL EXCEEDS RECORDED REVENUE"
            )

        if sales_count < 20:
            flags.append(
                "LIMITED SALES HISTORY"
            )

        print()
        print("=" * 60)
        print("FINANCIAL TRUTH STATUS")
        print("=" * 60)

        if flags:
            print(
                "Status               : "
                "🟡 REVIEW REQUIRED"
            )

            for flag in flags:
                print(f"- {flag}")
        else:
            print(
                "Status               : "
                "🟢 RECONCILED"
            )

        print()
        print("=" * 60)
        print("MANAGEMENT INTERPRETATION")
        print("=" * 60)

        if cost is None:
            print(
                "POS Ledger NG cannot safely calculate "
                "true gross profit or gross margin from "
                "the currently detected sales schema."
            )

            print(
                "The system must not treat revenue as profit."
            )

            print(
                "COGS / product-cost linkage should be "
                "verified before profitability decisions "
                "are considered authoritative."
            )
        else:
            print(
                "Revenue and recorded sales cost are "
                "available for profitability analysis."
            )

        if credit > 0:
            print(
                f"Customer credit of {money(credit)} "
                "represents potential recoverable liquidity."
            )

        if gap > 0:
            print(
                f"Supplier payment pressure remains at "
                f"{money(gap)}."
            )

        if inventory > 0:
            print(
                f"Inventory capital currently stands at "
                f"{money(inventory)}."
            )

        print()
        print("=" * 60)
        print("V77 SAFETY STATUS")
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
        con.close()


if __name__ == "__main__":
    main()
