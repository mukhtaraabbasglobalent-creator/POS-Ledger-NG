from database.connection import get_connection


def customer_statement():

    conn = get_connection()
    cur = conn.cursor()

    print("\n========================================")
    print("          CUSTOMER STATEMENT")
    print("========================================")

    customer_id = input("Customer ID: ").strip()

    if not customer_id.isdigit():
        print("\n❌ Invalid Customer ID.")
        conn.close()
        input("\nPress Enter to continue...")
        return

    cur.execute("""
        SELECT
            id,
            fullname,
            phone,
            email,
            address,
            credit_limit
        FROM customers
        WHERE id = ?
    """, (customer_id,))

    customer = cur.fetchone()

    if customer is None:

        print("\n❌ Customer not found.")

        conn.close()
        input("\nPress Enter to continue...")
        return

    print(f"Customer : {customer['fullname']}")
    print(f"Phone    : {customer['phone']}")
    print(f"Email    : {customer['email']}")
    print(f"Address  : {customer['address']}")
    print(f"Credit Limit: ₦{customer['credit_limit']:,.2f}")

    print("\n========================================")
    print("       FINANCIAL TRANSACTIONS")
    print("========================================")

    cur.execute("""
        SELECT
            id,
            transaction_type,
            amount,
            charge,
            provider_fee,
            profit,
            provider,
            transaction_date
        FROM transactions
        WHERE customer_id = ?
        ORDER BY id DESC
    """, (customer_id,))

    transactions = cur.fetchall()

    total_amount = 0
    total_charge = 0
    total_provider_fee = 0
    total_profit = 0

    if not transactions:

        print("No financial transactions found.")

    else:

        for transaction in transactions:

            amount = transaction["amount"] or 0
            charge = transaction["charge"] or 0
            provider_fee = transaction["provider_fee"] or 0
            profit = transaction["profit"] or 0

            total_amount += amount
            total_charge += charge
            total_provider_fee += provider_fee
            total_profit += profit

            print("----------------------------------------")

            print(
                f"Transaction ID : "
                f"{transaction['id']}"
            )

            print(
                f"Provider       : "
                f"{transaction['provider'] or 'N/A'}"
            )

            print(
                f"Type           : "
                f"{transaction['transaction_type']}"
            )

            print(
                f"Amount         : "
                f"₦{amount:,.2f}"
            )

            print(
                f"Customer Charge: "
                f"₦{charge:,.2f}"
            )

            print(
                f"Provider Fee   : "
                f"₦{provider_fee:,.2f}"
            )

            print(
                f"Profit         : "
                f"₦{profit:,.2f}"
            )

            print(
                f"Date           : "
                f"{transaction['transaction_date']}"
            )

        print("----------------------------------------")

        print(
            f"TOTAL AMOUNT   : "
            f"₦{total_amount:,.2f}"
        )

        print(
            f"TOTAL CHARGES  : "
            f"₦{total_charge:,.2f}"
        )

        print(
            f"TOTAL FEES     : "
            f"₦{total_provider_fee:,.2f}"
        )

        print(
            f"TOTAL PROFIT   : "
            f"₦{total_profit:,.2f}"
        )

    print("\n========================================")
    print("             SALES HISTORY")
    print("========================================")

    cur.execute("""
        SELECT
            receipt_no,
            sale_date,
            total_amount,
            payment_method,
            status
        FROM sales
        WHERE customer_id = ?
        ORDER BY id DESC
    """, (customer_id,))

    sales = cur.fetchall()

    total_sales = 0

    if not sales:

        print("No sales found for this customer.")

    else:

        for sale in sales:

            sale_amount = sale["total_amount"] or 0
            total_sales += sale_amount

            print("----------------------------------------")

            print(
                f"Receipt  : "
                f"{sale['receipt_no']}"
            )

            print(
                f"Date     : "
                f"{sale['sale_date']}"
            )

            print(
                f"Amount   : "
                f"₦{sale_amount:,.2f}"
            )

            print(
                f"Payment  : "
                f"{sale['payment_method']}"
            )

            print(
                f"Status   : "
                f"{sale['status']}"
            )

        print("----------------------------------------")

        print(
            f"TOTAL SALES: "
            f"₦{total_sales:,.2f}"
        )

    print("\n========================================")
    print("          STATEMENT SUMMARY")
    print("========================================")

    print(
        f"Transaction Amount : "
        f"₦{total_amount:,.2f}"
    )

    print(
        f"Transaction Charges: "
        f"₦{total_charge:,.2f}"
    )

    print(
        f"Transaction Profit  : "
        f"₦{total_profit:,.2f}"
    )

    print(
        f"Sales Amount        : "
        f"₦{total_sales:,.2f}"
    )

    print("========================================")

    conn.close()

    input("\nPress Enter to continue...")


if __name__ == "__main__":
    customer_statement()
