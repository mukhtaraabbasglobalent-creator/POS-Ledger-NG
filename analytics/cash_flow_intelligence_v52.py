import sqlite3
from datetime import datetime

DB = "data/posledger.db"


def money(value):
    return f"₦{value:,.2f}"


def get_one(conn, query, params=()):
    row = conn.execute(query, params).fetchone()
    return float(row[0] or 0) if row else 0.0


def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    print("=" * 40)
    print("       POS LEDGER NG V52")
    print(" CASH FLOW & MONEY MOVEMENT INTELLIGENCE")
    print("=" * 40)

    # -------------------------------------------------
    # BALANCE
    # -------------------------------------------------
    cash = get_one(conn, """
        SELECT cash_balance
        FROM balance
        ORDER BY id DESC
        LIMIT 1
    """)

    wallet = get_one(conn, """
        SELECT wallet_balance
        FROM balance
        ORDER BY id DESC
        LIMIT 1
    """)

    liquid_funds = cash + wallet

    # -------------------------------------------------
    # SALES INFLOW
    # -------------------------------------------------
    sales_revenue = get_one(conn, """
        SELECT COALESCE(SUM(total_amount), 0)
        FROM sales
        WHERE status = 'COMPLETED'
    """)

    # -------------------------------------------------
    # CUSTOMER CREDIT
    # -------------------------------------------------
    credit_created = get_one(conn, """
        SELECT COALESCE(SUM(total_amount), 0)
        FROM customer_credit
    """)

    credit_collected = get_one(conn, """
        SELECT COALESCE(SUM(amount), 0)
        FROM credit_payments
    """)

    # -------------------------------------------------
    # EXPENSES
    # -------------------------------------------------
    expenses = get_one(conn, """
        SELECT COALESCE(SUM(amount), 0)
        FROM expenses
    """)

    # -------------------------------------------------
    # SUPPLIER PAYMENTS
    # -------------------------------------------------
    supplier_paid = get_one(conn, """
        SELECT COALESCE(SUM(paid), 0)
        FROM creditors
    """)

    # -------------------------------------------------
    # PURCHASES
    # -------------------------------------------------
    purchases = get_one(conn, """
        SELECT COALESCE(SUM(total_cost), 0)
        FROM purchases
    """)

    # -------------------------------------------------
    # POS TRANSACTION PROFIT / CHARGES
    # -------------------------------------------------
    transaction_charges = get_one(conn, """
        SELECT COALESCE(SUM(charge), 0)
        FROM transactions
    """)

    transaction_provider_fees = get_one(conn, """
        SELECT COALESCE(SUM(provider_fee), 0)
        FROM transactions
    """)

    transaction_profit = transaction_charges - transaction_provider_fees

    # -------------------------------------------------
    # MONEY MOVEMENT
    # -------------------------------------------------
    gross_inflows = (
        sales_revenue
        + credit_collected
        + transaction_profit
    )

    gross_outflows = (
        expenses
        + supplier_paid
    )

    net_operating_movement = gross_inflows - gross_outflows

    # -------------------------------------------------
    # CREDIT STILL OUTSTANDING
    # -------------------------------------------------
    outstanding_credit = max(
        credit_created - credit_collected,
        0
    )

    # -------------------------------------------------
    # SIMPLE MANAGEMENT VIEW
    # -------------------------------------------------
    if liquid_funds > 0:
        liquidity_status = "🟢 POSITIVE LIQUIDITY"
    else:
        liquidity_status = "🔴 NO LIQUID LIQUIDITY"

    if outstanding_credit > liquid_funds:
        credit_status = "🟠 CREDIT EXCEEDS LIQUID FUNDS"
    else:
        credit_status = "🟢 CREDIT WITHIN LIQUID CAPACITY"

    print("\n" + "=" * 40)
    print("       LIQUID FUNDS POSITION")
    print("=" * 40)

    print(f"Cash Balance         : {money(cash)}")
    print(f"Wallet Balance       : {money(wallet)}")
    print(f"Liquid Funds         : {money(liquid_funds)}")
    print(f"Liquidity Status     : {liquidity_status}")

    print("\n" + "=" * 40)
    print("       CASH FLOW INFLOWS")
    print("=" * 40)

    print(f"Completed Sales      : {money(sales_revenue)}")
    print(f"Credit Collections   : {money(credit_collected)}")
    print(f"Transaction Profit   : {money(transaction_profit)}")
    print(f"Total Recorded Inflow: {money(gross_inflows)}")

    print("\n" + "=" * 40)
    print("       CASH FLOW OUTFLOWS")
    print("=" * 40)

    print(f"Expenses             : {money(expenses)}")
    print(f"Supplier Payments    : {money(supplier_paid)}")
    print(f"Recorded Purchases   : {money(purchases)}")
    print(f"Total Recorded Outflow: {money(gross_outflows)}")

    print("\n" + "=" * 40)
    print("       MONEY MOVEMENT")
    print("=" * 40)

    print(
        f"Net Operating Movement: "
        f"{money(net_operating_movement)}"
    )

    print("\n" + "=" * 40)
    print("       CUSTOMER CREDIT")
    print("=" * 40)

    print(f"Credit Created       : {money(credit_created)}")
    print(f"Credit Collected     : {money(credit_collected)}")
    print(f"Outstanding Credit   : {money(outstanding_credit)}")
    print(f"Credit Status        : {credit_status}")

    print("\n" + "=" * 40)
    print("       MANAGEMENT INSIGHTS")
    print("=" * 40)

    if sales_revenue > 0:
        print(
            f"1. Recorded sales generated "
            f"{money(sales_revenue)} in revenue."
        )

    print(
        f"2. Current liquid funds are "
        f"{money(liquid_funds)}."
    )

    print(
        f"3. Customer credit outstanding is "
        f"{money(outstanding_credit)}."
    )

    if expenses == 0:
        print(
            "4. No recorded business expenses were detected."
        )
    else:
        print(
            f"4. Recorded expenses total "
            f"{money(expenses)}."
        )

    if supplier_paid == 0 and purchases > 0:
        print(
            f"5. Supplier purchases of {money(purchases)} "
            "have no recorded supplier payments."
        )

    print("\n" + "=" * 40)
    print("       CASH FLOW STATUS")
    print("=" * 40)

    if outstanding_credit > liquid_funds:
        print("Status : 🟠 MANAGEMENT ATTENTION")
        print("Reason : Customer credit exceeds liquid funds.")
    elif liquid_funds > 0:
        print("Status : 🟢 CASH POSITION STABLE")
    else:
        print("Status : 🔴 LIQUIDITY WARNING")

    print("\n" + "=" * 40)
    print("       V52 MODULE STATUS")
    print("=" * 40)

    print("Mode                : READ-ONLY")
    print("Database modified   : NO")
    print("Sales modified      : NO")
    print("Products modified   : NO")
    print("Inventory modified  : NO")
    print("Balance modified    : NO")
    print("Credit modified     : NO")
    print("Suppliers modified  : NO")
    print("Expenses modified   : NO")

    print("=" * 40)

    conn.close()


if __name__ == "__main__":
    main()
