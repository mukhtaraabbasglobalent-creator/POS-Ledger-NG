import sqlite3

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


# ============================================================
# SALES REPORT
# ============================================================

def sales_report(title, date_filter):
    conn = get_connection()
    cur = conn.cursor()

    query = f"""
        SELECT
            COUNT(*) AS total_sales,
            IFNULL(SUM(total_amount), 0) AS sales_amount,
            IFNULL(SUM(total_profit), 0) AS profit
        FROM sales
        WHERE {date_filter}
        AND status = 'COMPLETED'
    """

    cur.execute(query)
    row = cur.fetchone()

    print("\n====================================")
    print(f"      {title}")
    print("====================================")
    print(f"Transactions : {row['total_sales']}")
    print(f"Sales Amount : ₦{row['sales_amount']:,.2f}")
    print(f"Profit       : ₦{row['profit']:,.2f}")
    print("====================================")

    conn.close()
    input("\nPress Enter to continue...")


def daily_sales_report():
    while True:
        print("""
====================================
        DAILY SALES REPORT
====================================
1. Today's Sales
2. Select Date
0. Back
====================================
""")

        choice = input("Select option: ").strip()

        if choice == "0":
            return

        if choice == "1":
            report_date = None

        elif choice == "2":
            report_date = input(
                "\nEnter date (YYYY-MM-DD): "
            ).strip()

            # Validate date format
            try:
                from datetime import datetime
                datetime.strptime(report_date, "%Y-%m-%d")
            except ValueError:
                print("\n❌ Invalid date.")
                input("\nPress Enter to continue...")
                continue

        else:
            print("\n❌ Invalid option.")
            continue

        conn = get_connection()
        cur = conn.cursor()

        if report_date:
            cur.execute("""
                SELECT
                    COUNT(*) AS total_sales,
                    IFNULL(SUM(total_amount), 0) AS sales_amount,
                    IFNULL(SUM(total_profit), 0) AS profit
                FROM sales
                WHERE DATE(sale_date) = ?
                  AND status = 'COMPLETED'
            """, (report_date,))

            title = f"SALES FOR {report_date}"

        else:
            cur.execute("""
                SELECT
                    COUNT(*) AS total_sales,
                    IFNULL(SUM(total_amount), 0) AS sales_amount,
                    IFNULL(SUM(total_profit), 0) AS profit
                FROM sales
                WHERE DATE(sale_date) = DATE('now', 'localtime')
                  AND status = 'COMPLETED'
            """)

            title = "TODAY'S SALES"

        row = cur.fetchone()

        print("\n====================================")
        print(f"        {title}")
        print("====================================")
        print(f"Transactions : {row['total_sales']}")
        print(f"Sales Amount : ₦{row['sales_amount']:,.2f}")
        print(f"Profit       : ₦{row['profit']:,.2f}")
        print("====================================")

        conn.close()

        input("\nPress Enter to continue...")


def weekly_sales_report():
    sales_report(
        "WEEKLY SALES REPORT",
        "DATE(sale_date) >= DATE('now', '-6 day')"
    )


def monthly_sales_report():
    sales_report(
        "MONTHLY SALES REPORT",
        "strftime('%Y-%m', sale_date) = strftime('%Y-%m', 'now')"
    )


def yearly_sales_report():
    sales_report(
        "YEARLY SALES REPORT",
        "strftime('%Y', sale_date) = strftime('%Y', 'now')"
    )


# ============================================================
# BEST SELLING PRODUCTS
# ============================================================

