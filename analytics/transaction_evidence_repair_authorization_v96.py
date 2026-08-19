"""
POS LEDGER NG V96
TRANSACTION EVIDENCE & REPAIR AUTHORIZATION INTELLIGENCE

Purpose:
    Convert V95 blocked repair candidates into an evidence-based
    authorization assessment.

Safety:
    READ-ONLY.
    No INSERT, UPDATE, DELETE, ALTER, DROP, or database writes.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from collections import defaultdict
from datetime import datetime


BASE_DIR = Path.home() / "POS-Ledger-NG"
DB_PATH = BASE_DIR / "data" / "posledger.db"


def money(value):
    try:
        return f"₦{float(value):,.2f}"
    except Exception:
        return "₦0.00"


def num(value):
    try:
        return f"{float(value):,.2f}"
    except Exception:
        return "0.00"


def safe_str(value):
    return "" if value is None else str(value).strip()


def normalize(value):
    return safe_str(value).lower().strip()


def table_exists(conn, table_name):
    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table' AND name=?
        """,
        (table_name,),
    ).fetchone()
    return row is not None


def columns(conn, table_name):
    if not table_exists(conn, table_name):
        return []
    return [
        row[1]
        for row in conn.execute(
            f"PRAGMA table_info({table_name})"
        ).fetchall()
    ]


def first_existing(cols, candidates):
    for candidate in candidates:
        if candidate in cols:
            return candidate
    return None


def fetch_sales(conn):
    if not table_exists(conn, "sales"):
        return []

    cols = columns(conn, "sales")

    id_col = first_existing(cols, ["id", "sale_id"])
    product_col = first_existing(
        cols, ["product_id", "product", "item_id"]
    )
    qty_col = first_existing(
        cols, ["quantity", "qty", "units", "quantity_sold"]
    )
    date_col = first_existing(
        cols, ["created_at", "sale_date", "date", "timestamp"]
    )
    receipt_col = first_existing(
        cols,
        [
            "receipt_number",
            "receipt_no",
            "receipt",
            "reference",
            "transaction_reference",
        ],
    )
    status_col = first_existing(cols, ["status", "sale_status"])

    if not id_col:
        return []

    query = f"SELECT * FROM sales ORDER BY {id_col}"

    rows = conn.execute(query).fetchall()
    result = []

    for row in rows:
        data = dict(zip(cols, row))

        status = normalize(data.get(status_col)) if status_col else ""
        if status and status not in {
            "completed",
            "complete",
            "paid",
            "success",
            "successful",
        }:
            continue

        result.append(
            {
                "id": data.get(id_col),
                "product_id": data.get(product_col)
                if product_col
                else None,
                "quantity": float(data.get(qty_col) or 0)
                if qty_col
                else 0.0,
                "date": data.get(date_col)
                if date_col
                else None,
                "receipt": data.get(receipt_col)
                if receipt_col
                else None,
                "raw": data,
            }
        )

    return result


def fetch_purchases(conn):
    if not table_exists(conn, "purchases"):
        return []

    cols = columns(conn, "purchases")

    id_col = first_existing(cols, ["id", "purchase_id"])
    product_col = first_existing(
        cols, ["product_id", "product", "item_id"]
    )
    qty_col = first_existing(
        cols, ["quantity", "qty", "units"]
    )
    date_col = first_existing(
        cols, ["created_at", "purchase_date", "date", "timestamp"]
    )
    ref_col = first_existing(
        cols,
        [
            "purchase_no",
            "purchase_number",
            "reference",
            "supplier",
            "purchase_reference",
        ],
    )

    if not id_col:
        return []

    rows = conn.execute(
        f"SELECT * FROM purchases ORDER BY {id_col}"
    ).fetchall()

    result = []

    for row in rows:
        data = dict(zip(cols, row))

        result.append(
            {
                "id": data.get(id_col),
                "product_id": data.get(product_col)
                if product_col
                else None,
                "quantity": float(data.get(qty_col) or 0)
                if qty_col
                else 0.0,
                "date": data.get(date_col)
                if date_col
                else None,
                "reference": data.get(ref_col)
                if ref_col
                else None,
                "raw": data,
            }
        )

    return result


