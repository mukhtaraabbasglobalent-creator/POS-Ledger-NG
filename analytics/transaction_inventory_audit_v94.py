"""
POS LEDGER NG V94
TRANSACTION ↔ INVENTORY AUDIT & REPAIR-PLAN INTELLIGENCE

READ-ONLY MODULE.

Purpose:
- Audit every completed sale against inventory SALE movements.
- Audit every purchase against inventory PURCHASE/IN movements.
- Match using reference, receipt number, product, quantity and date.
- Produce an evidence-based repair plan.
- Never modify the database.
"""

from __future__ import annotations

import os
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------
# DATABASE DISCOVERY
# ---------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

CANDIDATE_DATABASES = [
    PROJECT_ROOT / "data" / "posledger.db",
    PROJECT_ROOT / "data" / "pos_ledger.db",
    PROJECT_ROOT / "data" / "posledger_ng.db",
    PROJECT_ROOT / "posledger.db",
    PROJECT_ROOT / "pos_ledger.db",
]

EXCLUDED_PARTS = {
    "backups",
    ".git",
    "__pycache__",
}


def find_database() -> Path | None:
    for path in CANDIDATE_DATABASES:
        if path.exists() and path.is_file():
            return path

    candidates = []

    for root in [PROJECT_ROOT / "data", PROJECT_ROOT]:
        if not root.exists():
            continue

        try:
            for path in root.rglob("*.db"):
                if any(part in EXCLUDED_PARTS for part in path.parts):
                    continue
                if "backup" in path.name.lower():
                    continue
                candidates.append(path)
        except Exception:
            pass

    if not candidates:
        return None

    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


DB_PATH = find_database()


# ---------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------

def money(value) -> float:
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def qty(value) -> float:
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def fmt_money(value) -> str:
    return f"₦{money(value):,.2f}"


def fmt_qty(value) -> str:
    return f"{qty(value):,.2f}"


def normalize_text(value) -> str:
    if value is None:
        return ""
    return str(value).strip().upper()


def date_key(value) -> str:
    if value is None:
        return ""

    text = str(value).strip()

    if not text:
        return ""

    # ISO datetime
    if "T" in text:
        return text.split("T")[0]

    # SQLite timestamp with space
    if " " in text:
        return text.split(" ")[0]

    # Already date-like
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        return text[:10]

    return text


def close_connection(conn):
    try:
        conn.close()
    except Exception:
        pass


