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


def inventory_intelligence():
    conn = get_connection()
    cur = conn.cursor()

    print("\n========================================")
    print("       POS LEDGER NG V34")
    print("     INVENTORY INTELLIGENCE")
    print("========================================")

    # --------------------------------------------------
    # FIND PRODUCT TABLE
    # --------------------------------------------------

    products_table = find_table(
        cur,
        [
            "products",
            "product"
        ]
    )

    if not products_table:
        print("\nERROR: Products table was not found.")
        print("Existing records were NOT modified.")
        conn.close()
        input("\nPress Enter to continue...")
        return

    product_columns = get_columns(
        cur,
        products_table
    )

    # --------------------------------------------------
    # IDENTIFY PRODUCT FIELDS
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

    stock_column = first_existing(
        product_columns,
        [
            "stock",
            "quantity",
            "current_stock",
            "stock_quantity",
            "available_stock",
            "opening_stock"
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
            "price"
        ]
    )

    sku_column = first_existing(
        product_columns,
        [
            "sku",
            "product_code",
            "code"
        ]
    )

    # --------------------------------------------------
    # VALIDATE
    # --------------------------------------------------

    if not product_id or not product_name:
        print("\nERROR: Product ID/name fields could not be identified.")
        print("Detected columns:")
        print(product_columns)
        conn.close()
        input("\nPress Enter to continue...")
        return

    if not stock_column:
        print("\nERROR: Stock quantity column could not be identified.")
        print("Detected product columns:")
        print(product_columns)
        print("----------------------------------------")
        print("V34 requires an existing stock quantity field.")
        print("Existing records were NOT modified.")
        conn.close()
        input("\nPress Enter to continue...")
        return

    # --------------------------------------------------
    # LOAD PRODUCTS
    # --------------------------------------------------

    query = f"""
        SELECT
            {product_id} AS product_id,
            {product_name} AS product_name,
            {stock_column} AS stock_quantity
            {"," + buying_price + " AS buying_price" if buying_price else ""}
            {"," + selling_price + " AS selling_price" if selling_price else ""}
            {"," + sku_column + " AS sku" if sku_column else ""}
        FROM {products_table}
        ORDER BY {product_name}
    """

    try:
        rows = cur.execute(query).fetchall()
    except sqlite3.OperationalError as exc:
        print("\n========================================")
        print("       V34 DATABASE ERROR")
        print("========================================")
        print(f"Error: {exc}")
        print("----------------------------------------")
        print("Existing records were NOT modified.")
        print("========================================")
        conn.close()
        input("\nPress Enter to continue...")
        return

    # --------------------------------------------------
    # ANALYZE INVENTORY
    # --------------------------------------------------

    products = []

    total_stock = 0.0
    total_inventory_cost = 0.0
    total_inventory_retail = 0.0

    out_of_stock = []
    low_stock = []
    healthy_stock = []

    for row in rows:

        quantity = float(
            row["stock_quantity"] or 0
        )

        cost_price = float(
            row["buying_price"] or 0
        ) if buying_price else 0

        sale_price = float(
            row["selling_price"] or 0
        ) if selling_price else 0

        inventory_cost = quantity * cost_price
        inventory_retail = quantity * sale_price

        potential_profit = (
            inventory_retail - inventory_cost
        )

        if quantity <= 0:
            stock_status = "🔴 OUT OF STOCK"
            out_of_stock.append(row["product_name"])

        elif quantity <= 5:
            stock_status = "🟠 LOW STOCK"
            low_stock.append(row["product_name"])

        else:
            stock_status = "🟢 HEALTHY STOCK"
            healthy_stock.append(row["product_name"])

        product = {
            "product_id": row["product_id"],
            "product_name": row["product_name"],
            "quantity": quantity,
            "cost_price": cost_price,
            "selling_price": sale_price,
            "inventory_cost": inventory_cost,
            "inventory_retail": inventory_retail,
            "potential_profit": potential_profit,
            "status": stock_status
        }

        products.append(product)

        total_stock += quantity
        total_inventory_cost += inventory_cost
        total_inventory_retail += inventory_retail

    potential_profit = (
        total_inventory_retail -
        total_inventory_cost
    )

    # --------------------------------------------------
    # INVENTORY HEALTH
    # --------------------------------------------------

    if not products:
        inventory_health = "🔴 NO INVENTORY DATA"

    elif len(out_of_stock) > 0:
        inventory_health = "🔴 STOCKOUT RISK"

    elif len(low_stock) > 0:
        inventory_health = "🟠 REPLENISHMENT NEEDED"

    else:
        inventory_health = "🟢 HEALTHY INVENTORY"

    # --------------------------------------------------
    # DATA CONFIDENCE
    # --------------------------------------------------

    if len(products) >= 10:
        confidence = "🟢 HIGH"
    elif len(products) >= 5:
        confidence = "🟡 MODERATE"
    elif len(products) >= 1:
        confidence = "🟠 LIMITED"
    else:
        confidence = "🔴 VERY LIMITED"

    # --------------------------------------------------
    # MANAGEMENT RECOMMENDATION
    # --------------------------------------------------

    if out_of_stock:
        recommendation = (
            "RESTOCK OUT-OF-STOCK PRODUCTS"
        )

    elif low_stock:
        recommendation = (
            "PLAN REPLENISHMENT FOR LOW-STOCK PRODUCTS"
        )

    elif not products:
        recommendation = (
            "ADD PRODUCTS AND STOCK DATA"
        )

    else:
        recommendation = (
            "MAINTAIN STOCK LEVELS AND MONITOR MOVEMENT"
        )

    # --------------------------------------------------
    # INVENTORY POSITION
    # --------------------------------------------------

    print("\n========================================")
    print("       INVENTORY POSITION")
    print("========================================")
    print(f"Products            : {len(products)}")
    print(f"Total Stock Units   : {total_stock:,.2f}")
    print(f"Inventory Cost      : {money(total_inventory_cost)}")
    print(f"Retail Value        : {money(total_inventory_retail)}")
    print(f"Potential Gross Profit: {money(potential_profit)}")

    # --------------------------------------------------
    # STOCK STATUS
    # --------------------------------------------------

    print("\n========================================")
    print("         STOCK STATUS")
    print("========================================")
    print(f"Healthy Stock       : {len(healthy_stock)}")
    print(f"Low Stock           : {len(low_stock)}")
    print(f"Out of Stock        : {len(out_of_stock)}")
    print(f"Inventory Health    : {inventory_health}")

    # --------------------------------------------------
    # PRODUCT INVENTORY
    # --------------------------------------------------

    print("\n========================================")
    print("      PRODUCT INVENTORY")
    print("========================================")

    if not products:
        print("No products found.")

    else:

        for index, product in enumerate(
            products,
            1
        ):

            print("----------------------------------------")
            print(
                f"#{index} "
                f"{product['product_name']}"
            )
            print(
                f"Stock          : "
                f"{product['quantity']:,.2f}"
            )

            if buying_price:
                print(
                    f"Buying Price   : "
                    f"{money(product['cost_price'])}"
                )

            if selling_price:
                print(
                    f"Selling Price  : "
                    f"{money(product['selling_price'])}"
                )

            print(
                f"Inventory Cost : "
                f"{money(product['inventory_cost'])}"
            )

            print(
                f"Retail Value   : "
                f"{money(product['inventory_retail'])}"
            )

            print(
                f"Status         : "
                f"{product['status']}"
            )

    # --------------------------------------------------
    # LOW STOCK
    # --------------------------------------------------

    print("\n========================================")
    print("          LOW-STOCK PRODUCTS")
    print("========================================")

    if low_stock:

        for name in low_stock:
            print(f"🟠 {name}")

    else:
        print("No low-stock products detected.")

    # --------------------------------------------------
    # OUT OF STOCK
    # --------------------------------------------------

    print("\n========================================")
    print("        OUT-OF-STOCK PRODUCTS")
    print("========================================")

    if out_of_stock:

        for name in out_of_stock:
            print(f"🔴 {name}")

    else:
        print("No out-of-stock products detected.")

    # --------------------------------------------------
    # REPLENISHMENT
    # --------------------------------------------------

    print("\n========================================")
    print("       REPLENISHMENT INTELLIGENCE")
    print("========================================")

    if out_of_stock:

        print(
            "URGENT: Products with zero stock "
            "should be reviewed for restocking."
        )

    elif low_stock:

        print(
            "ATTENTION: Low-stock products "
            "should be considered for replenishment."
        )

    else:

        print(
            "No immediate replenishment warning."
        )

    # --------------------------------------------------
    # DATA CONFIDENCE
    # --------------------------------------------------

    print("\n========================================")
    print("        DATA CONFIDENCE")
    print("========================================")
    print(f"Confidence : {confidence}")

    # --------------------------------------------------
    # MANAGEMENT DECISION
    # --------------------------------------------------

    print("\n========================================")
    print("      MANAGEMENT DECISION")
    print("========================================")
    print(
        f"Recommendation : {recommendation}"
    )

    # --------------------------------------------------
    # MANAGEMENT SUMMARY
    # --------------------------------------------------

    print("\n========================================")
    print("       MANAGEMENT SUMMARY")
    print("========================================")

    print(
        f"• {len(products)} product(s) are "
        f"currently registered."
    )

    print(
        f"• Total stock is "
        f"{total_stock:,.2f} unit(s)."
    )

    print(
        f"• Inventory cost is "
        f"{money(total_inventory_cost)}."
    )

    print(
        f"• Current retail value is "
        f"{money(total_inventory_retail)}."
    )

    print(
        f"• Potential gross profit is "
        f"{money(potential_profit)}."
    )

    print(
        f"• {len(low_stock)} product(s) "
        f"are low-stock."
    )

    print(
        f"• {len(out_of_stock)} product(s) "
        f"are out of stock."
    )

    print(
        f"• Inventory health is "
        f"{inventory_health}."
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
    print("V34 STATUS : READ-ONLY")
    print("Product/inventory records were NOT modified.")
    print("========================================")

    conn.close()

    input("\nPress Enter to continue...")


if __name__ == "__main__":
    inventory_intelligence()
