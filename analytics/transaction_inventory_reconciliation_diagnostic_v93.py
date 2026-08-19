"""
POS LEDGER NG V93
TRANSACTION ↔ INVENTORY RECONCILIATION DIAGNOSTIC INTELLIGENCE

Purpose:
    Diagnose discrepancies between sales/purchases and inventory movements.

Safety:
    READ-ONLY.
    This module NEVER INSERTS, UPDATES, DELETES, ALTERs, or repairs data.

V93 focuses on:
    1. Sale-to-inventory movement matching
    2. Purchase-to-inventory movement matching
    3. Receipt/reference matching
    4. Date matching
    5. Duplicate inventory movement detection
    6. Orphan inventory movement detection
    7. Per-product reconciliation
    8. Expected-vs-actual stock analysis
    9. Repair-ready diagnostics
"""

import sqlite3
from pathlib import Path
from collections import defaultdict
from datetime import datetime


DB_PATH = Path("data/posledger.db")


# ============================================================
# FORMATTING
# ============================================================

def money(value):
    return f"₦{float(value or 0):,.2f}"


def number(value):
    return f"{float(value or 0):,.2f}"


def safe_float(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def normalize_text(value):
    if value is None:
        return ""
    return str(value).strip().upper()


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


def safe_query(conn, sql, params=()):
    try:
        return conn.execute(sql, params).fetchall()
    except sqlite3.Error:
        return []


def safe_one(conn, sql, params=()):
    try:
        return conn.execute(sql, params).fetchone()
    except sqlite3.Error:
        return None


def parse_date(value):
    if not value:
        return None

    text = str(value).strip()

    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y/%m/%d",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%d-%m-%Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(text[:19], fmt)
        except ValueError:
            continue

    return None


def same_day(date_a, date_b):
    a = parse_date(date_a)
    b = parse_date(date_b)

    if not a or not b:
        return False

    return a.date() == b.date()


# ============================================================
# MOVEMENT CLASSIFICATION
# ============================================================

def is_sale_movement(value):
    text = normalize_text(value)

    return text in {
        "SALE",
        "SOLD",
        "OUT",
        "STOCK_OUT",
        "SALE_OUT",
    } or "SALE" in text


def is_purchase_movement(value):
    text = normalize_text(value)

    return text in {
        "PURCHASE",
        "PURCHASES",
        "STOCK_IN",
        "IN",
        "RECEIPT",
        "RESTOCK",
        "STOCK PURCHASE",
    } or "PURCHASE" in text


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("POS LEDGER NG V93")
    print("TRANSACTION ↔ INVENTORY RECONCILIATION DIAGNOSTIC INTELLIGENCE")
    print("=" * 60)

    # --------------------------------------------------------
    # DATABASE CHECK
    # --------------------------------------------------------

    if not DB_PATH.exists():
        print()
        print("=" * 60)
        print("DATABASE STATUS")
        print("=" * 60)
        print(f"Database not found : {DB_PATH}")
        print("Run this module from the POS-Ledger-NG project root.")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:

        # ====================================================
        # TABLE STRUCTURE
        # ====================================================

        print()
        print("=" * 60)
        print("DATABASE STRUCTURE")
        print("=" * 60)

        tables = [
            "sales",
            "sales_items",
            "products",
            "inventory_movements",
            "purchases",
        ]

        available = {}

        for table in tables:
            available[table] = table_exists(conn, table)

            print(
                f"{table:<22}: "
                f"{'AVAILABLE' if available[table] else 'NOT DETECTED'}"
            )

        # ====================================================
        # SALES SCHEMA
        # ====================================================

        sales_cols = columns(conn, "sales")

        sale_id_col = first_existing(
            sales_cols,
            ["id"]
        )

        sale_product_col = first_existing(
            sales_cols,
            ["product_id"]
        )

        sale_quantity_col = first_existing(
            sales_cols,
            ["quantity"]
        )

        sale_revenue_col = first_existing(
            sales_cols,
            ["total_amount", "amount", "total"]
        )

        sale_receipt_col = first_existing(
            sales_cols,
            ["receipt_no", "receipt_number", "reference"]
        )

        sale_date_col = first_existing(
            sales_cols,
            ["sale_date", "created_at", "date"]
        )

        sale_status_col = first_existing(
            sales_cols,
            ["status"]
        )

        # ====================================================
        # PURCHASE SCHEMA
        # ====================================================

        purchase_cols = columns(conn, "purchases")

        purchase_id_col = first_existing(
            purchase_cols,
            ["id"]
        )

        purchase_product_col = first_existing(
            purchase_cols,
            ["product_id"]
        )

        purchase_quantity_col = first_existing(
            purchase_cols,
            ["quantity"]
        )

        purchase_reference_col = first_existing(
            purchase_cols,
            ["purchase_no", "purchase_number", "reference"]
        )

        purchase_date_col = first_existing(
            purchase_cols,
            ["purchase_date", "created_at", "date"]
        )

        purchase_cost_col = first_existing(
            purchase_cols,
            ["total_cost"]
        )

        # ====================================================
        # PRODUCT SCHEMA
        # ====================================================

        product_cols = columns(conn, "products")

        product_id_col = first_existing(
            product_cols,
            ["id"]
        )

        product_name_col = first_existing(
            product_cols,
            ["product_name", "name"]
        )

        product_sku_col = first_existing(
            product_cols,
            ["sku"]
        )

        product_stock_col = first_existing(
            product_cols,
            ["current_stock", "stock"]
        )

        product_cost_col = first_existing(
            product_cols,
            ["buying_price", "cost_price"]
        )

        # ====================================================
        # INVENTORY SCHEMA
        # ====================================================

        inventory_cols = columns(
            conn,
            "inventory_movements"
        )

        movement_id_col = first_existing(
            inventory_cols,
            ["id"]
        )

        movement_product_col = first_existing(
            inventory_cols,
            ["product_id"]
        )

        movement_type_col = first_existing(
            inventory_cols,
            ["movement_type", "type"]
        )

        movement_quantity_col = first_existing(
            inventory_cols,
            ["quantity", "qty"]
        )

        movement_balance_col = first_existing(
            inventory_cols,
            ["balance_after", "running_balance"]
        )

        movement_reference_col = first_existing(
            inventory_cols,
            ["reference", "ref", "receipt_no", "purchase_no"]
        )

        movement_date_col = first_existing(
            inventory_cols,
            ["movement_date", "created_at", "date"]
        )

        movement_remarks_col = first_existing(
            inventory_cols,
            ["remarks", "description", "note"]
        )

        # ====================================================
        # PRODUCT LOOKUP
        # ====================================================

        products = {}

        if available["products"] and product_id_col:

            product_rows = safe_query(
                conn,
                f"""
                SELECT *
                FROM products
                """
            )

            for row in product_rows:

                product_id = row[product_id_col]

                products[product_id] = {
                    "name": (
                        row[product_name_col]
                        if product_name_col
                        else f"Product {product_id}"
                    ),
                    "sku": (
                        row[product_sku_col]
                        if product_sku_col
                        else ""
                    ),
                    "stock": (
                        safe_float(row[product_stock_col])
                        if product_stock_col
                        else 0.0
                    ),
                    "cost": (
                        safe_float(row[product_cost_col])
                        if product_cost_col
                        else 0.0
                    ),
                }

        # ====================================================
        # LOAD COMPLETED SALES
        # ====================================================

        sales = []

        if available["sales"] and sale_id_col:

            status_filter = ""

            if sale_status_col:
                status_filter = f"""
                    WHERE UPPER(
                        COALESCE({sale_status_col}, '')
                    ) IN (
                        'COMPLETED',
                        'COMPLETE',
                        'SUCCESS',
                        'PAID'
                    )
                """

            sales = safe_query(
                conn,
                f"""
                SELECT *
                FROM sales
                {status_filter}
                ORDER BY {sale_id_col}
                """
            )

        # ====================================================
        # LOAD PURCHASES
        # ====================================================

        purchases = []

        if available["purchases"] and purchase_id_col:

            purchases = safe_query(
                conn,
                f"""
                SELECT *
                FROM purchases
                ORDER BY {purchase_id_col}
                """
            )

        # ====================================================
        # LOAD INVENTORY MOVEMENTS
        # ====================================================

        movements = []

        if (
            available["inventory_movements"]
            and movement_id_col
        ):

            movements = safe_query(
                conn,
                f"""
                SELECT *
                FROM inventory_movements
                ORDER BY {movement_id_col}
                """
            )

        # ====================================================
        # BASIC COUNTS
        # ====================================================

        print()
        print("=" * 60)
        print("TRANSACTION COUNTS")
        print("=" * 60)

        print(
            f"Completed sales       : {len(sales)}"
        )

        print(
            f"Purchase records      : {len(purchases)}"
        )

        print(
            f"Inventory movements   : {len(movements)}"
        )

        # ====================================================
        # CLASSIFY MOVEMENTS
        # ====================================================

        sale_movements = []
        purchase_movements = []
        other_movements = []

        for movement in movements:

            movement_type = (
                movement[movement_type_col]
                if movement_type_col
                else ""
            )

            if is_sale_movement(movement_type):
                sale_movements.append(movement)

            elif is_purchase_movement(movement_type):
                purchase_movements.append(movement)

            else:
                other_movements.append(movement)

        # ====================================================
        # MOVEMENT COUNTS
        # ====================================================

        print()
        print("=" * 60)
        print("INVENTORY MOVEMENT CLASSIFICATION")
        print("=" * 60)

        print(
            f"SALE movements        : "
            f"{len(sale_movements)}"
        )

        print(
            f"PURCHASE/IN movements  : "
            f"{len(purchase_movements)}"
        )

        print(
            f"Other movements        : "
            f"{len(other_movements)}"
        )

        # ====================================================
        # SALES AGGREGATION BY PRODUCT
        # ====================================================

        sales_by_product = defaultdict(
            lambda: {
                "sales": 0,
                "units": 0.0,
                "revenue": 0.0,
            }
        )

        for sale in sales:

            product_id = (
                sale[sale_product_col]
                if sale_product_col
                else None
            )

            quantity = (
                safe_float(sale[sale_quantity_col])
                if sale_quantity_col
                else 0.0
            )

            revenue = (
                safe_float(sale[sale_revenue_col])
                if sale_revenue_col
                else 0.0
            )

            sales_by_product[product_id]["sales"] += 1
            sales_by_product[product_id]["units"] += quantity
            sales_by_product[product_id]["revenue"] += revenue

        # ====================================================
        # INVENTORY SALE AGGREGATION BY PRODUCT
        # ====================================================

        inventory_sales_by_product = defaultdict(
            lambda: {
                "movements": 0,
                "units": 0.0,
            }
        )

        for movement in sale_movements:

            product_id = (
                movement[movement_product_col]
                if movement_product_col
                else None
            )

            quantity = (
                safe_float(movement[movement_quantity_col])
                if movement_quantity_col
                else 0.0
            )

            inventory_sales_by_product[
                product_id
            ]["movements"] += 1

            inventory_sales_by_product[
                product_id
            ]["units"] += quantity

        # ====================================================
        # PURCHASE AGGREGATION BY PRODUCT
        # ====================================================

        purchases_by_product = defaultdict(
            lambda: {
                "records": 0,
                "units": 0.0,
                "value": 0.0,
            }
        )

        for purchase in purchases:

            product_id = (
                purchase[purchase_product_col]
                if purchase_product_col
                else None
            )

            quantity = (
                safe_float(
                    purchase[purchase_quantity_col]
                )
                if purchase_quantity_col
                else 0.0
            )

            cost = (
                safe_float(
                    purchase[purchase_cost_col]
                )
                if purchase_cost_col
                else 0.0
            )

            purchases_by_product[
                product_id
            ]["records"] += 1

            purchases_by_product[
                product_id
            ]["units"] += quantity

            purchases_by_product[
                product_id
            ]["value"] += cost

        # ====================================================
        # INVENTORY PURCHASE AGGREGATION
        # ====================================================

        inventory_purchases_by_product = defaultdict(
            lambda: {
                "movements": 0,
                "units": 0.0,
            }
        )

        for movement in purchase_movements:

            product_id = (
                movement[movement_product_col]
                if movement_product_col
                else None
            )

            quantity = (
                safe_float(
                    movement[movement_quantity_col]
                )
                if movement_quantity_col
                else 0.0
            )

            inventory_purchases_by_product[
                product_id
            ]["movements"] += 1

            inventory_purchases_by_product[
                product_id
            ]["units"] += quantity

        # ====================================================
        # PRODUCT-LEVEL RECONCILIATION
        # ====================================================

        all_product_ids = set()

        all_product_ids.update(
            sales_by_product.keys()
        )

        all_product_ids.update(
            inventory_sales_by_product.keys()
        )

        all_product_ids.update(
            purchases_by_product.keys()
        )

        all_product_ids.update(
            inventory_purchases_by_product.keys()
        )

        print()
        print("=" * 60)
        print("PRODUCT-LEVEL RECONCILIATION")
        print("=" * 60)

        product_mismatches = []

        for product_id in sorted(
            all_product_ids,
            key=lambda x: str(x)
        ):

            product = products.get(
                product_id,
                {
                    "name": f"Unknown Product {product_id}",
                    "sku": "",
                    "stock": 0.0,
                    "cost": 0.0,
                }
            )

            sale_units = sales_by_product[
                product_id
            ]["units"]

            inventory_sale_units = (
                inventory_sales_by_product[
                    product_id
                ]["units"]
            )

            purchase_units = (
                purchases_by_product[
                    product_id
                ]["units"]
            )

            inventory_purchase_units = (
                inventory_purchases_by_product[
                    product_id
                ]["units"]
            )

            sale_difference = (
                sale_units - inventory_sale_units
            )

            purchase_difference = (
                purchase_units -
                inventory_purchase_units
            )

            print("-" * 40)

            print(
                f"Product ID            : {product_id}"
            )

            print(
                f"Product               : "
                f"{product['name']}"
            )

            print(
                f"SKU                   : "
                f"{product['sku'] or 'N/A'}"
            )

            print(
                f"Sales units           : "
                f"{number(sale_units)}"
            )

            print(
                f"Inventory SALE units  : "
                f"{number(inventory_sale_units)}"
            )

            print(
                f"SALE difference       : "
                f"{number(sale_difference)}"
            )

            print(
                f"Purchase units        : "
                f"{number(purchase_units)}"
            )

            print(
                f"Inventory IN units    : "
                f"{number(inventory_purchase_units)}"
            )

            print(
                f"Purchase difference   : "
                f"{number(purchase_difference)}"
            )

            if abs(sale_difference) > 0.0001:
                print(
                    "SALE STATUS           : 🔴 MISMATCH"
                )

                product_mismatches.append(
                    (
                        product_id,
                        "SALE",
                        sale_difference,
                    )
                )
            else:
                print(
                    "SALE STATUS           : 🟢 RECONCILED"
                )

            if abs(purchase_difference) > 0.0001:
                print(
                    "PURCHASE STATUS       : 🟠 REVIEW"
                )

                product_mismatches.append(
                    (
                        product_id,
                        "PURCHASE",
                        purchase_difference,
                    )
                )
            else:
                print(
                    "PURCHASE STATUS       : 🟢 RECONCILED"
                )

        # ====================================================
        # RECEIPT / REFERENCE MATCHING
        # ====================================================

        print()
        print("=" * 60)
        print("SALE RECEIPT ↔ INVENTORY REFERENCE TEST")
        print("=" * 60)

        matched_receipts = 0
        unmatched_receipts = 0
        missing_reference_sales = 0

        inventory_references = defaultdict(list)

        for movement in sale_movements:

            reference = (
                movement[movement_reference_col]
                if movement_reference_col
                else None
            )

            key = normalize_text(reference)

            if key:
                inventory_references[key].append(
                    movement
                )

        for sale in sales:

            receipt = (
                sale[sale_receipt_col]
                if sale_receipt_col
                else None
            )

            key = normalize_text(receipt)

            if not key:
                missing_reference_sales += 1
                continue

            if key in inventory_references:
                matched_receipts += 1
            else:
                unmatched_receipts += 1

        print(
            f"Sales with matched reference : "
            f"{matched_receipts}"
        )

        print(
            f"Sales without inventory ref   : "
            f"{unmatched_receipts}"
        )

        print(
            f"Sales missing receipt number  : "
            f"{missing_reference_sales}"
        )

        # ====================================================
        # PURCHASE REFERENCE MATCHING
        # ====================================================

        print()
        print("=" * 60)
        print("PURCHASE ↔ INVENTORY REFERENCE TEST")
        print("=" * 60)

        matched_purchases = 0
        unmatched_purchases = 0
        missing_purchase_reference = 0

        inventory_purchase_references = defaultdict(list)

        for movement in purchase_movements:

            reference = (
                movement[movement_reference_col]
                if movement_reference_col
                else None
            )

            key = normalize_text(reference)

            if key:
                inventory_purchase_references[
                    key
                ].append(movement)

        for purchase in purchases:

            reference = (
                purchase[purchase_reference_col]
                if purchase_reference_col
                else None
            )

            key = normalize_text(reference)

            if not key:
                missing_purchase_reference += 1
                continue

            if key in inventory_purchase_references:
                matched_purchases += 1
            else:
                unmatched_purchases += 1

        print(
            f"Purchases with matched ref    : "
            f"{matched_purchases}"
        )

        print(
            f"Purchases without inventory ref: "
            f"{unmatched_purchases}"
        )

        print(
            f"Purchases missing reference   : "
            f"{missing_purchase_reference}"
        )

        # ====================================================
        # DUPLICATE MOVEMENT DETECTION
        # ====================================================

        print()
        print("=" * 60)
        print("DUPLICATE INVENTORY MOVEMENT TEST")
        print("=" * 60)

        duplicate_groups = []

        movement_groups = defaultdict(list)

        for movement in movements:

            product_id = (
                movement[movement_product_col]
                if movement_product_col
                else None
            )

            movement_type = (
                normalize_text(
                    movement[movement_type_col]
                )
                if movement_type_col
                else ""
            )

            quantity = (
                safe_float(
                    movement[movement_quantity_col]
                )
                if movement_quantity_col
                else 0.0
            )

            reference = (
                normalize_text(
                    movement[movement_reference_col]
                )
                if movement_reference_col
                else ""
            )

            movement_date = (
                movement[movement_date_col]
                if movement_date_col
                else ""
            )

            # Exact duplicate signature.
            signature = (
                product_id,
                movement_type,
                quantity,
                reference,
                str(movement_date)[:19],
            )

            movement_groups[signature].append(
                movement
            )

        for signature, rows in movement_groups.items():

            if len(rows) > 1:
                duplicate_groups.append(
                    (signature, rows)
                )

        print(
            f"Duplicate movement groups : "
            f"{len(duplicate_groups)}"
        )

        if duplicate_groups:

            for signature, rows in duplicate_groups:
                print("-" * 40)
                print(
                    f"Product ID : {signature[0]}"
                )
                print(
                    f"Type       : {signature[1]}"
                )
                print(
                    f"Quantity   : {number(signature[2])}"
                )
                print(
                    f"Reference  : "
                    f"{signature[3] or 'NONE'}"
                )
                print(
                    f"Date       : {signature[4] or 'NONE'}"
                )
                print(
                    f"Copies     : {len(rows)}"
                )

        # ====================================================
        # ORPHAN MOVEMENT DETECTION
        # ====================================================

        print()
        print("=" * 60)
        print("ORPHAN INVENTORY MOVEMENT TEST")
        print("=" * 60)

        orphan_sale_movements = []
        orphan_purchase_movements = []

        sale_receipt_keys = set()

        for sale in sales:

            receipt = (
                sale[sale_receipt_col]
                if sale_receipt_col
                else None
            )

            key = normalize_text(receipt)

            if key:
                sale_receipt_keys.add(key)

        purchase_reference_keys = set()

        for purchase in purchases:

            reference = (
                purchase[purchase_reference_col]
                if purchase_reference_col
                else None
            )

            key = normalize_text(reference)

            if key:
                purchase_reference_keys.add(key)

        for movement in sale_movements:

            reference = (
                movement[movement_reference_col]
                if movement_reference_col
                else None
            )

            key = normalize_text(reference)

            if key and key not in sale_receipt_keys:
                orphan_sale_movements.append(movement)

        for movement in purchase_movements:

            reference = (
                movement[movement_reference_col]
                if movement_reference_col
                else None
            )

            key = normalize_text(reference)

            if (
                key
                and key not in purchase_reference_keys
            ):
                orphan_purchase_movements.append(
                    movement
                )

        print(
            f"Orphan SALE movements     : "
            f"{len(orphan_sale_movements)}"
        )

        print(
            f"Orphan PURCHASE movements : "
            f"{len(orphan_purchase_movements)}"
        )

        # ====================================================
        # DATE RECONCILIATION
        # ====================================================

        print()
        print("=" * 60)
        print("TRANSACTION DATE ↔ INVENTORY DATE TEST")
        print("=" * 60)

        date_matched_sales = 0
        date_mismatched_sales = 0

        # Reference-based date comparison.
        inventory_sale_by_reference = {}

        for movement in sale_movements:

            reference = (
                movement[movement_reference_col]
                if movement_reference_col
                else None
            )

            key = normalize_text(reference)

            if key:
                inventory_sale_by_reference[
                    key
                ] = movement

        for sale in sales:

            receipt = (
                sale[sale_receipt_col]
                if sale_receipt_col
                else None
            )

            key = normalize_text(receipt)

            if not key:
                continue

            movement = inventory_sale_by_reference.get(
                key
            )

            if not movement:
                continue

            sale_date = (
                sale[sale_date_col]
                if sale_date_col
                else None
            )

            movement_date = (
                movement[movement_date_col]
                if movement_date_col
                else None
            )

            if same_day(
                sale_date,
                movement_date
            ):
                date_matched_sales += 1
            else:
                date_mismatched_sales += 1

        print(
            f"Sales date matched        : "
            f"{date_matched_sales}"
        )

        print(
            f"Sales date mismatched     : "
            f"{date_mismatched_sales}"
        )

        # ====================================================
        # EXPECTED STOCK MODEL
        # ====================================================

        print()
        print("=" * 60)
        print("EXPECTED STOCK MOVEMENT MODEL")
        print("=" * 60)

        expected_stock_by_product = defaultdict(
            float
        )

        # Purchases increase stock.
        for product_id, data in purchases_by_product.items():
            expected_stock_by_product[
                product_id
            ] += data["units"]

        # Sales decrease stock.
        for product_id, data in sales_by_product.items():
            expected_stock_by_product[
                product_id
            ] -= data["units"]

        expected_total_stock = 0.0

        for product_id in all_product_ids:

            product = products.get(
                product_id,
                {
                    "name": f"Unknown Product {product_id}",
                    "stock": 0.0,
                }
            )

            actual_stock = safe_float(
                product.get("stock", 0.0)
            )

            expected_change = safe_float(
                expected_stock_by_product[
                    product_id
                ]
            )

            # This is a transaction-flow model, not an opening
            # stock model. Therefore it cannot by itself prove
            # the absolute current stock unless opening stock is
            # known.
            expected_total_stock += expected_change

            print("-" * 40)
            print(
                f"Product ID             : {product_id}"
            )
            print(
                f"Product                : "
                f"{product['name']}"
            )
            print(
                f"Purchase units         : "
                f"{number(purchases_by_product[product_id]['units'])}"
            )
            print(
                f"Sales units            : "
                f"{number(sales_by_product[product_id]['units'])}"
            )
            print(
                f"Net transaction change : "
                f"{number(expected_change)}"
            )
            print(
                f"Current stock          : "
                f"{number(actual_stock)}"
            )
            print(
                "Absolute stock check   : "
                "🟡 OPENING STOCK REQUIRED"
            )

        print()
        print(
            f"Net transaction stock change : "
            f"{number(expected_total_stock)}"
        )

        # ====================================================
        # CURRENT STOCK TOTAL
        # ====================================================

        actual_total_stock = 0.0

        for product in products.values():
            actual_total_stock += safe_float(
                product.get("stock", 0.0)
            )

        print(
            f"Actual current stock total   : "
            f"{number(actual_total_stock)}"
        )

        # ====================================================
        # RECONCILIATION SUMMARY
        # ====================================================

        total_sales_units = sum(
            data["units"]
            for data in sales_by_product.values()
        )

        total_inventory_sale_units = sum(
            data["units"]
            for data in
            inventory_sales_by_product.values()
        )

        total_purchase_units = sum(
            data["units"]
            for data in purchases_by_product.values()
        )

        total_inventory_purchase_units = sum(
            data["units"]
            for data in
            inventory_purchases_by_product.values()
        )

        sale_difference = (
            total_sales_units -
            total_inventory_sale_units
        )

        purchase_difference = (
            total_purchase_units -
            total_inventory_purchase_units
        )

        # ====================================================
        # DIAGNOSTIC FINDINGS
        # ====================================================

        findings = []

        if abs(sale_difference) > 0.0001:

            findings.append(
                (
                    "HIGH",
                    "SALE INVENTORY MISMATCH",
                    (
                        f"{number(abs(sale_difference))} "
                        "sales unit(s) are not represented "
                        "by inventory SALE movements."
                    ),
                )
            )

        if abs(purchase_difference) > 0.0001:

            findings.append(
                (
                    "MEDIUM",
                    "PURCHASE INVENTORY MISMATCH",
                    (
                        f"{number(abs(purchase_difference))} "
                        "purchase unit(s) do not reconcile "
                        "with inventory IN movements."
                    ),
                )
            )

        if unmatched_receipts > 0:

            findings.append(
                (
                    "HIGH",
                    "MISSING SALE REFERENCES",
                    (
                        f"{unmatched_receipts} completed "
                        "sale(s) have no matching inventory "
                        "reference."
                    ),
                )
            )

        if unmatched_purchases > 0:

            findings.append(
                (
                    "MEDIUM",
                    "MISSING PURCHASE REFERENCES",
                    (
                        f"{unmatched_purchases} purchase(s) "
                        "have no matching inventory reference."
                    ),
                )
            )

        if duplicate_groups:

            findings.append(
                (
                    "MEDIUM",
                    "DUPLICATE MOVEMENTS",
                    (
                        f"{len(duplicate_groups)} exact "
                        "duplicate inventory movement group(s) "
                        "were detected."
                    ),
                )
            )

        if orphan_sale_movements:

            findings.append(
                (
                    "MEDIUM",
                    "ORPHAN SALE MOVEMENTS",
                    (
                        f"{len(orphan_sale_movements)} inventory "
                        "SALE movement(s) have no matching sale "
                        "receipt."
                    ),
                )
            )

        if orphan_purchase_movements:

            findings.append(
                (
                    "MEDIUM",
                    "ORPHAN PURCHASE MOVEMENTS",
                    (
                        f"{len(orphan_purchase_movements)} inventory "
                        "purchase movement(s) have no matching "
                        "purchase reference."
                    ),
                )
            )

        if date_mismatched_sales:

            findings.append(
                (
                    "LOW",
                    "DATE MISMATCH",
                    (
                        f"{date_mismatched_sales} matched sale/"
                        "inventory pairs occur on different dates."
                    ),
                )
            )

        if not findings:

            findings.append(
                (
                    "GOOD",
                    "NO MAJOR EXCEPTION",
                    "No major transaction-integrity exception detected.",
                )
            )

        # ====================================================
        # SUMMARY
        # ====================================================

        print()
        print("=" * 60)
        print("V93 RECONCILIATION SUMMARY")
        print("=" * 60)

        print(
            f"Sales units             : "
            f"{number(total_sales_units)}"
        )

        print(
            f"Inventory SALE units    : "
            f"{number(total_inventory_sale_units)}"
        )

        print(
            f"SALE difference         : "
            f"{number(sale_difference)}"
        )

        print(
            f"Purchase units          : "
            f"{number(total_purchase_units)}"
        )

        print(
            f"Inventory IN units      : "
            f"{number(total_inventory_purchase_units)}"
        )

        print(
            f"PURCHASE difference     : "
            f"{number(purchase_difference)}"
        )

        print(
            f"Matched sale references : "
            f"{matched_receipts}"
        )

        print(
            f"Matched purchase refs   : "
            f"{matched_purchases}"
        )

        print(
            f"Duplicate groups        : "
            f"{len(duplicate_groups)}"
        )

        print(
            f"Orphan SALE movements   : "
            f"{len(orphan_sale_movements)}"
        )

        print(
            f"Orphan PURCHASE moves   : "
            f"{len(orphan_purchase_movements)}"
        )

        # ====================================================
        # FINDINGS
        # ====================================================

        print()
        print("=" * 60)
        print("V93 DIAGNOSTIC FINDINGS")
        print("=" * 60)

        for severity, title, message in findings:

            icon = {
                "HIGH": "🔴",
                "MEDIUM": "🟠",
                "LOW": "🟡",
                "GOOD": "🟢",
            }.get(severity, "⚪")

            print(
                f"{icon} [{severity}] {title}"
            )

            print(
                f"    {message}"
            )

        # ====================================================
        # REPAIR READINESS
        # ====================================================

        print()
        print("=" * 60)
        print("V93 REPAIR READINESS")
        print("=" * 60)

        if (
            abs(sale_difference) > 0.0001
            or abs(purchase_difference) > 0.0001
            or duplicate_groups
            or orphan_sale_movements
            or orphan_purchase_movements
        ):

            print(
                "Status : 🔴 NOT READY FOR AUTOMATIC REPAIR"
            )

            print()
            print(
                "Reason:"
            )

            print(
                "Transaction and inventory history contains "
                "unresolved discrepancies."
            )

            print(
                "A repair module must identify the exact "
                "missing/duplicate transactions before any "
                "database modification is considered."
            )

        else:

            print(
                "Status : 🟢 DIAGNOSTIC RECONCILIATION CLEAN"
            )

            print(
                "No transaction/inventory discrepancy requiring "
                "repair was detected."
            )

        # ====================================================
        # EXECUTIVE DECISION
        # ====================================================

        print()
        print("=" * 60)
        print("V93 EXECUTIVE DECISION")
        print("=" * 60)

        if abs(sale_difference) > 0.0001:

            print(
                "🔴 STOP — INVESTIGATE SALE/INVENTORY HISTORY"
            )

            print(
                f"{number(abs(sale_difference))} sales unit(s) "
                "remain unmatched."
            )

        elif abs(purchase_difference) > 0.0001:

            print(
                "🟠 REVIEW PURCHASE/INVENTORY HISTORY"
            )

        elif duplicate_groups:

            print(
                "🟠 REVIEW DUPLICATE INVENTORY MOVEMENTS"
            )

        elif orphan_sale_movements or orphan_purchase_movements:

            print(
                "🟠 REVIEW ORPHAN INVENTORY MOVEMENTS"
            )

        else:

            print(
                "🟢 TRANSACTION HISTORY RECONCILES"
            )

        # ====================================================
        # MANAGEMENT INTERPRETATION
        # ====================================================

        print()
        print("=" * 60)
        print("V93 MANAGEMENT INTERPRETATION")
        print("=" * 60)

        print(
            "V93 does not assume that an inventory mismatch "
            "means the financial sale is wrong."
        )

        print(
            "It separates transaction records from inventory "
            "movement records and identifies where the audit "
            "trail diverges."
        )

        print(
            "Opening stock must be known before absolute current "
            "stock can be proven solely from transaction history."
        )

        print(
            "No repair or automatic correction is performed."
        )

        # ====================================================
        # DATA INTEGRITY STATUS
        # ====================================================

        print()
        print("=" * 60)
        print("V93 DATA INTEGRITY STATUS")
        print("=" * 60)

        print(
            f"Sales source             : "
            f"{'AVAILABLE' if available['sales'] else 'NOT DETECTED'}"
        )

        print(
            f"Products source          : "
            f"{'AVAILABLE' if available['products'] else 'NOT DETECTED'}"
        )

        print(
            f"Inventory source         : "
            f"{'AVAILABLE' if available['inventory_movements'] else 'NOT DETECTED'}"
        )

        print(
            f"Purchases source         : "
            f"{'AVAILABLE' if available['purchases'] else 'NOT DETECTED'}"
        )

        print(
            f"Receipt linkage          : "
            f"{'DETECTED' if sale_receipt_col else 'NOT DETECTED'}"
        )

        print(
            f"Purchase linkage         : "
            f"{'DETECTED' if purchase_reference_col else 'NOT DETECTED'}"
        )

        print(
            f"Opening stock source     : NOT DETECTED"
        )

        # ====================================================
        # SAFETY
        # ====================================================

        print()
        print("=" * 60)
        print("V93 SAFETY STATUS")
        print("=" * 60)

        print("Mode                  : READ-ONLY")
        print("Database modified     : NO")
        print("Sales modified        : NO")
        print("Sales repaired        : NO")
        print("Products modified     : NO")
        print("Inventory modified    : NO")
        print("Inventory repaired    : NO")
        print("Purchases modified    : NO")
        print("Balance modified      : NO")
        print("Credit modified       : NO")
        print("Suppliers modified    : NO")
        print("Expenses modified     : NO")

        print("=" * 60)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
