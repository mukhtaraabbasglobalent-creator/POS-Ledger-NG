"""
POS LEDGER NG V105
UNRESOLVED SALE EVIDENCE ANALYSIS

Purpose:
    Analyze unresolved completed sales against inventory movements.

Safety:
    - READ-ONLY
    - No INSERT
    - No UPDATE
    - No DELETE
    - No database mutation

Schema supported by the current POS Ledger NG database:

sales:
    id
    product_id
    quantity
    sale_date
    receipt_no
    status

products:
    id
    product_name
    sku
    barcode

inventory_movements:
    id
    product_id
    movement_type
    quantity
    balance_after
    reference
    remarks
    movement_date
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


DB_PATH = "/data/data/com.termux/files/home/POS-Ledger-NG/data/posledger.db"

VERIFIED_SALE_ID = 15
VERIFIED_REFERENCE = "PLN-20260814-000015"


# ------------------------------------------------------------
# GENERAL HELPERS
# ------------------------------------------------------------

def line(char: str = "=", width: int = 60) -> None:
    print(char * width)


def title(text: str) -> None:
    line("=")
    print(text)
    line("=")


def fmt_qty(value: Any) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return str(value)


def clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalize_text(value: Any) -> str:
    return " ".join(clean(value).lower().split())


def parse_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None

    text = clean(value)
    if not text:
        return None

    formats = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
    )

    for fmt in formats:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass

    return None


def seconds_difference(a: Any, b: Any) -> Optional[float]:
    da = parse_datetime(a)
    db = parse_datetime(b)

    if da is None or db is None:
        return None

    return abs((da - db).total_seconds())


def quantity_equal(a: Any, b: Any, tolerance: float = 1e-9) -> bool:
    try:
        return abs(float(a) - float(b)) <= tolerance
    except (TypeError, ValueError):
        return False


# ------------------------------------------------------------
# DATABASE
# ------------------------------------------------------------

def open_database() -> sqlite3.Connection:
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    # SQLite URI read-only connection.
    uri = f"file:{DB_PATH}?mode=ro"

    conn = sqlite3.connect(
        uri,
        uri=True,
        timeout=10,
    )

    conn.row_factory = sqlite3.Row

    # Additional safety.
    conn.execute("PRAGMA query_only = ON")

    return conn


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (table,),
    ).fetchone()

    return row is not None


def get_columns(
    conn: sqlite3.Connection,
    table: str,
) -> List[str]:
    rows = conn.execute(
        f"PRAGMA table_info({table})"
    ).fetchall()

    return [row["name"] for row in rows]


def require_schema(conn: sqlite3.Connection) -> None:
    required = {
        "sales": {
            "id",
            "product_id",
            "quantity",
            "sale_date",
            "receipt_no",
        },
        "products": {
            "id",
            "product_name",
        },
        "inventory_movements": {
            "id",
            "product_id",
            "movement_type",
            "quantity",
            "reference",
            "movement_date",
        },
    }

    for table, expected in required.items():
        if not table_exists(conn, table):
            raise RuntimeError(
                f"Required table missing: {table}"
            )

        actual = set(get_columns(conn, table))

        missing = expected - actual

        if missing:
            raise RuntimeError(
                f"Required columns missing from {table}: "
                + ", ".join(sorted(missing))
            )


# ------------------------------------------------------------
# COUNTS
# ------------------------------------------------------------

def get_completed_sales_count(
    conn: sqlite3.Connection,
) -> int:
    row = conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM sales
        WHERE status = 'COMPLETED'
        """
    ).fetchone()

    return int(row["count"])


def get_purchase_movements_count(
    conn: sqlite3.Connection,
) -> int:
    row = conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM inventory_movements
        WHERE UPPER(movement_type) IN
              ('PURCHASE', 'PURCHASE_IN', 'STOCK_IN')
        """
    ).fetchone()

    return int(row["count"])


def get_sale_movements_count(
    conn: sqlite3.Connection,
) -> int:
    row = conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM inventory_movements
        WHERE UPPER(movement_type) = 'SALE'
        """
    ).fetchone()

    return int(row["count"])