def best_selling_products():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            p.product_name,
            SUM(si.quantity) AS qty_sold,
            SUM(si.subtotal) AS total_sales,
            SUM(si.profit) AS total_profit
        FROM sale_items si
        JOIN products p
            ON si.product_id = p.id
        JOIN sales s
            ON si.sale_id = s.id
        WHERE s.status = 'COMPLETED'
        GROUP BY si.product_id, p.product_name
        ORDER BY qty_sold DESC
        LIMIT 10
    """)

    rows = cur.fetchall()

    print("\n====================================")
    print("       BEST SELLING PRODUCTS")
    print("====================================")

    if not rows:
        print("No completed sales found.")
    else:
        for i, row in enumerate(rows, start=1):
            print("------------------------------------")
            print(f"{i}. {row['product_name']}")
            print(f"   Qty Sold : {row['qty_sold']}")
            print(f"   Sales    : ₦{row['total_sales']:,.2f}")
            print(f"   Profit   : ₦{row['total_profit']:,.2f}")

    print("====================================")

    conn.close()
    input("\nPress Enter to continue...")


def least_selling_products():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            p.id,
            p.product_name,
            p.sku,
            p.current_stock,
            COALESCE(SUM(si.quantity), 0) AS qty_sold,
            COALESCE(SUM(si.subtotal), 0) AS total_sales,
            COALESCE(SUM(si.profit), 0) AS total_profit
        FROM products p
        LEFT JOIN sale_items si
            ON p.id = si.product_id
        LEFT JOIN sales s
            ON si.sale_id = s.id
            AND s.status = 'COMPLETED'
        GROUP BY
            p.id,
            p.product_name,
            p.sku,
            p.current_stock
        ORDER BY
            qty_sold ASC,
            total_sales ASC
        LIMIT 10
    """)

    rows = cur.fetchall()

    print("\n====================================")
    print("       LEAST SELLING PRODUCTS")
    print("====================================")

    if not rows:
        print("No products found.")
    else:
        for i, row in enumerate(rows, start=1):
            print("------------------------------------")
            print(f"{i}. {row['product_name']}")
            print(f"   SKU       : {row['sku']}")
            print(f"   Qty Sold  : {row['qty_sold']}")
            print(f"   Sales     : ₦{row['total_sales']:,.2f}")
            print(f"   Profit    : ₦{row['total_profit']:,.2f}")
            print(f"   Stock     : {row['current_stock']}")

    print("====================================")

    conn.close()
    input("\nPress Enter to continue...")


# ============================================================
# REFUND REPORT
# ============================================================

def refund_report():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            COUNT(*) AS refund_count,
            IFNULL(SUM(total_amount), 0) AS refund_amount
        FROM sales
        WHERE status = 'REFUNDED'
    """)

    row = cur.fetchone()

    print("\n====================================")
    print("         REFUND REPORT")
    print("====================================")
    print(f"Refund Transactions : {row['refund_count']}")
    print(f"Refund Amount       : ₦{row['refund_amount']:,.2f}")
    print("====================================")

    conn.close()
    input("\nPress Enter to continue...")


# ============================================================
# STOCK VALUE REPORT
# ============================================================

def stock_value_report():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            IFNULL(SUM(current_stock), 0) AS total_units,
            IFNULL(SUM(current_stock * buying_price), 0) AS stock_cost,
            IFNULL(SUM(current_stock * selling_price), 0) AS stock_value
        FROM products
    """)

    row = cur.fetchone()

    total_units = row["total_units"] or 0
    stock_cost = row["stock_cost"] or 0
    stock_value = row["stock_value"] or 0
    potential_profit = stock_value - stock_cost

    print("\n====================================")
    print("        STOCK VALUE REPORT")
    print("====================================")
    print(f"Stock Units       : {total_units:,.2f}")
    print(f"Stock Cost Value  : ₦{stock_cost:,.2f}")
    print(f"Selling Value     : ₦{stock_value:,.2f}")
    print(f"Potential Profit  : ₦{potential_profit:,.2f}")
    print("====================================")

    conn.close()
    input("\nPress Enter to continue...")


# ============================================================
# PROFIT ANALYSIS
# ============================================================