def fetch_inventory_movements(conn):
    if not table_exists(conn, "inventory_movements"):
        return []

    cols = columns(conn, "inventory_movements")

    id_col = first_existing(cols, ["id", "movement_id"])
    product_col = first_existing(
        cols, ["product_id", "product", "item_id"]
    )
    qty_col = first_existing(
        cols, ["quantity", "qty", "units"]
    )
    type_col = first_existing(
        cols,
        [
            "movement_type",
            "type",
            "transaction_type",
            "movement",
        ],
    )
    date_col = first_existing(
        cols, ["created_at", "movement_date", "date", "timestamp"]
    )
    ref_col = first_existing(
        cols,
        [
            "reference",
            "reference_number",
            "receipt_number",
            "receipt_no",
            "transaction_reference",
        ],
    )

    if not id_col:
        return []

    rows = conn.execute(
        f"SELECT * FROM inventory_movements ORDER BY {id_col}"
    ).fetchall()

    result = []

    for row in rows:
        data = dict(zip(cols, row))

        movement_type = normalize(
            data.get(type_col)
        ) if type_col else ""

        result.append(
            {
                "id": data.get(id_col),
                "product_id": data.get(product_col)
                if product_col
                else None,
                "quantity": float(data.get(qty_col) or 0)
                if qty_col
                else 0.0,
                "type": movement_type,
                "date": data.get(date_col)
                if date_col
                else None,
                "reference": data.get(ref_col)
                if ref_col
                else None,
                "raw": data,
            }
        )

    return result


def product_name_map(conn):
    result = {}

    if not table_exists(conn, "products"):
        return result

    cols = columns(conn, "products")

    id_col = first_existing(cols, ["id", "product_id"])
    name_col = first_existing(
        cols, ["name", "product_name", "title"]
    )
    sku_col = first_existing(cols, ["sku", "code"])

    if not id_col:
        return result

    rows = conn.execute(
        f"SELECT * FROM products"
    ).fetchall()

    for row in rows:
        data = dict(zip(cols, row))
        pid = data.get(id_col)

        result[pid] = {
            "name": data.get(name_col)
            if name_col
            else f"Product {pid}",
            "sku": data.get(sku_col)
            if sku_col
            else "",
        }

    return result


def classify_movement_type(value):
    value = normalize(value)

    if value in {
        "sale",
        "out",
        "stock_out",
        "sold",
        "decrease",
        "debit",
    }:
        return "SALE"

    if value in {
        "purchase",
        "in",
        "stock_in",
        "received",
        "increase",
        "credit",
    }:
        return "PURCHASE"

    if "sale" in value:
        return "SALE"

    if "purchase" in value or value.endswith("in"):
        return "PURCHASE"

    return "OTHER"


def date_only(value):
    if value is None:
        return None

    text = safe_str(value)

    if " " in text:
        return text.split(" ")[0]

    if "T" in text:
        return text.split("T")[0]

    return text[:10] if len(text) >= 10 else text


def build_inventory_indexes(movements):
    by_product_sale = defaultdict(list)
    by_product_purchase = defaultdict(list)
    by_reference = defaultdict(list)

    for movement in movements:
        kind = classify_movement_type(movement["type"])

        if movement["reference"]:
            by_reference[
                normalize(movement["reference"])
            ].append(movement)

        pid = movement["product_id"]

        if kind == "SALE":
            by_product_sale[pid].append(movement)

        elif kind == "PURCHASE":
            by_product_purchase[pid].append(movement)

    return (
        by_product_sale,
        by_product_purchase,
        by_reference,
    )


def assess_sale(sale, by_product_sale, by_reference):
    receipt = normalize(sale["receipt"])

    # Strongest possible evidence:
    if receipt and receipt in by_reference:
        candidates = [
            m
            for m in by_reference[receipt]
            if classify_movement_type(m["type"]) == "SALE"
        ]

        if candidates:
            exact = [
                m
                for m in candidates
                if m["product_id"] == sale["product_id"]
                and abs(m["quantity"] - sale["quantity"]) < 0.000001
            ]

            if len(exact) == 1:
                return {
                    "status": "VERIFIED_REPAIR_CANDIDATE",
                    "confidence": "STRONG",
                    "reason": "Exact receipt/reference, product and quantity match.",
                    "movement": exact[0],
                }

    candidates = by_product_sale.get(
        sale["product_id"], []
    )

    exact_quantity = [
        m
        for m in candidates
        if abs(m["quantity"] - sale["quantity"]) < 0.000001
    ]

    if len(exact_quantity) == 1:
        movement = exact_quantity[0]

        sale_date = date_only(sale["date"])
        movement_date = date_only(movement["date"])

        if sale_date and movement_date and sale_date == movement_date:
            return {
                "status": "VERIFIED_REPAIR_CANDIDATE",
                "confidence": "STRONG",
                "reason": "Unique product, quantity and date match.",
                "movement": movement,
            }

        return {
            "status": "MANUAL_REVIEW",
            "confidence": "WEAK",
            "reason": "Product and quantity match, but transaction dates do not match.",
            "movement": movement,
        }

    if len(exact_quantity) > 1:
        return {
            "status": "MANUAL_REVIEW",
            "confidence": "AMBIGUOUS",
            "reason": "Multiple inventory movements match product and quantity.",
            "movement": None,
        }

    if not candidates:
        return {
            "status": "INSUFFICIENT_EVIDENCE",
            "confidence": "NONE",
            "reason": "No inventory SALE movement exists for this product.",
            "movement": None,
        }

    return {
        "status": "DO_NOT_REPAIR",
        "confidence": "NONE",
        "reason": "Existing movements do not provide a safe quantity match.",
        "movement": None,
    }


