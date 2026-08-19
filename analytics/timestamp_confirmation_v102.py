"""
POS LEDGER NG V102
HUMAN TIMESTAMP CORRECTION CONFIRMATION

READ-ONLY

V102 does NOT modify the database.

It reviews the timestamp correction candidate identified by V101
and records the human decision in memory/output only.

Allowed decisions:
    CONFIRM
    REJECT
    DEFER
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
PRODUCT_ID = 1
MOVEMENT_ID = 4
REFERENCE = "PLN-20260814-000015"

EXPECTED_SALE_DATE = "2026-08-14 00:50:48"
CURRENT_MOVEMENT_DATE = "2026-08-13 23:50:48"


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


def main():

    print("=" * 60)
    print("POS LEDGER NG V102")
    print("HUMAN TIMESTAMP CORRECTION CONFIRMATION")
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

        # --------------------------------------------------
        # DATABASE CHECK
        # --------------------------------------------------

        section("DATABASE")

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
                print("🔴 V102 CANNOT PROCEED")
                return

        # --------------------------------------------------
        # VERIFY SALE
        # --------------------------------------------------

        section("V102 APPROVED TIMESTAMP CANDIDATE")

        sale_columns = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(sales)"
            ).fetchall()
        }

        def choose(names):
            lookup = {
                c.lower(): c
                for c in sale_columns
            }

            for name in names:
                if name.lower() in lookup:
                    return lookup[name.lower()]

            return None

        sale_id_col = choose(
            ["id", "sale_id"]
        )

        product_col = choose(
            ["product_id"]
        )

        quantity_col = choose(
            ["quantity", "qty"]
        )

        date_col = choose(
            [
                "sale_date",
                "transaction_date",
                "created_at",
                "date",
            ]
        )

        reference_col = choose(
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
                "🔴 Required sales columns "
                "could not be identified."
            )

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
            f"Sale ID             : {SALE_ID}"
        )

        print(
            f"Product ID          : {sale_product}"
        )

        print(
            f"Quantity            : "
            f"{sale_quantity:.2f}"
        )

        print(
            f"Sale timestamp      : "
            f"{sale_date}"
        )

        print(
            f"Sale reference      : "
            f"{sale_reference or 'NONE'}"
        )

        # --------------------------------------------------
        # VERIFY MOVEMENT
        # --------------------------------------------------

        section("EXISTING INVENTORY MOVEMENT")

        inv_columns = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(inventory_movements)"
            ).fetchall()
        }

        def choose_inv(names):
            lookup = {
                c.lower(): c
                for c in inv_columns
            }

            for name in names:
                if name.lower() in lookup:
                    return lookup[name.lower()]

            return None

        inv_id_col = choose_inv(
            ["id", "movement_id"]
        )

        inv_product_col = choose_inv(
            ["product_id"]
        )

        inv_quantity_col = choose_inv(
            ["quantity", "qty"]
        )

        inv_type_col = choose_inv(
            [
                "movement_type",
                "type",
            ]
        )

        inv_date_col = choose_inv(
            [
                "movement_date",
                "transaction_date",
                "created_at",
                "date",
            ]
        )

        inv_reference_col = choose_inv(
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
                "🔴 Required inventory columns "
                "could not be identified."
            )

            return

        movement = conn.execute(
            f"""
            SELECT *
            FROM inventory_movements
            WHERE {inv_id_col} = ?
              AND {inv_product_col} = ?
              AND UPPER({inv_type_col}) = 'SALE'
              AND {inv_reference_col} = ?
            """,
            (
                MOVEMENT_ID,
                PRODUCT_ID,
                REFERENCE,
            ),
        ).fetchone()

        if movement is None:

            print(
                "🔴 Approved movement candidate "
                "could not be verified."
            )

            return

        movement_quantity = float(
            movement[inv_quantity_col] or 0
        )

        movement_date = str(
            movement[inv_date_col]
        )

        movement_reference = str(
            movement[inv_reference_col] or ""
        ).strip()

        print(
            f"Movement ID         : "
            f"{MOVEMENT_ID}"
        )

        print(
            f"Product ID          : "
            f"{movement[inv_product_col]}"
        )

        print(
            f"Movement quantity   : "
            f"{movement_quantity:.2f}"
        )

        print(
            f"Movement timestamp  : "
            f"{movement_date}"
        )

        print(
            f"Movement reference  : "
            f"{movement_reference}"
        )

        # --------------------------------------------------
        # SAFETY VALIDATION
        # --------------------------------------------------

        section("V102 SAFETY VALIDATION")

        product_ok = (
            sale_product == PRODUCT_ID
            and int(movement[inv_product_col])
            == PRODUCT_ID
        )

        quantity_ok = (
            abs(
                sale_quantity
                - movement_quantity
            )
            < 0.000001
        )

        reference_ok = (
            sale_reference == REFERENCE
            and movement_reference == REFERENCE
        )

        timestamp_difference = (
            sale_date != movement_date
        )

        print(
            "Product match       : "
            f"{'PASS' if product_ok else 'FAIL'}"
        )

        print(
            "Quantity match      : "
            f"{'PASS' if quantity_ok else 'FAIL'}"
        )

        print(
            "Reference match     : "
            f"{'PASS' if reference_ok else 'FAIL'}"
        )

        print(
            "Timestamp differs   : "
            f"{'YES' if timestamp_difference else 'NO'}"
        )

        if not (
            product_ok
            and quantity_ok
            and reference_ok
            and timestamp_difference
        ):

            print()
            print(
                "🔴 V102 SAFETY STOP"
            )

            print(
                "The timestamp correction candidate "
                "is no longer valid."
            )

            return

        # --------------------------------------------------
        # PROPOSED CORRECTION
        # --------------------------------------------------

        section("PROPOSED V103 ACTION")

        print(
            "Action              : "
            "UPDATE SALE MOVEMENT TIMESTAMP"
        )

        print(
            f"Movement ID         : "
            f"{MOVEMENT_ID}"
        )

        print(
            f"Current timestamp   : "
            f"{movement_date}"
        )

        print(
            f"Proposed timestamp  : "
            f"{sale_date}"
        )

        print(
            f"Reference           : "
            f"{REFERENCE}"
        )

        print()
        print(
            "⚠ V102 WILL NOT EXECUTE THIS ACTION."
        )

        print(
            "The database remains READ-ONLY."
        )

        # --------------------------------------------------
        # HUMAN DECISION
        # --------------------------------------------------

        section("V102 HUMAN CONFIRMATION")

        print(
            "Review the timestamp discrepancy carefully."
        )

        print()
        print(
            "Type one of:"
        )

        print(
            "  CONFIRM  - authorize timestamp correction for V103"
        )

        print(
            "  REJECT   - reject the timestamp correction"
        )

        print(
            "  DEFER    - leave the issue unresolved"
        )

        print()

        while True:

            try:
                decision = input(
                    "V102 decision > "
                ).strip().upper()

            except (EOFError, KeyboardInterrupt):

                print()
                print(
                    "DEFER"
                )

                decision = "DEFER"
                break

            if decision in {
                "CONFIRM",
                "REJECT",
                "DEFER",
            }:
                break

            print(
                "Invalid decision. "
                "Enter CONFIRM, REJECT, or DEFER."
            )

        # --------------------------------------------------
        # RESULT
        # --------------------------------------------------

        section("V102 AUTHORIZATION RESULT")

        if decision == "CONFIRM":

            print(
                "🟢 HUMAN DECISION : CONFIRM"
            )

            print(
                "Timestamp correction : APPROVED"
            )

            print(
                "Candidate status     : "
                "AUTHORIZED_FOR_V103"
            )

            print()
            print(
                "V103 may perform the "
                "controlled timestamp correction."
            )

        elif decision == "REJECT":

            print(
                "🔴 HUMAN DECISION : REJECT"
            )

            print(
                "Timestamp correction : REJECTED"
            )

            print(
                "Candidate status     : "
                "REJECTED"
            )

            print()
            print(
                "V103 MUST NOT modify this timestamp."
            )

        else:

            print(
                "🟡 HUMAN DECISION : DEFER"
            )

            print(
                "Timestamp correction : DEFERRED"
            )

            print(
                "Candidate status     : "
                "DEFERRED"
            )

            print()
            print(
                "No timestamp correction is authorized."
            )

        # --------------------------------------------------
        # IMPORTANT SAFETY NOTE
        # --------------------------------------------------

        section("V102 SAFETY STATUS")

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
            "V102 COMPLETE"
        )

    finally:
        conn.close()


if __name__ == "__main__":
    main()