def profit_analysis():
    conn = get_connection()
    cur = conn.cursor()

    # --------------------------------------------------------
    # PRODUCT SALES
    # --------------------------------------------------------

    cur.execute("""
        SELECT
            IFNULL(SUM(total_amount), 0),
            IFNULL(SUM(total_profit), 0)
        FROM sales
        WHERE status = 'COMPLETED'
    """)

    sales_row = cur.fetchone()

    product_sales = sales_row[0] or 0
    product_profit = sales_row[1] or 0

    # --------------------------------------------------------
    # POS TRANSACTIONS
    # --------------------------------------------------------

    cur.execute("""
        SELECT
            IFNULL(SUM(amount), 0),
            IFNULL(SUM(charge), 0),
            IFNULL(SUM(provider_fee), 0),
            IFNULL(SUM(profit), 0)
        FROM transactions
    """)

    transaction_row = cur.fetchone()

    transaction_volume = transaction_row[0] or 0
    transaction_charges = transaction_row[1] or 0
    provider_fees = transaction_row[2] or 0
    transaction_profit = transaction_row[3] or 0

    # --------------------------------------------------------
    # EXPENSES
    # --------------------------------------------------------

    cur.execute("""
        SELECT IFNULL(SUM(amount), 0)
        FROM expenses
    """)

    total_expenses = cur.fetchone()[0] or 0

    # --------------------------------------------------------
    # REFUNDS
    # --------------------------------------------------------

    cur.execute("""
        SELECT IFNULL(SUM(total_amount), 0)
        FROM sales
        WHERE status = 'REFUNDED'
    """)

    total_refunds = cur.fetchone()[0] or 0

    # --------------------------------------------------------
    # BUSINESS CALCULATIONS
    # --------------------------------------------------------

    total_revenue = product_sales + transaction_charges

    gross_profit = product_profit + transaction_profit

    net_profit = gross_profit - total_expenses - total_refunds

    if total_revenue > 0:
        profit_margin = (net_profit / total_revenue) * 100
    else:
        profit_margin = 0

    # --------------------------------------------------------
    # DISPLAY
    # --------------------------------------------------------

    print("\n====================================")
    print("        PROFIT ANALYSIS")
    print("====================================")

    print("\nPRODUCT SALES")
    print("------------------------------------")
    print(f"Sales Amount       : ₦{product_sales:,.2f}")
    print(f"Sales Profit       : ₦{product_profit:,.2f}")

    print("\nPOS TRANSACTIONS")
    print("------------------------------------")
    print(f"Transaction Amount : ₦{transaction_volume:,.2f}")
    print(f"Customer Charges   : ₦{transaction_charges:,.2f}")
    print(f"Provider Fees      : ₦{provider_fees:,.2f}")
    print(f"Transaction Profit : ₦{transaction_profit:,.2f}")

    print("\nBUSINESS TOTALS")
    print("------------------------------------")
    print(f"Total Revenue      : ₦{total_revenue:,.2f}")
    print(f"Gross Profit       : ₦{gross_profit:,.2f}")
    print(f"Expenses           : ₦{total_expenses:,.2f}")
    print(f"Refunds            : ₦{total_refunds:,.2f}")
    print(f"Net Profit         : ₦{net_profit:,.2f}")
    print(f"Profit Margin      : {profit_margin:.2f}%")

    print("====================================")

    conn.close()
    input("\nPress Enter to continue...")


# ============================================================
# BUSINESS SUMMARY DASHBOARD
# ============================================================

