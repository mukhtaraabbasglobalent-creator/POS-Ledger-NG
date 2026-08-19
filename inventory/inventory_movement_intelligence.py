import sqlite3

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

    for name in candidates:
        if name in tables:
            return name

    return None


def get_columns(cur, table):
    return [
        row["name"]
        for row in cur.execute(
            f"PRAGMA table_info({table})"
        ).fetchall()
    ]


def first_existing(columns, candidates):
    for name in candidates:
        if name in columns:
            return name
    return None


def money(value):
    return f"₦{float(value or 0):,.2f}"


def inventory_movement_intelligence():

    conn = get_connection()
    cur = conn.cursor()

    print("\n========================================")
    print("       POS LEDGER NG V35")
    print("  INVENTORY MOVEMENT INTELLIGENCE")
    print("========================================")

    # --------------------------------------------------
    # FIND TABLES
    # --------------------------------------------------

    products_table = find_table(
        cur,
        [
            "products",
            "product"
        ]
    )

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

    if not products_table:

        print("\nERROR: Products table not found.")
        print("Existing records were NOT modified.")

        conn.close()
        input("\nPress Enter to continue...")
        return

    # --------------------------------------------------
    # PRODUCT SCHEMA
    # --------------------------------------------------

    product_columns = get_columns(
        cur,
        products_table
    )

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

    stock_column = first_existing(
        product_columns,
        [
            "stock",
            "quantity",
            "current_stock",
            "stock_quantity",
            "available_stock"
        ]
    )

    buying_price = first_existing(
        product_columns,
        [
            "buying_price",
            "cost_price",
            "purchase_price",
            "average_cost",
            "avg_cost",
            "cost"
        ]
    )

    if not product_id or not product_name:

        print("\nERROR: Product identity fields not detected.")
        print(product_columns)

        conn.close()
        input("\nPress Enter to continue...")
        return

    # --------------------------------------------------
    # LOAD PRODUCTS
    # --------------------------------------------------

    product_select = [
        f"{product_id} AS product_id",
        f"{product_name} AS product_name"
    ]

    if stock_column:
        product_select.append(
            f"COALESCE({stock_column}, 0) AS current_stock"
        )
    else:
        product_select.append(
            "0 AS current_stock"
        )

    if buying_price:
        product_select.append(
            f"COALESCE({buying_price}, 0) AS buying_price"
        )
    else:
        product_select.append(
            "0 AS buying_price"
        )

    product_query = f"""
        SELECT
            {", ".join(product_select)}
        FROM {products_table}
        ORDER BY {product_name}
    """

    try:
        products = cur.execute(
            product_query
        ).fetchall()

    except sqlite3.OperationalError as exc:

        print("\nERROR:", exc)
        print("Existing records were NOT modified.")

        conn.close()
        input("\nPress Enter to continue...")
        return

    # --------------------------------------------------
    # MOVEMENT HELPERS
    # --------------------------------------------------

    def movement_for_table(
        table,
        target_product_id
    ):

        if not table:
            return {
                "quantity": 0.0,
                "records": 0,
                "value": 0.0
            }

        columns = get_columns(
            cur,
            table
        )

        movement_product_id = first_existing(
            columns,
            [
                "product_id",
                "product",
                "productid"
            ]
        )

        quantity_column = first_existing(
            columns,
            [
                "quantity",
                "qty",
                "units",
                "stock_quantity"
            ]
        )

        amount_column = first_existing(
            columns,
            [
                "total_amount",
                "amount",
                "total",
                "cost",
                "purchase_amount"
            ]
        )

        if not movement_product_id or not quantity_column:

            return {
                "quantity": 0.0,
                "records": 0,
                "value": 0.0
            }

        if amount_column:

            value_expression = (
                f"COALESCE(SUM({amount_column}), 0)"
            )

        else:

            value_expression = "0"

        query = f"""
            SELECT
                COALESCE(SUM({quantity_column}), 0)
                    AS quantity,
                COUNT(*) AS records,
                {value_expression} AS value
            FROM {table}
            WHERE {movement_product_id} = ?
        """

        try:

            row = cur.execute(
                query,
                (target_product_id,)
            ).fetchone()

            return {
                "quantity": float(
                    row["quantity"] or 0
                ),
                "records": int(
                    row["records"] or 0
                ),
                "value": float(
                    row["value"] or 0
                )
            }

        except sqlite3.OperationalError:

            return {
                "quantity": 0.0,
                "records": 0,
                "value": 0.0
            }

    # --------------------------------------------------
    # SALES MOVEMENT
    # --------------------------------------------------

    def sales_for_product(
        target_product_id
    ):

        if not sales_items_table:

            return {
                "quantity": 0.0,
                "records": 0
            }

        columns = get_columns(
            cur,
            sales_items_table
        )

        sales_product_id = first_existing(
            columns,
            [
                "product_id",
                "product",
                "productid"
            ]
        )

        quantity_column = first_existing(
            columns,
            [
                "quantity",
                "qty",
                "units"
            ]
        )

        if not sales_product_id or not quantity_column:

            return {
                "quantity": 0.0,
                "records": 0
            }

        query = f"""
            SELECT
                COALESCE(
                    SUM({quantity_column}),
                    0
                ) AS quantity,
                COUNT(*) AS records
            FROM {sales_items_table}
            WHERE {sales_product_id} = ?
        """

        try:

            row = cur.execute(
                query,
                (target_product_id,)
            ).fetchone()

            return {
                "quantity": float(
                    row["quantity"] or 0
                ),
                "records": int(
                    row["records"] or 0
                )
            }

        except sqlite3.OperationalError:

            return {
                "quantity": 0.0,
                "records": 0
            }

    # --------------------------------------------------
    # BUILD MOVEMENT DATA
    # --------------------------------------------------

    results = []

    total_stock_in = 0.0
    total_stock_out = 0.0
    total_sales = 0.0

    for product in products:

        pid = product["product_id"]

        stock_in = movement_for_table(
            stock_in_table,
            pid
        )

        stock_out = movement_for_table(
            stock_out_table,
            pid
        )

        sales = sales_for_product(pid)

        current_stock = float(
            product["current_stock"] or 0
        )

        cost_price = float(
            product["buying_price"] or 0
        )

        movement_total = (
            stock_in["quantity"]
            + stock_out["quantity"]
            + sales["quantity"]
        )

        # Sales are treated as stock-out activity.
        effective_out = (
            stock_out["quantity"]
            + sales["quantity"]
        )

        net_movement = (
            stock_in["quantity"]
            - effective_out
        )

        if effective_out >= 10:
            movement_status = "🚀 FAST MOVING"

        elif effective_out >= 1:
            movement_status = "🟡 MOVING"

        elif stock_in["quantity"] > 0:
            movement_status = "🔵 STOCK RECEIVED"

        else:
            movement_status = "⚪ NO RECORDED MOVEMENT"

        if current_stock <= 0:
            replenishment = "🔴 URGENT RESTOCK"

        elif current_stock <= 5:
            replenishment = "🟠 PLAN RESTOCK"

        elif effective_out > 0 and current_stock <= (
            effective_out * 0.5
        ):
            replenishment = "🟠 MONITOR STOCK"

        else:
            replenishment = "🟢 STOCK OK"

        result = {
            "product_id": pid,
            "product_name": product["product_name"],
            "current_stock": current_stock,
            "stock_in": stock_in["quantity"],
            "stock_out": stock_out["quantity"],
            "sales": sales["quantity"],
            "records_in": stock_in["records"],
            "records_out": stock_out["records"],
            "sales_records": sales["records"],
            "effective_out": effective_out,
            "net_movement": net_movement,
            "movement_total": movement_total,
            "cost_price": cost_price,
            "movement_status": movement_status,
            "replenishment": replenishment
        }

        results.append(result)

        total_stock_in += stock_in["quantity"]
        total_stock_out += stock_out["quantity"]
        total_sales += sales["quantity"]

    # --------------------------------------------------
    # RANKINGS
    # --------------------------------------------------

    fast_moving = sorted(
        results,
        key=lambda x: x["effective_out"],
        reverse=True
    )

    replenishment_priority = [
        row
        for row in results
        if row["replenishment"] != "🟢 STOCK OK"
    ]

    # --------------------------------------------------
    # CONFIDENCE
    # --------------------------------------------------

    total_movement_records = sum(
        row["records_in"]
        + row["records_out"]
        + row["sales_records"]
        for row in results
    )

    if len(results) >= 10 and total_movement_records >= 30:
        confidence = "🟢 HIGH"

    elif len(results) >= 5 and total_movement_records >= 10:
        confidence = "🟡 MODERATE"

    elif total_movement_records > 0:
        confidence = "🟠 LIMITED"

    else:
        confidence = "🔴 VERY LIMITED"

    # --------------------------------------------------
    # MOVEMENT HEALTH
    # --------------------------------------------------

    if not results:

        movement_health = "🔴 NO MOVEMENT DATA"

    elif total_stock_in == 0 and total_stock_out == 0 and total_sales == 0:

        movement_health = "⚪ NO RECORDED MOVEMENT"

    elif replenishment_priority:

        movement_health = "🟠 MOVEMENT REQUIRES ATTENTION"

    else:

        movement_health = "🟢 ACTIVE STOCK MOVEMENT"

    # --------------------------------------------------
    # RECOMMENDATION
    # --------------------------------------------------

    if replenishment_priority:

        recommendation = (
            "PRIORITIZE STOCK REPLENISHMENT "
            "AND MONITOR FAST-MOVING PRODUCTS"
        )

    elif total_stock_out + total_sales > 0:

        recommendation = (
            "MAINTAIN STOCK LEVELS AND "
            "MONITOR PRODUCT MOVEMENT"
        )

    elif total_stock_in > 0:

        recommendation = (
            "MONITOR STOCK RECEIPTS AND "
            "FUTURE SALES MOVEMENT"
        )

    else:

        recommendation = (
            "BUILD MORE INVENTORY MOVEMENT DATA"
        )

    # --------------------------------------------------
    # OUTPUT
    # --------------------------------------------------

    print("\n========================================")
    print("        MOVEMENT POSITION")
    print("========================================")
    print(
        f"Products Analyzed : {len(results)}"
    )
    print(
        f"Stock In          : {total_stock_in:,.2f}"
    )
    print(
        f"Stock Out         : {total_stock_out:,.2f}"
    )
    print(
        f"Sales Movement    : {total_sales:,.2f}"
    )
    print(
        f"Movement Records  : "
        f"{total_movement_records}"
    )

    print("\n========================================")
    print("       PRODUCT MOVEMENT")
    print("========================================")

    if not results:

        print("No products available.")

    else:

        for index, row in enumerate(
            fast_moving,
            1
        ):

            print("----------------------------------------")
            print(
                f"#{index} "
                f"{row['product_name']}"
            )
            print(
                f"Current Stock : "
                f"{row['current_stock']:,.2f}"
            )
            print(
                f"Stock In     : "
                f"{row['stock_in']:,.2f}"
            )
            print(
                f"Stock Out    : "
                f"{row['stock_out']:,.2f}"
            )
            print(
                f"Sales        : "
                f"{row['sales']:,.2f}"
            )
            print(
                f"Net Movement : "
                f"{row['net_movement']:,.2f}"
            )
            print(
                f"Movement     : "
                f"{row['movement_status']}"
            )
            print(
                f"Replenishment: "
                f"{row['replenishment']}"
            )

    # --------------------------------------------------
    # FAST MOVING
    # --------------------------------------------------

    print("\n========================================")
    print("        FAST-MOVING PRODUCTS")
    print("========================================")

    moving_products = [
        row
        for row in fast_moving
        if row["effective_out"] > 0
    ]

    if moving_products:

        for row in moving_products[:10]:

            print(
                f"🚀 {row['product_name']} "
                f"- {row['effective_out']:,.2f} units moved out"
            )

    else:

        print("No product movement recorded.")

    # --------------------------------------------------
    # REPLENISHMENT
    # --------------------------------------------------

    print("\n========================================")
    print("       REPLENISHMENT PRIORITY")
    print("========================================")

    if replenishment_priority:

        for row in replenishment_priority:

            print("----------------------------------------")
            print(
                f"{row['product_name']}"
            )
            print(
                f"Current Stock : "
                f"{row['current_stock']:,.2f}"
            )
            print(
                f"Movement Out  : "
                f"{row['effective_out']:,.2f}"
            )
            print(
                f"Action        : "
                f"{row['replenishment']}"
            )

    else:

        print(
            "No immediate replenishment "
            "priority detected."
        )

    # --------------------------------------------------
    # HEALTH
    # --------------------------------------------------

    print("\n========================================")
    print("        MOVEMENT HEALTH")
    print("========================================")

    print(
        f"Movement Health : "
        f"{movement_health}"
    )

    # --------------------------------------------------
    # CONFIDENCE
    # --------------------------------------------------

    print("\n========================================")
    print("        DATA CONFIDENCE")
    print("========================================")

    print(
        f"Confidence : {confidence}"
    )

    # --------------------------------------------------
    # MANAGEMENT DECISION
    # --------------------------------------------------

    print("\n========================================")
    print("      MANAGEMENT DECISION")
    print("========================================")

    print(
        f"Recommendation : "
        f"{recommendation}"
    )

    # --------------------------------------------------
    # SUMMARY
    # --------------------------------------------------

    print("\n========================================")
    print("       MANAGEMENT SUMMARY")
    print("========================================")

    print(
        f"• {len(results)} product(s) "
        f"were analyzed."
    )

    print(
        f"• Stock-in movement is "
        f"{total_stock_in:,.2f} unit(s)."
    )

    print(
        f"• Stock-out movement is "
        f"{total_stock_out:,.2f} unit(s)."
    )

    print(
        f"• Recorded sales movement is "
        f"{total_sales:,.2f} unit(s)."
    )

    print(
        f"• {len(moving_products)} "
        f"product(s) have recorded movement."
    )

    print(
        f"• {len(replenishment_priority)} "
        f"product(s) need replenishment attention."
    )

    print(
        f"• Movement health is "
        f"{movement_health}."
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
    print("V35 STATUS : READ-ONLY")
    print(
        "Inventory/sales records were NOT modified."
    )
    print("========================================")

    conn.close()

    input("\nPress Enter to continue...")


if __name__ == "__main__":
    inventory_movement_intelligence()