def assess_purchase(purchase, by_product_purchase):
    candidates = by_product_purchase.get(
        purchase["product_id"], []
    )

    exact = [
        m
        for m in candidates
        if abs(m["quantity"] - purchase["quantity"]) < 0.000001
        and date_only(m["date"]) == date_only(purchase["date"])
    ]

    if len(exact) == 1:
        return {
            "status": "VERIFIED",
            "confidence": "STRONG",
            "reason": "Product, quantity and date agree.",
            "movement": exact[0],
        }

    if len(exact) > 1:
        return {
            "status": "MANUAL_REVIEW",
            "confidence": "AMBIGUOUS",
            "reason": "Multiple purchase movements match.",
            "movement": None,
        }

    if not candidates:
        return {
            "status": "INSUFFICIENT_EVIDENCE",
            "confidence": "NONE",
            "reason": "No inventory PURCHASE movement exists for this product.",
            "movement": None,
        }

    return {
        "status": "MANUAL_REVIEW",
        "confidence": "WEAK",
        "reason": "Purchase movement exists but does not fully match date/quantity.",
        "movement": None,
    }


def main():
    print("=" * 60)
    print("POS LEDGER NG V96")
    print("TRANSACTION EVIDENCE & REPAIR AUTHORIZATION INTELLIGENCE")
    print("=" * 60)

    if not DB_PATH.exists():
        print("\nDATABASE NOT FOUND")
        return

    # Explicitly read-only SQLite connection.
    conn = sqlite3.connect(
        f"file:{DB_PATH}?mode=ro",
        uri=True,
    )

    try:
        print("\n" + "=" * 60)
        print("DATABASE")
        print("=" * 60)
        print(f"Database path : {DB_PATH}")
        print("Database mode : READ-ONLY")

        required = [
            "sales",
            "products",
            "inventory_movements",
            "purchases",
            "expenses",
            "customer_credit",
            "suppliers",
        ]

        for table in required:
            status = (
                "AVAILABLE"
                if table_exists(conn, table)
                else "NOT DETECTED"
            )
            print(f"{table:<22}: {status}")

        products = product_name_map(conn)
        sales = fetch_sales(conn)
        purchases = fetch_purchases(conn)
        movements = fetch_inventory_movements(conn)

        (
            by_product_sale,
            by_product_purchase,
            by_reference,
        ) = build_inventory_indexes(movements)

        print("\n" + "=" * 60)
        print("AUDIT INPUT COUNTS")
        print("=" * 60)

        print(f"Completed sales             : {len(sales)}")
        print(f"Purchase records            : {len(purchases)}")

        sale_movements = [
            m for m in movements
            if classify_movement_type(m["type"]) == "SALE"
        ]

        purchase_movements = [
            m for m in movements
            if classify_movement_type(m["type"]) == "PURCHASE"
        ]

        print(
            f"Inventory SALE movements    : "
            f"{len(sale_movements)}"
        )
        print(
            f"Inventory PURCHASE movements: "
            f"{len(purchase_movements)}"
        )

        sale_assessments = []

        for sale in sales:
            assessment = assess_sale(
                sale,
                by_product_sale,
                by_reference,
            )

            sale_assessments.append(
                (sale, assessment)
            )

        purchase_assessments = []

        for purchase in purchases:
            assessment = assess_purchase(
                purchase,
                by_product_purchase,
            )

            purchase_assessments.append(
                (purchase, assessment)
            )

        print("\n" + "=" * 60)
        print("V96 SALE EVIDENCE AUTHORIZATION")
        print("=" * 60)

        for sale, assessment in sale_assessments:
            pid = sale["product_id"]
            product = products.get(pid, {})

            movement = assessment["movement"]

            print("-" * 40)
            print(f"Sale ID             : {sale['id']}")
            print(
                f"Product             : "
                f"{product.get('name', 'UNKNOWN')}"
            )
            print(
                f"Quantity            : "
                f"{num(sale['quantity'])}"
            )
            print(
                f"Sale date           : "
                f"{safe_str(sale['date']) or 'UNKNOWN'}"
            )
            print(
                f"Receipt             : "
                f"{safe_str(sale['receipt']) or 'NOT RECORDED'}"
            )

            if movement:
                print(
                    f"Inventory movement  : "
                    f"{movement['id']}"
                )
                print(
                    f"Inventory quantity  : "
                    f"{num(movement['quantity'])}"
                )
                print(
                    f"Inventory date      : "
                    f"{safe_str(movement['date']) or 'UNKNOWN'}"
                )
            else:
                print("Inventory movement  : NONE")

            print(
                f"Evidence strength   : "
                f"{assessment['confidence']}"
            )
            print(
                f"Authorization       : "
                f"{assessment['status']}"
            )
            print(
                f"Reason              : "
                f"{assessment['reason']}"
            )

        print("\n" + "=" * 60)
        print("V96 PURCHASE EVIDENCE AUTHORIZATION")
        print("=" * 60)

        for purchase, assessment in purchase_assessments:
            pid = purchase["product_id"]
            product = products.get(pid, {})

            movement = assessment["movement"]

            print("-" * 40)
            print(f"Purchase ID         : {purchase['id']}")
            print(
                f"Product             : "
                f"{product.get('name', 'UNKNOWN')}"
            )
            print(
                f"Quantity            : "
                f"{num(purchase['quantity'])}"
            )
            print(
                f"Purchase date       : "
                f"{safe_str(purchase['date']) or 'UNKNOWN'}"
            )
            print(
                f"Purchase reference  : "
                f"{safe_str(purchase['reference']) or 'NOT RECORDED'}"
            )

            if movement:
                print(
                    f"Inventory movement  : "
                    f"{movement['id']}"
                )

            print(
                f"Evidence strength   : "
                f"{assessment['confidence']}"
            )
            print(
                f"Authorization       : "
                f"{assessment['status']}"
            )
            print(
                f"Reason              : "
                f"{assessment['reason']}"
            )

        strong_sales = sum(
            1
            for _, a in sale_assessments
            if a["confidence"] == "STRONG"
        )

        weak_sales = sum(
            1
            for _, a in sale_assessments
            if a["confidence"] == "WEAK"
        )

        ambiguous_sales = sum(
            1
            for _, a in sale_assessments
            if a["confidence"] == "AMBIGUOUS"
        )

        insufficient_sales = sum(
            1
            for _, a in sale_assessments
            if a["status"] == "INSUFFICIENT_EVIDENCE"
        )

        verified_repairs = sum(
            1
            for _, a in sale_assessments
            if a["status"] == "VERIFIED_REPAIR_CANDIDATE"
        )

        verified_purchases = sum(
            1
            for _, a in purchase_assessments
            if a["status"] == "VERIFIED"
        )

        purchase_review = sum(
            1
            for _, a in purchase_assessments
            if a["status"] == "MANUAL_REVIEW"
        )

        print("\n" + "=" * 60)
        print("V96 AUTHORIZATION SUMMARY")
        print("=" * 60)

        print(f"Sales audited             : {len(sales)}")
        print(f"Strong sale evidence      : {strong_sales}")
        print(f"Weak sale evidence        : {weak_sales}")
        print(f"Ambiguous sales           : {ambiguous_sales}")
        print(f"Insufficient sale evidence: {insufficient_sales}")
        print(
            f"Verified repair candidates: "
            f"{verified_repairs}"
        )

        print(
            f"Verified purchases        : "
            f"{verified_purchases}"
        )
        print(
            f"Purchase reviews          : "
            f"{purchase_review}"
        )

        print("\n" + "=" * 60)
        print("V96 REPAIR AUTHORIZATION DECISION")
        print("=" * 60)

        if verified_repairs == 0:
            print(
                "🔴 NO SALE REPAIRS AUTHORIZED"
            )
            print(
                "No sale has sufficient evidence "
                "for automatic repair."
            )
        elif ambiguous_sales > 0:
            print(
                "🟠 REPAIR AUTHORIZATION BLOCKED"
            )
            print(
                "Ambiguous evidence remains."
            )
        else:
            print(
                "🟡 VERIFIED CANDIDATES IDENTIFIED"
            )
            print(
                "Candidates may proceed to a "
                "separate repair-preview phase."
            )

        print("\n" + "=" * 60)
        print("V96 REPAIR RULES")
        print("=" * 60)

        print(
            "1. V96 never modifies the database."
        )
        print(
            "2. A missing movement is not automatically "
            "proof that a movement should be created."
        )
        print(
            "3. Product + quantity alone is insufficient "
            "for automatic repair."
        )
        print(
            "4. Date disagreement forces manual review."
        )
        print(
            "5. Ambiguous matches cannot be repaired automatically."
        )
        print(
            "6. Only explicitly verified candidates may "
            "enter a future repair-preview phase."
        )

        print("\n" + "=" * 60)
        print("V96 EXECUTIVE DECISION")
        print("=" * 60)

        if verified_repairs == 0:
            print(
                "🔴 STOP — EVIDENCE IS NOT SUFFICIENT "
                "FOR AUTOMATIC REPAIR"
            )
        else:
            print(
                "🟡 PROCEED TO V97 REPAIR PREVIEW"
            )

        print("\n" + "=" * 60)
        print("V96 SAFETY STATUS")
        print("=" * 60)

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
        print("=" * 60)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
