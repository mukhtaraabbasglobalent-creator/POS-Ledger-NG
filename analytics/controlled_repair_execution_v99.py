"""
POS LEDGER NG V99
CONTROLLED REPAIR EXECUTION

IMPORTANT:
- This is the first module in the repair sequence that may modify the DB.
- Creates a backup before any write.
- Uses a transaction and rollback on failure.
- Has a duplicate-protection preflight.
- NEVER changes the original sales record.
"""

from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path


BASE_DIR = Path.home() / "POS-Ledger-NG"
DB_PATH = BASE_DIR / "data" / "posledger.db"
BACKUP_DIR = BASE_DIR / "data" / "backups"

APPROVED_SALE_ID = 15
APPROVED_PRODUCT_ID = 1
APPROVED_QUANTITY = 1.0
APPROVED_REFERENCE = "PLN-20260814-000015"
APPROVED_DATE = "2026-08-14 00:50:48"


def money(value):
    return f"₦{float(value or 0):,.2f}"


def backup_database():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = (
        BACKUP_DIR
        / f"posledger_v99_backup_{stamp}.db"
    )

    shutil.copy2(DB_PATH, backup_path)
    return backup_path


def get_columns(conn, table):
    return {
        row[1]
        for row in conn.execute(
            f'PRAGMA table_info("{table}")'
        ).fetchall()
    }


def find_column(columns, candidates):
    lowered = {
        c.casefold(): c
        for c in columns
    }

    for candidate in candidates:
        if candidate.casefold() in lowered:
            return lowered[candidate.casefold()]

    return None


