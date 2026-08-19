"""
POS LEDGER NG V100
POST-REPAIR VERIFICATION & INTEGRITY AUDIT

READ-ONLY

Purpose:
    Verify the state after V99.

Safety:
    - No INSERT
    - No UPDATE
    - No DELETE
    - No schema changes
    - Database opened read-only
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from collections import defaultdict


BASE_DIR = Path.home() / "POS-Ledger-NG"
DB_PATH = BASE_DIR / "data" / "posledger.db"

APPROVED_SALE_ID = 15
APPROVED_PRODUCT_ID = 1
APPROVED_REFERENCE = "PLN-20260814-000015"
EXPECTED_QUANTITY = 1.0
EXPECTED_SALE_DATE = "2026-08-14 00:50:48"


def line():
    print("=" * 60)


def section(title):
    print()
    line()
    print(title)
    line()


def get_columns(conn, table):
    rows = conn.execute(
        f'PRAGMA table_info("{table}")'
    ).fetchall()

    return {
        row[1]
        for row in rows
    }


def find_column(columns, candidates):
    lookup = {
        column.casefold(): column
        for column in columns
    }

    for candidate in candidates:
        found = lookup.get(candidate.casefold())

        if found:
            return found

    return None


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


def safe_float(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def main():

    print("=" * 60)
    print("POS LEDGER NG V100")
    print("POST-REPAIR VERIFICATION & INTEGRITY AUDIT")
    print("=" * 60)

    print()
    print("=" * 60)
    print("DATABASE")
    print("=" * 60)

    print(f"Database path : {DB_PATH}")
    print("Database mode : READ-ONLY")

    if not DB_PATH.exists():
        print()
        print("🔴 DATABASE NOT FOUND")
        return

    # ---------------------------------------------------------
    # READ-ONLY CONNECTION
    # ---------------------------------------------------------

    uri = f"file:{DB_PATH}?mode=ro"

    conn = sqlite3.connect(
        uri,
        uri=True,
    )

    conn.row_factory = sqlite3.Row

    try:

        required_tables = [
            "sales",
            "products",
            "inventory_movements",
            "purchases",
        ]

        section("REQUIRED TABLES")

        table_status = {}

        for table in required_tables:
            exists = table_exists(
                conn,
                table,
            )

            table_status[table] = exists

            print(
                f"{table:<24}: "
                f"{'AVAILABLE' if exists else 'MISSING'}"
            )

        if not all(table_status.values()):
            print()
            print("🔴 V100 CANNOT PROCEED")
            print("Required table(s) missing.")
            return

        # -----------------------------------------------------
        # SCHEMA DISCOVERY
        # -----------------------------------------------------

        sales_cols = get_columns(
            conn,
            "sales",
        )

        products_cols = get_columns(
            conn,
            "products",
        )

        inventory_cols = get_columns(
            conn,
            "inventory_movements",
        )

        purchase_cols = get_columns(
            conn,
            "purchases",
        )

        sale_id_col = find_column(
            sales_cols,
            ["id", "sale_id"],
        )

        sale_product_col = find_column(
            sales_cols,
            ["product_id"],
        )

        sale_qty_col = find_column(
            sales_cols,
            ["quantity", "qty"],
        )

        sale_date_col = find_column(
            sales_cols,
            [
                "sale_date",
                "transaction_date",
                "created_at",
                "date",
            ],
        )

        sale_ref_col = find_column(
            sales_cols,
            [
                "receipt",
                "receipt_no",
                "receipt_number",
                "reference",
                "ref",
            ],
        )

        product_id_col = find_column(
            products_cols,
            ["id", "product_id"],
        )

        product_name_col = find_column(
            products_cols,
            [
                "name",
                "product_name",
            ],
        )

        inv_id_col = find_column(
            inventory_cols,
            ["id", "movement_id"],
        )

        inv_product_col = find_column(
            inventory_cols,
            ["product_id"],
        )

        inv_qty_col = find_column(
            inventory_cols,
            ["quantity", "qty"],
        )

        inv_type_col = find_column(
            inventory_cols,
            [
                "movement_type",
                "type",
            ],
        )

        inv_ref_col = find_column(
            inventory_cols,
            [
                "reference",
                "receipt",
                "receipt_no",
                "ref",
            ],
        )

        inv_date_col = find_column(
            inventory_cols,
            [
                "movement_date",
                "transaction_date",
                "created_at",
                "date",
            ],
        )

        purchase_id_col = find_column(
            purchase_cols,
            ["id", "purchase_id"],
        )

        purchase_product_col = find_column(
            purchase_cols,
            ["product_id"],
        )

        purchase_qty_col = find_column(
            purchase_cols,
            ["quantity", "qty"],
        )

        # -----------------------------------------------------
        # TRANSACTION COUNTS
        # -----------------------------------------------------

        section("V100 AUDIT INPUT COUNTS")

        sales_count = conn.execute(
            "SELECT COUNT(*) FROM sales"
        ).fetchone()[0]

        purchases_count = conn.execute(
            "SELECT COUNT(*) FROM purchases"
        ).fetchone()[0]

        sale_movement_count = conn.execute(
            f"""
            SELECT COUNT(*)
            FROM inventory_movements
            WHERE UPPER({inv_type_col}) = 'SALE'
            """
        ).fetchone()[0]

        purchase_movement_count = conn.execute(
            f"""
            SELECT COUNT(*)
            FROM inventory_movements
            WHERE UPPER({inv_type_col}) IN
                  ('PURCHASE', 'IN', 'STOCK_IN')
            """
        ).fetchone()[0]

        print(
            f"Completed sales             : {sales_count}"
        )

        print(
            f"Purchase records            : {purchases_count}"
        )

        print(
            f"Inventory SALE movements    : "
            f"{sale_movement_count}"
        )

        print(
            f"Inventory PURCHASE movements: "
            f"{purchase_movement_count}"
        )

        # -----------------------------------------------------
        # APPROVED SALE VERIFICATION
        # -----------------------------------------------------

        section(
            "V100 APPROVED REPAIR VERIFICATION"
        )

        sale = conn.execute(
            f"""
            SELECT *
            FROM sales
            WHERE {sale_id_col} = ?
            """,
            (APPROVED_SALE_ID,),
        ).fetchone()

        if sale is None:
            print(
                "🔴 APPROVED SALE NOT FOUND"
            )

            return

        actual_product_id = int(
            sale[sale_product_col]
        )

        actual_quantity = safe_float(
            sale[sale_qty_col]
        )

        actual_sale_date = (
            str(sale[sale_date_col])
            if sale_date_col
            else "UNKNOWN"
        )

        actual_reference = (
            str(sale[sale_ref_col] or "").strip()
            if sale_ref_col
            else ""
        )

        product_name = "UNKNOWN"

        if product_id_col and product_name_col:

            product = conn.execute(
                f"""
                SELECT {product_name_col}
                FROM products
                WHERE {product_id_col} = ?
                """,
                (actual_product_id,),
            ).fetchone()

            if product:
                product_name = str(
                    product[0]
                )

        print(
            f"Sale ID             : "
            f"{APPROVED_SALE_ID}"
        )

        print(
            f"Product ID          : "
            f"{actual_product_id}"
        )

        print(
            f"Product             : "
            f"{product_name}"
        )

        print(
            f"Quantity            : "
            f"{actual_quantity:.2f}"
        )

        print(
            f"Sale date           : "
            f"{actual_sale_date}"
        )

        print(
            f"Receipt/reference   : "
            f"{actual_reference or 'NOT RECORDED'}"
        )

        product_ok = (
            actual_product_id
            == APPROVED_PRODUCT_ID
        )

        quantity_ok = (
            abs(
                actual_quantity
                - EXPECTED_QUANTITY
            ) < 0.000001
        )

        reference_ok = (
            actual_reference
            == APPROVED_REFERENCE
        )

        date_ok = (
            actual_sale_date
            == EXPECTED_SALE_DATE
        )

        print()

        print(
            f"Product check       : "
            f"{'PASS' if product_ok else 'FAIL'}"
        )

        print(
            f"Quantity check      : "
            f"{'PASS' if quantity_ok else 'FAIL'}"
        )

        print(
            f"Reference check     : "
            f"{'PASS' if reference_ok else 'FAIL'}"
        )

        print(
            f"Sale-date check     : "
            f"{'PASS' if date_ok else 'REVIEW'}"
        )

        # -----------------------------------------------------
        # INVENTORY MATCH SEARCH
        # -----------------------------------------------------

        section(
            "V100 INVENTORY MOVEMENT VERIFICATION"
        )

        matching_movements = conn.execute(
            f"""
            SELECT *
            FROM inventory_movements
            WHERE {inv_product_col} = ?
              AND ABS({inv_qty_col} - ?) < 0.000001
              AND UPPER({inv_type_col}) = 'SALE'
              AND {inv_ref_col} = ?
            ORDER BY {inv_id_col}
            """,
            (
                APPROVED_PRODUCT_ID,
                EXPECTED_QUANTITY,
                APPROVED_REFERENCE,
            ),
        ).fetchall()

        print(
            f"Matching SALE movements : "
            f"{len(matching_movements)}"
        )

        if len(matching_movements) == 0:

            print(
                "🔴 APPROVED MOVEMENT NOT FOUND"
            )

            movement_verified = False

        elif len(matching_movements) == 1:

            movement_verified = True

            movement = matching_movements[0]

            movement_id = movement[
                inv_id_col
            ]

            movement_date = (
                str(movement[inv_date_col])
                if inv_date_col
                else "UNKNOWN"
            )

            movement_reference = (
                str(movement[inv_ref_col])
                if inv_ref_col
                else ""
            )

            movement_quantity = safe_float(
                movement[inv_qty_col]
            )

            print(
                f"Movement ID         : "
                f"{movement_id}"
            )

            print(
                f"Movement quantity   : "
                f"{movement_quantity:.2f}"
            )

            print(
                f"Movement date       : "
                f"{movement_date}"
            )

            print(
                f"Movement reference  : "
                f"{movement_reference}"
            )

            print()

            print(
                "Reference status    : 🟢 EXACT"
            )

            print(
                "Quantity status     : 🟢 EXACT"
            )

            if movement_date == EXPECTED_SALE_DATE:

                print(
                    "Date status         : 🟢 EXACT"
                )

                date_review = False

            else:

                print(
                    "Date status         : 🟡 REVIEW"
                )

                print(
                    "Reason              : "
                    "Inventory movement timestamp "
                    "differs from the sale timestamp."
                )

                date_review = True

        else:

            movement_verified = False
            date_review = True

            print(
                "🔴 DUPLICATE MATCHES FOUND"
            )

            for movement in matching_movements:

                print(
                    f"Movement ID : "
                    f"{movement[inv_id_col]}"
                )

        # -----------------------------------------------------
        # ALL INVENTORY MOVEMENTS FOR PRODUCT
        # -----------------------------------------------------

        section(
            "V100 PRODUCT MOVEMENT HISTORY"
        )

        product_movements = conn.execute(
            f"""
            SELECT *
            FROM inventory_movements
            WHERE {inv_product_col} = ?
            ORDER BY {inv_date_col if inv_date_col else inv_id_col}
            """,
            (APPROVED_PRODUCT_ID,),
        ).fetchall()

        if not product_movements:

            print(
                "No inventory movements found."
            )

        else:

            for movement in product_movements:

                movement_id = movement[
                    inv_id_col
                ]

                movement_type = str(
                    movement[inv_type_col]
                )

                quantity = safe_float(
                    movement[inv_qty_col]
                )

                reference = (
                    str(
                        movement[inv_ref_col]
                    )
                    if inv_ref_col
                    else ""
                )

                movement_date = (
                    str(
                        movement[inv_date_col]
                    )
                    if inv_date_col
                    else "UNKNOWN"
                )

                print(
                    f"ID {movement_id:<4} "
                    f"{movement_type:<10} "
                    f"Qty {quantity:>7.2f} "
                    f"Date {movement_date} "
                    f"Ref {reference}"
                )

        # -----------------------------------------------------
        # SALE / INVENTORY QUANTITY RECONCILIATION
        # -----------------------------------------------------

        section(
            "V100 QUANTITY RECONCILIATION"
        )

        sales_by_product = defaultdict(float)
        inventory_sale_by_product = defaultdict(float)

        sale_rows = conn.execute(
            f"""
            SELECT
                {sale_product_col} AS product_id,
                SUM({sale_qty_col}) AS quantity
            FROM sales
            GROUP BY {sale_product_col}
            """
        ).fetchall()

        for row in sale_rows:

            sales_by_product[
                int(row["product_id"])
            ] = safe_float(
                row["quantity"]
            )

        inventory_rows = conn.execute(
            f"""
            SELECT
                {inv_product_col} AS product_id,
                SUM({inv_qty_col}) AS quantity
            FROM inventory_movements
            WHERE UPPER({inv_type_col}) = 'SALE'
            GROUP BY {inv_product_col}
            """
        ).fetchall()

        for row in inventory_rows:

            inventory_sale_by_product[
                int(row["product_id"])
            ] = safe_float(
                row["quantity"]
            )

        product_ids = sorted(
            set(sales_by_product)
            | set(inventory_sale_by_product)
        )

        total_sales = 0.0
        total_inventory_sales = 0.0
        total_gap = 0.0

        for product_id in product_ids:

            sales_qty = sales_by_product[
                product_id
            ]

            inventory_qty = (
                inventory_sale_by_product[
                    product_id
                ]
            )

            gap = (
                sales_qty
                - inventory_qty
            )

            total_sales += sales_qty
            total_inventory_sales += inventory_qty
            total_gap += gap

            product_name = "UNKNOWN"

            if product_id_col and product_name_col:

                row = conn.execute(
                    f"""
                    SELECT {product_name_col}
                    FROM products
                    WHERE {product_id_col} = ?
                    """,
                    (product_id,),
                ).fetchone()

                if row:
                    product_name = str(
                        row[0]
                    )

            status = (
                "🟢 RECONCILED"
                if abs(gap) < 0.000001
                else "🔴 MISMATCH"
            )

            print(
                "----------------------------------------"
            )

            print(
                f"Product ID          : {product_id}"
            )

            print(
                f"Product             : {product_name}"
            )

            print(
                f"Sales units         : {sales_qty:.2f}"
            )

            print(
                f"Inventory SALE units: "
                f"{inventory_qty:.2f}"
            )

            print(
                f"Difference          : {gap:.2f}"
            )

            print(
                f"Status              : {status}"
            )

        print(
            "----------------------------------------"
        )

        print(
            f"Total sales units         : "
            f"{total_sales:.2f}"
        )

        print(
            f"Total inventory SALE units: "
            f"{total_inventory_sales:.2f}"
        )

        print(
            f"Total unrepresented units : "
            f"{total_gap:.2f}"
        )

        # -----------------------------------------------------
        # UNMATCHED SALES
        # -----------------------------------------------------

        section(
            "V100 REMAINING UNMATCHED SALES"
        )

        unmatched_sales = []

        all_sales = conn.execute(
            f"""
            SELECT *
            FROM sales
            ORDER BY {sale_id_col}
            """
        ).fetchall()

        for sale_row in all_sales:

            sale_id = sale_row[
                sale_id_col
            ]

            product_id = int(
                sale_row[sale_product_col]
            )

            quantity = safe_float(
                sale_row[sale_qty_col]
            )

            reference = (
                str(
                    sale_row[sale_ref_col] or ""
                ).strip()
                if sale_ref_col
                else ""
            )

            # A sale is considered represented if
            # there is an exact reference/product/
            # quantity SALE movement.
            exact = conn.execute(
                f"""
                SELECT COUNT(*)
                FROM inventory_movements
                WHERE {inv_product_col} = ?
                  AND ABS({inv_qty_col} - ?) < 0.000001
                  AND UPPER({inv_type_col}) = 'SALE'
                  AND {inv_ref_col} = ?
                """,
                (
                    product_id,
                    quantity,
                    reference,
                ),
            ).fetchone()[0]

            if exact == 0:

                unmatched_sales.append(
                    (
                        sale_id,
                        product_id,
                        quantity,
                        reference,
                    )
                )

        print(
            f"Unmatched sales : "
            f"{len(unmatched_sales)}"
        )

        for item in unmatched_sales:

            sale_id, product_id, quantity, reference = item

            print(
                f"Sale {sale_id} | "
                f"Product {product_id} | "
                f"Qty {quantity:.2f} | "
                f"Ref {reference or 'NONE'}"
            )

        # -----------------------------------------------------
        # DUPLICATE REFERENCE CHECK
        # -----------------------------------------------------

        section(
            "V100 DUPLICATE REFERENCE CHECK"
        )

        duplicate_refs = conn.execute(
            f"""
            SELECT
                {inv_ref_col} AS reference,
                COUNT(*) AS count
            FROM inventory_movements
            WHERE UPPER({inv_type_col}) = 'SALE'
              AND {inv_ref_col} IS NOT NULL
              AND TRIM({inv_ref_col}) != ''
            GROUP BY {inv_ref_col}
            HAVING COUNT(*) > 1
            ORDER BY COUNT(*) DESC
            """
        ).fetchall()

        print(
            f"Duplicate SALE references : "
            f"{len(duplicate_refs)}"
        )

        for row in duplicate_refs:

            print(
                f"Reference {row['reference']} "
                f"appears {row['count']} times"
            )

        # -----------------------------------------------------
        # FINAL INTEGRITY DECISION
        # -----------------------------------------------------

        section(
            "V100 INTEGRITY DECISION"
        )

        critical_failures = []

        if not product_ok:
            critical_failures.append(
                "Approved product changed"
            )

        if not quantity_ok:
            critical_failures.append(
                "Approved quantity changed"
            )

        if not reference_ok:
            critical_failures.append(
                "Approved reference changed"
            )

        if not movement_verified:
            critical_failures.append(
                "Approved inventory movement "
                "is not uniquely verified"
            )

        if len(matching_movements) > 1:
            critical_failures.append(
                "Duplicate inventory movement "
                "matches approved reference"
            )

        if duplicate_refs:
            critical_failures.append(
                "Duplicate SALE references exist"
            )

        print(
            f"Critical failures : "
            f"{len(critical_failures)}"
        )

        for failure in critical_failures:
            print(
                f"🔴 {failure}"
            )

        if date_review:
            print()
            print(
                "🟡 TIMESTAMP REVIEW REQUIRED"
            )

            print(
                "The existing inventory movement "
                "has a different timestamp from "
                "the sale."
            )

            print(
                "V100 does NOT change that timestamp."
            )

        print()
        print(
            "V100 database writes : 0"
        )

        print(
            "V100 INSERT operations: 0"
        )

        print(
            "V100 UPDATE operations: 0"
        )

        print(
            "V100 DELETE operations: 0"
        )

        # -----------------------------------------------------
        # EXECUTIVE DECISION
        # -----------------------------------------------------

        section(
            "V100 EXECUTIVE DECISION"
        )

        if critical_failures:

            print(
                "🔴 STOP — INTEGRITY ISSUES REMAIN"
            )

            print(
                "Do not proceed to production "
                "hardening yet."
            )

        elif date_review:

            print(
                "🟡 VERIFIED WITH TIMESTAMP REVIEW"
            )

            print(
                "Core reference/quantity integrity "
                "is verified, but the movement timestamp "
                "requires separate investigation."
            )

            print(
                "Do not automatically alter the timestamp."
            )

        elif unmatched_sales:

            print(
                "🟡 PARTIAL RECONCILIATION"
            )

            print(
                "The approved candidate is verified, "
                "but other sales remain unresolved."
            )

        else:

            print(
                "🟢 INTEGRITY VERIFIED"
            )

        # -----------------------------------------------------
        # SAFETY STATUS
        # -----------------------------------------------------

        section(
            "V100 SAFETY STATUS"
        )

        print(
            "Mode                  : READ-ONLY"
        )

        print(
            "Database modified     : NO"
        )

        print(
            "Sales modified        : NO"
        )

        print(
            "Inventory modified    : NO"
        )

        print(
            "Purchases modified    : NO"
        )

        print(
            "Products modified     : NO"
        )

        print(
            "Balance modified      : NO"
        )

        print(
            "Credit modified       : NO"
        )

        print(
            "Suppliers modified    : NO"
        )

        print(
            "Expenses modified     : NO"
        )

        print()
        print(
            "V100 COMPLETE"
        )

    finally:
        conn.close()


if __name__ == "__main__":
    main()
