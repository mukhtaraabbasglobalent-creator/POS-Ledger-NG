"""
POS LEDGER NG V92
FINANCIAL RECONCILIATION & TRANSACTION INTEGRITY INTELLIGENCE

READ-ONLY ANALYTICS
Does not modify the database.
"""

import sqlite3
from pathlib import Path
from datetime import datetime


DB_PATH = Path("data/posledger.db")


def money(value):
    return f"₦{float(value or 0):,.2f}"


def pct(value):
    return f"{float(value or 0):.2f}%"


def safe_float(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def table_exists(conn, table_name):
    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table' AND name=?
        """,
        (table_name,),
    ).fetchone()
    return row is not None


def columns(conn, table_name):
    if not table_exists(conn, table_name):
        return []
    return [
        row[1]
        for row in conn.execute(
            f"PRAGMA table_info({table_name})"
        ).fetchall()
    ]


def first_existing(cols, candidates):
    for candidate in candidates:
        if candidate in cols:
            return candidate
    return None


def fetch_one(conn, sql, params=()):
    try:
        return conn.execute(sql, params).fetchone()
    except sqlite3.Error:
        return None


def fetch_all(conn, sql, params=()):
    try:
        return conn.execute(sql, params).fetchall()
    except sqlite3.Error:
        return []


def main():
    print("=" * 60)
    print("POS LEDGER NG V92")
    print("FINANCIAL RECONCILIATION & TRANSACTION INTEGRITY INTELLIGENCE")
    print("=" * 60)

    if not DB_PATH.exists():
        print()
        print("DATABASE STATUS")
        print("=" * 60)
        print(f"Database not found : {DB_PATH}")
        print("Run this module from the POS-Ledger-NG project root.")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        # ---------------------------------------------------------
        # DATABASE STRUCTURE
        # ---------------------------------------------------------
        print()
        print("=" * 60)
        print("DATABASE STRUCTURE")
        print("=" * 60)

        required_tables = [
            "sales",
            "products",
            "inventory_movements",
            "purchases",
            "expenses",
            "customer_credit",
            "suppliers",
        ]

        available = {}

        for table in required_tables:
            exists = table_exists(conn, table)
            available[table] = exists
            print(
                f"{table:<22}: "
                f"{'AVAILABLE' if exists else 'NOT DETECTED'}"
            )

        # ---------------------------------------------------------
        # SALES RECONCILIATION
        # ---------------------------------------------------------
        sales_cols = columns(conn, "sales")

        sale_id_col = first_existing(sales_cols, ["id"])
        sale_product_col = first_existing(
            sales_cols, ["product_id"]
        )
        sale_qty_col = first_existing(
            sales_cols, ["quantity"]
        )
        sale_revenue_col = first_existing(
            sales_cols, ["total_amount", "amount", "total"]
        )
        sale_cogs_col = first_existing(
            sales_cols, ["cogs"]
        )
        sale_profit_col = first_existing(
            sales_cols, ["gross_profit", "total_profit", "profit"]
        )
        sale_status_col = first_existing(
            sales_cols, ["status"]
        )

        sales_where = ""

        if sale_status_col:
            sales_where = (
                f"WHERE UPPER(COALESCE({sale_status_col}, '')) "
                f"IN ('COMPLETED', 'COMPLETE', 'SUCCESS', 'PAID')"
            )

        sales_count = 0
        revenue = 0.0
        cogs = 0.0
        gross_profit = 0.0
        units_sold = 0.0

        if available["sales"] and sale_id_col:
            row = fetch_one(
                conn,
                f"""
                SELECT
                    COUNT(*) AS sales_count,
                    COALESCE(SUM({sale_qty_col}), 0) AS units,
                    COALESCE(SUM({sale_revenue_col}), 0) AS revenue,
                    COALESCE(SUM({sale_cogs_col}), 0) AS cogs,
                    COALESCE(SUM({sale_profit_col}), 0) AS profit
                FROM sales
                {sales_where}
                """,
            )

            if row:
                sales_count = int(row["sales_count"] or 0)
                units_sold = safe_float(row["units"])
                revenue = safe_float(row["revenue"])
                cogs = safe_float(row["cogs"])
                gross_profit = safe_float(row["profit"])

        print()
        print("=" * 60)
        print("SALES FINANCIAL RECONCILIATION")
        print("=" * 60)
        print(f"Completed sales       : {sales_count}")
        print(f"Units sold            : {units_sold:,.2f}")
        print(f"Revenue               : {money(revenue)}")
        print(f"Recorded COGS         : {money(cogs)}")
        print(f"Recorded gross profit : {money(gross_profit)}")

        # ---------------------------------------------------------
        # SALES WITHOUT PRODUCT
        # ---------------------------------------------------------
        sales_missing_product = 0

        if (
            available["sales"]
            and available["products"]
            and sale_product_col
        ):
            row = fetch_one(
                conn,
                f"""
                SELECT COUNT(*)
                FROM sales s
                LEFT JOIN products p
                    ON p.id = s.{sale_product_col}
                {sales_where}
                {"AND" if sales_where else "WHERE"}
                    p.id IS NULL
                """,
            )

            if row:
                sales_missing_product = int(row[0] or 0)

        # ---------------------------------------------------------
        # SALES WITHOUT COGS
        # ---------------------------------------------------------
        sales_missing_cogs = 0

        if (
            available["sales"]
            and sale_cogs_col
        ):
            row = fetch_one(
                conn,
                f"""
                SELECT COUNT(*)
                FROM sales
                {sales_where}
                {"AND" if sales_where else "WHERE"}
                    COALESCE({sale_cogs_col}, 0) <= 0
                """,
            )

            if row:
                sales_missing_cogs = int(row[0] or 0)

        # ---------------------------------------------------------
        # PURCHASE RECONCILIATION
        # ---------------------------------------------------------
        purchase_cols = columns(conn, "purchases")

        purchase_qty_col = first_existing(
            purchase_cols, ["quantity"]
        )
        purchase_cost_col = first_existing(
            purchase_cols, ["total_cost"]
        )
        purchase_product_col = first_existing(
            purchase_cols, ["product_id"]
        )

        purchase_records = 0
        purchase_units = 0.0
        purchase_value = 0.0

        if available["purchases"]:
            row = fetch_one(
                conn,
                f"""
                SELECT
                    COUNT(*) AS records,
                    COALESCE(SUM({purchase_qty_col}), 0) AS units,
                    COALESCE(SUM({purchase_cost_col}), 0) AS value
                FROM purchases
                """,
            )

            if row:
                purchase_records = int(row["records"] or 0)
                purchase_units = safe_float(row["units"])
                purchase_value = safe_float(row["value"])

        print()
        print("=" * 60)
        print("PURCHASE RECONCILIATION")
        print("=" * 60)
        print(f"Purchase records      : {purchase_records}")
        print(f"Purchased units       : {purchase_units:,.2f}")
        print(f"Purchase value        : {money(purchase_value)}")

        # ---------------------------------------------------------
        # INVENTORY MOVEMENT RECONCILIATION
        # ---------------------------------------------------------
        inventory_cols = columns(conn, "inventory_movements")

        movement_type_col = first_existing(
            inventory_cols, ["movement_type"]
        )
        movement_qty_col = first_existing(
            inventory_cols, ["quantity"]
        )

        inventory_sale_units = 0.0
        inventory_purchase_units = 0.0
        inventory_sale_movements = 0
        inventory_purchase_movements = 0

        if available["inventory_movements"]:
            if movement_type_col:
                row = fetch_one(
                    conn,
                    f"""
                    SELECT
                        COUNT(*) AS movements,
                        COALESCE(SUM({movement_qty_col}), 0) AS units
                    FROM inventory_movements
                    WHERE UPPER({movement_type_col}) = 'SALE'
                    """,
                )

                if row:
                    inventory_sale_movements = int(
                        row["movements"] or 0
                    )
                    inventory_sale_units = safe_float(
                        row["units"]
                    )

                row = fetch_one(
                    conn,
                    f"""
                    SELECT
                        COUNT(*) AS movements,
                        COALESCE(SUM({movement_qty_col}), 0) AS units
                    FROM inventory_movements
                    WHERE UPPER({movement_type_col})
                    IN ('PURCHASE', 'STOCK_IN', 'IN')
                    """,
                )

                if row:
                    inventory_purchase_movements = int(
                        row["movements"] or 0
                    )
                    inventory_purchase_units = safe_float(
                        row["units"]
                    )

        print()
        print("=" * 60)
        print("INVENTORY MOVEMENT RECONCILIATION")
        print("=" * 60)
        print(
            f"SALE movements       : {inventory_sale_movements}"
        )
        print(
            f"Sale movement units  : {inventory_sale_units:,.2f}"
        )
        print(
            f"Purchase movements   : {inventory_purchase_movements}"
        )
        print(
            f"Purchase movement units: "
            f"{inventory_purchase_units:,.2f}"
        )

        # ---------------------------------------------------------
        # SALES VS INVENTORY
        # ---------------------------------------------------------
        sales_inventory_difference = (
            units_sold - inventory_sale_units
        )

        print()
        print("=" * 60)
        print("SALES ↔ INVENTORY RECONCILIATION")
        print("=" * 60)
        print(f"Sales units           : {units_sold:,.2f}")
        print(
            f"Inventory SALE units  : "
            f"{inventory_sale_units:,.2f}"
        )
        print(
            f"Difference            : "
            f"{sales_inventory_difference:,.2f}"
        )

        if abs(sales_inventory_difference) < 0.0001:
            sales_inventory_status = "🟢 RECONCILED"
        else:
            sales_inventory_status = "🔴 MISMATCH"

        print(f"Status                : {sales_inventory_status}")

        # ---------------------------------------------------------
        # PURCHASES VS INVENTORY
        # ---------------------------------------------------------
        purchase_inventory_difference = (
            purchase_units - inventory_purchase_units
        )

        print()
        print("=" * 60)
        print("PURCHASES ↔ INVENTORY RECONCILIATION")
        print("=" * 60)
        print(f"Purchase units        : {purchase_units:,.2f}")
        print(
            f"Inventory IN units    : "
            f"{inventory_purchase_units:,.2f}"
        )
        print(
            f"Difference            : "
            f"{purchase_inventory_difference:,.2f}"
        )

        if not available["purchases"]:
            purchase_inventory_status = "🟡 PURCHASE TABLE UNAVAILABLE"
        elif not available["inventory_movements"]:
            purchase_inventory_status = (
                "🟡 INVENTORY MOVEMENTS UNAVAILABLE"
            )
        elif abs(purchase_inventory_difference) < 0.0001:
            purchase_inventory_status = "🟢 RECONCILED"
        else:
            purchase_inventory_status = "🟠 REVIEW"

        print(f"Status                : {purchase_inventory_status}")

        # ---------------------------------------------------------
        # PRODUCT STOCK RECONCILIATION
        # ---------------------------------------------------------
        current_stock = 0.0
        inventory_capital = 0.0

        product_cols = columns(conn, "products")

        stock_col = first_existing(
            product_cols, ["current_stock"]
        )
        product_buying_col = first_existing(
            product_cols, ["buying_price"]
        )

        if available["products"] and stock_col:
            row = fetch_one(
                conn,
                f"""
                SELECT
                    COALESCE(SUM({stock_col}), 0)
                FROM products
                """,
            )

            if row:
                current_stock = safe_float(row[0])

            if product_buying_col:
                row = fetch_one(
                    conn,
                    f"""
                    SELECT
                        COALESCE(
                            SUM(
                                COALESCE({stock_col}, 0) *
                                COALESCE({product_buying_col}, 0)
                            ),
                            0
                        )
                    FROM products
                    """,
                )

                if row:
                    inventory_capital = safe_float(row[0])

        print()
        print("=" * 60)
        print("CURRENT INVENTORY POSITION")
        print("=" * 60)
        print(f"Current stock units    : {current_stock:,.2f}")
        print(
            f"Inventory capital     : "
            f"{money(inventory_capital)}"
        )

        # ---------------------------------------------------------
        # EXPENSE RECONCILIATION
        # ---------------------------------------------------------
        expense_records = 0
        expenses = 0.0

        expense_cols = columns(conn, "expenses")

        expense_amount_col = first_existing(
            expense_cols, ["amount"]
        )

        if available["expenses"] and expense_amount_col:
            row = fetch_one(
                conn,
                f"""
                SELECT
                    COUNT(*) AS records,
                    COALESCE(SUM({expense_amount_col}), 0) AS total
                FROM expenses
                """,
            )

            if row:
                expense_records = int(row["records"] or 0)
                expenses = safe_float(row["total"])

        print()
        print("=" * 60)
        print("EXPENSE RECONCILIATION")
        print("=" * 60)
        print(f"Expense records       : {expense_records}")
        print(f"Operating expenses    : {money(expenses)}")

        # ---------------------------------------------------------
        # NET PROFIT RECONCILIATION
        # ---------------------------------------------------------
        calculated_gross_profit = revenue - cogs
        net_operating_profit = (
            calculated_gross_profit - expenses
        )

        calculated_margin = (
            (calculated_gross_profit / revenue) * 100
            if revenue > 0
            else 0
        )

        net_margin = (
            (net_operating_profit / revenue) * 100
            if revenue > 0
            else 0
        )

        print()
        print("=" * 60)
        print("PROFITABILITY RECONCILIATION")
        print("=" * 60)
        print(f"Revenue               : {money(revenue)}")
        print(f"COGS                  : {money(cogs)}")
        print(
            f"Calculated gross profit: "
            f"{money(calculated_gross_profit)}"
        )
        print(f"Expenses              : {money(expenses)}")
        print(
            f"Net operating profit  : "
            f"{money(net_operating_profit)}"
        )
        print(f"Gross margin          : {pct(calculated_margin)}")
        print(f"Net margin            : {pct(net_margin)}")

        # ---------------------------------------------------------
        # INTEGRITY FINDINGS
        # ---------------------------------------------------------
        findings = []

        if sales_missing_product > 0:
            findings.append(
                f"[HIGH] {sales_missing_product} completed "
                f"sale(s) have no valid product linkage."
            )

        if sales_missing_cogs > 0:
            findings.append(
                f"[HIGH] {sales_missing_cogs} completed "
                f"sale(s) have missing or zero COGS."
            )

        if abs(sales_inventory_difference) >= 0.0001:
            findings.append(
                "[HIGH] Sales quantities do not reconcile "
                "with SALE inventory movements."
            )

        if (
            available["purchases"]
            and available["inventory_movements"]
            and abs(purchase_inventory_difference) >= 0.0001
        ):
            findings.append(
                "[MEDIUM] Purchase quantities do not fully "
                "reconcile with inventory IN movements."
            )

        if not available["suppliers"]:
            findings.append(
                "[LOW] Supplier table was not detected."
            )

        if expense_records == 0:
            findings.append(
                "[LOW] No operating expenses are currently "
                "recorded."
            )

        if not findings:
            findings.append(
                "[GOOD] No major reconciliation exception "
                "was detected."
            )

        print()
        print("=" * 60)
        print("DATA INTEGRITY FINDINGS")
        print("=" * 60)

        for finding in findings:
            print(finding)

        # ---------------------------------------------------------
        # INTEGRITY SCORE
        # ---------------------------------------------------------
        score = 100.0

        if sales_missing_product > 0:
            score -= 25

        if sales_missing_cogs > 0:
            score -= 20

        if abs(sales_inventory_difference) >= 0.0001:
            score -= 25

        if (
            available["purchases"]
            and available["inventory_movements"]
            and abs(purchase_inventory_difference) >= 0.0001
        ):
            score -= 15

        if not available["suppliers"]:
            score -= 5

        score = max(0.0, min(100.0, score))

        if score >= 90:
            integrity_status = "🟢 STRONG"
        elif score >= 70:
            integrity_status = "🟡 REVIEW"
        elif score >= 50:
            integrity_status = "🟠 AT RISK"
        else:
            integrity_status = "🔴 CRITICAL"

        print()
        print("=" * 60)
        print("V92 FINANCIAL INTEGRITY SCORE")
        print("=" * 60)
        print(f"Integrity Score       : {score:.2f}/100")
        print(f"Integrity Status      : {integrity_status}")

        # ---------------------------------------------------------
        # EXECUTIVE DECISION
        # ---------------------------------------------------------
        if score >= 90:
            decision = "🟢 FINANCIAL DATA RECONCILED"
        elif score >= 70:
            decision = "🟡 FINANCIAL DATA REQUIRES REVIEW"
        elif score >= 50:
            decision = "🟠 RECONCILIATION RISK DETECTED"
        else:
            decision = "🔴 FINANCIAL INTEGRITY CRITICAL"

        print()
        print("=" * 60)
        print("V92 EXECUTIVE DECISION")
        print("=" * 60)
        print(decision)

        print()
        print("=" * 60)
        print("V92 MANAGEMENT INTERPRETATION")
        print("=" * 60)
        print(
            "V92 independently reconciles sales, products, "
            "inventory movements, purchases and expenses."
        )
        print(
            "The module is designed to detect inconsistencies "
            "before downstream business intelligence relies "
            "on the affected data."
        )
        print(
            "V92 is analytical only and does not automatically "
            "modify financial records."
        )

        # ---------------------------------------------------------
        # DATA SOURCES
        # ---------------------------------------------------------
        print()
        print("=" * 60)
        print("V92 DATA INTEGRITY STATUS")
        print("=" * 60)
        print(
            f"Sales source           : "
            f"{'AVAILABLE' if available['sales'] else 'NOT DETECTED'}"
        )
        print(
            f"Products source        : "
            f"{'AVAILABLE' if available['products'] else 'NOT DETECTED'}"
        )
        print(
            f"Inventory source       : "
            f"{'AVAILABLE' if available['inventory_movements'] else 'NOT DETECTED'}"
        )
        print(
            f"Purchases source       : "
            f"{'AVAILABLE' if available['purchases'] else 'NOT DETECTED'}"
        )
        print(
            f"Expenses source        : "
            f"{'AVAILABLE' if available['expenses'] else 'NOT DETECTED'}"
        )
        print(
            f"Supplier source        : "
            f"{'AVAILABLE' if available['suppliers'] else 'NOT DETECTED'}"
        )

        # ---------------------------------------------------------
        # SAFETY
        # ---------------------------------------------------------
        print()
        print("=" * 60)
        print("V92 SAFETY STATUS")
        print("=" * 60)
        print("Mode                  : READ-ONLY")
        print("Database modified     : NO")
        print("Sales modified        : NO")
        print("Products modified     : NO")
        print("Inventory modified    : NO")
        print("Purchases modified    : NO")
        print("Balance modified      : NO")
        print("Credit modified       : NO")
        print("Suppliers modified    : NO")
        print("Expenses modified     : NO")
        print("=" * 60)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