def main():
    print("=" * 60)
    print("POS LEDGER NG V99")
    print("CONTROLLED REPAIR EXECUTION")
    print("=" * 60)

    if not DB_PATH.exists():
        print("DATABASE NOT FOUND")
        return

    print()
    print("=" * 60)
    print("APPROVED REPAIR")
    print("=" * 60)
    print(f"Sale ID          : {APPROVED_SALE_ID}")
    print(f"Product ID       : {APPROVED_PRODUCT_ID}")
    print(f"Quantity         : {APPROVED_QUANTITY:.2f}")
    print(f"Reference        : {APPROVED_REFERENCE}")
    print(f"Transaction date : {APPROVED_DATE}")

    print()
    print("=" * 60)
    print("PRE-REPAIR SAFETY CHECK")
    print("=" * 60)

    # Open temporarily read-only for preflight.
    ro_uri = f"file:{DB_PATH}?mode=ro"

    ro = sqlite3.connect(ro_uri, uri=True)
    ro.row_factory = sqlite3.Row

    try:
        sales_cols = get_columns(ro, "sales")
        inv_cols = get_columns(ro, "inventory_movements")

        if not sales_cols or not inv_cols:
            print("Required tables/columns not available.")
            return

        # Verify approved sale still exists.
        sale_row = ro.execute(
            """
            SELECT *
            FROM sales
            WHERE id = ?
            """,
            (APPROVED_SALE_ID,),
        ).fetchone()

        if not sale_row:
            print("🔴 APPROVED SALE NO LONGER EXISTS")
            return

        sale_product_col = find_column(
            sales_cols,
            ["product_id"],
        )
        sale_qty_col = find_column(
            sales_cols,
            ["quantity", "qty"],
        )
        sale_status_col = find_column(
            sales_cols,
            ["status"],
        )

        if sale_product_col is None or sale_qty_col is None:
            print("🔴 SALE SCHEMA INSUFFICIENT")
            return

        actual_product = int(
            sale_row[sale_product_col]
        )

        actual_quantity = float(
            sale_row[sale_qty_col]
            or 0
        )

        if actual_product != APPROVED_PRODUCT_ID:
            print("🔴 PRODUCT ID CHANGED")
            print(
                f"Expected: {APPROVED_PRODUCT_ID}"
            )
            print(
                f"Actual  : {actual_product}"
            )
            return

        if abs(
            actual_quantity
            - APPROVED_QUANTITY
        ) > 0.000001:
            print("🔴 SALE QUANTITY CHANGED")
            print(
                f"Expected: {APPROVED_QUANTITY}"
            )
            print(
                f"Actual  : {actual_quantity}"
            )
            return

        if sale_status_col:
            status = str(
                sale_row[sale_status_col]
                or ""
            ).upper()

            if status not in {
                "",
                "COMPLETED",
                "COMPLETE",
                "PAID",
                "SUCCESS",
            }:
                print("🔴 SALE IS NOT COMPLETED")
                print(f"Status: {status}")
                return

        movement_product_col = find_column(
            inv_cols,
            ["product_id"],
        )
        movement_qty_col = find_column(
            inv_cols,
            ["quantity", "qty"],
        )
        movement_type_col = find_column(
            inv_cols,
            ["movement_type", "type"],
        )
        movement_ref_col = find_column(
            inv_cols,
            [
                "reference",
                "receipt_no",
                "receipt",
                "ref",
            ],
        )
        movement_date_col = find_column(
            inv_cols,
            [
                "movement_date",
                "created_at",
                "date",
            ],
        )

        if (
            movement_product_col is None
            or movement_qty_col is None
            or movement_type_col is None
        ):
            print("🔴 INVENTORY SCHEMA INSUFFICIENT")
            return

        # Duplicate-protection / existing-match search.
        params = [
            APPROVED_PRODUCT_ID,
            APPROVED_QUANTITY,
        ]

        existing_sql = f"""
            SELECT *
            FROM inventory_movements
            WHERE {movement_product_col} = ?
              AND ABS({movement_qty_col} - ?) < 0.000001
              AND UPPER({movement_type_col}) = 'SALE'
        """

        existing_rows = ro.execute(
            existing_sql,
            params,
        ).fetchall()

        matching_reference = []

        for row in existing_rows:
            if movement_ref_col:
                ref = str(
                    row[movement_ref_col]
                    or ""
                ).strip()

                if ref == APPROVED_REFERENCE:
                    matching_reference.append(row)

        print(
            f"Existing matching SALE movements : "
            f"{len(existing_rows)}"
        )

        print(
            f"Matching approved reference       : "
            f"{len(matching_reference)}"
        )

        if matching_reference:
            print()
            print(
                "🟡 NO-OP SAFETY STOP"
            )
            print(
                "The approved inventory movement "
                "already exists."
            )

            for row in matching_reference:
                print()
                print(
                    f"Existing movement ID : "
                    f"{row['id']}"
                )

                if movement_date_col:
                    print(
                        f"Existing movement date : "
                        f"{row[movement_date_col]}"
                    )

                if movement_ref_col:
                    print(
                        f"Existing reference     : "
                        f"{row[movement_ref_col]}"
                    )

            print()
            print(
                "V99 WILL NOT INSERT A DUPLICATE."
            )
            print(
                "A separate date-correction review "
                "would be required if the timestamp "
                "itself is believed to be wrong."
            )
            return

        print(
            "Preflight status : 🟢 SAFE TO PROCEED"
        )

    finally:
        ro.close()

    # ---------------------------------------------------------
    # BACKUP
    # ---------------------------------------------------------

    print()
    print("=" * 60)
    print("DATABASE BACKUP")
    print("=" * 60)

    backup_path = backup_database()

    print(
        f"Backup created : {backup_path}"
    )

    # ---------------------------------------------------------
    # CONTROLLED WRITE
    # ---------------------------------------------------------

    conn = sqlite3.connect(DB_PATH)

    try:
        conn.row_factory = sqlite3.Row

        inv_cols = get_columns(
            conn,
            "inventory_movements",
        )

        movement_type_col = find_column(
            inv_cols,
            ["movement_type", "type"],
        )
        movement_product_col = find_column(
            inv_cols,
            ["product_id"],
        )
        movement_qty_col = find_column(
            inv_cols,
            ["quantity", "qty"],
        )
        movement_ref_col = find_column(
            inv_cols,
            [
                "reference",
                "receipt_no",
                "receipt",
                "ref",
            ],
        )
        movement_date_col = find_column(
            inv_cols,
            [
                "movement_date",
                "created_at",
                "date",
            ],
        )
        movement_remarks_col = find_column(
            inv_cols,
            [
                "remarks",
                "description",
                "note",
            ],
        )

        required = [
            movement_type_col,
            movement_product_col,
            movement_qty_col,
        ]

        if any(x is None for x in required):
            raise RuntimeError(
                "Required inventory movement columns missing."
            )

        # Re-check immediately inside the write transaction.
        existing_sql = f"""
            SELECT *
            FROM inventory_movements
            WHERE {movement_product_col} = ?
              AND ABS({movement_qty_col} - ?) < 0.000001
              AND UPPER({movement_type_col}) = 'SALE'
        """

        duplicate_rows = conn.execute(
            existing_sql,
            (
                APPROVED_PRODUCT_ID,
                APPROVED_QUANTITY,
            ),
        ).fetchall()

        if duplicate_rows:
            print()
            print(
                "🟡 REPAIR CANCELLED"
            )
            print(
                "A matching SALE movement appeared "
                "before execution."
            )
            conn.rollback()
            return

        fields = [
            movement_product_col,
            movement_type_col,
            movement_qty_col,
        ]

        values = [
            APPROVED_PRODUCT_ID,
            "SALE",
            APPROVED_QUANTITY,
        ]

        if movement_ref_col:
            fields.append(movement_ref_col)
            values.append(APPROVED_REFERENCE)

        if movement_date_col:
            fields.append(movement_date_col)
            values.append(APPROVED_DATE)

        if movement_remarks_col:
            fields.append(movement_remarks_col)
            values.append(
                "V99 controlled repair; V98 human-confirmed"
            )

        placeholders = ", ".join(
            ["?"] * len(values)
        )

        sql = (
            f'INSERT INTO inventory_movements '
            f'({", ".join(fields)}) '
            f'VALUES ({placeholders})'
        )

        print()
        print("=" * 60)
        print("EXECUTING CONTROLLED REPAIR")
        print("=" * 60)

        cursor = conn.execute(
            sql,
            values,
        )

        new_movement_id = cursor.lastrowid

        conn.commit()

        print(
            "🟢 REPAIR EXECUTED"
        )

        print(
            f"New movement ID : "
            f"{new_movement_id}"
        )

    except Exception as exc:
        conn.rollback()

        print()
        print(
            "🔴 REPAIR FAILED — ROLLBACK COMPLETE"
        )
        print(
            f"Reason : {exc}"
        )
        print(
            f"Backup : {backup_path}"
        )

        return

    finally:
        conn.close()

    # ---------------------------------------------------------
    # POST-REPAIR VERIFICATION
    # ---------------------------------------------------------

    print()
    print("=" * 60)
    print("POST-REPAIR VERIFICATION")
    print("=" * 60)

    verify = sqlite3.connect(
        f"file:{DB_PATH}?mode=ro",
        uri=True,
    )
    verify.row_factory = sqlite3.Row

    try:
        inv_cols = get_columns(
            verify,
            "inventory_movements",
        )

        product_col = find_column(
            inv_cols,
            ["product_id"],
        )

        qty_col = find_column(
            inv_cols,
            ["quantity", "qty"],
        )

        type_col = find_column(
            inv_cols,
            ["movement_type", "type"],
        )

        ref_col = find_column(
            inv_cols,
            [
                "reference",
                "receipt_no",
                "receipt",
                "ref",
            ],
        )

        sql = f"""
            SELECT *
            FROM inventory_movements
            WHERE {product_col} = ?
              AND ABS({qty_col} - ?) < 0.000001
              AND UPPER({type_col}) = 'SALE'
        """

        rows = verify.execute(
            sql,
            (
                APPROVED_PRODUCT_ID,
                APPROVED_QUANTITY,
            ),
        ).fetchall()

        matching = []

        for row in rows:

            if ref_col:
                reference = str(
                    row[ref_col] or ""
                ).strip()

                if reference == APPROVED_REFERENCE:
                    matching.append(row)

        print(
            f"Verified matching SALE movements : "
            f"{len(matching)}"
        )

        if len(matching) == 1:
            print(
                "Post-repair status : 🟢 VERIFIED"
            )
        elif len(matching) == 0:
            print(
                "Post-repair status : 🔴 NOT FOUND"
            )
        else:
            print(
                "Post-repair status : 🔴 DUPLICATE DETECTED"
            )

    finally:
        verify.close()

    # ---------------------------------------------------------
    # SAFETY STATUS
    # ---------------------------------------------------------

    print()
    print("=" * 60)
    print("V99 SAFETY STATUS")
    print("=" * 60)

    print("Mode                  : CONTROLLED WRITE")
    print("Database modified     : YES")
    print("Sales modified        : NO")
    print("Inventory modified    : YES")
    print("Purchases modified    : NO")
    print("Products modified     : NO")
    print("Balance modified      : NO")
    print("Credit modified       : NO")
    print("Suppliers modified    : NO")
    print("Expenses modified     : NO")
    print(
        "Backup created        : "
        f"{backup_path}"
    )

    print()
    print("=" * 60)
    print("V99 EXECUTIVE DECISION")
    print("=" * 60)

    print(
        "🟡 CONTROLLED REPAIR COMPLETE — "
        "RUN V100 POST-REPAIR INTEGRITY AUDIT"
    )


if __name__ == "__main__":
    main()
