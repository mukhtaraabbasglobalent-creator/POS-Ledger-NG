"""
POS LEDGER NG V95
CONTROLLED TRANSACTION & INVENTORY REPAIR-PLAN INTELLIGENCE

READ-ONLY ONLY.
This module NEVER modifies the database.

Purpose:
1. Audit completed sales against inventory SALE movements.
2. Audit purchases against inventory PURCHASE/IN movements.
3. Identify safe, weak, ambiguous, and unmatched relationships.
4. Generate repair candidates WITHOUT applying repairs.
5. Create a backup-free repair plan only; actual repair belongs to a later
   explicitly approved phase.
"""

from __future__ import annotations

import os
import sqlite3
from collections import defaultdict
from datetime import datetime


DB_PATH = os.path.expanduser("~/POS-Ledger-NG/data/posledger.db")

SEP = "=" * 60
SUB = "-" * 40


def money(value):
    try:
        return f"₦{float(value or 0):,.2f}"
    except Exception:
        return "₦0.00"


def num(value):
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def table_exists(conn, table):
    row = conn.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None


def columns(conn, table):
    if not table_exists(conn, table):
        return set()
    return {
        row[1]
        for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
    }


def first_existing(cols, names):
    for name in names:
        if name in cols:
            return name
    return None


def load_sales(conn):
    if not table_exists(conn, "sales"):
        return []

    cols = columns(conn, "sales")

    product_col = first_existing(cols, ["product_id"])
    quantity_col = first_existing(cols, ["quantity"])
    date_col = first_existing(cols, ["sale_date", "created_at", "date"])
    receipt_col = first_existing(cols, ["receipt_no", "receipt", "reference"])
    status_col = first_existing(cols, ["status"])

    if not product_col or not quantity_col:
        return []

    query = (
        "SELECT id, "
        f"{product_col}, "
        f"{quantity_col}, "
        f"{date_col if date_col else 'NULL'}, "
        f"{receipt_col if receipt_col else 'NULL'}, "
        f"{status_col if status_col else 'NULL'} "
        "FROM sales"
    )

    rows = conn.execute(query).fetchall()

    result = []

    for row in rows:
        sale_id, product_id, quantity, sale_date, receipt, status = row

        if status_col:
            if str(status or "").upper() not in ("", "COMPLETED"):
                continue

        result.append(
            {
                "id": sale_id,
                "product_id": product_id,
                "quantity": num(quantity),
                "date": sale_date,
                "receipt": receipt,
            }
        )

    return result


def load_purchases(conn):
    if not table_exists(conn, "purchases"):
        return []

    cols = columns(conn, "purchases")

    product_col = first_existing(cols, ["product_id"])
    quantity_col = first_existing(cols, ["quantity"])
    date_col = first_existing(
        cols, ["purchase_date", "created_at", "date"]
    )
    purchase_no_col = first_existing(
        cols, ["purchase_no", "reference", "purchase_reference"]
    )

    if not product_col or not quantity_col:
        return []

    query = (
        "SELECT id, "
        f"{product_col}, "
        f"{quantity_col}, "
        f"{date_col if date_col else 'NULL'}, "
        f"{purchase_no_col if purchase_no_col else 'NULL'} "
        "FROM purchases"
    )

    result = []

    for row in conn.execute(query).fetchall():
        purchase_id, product_id, quantity, purchase_date, purchase_no = row

        result.append(
            {
                "id": purchase_id,
                "product_id": product_id,
                "quantity": num(quantity),
                "date": purchase_date,
                "reference": purchase_no,
            }
        )

    return result


def load_products(conn):
    if not table_exists(conn, "products"):
        return {}

    cols = columns(conn, "products")

    name_col = first_existing(cols, ["product_name", "name"])
    sku_col = first_existing(cols, ["sku"])

    select_name = name_col if name_col else "NULL"
    select_sku = sku_col if sku_col else "NULL"

    rows = conn.execute(
        f"SELECT id, {select_name}, {select_sku}, "
        "current_stock "
        "FROM products"
    ).fetchall()

    return {
        row[0]: {
            "name": row[1] or "UNKNOWN",
            "sku": row[2] or "",
            "stock": num(row[3]),
        }
        for row in rows
    }


