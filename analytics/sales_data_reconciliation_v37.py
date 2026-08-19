import sqlite3

DB_PATH = "data/posledger.db"


def sales_data_reconciliation():
    print("=" * 40)
    print("       POS LEDGER NG V37")
    print("   SALES DATA RECONCILIATION")
    print("=" * 40)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    issues = []

    # --------------------------------------------------
    # CHECK 1: sales table
    # --------------------------------------------------

    cur.execute("""
        SELECT COUNT(*) AS count
        FROM sales
        WHERE status IS NULL OR status != 'CANCELLED'
    """)

    total_sales = cur.fetchone()["count"]

    # --------------------------------------------------
    # CHECK 2: sale_items records
    # --------------------------------------------------

    cur.execute("""
        SELECT COUNT(*) AS count
        FROM sale_items
    """)

    total_items = cur.fetchone()["count"]

    # --------------------------------------------------
    # CHECK 3: orphan sale_items
    # --------------------------------------------------

    cur.execute("""
        SELECT
            si.id,
            si.sale_id
        FROM sale_items si
        LEFT JOIN sales s
            ON s.id = si.sale_id
        WHERE s.id IS NULL
    """)

    orphan_items = cur.fetchall()

    for row in orphan_items:
        issues.append(
            f"Orphan sale_item {row['id']} references "
            f"missing sale {row['sale_id']}"
        )

    # --------------------------------------------------
    # CHECK 4: product mismatch
    # --------------------------------------------------

    cur.execute("""
        SELECT
            si.id AS item_id,
            si.sale_id,
            s.product_id AS sale_product,
            si.product_id AS item_product
        FROM sale_items si
        JOIN sales s
            ON s.id = si.sale_id
        WHERE s.product_id != si.product_id
    """)

    product_mismatches = cur.fetchall()

    for row in product_mismatches:
        issues.append(
            f"Product mismatch: sale {row['sale_id']} "
            f"uses product {row['sale_product']} but "
            f"sale_item {row['item_id']} uses product "
            f"{row['item_product']}"
        )

    # --------------------------------------------------
    # CHECK 5: quantity mismatch
    # --------------------------------------------------

    cur.execute("""
        SELECT
            si.id AS item_id,
            si.sale_id,
            s.quantity AS sale_quantity,
            si.quantity AS item_quantity
        FROM sale_items si
        JOIN sales s
            ON s.id = si.sale_id
        WHERE ABS(s.quantity - si.quantity) > 0.000001
    """)

    quantity_mismatches = cur.fetchall()

    for row in quantity_mismatches:
        issues.append(
            f"Quantity mismatch: sale {row['sale_id']} "
            f"has {row['sale_quantity']} but "
            f"sale_item {row['item_id']} has "
            f"{row['item_quantity']}"
        )

    # --------------------------------------------------
    # CHECK 6: selling price mismatch
    # --------------------------------------------------

    cur.execute("""
        SELECT
            si.id AS item_id,
            si.sale_id,
            s.selling_price AS sale_price,
            si.selling_price AS item_price
        FROM sale_items si
        JOIN sales s
            ON s.id = si.sale_id
        WHERE ABS(s.selling_price - si.selling_price) > 0.000001
    """)

    price_mismatches = cur.fetchall()

    for row in price_mismatches:
        issues.append(
            f"Selling price mismatch: sale {row['sale_id']} "
            f"has ₦{row['sale_price']:.2f} but "
            f"sale_item {row['item_id']} has "
            f"₦{row['item_price']:.2f}"
        )

    # --------------------------------------------------
    # CHECK 7: subtotal mismatch
    # --------------------------------------------------

    cur.execute("""
        SELECT
            si.id AS item_id,
            si.sale_id,
            si.subtotal,
            (si.quantity * si.selling_price) AS calculated
        FROM sale_items si
        WHERE ABS(
            si.subtotal -
            (si.quantity * si.selling_price)
        ) > 0.000001
    """)

    subtotal_mismatches = cur.fetchall()

    for row in subtotal_mismatches:
        issues.append(
            f"Subtotal mismatch: sale_item {row['item_id']} "
            f"has ₦{row['subtotal']:.2f}, calculated "
            f"₦{row['calculated']:.2f}"
        )

    # --------------------------------------------------
    # CHECK 8: profit mismatch
    # --------------------------------------------------

    cur.execute("""
        SELECT
            si.id AS item_id,
            si.sale_id,
            si.profit,
            (
                si.quantity *
                (si.selling_price - si.buying_price)
            ) AS calculated
        FROM sale_items si
        WHERE ABS(
            si.profit -
            (
                si.quantity *
                (si.selling_price - si.buying_price)
            )
        ) > 0.000001
    """)

    profit_mismatches = cur.fetchall()

    for row in profit_mismatches:
        issues.append(
            f"Profit mismatch: sale_item {row['item_id']} "
            f"has ₦{row['profit']:.2f}, calculated "
            f"₦{row['calculated']:.2f}"
        )

    # --------------------------------------------------
    # CHECK 9: sales without sale_items
    # --------------------------------------------------

    cur.execute("""
        SELECT
            s.id
        FROM sales s
        LEFT JOIN sale_items si
            ON si.sale_id = s.id
        WHERE
            (s.status IS NULL OR s.status != 'CANCELLED')
            AND si.id IS NULL
    """)

    sales_without_items = cur.fetchall()

    for row in sales_without_items:
        issues.append(
            f"Sale {row['id']} has no sale_items record"
        )

    # --------------------------------------------------
    # FINANCIAL TOTALS
    # --------------------------------------------------

    cur.execute("""
        SELECT
            COALESCE(SUM(total_amount), 0) AS revenue,
            COALESCE(SUM(total_profit), 0) AS profit
        FROM sales
        WHERE status IS NULL OR status != 'CANCELLED'
    """)

    sales_totals = cur.fetchone()

    cur.execute("""
        SELECT
            COALESCE(SUM(subtotal), 0) AS revenue,
            COALESCE(SUM(profit), 0) AS profit
        FROM sale_items
    """)

    item_totals = cur.fetchone()

    revenue_difference = (
        sales_totals["revenue"] -
        item_totals["revenue"]
    )

    profit_difference = (
        sales_totals["profit"] -
        item_totals["profit"]
    )

    # --------------------------------------------------
    # REPORT
    # --------------------------------------------------

    print("\n" + "=" * 40)
    print("        RECONCILIATION POSITION")
    print("=" * 40)

    print(f"Completed Sales       : {total_sales}")
    print(f"Sale Items            : {total_items}")
    print(f"Orphan Items          : {len(orphan_items)}")
    print(f"Product Mismatches    : {len(product_mismatches)}")
    print(f"Quantity Mismatches   : {len(quantity_mismatches)}")
    print(f"Price Mismatches      : {len(price_mismatches)}")
    print(f"Subtotal Mismatches   : {len(subtotal_mismatches)}")
    print(f"Profit Mismatches     : {len(profit_mismatches)}")
    print(f"Sales Without Items   : {len(sales_without_items)}")

    print("\n" + "=" * 40)
    print("        FINANCIAL RECONCILIATION")
    print("=" * 40)

    print(
        f"Sales Revenue         : "
        f"₦{sales_totals['revenue']:,.2f}"
    )

    print(
        f"Item Revenue          : "
        f"₦{item_totals['revenue']:,.2f}"
    )

    print(
        f"Revenue Difference    : "
        f"₦{revenue_difference:,.2f}"
    )

    print(
        f"Sales Profit          : "
        f"₦{sales_totals['profit']:,.2f}"
    )

    print(
        f"Item Profit           : "
        f"₦{item_totals['profit']:,.2f}"
    )

    print(
        f"Profit Difference     : "
        f"₦{profit_difference:,.2f}"
    )

    print("\n" + "=" * 40)
    print("       RECONCILIATION STATUS")
    print("=" * 40)

    if issues:
        print("Status                : 🔴 DATA RECONCILIATION REQUIRED")
        print(f"Issues Detected       : {len(issues)}")

        print("\n" + "=" * 40)
        print("          DETECTED ISSUES")
        print("=" * 40)

        for index, issue in enumerate(issues, 1):
            print(f"{index}. {issue}")

    else:
        print("Status                : 🟢 RECONCILIATION PASS")
        print("No sales relationship inconsistencies detected.")

    print("\n" + "=" * 40)
    print("       INTEGRITY SAFETY")
    print("=" * 40)

    print("Mode                  : READ-ONLY")
    print("Database modified     : NO")
    print("Sales modified        : NO")
    print("Sale items modified   : NO")

    print("=" * 40)

    conn.close()


if __name__ == "__main__":
    sales_data_reconciliation()
