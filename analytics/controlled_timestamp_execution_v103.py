
"""
POS LEDGER NG V103
CONTROLLED TIMESTAMP CORRECTION EXECUTION

Purpose:
    Execute the single timestamp correction explicitly authorized
    by V102.

Safety:
    - Only inventory_movements row ID 4 may be changed.
    - Only its timestamp may be changed.
    - Product, quantity, type, and reference must match exactly.
    - The approved sale must still exist.
    - The operation is transactional.
    - A mismatch causes a safety stop.
    - No other table is modified.
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
MOVEMENT_ID = 4

REFERENCE = "PLN-20260814-000015"

OLD_TIMESTAMP = "2026-08-13 23:50:48"
NEW_TIMESTAMP = "2026-08-14 00:50:48"

EXPECTED_QUANTITY = 1.0
EXPECTED_TYPE = "SALE"


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


def parse_datetime(value):
    try:
        return datetime.strptime(
            str(value),
            "%Y-%m-%d %H:%M:%S",
        )
    except (TypeError, ValueError):
        return None


def main():

    print("=" * 60)
    print("POS LEDGER NG V103")
    print("CONTROLLED TIMESTAMP CORRECTION EXECUTION")
    print("=" * 60)

    print()
    print("Database path :", DB_PATH)
    print("Database mode : WRITE-ENABLED FOR ONE APPROVED CHANGE ONLY")

    if not DB_PATH.exists():
        print()
        print("🔴 DATABASE NOT FOUND")
        return

    # --------------------------------------------------
    # OPEN DATABASE
    # --------------------------------------------------

    conn = sqlite3.connect(DB_PATH)

    conn.row_factory = sqlite3.Row

    try:

        # --------------------------------------------------
        # DATABASE CHECK
        # --------------------------------------------------

        section("DATABASE SAFETY CHECK")

        required = [
            "sales",
            "products",
            "inventory_movements",
        ]

        for table in required:

            status = table_exists(
                conn,
                table,
            )

            print(
                f"{table:<24}: "
                f"{'AVAILABLE' if status else 'MISSING'}"
            )

            if not status:

                print()
                print("🔴 SAFETY STOP")
                print(
                    f"Required table missing: {table}"
                )

                conn.rollback()
                return

        # --------------------------------------------------
        # VERIFY V102 AUTHORIZATION
        # --------------------------------------------------

        section("V102 AUTHORIZATION")

        print(
            f"Authorized sale ID     : {SALE_ID}"
        )

        print(
            f"Authorized movement ID : {MOVEMENT_ID}"
        )

        print(
            f"Authorized reference   : {REFERENCE}"
        )

        print(
            f"Authorized old time    : {OLD_TIMESTAMP}"
        )

        print(
            f"Authorized new time    : {NEW_TIMESTAMP}"
        )

        print()
        print(
            "Authorization source : V102 CONFIRM"
        )

        # --------------------------------------------------
        # CHECK SALES TABLE
        # --------------------------------------------------

        section("SALE VERIFICATION")

        sale_columns = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(sales)"
            ).fetchall()
        }

        lookup = {
            c.lower(): c
            for c in sale_columns
        }

        def sale_col(names):
            for name in names:
                if name.lower() in lookup:
                    return lookup[name.lower()]
            return None

        sale_id_col = sale_col(
            ["id", "sale_id"]
        )

        product_col = sale_col(
            ["product_id"]
        )

        quantity_col = sale_col(
            ["quantity", "qty"]
        )

        date_col = sale_col(
            [
                "sale_date",
                "transaction_date",
                "created_at",
                "date",
            ]
        )

        reference_col = sale_col(
            [
                "receipt",
                "receipt_no",
                "receipt_number",
                "reference",
                "ref",
            ]
        )

        if not all(
            [
                sale_id_col,
                product_col,
                quantity_col,
                date_col,
            ]
        ):

            print(
                "🔴 Could not identify required "
                "sales columns."
            )

            conn.rollback()
            return

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
                f"🔴 Sale {SALE_ID} not found."
            )

            conn.rollback()
            return

        sale_product = int(
            sale[product_col]
        )

        sale_quantity = float(
            sale[quantity_col] or 0
        )

        sale_date = str(
            sale[date_col]
        )

        sale_reference = ""

        if reference_col:
            sale_reference = str(
                sale[reference_col] or ""
            ).strip()

        print(
            f"Sale ID          : {SALE_ID}"
        )

        print(
            f"Product ID       : {sale_product}"
        )

        print(
            f"Quantity         : {sale_quantity:.2f}"
        )

        print(
            f"Sale timestamp   : {sale_date}"
        )

        print(
            f"Sale reference   : "
            f"{sale_reference or 'NONE'}"
        )

        sale_ok = (
            sale_product == PRODUCT_ID
            and abs(
                sale_quantity
                - EXPECTED_QUANTITY
            ) < 0.000001
            and sale_reference == REFERENCE
            and sale_date == NEW_TIMESTAMP
        )

        print()
        print(
            "Sale authorization check : "
            f"{'PASS' if sale_ok else 'FAIL'}"
        )

        if not sale_ok:

            print()
            print("🔴 SAFETY STOP")
            print(
                "The sale no longer matches "
                "the V102-approved candidate."
            )

            conn.rollback()
            return

        # --------------------------------------------------
        # VERIFY INVENTORY MOVEMENT
        # --------------------------------------------------

        section("PRE-EXECUTION MOVEMENT CHECK")

        inv_columns = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(inventory_movements)"
            ).fetchall()
        }

        lookup = {
            c.lower(): c
            for c in inv_columns
        }

        def inv_col(names):
            for name in names:
                if name.lower() in lookup:
                    return lookup[name.lower()]
            return None

        inv_id_col = inv_col(
            ["id", "movement_id"]
        )

        inv_product_col = inv_col(
            ["product_id"]
        )

        inv_quantity_col = inv_col(
            ["quantity", "qty"]
        )

        inv_type_col = inv_col(
            ["movement_type", "type"]
        )

        inv_date_col = inv_col(
            [
                "movement_date",
                "transaction_date",
                "created_at",
                "date",
            ]
        )

        inv_reference_col = inv_col(
            [
                "reference",
                "receipt",
                "receipt_no",
                "ref",
            ]
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

            print(
                "🔴 Could not identify required "
                "inventory columns."
            )

            conn.rollback()
            return

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
                f"🔴 Movement {MOVEMENT_ID} not found."
            )

            conn.rollback()
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
            f"Quantity          : "
            f"{movement_quantity:.2f}"
        )

        print(
            f"Movement type     : {movement_type}"
        )

        print(
            f"Current timestamp : {movement_date}"
        )

        print(
            f"Reference         : "
            f"{movement_reference}"
        )

        # --------------------------------------------------
        # EXACT SAFETY MATCH
        # --------------------------------------------------

        section("EXACT PRE-REPAIR SAFETY CHECK")

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
            movement_type == EXPECTED_TYPE
        )

        reference_ok = (
            movement_reference == REFERENCE
        )

        old_timestamp_ok = (
            movement_date == OLD_TIMESTAMP
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
            "Old timestamp check : "
            f"{'PASS' if old_timestamp_ok else 'FAIL'}"
        )

        exact_match = all(
            [
                product_ok,
                quantity_ok,
                type_ok,
                reference_ok,
                old_timestamp_ok,
            ]
        )

        if not exact_match:

            print()
            print("🔴 SAFETY STOP")
            print(
                "The existing movement is not "
                "exactly the V102-authorized row."
            )

            print(
                "NO DATABASE CHANGE WILL BE MADE."
            )

            conn.rollback()
            return

        # --------------------------------------------------
        # TIMESTAMP VALIDATION
        # --------------------------------------------------

        section("TIMESTAMP VALIDATION")

        old_dt = parse_datetime(
            OLD_TIMESTAMP
        )

        new_dt = parse_datetime(
            NEW_TIMESTAMP
        )

        if old_dt is None or new_dt is None:

            print(
                "🔴 Invalid timestamp format."
            )

            conn.rollback()
            return

        difference = (
            new_dt - old_dt
        ).total_seconds()

        print(
            f"Current timestamp : "
            f"{OLD_TIMESTAMP}"
        )

        print(
            f"New timestamp     : "
            f"{NEW_TIMESTAMP}"
        )

        print(
            f"Difference        : "
            f"{difference:.0f} seconds"
        )

        if difference != 3600:

            print()
            print(
                "🔴 SAFETY STOP"
            )

            print(
                "Expected correction is "
                "exactly one hour."
            )

            conn.rollback()
            return

        # --------------------------------------------------
        # FINAL WARNING
        # --------------------------------------------------

        section("V103 FINAL EXECUTION")

        print(
            "AUTHORIZED CHANGE:"
        )

        print(
            f"inventory_movements.{inv_date_col}"
        )

        print(
            f"Movement ID {MOVEMENT_ID}"
        )

        print(
            f"{OLD_TIMESTAMP}"
        )

        print(
            "        ↓"
        )

        print(
            f"{NEW_TIMESTAMP}"
        )

        print()
        print(
            "Only this timestamp will be changed."
        )

        print(
            "No INSERT operation."
        )

        print(
            "No DELETE operation."
        )

        print(
            "No sales UPDATE."
        )

        print(
            "No product UPDATE."
        )

        print(
            "No purchase UPDATE."
        )

        print(
            "No balance UPDATE."
        )

        print()

        # --------------------------------------------------
        # EXECUTE SINGLE UPDATE
        # --------------------------------------------------

        conn.execute("BEGIN")

        cursor = conn.execute(
            f"""
            UPDATE inventory_movements
            SET {inv_date_col} = ?
            WHERE {inv_id_col} = ?
              AND {inv_product_col} = ?
              AND {inv_quantity_col} = ?
              AND UPPER({inv_type_col}) = ?
              AND {inv_reference_col} = ?
              AND {inv_date_col} = ?
            """,
            (
                NEW_TIMESTAMP,
                MOVEMENT_ID,
                PRODUCT_ID,
                EXPECTED_QUANTITY,
                EXPECTED_TYPE,
                REFERENCE,
                OLD_TIMESTAMP,
            ),
        )

        affected = cursor.rowcount

        print(
            f"Rows targeted : {affected}"
        )

        if affected != 1:

            print()
            print(
                "🔴 EXECUTION SAFETY STOP"
            )

            print(
                "Exactly one row was expected."
            )

            print(
                "Rolling back transaction."
            )

            conn.rollback()
            return

        # --------------------------------------------------
        # VERIFY BEFORE COMMIT
        # --------------------------------------------------

        section("POST-UPDATE VERIFICATION")

        updated = conn.execute(
            f"""
            SELECT *
            FROM inventory_movements
            WHERE {inv_id_col} = ?
            """,
            (MOVEMENT_ID,),
        ).fetchone()

        if updated is None:

            print(
                "🔴 Verification failed: "
                "movement disappeared."
            )

            conn.rollback()
            return

        updated_product = int(
            updated[inv_product_col]
        )

        updated_quantity = float(
            updated[inv_quantity_col] or 0
        )

        updated_type = str(
            updated[inv_type_col] or ""
        ).strip().upper()

        updated_date = str(
            updated[inv_date_col]
        )

        updated_reference = str(
            updated[inv_reference_col] or ""
        ).strip()

        verification_ok = all(
            [
                updated_product == PRODUCT_ID,
                abs(
                    updated_quantity
                    - EXPECTED_QUANTITY
                ) < 0.000001,
                updated_type == EXPECTED_TYPE,
                updated_date == NEW_TIMESTAMP,
                updated_reference == REFERENCE,
            ]
        )

        print(
            f"Product ID        : "
            f"{updated_product}"
        )

        print(
            f"Quantity          : "
            f"{updated_quantity:.2f}"
        )

        print(
            f"Movement type     : "
            f"{updated_type}"
        )

        print(
            f"Timestamp         : "
            f"{updated_date}"
        )

        print(
            f"Reference         : "
            f"{updated_reference}"
        )

        print()

        print(
            "Verification      : "
            f"{'PASS' if verification_ok else 'FAIL'}"
        )

        if not verification_ok:

            print()
            print(
                "🔴 VERIFICATION FAILED"
            )

            print(
                "Rolling back the transaction."
            )

            conn.rollback()
            return

        # --------------------------------------------------
        # COMMIT
        # --------------------------------------------------

        conn.commit()

        # --------------------------------------------------
        # FINAL RESULT
        # --------------------------------------------------

        section("V103 EXECUTION RESULT")

        print(
            "🟢 TIMESTAMP CORRECTION EXECUTED"
        )

        print(
            f"Movement ID       : {MOVEMENT_ID}"
        )

        print(
            f"Old timestamp     : {OLD_TIMESTAMP}"
        )

        print(
            f"New timestamp     : {NEW_TIMESTAMP}"
        )

        print(
            f"Reference         : {REFERENCE}"
        )

        print()
        print(
            "Database write     : 1 UPDATE"
        )

        print(
            "INSERT operations  : 0"
        )

        print(
            "DELETE operations  : 0"
        )

        print(
            "Other tables       : NOT MODIFIED"
        )

        # --------------------------------------------------
        # SAFETY STATUS
        # --------------------------------------------------

        section("V103 SAFETY STATUS")

        print(
            "Mode                  : CONTROLLED WRITE"
        )

        print(
            "Database modified     : YES"
        )

        print(
            "Inventory modified    : YES — TIMESTAMP ONLY"
        )

        print(
            "Sales modified        : NO"
        )

        print(
            "Products modified     : NO"
        )

        print(
            "Purchases modified    : NO"
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
            "V103 COMPLETE"
        )

    except Exception as exc:

        print()
        print("=" * 60)
        print("🔴 V103 EXCEPTION")
        print("=" * 60)

        print(
            f"{type(exc).__name__}: {exc}"
        )

        try:
            conn.rollback()
        except Exception:
            pass

        print()
        print(
            "Transaction rolled back."
        )

    finally:

        conn.close()


if __name__ == "__main__":
    main()
