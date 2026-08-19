import sqlite3
from datetime import datetime

from staff.manage import current_user

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def receive_payment():
    conn = get_connection()
    cur = conn.cursor()

    print("\n====================================")
    print("         RECEIVE PAYMENT")
    print("====================================")

    # ------------------------------------
    # SELECT CUSTOMER
    # ------------------------------------
    cur.execute("""
        SELECT id, fullname, phone
        FROM customers
        ORDER BY fullname
    """)

    customers = cur.fetchall()

    if not customers:
        print("\n❌ No customers found.")
        conn.close()
        input("\nPress Enter to continue...")
        return

    print("\nCUSTOMER LIST")
    print("------------------------------------")

    for customer in customers:
        print(
            f"{customer['id']}. "
            f"{customer['fullname']} "
            f"({customer['phone'] or 'No phone'})"
        )

    print("0. Cancel")
    print("------------------------------------")

    customer_input = input("Customer ID: ").strip()

    if customer_input == "0":
        conn.close()
        return

    try:
        customer_id = int(customer_input)
    except ValueError:
        print("\n❌ Invalid customer ID.")
        conn.close()
        input("\nPress Enter to continue...")
        return

    # ------------------------------------
    # FIND CUSTOMER
    # ------------------------------------
    cur.execute("""
        SELECT id, fullname, phone
        FROM customers
        WHERE id = ?
    """, (customer_id,))

    customer = cur.fetchone()

    if not customer:
        print("\n❌ Customer not found.")
        conn.close()
        input("\nPress Enter to continue...")
        return

    # ------------------------------------
    # GET OUTSTANDING CREDIT
    # ------------------------------------
    cur.execute("""
        SELECT
            id,
            sale_id,
            total_amount,
            amount_paid,
            balance,
            status,
            created_date
        FROM customer_credit
        WHERE customer_id = ?
          AND balance > 0
        ORDER BY id ASC
    """, (customer_id,))

    credits = cur.fetchall()

    print("\n====================================")
    print("       OUTSTANDING CREDIT")
    print("====================================")
    print(f"Customer : {customer['fullname']}")
    print(f"Phone    : {customer['phone'] or 'N/A'}")
    print("------------------------------------")

    if not credits:
        print("No outstanding credit found.")
        print("====================================")
        conn.close()
        input("\nPress Enter to continue...")
        return

    total_debt = sum(
        float(row["balance"] or 0)
        for row in credits
    )

    for row in credits:
        print(f"Credit ID : {row['id']}")
        print(
            f"Original  : "
            f"₦{float(row['total_amount']):,.2f}"
        )
        print(
            f"Paid      : "
            f"₦{float(row['amount_paid']):,.2f}"
        )
        print(
            f"Balance   : "
            f"₦{float(row['balance']):,.2f}"
        )
        print(f"Status    : {row['status']}")
        print(f"Date      : {row['created_date']}")
        print("------------------------------------")

    print(f"TOTAL DEBT : ₦{total_debt:,.2f}")
    print("====================================")

    # ------------------------------------
    # PAYMENT AMOUNT
    # ------------------------------------
    try:
        payment_amount = float(
            input("Payment Amount (₦): ").strip()
        )
    except ValueError:
        print("\n❌ Invalid payment amount.")
        conn.close()
        input("\nPress Enter to continue...")
        return

    if payment_amount <= 0:
        print("\n❌ Payment must be greater than zero.")
        conn.close()
        input("\nPress Enter to continue...")
        return

    if payment_amount > total_debt:
        print("\n❌ Payment exceeds customer's debt.")
        print(
            f"Outstanding Debt: "
            f"₦{total_debt:,.2f}"
        )
        conn.close()
        input("\nPress Enter to continue...")
        return

    # ------------------------------------
    # STAFF
    # ------------------------------------
    staff = current_user()

    if staff:
        staff_name = staff["fullname"]
    else:
        staff_name = "System"

    # ------------------------------------
    # PAYMENT NUMBER
    # ------------------------------------
    payment_no = (
        "PAY-" +
        datetime.now().strftime("%Y%m%d%H%M%S%f")
    )

    payment_date = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    remaining_payment = payment_amount
    allocations = []

    try:

        # --------------------------------
        # APPLY PAYMENT OLDEST FIRST
        # --------------------------------
        for credit in credits:

            if remaining_payment <= 0:
                break

            credit_balance = float(
                credit["balance"] or 0
            )

            allocation = min(
                remaining_payment,
                credit_balance
            )

            new_paid = (
                float(credit["amount_paid"] or 0)
                + allocation
            )

            new_balance = (
                credit_balance - allocation
            )

            if new_balance <= 0.000001:
                new_balance = 0
                new_status = "PAID"
            else:
                new_status = "PARTLY PAID"

            # Update credit
            cur.execute("""
                UPDATE customer_credit
                SET
                    amount_paid = ?,
                    balance = ?,
                    status = ?
                WHERE id = ?
            """, (
                new_paid,
                new_balance,
                new_status,
                credit["id"]
            ))

            # Save payment allocation
            cur.execute("""
                INSERT INTO credit_payments
                (
                    payment_no,
                    customer_id,
                    credit_id,
                    amount,
                    payment_date,
                    staff_name
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                payment_no,
                customer_id,
                credit["id"],
                allocation,
                payment_date,
                staff_name
            ))

            allocations.append({
                "credit_id": credit["id"],
                "amount": allocation,
                "balance": new_balance,
                "status": new_status
            })

            remaining_payment -= allocation

        conn.commit()

    except Exception as e:

        conn.rollback()

        print("\n❌ Payment failed.")
        print(f"Error: {e}")

        conn.close()

        input("\nPress Enter to continue...")
        return

    conn.close()

    # ------------------------------------
    # PAYMENT RECEIPT
    # ------------------------------------
    print("\n====================================")
    print("       PAYMENT RECEIVED")
    print("====================================")
    print(f"Payment No : {payment_no}")
    print(f"Date       : {payment_date}")
    print(f"Customer   : {customer['fullname']}")
    print(f"Phone      : {customer['phone'] or 'N/A'}")
    print(f"Paid       : ₦{payment_amount:,.2f}")
    print(f"Staff      : {staff_name}")
    print("------------------------------------")

    print("PAYMENT ALLOCATION")
    print("------------------------------------")

    for allocation in allocations:

        print(
            f"Credit #{allocation['credit_id']}"
        )

        print(
            f"Paid      : "
            f"₦{allocation['amount']:,.2f}"
        )

        print(
            f"Remaining : "
            f"₦{allocation['balance']:,.2f}"
        )

        print(
            f"Status    : "
            f"{allocation['status']}"
        )

        print("------------------------------------")

    remaining_debt = (
        total_debt - payment_amount
    )

    print(
        f"Debt Before : "
        f"₦{total_debt:,.2f}"
    )

    print(
        f"Payment     : "
        f"₦{payment_amount:,.2f}"
    )

    print(
        f"Debt After  : "
        f"₦{remaining_debt:,.2f}"
    )

    print("====================================")

    input("\nPress Enter to continue...")


if __name__ == "__main__":
    receive_payment()
