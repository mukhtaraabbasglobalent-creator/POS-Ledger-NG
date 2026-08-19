import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path("data/posledger.db")


def money(value):
    return f"₦{float(value or 0):,.2f}"


def get_columns(conn, table):
    try:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        return [row[1] for row in rows]
    except Exception:
        return []


def table_exists(conn, table):
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,)
    ).fetchone()
    return row is not None


def find_column(columns, candidates):
    lowered = {c.lower(): c for c in columns}

    for candidate in candidates:
        if candidate.lower() in lowered:
            return lowered[candidate.lower()]

    return None


def main():
    print("=" * 60)
    print("POS LEDGER NG V80")
    print("HISTORICAL COST & PROFITABILITY INTEGRITY INTELLIGENCE")
    print("=" * 60)

    if not DB_PATH.exists():
        print()
        print("DATABASE STATUS : NOT FOUND")
        print(f"Expected path  : {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        print()
        print("=" * 60)
        print("DATABASE STRUCTURE")
        print("=" * 60)

        tables = [
            "sales",
            "products",
            "inventory_movements",
            "stock_purchases",
            "purchases",
        ]

        for table in tables:
            if table_exists(conn, table):
                print(f"{table:<24}: AVAILABLE")
            else:
                print(f"{table:<24}: NOT DETECTED")

        sales_cols = get_columns(conn, "sales")
        product_cols = get_columns(conn, "products")

        inventory_table = None
        for candidate in ["inventory_movements", "stock_purchases", "purchases"]:
            if table_exists(conn, candidate):
                inventory_table = candidate
                break

        inventory_cols = get_columns(conn, inventory_table) if inventory_table else []

        print()
        print("=" * 60)
        print("DETECTED FIELDS")
        print("=" * 60)

        sale_product_col = find_column(
            sales_cols,
            ["product_id", "productid"]
        )

        sale_quantity_col = find_column(
            sales_cols,
            ["quantity", "qty"]
        )

        sale_revenue_col = find_column(
            sales_cols,
            ["total_amount", "total", "amount"]
        )

        sale_date_col = find_column(
            sales_cols,
            ["sale_date", "created_at", "transaction_date", "date"]
        )

        product_id_col = find_column(
            product_cols,
            ["id", "product_id"]
        )

        product_cost_col = find_column(
            product_cols,
            ["buying_price", "cost_price", "purchase_price"]
        )

        product_name_col = find_column(
            product_cols,
            ["product_name", "name"]
        )

        inventory_product_col = find_column(
            inventory_cols,
            ["product_id", "productid"]
        )

        inventory_quantity_col = find_column(
            inventory_cols,
            ["quantity", "qty"]
        )

        inventory_cost_col = find_column(
            inventory_cols,
            [
                "buying_price",
                "cost_price",
                "unit_cost",
                "purchase_price",
                "cost"
            ]
        )

        inventory_date_col = find_column(
            inventory_cols,
            [
                "movement_date",
                "created_at",
                "purchase_date",
                "transaction_date",
                "date"
            ]
        )

        print(f"Sales product field      : {sale_product_col or 'NOT DETECTED'}")
        print(f"Sales quantity field     : {sale_quantity_col or 'NOT DETECTED'}")
        print(f"Sales revenue field      : {sale_revenue_col or 'NOT DETECTED'}")
        print(f"Sales date field         : {sale_date_col or 'NOT DETECTED'}")
        print(f"Product cost field       : {product_cost_col or 'NOT DETECTED'}")
        print(f"Inventory table          : {inventory_table or 'NOT DETECTED'}")
        print(f"Inventory cost field     : {inventory_cost_col or 'NOT DETECTED'}")
        print(f"Inventory date field     : {inventory_date_col or 'NOT DETECTED'}")

        print()
        print("=" * 60)
        print("HISTORICAL COST TEST")
        print("=" * 60)

        if not sale_product_col or not sale_quantity_col or not sale_revenue_col:
            print("STATUS : ❌ SALES STRUCTURE INSUFFICIENT")
            return

        if not product_id_col or not product_cost_col:
            print("STATUS : ❌ PRODUCT COST STRUCTURE INSUFFICIENT")
            return

        sales = conn.execute(
            f"""
            SELECT
                s.rowid AS sale_rowid,
                s.*,
                p.{product_name_col or product_id_col} AS product_name,
                p.{product_cost_col} AS current_cost
            FROM sales s
            LEFT JOIN products p
                ON s.{sale_product_col} = p.{product_id_col}
            ORDER BY s.rowid
            """
        ).fetchall()

        verified = 0
        estimated = 0
        unresolved = 0

        verified_cogs = 0.0
        estimated_cogs = 0.0
        revenue_total = 0.0

        for index, sale in enumerate(sales, start=1):
            product_name = sale["product_name"]
            quantity = float(sale[sale_quantity_col] or 0)
            revenue = float(sale[sale_revenue_col] or 0)
            current_cost = sale["current_cost"]

            revenue_total += revenue

            print("-" * 40)
            print(f"Sale #{index}")
            print(f"Product              : {product_name or 'UNKNOWN'}")
            print(f"Quantity              : {quantity:g}")
            print(f"Revenue               : {money(revenue)}")

            if current_cost is None:
                print("Current Cost         : UNAVAILABLE")
                print("Historical Cost      : ❌ UNRESOLVED")
                unresolved += 1
                continue

            current_cost = float(current_cost)

            print(f"Current Cost/Unit    : {money(current_cost)}")

            historical_cost = None

            # Try to establish historical purchase cost.
            if (
                inventory_table
                and inventory_product_col
                and inventory_quantity_col
                and inventory_cost_col
            ):
                try:
                    if sale_date_col and inventory_date_col:
                        sale_date = sale[sale_date_col]

                        if sale_date:
                            row = conn.execute(
                                f"""
                                SELECT {inventory_cost_col} AS cost
                                FROM {inventory_table}
                                WHERE {inventory_product_col} = ?
                                  AND {inventory_cost_col} IS NOT NULL
                                  AND {inventory_date_col} <= ?
                                ORDER BY {inventory_date_col} DESC
                                LIMIT 1
                                """,
                                (
                                    sale[sale_product_col],
                                    sale_date
                                )
                            ).fetchone()

                            if row and row["cost"] is not None:
                                historical_cost = float(row["cost"])

                    if historical_cost is None:
                        row = conn.execute(
                            f"""
                            SELECT {inventory_cost_col} AS cost
                            FROM {inventory_table}
                            WHERE {inventory_product_col} = ?
                              AND {inventory_cost_col} IS NOT NULL
                            ORDER BY rowid DESC
                            LIMIT 1
                            """,
                            (sale[sale_product_col],)
                        ).fetchone()

                        if row and row["cost"] is not None:
                            historical_cost = float(row["cost"])

                except Exception:
                    historical_cost = None

            if historical_cost is not None:
                cogs = quantity * historical_cost
                profit = revenue - cogs

                verified += 1
                verified_cogs += cogs

                print(f"Historical Cost/Unit : {money(historical_cost)}")
                print(f"Historical COGS      : {money(cogs)}")
                print(f"Historical Profit    : {money(profit)}")
                print("Status               : 🟢 COST HISTORY FOUND")
            else:
                cogs = quantity * current_cost
                profit = revenue - cogs

                estimated += 1
                estimated_cogs += cogs

                print("Historical Cost/Unit : NOT VERIFIED")
                print(f"Estimated COGS      : {money(cogs)}")
                print(f"Estimated Profit    : {money(profit)}")
                print("Status               : 🟡 CURRENT COST USED")

        print()
        print("=" * 60)
        print("V80 COST INTEGRITY SUMMARY")
        print("=" * 60)

        print(f"Recorded Sales          : {len(sales)}")
        print(f"Historical Cost Verified: {verified}")
        print(f"Estimated From Current  : {estimated}")
        print(f"Unresolved Sales        : {unresolved}")
        print(f"Revenue                 : {money(revenue_total)}")
        print(f"Verified COGS           : {money(verified_cogs)}")
        print(f"Estimated COGS          : {money(estimated_cogs)}")

        total_known_cogs = verified_cogs + estimated_cogs

        print(f"Known/Estimated COGS    : {money(total_known_cogs)}")

        if revenue_total > 0 and total_known_cogs >= 0:
            profit = revenue_total - total_known_cogs
            margin = (profit / revenue_total) * 100

            print(f"Derived Profit          : {money(profit)}")
            print(f"Derived Margin          : {margin:.2f}%")

        print()
        print("=" * 60)
        print("FINANCIAL TRUTH STATUS")
        print("=" * 60)

        if unresolved > 0:
            status = "🔴 INCOMPLETE"
            explanation = (
                "Some sales cannot be linked to a reliable historical cost."
            )
        elif estimated > 0:
            status = "🟡 PARTIALLY VERIFIED"
            explanation = (
                "Historical cost is unavailable for some sales; "
                "current product cost was used as an estimate."
            )
        else:
            status = "🟢 HISTORICALLY VERIFIED"
            explanation = (
                "All sales have a historical cost source."
            )

        print(f"Status                  : {status}")
        print(f"Explanation             : {explanation}")

        print()
        print("=" * 60)
        print("V80 DEVELOPMENT RECOMMENDATION")
        print("=" * 60)

        print("1. Add permanent cost_snapshot to sales.")
        print("2. Capture buying cost during checkout.")
        print("3. Never depend on today's product cost for old sales.")
        print("4. Preserve historical profitability.")
        print("5. Reconcile sales against inventory purchases.")
        print("6. Feed only verified profitability into KPI intelligence.")

        print()
        print("=" * 60)
        print("V80 SAFETY STATUS")
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
