import sqlite3

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def money(value):
    return f"₦{float(value or 0):,.2f}"


def customer_statement():
    conn = get_connection()
    cur = conn.cursor()

    print("\n========================================")
    print("       CUSTOMER ACCOUNT STATEMENT")
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
        cur.execute(
            """
            SELECT id, fullname, phone, credit_limit
            FROM customers
            WHERE id = ?
            """,
            (int(search),),
        )
    else:
        cur.execute(
            """
            SELECT id, fullname, phone, credit_limit
            FROM customers
            WHERE LOWER(fullname) LIKE LOWER(?)
            ORDER BY id
            LIMIT 1
            """,
            (f"%{search}%",),
        )

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
    cur.execute(
        """
        SELECT
            cc.id,
            cc.sale_id,
            cc.total_amount,
            cc.amount_paid,
            cc.balance,
            cc.status,
            cc.staff_name,
            cc.created_date,
            s.receipt_no
        FROM customer_credit cc
        LEFT JOIN sales s
            ON s.id = cc.sale_id
        WHERE cc.customer_id = ?
        ORDER BY cc.created_date ASC, cc.id ASC
        """,
        (customer_id,),
    )

    credits = cur.fetchall()

    # ------------------------------------
    # NORMAL PAYMENT HISTORY
    # ------------------------------------
    cur.execute(
        """
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
        """,
        (customer_id,),
    )

    normal_payments = cur.fetchall()

    # ------------------------------------
    # HISTORICAL PAYMENT HISTORY
    # ------------------------------------
    cur.execute(
        """
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
        AND cr.reconciliation_type = 'HISTORICAL_PAYMENT'
        ORDER BY cr.reconciliation_date ASC, cr.id ASC
        """,
        (customer_id,),
    )

    historical_payments = cur.fetchall()

    # ------------------------------------
    # TOTALS
    # ------------------------------------
    total_credit = sum(
        float(row["total_amount"] or 0)
        for row in credits
    )

    normal_total = sum(
        float(row["amount"] or 0)
        for row in normal_payments
    )

    historical_total = sum(
        float(row["amount"] or 0)
        for row in historical_payments
    )

    total_paid = normal_total + historical_total

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
    print(f"Credit Limit  : {money(credit_limit)}")
    print("========================================")

    # ------------------------------------
    # CREDIT SALES
    # ------------------------------------
    print("\n========================================")
    print("             CREDIT SALES")
    print("========================================")

    if not credits:
        print("No credit accounts found.")
    else:
        for row in credits:
            print("----------------------------------------")
            print(f"Credit ID  : {row['id']}")

            if row["receipt_no"]:
                print(f"Receipt No : {row['receipt_no']}")
            else:
                print("Receipt No : N/A")

            print(f"Date       : {row['created_date']}")
            print(f"Original   : {money(row['total_amount'])}")
            print(f"Recorded Paid : {money(row['amount_paid'])}")
            print(f"Balance    : {money(row['balance'])}")
            print(f"Status     : {row['status']}")

    print("----------------------------------------")
    print(f"TOTAL CREDIT : {money(total_credit)}")
    print("========================================")

    # ------------------------------------
    # ACCOUNT TRANSACTION LEDGER
    # ------------------------------------
    print("\n========================================")
    print("      ACCOUNT TRANSACTION LEDGER")
    print("========================================")

    ledger = []

    # Credit sales
    for row in credits:
        ledger.append(
            {
                "date": row["created_date"],
                "type": "CREDIT SALE",
                "credit_id": row["id"],
                "amount": float(row["total_amount"] or 0),
                "staff": row["staff_name"] or "System",
                "receipt_no": row["receipt_no"] or "N/A",
            }
        )

    # Normal payments
    for row in normal_payments:
        ledger.append(
            {
                "date": row["payment_date"],
                "type": "PAYMENT",
                "credit_id": row["credit_id"],
                "amount": float(row["amount"] or 0),
                "staff": row["staff_name"] or "System",
                "payment_no": row["payment_no"],
            }
        )

    # Historical payments
    for row in historical_payments:
        ledger.append(
            {
                "date": row["reconciliation_date"],
                "type": "HISTORICAL PAYMENT",
                "credit_id": row["credit_id"],
                "amount": float(row["amount"] or 0),
                "staff": row["staff_name"] or "System",
                "reference": row["reference"],
            }
        )

    ledger.sort(
        key=lambda item: item["date"]
    )

    running_balance = 0.0

    if not ledger:
        print("No account transactions found.")
    else:
        for item in ledger:

            if item["type"] == "CREDIT SALE":
                running_balance += item["amount"]
            else:
                running_balance -= item["amount"]

            print("----------------------------------------")
            print(f"DATE       : {item['date']}")
            print(f"TYPE       : {item['type']}")
            print(f"Credit ID  : {item['credit_id']}")

            if item["type"] == "CREDIT SALE":
                print(f"Receipt No : {item['receipt_no']}")
                print(f"Amount     : {money(item['amount'])}")

            elif item["type"] == "PAYMENT":
                print(f"Payment No : {item['payment_no']}")
                print(f"Paid       : {money(item['amount'])}")

            else:
                print(f"Reference  : {item['reference']}")
                print(f"Paid       : {money(item['amount'])}")

            print(f"Balance    : {money(running_balance)}")
            print(f"Staff      : {item['staff']}")

    print("----------------------------------------")
    print(f"FINAL LEDGER BALANCE : {money(running_balance)}")
    print("========================================")

    # ------------------------------------
    # NORMAL PAYMENTS
    # ------------------------------------
    print("\n========================================")
    print("          CREDIT PAYMENTS")
    print("========================================")

    if not normal_payments:
        print("No normal payments recorded.")
    else:
        for index, row in enumerate(
            normal_payments,
            start=1
        ):
            print("----------------------------------------")
            print(
                f"{index}. Payment No : "
                f"{row['payment_no']}"
            )
            print(
                f"   Credit ID   : "
                f"{row['credit_id']}"
            )
            print(
                f"   Amount      : "
                f"{money(row['amount'])}"
            )
            print(
                f"   Date        : "
                f"{row['payment_date']}"
            )
            print(
                f"   Staff       : "
                f"{row['staff_name'] or 'System'}"
            )

    print("----------------------------------------")
    print(
        f"TOTAL NORMAL PAYMENTS : "
        f"{money(normal_total)}"
    )
    print("========================================")

    # ------------------------------------
    # HISTORICAL PAYMENTS
    # ------------------------------------
    print("\n========================================")
    print("       HISTORICAL PAYMENTS")
    print("========================================")

    if not historical_payments:
        print("No historical payments recorded.")
    else:
        for row in historical_payments:
            print("----------------------------------------")
            print(
                f"Reference   : "
                f"{row['reference']}"
            )
            print(
                f"Credit ID   : "
                f"{row['credit_id']}"
            )
            print(
                f"Amount      : "
                f"{money(row['amount'])}"
            )
            print(
                f"Date        : "
                f"{row['reconciliation_date']}"
            )
            print(
                f"Staff       : "
                f"{row['staff_name'] or 'System'}"
            )
            print(
                "Type        : Historical Payment"
            )

    print("----------------------------------------")
    print(
        f"TOTAL HISTORICAL PAYMENTS : "
        f"{money(historical_total)}"
    )
    print("========================================")

    # ------------------------------------
    # FINAL ACCOUNT SUMMARY
    # ------------------------------------
    print("\n========================================")
    print("             ACCOUNT SUMMARY")
    print("========================================")

    print(
        f"Total Credit Sales : "
        f"{money(total_credit)}"
    )

    print(
        f"Normal Payments    : "
        f"{money(normal_total)}"
    )

    print(
        f"Historical Payments: "
        f"{money(historical_total)}"
    )

    print(
        f"TOTAL PAID         : "
        f"{money(total_paid)}"
    )

    print(
        f"Outstanding Debt    : "
        f"{money(outstanding)}"
    )

    print(
        f"Credit Limit       : "
        f"{money(credit_limit)}"
    )

    print(
        f"Available Credit   : "
        f"{money(available_credit)}"
    )

    print("----------------------------------------")

    if outstanding <= 0.000001:
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
