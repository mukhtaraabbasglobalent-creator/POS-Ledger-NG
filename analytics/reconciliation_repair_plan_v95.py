#!/usr/bin/env python3
"""
POS LEDGER NG V95
RECONCILIATION REPAIR PLAN INTELLIGENCE

Purpose
-------
Convert V94 transaction/inventory audit findings into a controlled,
read-only repair plan.

IMPORTANT:
    This module NEVER modifies the database.

It identifies:
    - unmatched sales
    - weak sale matches
    - orphan purchase movements
    - purchase/inventory discrepancies
    - product-level stock discrepancies
    - safe repair candidates
    - blocked repair candidates
    - quantities requiring investigation

V95 is a planning layer only.

Pipeline:
    V94 Audit
        ↓
    V95 Repair Plan
        ↓
    V96 Verification / Approval
        ↓
    V97 Controlled Repair
        ↓
    V98 Post-Repair Audit
        ↓
    V99 Integrity Certification
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "posledger.db"

TARGET_MARGIN = 0.10

VERSION = "V95"


# ============================================================
# DISPLAY HELPERS
# ============================================================

LINE = "=" * 60
SUBLINE = "-" * 40


def money(value: float) -> str:
    return f"₦{value:,.2f}"


def number(value: float) -> str:
    return f"{value:,.2f}"


def pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def print_header(title: str) -> None:
    print(LINE)
    print(title)
    print(LINE)


# ============================================================
# DATABASE HELPERS
# ============================================================

def connect_read_only() -> sqlite3.Connection:
    """
    Open SQLite database in read-only mode.

    SQLite URI mode prevents accidental writes from this module.
    """
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    uri = f"file:{DB_PATH}?mode=ro"

    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row

    return conn


def table_exists(
    conn: sqlite3.Connection,
    table_name: str,
) -> bool:
    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (table_name,),
    ).fetchone()

    return row is not None


def column_names(
    conn: sqlite3.Connection,
    table_name: str,
) -> list[str]:
    if not table_exists(conn, table_name):
        return []

    rows = conn.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return [row["name"] for row in rows]


def first_existing_column(
    columns: list[str],
    candidates: list[str],
) -> Optional[str]:
    for candidate in candidates:
        if candidate in columns:
            return candidate
    return None


# ============================================================
# GENERIC VALUE HELPERS
# ============================================================

def row_value(
    row: sqlite3.Row,
    candidates: list[str],
    default: Any = None,
) -> Any:
    keys = row.keys()

    for name in candidates:
        if name in keys:
            return row[name]

    return default


def normalize_text(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip().lower()


def parse_date(value: Any) -> Optional[datetime]:
    if not value:
        return None

    text = str(value).strip()

    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue

    return None


def same_date(a: Any, b: Any) -> bool:
    da = parse_date(a)
    db = parse_date(b)

    if da is None or db is None:
        return False

    return da.date() == db.date()


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class SaleRecord:
    sale_id: int
    product_id: Optional[int]
    product_name: str
    quantity: float
    receipt: str
    sale_date: str
    total_amount: float
    cogs: float


@dataclass
class PurchaseRecord:
    purchase_id: int
    product_id: Optional[int]
    product_name: str
    quantity: float
    purchase_no: str
    purchase_date: str
    total_amount: float


@dataclass
class InventoryMovement:
    movement_id: int
    product_id: Optional[int]
    product_name: str
    movement_type: str
    quantity: float
    balance_after: Optional[float]
    reference: str
    movement_date: str


@dataclass
class RepairCandidate:
    candidate_id: int
    category: str
    priority: str
    record_id: int
    product_id: Optional[int]
    product_name: str
    quantity: float
    proposed_action: str
    evidence: str
    status: str


# ============================================================
# SALES LOADING
# ============================================================

def load_sales(
    conn: sqlite3.Connection,
) -> list[SaleRecord]:

    if not table_exists(conn, "sales"):
        return []

    columns = column_names(conn, "sales")

    id_col = first_existing_column(
        columns,
        ["id", "sale_id"],
    )

    product_col = first_existing_column(
        columns,
        ["product_id", "product"],
    )

    quantity_col = first_existing_column(
        columns,
        ["quantity", "qty"],
    )

    receipt_col = first_existing_column(
        columns,
        [
            "receipt_no",
            "receipt_number",
            "reference",
            "invoice_no",
        ],
    )

    date_col = first_existing_column(
        columns,
        [
            "sale_date",
            "created_at",
            "date",
            "timestamp",
        ],
    )

    amount_col = first_existing_column(
        columns,
        [
            "total_amount",
            "total",
            "amount",
        ],
    )

    cogs_col = first_existing_column(
        columns,
        [
            "cogs",
            "cost_of_goods_sold",
            "cost",
        ],
    )

    status_col = first_existing_column(
        columns,
        ["status"],
    )

    if id_col is None:
        return []

    select_parts = [
        f"{id_col} AS _id",
    ]

    if product_col:
        select_parts.append(
            f"{product_col} AS _product"
        )
    else:
        select_parts.append(
            "NULL AS _product"
        )

    if quantity_col:
        select_parts.append(
            f"{quantity_col} AS _quantity"
        )
    else:
        select_parts.append(
            "0 AS _quantity"
        )

    if receipt_col:
        select_parts.append(
            f"{receipt_col} AS _receipt"
        )
    else:
        select_parts.append(
            "NULL AS _receipt"
        )

    if date_col:
        select_parts.append(
            f"{date_col} AS _date"
        )
    else:
        select_parts.append(
            "NULL AS _date"
        )

    if amount_col:
        select_parts.append(
            f"{amount_col} AS _amount"
        )
    else:
        select_parts.append(
            "0 AS _amount"
        )

    if cogs_col:
        select_parts.append(
            f"{cogs_col} AS _cogs"
        )
    else:
        select_parts.append(
            "0 AS _cogs"
        )

    where_clause = ""

    if status_col:
        where_clause = (
            f"WHERE LOWER(COALESCE({status_col}, '')) "
            f"IN ('completed', 'complete', 'paid')"
        )

    query = f"""
        SELECT {", ".join(select_parts)}
        FROM sales
        {where_clause}
        ORDER BY {id_col}
    """

    rows = conn.execute(query).fetchall()

    products = load_product_lookup(conn)

    result: list[SaleRecord] = []

    for row in rows:
        product_id = None

        raw_product = row["_product"]

        try:
            if raw_product is not None:
                product_id = int(raw_product)
        except (TypeError, ValueError):
            product_id = None

        product_name = products.get(
            product_id,
            str(raw_product)
            if raw_product is not None
            else "Unknown product",
        )

        result.append(
            SaleRecord(
                sale_id=int(row["_id"]),
                product_id=product_id,
                product_name=product_name,
                quantity=safe_float(
                    row["_quantity"]
                ),
                receipt=str(
                    row["_receipt"] or ""
                ).strip(),
                sale_date=str(
                    row["_date"] or ""
                ),
                total_amount=safe_float(
                    row["_amount"]
                ),
                cogs=safe_float(
                    row["_cogs"]
                ),
            )
        )

    return result


# ============================================================
# PURCHASE LOADING
# ============================================================

def load_purchases(
    conn: sqlite3.Connection,
) -> list[PurchaseRecord]:

    if not table_exists(conn, "purchases"):
        return []

    columns = column_names(conn, "purchases")

    id_col = first_existing_column(
        columns,
        ["id", "purchase_id"],
    )

    product_col = first_existing_column(
        columns,
        ["product_id", "product"],
    )

    quantity_col = first_existing_column(
        columns,
        ["quantity", "qty"],
    )

    reference_col = first_existing_column(
        columns,
        [
            "purchase_no",
            "purchase_number",
            "reference",
            "invoice_no",
        ],
    )

    date_col = first_existing_column(
        columns,
        [
            "purchase_date",
            "created_at",
            "date",
            "timestamp",
        ],
    )

    amount_col = first_existing_column(
        columns,
        [
            "total_amount",
            "total",
            "amount",
        ],
    )

    if id_col is None:
        return []

    select_parts = [
        f"{id_col} AS _id",
    ]

    if product_col:
        select_parts.append(
            f"{product_col} AS _product"
        )
    else:
        select_parts.append(
            "NULL AS _product"
        )

    if quantity_col:
        select_parts.append(
            f"{quantity_col} AS _quantity"
        )
    else:
        select_parts.append(
            "0 AS _quantity"
        )

    if reference_col:
        select_parts.append(
            f"{reference_col} AS _reference"
        )
    else:
        select_parts.append(
            "NULL AS _reference"
        )

    if date_col:
        select_parts.append(
            f"{date_col} AS _date"
        )
    else:
        select_parts.append(
            "NULL AS _date"
        )

    if amount_col:
        select_parts.append(
            f"{amount_col} AS _amount"
        )
    else:
        select_parts.append(
            "0 AS _amount"
        )

    query = f"""
        SELECT {", ".join(select_parts)}
        FROM purchases
        ORDER BY {id_col}
    """

    rows = conn.execute(query).fetchall()

    products = load_product_lookup(conn)

    result: list[PurchaseRecord] = []

    for row in rows:
        product_id = None

        raw_product = row["_product"]

        try:
            if raw_product is not None:
                product_id = int(raw_product)
        except (TypeError, ValueError):
            product_id = None

        product_name = products.get(
            product_id,
            str(raw_product)
            if raw_product is not None
            else "Unknown product",
        )

        result.append(
            PurchaseRecord(
                purchase_id=int(row["_id"]),
                product_id=product_id,
                product_name=product_name,
                quantity=safe_float(
                    row["_quantity"]
                ),
                purchase_no=str(
                    row["_reference"] or ""
                ).strip(),
                purchase_date=str(
                    row["_date"] or ""
                ),
                total_amount=safe_float(
                    row["_amount"]
                ),
            )
        )

    return result


# ============================================================
# PRODUCT LOOKUP
# ============================================================

def load_product_lookup(
    conn: sqlite3.Connection,
) -> dict[Optional[int], str]:

    if not table_exists(conn, "products"):
        return {}

    columns = column_names(conn, "products")

    id_col = first_existing_column(
        columns,
        ["id", "product_id"],
    )

    name_col = first_existing_column(
        columns,
        [
            "name",
            "product_name",
            "title",
        ],
    )

    if id_col is None or name_col is None:
        return {}

    rows = conn.execute(
        f"""
        SELECT {id_col} AS _id,
               {name_col} AS _name
        FROM products
        """
    ).fetchall()

    result: dict[Optional[int], str] = {}

    for row in rows:
        try:
            pid = int(row["_id"])
        except (TypeError, ValueError):
            continue

        result[pid] = str(
            row["_name"] or "Unknown product"
        )

    return result


# ============================================================
# INVENTORY MOVEMENT LOADING
# ============================================================

def load_inventory_movements(
    conn: sqlite3.Connection,
) -> list[InventoryMovement]:

    if not table_exists(
        conn,
        "inventory_movements",
    ):
        return []

    columns = column_names(
        conn,
        "inventory_movements",
    )

    id_col = first_existing_column(
        columns,
        ["id", "movement_id"],
    )

    product_col = first_existing_column(
        columns,
        ["product_id", "product"],
    )

    type_col = first_existing_column(
        columns,
        [
            "movement_type",
            "type",
            "transaction_type",
        ],
    )

    quantity_col = first_existing_column(
        columns,
        ["quantity", "qty"],
    )

    balance_col = first_existing_column(
        columns,
        [
            "balance_after",
            "stock_after",
            "running_balance",
        ],
    )

    reference_col = first_existing_column(
        columns,
        [
            "reference",
            "reference_no",
            "receipt_no",
        ],
    )

    date_col = first_existing_column(
        columns,
        [
            "movement_date",
            "created_at",
            "date",
            "timestamp",
        ],
    )

    if id_col is None:
        return []

    select_parts = [
        f"{id_col} AS _id",
    ]

    for column, alias in [
        (product_col, "_product"),
        (type_col, "_type"),
        (quantity_col, "_quantity"),
        (balance_col, "_balance"),
        (reference_col, "_reference"),
        (date_col, "_date"),
    ]:
        if column:
            select_parts.append(
                f"{column} AS {alias}"
            )
        else:
            select_parts.append(
                f"NULL AS {alias}"
            )

    query = f"""
        SELECT {", ".join(select_parts)}
        FROM inventory_movements
        ORDER BY {id_col}
    """

    rows = conn.execute(query).fetchall()

    products = load_product_lookup(conn)

    result: list[InventoryMovement] = []

    for row in rows:
        product_id = None

        raw_product = row["_product"]

        try:
            if raw_product is not None:
                product_id = int(raw_product)
        except (TypeError, ValueError):
            product_id = None

        result.append(
            InventoryMovement(
                movement_id=int(row["_id"]),
                product_id=product_id,
                product_name=products.get(
                    product_id,
                    "Unknown product",
                ),
                movement_type=str(
                    row["_type"] or ""
                ).strip().upper(),
                quantity=safe_float(
                    row["_quantity"]
                ),
                balance_after=(
                    safe_float(
                        row["_balance"]
                    )
                    if row["_balance"] is not None
                    else None
                ),
                reference=str(
                    row["_reference"] or ""
                ).strip(),
                movement_date=str(
                    row["_date"] or ""
                ),
            )
        )

    return result


# ============================================================
# CURRENT STOCK
# ============================================================

def load_current_stock(
    conn: sqlite3.Connection,
) -> dict[int, float]:

    if not table_exists(conn, "products"):
        return {}

    columns = column_names(
        conn,
        "products",
    )

    id_col = first_existing_column(
        columns,
        ["id", "product_id"],
    )

    stock_col = first_existing_column(
        columns,
        [
            "current_stock",
            "stock",
            "quantity_in_stock",
            "qty_in_stock",
        ],
    )

    if id_col is None or stock_col is None:
        return {}

    rows = conn.execute(
        f"""
        SELECT {id_col} AS _id,
               {stock_col} AS _stock
        FROM products
        """
    ).fetchall()

    result: dict[int, float] = {}

    for row in rows:
        try:
            pid = int(row["_id"])
        except (TypeError, ValueError):
            continue

        result[pid] = safe_float(
            row["_stock"]
        )

    return result


# ============================================================
# MATCHING
# ============================================================

def normalize_reference(value: str) -> str:
    return normalize_text(value)


def find_exact_reference_matches(
    sale: SaleRecord,
    movements: list[InventoryMovement],
) -> list[InventoryMovement]:

    if not sale.receipt:
        return []

    reference = normalize_reference(
        sale.receipt
    )

    if not reference:
        return []

    matches = []

    for movement in movements:

        if movement.movement_type != "SALE":
            continue

        if (
            normalize_reference(
                movement.reference
            )
            == reference
        ):
            matches.append(movement)

    return matches


def find_product_quantity_matches(
    sale: SaleRecord,
    movements: list[InventoryMovement],
) -> list[InventoryMovement]:

    matches = []

    for movement in movements:

        if movement.movement_type != "SALE":
            continue

        if (
            movement.product_id
            == sale.product_id
            and abs(
                movement.quantity
                - sale.quantity
            )
            < 0.000001
        ):
            matches.append(movement)

    return matches


def classify_sale(
    sale: SaleRecord,
    movements: list[InventoryMovement],
) -> tuple[str, Optional[InventoryMovement], str]:

    exact = find_exact_reference_matches(
        sale,
        movements,
    )

    if len(exact) == 1:
        return (
            "SAFE_REFERENCE_MATCH",
            exact[0],
            "Exact receipt/reference match",
        )

    if len(exact) > 1:
        return (
            "AMBIGUOUS_REFERENCE",
            None,
            "Multiple inventory movements use the same reference",
        )

    product_quantity = find_product_quantity_matches(
        sale,
        movements,
    )

    if len(product_quantity) == 1:
        movement = product_quantity[0]

        if same_date(
            sale.sale_date,
            movement.movement_date,
        ):
            return (
                "STRONG_PRODUCT_QUANTITY_DATE",
                movement,
                "Product, quantity and date agree",
            )

        return (
            "WEAK_PRODUCT_QUANTITY",
            movement,
            "Product and quantity agree but date differs",
        )

    if len(product_quantity) > 1:
        return (
            "AMBIGUOUS_PRODUCT_QUANTITY",
            None,
            "Multiple product/quantity candidates",
        )

    return (
        "UNMATCHED",
        None,
        "No safe inventory SALE movement found",
    )


# ============================================================
# PRODUCT RECONCILIATION
# ============================================================

def sales_by_product(
    sales: list[SaleRecord],
) -> dict[int, float]:

    result: dict[int, float] = {}

    for sale in sales:

        if sale.product_id is None:
            continue

        result[sale.product_id] = (
            result.get(
                sale.product_id,
                0.0,
            )
            + sale.quantity
        )

    return result


def purchases_by_product(
    purchases: list[PurchaseRecord],
) -> dict[int, float]:

    result: dict[int, float] = {}

    for purchase in purchases:

        if purchase.product_id is None:
            continue

        result[purchase.product_id] = (
            result.get(
                purchase.product_id,
                0.0,
            )
            + purchase.quantity
        )

    return result


def inventory_by_product(
    movements: list[InventoryMovement],
    movement_types: set[str],
) -> dict[int, float]:

    result: dict[int, float] = {}

    for movement in movements:

        if (
            movement.product_id is None
            or movement.movement_type
            not in movement_types
        ):
            continue

        result[movement.product_id] = (
            result.get(
                movement.product_id,
                0.0,
            )
            + movement.quantity
        )

    return result


# ============================================================
# REPAIR CANDIDATES
# ============================================================

def build_repair_plan(
    sales: list[SaleRecord],
    purchases: list[PurchaseRecord],
    movements: list[InventoryMovement],
    current_stock: dict[int, float],
) -> list[RepairCandidate]:

    candidates: list[RepairCandidate] = []

    candidate_id = 1

    sale_movement_ids: set[int] = set()

    # --------------------------------------------------------
    # SALE AUDIT
    # --------------------------------------------------------

    for sale in sales:

        classification, movement, evidence = classify_sale(
            sale,
            movements,
        )

        if movement:
            sale_movement_ids.add(
                movement.movement_id
            )

        if classification == "SAFE_REFERENCE_MATCH":
            continue

        if classification == "STRONG_PRODUCT_QUANTITY_DATE":

            candidates.append(
                RepairCandidate(
                    candidate_id=candidate_id,
                    category="SALE_MATCH_VERIFICATION",
                    priority="MEDIUM",
                    record_id=sale.sale_id,
                    product_id=sale.product_id,
                    product_name=sale.product_name,
                    quantity=sale.quantity,
                    proposed_action=(
                        "VERIFY existing inventory movement; "
                        "do not create duplicate movement"
                    ),
                    evidence=evidence,
                    status="VERIFY",
                )
            )

            candidate_id += 1

        elif classification == "WEAK_PRODUCT_QUANTITY":

            candidates.append(
                RepairCandidate(
                    candidate_id=candidate_id,
                    category="SALE_WEAK_MATCH",
                    priority="HIGH",
                    record_id=sale.sale_id,
                    product_id=sale.product_id,
                    product_name=sale.product_name,
                    quantity=sale.quantity,
                    proposed_action=(
                        "MANUAL REVIEW before linking "
                        "sale to inventory movement"
                    ),
                    evidence=evidence,
                    status="BLOCKED",
                )
            )

            candidate_id += 1

        elif classification.startswith(
            "AMBIGUOUS"
        ):

            candidates.append(
                RepairCandidate(
                    candidate_id=candidate_id,
                    category="SALE_AMBIGUOUS",
                    priority="HIGH",
                    record_id=sale.sale_id,
                    product_id=sale.product_id,
                    product_name=sale.product_name,
                    quantity=sale.quantity,
                    proposed_action=(
                        "Resolve competing inventory candidates"
                    ),
                    evidence=evidence,
                    status="BLOCKED",
                )
            )

            candidate_id += 1

        else:

            candidates.append(
                RepairCandidate(
                    candidate_id=candidate_id,
                    category="SALE_UNMATCHED",
                    priority="HIGH",
                    record_id=sale.sale_id,
                    product_id=sale.product_id,
                    product_name=sale.product_name,
                    quantity=sale.quantity,
                    proposed_action=(
                        "Investigate transaction history; "
                        "possible missing SALE movement"
                    ),
                    evidence=evidence,
                    status="BLOCKED",
                )
            )

            candidate_id += 1

    # --------------------------------------------------------
    # ORPHAN PURCHASE MOVEMENTS
    # --------------------------------------------------------

    purchase_movements = [
        movement
        for movement in movements
        if movement.movement_type
        in {"PURCHASE", "IN"}
    ]

    purchase_match_ids: set[int] = set()

    for purchase in purchases:

        for movement in purchase_movements:

            if movement.movement_id in purchase_match_ids:
                continue

            if (
                movement.product_id
                == purchase.product_id
                and abs(
                    movement.quantity
                    - purchase.quantity
                )
                < 0.000001
                and same_date(
                    movement.movement_date,
                    purchase.purchase_date,
                )
            ):
                purchase_match_ids.add(
                    movement.movement_id
                )
                break

    for movement in purchase_movements:

        if (
            movement.movement_id
            in purchase_match_ids
        ):
            continue

        candidates.append(
            RepairCandidate(
                candidate_id=candidate_id,
                category="ORPHAN_PURCHASE_MOVEMENT",
                priority="MEDIUM",
                record_id=movement.movement_id,
                product_id=movement.product_id,
                product_name=movement.product_name,
                quantity=movement.quantity,
                proposed_action=(
                    "Identify originating purchase before "
                    "linking or removing movement"
                ),
                evidence=(
                    "Inventory purchase movement has "
                    "no verified purchase transaction"
                ),
                status="BLOCKED",
            )
        )

        candidate_id += 1

    # --------------------------------------------------------
    # PRODUCT LEVEL DIFFERENCES
    # --------------------------------------------------------

    sales_totals = sales_by_product(
        sales
    )

    purchase_totals = purchases_by_product(
        purchases
    )

    inventory_sales = inventory_by_product(
        movements,
        {"SALE"},
    )

    inventory_in = inventory_by_product(
        movements,
        {"PURCHASE", "IN"},
    )

    product_ids = set(
        list(sales_totals.keys())
        + list(purchase_totals.keys())
        + list(inventory_sales.keys())
        + list(inventory_in.keys())
        + list(current_stock.keys())
    )

    for product_id in sorted(
        product_ids,
        key=lambda x: x if x is not None else -1,
    ):

        sales_units = sales_totals.get(
            product_id,
            0.0,
        )

        inventory_sale_units = inventory_sales.get(
            product_id,
            0.0,
        )

        purchase_units = purchase_totals.get(
            product_id,
            0.0,
        )

        inventory_in_units = inventory_in.get(
            product_id,
            0.0,
        )

        sale_difference = (
            sales_units
            - inventory_sale_units
        )

        purchase_difference = (
            purchase_units
            - inventory_in_units
        )

        product_name = "Unknown product"

        for sale in sales:
            if sale.product_id == product_id:
                product_name = sale.product_name
                break

        if abs(sale_difference) > 0.000001:

            candidates.append(
                RepairCandidate(
                    candidate_id=candidate_id,
                    category="PRODUCT_SALE_RECONCILIATION",
                    priority="HIGH",
                    record_id=product_id,
                    product_id=product_id,
                    product_name=product_name,
                    quantity=abs(
                        sale_difference
                    ),
                    proposed_action=(
                        "Investigate missing or unrecorded "
                        "SALE inventory movements"
                    ),
                    evidence=(
                        f"Sales={number(sales_units)}, "
                        f"Inventory SALE="
                        f"{number(inventory_sale_units)}, "
                        f"Difference="
                        f"{number(sale_difference)}"
                    ),
                    status="BLOCKED",
                )
            )

            candidate_id += 1

        if abs(purchase_difference) > 0.000001:

            candidates.append(
                RepairCandidate(
                    candidate_id=candidate_id,
                    category="PRODUCT_PURCHASE_RECONCILIATION",
                    priority="MEDIUM",
                    record_id=product_id,
                    product_id=product_id,
                    product_name=product_name,
                    quantity=abs(
                        purchase_difference
                    ),
                    proposed_action=(
                        "Investigate purchase/inventory "
                        "movement linkage"
                    ),
                    evidence=(
                        f"Purchases={number(purchase_units)}, "
                        f"Inventory IN="
                        f"{number(inventory_in_units)}, "
                        f"Difference="
                        f"{number(purchase_difference)}"
                    ),
                    status="BLOCKED",
                )
            )

            candidate_id += 1

    return candidates


# ============================================================
# REPAIR READINESS
# ============================================================

def calculate_readiness(
    candidates: list[RepairCandidate],
) -> tuple[str, str]:

    if not candidates:
        return (
            "READY FOR VERIFICATION",
            "No unresolved repair candidates detected.",
        )

    blocked = [
        c
        for c in candidates
        if c.status == "BLOCKED"
    ]

    if blocked:
        return (
            "NOT READY",
            (
                f"{len(blocked)} repair candidate(s) "
                "remain unresolved."
            ),
        )

    return (
        "READY FOR VERIFICATION",
        "All candidates require verification before repair.",
    )


# ============================================================
# SCORE
# ============================================================

def calculate_repair_readiness_score(
    candidates: list[RepairCandidate],
) -> float:

    if not candidates:
        return 100.0

    high = sum(
        1
        for c in candidates
        if c.priority == "HIGH"
    )

    medium = sum(
        1
        for c in candidates
        if c.priority == "MEDIUM"
    )

    low = sum(
        1
        for c in candidates
        if c.priority == "LOW"
    )

    penalty = (
        high * 8.0
        + medium * 4.0
        + low * 1.0
    )

    return max(
        0.0,
        100.0 - penalty,
    )


# ============================================================
# REPORT
# ============================================================

def print_report(
    conn: sqlite3.Connection,
    sales: list[SaleRecord],
    purchases: list[PurchaseRecord],
    movements: list[InventoryMovement],
    current_stock: dict[int, float],
    candidates: list[RepairCandidate],
) -> None:

    print_header(
        "POS LEDGER NG V95\n"
        "RECONCILIATION REPAIR PLAN INTELLIGENCE"
    )

    print()

    print_header("DATABASE")
    print(
        f"Database path : {DB_PATH}"
    )
    print(
        "Database mode : READ-ONLY"
    )

    print()

    for table in [
        "sales",
        "products",
        "inventory_movements",
        "purchases",
        "expenses",
        "customer_credit",
        "suppliers",
    ]:

        status = (
            "AVAILABLE"
            if table_exists(
                conn,
                table,
            )
            else "NOT DETECTED"
        )

        print(
            f"{table:<22}: {status}"
        )

    # --------------------------------------------------------
    # COUNTS
    # --------------------------------------------------------

    print()
    print_header(
        "TRANSACTION & MOVEMENT COUNTS"
    )

    sale_movements = [
        m
        for m in movements
        if m.movement_type == "SALE"
    ]

    purchase_movements = [
        m
        for m in movements
        if m.movement_type
        in {"PURCHASE", "IN"}
    ]

    print(
        f"Completed sales             : {len(sales)}"
    )

    print(
        f"Purchase records            : {len(purchases)}"
    )

    print(
        f"Inventory SALE movements    : "
        f"{len(sale_movements)}"
    )

    print(
        f"Inventory PURCHASE movements: "
        f"{len(purchase_movements)}"
    )

    # --------------------------------------------------------
    # QUANTITIES
    # --------------------------------------------------------

    total_sales_units = sum(
        sale.quantity
        for sale in sales
    )

    total_purchase_units = sum(
        purchase.quantity
        for purchase in purchases
    )

    inventory_sale_units = sum(
        movement.quantity
        for movement in sale_movements
    )

    inventory_purchase_units = sum(
        movement.quantity
        for movement in purchase_movements
    )

    print()
    print_header(
        "RECONCILIATION QUANTITY POSITION"
    )

    print(
        f"Sales units                 : "
        f"{number(total_sales_units)}"
    )

    print(
        f"Inventory SALE units        : "
        f"{number(inventory_sale_units)}"
    )

    print(
        f"Unrepresented sale units    : "
        f"{number(max(0.0, total_sales_units - inventory_sale_units))}"
    )

    print(
        f"Purchase units              : "
        f"{number(total_purchase_units)}"
    )

    print(
        f"Inventory IN units          : "
        f"{number(inventory_purchase_units)}"
    )

    print(
        f"Purchase movement difference: "
        f"{number(total_purchase_units - inventory_purchase_units)}"
    )

    # --------------------------------------------------------
    # PRODUCT POSITION
    # --------------------------------------------------------

    print()
    print_header(
        "PRODUCT REPAIR PRESSURE"
    )

    sales_totals = sales_by_product(
        sales
    )

    purchase_totals = purchases_by_product(
        purchases
    )

    inventory_sales = inventory_by_product(
        movements,
        {"SALE"},
    )

    inventory_in = inventory_by_product(
        movements,
        {"PURCHASE", "IN"},
    )

    product_ids = set(
        list(sales_totals.keys())
        + list(purchase_totals.keys())
        + list(current_stock.keys())
    )

    for product_id in sorted(
        product_ids,
        key=lambda x: x if x is not None else -1,
    ):

        product_name = "Unknown product"

        for sale in sales:
            if sale.product_id == product_id:
                product_name = sale.product_name
                break

        if product_name == "Unknown product":
            for purchase in purchases:
                if purchase.product_id == product_id:
                    product_name = purchase.product_name
                    break

        sales_units = sales_totals.get(
            product_id,
            0.0,
        )

        inv_sale_units = inventory_sales.get(
            product_id,
            0.0,
        )

        purchase_units = purchase_totals.get(
            product_id,
            0.0,
        )

        inv_in_units = inventory_in.get(
            product_id,
            0.0,
        )

        stock = current_stock.get(
            product_id,
            0.0,
        )

        print(SUBLINE)
        print(
            f"Product ID       : {product_id}"
        )
        print(
            f"Product           : {product_name}"
        )
        print(
            f"Sales units       : {number(sales_units)}"
        )
        print(
            f"Inventory SALE    : {number(inv_sale_units)}"
        )
        print(
            f"Sale gap          : "
            f"{number(sales_units - inv_sale_units)}"
        )
        print(
            f"Purchase units    : {number(purchase_units)}"
        )
        print(
            f"Inventory IN      : {number(inv_in_units)}"
        )
        print(
            f"Purchase gap      : "
            f"{number(purchase_units - inv_in_units)}"
        )
        print(
            f"Current stock     : {number(stock)}"
        )

    # --------------------------------------------------------
    # REPAIR PLAN
    # --------------------------------------------------------

    print()
    print_header("V95 REPAIR-REVIEW PLAN")

    print(
        f"Repair-review candidates : "
        f"{len(candidates)}"
    )

    if not candidates:
        print(
            "No repair candidates detected."
        )

    else:

        for candidate in candidates:

            print(SUBLINE)

            print(
                f"{candidate.candidate_id}. "
                f"[{candidate.priority}] "
                f"{candidate.category}"
            )

            print(
                f"Record ID       : "
                f"{candidate.record_id}"
            )

            print(
                f"Product         : "
                f"{candidate.product_name}"
            )

            print(
                f"Quantity        : "
                f"{number(candidate.quantity)}"
            )

            print(
                f"Proposed action : "
                f"{candidate.proposed_action}"
            )

            print(
                f"Evidence        : "
                f"{candidate.evidence}"
            )

            print(
                f"Status          : "
                f"{candidate.status}"
            )

    # --------------------------------------------------------
    # SAFE / BLOCKED SUMMARY
    # --------------------------------------------------------

    safe = [
        c
        for c in candidates
        if c.status == "VERIFY"
    ]

    blocked = [
        c
        for c in candidates
        if c.status == "BLOCKED"
    ]

    print()
    print_header(
        "REPAIR CONTROL SUMMARY"
    )

    print(
        f"Verification candidates : "
        f"{len(safe)}"
    )

    print(
        f"Blocked candidates      : "
        f"{len(blocked)}"
    )

    print(
        f"Total candidates        : "
        f"{len(candidates)}"
    )

    # --------------------------------------------------------
    # SCORE
    # --------------------------------------------------------

    score = calculate_repair_readiness_score(
        candidates
    )

    print()
    print_header(
        "V95 REPAIR READINESS INDICATOR"
    )

    print(
        f"Readiness indicator : "
        f"{score:.2f}/100"
    )

    if blocked:
        print(
            "Status              : 🔴 BLOCKED"
        )
    elif safe:
        print(
            "Status              : 🟡 VERIFY"
        )
    else:
        print(
            "Status              : 🟢 CLEAR"
        )

    # --------------------------------------------------------
    # READINESS
    # --------------------------------------------------------

    readiness, reason = calculate_readiness(
        candidates
    )

    print()
    print_header(
        "V95 REPAIR READINESS"
    )

    if readiness == "NOT READY":
        print(
            "Status : 🔴 NOT READY"
        )
    else:
        print(
            "Status : 🟡 "
            f"{readiness}"
        )

    print()
    print(reason)

    print()
    print(
        "Automatic database repair is "
        "PROHIBITED in V95."
    )

    # --------------------------------------------------------
    # EXECUTIVE DECISION
    # --------------------------------------------------------

    print()
    print_header(
        "V95 EXECUTIVE DECISION"
    )

    if blocked:
        print(
            "🔴 STOP — VERIFY TRANSACTION/"
            "INVENTORY DISCREPANCIES"
        )

        print(
            f"{len(blocked)} blocked repair candidate(s) "
            "require human verification."
        )

    elif safe:
        print(
            "🟡 VERIFY — CONTROLLED REPAIR "
            "CANDIDATES IDENTIFIED"
        )

    else:
        print(
            "🟢 NO REPAIR PRESSURE DETECTED"
        )

    # --------------------------------------------------------
    # INTERPRETATION
    # --------------------------------------------------------

    print()
    print_header(
        "V95 MANAGEMENT INTERPRETATION"
    )

    print(
        "V95 converts V94 audit findings into "
        "explicit repair-review candidates."
    )

    print(
        "A repair candidate is not treated as "
        "proof that a database record is wrong."
    )

    print(
        "Missing inventory movements, orphan "
        "movements and product-level differences "
        "must be verified before any modification."
    )

    print(
        "Opening stock remains necessary for "
        "absolute stock reconstruction."
    )

    print(
        "V95 performs no automatic transaction, "
        "inventory, purchase or financial repair."
    )

    # --------------------------------------------------------
    # DATA INTEGRITY
    # --------------------------------------------------------

    print()
    print_header(
        "V95 DATA INTEGRITY STATUS"
    )

    print(
        f"Sales source             : "
        f"{'AVAILABLE' if sales else 'NOT DETECTED'}"
    )

    print(
        f"Products source          : "
        f"{'AVAILABLE' if table_exists(conn, 'products') else 'NOT DETECTED'}"
    )

    print(
        f"Inventory source         : "
        f"{'AVAILABLE' if movements else 'NOT DETECTED'}"
    )

    print(
        f"Purchases source         : "
        f"{'AVAILABLE' if purchases else 'NOT DETECTED'}"
    )

    print(
        f"Current stock source     : "
        f"{'DETECTED' if current_stock else 'NOT DETECTED'}"
    )

    print(
        "V94 audit findings       : USED"
    )

    print(
        "Automatic repair         : NO"
    )

    # --------------------------------------------------------
    # SAFETY
    # --------------------------------------------------------

    print()
    print_header(
        "V95 SAFETY STATUS"
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
        "Products modified     : NO"
    )

    print(
        "Inventory modified    : NO"
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

    print(LINE)


# ============================================================
# MAIN
# ============================================================

def main() -> None:

    conn = connect_read_only()

    try:

        sales = load_sales(
            conn
        )

        purchases = load_purchases(
            conn
        )

        movements = load_inventory_movements(
            conn
        )

        current_stock = load_current_stock(
            conn
        )

        candidates = build_repair_plan(
            sales=sales,
            purchases=purchases,
            movements=movements,
            current_stock=current_stock,
        )

        print_report(
            conn=conn,
            sales=sales,
            purchases=purchases,
            movements=movements,
            current_stock=current_stock,
            candidates=candidates,
        )

    finally:
        conn.close()


if __name__ == "__main__":
    main()
