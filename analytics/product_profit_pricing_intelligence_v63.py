import sqlite3
from pathlib import Path
from dataclasses import dataclass


DB_PATH = Path("data/posledger.db")

TARGET_MARGIN = 0.10


@dataclass
class ProductAnalysis:
    name: str
    sku: str
    cost: float
    selling_price: float
    stock: float
    profit_unit: float
    margin: float
    target_price: float
    additional_profit: float
    status: str


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
        WHERE type = 'table'
        AND name = ?
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
        [
            "name",
            "product_name",
            "title",
        ],
    )

    sku_col = choose_column(
        columns,
        [
            "sku",
            "product_sku",
            "code",
        ],
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
            "selling",
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

    missing = []

    if name_col is None:
        missing.append("product name")

    if cost_col is None:
        missing.append("buying/cost price")

    if selling_col is None:
        missing.append("selling price")

    if missing:
        raise RuntimeError(
            "Required product columns missing: "
            + ", ".join(missing)
        )

    sku_expression = (
        sku_col
        if sku_col
        else "''"
    )

    stock_expression = (
        stock_col
        if stock_col
        else "0"
    )

    query = f"""
        SELECT
            {name_col},
            {sku_expression},
            {cost_col},
            {selling_col},
            {stock_expression}
        FROM products
        ORDER BY {name_col}
    """

    rows = conn.execute(query).fetchall()

    return rows


def analyse_product(row):
    name = str(row[0] or "UNKNOWN PRODUCT")
    sku = str(row[1] or "")

    try:
        cost = float(row[2] or 0)
    except (TypeError, ValueError):
        cost = 0.0

    try:
        selling_price = float(row[3] or 0)
    except (TypeError, ValueError):
        selling_price = 0.0

    try:
        stock = float(row[4] or 0)
    except (TypeError, ValueError):
        stock = 0.0

    profit_unit = selling_price - cost

    if selling_price > 0:
        margin = profit_unit / selling_price
    else:
        margin = 0.0

    # Price required to achieve target margin:
    #
    # Selling Price = Cost / (1 - Target Margin)
    #
    if cost > 0:
        target_price = cost / (
            1 - TARGET_MARGIN
        )
    else:
        target_price = 0.0

    additional_profit = max(
        target_price - selling_price,
        0,
    )

    if cost <= 0:
        status = "⚪ COST DATA REQUIRED"

    elif selling_price <= 0:
        status = "🔴 NO SELLING PRICE"

    elif margin < 0:
        status = "🔴 SELLING BELOW COST"

    elif margin < TARGET_MARGIN:
        status = "🟠 BELOW TARGET"

    elif margin < TARGET_MARGIN + 0.05:
        status = "🟡 ACCEPTABLE"

    else:
        status = "🟢 STRONG MARGIN"

    return ProductAnalysis(
        name=name,
        sku=sku,
        cost=cost,
        selling_price=selling_price,
        stock=stock,
        profit_unit=profit_unit,
        margin=margin,
        target_price=target_price,
        additional_profit=additional_profit,
        status=status,
    )


def analyse_all(rows):
    return [
        analyse_product(row)
        for row in rows
    ]


def print_report(products):
    print("=" * 60)
    print("POS LEDGER NG V63")
    print("PRODUCT PROFIT & PRICING INTELLIGENCE")
    print("=" * 60)

    print("\n" + "=" * 60)
    print("TARGET")
    print("=" * 60)

    print(
        f"Target Gross Margin : "
        f"{TARGET_MARGIN * 100:.2f}%"
    )

    print("\n" + "=" * 60)
    print("PRODUCT PROFIT ANALYSIS")
    print("=" * 60)

    if not products:
        print("No products found.")
        return

    for product in products:
        print("-" * 40)

        print(
            f"Product             : "
            f"{product.name}"
        )

        print(
            f"SKU                 : "
            f"{product.sku or 'N/A'}"
        )

        print(
            f"Buying Cost         : "
            f"{money(product.cost)}"
        )

        print(
            f"Selling Price       : "
            f"{money(product.selling_price)}"
        )

        print(
            f"Stock               : "
            f"{product.stock:g}"
        )

        print(
            f"Profit / Unit       : "
            f"{money(product.profit_unit)}"
        )

        print(
            f"Current Margin      : "
            f"{product.margin * 100:.2f}%"
        )

        print(
            f"Target Price        : "
            f"{money(product.target_price)}"
        )

        print(
            f"Extra Profit/Unit   : "
            f"{money(product.additional_profit)}"
        )

        print(
            f"Status              : "
            f"{product.status}"
        )

    # --------------------------------------------------
    # UNDERPRICED PRODUCTS
    # --------------------------------------------------

    underpriced = [
        p for p in products
        if p.margin < TARGET_MARGIN
        and p.cost > 0
        and p.selling_price > 0
    ]

    print("\n" + "=" * 60)
    print("UNDERPRICED PRODUCTS")
    print("=" * 60)

    if underpriced:
        for product in underpriced:
            print("-" * 40)

            print(
                f"Product             : "
                f"{product.name}"
            )

            print(
                f"Current Price       : "
                f"{money(product.selling_price)}"
            )

            print(
                f"Current Margin      : "
                f"{product.margin * 100:.2f}%"
            )

            print(
                f"Recommended Price   : "
                f"{money(product.target_price)}"
            )

            print(
                f"Additional Profit   : "
                f"{money(product.additional_profit)}"
            )
    else:
        print(
            "No products are currently below "
            "the target margin."
        )

    # --------------------------------------------------
    # BELOW COST
    # --------------------------------------------------

    loss_products = [
        p for p in products
        if p.profit_unit < 0
    ]

    print("\n" + "=" * 60)
    print("SELLING-BELOW-COST ALERTS")
    print("=" * 60)

    if loss_products:
        for product in loss_products:
            print("-" * 40)

            print(
                f"Product             : "
                f"{product.name}"
            )

            print(
                f"Cost                : "
                f"{money(product.cost)}"
            )

            print(
                f"Selling Price       : "
                f"{money(product.selling_price)}"
            )

            print(
                f"Loss / Unit         : "
                f"{money(abs(product.profit_unit))}"
            )
    else:
        print(
            "No products are currently selling "
            "below recorded cost."
        )

    # --------------------------------------------------
    # BEST MARGIN
    # --------------------------------------------------

    valid = [
        p for p in products
        if p.cost > 0
        and p.selling_price > 0
    ]

    print("\n" + "=" * 60)
    print("MARGIN OPPORTUNITY")
    print("=" * 60)

    if valid:
        best = max(
            valid,
            key=lambda p: p.additional_profit,
        )

        print(
            f"Highest Pricing Opportunity : "
            f"{best.name}"
        )

        print(
            f"Current Margin              : "
            f"{best.margin * 100:.2f}%"
        )

        print(
            f"Recommended Price           : "
            f"{money(best.target_price)}"
        )

        print(
            f"Potential Extra Profit/Unit : "
            f"{money(best.additional_profit)}"
        )

    # --------------------------------------------------
    # MANAGEMENT INTERPRETATION
    # --------------------------------------------------

    print("\n" + "=" * 60)
    print("MANAGEMENT INTERPRETATION")
    print("=" * 60)

    if underpriced:
        print(
            "Pricing action is recommended for "
            f"{len(underpriced)} product(s)."
        )

        print(
            "Review customer acceptance before "
            "implementing price changes."
        )
    else:
        print(
            "Product pricing is currently at or "
            "above the target margin."
        )

    if loss_products:
        print(
            "Immediate attention is required for "
            "products selling below cost."
        )

    print("\n" + "=" * 60)
    print("V63 SAFETY STATUS")
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
            rows = load_products(conn)
            products = analyse_all(rows)
            print_report(products)

        finally:
            conn.close()

    except Exception as exc:
        print("=" * 60)
        print("V63 ERROR")
        print("=" * 60)
        print(str(exc))


if __name__ == "__main__":
    main()
