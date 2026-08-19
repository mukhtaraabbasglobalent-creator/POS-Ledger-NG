"""
POS LEDGER NG V97
TRANSACTION ↔ INVENTORY REPAIR PREVIEW

READ-ONLY PREVIEW ONLY.
This module does NOT modify the database.

It consumes the authorization logic from the existing database state and
produces a deterministic preview of repairs that would be allowed only when
there is strong evidence.

V97 is intentionally conservative:
- no INSERT
- no UPDATE
- no DELETE
- no COMMIT
- no automatic repair
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


DB_PATH = "/data/data/com.termux/files/home/POS-Ledger-NG/data/posledger.db"


@dataclass
class RepairCandidate:
    sale_id: int
    product_id: int
    product_name: str
    quantity: float
    sale_date: str
    receipt: str
    movement_id: int
    movement_quantity: float
    movement_date: str
    movement_reference: str


def money_or_number(value) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return str(value)


def normalize(value) -> str:
    return str(value or "").strip().casefold()


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        """,
        (table_name,),
    ).fetchone()
    return row is not None


def get_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    return {
        row[1]
        for row in conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()
    }


def find_column(
    columns: set[str],
    candidates: list[str],
) -> Optional[str]:
    lowered = {c.casefold(): c for c in columns}

    for candidate in candidates:
        if candidate.casefold() in lowered:
            return lowered[candidate.casefold()]

    for column in columns:
        lc = column.casefold()
        for candidate in candidates:
            if candidate.casefold() in lc:
                return column

    return None


def safe_select(
    conn: sqlite3.Connection,
    table_name: str,
    aliases: dict[str, list[str]],
) -> list[sqlite3.Row]:
    columns = get_columns(conn, table_name)

    selected = []

    for alias, candidates in aliases.items():
        column = find_column(columns, candidates)

        if column:
            selected.append(
                f'"{column}" AS "{alias}"'
            )
        else:
            selected.append(
                f'NULL AS "{alias}"'
            )

    sql = f'''
        SELECT {", ".join(selected)}
        FROM "{table_name}"
    '''

    return conn.execute(sql).fetchall()


def get_verified_candidate(
    conn: sqlite3.Connection,
) -> Optional[RepairCandidate]:

    if not table_exists(conn, "sales"):
        return None

    if not table_exists(conn, "inventory_movements"):
        return None

    sales = safe_select(
        conn,
        "sales",
        {
            "id": ["id", "sale_id", "transaction_id"],
            "product_id": ["product_id", "product"],
            "product_name": ["product_name", "name", "description"],
            "quantity": ["quantity", "qty", "units"],
            "sale_date": [
                "sale_date",
                "transaction_date",
                "created_at",
                "date",
            ],
            "receipt": [
                "receipt",
                "receipt_no",
                "receipt_number",
                "reference",
                "sale_reference",
            ],
        },
    )

    movements = safe_select(
        conn,
        "inventory_movements",
        {
            "id": ["id", "movement_id"],
            "product_id": ["product_id", "product"],
            "quantity": ["quantity", "qty", "units"],
            "movement_type": [
                "movement_type",
                "type",
                "transaction_type",
            ],
            "movement_date": [
                "movement_date",
                "transaction_date",
                "created_at",
                "date",
            ],
            "reference": [
                "reference",
                "ref",
                "document_reference",
                "receipt",
                "receipt_no",
            ],
        },
    )

    # Only inspect SALE movements.
    sale_movements = [
        row
        for row in movements
        if normalize(row["movement_type"]) == "sale"
    ]

    # Find candidates using the strongest evidence available:
    # exact receipt/reference + product + quantity.
    candidates: list[RepairCandidate] = []

    for sale in sales:
        receipt = str(sale["receipt"] or "").strip()

        if not receipt:
            continue

        if sale["product_id"] is None:
            continue

        try:
            sale_qty = float(sale["quantity"])
        except (TypeError, ValueError):
            continue

        for movement in sale_movements:
            if movement["product_id"] is None:
                continue

            if int(movement["product_id"]) != int(sale["product_id"]):
                continue

            try:
                movement_qty = float(movement["quantity"])
            except (TypeError, ValueError):
                continue

            if abs(sale_qty - movement_qty) > 0.000001:
                continue

            movement_reference = str(
                movement["reference"] or ""
            ).strip()

            if not movement_reference:
                continue

            if movement_reference != receipt:
                continue

            candidates.append(
                RepairCandidate(
                    sale_id=int(sale["id"]),
                    product_id=int(sale["product_id"]),
                    product_name=str(
                        sale["product_name"] or "UNKNOWN"
                    ),
                    quantity=sale_qty,
                    sale_date=str(
                        sale["sale_date"] or ""
                    ),
                    receipt=receipt,
                    movement_id=int(movement["id"]),
                    movement_quantity=movement_qty,
                    movement_date=str(
                        movement["movement_date"] or ""
                    ),
                    movement_reference=movement_reference,
                )
            )

    # A repair candidate must be unique.
    if len(candidates) != 1:
        return None

    return candidates[0]