def business_summary():
    conn = get_connection()
    cur = conn.cursor()

    # --------------------------------------------------------
    # PRODUCT SALES
    # --------------------------------------------------------

    cur.execute("""
        SELECT
            IFNULL(SUM(total_amount), 0),
            IFNULL(SUM(total_profit), 0)
        FROM sales
        WHERE status = 'COMPLETED'
    """)

    sales_row = cur.fetchone()

    product_sales = sales_row[0] or 0
    product_profit = sales_row[1] or 0

    # --------------------------------------------------------
    # POS TRANSACTIONS
    # --------------------------------------------------------

    cur.execute("""
        SELECT
            IFNULL(SUM(amount), 0),
            IFNULL(SUM(charge), 0),
            IFNULL(SUM(provider_fee), 0),
            IFNULL(SUM(profit), 0)
        FROM transactions
    """)

    transaction_row = cur.fetchone()

    transaction_volume = transaction_row[0] or 0
    transaction_charges = transaction_row[1] or 0
    provider_fees = transaction_row[2] or 0
    transaction_profit = transaction_row[3] or 0

    # --------------------------------------------------------
    # EXPENSES
    # --------------------------------------------------------

    cur.execute("""
        SELECT IFNULL(SUM(amount), 0)
        FROM expenses
    """)

    total_expenses = cur.fetchone()[0] or 0

    # --------------------------------------------------------
    # REFUNDS
    # --------------------------------------------------------

    cur.execute("""
        SELECT IFNULL(SUM(total_amount), 0)
        FROM sales
        WHERE status = 'REFUNDED'
    """)

    total_refunds = cur.fetchone()[0] or 0

    # --------------------------------------------------------
    # CUSTOMERS
    # --------------------------------------------------------

    cur.execute("""
        SELECT COUNT(*)
        FROM customers
    """)

    total_customers = cur.fetchone()[0] or 0

    # --------------------------------------------------------
    # PRODUCTS
    # --------------------------------------------------------

    cur.execute("""
        SELECT COUNT(*)
        FROM products
    """)

    total_products = cur.fetchone()[0] or 0

    # --------------------------------------------------------
    # STOCK
    # --------------------------------------------------------

    cur.execute("""
        SELECT IFNULL(SUM(current_stock), 0)
        FROM products
    """)

    total_stock = cur.fetchone()[0] or 0

    # --------------------------------------------------------
    # BUSINESS CALCULATIONS
    # --------------------------------------------------------

    total_revenue = product_sales + transaction_charges

    gross_profit = product_profit + transaction_profit

    net_profit = gross_profit - total_expenses - total_refunds

    if total_revenue > 0:
        profit_margin = (net_profit / total_revenue) * 100
    else:
        profit_margin = 0

    # --------------------------------------------------------
    # DISPLAY
    # --------------------------------------------------------

    print("\n====================================")
    print("      BUSINESS SUMMARY")
    print("====================================")

    print(f"Product Sales         : ₦{product_sales:,.2f}")
    print(f"POS Charges           : ₦{transaction_charges:,.2f}")
    print(f"Total Revenue         : ₦{total_revenue:,.2f}")

    print("------------------------------------")

    print(f"Product Profit        : ₦{product_profit:,.2f}")
    print(f"POS Transaction Profit : ₦{transaction_profit:,.2f}")
    print(f"Gross Profit          : ₦{gross_profit:,.2f}")

    print(f"Expenses              : ₦{total_expenses:,.2f}")
    print(f"Refunds               : ₦{total_refunds:,.2f}")
    print(f"Net Profit            : ₦{net_profit:,.2f}")
    print(f"Profit Margin         : {profit_margin:.2f}%")

    print("------------------------------------")

    print(f"POS Volume            : ₦{transaction_volume:,.2f}")
    print(f"Provider Fees         : ₦{provider_fees:,.2f}")

    print("------------------------------------")

    print(f"Products              : {total_products}")
    print(f"Customers             : {total_customers}")
    print(f"Stock Units           : {total_stock:,.2f}")

    print("====================================")

    conn.close()
    input("\nPress Enter to continue...")


# ============================================================
# ANALYTICS MENU
# ============================================================

def analytics_menu():

    while True:

        print("""
====================================
      BUSINESS ANALYTICS
====================================
1. Daily Sales Report
2. Weekly Sales Report
3. Monthly Sales Report
4. Yearly Sales Report
5. Best Selling Products
6. Least Selling Products
7. Refund Report
8. Profit Analysis
9. Stock Value Report
10. Business Summary Dashboard
0. Back
====================================
""")

        choice = input("Select option: ").strip()

        if choice == "1":
            daily_sales_report()

        elif choice == "2":
            weekly_sales_report()

        elif choice == "3":
            monthly_sales_report()

        elif choice == "4":
            yearly_sales_report()

        elif choice == "5":
            best_selling_products()

        elif choice == "6":
            least_selling_products()

        elif choice == "7":
            refund_report()

        elif choice == "8":
            profit_analysis()

        elif choice == "9":
            stock_value_report()

        elif choice == "10":
            business_summary()

        elif choice == "0":
            break

        else:
            print("\n❌ Invalid option.")