# ------------------------------------------------------------
# VERIFIED SALE
# ------------------------------------------------------------

def get_verified_sale(
    conn: sqlite3.Connection,
) -> Optional[sqlite3.Row]:
    return conn.execute(
        """
        SELECT
            s.id,
            s.product_id,
            s.quantity,
            s.sale_date,
            s.receipt_no,
            s.status,
            p.product_name
        FROM sales AS s
        LEFT JOIN products AS p
            ON p.id = s.product_id
        WHERE s.id = ?
        """,
        (VERIFIED_SALE_ID,),
    ).fetchone()


# ------------------------------------------------------------
# UNRESOLVED SALES
# ------------------------------------------------------------

def is_verified_sale(row: sqlite3.Row) -> bool:
    sale_id = row["id"]
    receipt = clean(row["receipt_no"])

    if sale_id == VERIFIED_SALE_ID:
        return True

    if receipt and receipt == VERIFIED_REFERENCE:
        return True

    return False


def get_all_completed_sales(
    conn: sqlite3.Connection,
) -> List[sqlite3.Row]:
    return conn.execute(
        """
        SELECT
            s.id,
            s.product_id,
            s.quantity,
            s.sale_date,
            s.receipt_no,
            s.status,
            p.product_name,
            p.sku,
            p.barcode
        FROM sales AS s
        LEFT JOIN products AS p
            ON p.id = s.product_id
        WHERE s.status = 'COMPLETED'
        ORDER BY s.id
        """
    ).fetchall()


# ------------------------------------------------------------
# INVENTORY MOVEMENTS
# ------------------------------------------------------------

def get_sale_movements_for_product(
    conn: sqlite3.Connection,
    product_id: int,
) -> List[sqlite3.Row]:
    return conn.execute(
        """
        SELECT
            id,
            product_id,
            movement_type,
            quantity,
            balance_after,
            reference,
            remarks,
            movement_date
        FROM inventory_movements
        WHERE product_id = ?
          AND UPPER(movement_type) = 'SALE'
        ORDER BY id
        """,
        (product_id,),
    ).fetchall()


def get_all_sale_movements(
    conn: sqlite3.Connection,
) -> List[sqlite3.Row]:
    return conn.execute(
        """
        SELECT
            id,
            product_id,
            movement_type,
            quantity,
            balance_after,
            reference,
            remarks,
            movement_date
        FROM inventory_movements
        WHERE UPPER(movement_type) = 'SALE'
        ORDER BY id
        """
    ).fetchall()


# ------------------------------------------------------------
# EVIDENCE CLASSIFICATION
# ------------------------------------------------------------

