import sqlite3
from pathlib import Path

DB_PATH = Path("data/posledger.db")


def money(value):
    if value is None:
        return "₦0.00"
    return f"₦{value:,.2f}"


def get_connection():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")
    return sqlite3.connect(DB_PATH)


def tables(conn):
    rows = conn.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        ORDER BY name
    """).fetchall()
    return [r[0] for r in rows]


def columns(conn, table):
    try:
        return [
            r[1]
            for r in conn.execute(
                f'PRAGMA table_info("{table}")'
            ).fetchall()
        ]
    except Exception:
        return []


def find_table(all_tables, candidates):
    lower = {t.lower(): t for t in all_tables}

    for candidate in candidates:
        if candidate.lower() in lower:
            return lower[candidate.lower()]

    for t in all_tables:
        tl = t.lower()
        for candidate in candidates:
            if candidate.lower() in tl:
                return t

    return None


def find_column(cols, candidates):
    lower = {c.lower(): c for c in cols}

    for candidate in candidates:
        if candidate.lower() in lower:
            return lower[candidate.lower()]

    for c in cols:
        cl = c.lower()
        for candidate in candidates:
            if candidate.lower() in cl:
                return c

    return None


def get_numeric_total(conn, table, column):
    if not table or not column:
        return 0.0

    try:
        row = conn.execute(
            f'SELECT COALESCE(SUM("{column}"), 0) FROM "{table}"'
        ).fetchone()
        return float(row[0] or 0)
    except Exception:
        return 0.0


def count_rows(conn, table):
    if not table:
        return 0

    try:
        return int(
            conn.execute(
                f'SELECT COUNT(*) FROM "{table}"'
            ).fetchone()[0]
        )
    except Exception:
        return 0


def main():
    print("=" * 60)
    print("POS LEDGER NG V78")
    print("FINANCIAL DATA RECONCILIATION & COGS LINKAGE INTELLIGENCE")
    print("=" * 60)

    try:
        conn = get_connection()
    except Exception as e:
        print(f"DATABASE ERROR: {e}")
        return

    all_tables = tables(conn)

    sales_table = find_table(
        all_tables,
        ["sales", "sale", "transactions", "transactions_sales"]
    )

    products_table = find_table(
        all_tables,
        ["products", "product"]
    )

    inventory_table = find_table(
        all_tables,
        ["inventory", "stock", "stocks"]
    )

    credit_table = find_table(
        all_tables,
        ["customer_credit", "credits", "credit"]
    )

    suppliers_table = find_table(
        all_tables,
        ["suppliers", "supplier"]
    )

    print()
    print("=" * 60)
    print("DATABASE STRUCTURE")
    print("=" * 60)

    print(f"Sales table       : {sales_table or 'NOT DETECTED'}")
    print(f"Products table    : {products_table or 'NOT DETECTED'}")
    print(f"Inventory table   : {inventory_table or 'NOT DETECTED'}")
    print(f"Credit table      : {credit_table or 'NOT DETECTED'}")
    print(f"Supplier table    : {suppliers_table or 'NOT DETECTED'}")

    print()
    print("=" * 60)
    print("SALES DATA RECONCILIATION")
    print("=" * 60)

    sales_cols = columns(conn, sales_table) if sales_table else []

    revenue_col = find_column(
        sales_cols,
        [
            "total_amount",
            "sale_total",
            "total",
            "amount",
            "selling_total",
            "revenue"
        ]
    )

    quantity_col = find_column(
        sales_cols,
        [
            "quantity",
            "qty",
            "units"
        ]
    )

    product_id_col = find_column(
        sales_cols,
        [
            "product_id",
            "product",
            "sku",
            "product_sku"
        ]
    )

    cost_col = find_column(
        sales_cols,
        [
            "cost",
            "cost_price",
            "buying_cost",
            "purchase_price",
            "unit_cost",
            "cogs",
            "cost_of_goods_sold"
        ]
    )

    print(f"Sales records     : {count_rows(conn, sales_table)}")
    print(f"Revenue column    : {revenue_col or 'NOT DETECTED'}")
    print(f"Quantity column   : {quantity_col or 'NOT DETECTED'}")
    print(f"Product linkage   : {product_id_col or 'NOT DETECTED'}")
    print(f"Cost/COGS column  : {cost_col or 'NOT DETECTED'}")

    revenue = get_numeric_total(
        conn,
        sales_table,
        revenue_col
    )

    sales_cost = get_numeric_total(
        conn,
        sales_table,
        cost_col
    ) if cost_col else None

    print()
    print(f"Detected Revenue  : {money(revenue)}")

    if sales_cost is None:
        print("Detected Sales Cost: UNAVAILABLE")
    else:
        print(f"Detected Sales Cost: {money(sales_cost)}")

    print()
    print("=" * 60)
    print("COGS LINKAGE TEST")
    print("=" * 60)

    products_cols = columns(conn, products_table) if products_table else []

    buying_cost_col = find_column(
        products_cols,
        [
            "buying_price",
            "buying_cost",
            "cost_price",
            "purchase_price",
            "unit_cost"
        ]
    )

    selling_price_col = find_column(
        products_cols,
        [
            "selling_price",
            "sale_price",
            "selling_cost",
            "price"
        ]
    )

    sku_col = find_column(
        products_cols,
        [
            "sku",
            "product_sku",
            "code"
        ]
    )

    print(f"Product SKU       : {sku_col or 'NOT DETECTED'}")
    print(f"Buying cost       : {buying_cost_col or 'NOT DETECTED'}")
    print(f"Selling price     : {selling_price_col or 'NOT DETECTED'}")

    if cost_col:
        cogs_status = "AVAILABLE FROM SALES DATA"
    elif products_table and buying_cost_col and product_id_col:
        cogs_status = "POTENTIALLY DERIVABLE FROM PRODUCT LINKAGE"
    else:
        cogs_status = "NOT RELIABLY AVAILABLE"

    print(f"COGS status       : {cogs_status}")

    print()
    print("=" * 60)
    print("FINANCIAL TRUTH CHECK")
    print("=" * 60)

    truth_status = "REVIEW REQUIRED"

    if revenue <= 0:
        truth_status = "INSUFFICIENT REVENUE DATA"
    elif cost_col and sales_cost is not None:
        gross_profit = revenue - sales_cost
        margin = (
            gross_profit / revenue * 100
            if revenue else 0
        )

        truth_status = "CALCULABLE"

        print(f"Revenue           : {money(revenue)}")
        print(f"COGS              : {money(sales_cost)}")
        print(f"Gross Profit      : {money(gross_profit)}")
        print(f"Gross Margin      : {margin:.2f}%")
    else:
        print(f"Revenue           : {money(revenue)}")
        print("COGS              : UNAVAILABLE")
        print("Gross Profit      : NOT RELIABLY CALCULABLE")
        print("Gross Margin      : NOT RELIABLY CALCULABLE")

    print(f"Financial Truth   : {truth_status}")

    print()
    print("=" * 60)
    print("DATA INTEGRITY FINDINGS")
    print("=" * 60)

    findings = []

    if not sales_table:
        findings.append("SALES TABLE NOT DETECTED")

    if sales_table and not revenue_col:
        findings.append("SALES REVENUE FIELD NOT DETECTED")

    if sales_table and not product_id_col:
        findings.append("SALES-TO-PRODUCT LINKAGE NOT DETECTED")

    if not cost_col:
        findings.append("COGS / SALES COST DATA NOT DIRECTLY AVAILABLE")

    if not products_table:
        findings.append("PRODUCT TABLE NOT DETECTED")

    if products_table and not buying_cost_col:
        findings.append("PRODUCT BUYING COST NOT DETECTED")

    if sales_table and count_rows(conn, sales_table) < 20:
        findings.append("LIMITED SALES HISTORY")

    if findings:
        for item in findings:
            print(f"- {item}")
    else:
        print("- NO MAJOR STRUCTURAL DATA GAPS DETECTED")

    print()
    print("=" * 60)
    print("V78 MANAGEMENT INTERPRETATION")
    print("=" * 60)

    if truth_status == "CALCULABLE":
        print(
            "The database contains sufficient sales-cost information "
            "to calculate gross profitability."
        )
        print(
            "Future KPI modules may use the reconciled COGS data "
            "for profitability analysis."
        )
    else:
        print(
            "POS Ledger NG must not treat revenue as profit."
        )
        print(
            "True gross profit and gross margin remain "
            "unreliable until sales-to-product cost linkage "
            "is verified."
        )
        print(
            "The next development priority is financial data "
            "reconciliation rather than additional scoring."
        )

    print()
    print("=" * 60)
    print("V78 RECOMMENDED DEVELOPMENT PRIORITY")
    print("=" * 60)

    if not product_id_col:
        print("1. LINK EACH SALE TO A PRODUCT / SKU")
    elif not cost_col:
        print("1. DERIVE COGS FROM PRODUCT COST + SALE QUANTITY")

    print("2. STORE COST SNAPSHOT AT THE TIME OF SALE")
    print("3. CALCULATE TRUE COGS PER SALE")
    print("4. CALCULATE TRUE GROSS PROFIT")
    print("5. RECALCULATE GROSS MARGIN")
    print("6. RECONCILE SALES WITH INVENTORY MOVEMENT")
    print("7. ONLY THEN FEED PROFIT DATA INTO KPI INTELLIGENCE")

    print()
    print("=" * 60)
    print("V78 SAFETY STATUS")
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

    conn.close()


if __name__ == "__main__":
    main()
