"""
POS LEDGER NG V104
POST-WRITE INTEGRITY VERIFICATION

Purpose:
    Verify that the V103 timestamp correction persisted correctly
    and that the approved sale/inventory relationship remains intact.

Safety:
    - READ-ONLY.
    - No INSERT.
    - No UPDATE.
    - No DELETE.
    - No transaction writes.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


DB_PATH = (
    Path.home()
    / "POS-Ledger-NG"
    / "data"
    / "posledger.db"
)

SALE_ID = 15
MOVEMENT_ID = 4
PRODUCT_ID = 1
REFERENCE = "PLN-20260814-000015"

EXPECTED_QUANTITY = 1.0
EXPECTED_TIMESTAMP = "2026-08-14 00:50:48"
EXPECTED_MOVEMENT_TYPE = "SALE"


def line():
    print("=" * 60)


def section(title):
    print()
    line()
    print(title)
    line()


def table_exists(conn, table):
    row = conn.execute(
        """
        SELECT COUNT(*)
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (table,),
    ).fetchone()

    return bool(row[0])


def get_columns(conn, table):
    return {
        row[1]
        for row in conn.execute(
            f"PRAGMA table_info({table})"
        ).fetchall()
    }


def find_column(columns, candidates):
    lookup = {
        str(c).lower(): c
        for c in columns
    }

    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]

    return None


def close_quietly(conn):
    try:
        conn.close()
    except Exception:
        pass


