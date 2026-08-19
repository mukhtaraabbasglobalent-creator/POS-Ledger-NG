import sqlite3
from pathlib import Path


DB_PATH = Path("data/posledger.db")


def money(value):
    return f"₦{value:,.2f}"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def table_exists(conn, table):
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,)
    ).fetchone()
    return row is not None


def scalar(conn, query, default=0):
    try:
        row = conn.execute(query).fetchone()
        if row is None or row[0] is None:
            return default
        return float(row[0])
    except sqlite3.Error:
        return default


def main():
    conn = get_connection()

    print("=" * 40)
    print("       POS LEDGER NG V51")
    print(" FINANCIAL POSITION & RECONCILIATION")
    print("=" * 40)

    # ----------------------------------------
    # BALANCE
    # ----------------------------------------
    cash = 0
    wallet = 0
    opening = 0

    if table_exists(conn, "balance"):
        row = conn.execute("""
            SELECT
                COALESCE(cash_balance, 0),
                COALESCE(wallet_balance, 0),
                COALESCE(opening_balance, 0)
            FROM balance
            ORDER BY id DESC
            LIMIT 1
        """).fetchone()

        if row:
            cash = float(row[0])
            wallet = float(row[1])
            opening = float(row[2])

    liquid_funds = cash + wallet

    print("\n" + "=" * 40)
    print("       BALANCE POSITION")
    print("=" * 40)
    print(f"Opening Balance      : {money(opening)}")
    print(f"Cash Balance         : {money(cash)}")
    print(f"Wallet Balance       : {money(wallet)}")
    print(f"Liquid Funds         : {money(liquid_funds)}")

    # ----------------------------------------
    # SALES
    # ----------------------------------------
    sales_revenue = 0
    sales_profit = 0
    completed_sales = 0
    units_sold = 0

    if table_exists(conn, "sales"):
        sales_revenue = scalar(conn, """
            SELECT COALESCE(SUM(total_amount), 0)
            FROM sales
            WHERE status = 'COMPLETED'
        """)

        sales_profit = scalar(conn, """
            SELECT COALESCE(SUM(total_profit), 0)
            FROM sales
            WHERE status = 'COMPLETED'
        """)

        completed_sales = int(scalar(conn, """
            SELECT COUNT(*)
            FROM sales
            WHERE status = 'COMPLETED'
        """))

        units_sold = scalar(conn, """
            SELECT COALESCE(SUM(quantity), 0)
            FROM sales
            WHERE status = 'COMPLETED'
        """)

    print("\n" + "=" * 40)
    print("       SALES POSITION")
    print("=" * 40)
    print(f"Sales Revenue       : {money(sales_revenue)}")
    print(f"Sales Profit        : {money(sales_profit)}")
    print(f"Completed Sales     : {completed_sales}")
    print(f"Units Sold          : {units_sold:.2f}")

    # ----------------------------------------
    # CUSTOMER CREDIT
    # ----------------------------------------
    customer_credit = 0
    credit_paid = 0
    outstanding_credit = 0

    if table_exists(conn, "customer_credit"):
        customer_credit = scalar(conn, """
            SELECT COALESCE(SUM(total_amount), 0)
            FROM customer_credit
        """)

        outstanding_credit = scalar(conn, """
            SELECT COALESCE(SUM(balance), 0)
            FROM customer_credit
        """)

        credit_paid = customer_credit - outstanding_credit

    elif table_exists(conn, "debtors"):
        customer_credit = scalar(conn, """
            SELECT COALESCE(SUM(amount), 0)
            FROM debtors
        """)

        outstanding_credit = scalar(conn, """
            SELECT COALESCE(SUM(balance), 0)
            FROM debtors
        """)

        credit_paid = customer_credit - outstanding_credit

    print("\n" + "=" * 40)
    print("       CUSTOMER CREDIT POSITION")
    print("=" * 40)
    print(f"Credit Created       : {money(customer_credit)}")
    print(f"Credit Payments      : {money(credit_paid)}")
    print(f"Outstanding Credit   : {money(outstanding_credit)}")

    # ----------------------------------------
    # SUPPLIER LIABILITY
    # ----------------------------------------
    supplier_liability = 0
    supplier_paid = 0
    outstanding_supplier = 0

    if table_exists(conn, "creditors"):
        supplier_liability = scalar(conn, """
            SELECT COALESCE(SUM(amount), 0)
            FROM creditors
        """)

        supplier_paid = scalar(conn, """
            SELECT COALESCE(SUM(paid), 0)
            FROM creditors
        """)

        outstanding_supplier = scalar(conn, """
            SELECT COALESCE(SUM(balance), 0)
            FROM creditors
        """)

    print("\n" + "=" * 40)
    print("       SUPPLIER POSITION")
    print("=" * 40)
    print(f"Supplier Purchases  : {money(supplier_liability)}")
    print(f"Supplier Payments   : {money(supplier_paid)}")
    print(f"Outstanding Debt    : {money(outstanding_supplier)}")

    # ----------------------------------------
    # INVENTORY
    # ----------------------------------------
    inventory_capital = 0
    product_count = 0
    stock_units = 0

    if table_exists(conn, "products"):
        inventory_capital = scalar(conn, """
            SELECT COALESCE(SUM(buying_price * current_stock), 0)
            FROM products
        """)

        product_count = int(scalar(conn, """
            SELECT COUNT(*)
            FROM products
        """))

        stock_units = scalar(conn, """
            SELECT COALESCE(SUM(current_stock), 0)
            FROM products
        """)

    print("\n" + "=" * 40)
    print("       INVENTORY POSITION")
    print("=" * 40)
    print(f"Products            : {product_count}")
    print(f"Stock Units         : {stock_units:.2f}")
    print(f"Inventory Capital   : {money(inventory_capital)}")

    # ----------------------------------------
    # EXPENSES
    # ----------------------------------------
    expenses = 0

    if table_exists(conn, "expenses"):
        expenses = scalar(conn, """
            SELECT COALESCE(SUM(amount), 0)
            FROM expenses
        """)

    print("\n" + "=" * 40)
    print("       EXPENSE POSITION")
    print("=" * 40)
    print(f"Recorded Expenses   : {money(expenses)}")

    # ----------------------------------------
    # FINANCIAL POSITION
    # ----------------------------------------
    gross_position = liquid_funds + outstanding_credit + inventory_capital

    net_position = (
        liquid_funds
        + outstanding_credit
        + inventory_capital
        - outstanding_supplier
    )

    print("\n" + "=" * 40)
    print("       FINANCIAL POSITION")
    print("=" * 40)
    print(f"Liquid Funds        : {money(liquid_funds)}")
    print(f"Customer Credit     : {money(outstanding_credit)}")
    print(f"Inventory Capital   : {money(inventory_capital)}")
    print(f"Supplier Liability  : {money(outstanding_supplier)}")
    print(f"Net Position        : {money(net_position)}")

    # ----------------------------------------
    # RECONCILIATION
    # ----------------------------------------
    print("\n" + "=" * 40)
    print("       DATA RECONCILIATION")
    print("=" * 40)

    balance_status = "OK"
    inventory_status = "OK"
    sales_status = "OK"
    credit_status = "OK"
    supplier_status = "OK"

    if not table_exists(conn, "balance"):
        balance_status = "MISSING TABLE"

    if not table_exists(conn, "products"):
        inventory_status = "MISSING TABLE"

    if not table_exists(conn, "sales"):
        sales_status = "MISSING TABLE"

    if not table_exists(conn, "customer_credit") and not table_exists(conn, "debtors"):
        credit_status = "MISSING TABLE"

    if not table_exists(conn, "creditors"):
        supplier_status = "MISSING TABLE"

    print(f"Balance Data       : {balance_status}")
    print(f"Sales Data         : {sales_status}")
    print(f"Inventory Data     : {inventory_status}")
    print(f"Customer Credit    : {credit_status}")
    print(f"Supplier Data      : {supplier_status}")

    # ----------------------------------------
    # MANAGEMENT INSIGHTS
    # ----------------------------------------
    print("\n" + "=" * 40)
    print("       MANAGEMENT INSIGHTS")
    print("=" * 40)

    if liquid_funds == 0 and sales_revenue > 0:
        print("1. [HIGH] Sales revenue exists but liquid balance is zero.")
        print("   Review the balance-update integration.")

    if sales_revenue > 0 and sales_profit > 0:
        margin = (sales_profit / sales_revenue) * 100
        print(f"2. Gross sales margin currently measures {margin:.2f}%.")

    if inventory_capital > 0:
        print(
            f"3. {money(inventory_capital)} of capital is currently "
            "represented by inventory."
        )

    if outstanding_credit > 0:
        print(
            f"4. {money(outstanding_credit)} remains in customer credit."
        )
    else:
        print("4. No outstanding customer credit detected.")

    if outstanding_supplier > 0:
        print(
            f"5. Supplier liability currently stands at "
            f"{money(outstanding_supplier)}."
        )
    else:
        print("5. No outstanding supplier liability detected.")

    # ----------------------------------------
    # OVERALL STATUS
    # ----------------------------------------
    if liquid_funds == 0 and sales_revenue > 0:
        overall_status = "🟠 RECONCILIATION REQUIRED"
    elif outstanding_credit > 0:
        overall_status = "🟡 MONITOR CREDIT"
    elif outstanding_supplier > 0:
        overall_status = "🟡 MONITOR SUPPLIER LIABILITY"
    else:
        overall_status = "🟢 FINANCIAL POSITION STABLE"

    print("\n" + "=" * 40)
    print("       OVERALL FINANCIAL STATUS")
    print("=" * 40)
    print(f"Status              : {overall_status}")

    # ----------------------------------------
    # MODULE STATUS
    # ----------------------------------------
    print("\n" + "=" * 40)
    print("       V51 MODULE STATUS")
    print("=" * 40)
    print("Mode                : READ-ONLY")
    print("Database modified   : NO")
    print("Sales modified      : NO")
    print("Balance modified    : NO")
    print("Credit modified     : NO")
    print("Inventory modified  : NO")
    print("Suppliers modified  : NO")
    print("Expenses modified   : NO")
    print("=" * 40)

    conn.close()


if __name__ == "__main__":
    main()
