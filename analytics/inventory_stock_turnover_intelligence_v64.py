import sqlite3
from pathlib import Path
from dataclasses import dataclass


DB_PATH = Path("data/posledger.db")

LOW_STOCK_DAYS = 7
HIGH_STOCK_DAYS = 30


@dataclass
class InventoryAnalysis:
    name: str
    sku: str
    stock: float
    cost: float
    selling_price: float
    inventory_value: float
    units_sold: float
    daily_sales: float
    days_remaining: float
    turnover_status: str
    action: str


def money(value):
    return f"₦{value:,.2f}"


def get_connection():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    return sqlite3.connect(DB_PATH)


def table_exists(conn, table):
    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        AND name=?
        """,
        (table,),
    ).fetchone()

    return row is not None


def get_columns(conn, table):
    if not table_exists(conn, table):
        return set()

    rows = conn.execute(
        f"PRAGMA table_info({table})"
    ).fetchall()

    return {row[1] for row in rows}


def choose_column(columns, candidates):
    for column in candidates:
        if column in columns:
            return column

    return None


def load_products(conn):
    if not table_exists(conn, "products"):
        raise RuntimeError(
            "Products table was not found."
        )

    columns = get_columns(conn, "products")

    name_col = choose_column(
        columns,
        ["name", "product_name", "title"],
    )

    sku_col = choose_column(
        columns,
        ["sku", "product_sku", "code"],
    )

    cost_col = choose_column(
        columns,
        [
            "buying_price",
            "cost_price",
            "purchase_price",
        ],
    )

    selling_col = choose_column(
        columns,
        [
            "selling_price",
            "sale_price",
        ],
    )

    stock_col = choose_column(
        columns,
        [
            "current_stock",
            "stock",
            "quantity",
        ],
    )

    if not name_col:
        raise RuntimeError(
            "Product name column not found."
        )

    if not cost_col:
        raise RuntimeError(
            "Buying/cost price column not found."
        )

    if not selling_col:
        raise RuntimeError(
            "Selling price column not found."
        )

    if not stock_col:
        raise RuntimeError(
            "Stock column not found."
        )

    sku_expression = sku_col or "''"

    query = f"""
        SELECT
            {name_col},
            {sku_expression},
            {cost_col},
            {selling_col},
            {stock_col}
        FROM products
        ORDER BY {name_col}
    """

    return conn.execute(query).fetchall()


def load_sales_data(conn):
    if not table_exists(conn, "sales"):
        return {}

    columns = get_columns(conn, "sales")

    product_col = choose_column(
        columns,
        [
            "product_name",
            "product",
            "name",
        ],
    )

    quantity_col = choose_column(
        columns,
        [
            "quantity",
            "qty",
            "units",
        ],
    )

    date_col = choose_column(
        columns,
        [
            "sale_date",
            "created_at",
            "date",
        ],
    )

    if not product_col or not quantity_col:
        return {}

    date_expression = date_col or "NULL"

    query = f"""
        SELECT
            {product_col},
            COALESCE(SUM({quantity_col}), 0),
            MIN({date_expression}),
            MAX({date_expression})
        FROM sales
        GROUP BY {product_col}
    """

    result = {}

    try:
        rows = conn.execute(query).fetchall()

        for row in rows:
            name = str(row[0] or "").strip().lower()

            result[name] = {
                "units": float(row[1] or 0),
                "first": row[2],
                "last": row[3],
            }

    except sqlite3.Error:
        return {}

    return result


def calculate_days(first_date, last_date):
    if not first_date or not last_date:
        return 1

    try:
        from datetime import datetime

        first = datetime.fromisoformat(
            str(first_date)
        )

        last = datetime.fromisoformat(
            str(last_date)
        )

        days = (last - first).days + 1

        return max(days, 1)

    except Exception:
        return 1


def analyse_product(row, sales_data):
    name = str(row[0] or "UNKNOWN")
    sku = str(row[1] or "")

    cost = float(row[2] or 0)
    selling_price = float(row[3] or 0)
    stock = float(row[4] or 0)

    inventory_value = stock * cost

    key = name.strip().lower()

    sale_info = sales_data.get(
        key,
        {
            "units": 0,
            "first": None,
            "last": None,
        },
    )

    units_sold = sale_info["units"]

    days = calculate_days(
        sale_info["first"],
        sale_info["last"],
    )

    if units_sold > 0:
        daily_sales = units_sold / days
        days_remaining = stock / daily_sales
    else:
        daily_sales = 0
        days_remaining = float("inf")

    if stock <= 0:
        turnover_status = "🔴 OUT OF STOCK"
        action = "RESTOCK REQUIRED"

    elif units_sold == 0:
        turnover_status = "🟠 NO RECORDED SALES"
        action = "REVIEW SLOW-MOVING STOCK"

    elif days_remaining <= LOW_STOCK_DAYS:
        turnover_status = "🔴 FAST / LOW STOCK"
        action = "CONSIDER RESTOCKING"

    elif days_remaining >= HIGH_STOCK_DAYS:
        turnover_status = "🟠 SLOW-MOVING"
        action = "CONTROL FUTURE PURCHASES"

    else:
        turnover_status = "🟢 HEALTHY TURNOVER"
        action = "CONTINUE MONITORING"

    return InventoryAnalysis(
        name=name,
        sku=sku,
        stock=stock,
        cost=cost,
        selling_price=selling_price,
        inventory_value=inventory_value,
        units_sold=units_sold,
        daily_sales=daily_sales,
        days_remaining=days_remaining,
        turnover_status=turnover_status,
        action=action,
    )


def print_days(value):
    if value == float("inf"):
        return "N/A"

    return f"{value:.1f} days"


def print_report(products):
    print("=" * 60)
    print("POS LEDGER NG V64")
    print("INVENTORY STOCK TURNOVER INTELLIGENCE")
    print("=" * 60)

    print("\n" + "=" * 60)
    print("INVENTORY ANALYSIS")
    print("=" * 60)

    if not products:
        print("No products found.")
        return

    total_inventory = 0
    total_units = 0

    for p in products:
        total_inventory += p.inventory_value
        total_units += p.stock

        print("-" * 40)

        print(f"Product             : {p.name}")
        print(f"SKU                 : {p.sku or 'N/A'}")
        print(f"Current Stock       : {p.stock:g}")
        print(f"Buying Cost         : {money(p.cost)}")
        print(f"Inventory Value     : {money(p.inventory_value)}")
        print(f"Units Sold          : {p.units_sold:g}")
        print(f"Daily Sales Rate    : {p.daily_sales:.2f}")
        print(
            f"Estimated Stock Life: "
            f"{print_days(p.days_remaining)}"
        )
        print(f"Turnover Status     : {p.turnover_status}")
        print(f"Recommended Action  : {p.action}")

    print("\n" + "=" * 60)
    print("INVENTORY SUMMARY")
    print("=" * 60)

    print(
        f"Total Inventory Capital : "
        f"{money(total_inventory)}"
    )

    print(
        f"Total Units in Stock   : "
        f"{total_units:g}"
    )

    fast = [
        p for p in products
        if "FAST" in p.turnover_status
    ]

    slow = [
        p for p in products
        if "SLOW" in p.turnover_status
        or "NO RECORDED" in p.turnover_status
    ]

    out = [
        p for p in products
        if "OUT OF STOCK" in p.turnover_status
    ]

    print("\n" + "=" * 60)
    print("STOCK RISK SUMMARY")
    print("=" * 60)

    print(f"Fast / Low Stock     : {len(fast)}")
    print(f"Slow-Moving Products : {len(slow)}")
    print(f"Out of Stock         : {len(out)}")

    print("\n" + "=" * 60)
    print("CAPITAL TIED IN SLOW STOCK")
    print("=" * 60)

    slow_capital = sum(
        p.inventory_value for p in slow
    )

    print(
        f"Slow Stock Capital : "
        f"{money(slow_capital)}"
    )

    if slow:
        for p in slow:
            print(
                f"- {p.name}: "
                f"{money(p.inventory_value)}"
            )
    else:
        print("No slow-moving stock detected.")

    print("\n" + "=" * 60)
    print("MANAGEMENT INTERPRETATION")
    print("=" * 60)

    if out:
        print(
            "Some products are out of stock. "
            "Review replenishment needs."
        )

    if fast:
        print(
            "Some products are selling quickly "
            "and may require closer restocking."
        )

    if slow:
        print(
            "Capital is tied up in slow-moving "
            "or inactive inventory."
        )

    if not fast and not slow and not out:
        print(
            "Inventory turnover currently appears "
            "balanced based on recorded data."
        )

    print("\n" + "=" * 60)
    print("V64 SAFETY STATUS")
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


def main():
    try:
        conn = get_connection()

        try:
            product_rows = load_products(conn)
            sales_data = load_sales_data(conn)

            products = [
                analyse_product(
                    row,
                    sales_data,
                )
                for row in product_rows
            ]

            print_report(products)

        finally:
            conn.close()

    except Exception as exc:
        print("=" * 60)
        print("V64 ERROR")
        print("=" * 60)
        print(str(exc))


if __name__ == "__main__":
    main()
