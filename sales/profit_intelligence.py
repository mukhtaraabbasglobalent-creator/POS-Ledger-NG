import sqlite3

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def get_columns(cur, table):
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


def money(value):
    return f"₦{float(value or 0):,.2f}"


def profit_intelligence():
    conn = get_connection()
    cur = conn.cursor()

    print("\n========================================")
    print("       POS LEDGER NG V33")
    print("        PROFIT INTELLIGENCE")
    print("========================================")

    # --------------------------------------------------
    # Locate tables
    # --------------------------------------------------

    products_table = find_table(
        cur,
        ["products", "product"]
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

    if not products_table:
        print("\nERROR: Products table not found.")
        conn.close()
        input("\nPress Enter to continue...")
        return

    if not items_table:
        print("\nERROR: Sales item table not found.")
        conn.close()
        input("\nPress Enter to continue...")
        return

    # --------------------------------------------------
    # Inspect columns
    # --------------------------------------------------

    product_columns = get_columns(
        cur,
        products_table
    )

    item_columns = get_columns(
        cur,
        items_table
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

    selling_price = first_existing(
        product_columns,
        [
            "selling_price",
            "sale_price",
            "selling_price_per_unit",
            "price"
        ]
    )

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

    item_product_name = first_existing(
        item_columns,
        [
            "product_name",
            "name",
            "item_name"
        ]
    )

    # --------------------------------------------------
    # Validate minimum fields
    # --------------------------------------------------

    if not product_id or not product_name:
        print("\nERROR: Product ID/name fields could not be identified.")
        conn.close()
        input("\nPress Enter to continue...")
        return

    if not buying_price:
        print("\nERROR: Buying/cost price column not found.")
        print("V33 requires product cost information.")
        conn.close()
        input("\nPress Enter to continue...")
        return

    # --------------------------------------------------
    # Build query
    # --------------------------------------------------

    if item_product_id:

        if item_quantity:
            quantity_expression = (
                f"COALESCE(SUM(si.{item_quantity}), 0)"
            )
        else:
            quantity_expression = "COUNT(*)"

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

        query = f"""
            SELECT
                p.{product_id} AS product_id,
                p.{product_name} AS product_name,
                COALESCE(p.{buying_price}, 0) AS cost_price,
                COALESCE(p.{selling_price}, 0) AS current_selling_price,
                {quantity_expression} AS quantity_sold,
                {revenue_expression} AS revenue
            FROM {items_table} si
            INNER JOIN {products_table} p
                ON p.{product_id} = si.{item_product_id}
            GROUP BY
                p.{product_id},
                p.{product_name},
                p.{buying_price},
                p.{selling_price}
            ORDER BY revenue DESC
        """

    elif item_product_name:

        if item_quantity:
            quantity_expression = (
                f"COALESCE(SUM(si.{item_quantity}), 0)"
            )
        else:
            quantity_expression = "COUNT(*)"

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

        query = f"""
            SELECT
                p.{product_id} AS product_id,
                p.{product_name} AS product_name,
                COALESCE(p.{buying_price}, 0) AS cost_price,
                COALESCE(p.{selling_price}, 0) AS current_selling_price,
                {quantity_expression} AS quantity_sold,
                {revenue_expression} AS revenue
            FROM {items_table} si
            INNER JOIN {products_table} p
                ON LOWER(TRIM(p.{product_name}))
                 = LOWER(TRIM(si.{item_product_name}))
            GROUP BY
                p.{product_id},
                p.{product_name},
                p.{buying_price},
                p.{selling_price}
            ORDER BY revenue DESC
        """

    else:

        print("\nERROR: Cannot connect sales items to products.")
        conn.close()
        input("\nPress Enter to continue...")
        return

    # --------------------------------------------------
    # Execute safely
    # --------------------------------------------------

    try:
        rows = cur.execute(query).fetchall()

    except sqlite3.OperationalError as exc:

        print("\n========================================")
        print("       V33 DATABASE COMPATIBILITY")
        print("========================================")
        print(f"Error: {exc}")
        print("----------------------------------------")
        print("Existing records were NOT modified.")
        print("========================================")

        conn.close()
        input("\nPress Enter to continue...")
        return

    # --------------------------------------------------
    # Calculate profit
    # --------------------------------------------------

    results = []

    total_quantity = 0.0
    total_revenue = 0.0
    total_cost = 0.0
    total_profit = 0.0

    for row in rows:

        quantity = float(
            row["quantity_sold"] or 0
        )

        revenue = float(
            row["revenue"] or 0
        )

        cost_price = float(
            row["cost_price"] or 0
        )

        cost = quantity * cost_price

        profit = revenue - cost

        margin = (
            (profit / revenue) * 100
            if revenue > 0
            else 0
        )

        unit_profit = (
            profit / quantity
            if quantity > 0
            else 0
        )

        results.append(
            {
                "product_id": row["product_id"],
                "product_name": row["product_name"],
                "quantity": quantity,
                "cost_price": cost_price,
                "revenue": revenue,
                "cost": cost,
                "profit": profit,
                "margin": margin,
                "unit_profit": unit_profit
            }
        )

        total_quantity += quantity
        total_revenue += revenue
        total_cost += cost
        total_profit += profit

    overall_margin = (
        (total_profit / total_revenue) * 100
        if total_revenue > 0
        else 0
    )

    # --------------------------------------------------
    # Profit ranking
    # --------------------------------------------------

    results_by_profit = sorted(
        results,
        key=lambda x: x["profit"],
        reverse=True
    )

    results_by_margin = sorted(
        results,
        key=lambda x: x["margin"],
        reverse=True
    )

    profitable_products = [
        row
        for row in results
        if row["profit"] > 0
    ]

    weak_margin_products = [
        row
        for row in results
        if 0 <= row["margin"] < 10
    ]

    loss_products = [
        row
        for row in results
        if row["profit"] < 0
    ]

    # --------------------------------------------------
    # Confidence
    # --------------------------------------------------

    if len(results) >= 10 and total_quantity >= 50:
        confidence = "🟢 HIGH"
    elif len(results) >= 5 and total_quantity >= 20:
        confidence = "🟡 MODERATE"
    elif len(results) >= 1:
        confidence = "🟠 LIMITED"
    else:
        confidence = "🔴 VERY LIMITED"

    # --------------------------------------------------
    # Management recommendation
    # --------------------------------------------------

    if not results:
        recommendation = (
            "NO PROFIT DATA AVAILABLE"
        )

    elif loss_products:
        recommendation = (
            "URGENTLY REVIEW LOSS-MAKING PRODUCTS"
        )

    elif weak_margin_products:
        recommendation = (
            "REVIEW LOW-MARGIN PRODUCTS AND PRICING"
        )

    elif overall_margin < 10:
        recommendation = (
            "MONITOR PROFIT MARGIN AND REVIEW PRICING"
        )

    else:
        recommendation = (
            "MAINTAIN PROFITABLE SALES AND MONITOR MARGINS"
        )

    # --------------------------------------------------
    # Output
    # --------------------------------------------------

    print("\n========================================")
    print("        PROFIT POSITION")
    print("========================================")
    print(f"Products With Sales : {len(results)}")
    print(f"Quantity Sold       : {total_quantity:,.2f}")
    print(f"Revenue             : {money(total_revenue)}")
    print(f"Total Cost          : {money(total_cost)}")
    print(f"Gross Profit        : {money(total_profit)}")
    print(f"Gross Margin        : {overall_margin:.2f}%")

    print("\n========================================")
    print("        PROFIT RANKING")
    print("========================================")

    if not results_by_profit:

        print("No product profit records available.")

    else:

        for index, row in enumerate(
            results_by_profit[:10],
            1
        ):

            print("----------------------------------------")
            print(f"#{index} {row['product_name']}")
            print(f"Quantity Sold : {row['quantity']:,.2f}")
            print(f"Revenue       : {money(row['revenue'])}")
            print(f"Cost          : {money(row['cost'])}")
            print(f"Gross Profit  : {money(row['profit'])}")
            print(f"Profit/Unit   : {money(row['unit_profit'])}")
            print(f"Margin        : {row['margin']:.2f}%")

    print("\n========================================")
    print("       MOST PROFITABLE PRODUCT")
    print("========================================")

    if results_by_profit:

        row = results_by_profit[0]

        print(f"Product      : {row['product_name']}")
        print(f"Gross Profit : {money(row['profit'])}")
        print(f"Profit/Unit  : {money(row['unit_profit'])}")
        print(f"Margin       : {row['margin']:.2f}%")

    else:

        print("No profitable product identified.")

    print("\n========================================")
    print("        LOWEST PROFIT")
    print("========================================")

    if results_by_profit:

        row = results_by_profit[-1]

        print(f"Product      : {row['product_name']}")
        print(f"Gross Profit : {money(row['profit'])}")
        print(f"Margin       : {row['margin']:.2f}%")

    else:

        print("No product profit data available.")

    print("\n========================================")
    print("        PROFIT HEALTH")
    print("========================================")

    print(
        f"Profitable Products : "
        f"{len(profitable_products)}"
    )

    print(
        f"Low-Margin Products : "
        f"{len(weak_margin_products)}"
    )

    print(
        f"Loss-Making Products: "
        f"{len(loss_products)}"
    )

    if overall_margin >= 30:
        health = "🟢 STRONG PROFITABILITY"
    elif overall_margin >= 15:
        health = "🟢 HEALTHY PROFITABILITY"
    elif overall_margin >= 10:
        health = "🟡 MODERATE PROFITABILITY"
    elif overall_margin > 0:
        health = "🟠 WEAK PROFITABILITY"
    else:
        health = "🔴 LOSS / NO PROFIT"

    print(f"Profit Health       : {health}")

    print("\n========================================")
    print("       DATA CONFIDENCE")
    print("========================================")
    print(f"Confidence : {confidence}")

    print("\n========================================")
    print("      MANAGEMENT DECISION")
    print("========================================")
    print(f"Recommendation : {recommendation}")

    print("\n========================================")
    print("       MANAGEMENT SUMMARY")
    print("========================================")

    print(
        f"• Revenue is {money(total_revenue)}."
    )

    print(
        f"• Cost of goods is {money(total_cost)}."
    )

    print(
        f"• Gross profit is {money(total_profit)}."
    )

    print(
        f"• Gross margin is {overall_margin:.2f}%."
    )

    print(
        f"• {len(profitable_products)} product(s) "
        f"are profitable."
    )

    print(
        f"• {len(weak_margin_products)} product(s) "
        f"have margins below 10%."
    )

    print(
        f"• {len(loss_products)} product(s) "
        f"are loss-making."
    )

    print(
        f"• Profit health is {health}."
    )

    print(
        f"• Data confidence is {confidence}."
    )

    print(
        f"• Recommendation: {recommendation}."
    )

    print("----------------------------------------")
    print("V33 STATUS : READ-ONLY")
    print("Sales/product records were NOT modified.")
    print("========================================")

    conn.close()

    input("\nPress Enter to continue...")


if __name__ == "__main__":
    profit_intelligence()
