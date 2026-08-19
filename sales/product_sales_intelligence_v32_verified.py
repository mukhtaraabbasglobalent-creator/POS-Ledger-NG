import sqlite3
from datetime import datetime

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def find_table(cur, candidates):
    tables = {
        row["name"]
        for row in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }

    for candidate in candidates:
        if candidate in tables:
            return candidate

    return None


def get_columns(cur, table):
    if not table:
        return []

    return [
        row["name"]
        for row in cur.execute(
            f"PRAGMA table_info({table})"
        ).fetchall()
    ]


def first_existing(columns, candidates):
    for candidate in candidates:
        if candidate in columns:
            return candidate

    return None


def product_sales_intelligence():
    conn = get_connection()
    cur = conn.cursor()

    print("\n========================================")
    print("       POS LEDGER NG V32")
    print("   PRODUCT SALES INTELLIGENCE")
    print("========================================")

    # --------------------------------------------------
    # Locate existing tables
    # --------------------------------------------------
    sales_table = find_table(
        cur,
        [
            "sales",
            "sale",
            "transactions"
        ]
    )

    items_table = find_table(
        cur,
        [
            "sale_items",
            "sales_items",
            "sale_details",
            "sales_details",
            "transaction_items",
            "cart_items"
        ]
    )

    products_table = find_table(
        cur,
        [
            "products",
            "product"
        ]
    )

    if not sales_table:
        print("\nERROR: No sales table was found.")
        conn.close()
        input("\nPress Enter to continue...")
        return

    # --------------------------------------------------
    # Inspect table structures
    # --------------------------------------------------
    sales_columns = get_columns(cur, sales_table)
    item_columns = get_columns(cur, items_table)
    product_columns = get_columns(cur, products_table)

    # --------------------------------------------------
    # Find sales item relationships
    # --------------------------------------------------
    item_product_id = first_existing(
        item_columns,
        [
            "product_id",
            "product",
            "productid"
        ]
    )

    item_quantity = first_existing(
        item_columns,
        [
            "quantity",
            "qty",
            "units"
        ]
    )

    item_price = first_existing(
        item_columns,
        [
            "selling_price",
            "unit_price",
            "price",
            "sale_price"
        ]
    )

    item_total = first_existing(
        item_columns,
        [
            "total",
            "total_amount",
            "line_total",
            "amount",
            "subtotal"
        ]
    )

    item_sale_id = first_existing(
        item_columns,
        [
            "sale_id",
            "sales_id",
            "transaction_id"
        ]
    )

    item_product_name = first_existing(
        item_columns,
        [
            "product_name",
            "name",
            "item_name"
        ]
    )

    # --------------------------------------------------
    # Product table fields
    # --------------------------------------------------
    product_id = first_existing(
        product_columns,
        [
            "id",
            "product_id"
        ]
    )

    product_name = first_existing(
        product_columns,
        [
            "name",
            "product_name",
            "title"
        ]
    )

    product_sku = first_existing(
        product_columns,
        [
            "sku",
            "product_sku",
            "code"
        ]
    )

    # --------------------------------------------------
    # Find sale date
    # --------------------------------------------------
    sale_date = first_existing(
        sales_columns,
        [
            "sale_date",
            "created_at",
            "created_date",
            "transaction_date",
            "date"
        ]
    )

    # --------------------------------------------------
    # Basic validation
    # --------------------------------------------------
    if not items_table:
        print("\nNo sales-item table was found.")
        print("V32 requires product-level sales records.")
        print("\nDetected tables:")
        for table in sorted(
            row["name"]
            for row in cur.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table'"
            ).fetchall()
        ):
            print(f"• {table}")

        conn.close()
        input("\nPress Enter to continue...")
        return

    if not item_product_id and not item_product_name:
        print("\nUnable to identify product information in sales items.")
        print("V32 cannot safely calculate product performance.")

        conn.close()
        input("\nPress Enter to continue...")
        return

    # --------------------------------------------------
    # Build product sales query
    # --------------------------------------------------
    product_label = None

    if products_table and product_id and product_name and item_product_id:

        product_label = f"""
        COALESCE(p.{product_name}, 'Unknown Product')
        """

        join_clause = f"""
        LEFT JOIN {products_table} p
          ON p.{product_id} = si.{item_product_id}
        """

    elif item_product_name:

        product_label = f"""
        COALESCE(si.{item_product_name}, 'Unknown Product')
        """

        join_clause = ""

    else:

        product_label = f"""
        'Product #' || si.{item_product_id}
        """

        join_clause = ""

    # --------------------------------------------------
    # Quantity expression
    # --------------------------------------------------
    if item_quantity:
        quantity_expression = (
            f"COALESCE(SUM(si.{item_quantity}), 0)"
        )
    else:
        quantity_expression = "COUNT(*)"

    # --------------------------------------------------
    # Revenue expression
    # --------------------------------------------------
    if item_total:

        revenue_expression = (
            f"COALESCE(SUM(si.{item_total}), 0)"
        )

    elif item_quantity and item_price:

        revenue_expression = (
            f"COALESCE("
            f"SUM(si.{item_quantity} * si.{item_price}), "
            f"0)"
        )

    elif item_price:

        revenue_expression = (
            f"COALESCE(SUM(si.{item_price}), 0)"
        )

    else:

        revenue_expression = "0"

    # --------------------------------------------------
    # Product performance
    # --------------------------------------------------
    query = f"""
        SELECT
            {product_label} AS product_name,
            {quantity_expression} AS quantity_sold,
            {revenue_expression} AS revenue
        FROM {items_table} si
        {join_clause}
        GROUP BY {product_label}
        ORDER BY revenue DESC, quantity_sold DESC
    """

    try:
        product_rows = cur.execute(query).fetchall()

    except sqlite3.OperationalError as exc:

        print("\nV32 DATABASE COMPATIBILITY ERROR")
        print("----------------------------------------")
        print(str(exc))
        print("----------------------------------------")
        print("Existing records were NOT modified.")

        conn.close()
        input("\nPress Enter to continue...")
        return

    # --------------------------------------------------
    # Overall product metrics
    # --------------------------------------------------
    total_products = len(product_rows)

    total_quantity = sum(
        float(row["quantity_sold"] or 0)
        for row in product_rows
    )

    total_revenue = sum(
        float(row["revenue"] or 0)
        for row in product_rows
    )

    # --------------------------------------------------
    # Product rankings
    # --------------------------------------------------
    best_product = None
    slow_product = None

    if product_rows:

        best_product = product_rows[0]

        non_zero_products = [
            row
            for row in product_rows
            if float(row["quantity_sold"] or 0) > 0
        ]

        if non_zero_products:
            slow_product = min(
                non_zero_products,
                key=lambda row: (
                    float(row["quantity_sold"] or 0),
                    float(row["revenue"] or 0)
                )
            )

    # --------------------------------------------------
    # Revenue contribution
    # --------------------------------------------------
    top_product_share = 0.0

    if best_product and total_revenue > 0:

        top_product_share = (
            float(best_product["revenue"] or 0)
            / total_revenue
        ) * 100

    # --------------------------------------------------
    # Sales concentration
    # --------------------------------------------------
    if total_products == 0:

        concentration = "NO PRODUCT SALES"

    elif top_product_share >= 70:

        concentration = "HIGH CONCENTRATION"

    elif top_product_share >= 40:

        concentration = "MODERATE CONCENTRATION"

    else:

        concentration = "DIVERSIFIED SALES"

    # --------------------------------------------------
    # Product activity
    # --------------------------------------------------
    if total_quantity == 0:

        activity_status = "🔴 NO PRODUCT SALES"

    elif total_quantity < 10:

        activity_status = "🟡 LOW PRODUCT ACTIVITY"

    elif total_quantity < 50:

        activity_status = "🟢 ACTIVE PRODUCT SALES"

    else:

        activity_status = "🟢 HIGH PRODUCT ACTIVITY"

    # --------------------------------------------------
    # Data confidence
    # --------------------------------------------------
    if total_products >= 10:

        confidence = "🟢 HIGH"

    elif total_products >= 5:

        confidence = "🟡 MODERATE"

    elif total_products >= 1:

        confidence = "🟠 LIMITED"

    else:

        confidence = "🔴 VERY LIMITED"

    # --------------------------------------------------
    # Management recommendation
    # --------------------------------------------------
    if total_products == 0:

        recommendation = (
            "NO PRODUCT SALES DATA AVAILABLE"
        )

    elif top_product_share >= 70:

        recommendation = (
            "MONITOR DEPENDENCE ON TOP PRODUCT"
        )

    elif slow_product and total_products >= 3:

        recommendation = (
            "REVIEW SLOW-MOVING PRODUCTS"
        )

    else:

        recommendation = (
            "NORMAL PRODUCT SALES MONITORING"
        )

    # --------------------------------------------------
    # Output
    # --------------------------------------------------
    print("\n========================================")
    print("       PRODUCT SALES POSITION")
    print("========================================")
    print(f"Products With Sales : {total_products}")
    print(f"Quantity Sold       : {total_quantity:,.2f}")
    print(f"Product Revenue     : ₦{total_revenue:,.2f}")

    print("\n========================================")
    print("       PRODUCT SALES RANKING")
    print("========================================")

    if not product_rows:

        print("No product sales recorded.")

    else:

        for index, row in enumerate(product_rows[:10], 1):

            name = row["product_name"]
            quantity = float(row["quantity_sold"] or 0)
            revenue = float(row["revenue"] or 0)

            share = (
                (revenue / total_revenue) * 100
                if total_revenue > 0
                else 0
            )

            print("----------------------------------------")
            print(f"#{index} {name}")
            print(f"Quantity Sold : {quantity:,.2f}")
            print(f"Revenue       : ₦{revenue:,.2f}")
            print(f"Revenue Share : {share:.2f}%")

    print("\n========================================")
    print("       TOP PRODUCT")
    print("========================================")

    if best_product:

        print(f"Product       : {best_product['product_name']}")
        print(
            f"Quantity Sold : "
            f"{float(best_product['quantity_sold'] or 0):,.2f}"
        )
        print(
            f"Revenue       : "
            f"₦{float(best_product['revenue'] or 0):,.2f}"
        )
        print(f"Revenue Share : {top_product_share:.2f}%")

    else:

        print("No top product available.")

    print("\n========================================")
    print("       SLOW-MOVING PRODUCT")
    print("========================================")

    if slow_product:

        print(f"Product       : {slow_product['product_name']}")
        print(
            f"Quantity Sold : "
            f"{float(slow_product['quantity_sold'] or 0):,.2f}"
        )
        print(
            f"Revenue       : "
            f"₦{float(slow_product['revenue'] or 0):,.2f}"
        )

    else:

        print("No slow-moving product identified.")

    print("\n========================================")
    print("       SALES CONCENTRATION")
    print("========================================")
    print(f"Concentration : {concentration}")
    print(f"Top Product Share : {top_product_share:.2f}%")

    print("\n========================================")
    print("       PRODUCT ACTIVITY")
    print("========================================")
    print(f"Activity Status : {activity_status}")

    print("\n========================================")
    print("       DATA CONFIDENCE")
    print("========================================")
    print(f"Confidence      : {confidence}")

    print("\n========================================")
    print("      MANAGEMENT DECISION")
    print("========================================")
    print(f"Recommendation  : {recommendation}")

    print("\n========================================")
    print("       MANAGEMENT SUMMARY")
    print("========================================")

    if best_product:

        print(
            f"• Top product is "
            f"{best_product['product_name']}."
        )

        print(
            f"• It generated "
            f"₦{float(best_product['revenue'] or 0):,.2f}."
        )

    print(
        f"• {total_products} product(s) generated sales."
    )

    print(
        f"• Total product quantity sold is "
        f"{total_quantity:,.2f}."
    )

    print(
        f"• Product revenue is "
        f"₦{total_revenue:,.2f}."
    )

    print(
        f"• Sales concentration is {concentration}."
    )

    print(
        f"• Data confidence is {confidence}."
    )

    print(
        f"• Recommendation: {recommendation}."
    )

    print("----------------------------------------")
    print("V32 STATUS : READ-ONLY")
    print("Sales/product records were NOT modified.")
    print("========================================")

    conn.close()

    input("\nPress Enter to continue...")


if __name__ == "__main__":
    product_sales_intelligence()
