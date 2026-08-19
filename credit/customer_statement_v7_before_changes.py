import sqlite3

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def customer_statement():
    conn = get_connection()
    cur = conn.cursor()

    print("\n========================================")
    print("        CUSTOMER ACCOUNT STATEMENT")
    print("========================================")

    search = input("Enter Customer ID or Name: ").strip()

    if not search:
        print("❌ Customer information required.")
        conn.close()
        input("\nPress Enter to continue...")
        return

    # ------------------------------------
    # FIND CUSTOMER
    # ------------------------------------
    if search.isdigit():
        cur.execute("""
            SELECT id, fullname, phone, credit_limit
            FROM customers
            WHERE id = ?
        """, (int(search),))
    else:
        cur.execute("""
            SELECT id, fullname, phone, credit_limit
            FROM customers
            WHERE fullname LIKE ?
            ORDER BY id
            LIMIT 1
        """, (f"%{search}%",))

    customer = cur.fetchone()

    if not customer:
        print("❌ Customer not found.")
        conn.close()
        input("\nPress Enter to continue...")
        return

    customer_id = customer["id"]

    # ------------------------------------
    # CREDIT ACCOUNTS
    # ------------------------------------
    cur.execute("""
        SELECT
            cc.id,
            cc.sale_id,
            cc.total_amount,
            cc.amount_paid,
            cc.balance,
            cc.status,
            cc.created_date,
            s.receipt_no
        FROM customer_credit cc
        LEFT JOIN sales s
            ON s.id = cc.sale_id
        WHERE cc.customer_id = ?
        ORDER BY cc.created_date ASC, cc.id ASC
    """, (customer_id,))

    credits = cur.fetchall()

    # ------------------------------------
    # NORMAL PAYMENT HISTORY
    # ------------------------------------
    cur.execute("""
        SELECT
            cp.id,
            cp.payment_no,
            cp.credit_id,
            cp.amount,
            cp.payment_date,
            cp.staff_name
        FROM credit_payments cp
        WHERE cp.customer_id = ?
        ORDER BY cp.payment_date ASC, cp.id ASC
    """, (customer_id,))

    payments = cur.fetchall()

    # ------------------------------------
    # HISTORICAL RECONCILIATIONS
    # ------------------------------------
    cur.execute("""
        SELECT
            cr.id,
            cr.credit_id,
            cr.amount,
            cr.reconciliation_type,
            cr.reference,
            cr.reconciliation_date,
            cr.staff_name,
            cr.notes
        FROM credit_reconciliations cr
        WHERE cr.customer_id = ?
        ORDER BY cr.reconciliation_date ASC, cr.id ASC
    """, (customer_id,))

    reconciliations = cur.fetchall()

    # ------------------------------------
    # TOTALS
    # ------------------------------------
    total_credit = sum(
        float(row["total_amount"] or 0)
        for row in credits
    )

    normal_payments = sum(
        float(row["amount"] or 0)
        for row in payments
    )

    historical_payments = sum(
        float(row["amount"] or 0)
        for row in reconciliations
    )

    total_paid = normal_payments + historical_payments

    outstanding = sum(
        float(row["balance"] or 0)
        for row in credits
    )

    credit_limit = float(
        customer["credit_limit"] or 0
    )

    available_credit = max(
        credit_limit - outstanding,
        0
    )

    # ------------------------------------
    # CUSTOMER INFORMATION
    # ------------------------------------
    print("\n========================================")
    print("          CUSTOMER INFORMATION")
    print("========================================")
    print(f"Customer ID   : {customer_id}")
    print(f"Customer Name : {customer['fullname']}")
    print(f"Phone         : {customer['phone'] or 'N/A'}")
    print(f"Credit Limit  : ₦{credit_limit:,.2f}")
    print("========================================")

    # ------------------------------------
    # CREDIT ACCOUNTS
    # ------------------------------------
    print("\n========================================")
    print("             CREDIT ACCOUNTS")
    print("========================================")

    if not credits:
        print("No credit accounts found.")
    else:
        for row in credits:

            original = float(
                row["total_amount"] or 0
            )

            paid = float(
                row["amount_paid"] or 0
            )

            balance = float(
                row["balance"] or 0
            )

            print("----------------------------------------")
            print(f"Credit ID  : {row['id']}")

            if row["receipt_no"]:
                print(f"Receipt No : {row['receipt_no']}")

            print(f"Date       : {row['created_date']}")
            print(f"Original   : ₦{original:,.2f}")
            print(f"Paid       : ₦{paid:,.2f}")
            print(f"Balance    : ₦{balance:,.2f}")
            print(f"Status     : {row['status']}")

    print("----------------------------------------")
    print(f"TOTAL CREDIT : ₦{total_credit:,.2f}")
    print("========================================")

    # ------------------------------------
    # ACCOUNT LEDGER
    # ------------------------------------
    print("\n========================================")
    print("          ACCOUNT TRANSACTION LEDGER")
    print("========================================")

    transactions = []

    # Credit sales
    for row in credits:
        transactions.append({
            "date": row["created_date"],
            "type": "CREDIT SALE",
            "credit_id": row["id"],
            "amount": float(row["total_amount"] or 0),
            "paid": 0,
            "reference": row["receipt_no"] or "N/A",
            "staff": None,
            "sort_id": row["id"]
        })

    # Historical payments
    for row in reconciliations:
        transactions.append({
            "date": row["reconciliation_date"],
            "type": "HISTORICAL PAYMENT",
            "credit_id": row["credit_id"],
            "amount": 0,
            "paid": float(row["amount"] or 0),
            "reference": row["reference"],
            "staff": row["staff_name"],
            "sort_id": 100000 + row["id"]
        })

    # Normal payments
    for row in payments:
        transactions.append({
            "date": row["payment_date"],
            "type": "PAYMENT",
            "credit_id": row["credit_id"],
            "amount": 0,
            "paid": float(row["amount"] or 0),
            "reference": row["payment_no"],
            "staff": row["staff_name"],
            "sort_id": 200000 + row["id"]
        })

    transactions.sort(
        key=lambda x: (x["date"], x["sort_id"])
    )

    running_debt = 0

    if not transactions:
        print("No account transactions found.")
    else:
        for tx in transactions:

            if tx["type"] == "CREDIT SALE":
                running_debt += tx["amount"]
            else:
                running_debt -= tx["paid"]

            print("----------------------------------------")
            print(f"DATE       : {tx['date']}")
            print(f"TYPE       : {tx['type']}")
            print(f"Credit ID  : {tx['credit_id']}")

            if tx["type"] == "CREDIT SALE":
                print(f"Receipt No : {tx['reference']}")
                print(f"Amount     : ₦{tx['amount']:,.2f}")
            else:
                print(f"Payment No : {tx['reference']}")
                print(f"Paid       : ₦{tx['paid']:,.2f}")

            print(f"Balance    : ₦{running_debt:,.2f}")

            if tx["staff"]:
                print(f"Staff      : {tx['staff']}")

    print("----------------------------------------")
    print("========================================")

    # ------------------------------------
    # NORMAL PAYMENT HISTORY
    # ------------------------------------
    print("\n========================================")
    print("          CREDIT PAYMENTS")
    print("========================================")

    if not payments:
        print("No normal payment records found.")
    else:
        for index, row in enumerate(payments, start=1):
            print("----------------------------------------")
            print(f"{index}. Payment No : {row['payment_no']}")
            print(f"   Credit ID   : {row['credit_id']}")
            print(f"   Amount      : ₦{float(row['amount'] or 0):,.2f}")
            print(f"   Date        : {row['payment_date']}")
            print(f"   Staff       : {row['staff_name'] or 'System'}")

    print("----------------------------------------")
    print(f"TOTAL NORMAL PAYMENTS : ₦{normal_payments:,.2f}")
    print("========================================")

    # ------------------------------------
    # HISTORICAL PAYMENTS
    # ------------------------------------
    print("\n========================================")
    print("       HISTORICAL PAYMENTS")
    print("========================================")

    if not reconciliations:
        print("No historical payments recorded.")
    else:
        for row in reconciliations:
            print("----------------------------------------")
            print(f"Reference   : {row['reference']}")
            print(f"Credit ID   : {row['credit_id']}")
            print(f"Amount      : ₦{float(row['amount'] or 0):,.2f}")
            print(f"Date        : {row['reconciliation_date']}")
            print(f"Staff       : {row['staff_name'] or 'System'}")
            print("Type        : Historical Payment")

    print("----------------------------------------")
    print(
        f"TOTAL HISTORICAL PAYMENTS : "
        f"₦{historical_payments:,.2f}"
    )
    print("========================================")

    # ------------------------------------
    # FINAL ACCOUNT SUMMARY
    # ------------------------------------
    print("\n========================================")
    print("             ACCOUNT SUMMARY")
    print("========================================")

    print(f"Total Credit Sales : ₦{total_credit:,.2f}")
    print(f"Normal Payments    : ₦{normal_payments:,.2f}")
    print(f"Historical Payments: ₦{historical_payments:,.2f}")
    print(f"TOTAL PAID         : ₦{total_paid:,.2f}")
    print(f"Outstanding Debt   : ₦{outstanding:,.2f}")
    print(f"Credit Limit       : ₦{credit_limit:,.2f}")
    print(f"Available Credit   : ₦{available_credit:,.2f}")

    print("----------------------------------------")

    if outstanding <= 0:
        print("STATUS : ✅ ACCOUNT CLEARED")
    elif credit_limit > 0 and outstanding >= credit_limit:
        print("STATUS : 🔴 CREDIT LIMIT REACHED")
    else:
        print("STATUS : 🟡 ACCOUNT OUTSTANDING")

    print("========================================")

    conn.close()

    input("\nPress Enter to continue...")


if __name__ == "__main__":
    customer_statement()
