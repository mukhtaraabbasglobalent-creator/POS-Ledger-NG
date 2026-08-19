"""
POS LEDGER NG V101
TIMESTAMP INVESTIGATION & REPAIR RESOLUTION PREVIEW

READ-ONLY

Purpose:
    Investigate the timestamp difference between an approved sale
    and its existing inventory SALE movement.

Safety:
    - No INSERT
    - No UPDATE
    - No DELETE
    - No schema changes
    - Database opened in read-only mode
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from datetime import datetime


DB_PATH = (
    Path.home()
    / "POS-Ledger-NG"
    / "data"
    / "posledger.db"
)

SALE_ID = 15
PRODUCT_ID = 1
REFERENCE = "PLN-20260814-000015"
EXPECTED_SALE_DATE = "2026-08-14 00:50:48"


def line():
    print("=" * 60)


def section(title):
    print()
    line()
    print(title)
    line()


def columns(conn, table):
    rows = conn.execute(
        f'PRAGMA table_info("{table}")'
    ).fetchall()

    return {row[1] for row in rows}


def choose(cols, names):
    lookup = {
        c.lower(): c
        for c in cols
    }

    for name in names:
        if name.lower() in lookup:
            return lookup[name.lower()]

    return None


def parse_date(value):
    if not value:
        return None

    text = str(value).strip()

    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass

    return None


def main():

    print("=" * 60)
    print("POS LEDGER NG V101")
    print("TIMESTAMP INVESTIGATION & RESOLUTION PREVIEW")
    print("=" * 60)

    print()
    print("Database path :", DB_PATH)
    print("Database mode : READ-ONLY")

    if not DB_PATH.exists():
        print()
        print("🔴 DATABASE NOT FOUND")
        return

    conn = sqlite3.connect(
        f"file:{DB_PATH}?mode=ro",
        uri=True,
    )

    conn.row_factory = sqlite3.Row

    try:

        # -----------------------------------------------------
        # TABLE CHECK
        # -----------------------------------------------------

        section("DATABASE TABLES")

        required = [
            "sales",
            "products",
            "inventory_movements",
        ]

        for table in required:

            exists = conn.execute(
                """
                SELECT COUNT(*)
                FROM sqlite_master
                WHERE type = 'table'
                  AND name = ?
                """,
                (table,),
            ).fetchone()[0]

            print(
                f"{table:<24}: "
                f"{'AVAILABLE' if exists else 'MISSING'}"
            )

            if not exists:
                print()
                print("🔴 V101 CANNOT PROCEED")
                return

        # -----------------------------------------------------
        # SCHEMA DISCOVERY
        # -----------------------------------------------------

        sales_cols = columns(
            conn,
            "sales",
        )

        product_cols = columns(
            conn,
            "products",
        )

        inv_cols = columns(
            conn,
            "inventory_movements",
        )

        sale_id = choose(
            sales_cols,
            ["id", "sale_id"],
        )

        sale_product = choose(
            sales_cols,
            ["product_id"],
        )

        sale_quantity = choose(
            sales_cols,
            ["quantity", "qty"],
        )

        sale_date = choose(
            sales_cols,
            [
                "sale_date",
                "transaction_date",
                "created_at",
                "date",
            ],
        )

        sale_reference = choose(
            sales_cols,
            [
                "receipt",
                "receipt_no",
                "receipt_number",
                "reference",
                "ref",
            ],
        )

        product_id = choose(
            product_cols,
            ["id", "product_id"],
        )

        product_name = choose(
            product_cols,
            [
                "name",
                "product_name",
            ],
        )

        inv_id = choose(
            inv_cols,
            ["id", "movement_id"],
        )

        inv_product = choose(
            inv_cols,
            ["product_id"],
        )

        inv_quantity = choose(
            inv_cols,
            ["quantity", "qty"],
        )

        inv_type = choose(
            inv_cols,
            [
                "movement_type",
                "type",
            ],
        )

        inv_reference = choose(
            inv_cols,
            [
                "reference",
                "receipt",
                "receipt_no",
                "ref",
            ],
        )

        inv_date = choose(
            inv_cols,
            [
                "movement_date",
                "transaction_date",
                "created_at",
                "date",
            ],
        )

        # -----------------------------------------------------
        # SALE
        # -----------------------------------------------------

        section("V101 SALE UNDER INVESTIGATION")

        sale = conn.execute(
            f"""
            SELECT *
            FROM sales
            WHERE {sale_id} = ?
            """,
            (SALE_ID,),
        ).fetchone()

        if sale is None:
            print("🔴 Sale not found.")
            return

        actual_product = int(
            sale[sale_product]
        )

        actual_quantity = float(
            sale[sale_quantity] or 0
        )

        actual_date = str(
            sale[sale_date]
        )

        actual_reference = (
            str(
                sale[sale_reference] or ""
            ).strip()
            if sale_reference
            else ""
        )

        name = "UNKNOWN"

        if product_id and product_name:

            row = conn.execute(
                f"""
                SELECT {product_name}
                FROM products
                WHERE {product_id} = ?
                """,
                (actual_product,),
            ).fetchone()

            if row:
                name = str(row[0])

        print(
            f"Sale ID             : {SALE_ID}"
        )

        print(
            f"Product ID          : {actual_product}"
        )

        print(
            f"Product             : {name}"
        )

        print(
            f"Quantity            : {actual_quantity:.2f}"
        )

        print(
            f"Sale date           : {actual_date}"
        )

        print(
            f"Receipt/reference   : "
            f"{actual_reference or 'NONE'}"
        )

        # -----------------------------------------------------
        # EXACT MOVEMENT
        # -----------------------------------------------------

        section(
            "V101 EXISTING INVENTORY MOVEMENT"
        )

        movement = conn.execute(
            f"""
            SELECT *
            FROM inventory_movements
            WHERE {inv_product} = ?
              AND UPPER({inv_type}) = 'SALE'
              AND {inv_reference} = ?
            ORDER BY {inv_id}
            """,
            (
                PRODUCT_ID,
                REFERENCE,
            ),
        ).fetchall()

        print(
            f"Matching SALE movements : "
            f"{len(movement)}"
        )

        if len(movement) == 0:
            print(
                "🔴 No matching SALE movement found."
            )
            return

        for row in movement:

            print(
                "----------------------------------------"
            )

            print(
                f"Movement ID         : "
                f"{row[inv_id]}"
            )

            print(
                f"Movement quantity   : "
                f"{float(row[inv_quantity] or 0):.2f}"
            )

            print(
                f"Movement date       : "
                f"{row[inv_date]}"
            )

            print(
                f"Movement reference  : "
                f"{row[inv_reference]}"
            )

        if len(movement) > 1:

            print()
            print(
                "🔴 DUPLICATE REFERENCE CONDITION"
            )

            print(
                "V101 will not recommend "
                "automatic timestamp correction."
            )

            return

        existing = movement[0]

        movement_date = str(
            existing[inv_date]
        )

        movement_quantity = float(
            existing[inv_quantity] or 0
        )

        # -----------------------------------------------------
        # TIMESTAMP DIFFERENCE
        # -----------------------------------------------------

        section(
            "V101 TIMESTAMP COMPARISON"
        )

        sale_dt = parse_date(
            actual_date
        )

        movement_dt = parse_date(
            movement_date
        )

        print(
            f"Sale timestamp      : "
            f"{actual_date}"
        )

        print(
            f"Movement timestamp  : "
            f"{movement_date}"
        )

        if sale_dt and movement_dt:

            difference = (
                sale_dt - movement_dt
            )

            seconds = int(
                difference.total_seconds()
            )

            hours = seconds / 3600

            print(
                f"Timestamp difference: "
                f"{seconds} seconds"
            )

            print(
                f"Timestamp difference: "
                f"{hours:.4f} hours"
            )

            if seconds == 0:

                print(
                    "Timestamp status    : 🟢 EXACT"
                )

                timestamp_status = "EXACT"

            elif seconds > 0:

                print(
                    "Timestamp status    : 🟡 MOVEMENT EARLIER"
                )

                timestamp_status = "MOVEMENT_EARLIER"

            else:

                print(
                    "Timestamp status    : 🟡 MOVEMENT LATER"
                )

                timestamp_status = "MOVEMENT_LATER"

        else:

            print(
                "Timestamp status    : 🟡 UNPARSEABLE"
            )

            timestamp_status = "UNPARSEABLE"
            seconds = None

        # -----------------------------------------------------
        # REFERENCE / QUANTITY CHECK
        # -----------------------------------------------------

        section(
            "V101 EVIDENCE CHECK"
        )

        reference_exact = (
            actual_reference
            == REFERENCE
            == str(
                existing[inv_reference]
            )
        )

        quantity_exact = (
            abs(
                actual_quantity
                - movement_quantity
            )
            < 0.000001
        )

        product_exact = (
            actual_product
            == PRODUCT_ID
            == int(
                existing[inv_product]
            )
        )

        print(
            "Product match       : "
            f"{'PASS' if product_exact else 'FAIL'}"
        )

        print(
            "Quantity match      : "
            f"{'PASS' if quantity_exact else 'FAIL'}"
        )

        print(
            "Reference match     : "
            f"{'PASS' if reference_exact else 'FAIL'}"
        )

        # -----------------------------------------------------
        # SURROUNDING MOVEMENT HISTORY
        # -----------------------------------------------------

        section(
            "V101 SURROUNDING MOVEMENT HISTORY"
        )

        if inv_date:

            nearby = conn.execute(
                f"""
                SELECT *
                FROM inventory_movements
                WHERE {inv_product} = ?
                ORDER BY {inv_date}, {inv_id}
                """,
                (PRODUCT_ID,),
            ).fetchall()

        else:

            nearby = conn.execute(
                f"""
                SELECT *
                FROM inventory_movements
                WHERE {inv_product} = ?
                ORDER BY {inv_id}
                """,
                (PRODUCT_ID,),
            ).fetchall()

        for row in nearby:

            print(
                f"ID {row[inv_id]:<4} "
                f"{str(row[inv_type]):<10} "
                f"Qty {float(row[inv_quantity] or 0):>7.2f} "
                f"Date {str(row[inv_date]):<20} "
                f"Ref {str(row[inv_reference] or 'NONE')}"
            )

        # -----------------------------------------------------
        # DATE CORRECTION PREVIEW
        # -----------------------------------------------------

        section(
            "V101 TIMESTAMP CORRECTION PREVIEW"
        )

        if (
            product_exact
            and quantity_exact
            and reference_exact
            and timestamp_status
            != "EXACT"
        ):

            print(
                "Proposed action     : "
                "REVIEW TIMESTAMP CORRECTION"
            )

            print(
                f"Movement ID         : "
                f"{existing[inv_id]}"
            )

            print(
                f"Current timestamp   : "
                f"{movement_date}"
            )

            print(
                f"Sale timestamp      : "
                f"{actual_date}"
            )

            print()
            print(
                "Potential correction:"
            )

            print(
                f"SET movement timestamp "
                f"TO {actual_date}"
            )

            print()
            print(
                "⚠ V101 WILL NOT EXECUTE THIS."
            )

        else:

            print(
                "No timestamp correction "
                "candidate generated."
            )

        # -----------------------------------------------------
        # DECISION
        # -----------------------------------------------------

        section(
            "V101 EXECUTIVE DECISION"
        )

        if (
            product_exact
            and quantity_exact
            and reference_exact
            and timestamp_status
            != "EXACT"
        ):

            print(
                "🟡 TIMESTAMP CORRECTION CANDIDATE"
            )

            print(
                "The movement is correctly associated "
                "with the sale, but its timestamp differs."
            )

            print(
                "A separate human-confirmation phase "
                "is required before any timestamp change."
            )

        elif (
            product_exact
            and quantity_exact
            and reference_exact
            and timestamp_status == "EXACT"
        ):

            print(
                "🟢 NO TIMESTAMP REPAIR REQUIRED"
            )

        else:

            print(
                "🔴 STOP — EVIDENCE INCONSISTENCY"
            )

        # -----------------------------------------------------
        # SAFETY
        # -----------------------------------------------------

        section("V101 SAFETY STATUS")

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
            "V101 COMPLETE"
        )

    finally:

        conn.close()


if __name__ == "__main__":
    main()
