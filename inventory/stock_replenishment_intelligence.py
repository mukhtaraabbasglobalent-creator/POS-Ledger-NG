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
            "SELECT name FROM sqlite_master "
            "WHERE type='table'"
        ).fetchall()
    }

    for table in candidates:
        if table in tables:
            return table

    return None


def get_columns(cur, table):
    return [
        row["name"]
        for row in cur.execute(
            f"PRAGMA table_info({table})"
        ).fetchall()
    ]


def first_existing(columns, candidates):
    for column in candidates:
        if column in columns:
            return column
    return None


def money(value):
    return f"₦{float(value or 0):,.2f}"


def stock_replenishment_intelligence():

    conn = get_connection()
    cur = conn.cursor()

    print("\n========================================")
    print("       POS LEDGER NG V36")
    print("   STOCK REPLENISHMENT INTELLIGENCE")
    print("========================================")

    # --------------------------------------------------
    # FIND PRODUCTS TABLE
    # --------------------------------------------------

    products_table = find_table(
        cur,
        [
            "products",
            "product"
        ]
    )

    if not products_table:
        print("\nERROR: Products table not found.")
        print("Existing records were NOT modified.")
        conn.close()
        input("\nPress Enter to continue...")
        return

    columns = get_columns(cur, products_table)

    product_id = first_existing(
        columns,
        ["id", "product_id"]
    )

    product_name = first_existing(
        columns,
        ["name", "product_name", "title"]
    )

    stock_column = first_existing(
        columns,
        [
            "stock",
            "quantity",
            "current_stock",
            "stock_quantity",
            "available_stock"
        ]
    )

    buying_price = first_existing(
        columns,
        [
            "buying_price",
            "cost_price",
            "purchase_price",
            "average_cost",
            "avg_cost",
            "cost"
        ]
    )

    selling_price = first_existing(
        columns,
        [
            "selling_price",
            "sale_price",
            "selling",
            "price"
        ]
    )

    if not product_id or not product_name:
        print("\nERROR: Product identity fields not found.")
        print(columns)
        conn.close()
        input("\nPress Enter to continue...")
        return

    # --------------------------------------------------
    # OPTIONAL MOVEMENT TABLES
    # --------------------------------------------------

    stock_in_table = find_table(
        cur,
        [
            "stock_in",
            "stock_in_history",
            "inventory_stock_in",
            "stock_purchases",
            "purchases"
        ]
    )

    stock_out_table = find_table(
        cur,
        [
            "stock_out",
            "stock_out_history",
            "inventory_stock_out",
            "stock_issues"
        ]
    )

    sales_items_table = find_table(
        cur,
        [
            "sale_items",
            "sales_items",
            "sale_details",
            "sales_details",
            "transaction_items"
        ]
    )

    # --------------------------------------------------
    # LOAD PRODUCTS
    # --------------------------------------------------

    select_fields = [
        f"{product_id} AS product_id",
        f"{product_name} AS product_name"
    ]

    if stock_column:
        select_fields.append(
            f"COALESCE({stock_column}, 0) AS current_stock"
        )
    else:
        select_fields.append(
            "0 AS current_stock"
        )

    if buying_price:
        select_fields.append(
            f"COALESCE({buying_price}, 0) AS buying_price"
        )
    else:
        select_fields.append(
            "0 AS buying_price"
        )

    if selling_price:
        select_fields.append(
            f"COALESCE({selling_price}, 0) AS selling_price"
        )
    else:
        select_fields.append(
            "0 AS selling_price"
        )

    try:
        products = cur.execute(
            f"""
            SELECT {", ".join(select_fields)}
            FROM {products_table}
            ORDER BY {product_name}
            """
        ).fetchall()

    except sqlite3.OperationalError as exc:
        print("\nERROR:", exc)
        print("Existing records were NOT modified.")
        conn.close()
        input("\nPress Enter to continue...")
        return

    # --------------------------------------------------
    # MOVEMENT FUNCTION
    # --------------------------------------------------

    def get_movement(table, pid):

        if not table:
            return 0.0, 0

        table_columns = get_columns(
            cur,
            table
        )

        movement_product_id = first_existing(
            table_columns,
            [
                "product_id",
                "product",
                "productid"
            ]
        )

        quantity_column = first_existing(
            table_columns,
            [
                "quantity",
                "qty",
                "units",
                "stock_quantity"
            ]
        )

        if not movement_product_id or not quantity_column:
            return 0.0, 0

        try:
            row = cur.execute(
                f"""
                SELECT
                    COALESCE(
                        SUM({quantity_column}),
                        0
                    ) AS quantity,
                    COUNT(*) AS records
                FROM {table}
                WHERE {movement_product_id} = ?
                """,
                (pid,)
            ).fetchone()

            return (
                float(row["quantity"] or 0),
                int(row["records"] or 0)
            )

        except sqlite3.OperationalError:
            return 0.0, 0

    # --------------------------------------------------
    # SALES FUNCTION
    # --------------------------------------------------

    def get_sales(pid):

        if not sales_items_table:
            return 0.0, 0

        table_columns = get_columns(
            cur,
            sales_items_table
        )

        sales_product_id = first_existing(
            table_columns,
            [
                "product_id",
                "product",
                "productid"
            ]
        )

        quantity_column = first_existing(
            table_columns,
            [
                "quantity",
                "qty",
                "units"
            ]
        )

        if not sales_product_id or not quantity_column:
            return 0.0, 0

        try:
            row = cur.execute(
                f"""
                SELECT
                    COALESCE(
                        SUM({quantity_column}),
                        0
                    ) AS quantity,
                    COUNT(*) AS records
                FROM {sales_items_table}
                WHERE {sales_product_id} = ?
                """,
                (pid,)
            ).fetchone()

            return (
                float(row["quantity"] or 0),
                int(row["records"] or 0)
            )

        except sqlite3.OperationalError:
            return 0.0, 0

    # --------------------------------------------------
    # BUILD REPLENISHMENT DATA
    # --------------------------------------------------

    results = []

    for product in products:

        pid = product["product_id"]

        current_stock = float(
            product["current_stock"] or 0
        )

        cost_price = float(
            product["buying_price"] or 0
        )

        selling_price = float(
            product["selling_price"] or 0
        )

        stock_in, stock_in_records = get_movement(
            stock_in_table,
            pid
        )

        stock_out, stock_out_records = get_movement(
            stock_out_table,
            pid
        )

        sales, sales_records = get_sales(pid)

        effective_out = (
            stock_out + sales
        )

        # --------------------------------------------------
        # SALES VELOCITY
        # --------------------------------------------------

        if sales >= 20:
            velocity = "VERY HIGH"

        elif sales >= 10:
            velocity = "HIGH"

        elif sales >= 5:
            velocity = "MODERATE"

        elif sales > 0:
            velocity = "LOW"

        else:
            velocity = "NONE"

        # --------------------------------------------------
        # STOCK LEVEL
        # --------------------------------------------------

        if current_stock <= 0:
            stock_status = "🔴 OUT OF STOCK"

        elif current_stock <= 5:
            stock_status = "🟠 CRITICAL STOCK"

        elif current_stock <= 10:
            stock_status = "🟡 LOW STOCK"

        else:
            stock_status = "🟢 HEALTHY STOCK"

        # --------------------------------------------------
        # COVER ESTIMATE
        # --------------------------------------------------

        if sales > 0:

            estimated_cover = (
                current_stock / sales
            ) * 30

        else:

            estimated_cover = None

        # --------------------------------------------------
        # REORDER QUANTITY
        # --------------------------------------------------

        if sales > 0:

            target_stock = max(
                10,
                sales * 0.5
            )

            reorder_quantity = max(
                0,
                target_stock - current_stock
            )

        else:

            reorder_quantity = 0

        # --------------------------------------------------
        # PRIORITY SCORE
        # --------------------------------------------------

        score = 0

        if current_stock <= 0:
            score += 60

        elif current_stock <= 5:
            score += 45

        elif current_stock <= 10:
            score += 25

        elif current_stock <= 15:
            score += 10

        if sales >= 20:
            score += 30

        elif sales >= 10:
            score += 25

        elif sales >= 5:
            score += 15

        elif sales > 0:
            score += 5

        if estimated_cover is not None:

            if estimated_cover < 7:
                score += 20

            elif estimated_cover < 14:
                score += 10

        score = min(
            score,
            100
        )

        # --------------------------------------------------
        # PRIORITY
        # --------------------------------------------------

        if score >= 70:
            priority = "🔴 URGENT"

        elif score >= 45:
            priority = "🟠 HIGH"

        elif score >= 25:
            priority = "🟡 MEDIUM"

        else:
            priority = "🟢 MONITOR"

        # --------------------------------------------------
        # ACTION
        # --------------------------------------------------

        if score >= 70:

            action = (
                "RESTOCK IMMEDIATELY"
            )

        elif score >= 45:

            action = (
                "PLAN RESTOCK SOON"
            )

        elif score >= 25:

            action = (
                "MONITOR STOCK AND SALES"
            )

        else:

            action = (
                "NORMAL STOCK MONITORING"
            )

        # --------------------------------------------------
        # POTENTIAL PROFIT
        # --------------------------------------------------

        unit_margin = (
            selling_price - cost_price
        )

        potential_reorder_profit = (
            reorder_quantity
            * unit_margin
        )

        results.append(
            {
                "product_id": pid,
                "product_name": product["product_name"],
                "stock": current_stock,
                "stock_in": stock_in,
                "stock_out": stock_out,
                "sales": sales,
                "effective_out": effective_out,
                "velocity": velocity,
                "stock_status": stock_status,
                "estimated_cover": estimated_cover,
                "reorder_quantity": reorder_quantity,
                "cost_price": cost_price,
                "selling_price": selling_price,
                "unit_margin": unit_margin,
                "potential_reorder_profit":
                    potential_reorder_profit,
                "score": score,
                "priority": priority,
                "action": action,
                "records":
                    stock_in_records
                    + stock_out_records
                    + sales_records
            }
        )

    # --------------------------------------------------
    # RANK
    # --------------------------------------------------

    results.sort(
        key=lambda x: (
            x["score"],
            x["sales"]
        ),
        reverse=True
    )

    # --------------------------------------------------
    # COUNTS
    # --------------------------------------------------

    urgent = sum(
        1 for x in results
        if x["priority"] == "🔴 URGENT"
    )

    high = sum(
        1 for x in results
        if x["priority"] == "🟠 HIGH"
    )

    medium = sum(
        1 for x in results
        if x["priority"] == "🟡 MEDIUM"
    )

    monitor = sum(
        1 for x in results
        if x["priority"] == "🟢 MONITOR"
    )

    total_reorder = sum(
        x["reorder_quantity"]
        for x in results
    )

    total_profit = sum(
        x["potential_reorder_profit"]
        for x in results
    )

    movement_records = sum(
        x["records"]
        for x in results
    )

    if len(results) >= 10 and movement_records >= 30:
        confidence = "🟢 HIGH"

    elif len(results) >= 5 and movement_records >= 10:
        confidence = "🟡 MODERATE"

    elif movement_records > 0:
        confidence = "🟠 LIMITED"

    else:
        confidence = "🔴 VERY LIMITED"

    if urgent:
        recommendation = (
            "RESTOCK URGENT PRODUCTS "
            "AND PROTECT FAST-MOVING SALES"
        )

    elif high:
        recommendation = (
            "PLAN REPLENISHMENT FOR "
            "HIGH-PRIORITY PRODUCTS"
        )

    elif medium:
        recommendation = (
            "MONITOR STOCK VELOCITY "
            "AND PLAN FUTURE REPLENISHMENT"
        )

    else:
        recommendation = (
            "MAINTAIN CURRENT STOCK LEVELS "
            "AND MONITOR SALES"
        )

    print("\n========================================")
    print("      REPLENISHMENT OVERVIEW")
    print("========================================")
    print(f"Products Analyzed : {len(results)}")
    print(f"Urgent            : {urgent}")
    print(f"High              : {high}")
    print(f"Medium            : {medium}")
    print(f"Monitor           : {monitor}")
    print(
        f"Suggested Reorder : "
        f"{total_reorder:,.2f} units"
    )
    print(
        f"Potential Profit   : "
        f"{money(total_profit)}"
    )

    print("\n========================================")
    print("       REPLENISHMENT PRIORITY")
    print("========================================")

    if results:
        for index, row in enumerate(results, 1):

            print("----------------------------------------")
            print(
                f"#{index} "
                f"{row['product_name']}"
            )
            print(
                f"Current Stock : "
                f"{row['stock']:,.2f}"
            )
            print(
                f"Sales         : "
                f"{row['sales']:,.2f}"
            )
            print(
                f"Velocity      : "
                f"{row['velocity']}"
            )
            print(
                f"Stock Status  : "
                f"{row['stock_status']}"
            )

            if row["estimated_cover"] is None:
                print(
                    "Estimated Cover: "
                    "NO SALES DATA"
                )
            else:
                print(
                    f"Estimated Cover: "
                    f"{row['estimated_cover']:.1f} day(s)"
                )

            print(
                f"Reorder Qty   : "
                f"{row['reorder_quantity']:,.2f}"
            )
            print(
                f"Priority Score: "
                f"{row['score']}/100"
            )
            print(
                f"Priority      : "
                f"{row['priority']}"
            )
            print(
                f"Action        : "
                f"{row['action']}"
            )

    else:
        print("No products available.")

    print("\n========================================")
    print("        TOP RESTOCK ACTION")
    print("========================================")

    if results:
        top = results[0]

        print(
            f"Product       : "
            f"{top['product_name']}"
        )
        print(
            f"Priority      : "
            f"{top['priority']}"
        )
        print(
            f"Action        : "
            f"{top['action']}"
        )
        print(
            f"Reorder Qty   : "
            f"{top['reorder_quantity']:,.2f}"
        )

    else:
        print("No restocking recommendation.")

    print("\n========================================")
    print("        DATA CONFIDENCE")
    print("========================================")
    print(f"Confidence : {confidence}")

    print("\n========================================")
    print("      MANAGEMENT DECISION")
    print("========================================")
    print(
        f"Recommendation : "
        f"{recommendation}"
    )

    print("\n========================================")
    print("       MANAGEMENT SUMMARY")
    print("========================================")
    print(
        f"• {len(results)} product(s) "
        f"were analyzed."
    )
    print(
        f"• {urgent} product(s) "
        f"require urgent replenishment."
    )
    print(
        f"• {high} product(s) "
        f"have high replenishment priority."
    )
    print(
        f"• {medium} product(s) "
        f"have medium priority."
    )
    print(
        f"• Suggested reorder quantity is "
        f"{total_reorder:,.2f} unit(s)."
    )
    print(
        f"• Potential reorder gross profit is "
        f"{money(total_profit)}."
    )
    print(
        f"• Data confidence is "
        f"{confidence}."
    )
    print(
        f"• Recommendation: "
        f"{recommendation}."
    )

    print("----------------------------------------")
    print("V36 STATUS : READ-ONLY")
    print(
        "Product/inventory records were NOT modified."
    )
    print("========================================")

    conn.close()

    input("\nPress Enter to continue...")


if __name__ == "__main__":
    stock_replenishment_intelligence()