def print_header(title: str) -> None:
    print("=" * 60)
    print(title)
    print("=" * 60)


def main() -> None:
    print_header(
        "POS LEDGER NG V97"
    )
    print(
        "TRANSACTION ↔ INVENTORY REPAIR PREVIEW"
    )

    print()
    print_header("DATABASE")

    print(f"Database path : {DB_PATH}")
    print("Database mode : READ-ONLY")
    print()

    if not os.path.exists(DB_PATH):
        print("🔴 DATABASE NOT FOUND")
        return

    # SQLite URI explicitly opens the database read-only.
    uri = f"file:{DB_PATH}?mode=ro"

    try:
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row
    except sqlite3.Error as exc:
        print("🔴 DATABASE OPEN FAILED")
        print(f"Reason : {exc}")
        return

    try:
        required_tables = [
            "sales",
            "products",
            "inventory_movements",
            "purchases",
        ]

        print("Required tables:")

        missing = []

        for table in required_tables:
            available = table_exists(conn, table)

            print(
                f"{table:<22}: "
                f"{'AVAILABLE' if available else 'MISSING'}"
            )

            if not available:
                missing.append(table)

        if missing:
            print()
            print("🔴 V97 CANNOT RUN")
            print(
                "Missing required tables: "
                + ", ".join(missing)
            )
            return

        print()
        print_header(
            "V97 VERIFIED REPAIR CANDIDATE SEARCH"
        )

        candidate = get_verified_candidate(conn)

        if candidate is None:
            print(
                "Verified repair candidates : 0"
            )
            print()
            print(
                "🟡 NO REPAIR PREVIEW GENERATED"
            )
            print(
                "No unique strong-evidence candidate "
                "was found."
            )

            print()
            print_header("V97 SAFETY STATUS")

            print("Mode                  : READ-ONLY")
            print("Database modified     : NO")
            print("Sales modified        : NO")
            print("Inventory modified    : NO")
            print("Purchases modified    : NO")
            print("Products modified     : NO")
            print("Balance modified      : NO")
            print("Credit modified       : NO")
            print("Suppliers modified    : NO")
            print("Expenses modified     : NO")

            return

        print(
            "Verified repair candidates : 1"
        )

        print()
        print_header(
            "V97 REPAIR PREVIEW"
        )

        print("----------------------------------------")
        print(
            f"Sale ID             : {candidate.sale_id}"
        )
        print(
            f"Product ID          : {candidate.product_id}"
        )
        print(
            f"Product             : {candidate.product_name}"
        )
        print(
            f"Quantity            : "
            f"{money_or_number(candidate.quantity)}"
        )
        print(
            f"Sale date           : {candidate.sale_date}"
        )
        print(
            f"Receipt             : {candidate.receipt}"
        )

        print()
        print("PROPOSED INVENTORY ACTION")
        print(
            "Action              : CREATE SALE MOVEMENT"
        )
        print(
            f"Product ID          : {candidate.product_id}"
        )
        print(
            f"Quantity            : "
            f"-{money_or_number(candidate.quantity)}"
        )
        print(
            f"Reference           : {candidate.receipt}"
        )
        print(
            f"Transaction date    : {candidate.sale_date}"
        )

        print()
        print("EVIDENCE BASIS")
        print(
            f"Existing movement   : "
            f"{candidate.movement_id}"
        )
        print(
            f"Movement quantity   : "
            f"{money_or_number(candidate.movement_quantity)}"
        )
        print(
            f"Movement date       : "
            f"{candidate.movement_date}"
        )
        print(
            f"Movement reference  : "
            f"{candidate.movement_reference}"
        )

        print()
        print(
            "Evidence strength   : STRONG"
        )
        print(
            "Preview status      : VERIFIED"
        )

        print()
        print_header(
            "V97 IMPORTANT SAFETY CHECK"
        )

        print(
            "The preview above is NOT an executed repair."
        )
        print(
            "No inventory movement was created."
        )
        print(
            "No existing inventory movement was changed."
        )
        print(
            "No sale was changed."
        )
        print(
            "No purchase was changed."
        )

        print()
        print_header(
            "V97 EXECUTIVE DECISION"
        )

        print(
            "🟡 REPAIR PREVIEW READY"
        )
        print()
        print(
            "One explicitly verified candidate is "
            "available for the next human-confirmation phase."
        )
        print()
        print(
            "NEXT PHASE : V98 HUMAN CONFIRMATION"
        )

        print()
        print_header(
            "V97 SAFETY STATUS"
        )

        print("Mode                  : READ-ONLY")
        print("Database modified     : NO")
        print("Sales modified        : NO")
        print("Inventory modified    : NO")
        print("Purchases modified    : NO")
        print("Products modified     : NO")
        print("Balance modified      : NO")
        print("Credit modified       : NO")
        print("Suppliers modified    : NO")
        print("Expenses modified     : NO")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
