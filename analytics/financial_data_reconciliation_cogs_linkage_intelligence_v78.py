import sqlite3
from pathlib import Path

DB_PATH = Path("data/posledger.db")


def money(value):
    return f"₦{float(value or 0):,.2f}"


def pct(value):
    return f"{float(value or 0):.2f}%"


def get_columns(conn, table):
    return [
        row[1]
        for row in conn.execute(
            f'PRAGMA table_info("{table}")'
        ).fetchall()
    ]


def find_column(columns, candidates):
    lower = {c.lower(): c for c in columns}

    for candidate in candidates:
        if candidate.lower() in lower:
            return lower[candidate.lower()]

    return None


def main():

    print("=" * 60)
    print("POS LEDGER NG V79")
    print("SALES-TO-PRODUCT COGS RECONCILIATION INTELLIGENCE")
    print("=" * 60)

    if not DB_PATH.exists():
        print("DATABASE ERROR: data/posledger.db not found")
        return

    conn = sqlite3.connect(DB_PATH)

    try:

        sales_columns = get_columns(conn, "sales")
        product_columns = get_columns(conn, "products")

        sale_product_col = find_column(
            sales_columns,
            ["product_id"]
        )

        sale_quantity_col = find_column(
            sales_columns,
            ["quantity", "qty", "units"]
        )

        sale_total_col = find_column(
            sales_columns,
            ["total_amount", "sale_total", "total", "amount"]
        )

        product_id_col = find_column(
            product_columns,
            ["id", "product_id"]
        )

        product_name_col = find_column(
            product_columns,
            ["name", "product_name", "title"]
        )

        buying_price_col = find_column(
            product_columns,
            [
                "buying_price",
                "buying_cost",
                "cost_price",
                "purchase_price"
            ]
        )

        selling_price_col = find_column(
            product_columns,
            [
                "selling_price",
                "sale_price",
                "price"
            ]
        )

        print()
        print("=" * 60)
        print("LINKAGE STRUCTURE")
        print("=" * 60)

        print(
            f"Sales product field : "
            f"{sale_product_col or 'NOT FOUND'}"
        )

        print(
            f"Sales quantity      : "
            f"{sale_quantity_col or 'NOT FOUND'}"
        )

        print(
            f"Sales revenue field : "
            f"{sale_total_col or 'NOT FOUND'}"
        )

        print(
            f"Product ID field    : "
            f"{product_id_col or 'NOT FOUND'}"
        )

        print(
            f"Product name field  : "
            f"{product_name_col or 'NOT FOUND'}"
        )

        print(
            f"Buying price field  : "
            f"{buying_price_col or 'NOT FOUND'}"
        )

        print(
            f"Selling price field : "
            f"{selling_price_col or 'NOT FOUND'}"
        )

        required = [
            sale_product_col,
            sale_quantity_col,
            sale_total_col,
            product_id_col,
            buying_price_col
        ]

        if any(x is None for x in required):
            print()
            print("=" * 60)
            print("RECONCILIATION STATUS")
            print("=" * 60)
            print("Status : 🟡 INCOMPLETE")
            print()
            print(
                "Required sales/product linkage fields "
                "could not all be detected."
            )
            print()
            print("DATABASE MODIFIED : NO")
            return

        query = f"""
            SELECT
                s."{sale_product_col}",
                s."{sale_quantity_col}",
                s."{sale_total_col}",
                p."{product_name_col if product_name_col else product_id_col}",
                p."{buying_price_col}"
            FROM sales s
            LEFT JOIN products p
                ON s."{sale_product_col}"
                = p."{product_id_col}"
        """

        rows = conn.execute(query).fetchall()

        print()
        print("=" * 60)
        print("SALE-BY-SALE COGS RECONCILIATION")
        print("=" * 60)

        total_revenue = 0.0
        total_cogs = 0.0
        valid_sales = 0
        invalid_sales = 0

        for index, row in enumerate(rows, start=1):

            product_id = row[0]
            quantity = row[1]
            revenue = row[2]
            product_name = row[3]
            buying_price = row[4]

            quantity = float(quantity or 0)
            revenue = float(revenue or 0)

            print("-" * 40)
            print(f"Sale #{index}")
            print(f"Product ID       : {product_id}")
            print(f"Product          : {product_name or 'UNKNOWN'}")
            print(f"Quantity         : {quantity:g}")
            print(f"Revenue          : {money(revenue)}")

            if product_name is None:
                print("COGS             : UNAVAILABLE")
                print("Status           : 🔴 PRODUCT NOT FOUND")
                invalid_sales += 1
                continue

            if buying_price is None:
                print("COGS             : UNAVAILABLE")
                print("Status           : 🔴 BUYING PRICE NOT FOUND")
                invalid_sales += 1
                continue

            buying_price = float(buying_price or 0)

            if buying_price < 0:
                print("COGS             : INVALID")
                print("Status           : 🔴 NEGATIVE BUYING PRICE")
                invalid_sales += 1
                continue

            if quantity <= 0:
                print("COGS             : INVALID")
                print("Status           : 🔴 INVALID QUANTITY")
                invalid_sales += 1
                continue

            cogs = quantity * buying_price
            gross_profit = revenue - cogs

            total_revenue += revenue
            total_cogs += cogs
            valid_sales += 1

            print(
                f"Buying Cost/Unit : "
                f"{money(buying_price)}"
            )

            print(
                f"Calculated COGS  : "
                f"{money(cogs)}"
            )

            print(
                f"Gross Profit     : "
                f"{money(gross_profit)}"
            )

            if revenue > 0:
                sale_margin = (
                    gross_profit / revenue
                ) * 100
            else:
                sale_margin = 0

            print(
                f"Gross Margin     : "
                f"{pct(sale_margin)}"
            )

            if gross_profit < 0:
                print("Status           : 🔴 LOSS-MAKING SALE")
            else:
                print("Status           : 🟢 RECONCILED")

        gross_profit = total_revenue - total_cogs

        if total_revenue > 0:
            gross_margin = (
                gross_profit / total_revenue
            ) * 100
        else:
            gross_margin = 0

        print()
        print("=" * 60)
        print("RECONCILIATION SUMMARY")
        print("=" * 60)

        print(
            f"Recorded Sales    : "
            f"{len(rows)}"
        )

        print(
            f"Valid Sales       : "
            f"{valid_sales}"
        )

        print(
            f"Invalid Sales     : "
            f"{invalid_sales}"
        )

        print(
            f"Reconciled Revenue: "
            f"{money(total_revenue)}"
        )

        print(
            f"Calculated COGS   : "
            f"{money(total_cogs)}"
        )

        print(
            f"True Gross Profit : "
            f"{money(gross_profit)}"
        )

        print(
            f"True Gross Margin : "
            f"{pct(gross_margin)}"
        )

        print()
        print("=" * 60)
        print("FINANCIAL TRUTH STATUS")
        print("=" * 60)

        if len(rows) == 0:
            print("Status : 🔴 NO SALES DATA")

        elif invalid_sales > 0:
            print("Status : 🟡 REVIEW REQUIRED")
            print(
                "Some sales could not be reconciled "
                "against product cost."
            )

        else:
            print("Status : 🟢 FULLY RECONCILED")
            print(
                "All recorded sales have a product "
                "and buying-cost linkage."
            )

        print()
        print("=" * 60)
        print("V79 MANAGEMENT INTERPRETATION")
        print("=" * 60)

        if invalid_sales == 0 and len(rows) > 0:

            print(
                "V79 successfully derives COGS from "
                "product buying cost and sale quantity."
            )

            print(
                f"Reconciled gross profit is "
                f"{money(gross_profit)}."
            )

            print(
                f"Reconciled gross margin is "
                f"{pct(gross_margin)}."
            )

            print(
                "Future KPI modules can use this "
                "reconciled profitability data."
            )

        else:

            print(
                "Profitability should not yet be treated "
                "as fully authoritative."
            )

            print(
                "The unresolved sales records require "
                "product/cost reconciliation."
            )

        print()
        print("=" * 60)
        print("V79 SAFETY STATUS")
        print("=" * 60)

        print("Mode                : READ-ONLY")
        print("Database modified   : NO")
        print("Sales modified      : NO")
        print("Products modified   : NO")
        print("Inventory modified  : NO")
        print("Balance modified    : NO")
        print("Credit modified     : NO")
        print("Suppliers modified  : NO")
        print("Expenses modified   : NO")

        print("=" * 60)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