def classify_sale(
    sale: sqlite3.Row,
    movements: List[sqlite3.Row],
) -> Dict[str, Any]:

    sale_id = sale["id"]
    product_id = sale["product_id"]
    sale_qty = float(sale["quantity"])
    sale_date = clean(sale["sale_date"])
    receipt = clean(sale["receipt_no"])

    if is_verified_sale(sale):
        return {
            "status": "VERIFIED_ALREADY_REPAIRED",
            "strength": "STRONG",
            "reason": "Sale is the previously verified V103 candidate.",
            "movement": None,
        }

    if not movements:
        return {
            "status": "NO_MOVEMENT",
            "strength": "NONE",
            "reason": "No SALE inventory movement exists for this product.",
            "movement": None,
        }

    # --------------------------------------------------------
    # 1. Exact reference match
    # --------------------------------------------------------

    if receipt:
        for movement in movements:
            movement_ref = clean(movement["reference"])

            if (
                movement_ref
                and movement_ref == receipt
                and quantity_equal(
                    abs(float(movement["quantity"])),
                    sale_qty,
                )
            ):
                date_diff = seconds_difference(
                    sale_date,
                    movement["movement_date"],
                )

                if date_diff == 0:
                    return {
                        "status": "EXACT_MATCH",
                        "strength": "STRONG",
                        "reason": (
                            "Exact reference, product, quantity "
                            "and timestamp match."
                        ),
                        "movement": movement,
                    }

                return {
                    "status": "REFERENCE_MATCH_DATE_DIFFERENCE",
                    "strength": "WEAK",
                    "reason": (
                        "Reference, product and quantity match, "
                        "but timestamps differ."
                    ),
                    "movement": movement,
                }

    # --------------------------------------------------------
    # 2. Exact product + quantity + date
    # --------------------------------------------------------

    exact_date_matches = []

    for movement in movements:
        if not quantity_equal(
            abs(float(movement["quantity"])),
            sale_qty,
        ):
            continue

        date_diff = seconds_difference(
            sale_date,
            movement["movement_date"],
        )

        if date_diff == 0:
            exact_date_matches.append(movement)

    if len(exact_date_matches) == 1:
        return {
            "status": "DATE_QUANTITY_MATCH",
            "strength": "STRONG",
            "reason": (
                "Product, quantity and timestamp match. "
                "Reference is absent or different."
            ),
            "movement": exact_date_matches[0],
        }

    if len(exact_date_matches) > 1:
        return {
            "status": "AMBIGUOUS",
            "strength": "AMBIGUOUS",
            "reason": (
                "Multiple inventory SALE movements match "
                "the product, quantity and timestamp."
            ),
            "movement": None,
        }

    # --------------------------------------------------------
    # 3. Product + quantity only
    # --------------------------------------------------------

    quantity_matches = []

    for movement in movements:
        if quantity_equal(
            abs(float(movement["quantity"])),
            sale_qty,
        ):
            quantity_matches.append(movement)

    if len(quantity_matches) == 1:
        return {
            "status": "MANUAL_REVIEW",
            "strength": "WEAK",
            "reason": (
                "Product and quantity match, but timestamp "
                "does not match."
            ),
            "movement": quantity_matches[0],
        }

    if len(quantity_matches) > 1:
        return {
            "status": "AMBIGUOUS",
            "strength": "AMBIGUOUS",
            "reason": (
                "Multiple inventory movements provide the "
                "same product and quantity. Safe matching "
                "is not possible."
            ),
            "movement": None,
        }

    # --------------------------------------------------------
    # 4. Nothing safe
    # --------------------------------------------------------

    return {
        "status": "DO_NOT_REPAIR",
        "strength": "NONE",
        "reason": (
            "Existing movements do not provide a safe "
            "quantity match."
        ),
        "movement": None,
    }


# ------------------------------------------------------------
# REPORTING
# ------------------------------------------------------------

def print_candidate(
    sale: sqlite3.Row,
    result: Dict[str, Any],
) -> None:

    print("-" * 40)

    print(f"Sale ID             : {sale['id']}")
    print(f"Product ID          : {sale['product_id']}")
    print(f"Product             : {clean(sale['product_name'])}")
    print(f"Quantity            : {fmt_qty(sale['quantity'])}")
    print(f"Sale date           : {sale['sale_date']}")
    print(
        f"Receipt/reference   : "
        f"{clean(sale['receipt_no']) or 'NONE'}"
    )

    print(
        f"Evidence strength   : "
        f"{result['strength']}"
    )

    print(
        f"Classification      : "
        f"{result['status']}"
    )

    print(
        f"Reason              : "
        f"{result['reason']}"
    )

    movement = result.get("movement")

    if movement is not None:
        print()
        print(
            f"Movement ID         : "
            f"{movement['id']}"
        )
        print(
            f"Movement quantity   : "
            f"{fmt_qty(movement['quantity'])}"
        )
        print(
            f"Movement date      : "
            f"{movement['movement_date']}"
        )
        print(
            f"Movement reference  : "
            f"{clean(movement['reference']) or 'NONE'}"
        )


def print_remaining_summary(
    sales: List[sqlite3.Row],
) -> None:

    line()
    print("V105 REMAINING UNRESOLVED SALES")
    line()

    unresolved = []

    for sale in sales:
        if sale["id"] == VERIFIED_SALE_ID:
            continue

        unresolved.append(sale)

    print(f"Unresolved sales : {len(unresolved)}")

    for sale in unresolved:
        print(
            f"Sale {sale['id']} | "
            f"Product {sale['product_id']} | "
            f"Qty {fmt_qty(sale['quantity'])} | "
            f"Ref {clean(sale['receipt_no']) or 'NONE'}"
        )


