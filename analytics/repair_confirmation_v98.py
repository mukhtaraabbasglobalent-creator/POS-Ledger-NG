"""
POS LEDGER NG V98
HUMAN CONFIRMATION & REPAIR AUTHORIZATION

READ-ONLY CONFIRMATION GATE.

V98 does NOT modify the database.
V98 does NOT execute repairs.

It reads the V97 repair-preview candidate and requires an
explicit human decision:

    CONFIRM
    REJECT
    DEFER

Only CONFIRM is eligible for V99 controlled execution.
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime


DB_PATH = "/data/data/com.termux/files/home/POS-Ledger-NG/data/posledger.db"


@dataclass
class Candidate:
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


def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (name,),
    ).fetchone()

    return row is not None


def columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {
        row[1]
        for row in conn.execute(
            f'PRAGMA table_info("{table}")'
        ).fetchall()
    }


def find_column(
    available: set[str],
    names: list[str],
) -> str | None:

    lowered = {
        name.casefold(): name
        for name in available
    }

    for name in names:
        if name.casefold() in lowered:
            return lowered[name.casefold()]

    for column in available:
        for name in names:
            if name.casefold() in column.casefold():
                return column

    return None


def select_rows(
    conn: sqlite3.Connection,
    table: str,
    mapping: dict[str, list[str]],
):
    available = columns(conn, table)

    fields = []

    for alias, candidates in mapping.items():

        column = find_column(
            available,
            candidates,
        )

        if column:
            fields.append(
                f'"{column}" AS "{alias}"'
            )
        else:
            fields.append(
                f'NULL AS "{alias}"'
            )

    sql = f'''
        SELECT {", ".join(fields)}
        FROM "{table}"
    '''

    return conn.execute(sql).fetchall()


def normalize(value) -> str:
    return str(value or "").strip().casefold()


def find_candidate(
    conn: sqlite3.Connection,
) -> Candidate | None:

    sales = select_rows(
        conn,
        "sales",
        {
            "id": [
                "id",
                "sale_id",
                "transaction_id",
            ],
            "product_id": [
                "product_id",
                "product",
            ],
            "product_name": [
                "product_name",
                "name",
                "description",
            ],
            "quantity": [
                "quantity",
                "qty",
                "units",
            ],
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

    movements = select_rows(
        conn,
        "inventory_movements",
        {
            "id": [
                "id",
                "movement_id",
            ],
            "product_id": [
                "product_id",
                "product",
            ],
            "quantity": [
                "quantity",
                "qty",
                "units",
            ],
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

    sale_movements = [
        row
        for row in movements
        if normalize(row["movement_type"]) == "sale"
    ]

    candidates = []

    for sale in sales:

        receipt = str(
            sale["receipt"] or ""
        ).strip()

        if not receipt:
            continue

        if sale["product_id"] is None:
            continue

        try:
            quantity = float(
                sale["quantity"]
            )
        except (
            TypeError,
            ValueError,
        ):
            continue

        for movement in sale_movements:

            if movement["product_id"] is None:
                continue

            if int(
                movement["product_id"]
            ) != int(
                sale["product_id"]
            ):
                continue

            try:
                movement_quantity = float(
                    movement["quantity"]
                )
            except (
                TypeError,
                ValueError,
            ):
                continue

            if abs(
                quantity - movement_quantity
            ) > 0.000001:
                continue

            movement_reference = str(
                movement["reference"] or ""
            ).strip()

            if (
                movement_reference
                != receipt
            ):
                continue

            candidates.append(
                Candidate(
                    sale_id=int(
                        sale["id"]
                    ),
                    product_id=int(
                        sale["product_id"]
                    ),
                    product_name=str(
                        sale["product_name"]
                        or "UNKNOWN"
                    ),
                    quantity=quantity,
                    sale_date=str(
                        sale["sale_date"]
                        or ""
                    ),
                    receipt=receipt,
                    movement_id=int(
                        movement["id"]
                    ),
                    movement_quantity=movement_quantity,
                    movement_date=str(
                        movement["movement_date"]
                        or ""
                    ),
                    movement_reference=movement_reference,
                )
            )

    if len(candidates) != 1:
        return None

    return candidates[0]


def print_header(title: str) -> None:
    print("=" * 60)
    print(title)
    print("=" * 60)


def get_human_decision() -> str:

    print()
    print_header(
        "V98 HUMAN CONFIRMATION"
    )

    print(
        "Review the candidate above carefully."
    )

    print()
    print(
        "Type one of:"
    )
    print(
        "  CONFIRM  - authorize candidate for V99"
    )
    print(
        "  REJECT   - permanently reject this candidate"
    )
    print(
        "  DEFER    - leave unresolved for later review"
    )

    while True:

        try:
            decision = input(
                "\nV98 decision > "
            ).strip().upper()
        except EOFError:
            return "DEFER"

        if decision in {
            "CONFIRM",
            "REJECT",
            "DEFER",
        }:
            return decision

        print(
            "Invalid decision. "
            "Enter CONFIRM, REJECT, or DEFER."
        )


def main() -> None:

    print_header(
        "POS LEDGER NG V98"
    )

    print(
        "HUMAN CONFIRMATION & REPAIR AUTHORIZATION"
    )

    print()
    print_header("DATABASE")

    print(
        f"Database path : {DB_PATH}"
    )
    print(
        "Database mode : READ-ONLY"
    )

    if not os.path.exists(DB_PATH):

        print()
        print(
            "🔴 DATABASE NOT FOUND"
        )
        return

    uri = (
        f"file:{DB_PATH}"
        "?mode=ro"
    )

    try:

        conn = sqlite3.connect(
            uri,
            uri=True,
        )

        conn.row_factory = sqlite3.Row

    except sqlite3.Error as exc:

        print()
        print(
            "🔴 DATABASE OPEN FAILED"
        )
        print(
            f"Reason : {exc}"
        )
        return

    try:

        required = [
            "sales",
            "products",
            "inventory_movements",
            "purchases",
        ]

        print()
        print("Required tables:")

        missing = []

        for table in required:

            available = table_exists(
                conn,
                table,
            )

            print(
                f"{table:<22}: "
                f"{'AVAILABLE' if available else 'MISSING'}"
            )

            if not available:
                missing.append(table)

        if missing:

            print()
            print(
                "🔴 V98 CANNOT RUN"
            )

            print(
                "Missing required tables: "
                + ", ".join(missing)
            )

            return

        print()
        print_header(
            "V98 AUTHORIZATION INPUT"
        )

        candidate = find_candidate(
            conn
        )

        if candidate is None:

            print(
                "Verified candidates : 0"
            )

            print()
            print(
                "🟡 NO CANDIDATE AVAILABLE"
            )

            print(
                "V98 cannot authorize a repair "
                "without exactly one strong-evidence candidate."
            )

            print()
            print_header(
                "V98 EXECUTIVE DECISION"
            )

            print(
                "⏸ STOP — NO REPAIR AUTHORIZED"
            )

            return

        print(
            "Verified candidates : 1"
        )

        print()
        print_header(
            "V98 CANDIDATE FOR HUMAN REVIEW"
        )

        print("----------------------------------------")

        print(
            f"Sale ID             : "
            f"{candidate.sale_id}"
        )

        print(
            f"Product ID          : "
            f"{candidate.product_id}"
        )

        print(
            f"Product             : "
            f"{candidate.product_name}"
        )

        print(
            f"Quantity            : "
            f"{candidate.quantity:.2f}"
        )

        print(
            f"Sale date           : "
            f"{candidate.sale_date}"
        )

        print(
            f"Receipt             : "
            f"{candidate.receipt}"
        )

        print()

        print(
            "Existing movement   : "
            f"{candidate.movement_id}"
        )

        print(
            "Movement quantity   : "
            f"{candidate.movement_quantity:.2f}"
        )

        print(
            "Movement date       : "
            f"{candidate.movement_date}"
        )

        print(
            "Movement reference  : "
            f"{candidate.movement_reference}"
        )

        print()
        print(
            "Evidence strength   : STRONG"
        )

        print(
            "V97 preview status  : VERIFIED"
        )

        print()
        print_header(
            "PROPOSED V99 ACTION"
        )

        print(
            "Action              : "
            "CREATE SALE MOVEMENT"
        )

        print(
            f"Product ID          : "
            f"{candidate.product_id}"
        )

        print(
            f"Quantity            : "
            f"-{candidate.quantity:.2f}"
        )

        print(
            f"Reference           : "
            f"{candidate.receipt}"
        )

        print(
            f"Transaction date    : "
            f"{candidate.sale_date}"
        )

        print()
        print(
            "⚠ THIS IS ONLY A PROPOSED ACTION."
        )

        print(
            "V98 will NOT execute it."
        )

        decision = get_human_decision()

        print()
        print_header(
            "V98 AUTHORIZATION RESULT"
        )

        if decision == "CONFIRM":

            print(
                "🟢 HUMAN DECISION : CONFIRM"
            )

            print()
            print(
                "Repair authorization : APPROVED"
            )

            print(
                "Candidate status      : AUTHORIZED_FOR_V99"
            )

            print()
            print(
                "V99 may use this candidate "
                "for controlled execution."
            )

        elif decision == "REJECT":

            print(
                "🔴 HUMAN DECISION : REJECT"
            )

            print()
            print(
                "Repair authorization : REJECTED"
            )

            print(
                "Candidate status      : REJECTED"
            )

            print()
            print(
                "V99 must NOT execute this candidate."
            )

        else:

            print(
                "🟡 HUMAN DECISION : DEFER"
            )

            print()
            print(
                "Repair authorization : DEFERRED"
            )

            print(
                "Candidate status      : DEFERRED"
            )

            print()
            print(
                "V99 must NOT execute this candidate."
            )

        print()
        print_header(
            "V98 SAFETY STATUS"
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
        print_header(
            "V98 EXECUTIVE DECISION"
        )

        if decision == "CONFIRM":

            print(
                "🟢 PROCEED TO V99 CONTROLLED EXECUTION"
            )

        elif decision == "REJECT":

            print(
                "🔴 STOP — REPAIR CANDIDATE REJECTED"
            )

        else:

            print(
                "🟡 STOP — REPAIR CANDIDATE DEFERRED"
            )

    finally:

        conn.close()


if __name__ == "__main__":
    main()
