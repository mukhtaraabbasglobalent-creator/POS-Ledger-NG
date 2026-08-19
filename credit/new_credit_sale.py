import sqlite3
from datetime import datetime

from staff.manage import current_user

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def new_credit_sale():
    conn = get_connection()
    cur = conn.cursor()

    try:
        print("\n====================================")
        print("          NEW CREDIT SALE")
        print("====================================")

        # ----------------------------------------
        # CUSTOMER
        # ----------------------------------------

        customer_id = input("Customer ID: ").strip()

        if not customer_id.isdigit():
            print("❌ Invalid customer ID.")
            return

        cur.execute("""
            SELECT id, fullname, phone, credit_limit
            FROM customers
            WHERE id = ?
        """, (int(customer_id),))

        customer = cur.fetchone()

        if not customer:
            print("❌ Customer not found.")
            return

        # ----------------------------------------
        # CURRENT CREDIT BALANCE
        # ----------------------------------------

        cur.execute("""
            SELECT COALESCE(SUM(balance), 0)
            FROM customer_credit
            WHERE customer_id = ?
              AND status != 'PAID'
        """, (customer["id"],))

        outstanding = float(cur.fetchone()[0] or 0)

        credit_limit = float(customer["credit_limit"] or 0)

        # If no credit limit has been configured,
        # don't allow unlimited credit accidentally.
        if credit_limit <= 0:
            print("\n❌ This customer has no credit limit.")
            print("Set a credit limit before making a credit sale.")
            return

        available_credit = credit_limit - outstanding

        print("\n====================================")
        print("            CUSTOMER")
        print("====================================")
        print(f"Name              : {customer['fullname']}")
        print(f"Phone             : {customer['phone'] or 'N/A'}")
        print(f"Credit Limit      : ₦{credit_limit:,.2f}")
        print(f"Outstanding Debt  : ₦{outstanding:,.2f}")
        print(f"Available Credit  : ₦{available_credit:,.2f}")
        print("====================================")

        # ----------------------------------------
        # PRODUCT
        # ----------------------------------------

        code = input(
            "\nBarcode / Product ID / Product Name: "
        ).strip()

        if not code:
            print("❌ Product is required.")
            return

        cur.execute("""
            SELECT
                id,
                product_name,
                sku,
                barcode,
                current_stock,
                buying_price,
                selling_price
            FROM products
            WHERE CAST(id AS TEXT) = ?
               OR barcode = ?
               OR sku = ?
               OR LOWER(product_name) LIKE LOWER(?)
            LIMIT 1
        """, (
            code,
            code,
            code,
            f"%{code}%"
        ))

        product = cur.fetchone()

        if not product:
            print("❌ Product not found.")
            return

        print("\n====================================")
        print("          PRODUCT FOUND")
        print("====================================")
        print(f"Product : {product['product_name']}")
        print(f"SKU     : {product['sku']}")
        print(f"Stock   : {product['current_stock']}")
        print(f"Price   : ₦{product['selling_price']:,.2f}")
        print("====================================")

        # ----------------------------------------
        # QUANTITY
        # ----------------------------------------

        try:
            quantity = float(input("Quantity: ").strip())
        except ValueError:
            print("❌ Invalid quantity.")
            return

        if quantity <= 0:
            print("❌ Quantity must be greater than zero.")
            return

        if quantity > float(product["current_stock"]):
            print("\n❌ Not enough stock.")
            print(
                f"Available Stock: "
                f"{product['current_stock']}"
            )
            return

        # ----------------------------------------
        # CALCULATIONS
        # ----------------------------------------

        buying_price = float(product["buying_price"])
        selling_price = float(product["selling_price"])

        subtotal = selling_price * quantity
        profit = (selling_price - buying_price) * quantity

        print("\n====================================")
        print("             CREDIT SALE")
        print("====================================")
        print(f"Product     : {product['product_name']}")
        print(f"Quantity    : {quantity:g}")
        print(f"Unit Price  : ₦{selling_price:,.2f}")
        print(f"Subtotal    : ₦{subtotal:,.2f}")
        print(f"Profit      : ₦{profit:,.2f}")
        print("====================================")

        # ----------------------------------------
        # CREDIT LIMIT CHECK
        # ----------------------------------------

        if subtotal > available_credit:
            print("\n❌ CREDIT LIMIT EXCEEDED")
            print(f"Available Credit : ₦{available_credit:,.2f}")
            print(f"Sale Amount      : ₦{subtotal:,.2f}")
            return

        # ----------------------------------------
        # CONFIRMATION
        # ----------------------------------------

        confirm = input(
            "\nComplete Credit Sale? (Y/N): "
        ).strip().upper()

        if confirm != "Y":
            print("\n❌ Credit sale cancelled.")
            return

        # ----------------------------------------
        # STAFF
        # ----------------------------------------

        user = current_user()

        if user:
            staff_name = user["fullname"]
        else:
            staff_name = "System"

        sale_date = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        # ----------------------------------------
        # RECEIPT NUMBER
        # ----------------------------------------

        today = datetime.now().strftime("%Y%m%d")

        cur.execute("""
            SELECT IFNULL(MAX(id), 0) + 1
            FROM sales
        """)

        next_sale_id = cur.fetchone()[0]

        receipt_no = (
            f"PLN-{today}-{next_sale_id:06d}"
        )

        # ----------------------------------------
        # SAVE SALE
        # ----------------------------------------

        cur.execute("""
            INSERT INTO sales (
                product_id,
                customer_id,
                quantity,
                buying_price,
                selling_price,
                total_amount,
                total_profit,
                sale_date,
                staff_name,
                receipt_no,
                payment_method,
                discount,
                vat,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            product["id"],
            customer["id"],
            quantity,
            buying_price,
            selling_price,
            subtotal,
            profit,
            sale_date,
            staff_name,
            receipt_no,
            "Credit",
            0,
            0,
            "COMPLETED"
        ))

        sale_id = cur.lastrowid

        # ----------------------------------------
        # SAVE SALE ITEM
        # ----------------------------------------

        cur.execute("""
            INSERT INTO sale_items (
                sale_id,
                product_id,
                quantity,
                buying_price,
                selling_price,
                profit,
                subtotal
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            sale_id,
            product["id"],
            quantity,
            buying_price,
            selling_price,
            profit,
            subtotal
        ))

        # ----------------------------------------
        # UPDATE STOCK
        # ----------------------------------------

        cur.execute("""
            UPDATE products
            SET current_stock = current_stock - ?
            WHERE id = ?
        """, (
            quantity,
            product["id"]
        ))

        # ----------------------------------------
        # SAVE RECEIPT
        # ----------------------------------------

        cur.execute("""
            INSERT INTO receipts (
                receipt_no,
                customer_name,
                transaction_type,
                amount,
                charge,
                total,
                receipt_date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            receipt_no,
            customer["fullname"],
            "Credit Sale",
            subtotal,
            0,
            subtotal,
            sale_date
        ))

        # ----------------------------------------
        # SAVE RECEIPT ITEM
        # ----------------------------------------

        cur.execute("""
            INSERT INTO receipt_items (
                receipt_no,
                product_id,
                product_name,
                quantity,
                unit_price,
                line_total
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            receipt_no,
            product["id"],
            product["product_name"],
            quantity,
            selling_price,
            subtotal
        ))

        # ----------------------------------------
        # CREATE CUSTOMER DEBT
        # ----------------------------------------

        cur.execute("""
            INSERT INTO customer_credit (
                customer_id,
                sale_id,
                total_amount,
                amount_paid,
                balance,
                status,
                staff_name,
                created_date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            customer["id"],
            sale_id,
            subtotal,
            0,
            subtotal,
            "UNPAID",
            staff_name,
            sale_date
        ))

        # ----------------------------------------
        # COMMIT EVERYTHING
        # ----------------------------------------

        conn.commit()

        # ----------------------------------------
        # RESULT
        # ----------------------------------------

        print("\n====================================")
        print("       CREDIT SALE COMPLETED")
        print("====================================")
        print(f"Receipt No : {receipt_no}")
        print(f"Sale ID    : {sale_id}")
        print(f"Customer   : {customer['fullname']}")
        print(f"Phone      : {customer['phone'] or 'N/A'}")
        print(f"Product    : {product['product_name']}")
        print(f"Quantity   : {quantity:g}")
        print(f"Amount     : ₦{subtotal:,.2f}")
        print(f"Profit     : ₦{profit:,.2f}")
        print(f"Credit     : ₦{subtotal:,.2f}")
        print(f"Status     : UNPAID")
        print(f"Staff      : {staff_name}")
        print("====================================")

        # ----------------------------------------
        # PRINT RECEIPT
        # ----------------------------------------

        try:
            from sales.receipt import print_receipt

            print_receipt(receipt_no)

        except Exception as receipt_error:
            print(
                "\n⚠️ Sale saved, but receipt display failed:"
            )
            print(receipt_error)

        return True

    except Exception as e:

        conn.rollback()

        print("\n❌ CREDIT SALE FAILED")
        print(f"Error: {e}")

        return False

    finally:

        conn.close()


if __name__ == "__main__":
    new_credit_sale()
