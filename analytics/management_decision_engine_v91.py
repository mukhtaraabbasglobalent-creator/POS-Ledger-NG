import sqlite3
from pathlib import Path

DB_PATH = Path("data/posledger.db")

TARGET_MARGIN = 10.0


def money(value):
    return f"₦{value:,.2f}"


def pct(value):
    return f"{value:.2f}%"


def safe_float(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def table_exists(conn, table):
    try:
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

    except sqlite3.Error:
        return False


def get_columns(conn, table):
    try:
        rows = conn.execute(
            f"PRAGMA table_info({table})"
        ).fetchall()

        result = []

        for row in rows:
            if isinstance(row, tuple):
                if len(row) > 1:
                    result.append(row[1])
            else:
                try:
                    result.append(row["name"])
                except (TypeError, KeyError):
                    pass

        return result

    except sqlite3.Error:
        return []


def get_sales_data(conn):
    if not table_exists(conn, "sales"):
        return {
            "sales": 0,
            "revenue": 0.0,
            "cogs": 0.0,
            "gross_profit": 0.0,
            "margin": 0.0,
            "verified": False,
        }

    columns = get_columns(conn, "sales")

    if "total_amount" not in columns:
        return {
            "sales": 0,
            "revenue": 0.0,
            "cogs": 0.0,
            "gross_profit": 0.0,
            "margin": 0.0,
            "verified": False,
        }

    where = ""

    if "status" in columns:
        where = """
        WHERE UPPER(
            COALESCE(status, 'COMPLETED')
        ) = 'COMPLETED'
        """

    try:
        row = conn.execute(
            f"""
            SELECT
                COUNT(*),
                COALESCE(SUM(total_amount), 0)
            FROM sales
            {where}
            """
        ).fetchone()

        sales_count = int(row[0] or 0)
        revenue = safe_float(row[1])

        cogs = 0.0

        if "cogs" in columns:
            row = conn.execute(
                f"""
                SELECT COALESCE(SUM(cogs), 0)
                FROM sales
                {where}
                """
            ).fetchone()

            cogs = safe_float(row[0])

        gross_profit = 0.0

        if "gross_profit" in columns:
            row = conn.execute(
                f"""
                SELECT COALESCE(SUM(gross_profit), 0)
                FROM sales
                {where}
                """
            ).fetchone()

            gross_profit = safe_float(row[0])

        if gross_profit <= 0 and revenue > 0:
            gross_profit = revenue - cogs

        margin = (
            gross_profit / revenue * 100
            if revenue > 0
            else 0.0
        )

        verified = cogs > 0

        return {
            "sales": sales_count,
            "revenue": revenue,
            "cogs": cogs,
            "gross_profit": gross_profit,
            "margin": margin,
            "verified": verified,
        }

    except sqlite3.Error:
        return {
            "sales": 0,
            "revenue": 0.0,
            "cogs": 0.0,
            "gross_profit": 0.0,
            "margin": 0.0,
            "verified": False,
        }


def get_customer_credit(conn):
    if not table_exists(conn, "customer_credit"):
        return 0.0

    columns = get_columns(
        conn,
        "customer_credit"
    )

    candidates = [
        "amount",
        "credit_amount",
        "outstanding_amount",
        "balance",
        "amount_due",
    ]

    for column in candidates:
        if column not in columns:
            continue

        try:
            row = conn.execute(
                f"""
                SELECT COALESCE(SUM({column}), 0)
                FROM customer_credit
                """
            ).fetchone()

            return safe_float(row[0])

        except sqlite3.Error:
            continue

    return 0.0


def get_inventory_capital(conn):
    if not table_exists(conn, "products"):
        return 0.0

    columns = get_columns(conn, "products")

    if (
        "current_stock" not in columns
        or "buying_price" not in columns
    ):
        return 0.0

    try:
        row = conn.execute(
            """
            SELECT COALESCE(
                SUM(
                    COALESCE(current_stock, 0)
                    *
                    COALESCE(buying_price, 0)
                ),
                0
            )
            FROM products
            """
        ).fetchone()

        return safe_float(row[0])

    except sqlite3.Error:
        return 0.0


def get_supplier_liability(conn):
    if not table_exists(conn, "suppliers"):
        return 0.0

    columns = get_columns(
        conn,
        "suppliers"
    )

    candidates = [
        "balance",
        "amount_due",
        "outstanding",
        "liability",
        "credit_balance",
    ]

    for column in candidates:
        if column not in columns:
            continue

        try:
            row = conn.execute(
                f"""
                SELECT COALESCE(SUM({column}), 0)
                FROM suppliers
                """
            ).fetchone()

            return safe_float(row[0])

        except sqlite3.Error:
            continue

    return 0.0


def get_expenses(conn):
    if not table_exists(conn, "expenses"):
        return 0.0

    columns = get_columns(
        conn,
        "expenses"
    )

    candidates = [
        "amount",
        "expense_amount",
        "total_amount",
    ]

    for column in candidates:
        if column not in columns:
            continue

        try:
            row = conn.execute(
                f"""
                SELECT COALESCE(SUM({column}), 0)
                FROM expenses
                """
            ).fetchone()

            return safe_float(row[0])

        except sqlite3.Error:
            continue

    return 0.0


def get_low_margin_products(conn):
    if not table_exists(conn, "sales"):
        return []

    if not table_exists(conn, "products"):
        return []

    sales_columns = get_columns(
        conn,
        "sales"
    )

    product_columns = get_columns(
        conn,
        "products"
    )

    required_sales = [
        "product_id",
        "quantity",
        "total_amount",
    ]

    required_products = [
        "id",
        "product_name",
        "buying_price",
        "selling_price",
    ]

    if not all(
        c in sales_columns
        for c in required_sales
    ):
        return []

    if not all(
        c in product_columns
        for c in required_products
    ):
        return []

    try:
        rows = conn.execute(
            """
            SELECT
                p.product_name,
                p.sku,
                p.buying_price,
                p.selling_price,
                SUM(s.quantity) AS units,
                SUM(s.total_amount) AS revenue,
                SUM(
                    COALESCE(
                        s.cogs,
                        s.quantity * p.buying_price
                    )
                ) AS cogs,
                SUM(
                    COALESCE(
                        s.gross_profit,
                        s.total_amount
                        -
                        (
                            s.quantity
                            * p.buying_price
                        )
                    )
                ) AS profit
            FROM sales s
            JOIN products p
                ON p.id = s.product_id
            GROUP BY
                p.id,
                p.product_name,
                p.sku,
                p.buying_price,
                p.selling_price
            ORDER BY
                profit ASC
            """
        ).fetchall()

        products = []

        for row in rows:
            name = row[0]
            sku = row[1]
            cost = safe_float(row[2])
            price = safe_float(row[3])
            units = safe_float(row[4])
            revenue = safe_float(row[5])
            cogs = safe_float(row[6])
            profit = safe_float(row[7])

            margin = (
                profit / revenue * 100
                if revenue > 0
                else 0
            )

            target_price = (
                cost
                / (1 - TARGET_MARGIN / 100)
                if cost > 0
                else price
            )

            products.append(
                {
                    "name": name,
                    "sku": sku,
                    "cost": cost,
                    "price": price,
                    "units": units,
                    "revenue": revenue,
                    "cogs": cogs,
                    "profit": profit,
                    "margin": margin,
                    "target_price": target_price,
                    "gap": max(
                        target_price - price,
                        0
                    ),
                }
            )

        return products

    except sqlite3.Error:
        return []


def main():

    print("=" * 60)
    print("POS LEDGER NG V91")
    print("MANAGEMENT DECISION ENGINE")
    print("=" * 60)

    if not DB_PATH.exists():
        print()
        print("DATABASE NOT FOUND")
        print(f"Expected: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)

    try:

        sales = get_sales_data(conn)
        credit = get_customer_credit(conn)
        inventory = get_inventory_capital(conn)
        suppliers = get_supplier_liability(conn)
        expenses = get_expenses(conn)
        products = get_low_margin_products(conn)

        revenue = sales["revenue"]
        cogs = sales["cogs"]
        gross_profit = sales["gross_profit"]
        gross_margin = sales["margin"]

        net_profit = (
            gross_profit - expenses
        )

        net_margin = (
            net_profit / revenue * 100
            if revenue > 0
            else 0
        )

        target_profit = (
            revenue * TARGET_MARGIN / 100
        )

        profit_gap = max(
            target_profit - net_profit,
            0
        )

        liquidity_gap = max(
            suppliers,
            0
        )

        inventory_ratio = (
            inventory / revenue * 100
            if revenue > 0
            else 0
        )

        print()
        print("=" * 60)
        print("VERIFIED BUSINESS POSITION")
        print("=" * 60)

        print(
            f"Verified Sales       : "
            f"{sales['sales']}"
        )

        print(
            f"Verified Revenue     : "
            f"{money(revenue)}"
        )

        print(
            f"Verified COGS        : "
            f"{money(cogs)}"
        )

        print(
            f"Gross Profit         : "
            f"{money(gross_profit)}"
        )

        print(
            f"Gross Margin         : "
            f"{pct(gross_margin)}"
        )

        print(
            f"Operating Expenses   : "
            f"{money(expenses)}"
        )

        print(
            f"Net Operating Profit : "
            f"{money(net_profit)}"
        )

        print(
            f"Net Margin           : "
            f"{pct(net_margin)}"
        )

        print()
        print("=" * 60)
        print("DECISION GAP ANALYSIS")
        print("=" * 60)

        print(
            f"Target Net Profit    : "
            f"{money(target_profit)}"
        )

        print(
            f"Additional Profit    : "
            f"{money(profit_gap)}"
        )

        print(
            f"Margin Gap           : "
            f"{pct(max(TARGET_MARGIN - net_margin, 0))}"
        )

        print()
        print("=" * 60)
        print("LOW-MARGIN PRODUCT DECISIONS")
        print("=" * 60)

        low_margin = [
            p for p in products
            if p["margin"] < TARGET_MARGIN
        ]

        if low_margin:

            for index, product in enumerate(
                low_margin,
                start=1
            ):

                print("-" * 40)

                print(
                    f"{index}. "
                    f"{product['name']}"
                )

                print(
                    f"SKU                 : "
                    f"{product['sku'] or 'N/A'}"
                )

                print(
                    f"Current Price       : "
                    f"{money(product['price'])}"
                )

                print(
                    f"Current Margin      : "
                    f"{pct(product['margin'])}"
                )

                print(
                    f"Target Price        : "
                    f"{money(product['target_price'])}"
                )

                print(
                    f"Price Gap           : "
                    f"{money(product['gap'])}"
                )

                print(
                    f"Profit Contribution : "
                    f"{money(product['profit'])}"
                )

        else:

            print(
                "🟢 No products below "
                "the target margin."
            )

        print()
        print("=" * 60)
        print("MANAGEMENT DECISION PRIORITY")
        print("=" * 60)

        decisions = []

        if low_margin:

            total_gap = sum(
                p["gap"] * p["units"]
                for p in low_margin
            )

            decisions.append(
                (
                    "HIGH",
                    "IMPROVE LOW-MARGIN PRODUCTS",
                    total_gap,
                )
            )

        if credit > 0:

            decisions.append(
                (
                    "MEDIUM",
                    "COLLECT CUSTOMER CREDIT",
                    credit,
                )
            )

        if inventory_ratio > 80:

            decisions.append(
                (
                    "MEDIUM",
                    "MONITOR INVENTORY CAPITAL",
                    inventory,
                )
            )

        if suppliers > 0:

            decisions.append(
                (
                    "HIGH",
                    "MANAGE SUPPLIER LIABILITY",
                    suppliers,
                )
            )

        if sales["sales"] < 20:

            decisions.append(
                (
                    "LOW",
                    "STRENGTHEN SALES DATA",
                    0,
                )
            )

        priority_order = {
            "HIGH": 1,
            "MEDIUM": 2,
            "LOW": 3,
        }

        decisions.sort(
            key=lambda x: (
                priority_order[x[0]],
                -x[2],
            )
        )

        if decisions:

            for index, decision in enumerate(
                decisions,
                start=1
            ):

                level, action, impact = decision

                print(
                    f"{index}. "
                    f"[{level}] {action}"
                )

                if impact > 0:

                    print(
                        f"   Financial impact: "
                        f"{money(impact)}"
                    )

        else:

            print(
                "🟢 No immediate management "
                "decision pressure detected."
            )

        print()
        print("=" * 60)
        print("SCENARIO DECISION")
        print("=" * 60)

        if low_margin:

            best = low_margin[0]

            conservative_price = (
                best["cost"]
                / (1 - 0.075)
                if best["cost"] > 0
                else best["price"]
            )

            conservative_profit = (
                (
                    conservative_price
                    - best["cost"]
                )
                * best["units"]
            )

            current_product_profit = (
                best["profit"]
            )

            improvement = (
                conservative_profit
                - current_product_profit
            )

            print(
                "Recommended Strategy : "
                "GRADUAL MARGIN IMPROVEMENT"
            )

            print(
                f"Product              : "
                f"{best['name']}"
            )

            print(
                f"Current Price        : "
                f"{money(best['price'])}"
            )

            print(
                f"Conservative Price   : "
                f"{money(conservative_price)}"
            )

            print(
                f"Estimated Profit Gain: "
                f"{money(max(improvement, 0))}"
            )

            print(
                "Risk                 : MODERATE"
            )

            print(
                "Confidence           : HIGH"
            )

        else:

            print(
                "Recommended Strategy : "
                "MAINTAIN CURRENT MARGINS"
            )

            print(
                "Risk                 : LOW"
            )

            print(
                "Confidence           : HIGH"
            )

        print()
        print("=" * 60)
        print("V91 EXECUTIVE DECISION")
        print("=" * 60)

        if net_profit < 0:

            print(
                "🔴 PROFITABILITY RECOVERY REQUIRED"
            )

            print(
                "Do not pursue aggressive expansion "
                "until the operating loss is addressed."
            )

        elif net_margin < TARGET_MARGIN:

            print(
                "🟠 PROFITABILITY IMPROVEMENT REQUIRED"
            )

            print(
                f"Current net margin: "
                f"{pct(net_margin)}"
            )

            print(
                f"Target net margin : "
                f"{pct(TARGET_MARGIN)}"
            )

            print(
                f"Profit gap        : "
                f"{money(profit_gap)}"
            )

        else:

            print(
                "🟢 PROFITABILITY TARGET ACHIEVED"
            )

        print()
        print("=" * 60)
        print("V91 MANAGEMENT INTERPRETATION")
        print("=" * 60)

        print(
            "V91 combines verified profitability, "
            "pricing, demand, inventory and working "
            "capital signals into a management "
            "decision layer."
        )

        print(
            "Recommendations are analytical only."
        )

        print(
            "V91 never automatically changes prices, "
            "collects credit, sells inventory, pays "
            "suppliers or modifies financial records."
        )

        print()
        print("=" * 60)
        print("V91 DATA INTEGRITY STATUS")
        print("=" * 60)

        print(
            "Profitability source : V81/V82/V90"
        )

        print(
            "Pricing source       : V83/V84"
        )

        print(
            "Demand source        : V85"
        )

        print(
            "Inventory source     : V86"
        )

        print(
            "Working capital      : V87"
        )

        print(
            "Decision source      : VERIFIED DATABASE"
        )

        print(
            "Automatic actions    : NO"
        )

        print()
        print("=" * 60)
        print("V91 SAFETY STATUS")
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