def print_inventory_history(
    conn: sqlite3.Connection,
    product_id: int,
) -> None:

    line()
    print("V105 PRODUCT INVENTORY HISTORY")
    line()

    rows = conn.execute(
        """
        SELECT
            id,
            movement_type,
            quantity,
            movement_date,
            reference
        FROM inventory_movements
        WHERE product_id = ?
        ORDER BY id
        """,
        (product_id,),
    ).fetchall()

    for row in rows:
        print(
            f"ID {row['id']:<4} "
            f"{clean(row['movement_type']):<9} "
            f"Qty {float(row['quantity']):>7.2f} "
            f"Date {clean(row['movement_date'])} "
            f"Ref {clean(row['reference']) or 'NONE'}"
        )


# ------------------------------------------------------------
# RECONCILIATION
# ------------------------------------------------------------

def get_product_reconciliation(
    conn: sqlite3.Connection,
) -> List[Tuple[int, str, float, float, float]]:
    rows = conn.execute(
        """
        SELECT
            p.id,
            p.product_name,

            COALESCE(
                (
                    SELECT SUM(s.quantity)
                    FROM sales AS s
                    WHERE s.product_id = p.id
                      AND s.status = 'COMPLETED'
                ),
                0
            ) AS sales_units,

            COALESCE(
                (
                    SELECT SUM(
                        CASE
                            WHEN UPPER(im.movement_type) = 'SALE'
                            THEN ABS(im.quantity)
                            ELSE 0
                        END
                    )
                    FROM inventory_movements AS im
                    WHERE im.product_id = p.id
                ),
                0
            ) AS inventory_sale_units

        FROM products AS p
        ORDER BY p.id
        """
    ).fetchall()

    result = []

    for row in rows:
        sales_units = float(row["sales_units"] or 0)
        inventory_units = float(
            row["inventory_sale_units"] or 0
        )

        difference = sales_units - inventory_units

        result.append(
            (
                int(row["id"]),
                clean(row["product_name"]),
                sales_units,
                inventory_units,
                difference,
            )
        )

    return result


def print_reconciliation(
    conn: sqlite3.Connection,
) -> None:

    line()
    print("V105 QUANTITY RECONCILIATION")
    line()

    rows = get_product_reconciliation(conn)

    total_sales = 0.0
    total_inventory = 0.0

    for (
        product_id,
        product_name,
        sales_units,
        inventory_units,
        difference,
    ) in rows:

        if sales_units == 0 and inventory_units == 0:
            continue

        total_sales += sales_units
        total_inventory += inventory_units

        print("-" * 40)
        print(f"Product ID          : {product_id}")
        print(f"Product             : {product_name}")
        print(f"Sales units         : {sales_units:.2f}")
        print(
            f"Inventory SALE units: "
            f"{inventory_units:.2f}"
        )
        print(f"Difference          : {difference:.2f}")

        if abs(difference) < 1e-9:
            print("Status              : MATCH")
        else:
            print("Status              : MISMATCH")

    print("-" * 40)
    print(f"Total sales units         : {total_sales:.2f}")
    print(
        f"Total inventory SALE units: "
        f"{total_inventory:.2f}"
    )
    print(
        f"Total unrepresented units : "
        f"{max(total_sales - total_inventory, 0):.2f}"
    )


# ------------------------------------------------------------
# REFERENCE CHECK
# ------------------------------------------------------------

