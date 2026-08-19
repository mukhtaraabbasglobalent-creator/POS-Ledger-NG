from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from database.connection import get_connection
import os


EXPORT_DIR = "exports/files"


def export_sales_pdf():
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

    filename = os.path.join(EXPORT_DIR, "sales_report.pdf")

    pdf = SimpleDocTemplate(filename)

    data = [[
        "Receipt",
        "Amount",
        "Profit",
        "Payment",
        "Date"
    ]]

    for row in rows:
        data.append([
            row["receipt_no"],
            f"₦{row['total_amount']:.2f}",
            f"₦{row['total_profit']:.2f}",
            row["payment_method"],
            row["sale_date"]
        ])

    table = Table(data)

    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.grey),
        ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
        ("GRID", (0,0), (-1,-1), 1, colors.black),
        ("BACKGROUND", (0,1), (-1,-1), colors.beige),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("BOTTOMPADDING", (0,0), (-1,0), 10),
    ]))

    pdf.build([table])

    conn.close()

    print("\n========== PDF EXPORT ==========")
    print(f"Saved To : {filename}")
    print("✅ Sales report exported successfully.")


if __name__ == "__main__":
    export_sales_pdf()