def main():

    print("=" * 60)
    print("POS LEDGER NG V104")
    print("POST-WRITE INTEGRITY VERIFICATION")
    print("=" * 60)

    print()
    print("Database path :", DB_PATH)
    print("Database mode : READ-ONLY")

    # --------------------------------------------------
    # DATABASE OPEN
    # --------------------------------------------------

    if not DB_PATH.exists():
        print()
        print("🔴 DATABASE NOT FOUND")
        return

    conn = sqlite3.connect(
        DB_PATH,
        uri=False,
    )

    conn.row_factory = sqlite3.Row

    try:

        # --------------------------------------------------
        # REQUIRED TABLES
        # --------------------------------------------------

        section("DATABASE TABLES")

        required_tables = [
            "sales",
            "products",
            "inventory_movements",
            "purchases",
        ]

        all_tables_ok = True

        for table in required_tables:

            available = table_exists(
                conn,
                table,
            )

            print(
                f"{table:<24}: "
                f"{'AVAILABLE' if available else 'MISSING'}"
            )

            if not available:
                all_tables_ok = False

        if not all_tables_ok:

            print()
            print("🔴 V104 SAFETY STOP")
            print("Required database tables are missing.")
            return

        # --------------------------------------------------
        # SALES COLUMN DISCOVERY
        # --------------------------------------------------

        sale_columns = get_columns(
            conn,
            "sales",
        )

        sale_id_col = find_column(
            sale_columns,
            ["id", "sale_id"],
        )

        sale_product_col = find_column(
            sale_columns,
            ["product_id"],
        )

        sale_quantity_col = find_column(
            sale_columns,
            ["quantity", "qty"],
        )

        sale_date_col = find_column(
            sale_columns,
            [
                "sale_date",
                "transaction_date",
                "created_at",
                "date",
            ],
        )

        sale_reference_col = find_column(
            sale_columns,
            [
                "receipt",
                "receipt_no",
                "receipt_number",
                "reference",
                "ref",
            ],
        )

        if not all(
            [
                sale_id_col,
                sale_product_col,
                sale_quantity_col,
                sale_date_col,
            ]
        ):

            print()
            print("🔴 V104 SAFETY STOP")
            print("Required sales columns could not be identified.")
            return

        # --------------------------------------------------
        # INVENTORY COLUMN DISCOVERY
        # --------------------------------------------------

        inventory_columns = get_columns(
            conn,
            "inventory_movements",
        )

        inv_id_col = find_column(
            inventory_columns,
            ["id", "movement_id"],
        )

        inv_product_col = find_column(
            inventory_columns,
            ["product_id"],
        )

        inv_quantity_col = find_column(
            inventory_columns,
            ["quantity", "qty"],
        )

        inv_type_col = find_column(
            inventory_columns,
            ["movement_type", "type"],
        )

        inv_date_col = find_column(
            inventory_columns,
            [
                "movement_date",
                "transaction_date",
                "created_at",
                "date",
            ],
        )

        inv_reference_col = find_column(
            inventory_columns,
            [
                "reference",
                "receipt",
                "receipt_no",
                "ref",
            ],
        )

        if not all(
            [
                inv_id_col,
                inv_product_col,
                inv_quantity_col,
                inv_type_col,
                inv_date_col,
                inv_reference_col,
            ]
        ):

            print()
            print("🔴 V104 SAFETY STOP")
            print(
                "Required inventory movement columns "
                "could not be identified."
            )
            return

        # --------------------------------------------------
        # V103 PERSISTENCE CHECK
        # --------------------------------------------------

        section("V103 PERSISTENCE CHECK")

        movement = conn.execute(
            f"""
            SELECT *
            FROM inventory_movements
            WHERE {inv_id_col} = ?
            """,
            (MOVEMENT_ID,),
        ).fetchone()

        if movement is None:

            print(
                f"🔴 Movement {MOVEMENT_ID} is missing."
            )

            print(
                "V103 correction cannot be verified."
            )
            return

        movement_product = int(
            movement[inv_product_col]
        )

        movement_quantity = float(
            movement[inv_quantity_col] or 0
        )

        movement_type = str(
            movement[inv_type_col] or ""
        ).strip().upper()

        movement_date = str(
            movement[inv_date_col]
        )

        movement_reference = str(
            movement[inv_reference_col] or ""
        ).strip()

        print(
            f"Movement ID       : {MOVEMENT_ID}"
        )

        print(
            f"Product ID        : {movement_product}"
        )

        print(
            f"Quantity          : {movement_quantity:.2f}"
        )

        print(
            f"Movement type     : {movement_type}"
        )

        print(
            f"Movement timestamp: {movement_date}"
        )

        print(
            f"Reference         : {movement_reference}"
        )

        # --------------------------------------------------
        # MOVEMENT VALIDATION
        # --------------------------------------------------

        section("V104 MOVEMENT VALIDATION")

        product_ok = (
            movement_product == PRODUCT_ID
        )

        quantity_ok = (
            abs(
                movement_quantity
                - EXPECTED_QUANTITY
            ) < 0.000001
        )

        type_ok = (
            movement_type
            == EXPECTED_MOVEMENT_TYPE
        )

        reference_ok = (
            movement_reference
            == REFERENCE
        )

        timestamp_ok = (
            movement_date
            == EXPECTED_TIMESTAMP
        )

        print(
            "Product check       : "
            f"{'PASS' if product_ok else 'FAIL'}"
        )

        print(
            "Quantity check      : "
            f"{'PASS' if quantity_ok else 'FAIL'}"
        )

        print(
            "Movement type check : "
            f"{'PASS' if type_ok else 'FAIL'}"
        )

        print(
            "Reference check     : "
            f"{'PASS' if reference_ok else 'FAIL'}"
        )

        print(
            "Timestamp check     : "
            f"{'PASS' if timestamp_ok else 'FAIL'}"
        )

        movement_integrity_ok = all(
            [
                product_ok,
                quantity_ok,
                type_ok,
                reference_ok,
                timestamp_ok,
            ]
        )

        # --------------------------------------------------
        # SALE VERIFICATION
        # --------------------------------------------------

        section("V104 SALE VERIFICATION")

        sale = conn.execute(
            f"""
            SELECT *
            FROM sales
            WHERE {sale_id_col} = ?
            """,
            (SALE_ID,),
        ).fetchone()

        if sale is None:

            print(
                f"🔴 Sale {SALE_ID} is missing."
            )

            sale_integrity_ok = False

        else:

            sale_product = int(
                sale[sale_product_col]
            )

            sale_quantity = float(
                sale[sale_quantity_col] or 0
            )

            sale_date = str(
                sale[sale_date_col]
            )

            sale_reference = ""

            if sale_reference_col:
                sale_reference = str(
                    sale[sale_reference_col] or ""
                ).strip()

            print(
                f"Sale ID        : {SALE_ID}"
            )

            print(
                f"Product ID     : {sale_product}"
            )

            print(
                f"Quantity       : {sale_quantity:.2f}"
            )

            print(
                f"Sale timestamp : {sale_date}"
            )

            print(
                f"Reference      : "
                f"{sale_reference or 'NONE'}"
            )

            sale_product_ok = (
                sale_product == PRODUCT_ID
            )

            sale_quantity_ok = (
                abs(
                    sale_quantity
                    - EXPECTED_QUANTITY
                ) < 0.000001
            )

            sale_date_ok = (
                sale_date
                == EXPECTED_TIMESTAMP
            )

            sale_reference_ok = (
                sale_reference == REFERENCE
            )

            print()

            print(
                "Product check    : "
                f"{'PASS' if sale_product_ok else 'FAIL'}"
            )

            print(
                "Quantity check   : "
                f"{'PASS' if sale_quantity_ok else 'FAIL'}"
            )

            print(
                "Timestamp check  : "
                f"{'PASS' if sale_date_ok else 'FAIL'}"
            )

            print(
                "Reference check  : "
                f"{'PASS' if sale_reference_ok else 'FAIL'}"
            )

            sale_integrity_ok = all(
                [
                    sale_product_ok,
                    sale_quantity_ok,
                    sale_date_ok,
                    sale_reference_ok,
                ]
            )

        # --------------------------------------------------
        # SALE ↔ MOVEMENT RELATIONSHIP
        # --------------------------------------------------

        section("V104 TRANSACTION ↔ INVENTORY RELATIONSHIP")

        relationship_ok = (
            movement_integrity_ok
            and sale_integrity_ok
        )

        if relationship_ok:

            print(
                "🟢 SALE ↔ INVENTORY RELATIONSHIP : VERIFIED"
            )

            print(
                "Product, quantity, reference and "
                "timestamp agree."
            )

        else:

            print(
                "🔴 SALE ↔ INVENTORY RELATIONSHIP : FAILED"
            )

        # --------------------------------------------------
        # DUPLICATE REFERENCE CHECK
        # --------------------------------------------------

        section("V104 DUPLICATE REFERENCE CHECK")

        duplicate_movements = conn.execute(
            f"""
            SELECT
                COUNT(*)
            FROM inventory_movements
            WHERE {inv_reference_col} = ?
              AND UPPER({inv_type_col}) = ?
            """,
            (
                REFERENCE,
                EXPECTED_MOVEMENT_TYPE,
            ),
        ).fetchone()[0]

        print(
            f"SALE movements using reference : "
            f"{duplicate_movements}"
        )

        duplicate_reference_ok = (
            duplicate_movements == 1
        )

        print(
            "Reference uniqueness : "
            f"{'PASS' if duplicate_reference_ok else 'FAIL'}"
        )

        # --------------------------------------------------
        # PRODUCT MOVEMENT HISTORY
        # --------------------------------------------------

        section("V104 PRODUCT MOVEMENT HISTORY")

        history = conn.execute(
            f"""
            SELECT
                {inv_id_col} AS movement_id,
                {inv_type_col} AS movement_type,
                {inv_quantity_col} AS quantity,
                {inv_date_col} AS movement_date,
                {inv_reference_col} AS reference
            FROM inventory_movements
            WHERE {inv_product_col} = ?
            ORDER BY {inv_date_col}, {inv_id_col}
            """,
            (PRODUCT_ID,),
        ).fetchall()

        if not history:

            print("No inventory history found.")

        else:

            for row in history:

                ref = row["reference"]

                print(
                    f"ID {row['movement_id']:<4} "
                    f"{str(row['movement_type']):<10} "
                    f"Qty {float(row['quantity'] or 0):7.2f} "
                    f"Date {row['movement_date']} "
                    f"Ref {ref or 'NONE'}"
                )

        # --------------------------------------------------
        # CURRENT SALES / MOVEMENT COUNTS
        # --------------------------------------------------

        section("V104 CURRENT AUDIT COUNTS")

        completed_sales = conn.execute(
            f"""
            SELECT COUNT(*)
            FROM sales
            """
        ).fetchone()[0]

        sale_movements = conn.execute(
            f"""
            SELECT COUNT(*)
            FROM inventory_movements
            WHERE UPPER({inv_type_col}) = 'SALE'
            """
        ).fetchone()[0]

        purchases = conn.execute(
            """
            SELECT COUNT(*)
            FROM purchases
            """
        ).fetchone()[0]

        purchase_movements = conn.execute(
            f"""
            SELECT COUNT(*)
            FROM inventory_movements
            WHERE UPPER({inv_type_col}) IN
                  ('PURCHASE', 'STOCK_IN', 'IN')
            """
        ).fetchone()[0]

        print(
            f"Completed sales              : "
            f"{completed_sales}"
        )

        print(
            f"Inventory SALE movements    : "
            f"{sale_movements}"
        )

        print(
            f"Purchase records             : "
            f"{purchases}"
        )

        print(
            f"Inventory PURCHASE movements: "
            f"{purchase_movements}"
        )

        # --------------------------------------------------
        # REMAINING UNMATCHED SALES
        # --------------------------------------------------

        section("V104 REMAINING UNMATCHED SALES")

        unmatched = []

        sales_rows = conn.execute(
            f"""
            SELECT
                s.{sale_id_col} AS sale_id,
                s.{sale_product_col} AS product_id,
                s.{sale_quantity_col} AS quantity,
                s.{sale_date_col} AS sale_date
                {', s.' + sale_reference_col + ' AS reference'
                if sale_reference_col else ''}
            FROM sales s
            ORDER BY s.{sale_id_col}
            """
        ).fetchall()

        for row in sales_rows:

            sale_id = int(row["sale_id"])

            product_id = int(row["product_id"])

            quantity = float(
                row["quantity"] or 0
            )

            reference = ""

            if sale_reference_col:
                reference = str(
                    row["reference"] or ""
                ).strip()

            if sale_id == SALE_ID:
                continue

            # First try exact reference.
            matched = False

            if reference:

                exact_count = conn.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM inventory_movements
                    WHERE {inv_product_col} = ?
                      AND ABS(
                          {inv_quantity_col} - ?
                      ) < 0.000001
                      AND UPPER({inv_type_col}) = 'SALE'
                      AND {inv_reference_col} = ?
                    """,
                    (
                        product_id,
                        quantity,
                        reference,
                    ),
                ).fetchone()[0]

                matched = (
                    exact_count > 0
                )

            if not matched:

                unmatched.append(
                    (
                        sale_id,
                        product_id,
                        quantity,
                        reference,
                    )
                )

        print(
            f"Unmatched sales excluding "
            f"verified sale {SALE_ID}: "
            f"{len(unmatched)}"
        )

        for (
            sale_id,
            product_id,
            quantity,
            reference,
        ) in unmatched:

            print(
                f"Sale {sale_id} | "
                f"Product {product_id} | "
                f"Qty {quantity:.2f} | "
                f"Ref {reference or 'NONE'}"
            )

        # --------------------------------------------------
        # CRITICAL FAILURE CHECK
        # --------------------------------------------------

        section("V104 INTEGRITY DECISION")

        critical_failures = 0

        if not movement_integrity_ok:
            critical_failures += 1

        if not sale_integrity_ok:
            critical_failures += 1

        if not relationship_ok:
            critical_failures += 1

        if not duplicate_reference_ok:
            critical_failures += 1

        print(
            f"Critical failures : "
            f"{critical_failures}"
        )

        if critical_failures == 0:

            print()
            print(
                "🟢 V103 WRITE VERIFIED"
            )

            print(
                "The approved timestamp correction "
                "persisted correctly."
            )

        else:

            print()
            print(
                "🔴 V104 INTEGRITY FAILURE"
            )

            print(
                "Further repair actions are blocked."
            )

        # --------------------------------------------------
        # WRITE SAFETY ASSERTION
        # --------------------------------------------------

        section("V104 WRITE SAFETY")

        print(
            "Database writes : 0"
        )

        print(
            "INSERT          : 0"
        )

        print(
            "UPDATE          : 0"
        )

        print(
            "DELETE          : 0"
        )

        print(
            "Mode            : READ-ONLY"
        )

        # --------------------------------------------------
        # EXECUTIVE DECISION
        # --------------------------------------------------

        section("V104 EXECUTIVE DECISION")

        if critical_failures == 0:

            if unmatched:

                print(
                    "🟡 V103 CORRECTION VERIFIED"
                )

                print(
                    "The approved repair is intact."
                )

                print(
                    f"{len(unmatched)} other sales "
                    "remain unresolved."
                )

                print(
                    "No automatic repair is authorized "
                    "for those records."
                )

            else:

                print(
                    "🟢 TRANSACTION ↔ INVENTORY "
                    "INTEGRITY VERIFIED"
                )

        else:

            print(
                "🔴 STOP — INTEGRITY INVESTIGATION REQUIRED"
            )

        # --------------------------------------------------
        # SAFETY STATUS
        # --------------------------------------------------

        section("V104 SAFETY STATUS")

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
        print("V104 COMPLETE")

    except Exception as exc:

        print()
        line()
        print("🔴 V104 EXCEPTION")
        line()

        print(
            f"{type(exc).__name__}: {exc}"
        )

        print()
        print(
            "V104 remained READ-ONLY."
        )

    finally:
        close_quietly(conn)


if __name__ == "__main__":
    main()
