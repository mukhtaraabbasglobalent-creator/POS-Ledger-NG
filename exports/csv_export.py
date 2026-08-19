import csv
import os
from database.connection import get_connection

EXPORT_DIR = "exports/files"


def export_sales_csv():
    if not os.path.exists(EXPORT_DIR):
        os.makedirs(EXPORT_DIR)

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            receipt_no,
            total_amount,
            total_profit,
            payment_method,
            sale_date
        FROM sales
        ORDER BY sale_date DESC
    """)

    rows = cur.fetchall()

    filename = os.path.join(EXPORT_DIR, "sales_report.csv")

    with open(filename, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        writer.writerow([
            "Receipt No",
            "Total Amount",
            "Total Profit",
            "Payment Method",
            "Sale Date"
        ])

        for row in rows:
            writer.writerow([
                row["receipt_no"],
                row["total_amount"],
                row["total_profit"],
                row["payment_method"],
                row["sale_date"]
            ])

    conn.close()

    print("\n========== CSV EXPORT ==========")
    print(f"Saved To : {filename}")
    print("✅ Sales report exported successfully.")


if __name__ == "__main__":
    export_sales_csv()
