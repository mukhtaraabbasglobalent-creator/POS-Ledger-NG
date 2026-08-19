import sqlite3
import shutil
from datetime import datetime

DB_PATH = "data/posledger.db"


def execute_v37_repair():
    print("=" * 40)
    print("       POS LEDGER NG V37")
    print("   CONTROLLED SALES REPAIR")
    print("=" * 40)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"data/posledger_v37_repair_{timestamp}.db"

    # SAFETY BACKUP
    shutil.copy2(DB_PATH, backup_path)

    print(f"Backup created : {backup_path}")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    try:
        conn.execute("BEGIN")

        # --------------------------------------------------
        # REPAIR SALE 1
        # --------------------------------------------------

        cur.execute(
            """
            SELECT
                id,
                product_id,
                quantity,
                buying_price,
                selling_price
            FROM sales
            WHERE id = 1
            """
        )

        sale = cur.fetchone()

        if sale:
            subtotal = sale["quantity"] * sale["selling_price"]

            profit = sale["quantity"] * (
                sale["selling_price"]
                - sale["buying_price"]
            )

            cur.execute(
                """
                UPDATE sale_items
                SET
                    product_id = ?,
                    quantity = ?,
                    buying_price = ?,
                    selling_price = ?,
                    profit = ?,
                    subtotal = ?
                WHERE sale_id = 1
                """,
                (
                    sale["product_id"],
                    sale["quantity"],
                    sale["buying_price"],
                    sale["selling_price"],
                    profit,
                    subtotal,
                ),
            )

            print("Sale 1 sale_item corrected.")

        # --------------------------------------------------
        # FIND MISSING SALE ITEMS
        # --------------------------------------------------

        cur.execute(
            """
            SELECT
                s.id,
                s.product_id,
                s.quantity,
                s.buying_price,
                s.selling_price
            FROM sales AS s
            LEFT JOIN sale_items AS si
                ON si.sale_id = s.id
            WHERE
                (s.status IS NULL OR s.status != 'CANCELLED')
                AND si.id IS NULL
            ORDER BY s.id
            """
        )

        missing_sales = cur.fetchall()

        created = 0

        # --------------------------------------------------
        # CREATE MISSING SALE ITEMS
        # --------------------------------------------------

        for sale in missing_sales:

            subtotal = (
                sale["quantity"]
                * sale["selling_price"]
            )

            profit = sale["quantity"] * (
                sale["selling_price"]
                - sale["buying_price"]
            )

            cur.execute(
                """
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
                """,
                (
                    sale["id"],
                    sale["product_id"],
                    sale["quantity"],
                    sale["buying_price"],
                    sale["selling_price"],
                    profit,
                    subtotal,
                ),
            )

            created += 1

            print(
                f"Sale {sale['id']} sale_item created."
            )

        # --------------------------------------------------
        # VERIFY MISSING ITEMS
        # --------------------------------------------------

        cur.execute(
            """
            SELECT COUNT(*)
            FROM sales AS s
            LEFT JOIN sale_items AS si
                ON si.sale_id = s.id
            WHERE
                (s.status IS NULL OR s.status != 'CANCELLED')
                AND si.id IS NULL
            """
        )

        remaining_missing = cur.fetchone()[0]

        # --------------------------------------------------
        # VERIFY PRODUCT / QUANTITY / PRICE
        # --------------------------------------------------

        cur.execute(
            """
            SELECT COUNT(*)
            FROM sale_items AS si
            JOIN sales AS s
                ON s.id = si.sale_id
            WHERE
                s.product_id != si.product_id
                OR ABS(s.quantity - si.quantity) > 0.000001
                OR ABS(
                    s.buying_price - si.buying_price
                ) > 0.000001
                OR ABS(
                    s.selling_price - si.selling_price
                ) > 0.000001
            """
        )

        remaining_mismatches = cur.fetchone()[0]

        # --------------------------------------------------
        # VERIFY FINANCIAL VALUES
        # --------------------------------------------------

        cur.execute(
            """
            SELECT COUNT(*)
            FROM sale_items AS si
            JOIN sales AS s
                ON s.id = si.sale_id
            WHERE
                ABS(
                    si.subtotal -
                    (
                        si.quantity
                        * si.selling_price
                    )
                ) > 0.000001
                OR ABS(
                    si.profit -
                    (
                        si.quantity
                        * (
                            si.selling_price
                            - si.buying_price
                        )
                    )
                ) > 0.000001
            """
        )

        remaining_financial_errors = cur.fetchone()[0]

        print("\n" + "=" * 40)
        print("       REPAIR VERIFICATION")
        print("=" * 40)

        print(f"Created sale_items      : {created}")
        print(f"Missing items remaining : {remaining_missing}")
        print(f"Mismatches remaining    : {remaining_mismatches}")
        print(
            f"Financial errors        : "
            f"{remaining_financial_errors}"
        )

        # --------------------------------------------------
        # SAFETY DECISION
        # --------------------------------------------------

        if (
            remaining_missing != 0
            or remaining_mismatches != 0
            or remaining_financial_errors != 0
        ):
            raise RuntimeError(
                "Repair verification failed."
            )

        conn.commit()

        print("\n" + "=" * 40)
        print("       REPAIR STATUS")
        print("=" * 40)

        print("Status            : REPAIR COMMITTED")
        print("Database modified : YES")
        print(f"Backup preserved  : {backup_path}")

    except Exception as error:

        conn.rollback()

        print("\n" + "=" * 40)
        print("       REPAIR STATUS")
        print("=" * 40)

        print("Status            : ROLLED BACK")
        print("Database modified : NO")
        print(f"Reason            : {error}")
        print(f"Backup preserved  : {backup_path}")

    finally:
        conn.close()


if __name__ == "__main__":
    execute_v37_repair()