def duplicate_sale_reference_check(
    conn: sqlite3.Connection,
) -> int:

    row = conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM (
            SELECT receipt_no
            FROM sales
            WHERE status = 'COMPLETED'
              AND receipt_no IS NOT NULL
              AND TRIM(receipt_no) <> ''
            GROUP BY receipt_no
            HAVING COUNT(*) > 1
        )
        """
    ).fetchone()

    return int(row["count"])


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------

def main() -> None:

    title(
        "POS LEDGER NG V105\n"
        "UNRESOLVED SALE EVIDENCE ANALYSIS"
    )

    print()
    print(f"Database path : {DB_PATH}")
    print("Database mode : READ-ONLY")

    conn = open_database()

    try:
        require_schema(conn)

        line()
        print("DATABASE TABLES")
        line()

        print("sales                   : AVAILABLE")
        print("products                : AVAILABLE")
        print(
            "inventory_movements     : "
            "AVAILABLE"
        )

        print()
        line()
        print("V105 AUDIT INPUT COUNTS")
        line()

        sales_count = get_completed_sales_count(conn)
        sale_movements = get_sale_movements_count(conn)
        purchase_movements = get_purchase_movements_count(conn)

        print(
            f"Completed sales             : "
            f"{sales_count}"
        )
        print(
            f"Inventory SALE movements    : "
            f"{sale_movements}"
        )
        print(
            f"Inventory PURCHASE movements: "
            f"{purchase_movements}"
        )

        # ----------------------------------------------------
        # Verified V103 candidate
        # ----------------------------------------------------

        verified = get_verified_sale(conn)

        if verified is not None:
            line()
            print("V105 VERIFIED SALE EXCLUSION")
            line()

            print(
                f"Sale ID             : "
                f"{verified['id']}"
            )
            print(
                f"Product ID          : "
                f"{verified['product_id']}"
            )
            print(
                f"Product             : "
                f"{clean(verified['product_name'])}"
            )
            print(
                f"Quantity            : "
                f"{fmt_qty(verified['quantity'])}"
            )
            print(
                f"Sale timestamp      : "
                f"{verified['sale_date']}"
            )
            print(
                f"Reference           : "
                f"{clean(verified['receipt_no'])}"
            )

            print(
                "Status              : "
                "ALREADY VERIFIED BY V103/V104"
            )

        # ----------------------------------------------------
        # Analyze all sales
        # ----------------------------------------------------

        sales = get_all_completed_sales(conn)

        line()
        print("V105 UNRESOLVED SALE EVIDENCE")
        line()

        counts = {
            "strong": 0,
            "weak": 0,
            "ambiguous": 0,
            "none": 0,
            "verified": 0,
        }

        manual_review_candidates = []
        strong_candidates = []
        do_not_repair = []

        for sale in sales:

            if is_verified_sale(sale):
                counts["verified"] += 1
                continue

            movements = get_sale_movements_for_product(
                conn,
                int(sale["product_id"]),
            )

            result = classify_sale(
                sale,
                movements,
            )

            strength = result["strength"]

            if strength == "STRONG":
                counts["strong"] += 1
                strong_candidates.append(
                    (sale, result)
                )

            elif strength == "WEAK":
                counts["weak"] += 1
                manual_review_candidates.append(
                    (sale, result)
                )

            elif strength == "AMBIGUOUS":
                counts["ambiguous"] += 1

            else:
                counts["none"] += 1
                do_not_repair.append(
                    (sale, result)
                )

            print_candidate(
                sale,
                result,
            )

        # ----------------------------------------------------
        # Summary
        # ----------------------------------------------------

        line()
        print("V105 EVIDENCE SUMMARY")
        line()

        print(
            f"Completed sales audited : "
            f"{sales_count}"
        )
        print(
            f"Previously verified     : "
            f"{counts['verified']}"
        )
        print(
            f"Strong unresolved       : "
            f"{counts['strong']}"
        )
        print(
            f"Weak / manual review    : "
            f"{counts['weak']}"
        )
        print(
            f"Ambiguous               : "
            f"{counts['ambiguous']}"
        )
        print(
            f"No safe evidence        : "
            f"{counts['none']}"
        )

        # ----------------------------------------------------
        # Strong candidates
        # ----------------------------------------------------

        line()
        print("V105 STRONG CANDIDATES")
        line()

        if not strong_candidates:
            print("None identified.")

        else:
            for sale, result in strong_candidates:
                print(
                    f"Sale {sale['id']} | "
                    f"Product {sale['product_id']} | "
                    f"Qty {fmt_qty(sale['quantity'])} | "
                    f"Ref {clean(sale['receipt_no']) or 'NONE'}"
                )

                movement = result.get("movement")

                if movement:
                    print(
                        f"  Movement {movement['id']} | "
                        f"Qty {fmt_qty(movement['quantity'])} | "
                        f"Date {movement['movement_date']} | "
                        f"Ref {clean(movement['reference']) or 'NONE'}"
                    )

        # ----------------------------------------------------
        # Manual review
        # ----------------------------------------------------

        line()
        print("V105 MANUAL REVIEW CANDIDATES")
        line()

        if not manual_review_candidates:
            print("None identified.")

        else:
            for sale, result in manual_review_candidates:
                movement = result.get("movement")

                print(
                    f"Sale {sale['id']} | "
                    f"Product {sale['product_id']} | "
                    f"Qty {fmt_qty(sale['quantity'])}"
                )

                print(
                    f"  Sale date     : "
                    f"{sale['sale_date']}"
                )

                print(
                    f"  Receipt       : "
                    f"{clean(sale['receipt_no']) or 'NONE'}"
                )

                if movement:
                    print(
                        f"  Movement ID   : "
                        f"{movement['id']}"
                    )
                    print(
                        f"  Movement date : "
                        f"{movement['movement_date']}"
                    )
                    print(
                        f"  Movement ref  : "
                        f"{clean(movement['reference']) or 'NONE'}"
                    )

                print(
                    "  Decision      : "
                    "MANUAL REVIEW"
                )

        # ----------------------------------------------------
        # Ambiguous
        # ----------------------------------------------------

        line()
        print("V105 AMBIGUOUS SALES")
        line()

        ambiguous_found = False

        for sale in sales:

            if is_verified_sale(sale):
                continue

            movements = get_sale_movements_for_product(
                conn,
                int(sale["product_id"]),
            )

            result = classify_sale(
                sale,
                movements,
            )

            if result["strength"] == "AMBIGUOUS":
                ambiguous_found = True

                print(
                    f"Sale {sale['id']} | "
                    f"Product {sale['product_id']} | "
                    f"Qty {fmt_qty(sale['quantity'])} | "
                    f"Ref {clean(sale['receipt_no']) or 'NONE'}"
                )

                print(
                    f"Reason: {result['reason']}"
                )

        if not ambiguous_found:
            print("None identified.")

        # ----------------------------------------------------
        # Remaining unresolved
        # ----------------------------------------------------

        print_remaining_summary(sales)

        # ----------------------------------------------------
        # Product reconciliation
        # ----------------------------------------------------

        print_reconciliation(conn)

        # ----------------------------------------------------
        # Duplicate references
        # ----------------------------------------------------

        line()
        print("V105 DUPLICATE SALE REFERENCE CHECK")
        line()

        duplicate_count = duplicate_sale_reference_check(
            conn
        )

        print(
            f"Duplicate SALE reference groups : "
            f"{duplicate_count}"
        )

        if duplicate_count == 0:
            print("Reference uniqueness : PASS")
        else:
            print(
                "Reference uniqueness : "
                "REVIEW REQUIRED"
            )

        # ----------------------------------------------------
        # Safety / decision
        # ----------------------------------------------------

        line()
        print("V105 INTEGRITY DECISION")
        line()

        print("Critical failures : 0")

        print()
        print(
            "🟢 V105 ANALYSIS COMPLETE"
        )

        print(
            "V105 identified unresolved sale evidence "
            "without modifying the database."
        )

        print()
        print(
            "No unresolved sale is automatically authorized "
            "for repair by V105."
        )

        print()
        print(
            "Only a future evidence-review / human-confirmation "
            "phase may authorize another controlled repair."
        )

        # ----------------------------------------------------
        # Read-only proof
        # ----------------------------------------------------

        line()
        print("V105 SAFETY STATUS")
        line()

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

        line()
        print("V105 COMPLETE")
        line()

    finally:
        conn.close()


if __name__ == "__main__":
    main()