def table_exists(conn, table_name: str) -> bool:
    row = conn.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type='table'
          AND name=?
        LIMIT 1
        """,
        (table_name,),
    ).fetchone()

    return row is not None


def get_columns(conn, table_name: str) -> set[str]:
    try:
        rows = conn.execute(
            f"PRAGMA table_info({table_name})"
        ).fetchall()

        return {row[1] for row in rows}
    except Exception:
        return set()


def print_header(title: str):
    print("=" * 60)
    print(title)
    print("=" * 60)


# ---------------------------------------------------------------------
# SAFE CONNECTION
# ---------------------------------------------------------------------

if DB_PATH is None:
    print("=" * 60)
    print("POS LEDGER NG V94")
    print("TRANSACTION ↔ INVENTORY AUDIT & REPAIR-PLAN INTELLIGENCE")
    print("=" * 60)
    print()
    print("DATABASE STATUS")
    print("=" * 60)
    print("❌ No SQLite database detected.")
    print()
    print("No database was modified.")
    raise SystemExit(1)


try:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
except Exception as exc:
    print("=" * 60)
    print("POS LEDGER NG V94")
    print("DATABASE CONNECTION FAILURE")
    print("=" * 60)
    print(f"Database: {DB_PATH}")
    print(f"Error   : {exc}")
    raise SystemExit(1)


# ---------------------------------------------------------------------
# START
# ---------------------------------------------------------------------

print("=" * 60)
print("POS LEDGER NG V94")
print("TRANSACTION ↔ INVENTORY AUDIT & REPAIR-PLAN INTELLIGENCE")
print("=" * 60)
print()

print("=" * 60)
print("DATABASE")
print("=" * 60)
print(f"Database path : {DB_PATH}")
print("Database mode : READ-ONLY")
print()


# ---------------------------------------------------------------------
# STRUCTURE DETECTION
# ---------------------------------------------------------------------

required_tables = [
    "sales",
    "products",
    "inventory_movements",
    "purchases",
]

for table in required_tables:
    status = "AVAILABLE" if table_exists(conn, table) else "NOT DETECTED"
    print(f"{table:<22}: {status}")

print()

if not table_exists(conn, "sales"):
    print("❌ sales table is required.")
    close_connection(conn)
    raise SystemExit(1)

if not table_exists(conn, "products"):
    print("❌ products table is required.")
    close_connection(conn)
    raise SystemExit(1)

if not table_exists(conn, "inventory_movements"):
    print("❌ inventory_movements table is required.")
    close_connection(conn)
    raise SystemExit(1)

sales_cols = get_columns(conn, "sales")
product_cols = get_columns(conn, "products")
inventory_cols = get_columns(conn, "inventory_movements")
purchase_cols = get_columns(conn, "purchases")


# ---------------------------------------------------------------------
# SALES AUDIT
# ---------------------------------------------------------------------

sales = []

sales_query = """
SELECT *
FROM sales
WHERE UPPER(COALESCE(status, 'COMPLETED')) = 'COMPLETED'
ORDER BY id
"""

try:
    sales_rows = conn.execute(sales_query).fetchall()
except Exception:
    sales_rows = conn.execute(
        "SELECT * FROM sales ORDER BY id"
    ).fetchall()


for row in sales_rows:
    sale = dict(row)

    sale["id"] = row["id"]
    sale["product_id"] = row["product_id"] if "product_id" in sales_cols else None
    sale["quantity"] = qty(row["quantity"]) if "quantity" in sales_cols else 0
    sale["receipt_no"] = (
        row["receipt_no"] if "receipt_no" in sales_cols else None
    )
    sale["sale_date"] = (
        row["sale_date"] if "sale_date" in sales_cols else None
    )

    sales.append(sale)


# ---------------------------------------------------------------------
# PRODUCTS
# ---------------------------------------------------------------------

products = {}

if table_exists(conn, "products"):
    product_rows = conn.execute(
        "SELECT * FROM products"
    ).fetchall()

    for row in product_rows:
        product = dict(row)
        products[row["id"]] = product


def product_name(product_id):
    product = products.get(product_id)

    if not product:
        return f"Product #{product_id}"

    return product.get("product_name") or f"Product #{product_id}"


def product_sku(product_id):
    product = products.get(product_id)

    if not product:
        return ""

    return product.get("sku") or ""


# ---------------------------------------------------------------------
# INVENTORY MOVEMENTS
# ---------------------------------------------------------------------

inventory_rows = conn.execute(
    """
    SELECT *
    FROM inventory_movements
    ORDER BY id
    """
).fetchall()


inventory_sales = []
inventory_purchases = []

for row in inventory_rows:
    movement = dict(row)

    movement["id"] = row["id"]
    movement["product_id"] = row["product_id"]
    movement["quantity"] = qty(row["quantity"])
    movement["movement_type"] = (
        normalize_text(row["movement_type"])
        if "movement_type" in inventory_cols
        else ""
    )
    movement["reference"] = (
        row["reference"]
        if "reference" in inventory_cols
        else None
    )
    movement["movement_date"] = (
        row["movement_date"]
        if "movement_date" in inventory_cols
        else None
    )

    movement_type = movement["movement_type"]

    if movement_type == "SALE":
        inventory_sales.append(movement)

    elif movement_type in {
        "PURCHASE",
        "PURCHASES",
        "IN",
        "STOCK_IN",
        "STOCK PURCHASE",
        "PURCHASE_IN",
    }:
        inventory_purchases.append(movement)


# ---------------------------------------------------------------------
# PURCHASE RECORDS
# ---------------------------------------------------------------------

purchases = []

if table_exists(conn, "purchases"):
    purchase_rows = conn.execute(
        """
        SELECT *
        FROM purchases
        ORDER BY id
        """
    ).fetchall()

    for row in purchase_rows:
        purchase = dict(row)

        purchase["id"] = row["id"]
        purchase["product_id"] = (
            row["product_id"]
            if "product_id" in purchase_cols
            else None
        )
        purchase["quantity"] = (
            qty(row["quantity"])
            if "quantity" in purchase_cols
            else 0
        )
        purchase["purchase_no"] = (
            row["purchase_no"]
            if "purchase_no" in purchase_cols
            else None
        )
        purchase["purchase_date"] = (
            row["purchase_date"]
            if "purchase_date" in purchase_cols
            else None
        )

        purchases.append(purchase)


# ---------------------------------------------------------------------
# MATCHING ENGINE
# ---------------------------------------------------------------------

def same_product(a, b):
    return a.get("product_id") == b.get("product_id")


def same_quantity(a, b, tolerance=0.0001):
    return abs(
        qty(a.get("quantity")) - qty(b.get("quantity"))
    ) <= tolerance


def same_reference(a, b):
    ref_a = normalize_text(
        a.get("receipt_no")
        or a.get("purchase_no")
        or a.get("reference")
    )

    ref_b = normalize_text(
        b.get("reference")
        or b.get("receipt_no")
        or b.get("purchase_no")
    )

    if not ref_a or not ref_b:
        return False

    return ref_a == ref_b


def same_date(a, b):
    da = date_key(
        a.get("sale_date")
        or a.get("purchase_date")
        or a.get("movement_date")
    )

    db = date_key(
        b.get("movement_date")
        or b.get("sale_date")
        or b.get("purchase_date")
    )

    if not da or not db:
        return False

    return da == db


def match_sale_to_inventory(sale, movements, used):
    candidates = [
        movement
        for movement in movements
        if movement["id"] not in used
        and same_product(sale, movement)
    ]

    if not candidates:
        return None, "NO_PRODUCT_MATCH"

    # Highest-confidence match:
    # reference + product + quantity
    for movement in candidates:
        if (
            same_reference(sale, movement)
            and same_quantity(sale, movement)
        ):
            return movement, "REFERENCE_PRODUCT_QUANTITY"

    # Product + quantity + date
    for movement in candidates:
        if (
            same_quantity(sale, movement)
            and same_date(sale, movement)
        ):
            return movement, "PRODUCT_QUANTITY_DATE"

    # Product + quantity only.
    # This is NOT automatically considered safe.
    quantity_candidates = [
        movement
        for movement in candidates
        if same_quantity(sale, movement)
    ]

    if len(quantity_candidates) == 1:
        return quantity_candidates[0], "PRODUCT_QUANTITY_ONLY"

    if len(quantity_candidates) > 1:
        return None, "AMBIGUOUS_PRODUCT_QUANTITY"

    return None, "NO_SAFE_MATCH"


def match_purchase_to_inventory(purchase, movements, used):
    candidates = [
        movement
        for movement in movements
        if movement["id"] not in used
        and same_product(purchase, movement)
    ]

    if not candidates:
        return None, "NO_PRODUCT_MATCH"

    # Purchase reference is strongest.
    for movement in candidates:
        if (
            same_reference(purchase, movement)
            and same_quantity(purchase, movement)
        ):
            return movement, "REFERENCE_PRODUCT_QUANTITY"

    # Product + quantity + date.
    for movement in candidates:
        if (
            same_quantity(purchase, movement)
            and same_date(purchase, movement)
        ):
            return movement, "PRODUCT_QUANTITY_DATE"

    quantity_candidates = [
        movement
        for movement in candidates
        if same_quantity(purchase, movement)
    ]

    if len(quantity_candidates) == 1:
        return quantity_candidates[0], "PRODUCT_QUANTITY_ONLY"

    if len(quantity_candidates) > 1:
        return None, "AMBIGUOUS_PRODUCT_QUANTITY"

    return None, "NO_SAFE_MATCH"


# ---------------------------------------------------------------------
# SALE MATCH RESULTS
# ---------------------------------------------------------------------

sale_matches = []
used_inventory_sale_ids = set()

for sale in sales:
    movement, method = match_sale_to_inventory(
        sale,
        inventory_sales,
        used_inventory_sale_ids,
    )

    if movement:
        used_inventory_sale_ids.add(movement["id"])

    sale_matches.append(
        {
            "sale": sale,
            "movement": movement,
            "method": method,
        }
    )


# ---------------------------------------------------------------------
# PURCHASE MATCH RESULTS
# ---------------------------------------------------------------------

purchase_matches = []
used_inventory_purchase_ids = set()

for purchase in purchases:
    movement, method = match_purchase_to_inventory(
        purchase,
        inventory_purchases,
        used_inventory_purchase_ids,
    )

    if movement:
        used_inventory_purchase_ids.add(movement["id"])

    purchase_matches.append(
        {
            "purchase": purchase,
            "movement": movement,
            "method": method,
        }
    )


# ---------------------------------------------------------------------
# MATCH QUALITY COUNTS
# ---------------------------------------------------------------------

sale_reference_matches = 0
sale_strong_matches = 0
sale_weak_matches = 0
sale_ambiguous = 0
sale_unmatched = 0

for result in sale_matches:
    method = result["method"]

    if method == "REFERENCE_PRODUCT_QUANTITY":
        sale_reference_matches += 1
        sale_strong_matches += 1

    elif method == "PRODUCT_QUANTITY_DATE":
        sale_strong_matches += 1

    elif method == "PRODUCT_QUANTITY_ONLY":
        sale_weak_matches += 1

    elif method == "AMBIGUOUS_PRODUCT_QUANTITY":
        sale_ambiguous += 1

    else:
        sale_unmatched += 1


purchase_reference_matches = 0
purchase_strong_matches = 0
purchase_weak_matches = 0
purchase_ambiguous = 0
purchase_unmatched = 0

for result in purchase_matches:
    method = result["method"]

    if method == "REFERENCE_PRODUCT_QUANTITY":
        purchase_reference_matches += 1
        purchase_strong_matches += 1

    elif method == "PRODUCT_QUANTITY_DATE":
        purchase_strong_matches += 1

    elif method == "PRODUCT_QUANTITY_ONLY":
        purchase_weak_matches += 1

    elif method == "AMBIGUOUS_PRODUCT_QUANTITY":
        purchase_ambiguous += 1

    else:
        purchase_unmatched += 1


# ---------------------------------------------------------------------
# UNMATCHED INVENTORY
# ---------------------------------------------------------------------

matched_sale_inventory_ids = {
    result["movement"]["id"]
    for result in sale_matches
    if result["movement"]
}

matched_purchase_inventory_ids = {
    result["movement"]["id"]
    for result in purchase_matches
    if result["movement"]
}

orphan_sale_movements = [
    movement
    for movement in inventory_sales
    if movement["id"] not in matched_sale_inventory_ids
]

orphan_purchase_movements = [
    movement
    for movement in inventory_purchases
    if movement["id"] not in matched_purchase_inventory_ids
]


# ---------------------------------------------------------------------
# PRODUCT RECONCILIATION
# ---------------------------------------------------------------------

sales_by_product = defaultdict(float)
inventory_sale_by_product = defaultdict(float)

purchase_by_product = defaultdict(float)
inventory_purchase_by_product = defaultdict(float)

for sale in sales:
    sales_by_product[sale["product_id"]] += sale["quantity"]

for movement in inventory_sales:
    inventory_sale_by_product[movement["product_id"]] += movement["quantity"]

for purchase in purchases:
    purchase_by_product[purchase["product_id"]] += purchase["quantity"]

for movement in inventory_purchases:
    inventory_purchase_by_product[movement["product_id"]] += movement["quantity"]


product_ids = sorted(
    set(sales_by_product)
    | set(inventory_sale_by_product)
    | set(purchase_by_product)
    | set(inventory_purchase_by_product)
)


# ---------------------------------------------------------------------
# REPORT
# ---------------------------------------------------------------------

print("=" * 60)
print("TRANSACTION AUDIT SUMMARY")
print("=" * 60)
print(f"Completed sales              : {len(sales)}")
print(f"Inventory SALE movements    : {len(inventory_sales)}")
print(f"Purchase records             : {len(purchases)}")
print(f"Inventory PURCHASE movements : {len(inventory_purchases)}")
print()

print("=" * 60)
print("SALE MATCH QUALITY")
print("=" * 60)
print(f"Reference matches            : {sale_reference_matches}")
print(f"Strong matches               : {sale_strong_matches}")
print(f"Weak matches                 : {sale_weak_matches}")
print(f"Ambiguous sales              : {sale_ambiguous}")
print(f"Unmatched sales              : {sale_unmatched}")
print()


print("=" * 60)
print("PURCHASE MATCH QUALITY")
print("=" * 60)
print(f"Reference matches            : {purchase_reference_matches}")
print(f"Strong matches               : {purchase_strong_matches}")
print(f"Weak matches                 : {purchase_weak_matches}")
print(f"Ambiguous purchases          : {purchase_ambiguous}")
print(f"Unmatched purchases          : {purchase_unmatched}")
print()


# ---------------------------------------------------------------------
# INDIVIDUAL SALE AUDIT
# ---------------------------------------------------------------------

print("=" * 60)
print("INDIVIDUAL SALE AUDIT")
print("=" * 60)

for result in sale_matches:
    sale = result["sale"]
    movement = result["movement"]
    method = result["method"]

    print("----------------------------------------")
    print(f"Sale ID             : {sale['id']}")
    print(f"Receipt             : {sale.get('receipt_no') or 'NOT RECORDED'}")
    print(f"Product             : {product_name(sale['product_id'])}")
    print(f"Quantity            : {fmt_qty(sale['quantity'])}")
    print(f"Sale date           : {sale.get('sale_date') or 'NOT RECORDED'}")

    if movement:
        print(f"Inventory movement  : {movement['id']}")
        print(f"Inventory quantity  : {fmt_qty(movement['quantity'])}")
        print(f"Inventory reference : {movement.get('reference') or 'NOT RECORDED'}")
        print(f"Inventory date      : {movement.get('movement_date') or 'NOT RECORDED'}")
        print(f"Match method        : {method}")

        if method == "PRODUCT_QUANTITY_ONLY":
            print("Audit status        : 🟡 WEAK MATCH — MANUAL REVIEW")

        else:
            print("Audit status        : 🟢 MATCHED")

    else:
        print("Inventory movement  : NONE")
        print(f"Match method        : {method}")
        print("Audit status        : 🔴 UNMATCHED")


# ---------------------------------------------------------------------
# INDIVIDUAL PURCHASE AUDIT
# ---------------------------------------------------------------------

print()
print("=" * 60)
print("INDIVIDUAL PURCHASE AUDIT")
print("=" * 60)

for result in purchase_matches:
    purchase = result["purchase"]
    movement = result["movement"]
    method = result["method"]

    print("----------------------------------------")
    print(f"Purchase ID         : {purchase['id']}")
    print(f"Purchase No         : {purchase.get('purchase_no') or 'NOT RECORDED'}")
    print(f"Product             : {product_name(purchase['product_id'])}")
    print(f"Quantity            : {fmt_qty(purchase['quantity'])}")
    print(f"Purchase date       : {purchase.get('purchase_date') or 'NOT RECORDED'}")

    if movement:
        print(f"Inventory movement  : {movement['id']}")
        print(f"Inventory quantity  : {fmt_qty(movement['quantity'])}")
        print(f"Inventory reference : {movement.get('reference') or 'NOT RECORDED'}")
        print(f"Inventory date      : {movement.get('movement_date') or 'NOT RECORDED'}")
        print(f"Match method        : {method}")

        if method == "PRODUCT_QUANTITY_ONLY":
            print("Audit status        : 🟡 WEAK MATCH — MANUAL REVIEW")
        else:
            print("Audit status        : 🟢 MATCHED")

    else:
        print("Inventory movement  : NONE")
        print(f"Match method        : {method}")
        print("Audit status        : 🔴 UNMATCHED")


# ---------------------------------------------------------------------
# PRODUCT-LEVEL AUDIT
# ---------------------------------------------------------------------

print()
print("=" * 60)
print("PRODUCT-LEVEL RECONCILIATION")
print("=" * 60)

for product_id in product_ids:
    sales_units = sales_by_product[product_id]
    inventory_sale_units = inventory_sale_by_product[product_id]

    purchase_units = purchase_by_product[product_id]
    inventory_purchase_units = inventory_purchase_by_product[product_id]

    sale_difference = sales_units - inventory_sale_units
    purchase_difference = purchase_units - inventory_purchase_units

    print("----------------------------------------")
    print(f"Product ID             : {product_id}")
    print(f"Product                : {product_name(product_id)}")
    print(f"SKU                    : {product_sku(product_id) or 'NOT RECORDED'}")
    print(f"Sales units             : {fmt_qty(sales_units)}")
    print(f"Inventory SALE units   : {fmt_qty(inventory_sale_units)}")
    print(f"SALE difference        : {fmt_qty(sale_difference)}")
    print(f"Purchase units         : {fmt_qty(purchase_units)}")
    print(f"Inventory IN units     : {fmt_qty(inventory_purchase_units)}")
    print(f"Purchase difference    : {fmt_qty(purchase_difference)}")

    if abs(sale_difference) < 0.0001:
        print("SALE status            : 🟢 RECONCILED")
    else:
        print("SALE status            : 🔴 MISMATCH")

    if abs(purchase_difference) < 0.0001:
        print("PURCHASE status        : 🟢 RECONCILED")
    else:
        print("PURCHASE status        : 🟠 REVIEW")


# ---------------------------------------------------------------------
# ORPHAN MOVEMENTS
# ---------------------------------------------------------------------

print()
print("=" * 60)
print("ORPHAN INVENTORY MOVEMENTS")
print("=" * 60)

print(f"Orphan SALE movements     : {len(orphan_sale_movements)}")

for movement in orphan_sale_movements:
    print("----------------------------------------")
    print(f"Movement ID         : {movement['id']}")
    print(f"Product             : {product_name(movement['product_id'])}")
    print(f"Quantity            : {fmt_qty(movement['quantity'])}")
    print(f"Reference           : {movement.get('reference') or 'NONE'}")
    print(f"Movement date       : {movement.get('movement_date') or 'NONE'}")


print()
print(f"Orphan PURCHASE movements : {len(orphan_purchase_movements)}")

for movement in orphan_purchase_movements:
    print("----------------------------------------")
    print(f"Movement ID         : {movement['id']}")
    print(f"Product             : {product_name(movement['product_id'])}")
    print(f"Quantity            : {fmt_qty(movement['quantity'])}")
    print(f"Reference           : {movement.get('reference') or 'NONE'}")
    print(f"Movement date       : {movement.get('movement_date') or 'NONE'}")


# ---------------------------------------------------------------------
# REPAIR PLAN
# ---------------------------------------------------------------------

repair_items = []

for result in sale_matches:
    sale = result["sale"]
    movement = result["movement"]
    method = result["method"]

    if movement:
        if method == "PRODUCT_QUANTITY_ONLY":
            repair_items.append(
                {
                    "type": "SALE_WEAK_MATCH",
                    "id": sale["id"],
                    "description": (
                        f"Sale {sale['id']} matches inventory movement "
                        f"{movement['id']} only by product and quantity."
                    ),
                }
            )
    else:
        repair_items.append(
            {
                "type": "SALE_UNMATCHED",
                "id": sale["id"],
                "description": (
                    f"Sale {sale['id']} has no safe inventory SALE match."
                ),
            }
        )


for result in purchase_matches:
    purchase = result["purchase"]
    movement = result["movement"]
    method = result["method"]

    if movement:
        if method == "PRODUCT_QUANTITY_ONLY":
            repair_items.append(
                {
                    "type": "PURCHASE_WEAK_MATCH",
                    "id": purchase["id"],
                    "description": (
                        f"Purchase {purchase['id']} matches inventory "
                        f"movement {movement['id']} only by product and quantity."
                    ),
                }
            )
    else:
        repair_items.append(
            {
                "type": "PURCHASE_UNMATCHED",
                "id": purchase["id"],
                "description": (
                    f"Purchase {purchase['id']} has no safe inventory "
                    f"PURCHASE match."
                ),
            }
        )


for movement in orphan_sale_movements:
    repair_items.append(
        {
            "type": "ORPHAN_SALE_MOVEMENT",
            "id": movement["id"],
            "description": (
                f"Inventory SALE movement {movement['id']} has no "
                f"corresponding transaction match."
            ),
        }
    )


for movement in orphan_purchase_movements:
    repair_items.append(
        {
            "type": "ORPHAN_PURCHASE_MOVEMENT",
            "id": movement["id"],
            "description": (
                f"Inventory PURCHASE movement {movement['id']} has no "
                f"corresponding purchase match."
            ),
        }
    )


print()
print("=" * 60)
print("V94 REPAIR PLAN")
print("=" * 60)

if not repair_items:
    print("🟢 No unresolved transaction/inventory repair candidates detected.")
else:
    print(f"Repair-review candidates : {len(repair_items)}")
    print()

    for index, item in enumerate(repair_items, start=1):
        print(
            f"{index}. [{item['type']}] "
            f"Record {item['id']}"
        )
        print(f"   {item['description']}")


# ---------------------------------------------------------------------
# REPAIR READINESS
# ---------------------------------------------------------------------

high_risk = (
    sale_unmatched
    + sale_ambiguous
    + purchase_unmatched
    + purchase_ambiguous
    + len(orphan_sale_movements)
    + len(orphan_purchase_movements)
)

weak_matches = sale_weak_matches + purchase_weak_matches


print()
print("=" * 60)
print("V94 REPAIR READINESS")
print("=" * 60)

if high_risk > 0:
    print("Status : 🔴 NOT READY")
    print()
    print(
        "Exact transaction-to-inventory relationships remain unresolved."
    )
    print(
        "Automatic database repair is prohibited."
    )

elif weak_matches > 0:
    print("Status : 🟡 MANUAL REVIEW REQUIRED")
    print()
    print(
        "Some records can only be matched using weak evidence."
    )
    print(
        "Automatic repair is prohibited."
    )

else:
    print("Status : 🟢 AUDITALLY RECONCILED")
    print()
    print(
        "All transaction/inventory relationships have a sufficiently "
        "strong match."
    )
    print(
        "V94 still performs no database modifications."
    )


# ---------------------------------------------------------------------
# EXECUTIVE DECISION
# ---------------------------------------------------------------------

print()
print("=" * 60)
print("V94 EXECUTIVE DECISION")
print("=" * 60)

if high_risk > 0:
    print("🔴 STOP — TRANSACTION HISTORY REQUIRES INVESTIGATION")
elif weak_matches > 0:
    print("🟡 REVIEW — SOME MATCHES REQUIRE HUMAN CONFIRMATION")
else:
    print("🟢 RECONCILIATION EVIDENCE ACCEPTABLE")


# ---------------------------------------------------------------------
# MANAGEMENT INTERPRETATION
# ---------------------------------------------------------------------

print()
print("=" * 60)
print("V94 MANAGEMENT INTERPRETATION")
print("=" * 60)

print(
    "V94 converts the V93 diagnostic findings into an individual "
    "transaction-level audit."
)

print(
    "It distinguishes strong evidence, weak evidence, ambiguous "
    "evidence and completely unmatched records."
)

print(
    "No inventory movement, sale, purchase or financial record is "
    "created, deleted or modified."
)

print(
    "A future repair module must only act on explicitly verified "
    "repair candidates."
)


# ---------------------------------------------------------------------
# DATA INTEGRITY STATUS
# ---------------------------------------------------------------------

print()
print("=" * 60)
print("V94 DATA INTEGRITY STATUS")
print("=" * 60)

print(f"Sales records audited        : {len(sales)}")
print(f"Inventory SALE records       : {len(inventory_sales)}")
print(f"Purchase records audited     : {len(purchases)}")
print(f"Inventory PURCHASE records   : {len(inventory_purchases)}")
print(f"Strong sale matches          : {sale_strong_matches}")
print(f"Weak sale matches            : {sale_weak_matches}")
print(f"Ambiguous sales              : {sale_ambiguous}")
print(f"Unmatched sales              : {sale_unmatched}")
print(f"Strong purchase matches     : {purchase_strong_matches}")
print(f"Weak purchase matches        : {purchase_weak_matches}")
print(f"Ambiguous purchases          : {purchase_ambiguous}")
print(f"Unmatched purchases          : {purchase_unmatched}")


# ---------------------------------------------------------------------
# SAFETY
# ---------------------------------------------------------------------

print()
print("=" * 60)
print("V94 SAFETY STATUS")
print("=" * 60)

print("Mode                  : READ-ONLY")
print("Database modified     : NO")
print("Sales modified        : NO")
print("Products modified     : NO")
print("Inventory modified    : NO")
print("Purchases modified    : NO")
print("Balance modified      : NO")
print("Credit modified       : NO")
print("Suppliers modified    : NO")
print("Expenses modified     : NO")
print("=" * 60)


# ---------------------------------------------------------------------
# CLOSE
# ---------------------------------------------------------------------

close_connection(conn)
