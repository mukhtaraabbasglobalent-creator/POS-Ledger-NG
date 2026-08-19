import sqlite3

DB_PATH = "data/posledger.db"


def sales_reconciliation_repair():
    print("=" * 40)
    print("       POS LEDGER NG V37")
    print("   SALES RECONCILIATION REPAIR")
    print("=" * 40)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    proposals = []

    # --------------------------------------------------
    # Find completed sales without sale_items
    # --------------------------------------------------

    cur.execute("""
        SELECT
            s.id,
            s.product_id,
            s.quantity,
            s.buying_price,
            s.selling_price,
            s.total_amount,
            s.total_profit,
            s.sale_date,
            s.receipt_no
        FROM sales s
        LEFT JOIN sale_items si
            ON si.sale_id = s.id
        WHERE
            (s.status IS NULL OR s.status != 'CANCELLED')
            AND si.id IS NULL
        ORDER BY s.id
    """)

    missing_items = cur.fetchall()

    for sale in missing_items:
        expected_profit = (
            sale["quantity"] *
            (sale["selling_price"] - sale["buying_price"])
        )

        expected_subtotal = (
            sale["quantity"] *
            sale["selling_price"]
        )

        proposals.append({
            "type": "MISSING_ITEM",
            "sale_id": sale["id"],
            "product_id": sale["product_id"],
            "quantity": sale["quantity"],
            "buying_price": sale["buying_price"],
            "selling_price": sale["selling_price"],
            "subtotal": expected_subtotal,
            "profit": expected_profit,
        })

    # --------------------------------------------------
    # Find mismatched sale_items
    # --------------------------------------------------

    cur.execute("""
        SELECT
            si.id AS item_id,
            si.sale_id,
            si.product_id AS item_product_id,
            si.quantity AS item_quantity,
            si.buying_price AS item_buying_price,
            si.selling_price AS item_selling_price,
            si.profit AS item_profit,
            si.subtotal AS item_subtotal,

            s.product_id AS sale_product_id,
            s.quantity AS sale_quantity,
            s.buying_price AS sale_buying_price,
            s.selling_price AS sale_selling_price,
            s.total_profit AS sale_profit,
            s.total_amount AS sale_amount

        FROM sale_items si
        JOIN sales s
            ON s.id = si.sale_id
        WHERE
            s.product_id != si.product_id
            OR ABS(s.quantity - si.quantity) > 0.000001
            OR ABS(s.buying_price - si.buying_price) > 0.000001
            OR ABS(s.selling_price - si.selling_price) > 0.000001
            OR ABS(
                si.profit -
                (
                    si.quantity *
                    (si.selling_price - si.buying_price)
                )
            ) > 0.000001
            OR ABS(
                si.subtotal -
                (
                    si.quantity *
                    si.selling_price
                )
            ) > 0.000001
        ORDER BY si.id
    """)

    mismatches = cur.fetchall()

    for row in mismatches:
        expected_profit = (
            row["sale_quantity"] *
            (
                row["sale_selling_price"] -
                row["sale_buying_price"]
            )
        )

        expected_subtotal = (
            row["sale_quantity"] *
            row["sale_selling_price"]
        )

        proposals.append({
            "type": "MISMATCH",
            "item_id": row["item_id"],
            "sale_id": row["sale_id"],
            "product_id": row["sale_product_id"],
            "quantity": row["sale_quantity"],
            "buying_price": row["sale_buying_price"],
            "selling_price": row["sale_selling_price"],
            "subtotal": expected_subtotal,
            "profit": expected_profit,
        })

    # --------------------------------------------------
    # Display proposal
    # --------------------------------------------------

    print("\n" + "=" * 40)
    print("       PROPOSED REPAIR PLAN")
    print("=" * 40)

    if not proposals:
        print("No repair proposals generated.")
    else:
        for number, item in enumerate(proposals, 1):

            print("-" * 40)
            print(f"Proposal #{number}")
            print(f"Type        : {item['type']}")
            print(f"Sale ID     : {item['sale_id']}")

            if item["type"] == "MISMATCH":
                print(f"Item ID     : {item['item_id']}")
                print("Action      : CORRECT EXISTING SALE ITEM")
            else:
                print("Item ID     : NONE")
                print("Action      : CREATE MISSING SALE ITEM")

            print(f"Product ID  : {item['product_id']}")
            print(f"Quantity    : {item['quantity']:.2f}")
            print(
                f"Buying      : ₦{item['buying_price']:,.2f}"
            )
            print(
                f"Selling     : ₦{item['selling_price']:,.2f}"
            )
            print(
                f"Subtotal    : ₦{item['subtotal']:,.2f}"
            )
            print(
                f"Profit      : ₦{item['profit']:,.2f}"
            )

    # --------------------------------------------------
    # Summary
    # --------------------------------------------------

    missing_count = sum(
        1 for x in proposals
        if x["type"] == "MISSING_ITEM"
    )

    mismatch_count = sum(
        1 for x in proposals
        if x["type"] == "MISMATCH"
    )

    proposed_revenue = sum(
        x["subtotal"]
        for x in proposals
    )

    proposed_profit = sum(
        x["profit"]
        for x in proposals
    )

    print("\n" + "=" * 40)
    print("        REPAIR SUMMARY")
    print("=" * 40)

    print(f"Total Proposals : {len(proposals)}")
    print(f"Missing Items   : {missing_count}")
    print(f"Mismatches      : {mismatch_count}")
    print(
        f"Proposed Revenue: ₦{proposed_revenue:,.2f}"
    )
    print(
        f"Proposed Profit : ₦{proposed_profit:,.2f}"
    )

    print("\n" + "=" * 40)
    print("        SAFETY STATUS")
    print("=" * 40)

    print("Mode            : READ-ONLY")
    print("Database changed: NO")
    print("Records changed : NO")
    print("Repair executed : NO")

    print("\nRepair proposals are informational only.")
    print("No financial records were modified.")

    print("=" * 40)

    conn.close()


if __name__ == "__main__":
    sales_reconciliation_repair()