def load_movements(conn):
    if not table_exists(conn, "inventory_movements"):
        return []

    cols = columns(conn, "inventory_movements")

    type_col = first_existing(cols, ["movement_type", "type"])
    product_col = first_existing(cols, ["product_id"])
    quantity_col = first_existing(cols, ["quantity"])
    date_col = first_existing(
        cols, ["movement_date", "created_at", "date"]
    )
    reference_col = first_existing(
        cols, ["reference", "receipt_no", "purchase_no"]
    )

    if not type_col or not product_col or not quantity_col:
        return []

    query = (
        "SELECT id, "
        f"{product_col}, "
        f"{type_col}, "
        f"{quantity_col}, "
        f"{date_col if date_col else 'NULL'}, "
        f"{reference_col if reference_col else 'NULL'} "
        "FROM inventory_movements "
        "ORDER BY id"
    )

    result = []

    for row in conn.execute(query).fetchall():
        movement_id, product_id, movement_type, quantity, date, reference = row

        result.append(
            {
                "id": movement_id,
                "product_id": product_id,
                "type": str(movement_type or "").upper(),
                "quantity": num(quantity),
                "date": date,
                "reference": reference,
            }
        )

    return result


def date_key(value):
    if not value:
        return ""

    text = str(value)

    # SQLite timestamps normally begin with YYYY-MM-DD.
    return text[:10]


def reference_key(value):
    if value is None:
        return ""

    return str(value).strip().upper()


def classify_sale(sale, movements):
    """
    Returns:
        SAFE
        WEAK
        AMBIGUOUS
        UNMATCHED
    """

    candidates = [
        m
        for m in movements
        if m["type"] in ("SALE", "OUT", "SALE_OUT")
        and m["product_id"] == sale["product_id"]
    ]

    if not candidates:
        return "UNMATCHED", None, "NO_PRODUCT_MATCH"

    sale_ref = reference_key(sale["receipt"])

    # 1. Exact reference + product + quantity.
    if sale_ref:
        exact = [
            m for m in candidates
            if reference_key(m["reference"]) == sale_ref
            and abs(m["quantity"] - sale["quantity"]) < 0.000001
        ]

        if len(exact) == 1:
            return "SAFE", exact[0], "REFERENCE_PRODUCT_QUANTITY"

        if len(exact) > 1:
            return "AMBIGUOUS", None, "DUPLICATE_REFERENCE_MATCH"

    # 2. Product + quantity + exact date.
    exact_date = [
        m for m in candidates
        if abs(m["quantity"] - sale["quantity"]) < 0.000001
        and date_key(m["date"]) == date_key(sale["date"])
    ]

    if len(exact_date) == 1:
        return "SAFE", exact_date[0], "PRODUCT_QUANTITY_DATE"

    if len(exact_date) > 1:
        return "AMBIGUOUS", None, "MULTIPLE_DATE_MATCHES"

    # 3. Product + quantity only.
    quantity_matches = [
        m for m in candidates
        if abs(m["quantity"] - sale["quantity"]) < 0.000001
    ]

    if len(quantity_matches) == 1:
        return "WEAK", quantity_matches[0], "PRODUCT_QUANTITY_ONLY"

    if len(quantity_matches) > 1:
        return "AMBIGUOUS", None, "MULTIPLE_QUANTITY_MATCHES"

    return "UNMATCHED", None, "NO_SAFE_MATCH"


def classify_purchase(purchase, movements):
    candidates = [
        m
        for m in movements
        if m["type"] in ("PURCHASE", "IN", "STOCK_IN")
        and m["product_id"] == purchase["product_id"]
    ]

    if not candidates:
        return "UNMATCHED", None, "NO_PRODUCT_MATCH"

    purchase_ref = reference_key(purchase["reference"])

    if purchase_ref:
        exact = [
            m for m in candidates
            if reference_key(m["reference"]) == purchase_ref
            and abs(m["quantity"] - purchase["quantity"]) < 0.000001
        ]

        if len(exact) == 1:
            return "SAFE", exact[0], "REFERENCE_PRODUCT_QUANTITY"

        if len(exact) > 1:
            return "AMBIGUOUS", None, "DUPLICATE_REFERENCE_MATCH"

    exact_date = [
        m for m in candidates
        if abs(m["quantity"] - purchase["quantity"]) < 0.000001
        and date_key(m["date"]) == date_key(purchase["date"])
    ]

    if len(exact_date) == 1:
        return "SAFE", exact_date[0], "PRODUCT_QUANTITY_DATE"

    if len(exact_date) > 1:
        return "AMBIGUOUS", None, "MULTIPLE_DATE_MATCHES"

    quantity_matches = [
        m for m in candidates
        if abs(m["quantity"] - purchase["quantity"]) < 0.000001
    ]

    if len(quantity_matches) == 1:
        return "WEAK", quantity_matches[0], "PRODUCT_QUANTITY_ONLY"

    if len(quantity_matches) > 1:
        return "AMBIGUOUS", None, "MULTIPLE_QUANTITY_MATCHES"

    return "UNMATCHED", None, "NO_SAFE_MATCH"


