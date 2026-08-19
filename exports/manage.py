import os
import csv
import sqlite3
from datetime import datetime
from openpyxl import Workbook

DB_NAME = "data/posledger.db"
EXPORT_DIR = "exports/files"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_export_folder():
    if not os.path.exists(EXPORT_DIR):
        os.makedirs(EXPORT_DIR)


def export_sales_csv():

    ensure_export_folder()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            id,
            product_id,
            quantity,
            buying_price,
            selling_price,
            total_amount,
            total_profit,
            sale_date
        FROM sales
        ORDER BY id DESC
    """)

    rows = cur.fetchall()

    filename = os.path.join(
        EXPORT_DIR,
        f"sales_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )

    with open(filename, "w", newline="", encoding="utf-8") as file:

        writer = csv.writer(file)

        writer.writerow([
            "ID",
            "Product ID",
            "Quantity",
            "Buying Price",
            "Selling Price",
            "Total Amount",
            "Profit",
            "Sale Date"
        ])

        for row in rows:
            writer.writerow([
                row["id"],
                row["product_id"],
                row["quantity"],
                row["buying_price"],
                row["selling_price"],
                row["total_amount"],
                row["total_profit"],
                row["sale_date"]
            ])

    conn.close()

    print("\n========== EXPORT ==========")
    print("Sales exported successfully.")
    print(f"File: {filename}")
    print("============================")
def export_purchases_csv():

    ensure_export_folder()

    conn = get_connection()
    cur = conn.cursor()

    try:

        cur.execute("""
            SELECT *
            FROM purchases
            ORDER BY id DESC
        """)

        rows = cur.fetchall()

    except sqlite3.OperationalError:

        print("\n❌ Purchases table not found.")
        conn.close()
        return

    filename = os.path.join(
        EXPORT_DIR,
        f"purchases_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )

    with open(filename, "w", newline="", encoding="utf-8") as file:

        writer = csv.writer(file)

        if rows:

            writer.writerow(rows[0].keys())

            for row in rows:
                writer.writerow(list(row))

    conn.close()

    print("\n========== EXPORT ==========")
    print("Purchases exported successfully.")
    print(f"File: {filename}")
    print("============================")


def export_expenses_csv():

    ensure_export_folder()

    conn = get_connection()
    cur = conn.cursor()

    try:

        cur.execute("""
            SELECT *
            FROM expenses
            ORDER BY id DESC
        """)

        rows = cur.fetchall()

    except sqlite3.OperationalError:

        print("\n❌ Expenses table not found.")
        conn.close()
        return

    filename = os.path.join(
        EXPORT_DIR,
        f"expenses_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )

    with open(filename, "w", newline="", encoding="utf-8") as file:

        writer = csv.writer(file)

        if rows:

            writer.writerow(rows[0].keys())

            for row in rows:
                writer.writerow(list(row))

    conn.close()

    print("\n========== EXPORT ==========")
    print("Expenses exported successfully.")
    print(f"File: {filename}")
    print("============================")
def export_sales_excel():

    ensure_export_folder()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            id,
            product_id,
            quantity,
            buying_price,
            selling_price,
            total_amount,
            total_profit,
            sale_date
        FROM sales
        ORDER BY id DESC
    """)

    rows = cur.fetchall()

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Sales"

    sheet.append([
        "ID",
        "Product ID",
        "Quantity",
        "Buying Price",
        "Selling Price",
        "Total Amount",
        "Profit",
        "Sale Date"
    ])

    for row in rows:
        sheet.append([
            row["id"],
            row["product_id"],
            row["quantity"],
            row["buying_price"],
            row["selling_price"],
            row["total_amount"],
            row["total_profit"],
            row["sale_date"]
        ])

    filename = os.path.join(
        EXPORT_DIR,
        f"sales_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    )

    workbook.save(filename)

    conn.close()

    print("\n========== EXPORT ==========")
    print("Sales exported to Excel successfully.")
    print(f"File: {filename}")
    print("============================")


def export_menu():

    while True:

        print("""
========== EXPORT REPORTS ==========
1. Export Sales (CSV)
2. Export Purchases (CSV)
3. Export Expenses (CSV)
4. Export Sales (Excel)
0. Back
====================================
""")

        choice = input("Select option: ").strip()

        if choice == "1":
            export_sales_csv()

        elif choice == "2":
            export_purchases_csv()

        elif choice == "3":
            export_expenses_csv()

        elif choice == "4":
            export_sales_excel()

        elif choice == "0":
            break

        else:
            print("Invalid option.")


if __name__ == "__main__":
    export_menu()