def main():
    print(SEP)
    print("POS LEDGER NG V95")
    print("CONTROLLED TRANSACTION & INVENTORY REPAIR-PLAN INTELLIGENCE")
    print(SEP)
    print()

    print(SEP)
    print("DATABASE SAFETY")
    print(SEP)
    print(f"Database path : {DB_PATH}")
    print("Database mode : READ-ONLY")
    print("Automatic repair : DISABLED")
    print()

    if not os.path.exists(DB_PATH):
        print("ERROR: Database not found.")
        return

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)

    try:
        required = [
            "sales",
            "products",
            "inventory_movements",
            "purchases",
        ]

        print(SEP)
        print("DATABASE STRUCTURE")
        print(SEP)

        for table in required:
            print(
                f"{table:<22}: "
                f"{'AVAILABLE' if table_exists(conn, table) else 'NOT DETECTED'}"
            )

        print()

        sales = load_sales(conn)
        purchases = load_purchases(conn)
        products = load_products(conn)
        movements = load_movements(conn)

        sale_movements = [
            m for m in movements
            if m["type"] in ("SALE", "OUT", "SALE_OUT")
        ]

        purchase_movements = [
            m for m in movements
            if m["type"] in ("PURCHASE", "IN", "STOCK_IN")
        ]

        print(SEP)
        print("V95 TRANSACTION LINKAGE SUMMARY")
        print(SEP)

        print(f"Completed sales             : {len(sales)}")
        print(f"Inventory SALE movements    : {len(sale_movements)}")
        print(f"Purchase records             : {len(purchases)}")
        print(
            f"Inventory PURCHASE movements : "
            f"{len(purchase_movements)}"
        )
        print()

        sale_results = []
        used_sale_movements = set()

        safe_sales = 0
        weak_sales = 0
        ambiguous_sales = 0
        unmatched_sales = 0

        for sale in sales:
            status, movement, method = classify_sale(
                sale,
                sale_movements,
            )

            if movement:
                used_sale_movements.add(movement["id"])

            sale_results.append(
                (sale, status, movement, method)
            )

            if status == "SAFE":
                safe_sales += 1
            elif status == "WEAK":
                weak_sales += 1
            elif status == "AMBIGUOUS":
                ambiguous_sales += 1
            else:
                unmatched_sales += 1

        purchase_results = []
        used_purchase_movements = set()

        safe_purchases = 0
        weak_purchases = 0
        ambiguous_purchases = 0
        unmatched_purchases = 0

        for purchase in purchases:
            status, movement, method = classify_purchase(
                purchase,
                purchase_movements,
            )

            if movement:
                used_purchase_movements.add(movement["id"])

            purchase_results.append(
                (purchase, status, movement, method)
            )

            if status == "SAFE":
                safe_purchases += 1
            elif status == "WEAK":
                weak_purchases += 1
            elif status == "AMBIGUOUS":
                ambiguous_purchases += 1
            else:
                unmatched_purchases += 1

        print(SEP)
        print("SALE LINKAGE QUALITY")
        print(SEP)
        print(f"Safe matches                : {safe_sales}")
        print(f"Weak matches                : {weak_sales}")
        print(f"Ambiguous sales             : {ambiguous_sales}")
        print(f"Unmatched sales             : {unmatched_sales}")
        print()

        print(SEP)
        print("PURCHASE LINKAGE QUALITY")
        print(SEP)
        print(f"Safe matches                : {safe_purchases}")
        print(f"Weak matches                : {weak_purchases}")
        print(f"Ambiguous purchases         : {ambiguous_purchases}")
        print(f"Unmatched purchases         : {unmatched_purchases}")
        print()

        # ---------------------------------------------------------
        # Repair candidates
        # ---------------------------------------------------------

        candidates = []

        for sale, status, movement, method in sale_results:
            if status == "UNMATCHED":
                candidates.append(
                    {
                        "type": "SALE_UNMATCHED",
                        "record_id": sale["id"],
                        "reason": (
                            f"Sale {sale['id']} has no safe inventory "
                            "SALE relationship."
                        ),
                    }
                )

            elif status == "WEAK":
                candidates.append(
                    {
                        "type": "SALE_WEAK_MATCH",
                        "record_id": sale["id"],
                        "reason": (
                            f"Sale {sale['id']} matches inventory movement "
                            f"{movement['id']} only by {method}."
                        ),
                    }
                )

            elif status == "AMBIGUOUS":
                candidates.append(
                    {
                        "type": "SALE_AMBIGUOUS",
                        "record_id": sale["id"],
                        "reason": (
                            f"Sale {sale['id']} has multiple possible "
                            "inventory relationships."
                        ),
                    }
                )

        for purchase, status, movement, method in purchase_results:
            if status == "UNMATCHED":
                candidates.append(
                    {
                        "type": "PURCHASE_UNMATCHED",
                        "record_id": purchase["id"],
                        "reason": (
                            f"Purchase {purchase['id']} has no safe "
                            "inventory relationship."
                        ),
                    }
                )

            elif status == "WEAK":
                candidates.append(
                    {
                        "type": "PURCHASE_WEAK_MATCH",
                        "record_id": purchase["id"],
                        "reason": (
                            f"Purchase {purchase['id']} matches inventory "
                            f"movement {movement['id']} only by {method}."
                        ),
                    }
                )

            elif status == "AMBIGUOUS":
                candidates.append(
                    {
                        "type": "PURCHASE_AMBIGUOUS",
                        "record_id": purchase["id"],
                        "reason": (
                            f"Purchase {purchase['id']} has multiple "
                            "possible inventory relationships."
                        ),
                    }
                )

        orphan_sale_movements = [
            m for m in sale_movements
            if m["id"] not in used_sale_movements
        ]

        orphan_purchase_movements = [
            m for m in purchase_movements
            if m["id"] not in used_purchase_movements
        ]

        for movement in orphan_sale_movements:
            candidates.append(
                {
                    "type": "ORPHAN_SALE_MOVEMENT",
                    "record_id": movement["id"],
                    "reason": (
                        f"Inventory SALE movement {movement['id']} has "
                        "no transaction match."
                    ),
                }
            )

        for movement in orphan_purchase_movements:
            candidates.append(
                {
                    "type": "ORPHAN_PURCHASE_MOVEMENT",
                    "record_id": movement["id"],
                    "reason": (
                        f"Inventory PURCHASE movement {movement['id']} "
                        "has no transaction match."
                    ),
                }
            )

        # ---------------------------------------------------------
        # Product-level quantity analysis
        # ---------------------------------------------------------

        sales_by_product = defaultdict(float)
        sale_moves_by_product = defaultdict(float)
        purchases_by_product = defaultdict(float)
        purchase_moves_by_product = defaultdict(float)

        for sale in sales:
            sales_by_product[sale["product_id"]] += sale["quantity"]

        for movement in sale_movements:
            sale_moves_by_product[movement["product_id"]] += movement[
                "quantity"
            ]

        for purchase in purchases:
            purchases_by_product[purchase["product_id"]] += purchase[
                "quantity"
            ]

        for movement in purchase_movements:
            purchase_moves_by_product[movement["product_id"]] += movement[
                "quantity"
            ]

        print(SEP)
        print("PRODUCT-LEVEL REPAIR PRESSURE")
        print(SEP)

        total_sale_difference = 0.0
        total_purchase_difference = 0.0

        for product_id in sorted(
            set(products)
            | set(sales_by_product)
            | set(sale_moves_by_product)
            | set(purchases_by_product)
            | set(purchase_moves_by_product)
        ):
            product = products.get(
                product_id,
                {
                    "name": "UNKNOWN",
                    "sku": "",
                    "stock": 0,
                },
            )

            sales_qty = sales_by_product[product_id]
            sale_move_qty = sale_moves_by_product[product_id]
            purchase_qty = purchases_by_product[product_id]
            purchase_move_qty = purchase_moves_by_product[product_id]

            sale_diff = sales_qty - sale_move_qty
            purchase_diff = purchase_qty - purchase_move_qty

            total_sale_difference += abs(sale_diff)
            total_purchase_difference += abs(purchase_diff)

            print(SUB)
            print(f"Product ID             : {product_id}")
            print(f"Product                : {product['name']}")
            print(f"SKU                    : {product['sku']}")
            print(f"Sales units            : {sales_qty:.2f}")
            print(f"Inventory SALE units   : {sale_move_qty:.2f}")
            print(f"SALE difference        : {sale_diff:.2f}")
            print(f"Purchase units         : {purchase_qty:.2f}")
            print(f"Inventory IN units     : {purchase_move_qty:.2f}")
            print(f"Purchase difference    : {purchase_diff:.2f}")

            if abs(sale_diff) < 0.000001:
                print("SALE status             : 🟢 RECONCILED")
            else:
                print("SALE status             : 🔴 REPAIR REVIEW")

            if abs(purchase_diff) < 0.000001:
                print("PURCHASE status         : 🟢 RECONCILED")
            else:
                print("PURCHASE status         : 🟠 REPAIR REVIEW")

        # ---------------------------------------------------------
        # Readiness decision
        # ---------------------------------------------------------

        print()
        print(SEP)
        print("V95 CONTROLLED REPAIR READINESS")
        print(SEP)

        if (
            ambiguous_sales
            or ambiguous_purchases
            or unmatched_sales
            or unmatched_purchases
            or orphan_sale_movements
            or orphan_purchase_movements
        ):
            readiness = "🔴 NOT READY"
            decision = (
                "STOP — EXACT TRANSACTION RELATIONSHIPS "
                "REQUIRE VERIFICATION"
            )
        elif weak_sales or weak_purchases:
            readiness = "🟡 MANUAL REVIEW REQUIRED"
            decision = (
                "REVIEW WEAK MATCHES BEFORE ANY REPAIR"
            )
        else:
            readiness = "🟢 CANDIDATES VERIFIED"
            decision = (
                "REPAIR MAY BE PLANNED, BUT NOT EXECUTED "
                "BY V95"
            )

        print(f"Status : {readiness}")
        print()
        print(
            "V95 does not modify sales, inventory, purchases, "
            "products or financial records."
        )
        print()

        print(SEP)
        print("V95 REPAIR CANDIDATES")
        print(SEP)

        print(f"Candidates requiring review : {len(candidates)}")

        for index, candidate in enumerate(candidates, 1):
            print()
            print(
                f"{index}. [{candidate['type']}] "
                f"Record {candidate['record_id']}"
            )
            print(f"   {candidate['reason']}")

        if not candidates:
            print("No unresolved repair candidates detected.")

        print()
        print(SEP)
        print("V95 EXECUTIVE DECISION")
        print(SEP)
        print(decision)

        print()
        print(SEP)
        print("V95 MANAGEMENT INTERPRETATION")
        print(SEP)
        print(
            "V95 converts the V94 transaction audit into a controlled "
            "repair-readiness assessment."
        )
        print(
            "Only relationships supported by explicit evidence may "
            "eventually become repair candidates."
        )
        print(
            "Weak, ambiguous, unmatched and orphan records remain "
            "blocked from automatic repair."
        )
        print(
            "The purpose of V95 is to prevent an incorrect repair from "
            "destroying historical financial truth."
        )

        print()
        print(SEP)
        print("V95 DATA INTEGRITY STATUS")
        print(SEP)
        print(f"Sales audited              : {len(sales)}")
        print(f"Purchases audited          : {len(purchases)}")
        print(f"Inventory movements        : {len(movements)}")
        print(f"Sale quantity difference   : {total_sale_difference:.2f}")
        print(
            f"Purchase quantity difference: "
            f"{total_purchase_difference:.2f}"
        )
        print(f"Safe sale matches          : {safe_sales}")
        print(f"Weak sale matches          : {weak_sales}")
        print(f"Ambiguous sales            : {ambiguous_sales}")
        print(f"Unmatched sales            : {unmatched_sales}")
        print(f"Safe purchase matches      : {safe_purchases}")
        print(f"Weak purchase matches      : {weak_purchases}")
        print(f"Ambiguous purchases        : {ambiguous_purchases}")
        print(f"Unmatched purchases        : {unmatched_purchases}")
        print(f"Orphan SALE movements      : {len(orphan_sale_movements)}")
        print(
            f"Orphan PURCHASE movements  : "
            f"{len(orphan_purchase_movements)}"
        )

        print()
        print(SEP)
        print("V95 SAFETY STATUS")
        print(SEP)
        print("Mode                  : READ-ONLY")
        print("Database modified     : NO")
        print("Sales modified        : NO")
        print("Sales repaired        : NO")
        print("Products modified     : NO")
        print("Inventory modified    : NO")
        print("Inventory repaired    : NO")
        print("Purchases modified    : NO")
        print("Purchases repaired    : NO")
        print("Balance modified      : NO")
        print("Credit modified       : NO")
        print("Suppliers modified    : NO")
        print("Expenses modified     : NO")
        print(SEP)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
