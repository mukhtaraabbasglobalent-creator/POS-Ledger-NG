import sqlite3
from datetime import datetime

DB_NAME = "data/posledger.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def sales_intelligence():
    conn = get_connection()
    cur = conn.cursor()

    print("\n========================================")
    print("       POS LEDGER NG V31")
    print("        SALES INTELLIGENCE")
    print("========================================")

    # --------------------------------------------------
    # Discover available sales tables safely
    # --------------------------------------------------
    tables = [
        row["name"]
        for row in cur.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' ORDER BY name"
        ).fetchall()
    ]

    if "sales" not in tables:
        print("\nNo sales table found.")
        print("V31 requires the existing sales table.")
        conn.close()
        input("\nPress Enter to continue...")
        return

    # --------------------------------------------------
    # Inspect sales table columns
    # --------------------------------------------------
    columns = [
        row["name"]
        for row in cur.execute(
            "PRAGMA table_info(sales)"
        ).fetchall()
    ]

    # --------------------------------------------------
    # Determine compatible columns
    # --------------------------------------------------
    amount_column = None

    for candidate in (
        "total_amount",
        "total",
        "grand_total",
        "amount",
        "sale_amount",
        "net_amount"
    ):
        if candidate in columns:
            amount_column = candidate
            break

    date_column = None

    for candidate in (
        "sale_date",
        "created_at",
        "created_date",
        "transaction_date",
        "date"
    ):
        if candidate in columns:
            date_column = candidate
            break

    customer_column = None

    for candidate in (
        "customer_id",
        "customer",
        "customer_name"
    ):
        if candidate in columns:
            customer_column = candidate
            break

    status_column = None

    for candidate in (
        "status",
        "sale_status"
    ):
        if candidate in columns:
            status_column = candidate
            break

    # --------------------------------------------------
    # Sales count
    # --------------------------------------------------
    total_sales = cur.execute(
        "SELECT COUNT(*) AS count FROM sales"
    ).fetchone()["count"]

    # --------------------------------------------------
    # Total sales amount
    # --------------------------------------------------
    total_revenue = 0.0

    if amount_column:
        row = cur.execute(
            f"""
            SELECT COALESCE(SUM({amount_column}), 0) AS total
            FROM sales
            """
        ).fetchone()

        total_revenue = float(row["total"] or 0)

    # --------------------------------------------------
    # Average sale
    # --------------------------------------------------
    average_sale = (
        total_revenue / total_sales
        if total_sales > 0
        else 0
    )

    # --------------------------------------------------
    # Today's sales
    # --------------------------------------------------
    today_revenue = 0.0
    today_sales = 0

    today = datetime.now().strftime("%Y-%m-%d")

    if date_column:
        today_sales = cur.execute(
            f"""
            SELECT COUNT(*) AS count
            FROM sales
            WHERE DATE({date_column}) = ?
            """,
            (today,)
        ).fetchone()["count"]

        if amount_column:
            today_revenue = float(
                cur.execute(
                    f"""
                    SELECT COALESCE(SUM({amount_column}), 0) AS total
                    FROM sales
                    WHERE DATE({date_column}) = ?
                    """,
                    (today,)
                ).fetchone()["total"] or 0
            )

    # --------------------------------------------------
    # Seven-day sales
    # --------------------------------------------------
    seven_day_revenue = 0.0
    seven_day_sales = 0

    if date_column:
        seven_day_sales = cur.execute(
            f"""
            SELECT COUNT(*) AS count
            FROM sales
            WHERE DATE({date_column})
                  >= DATE('now', '-6 day')
            """
        ).fetchone()["count"]

        if amount_column:
            seven_day_revenue = float(
                cur.execute(
                    f"""
                    SELECT COALESCE(SUM({amount_column}), 0) AS total
                    FROM sales
                    WHERE DATE({date_column})
                          >= DATE('now', '-6 day')
                    """
                ).fetchone()["total"] or 0
            )

    # --------------------------------------------------
    # Thirty-day sales
    # --------------------------------------------------
    thirty_day_revenue = 0.0
    thirty_day_sales = 0

    if date_column:
        thirty_day_sales = cur.execute(
            f"""
            SELECT COUNT(*) AS count
            FROM sales
            WHERE DATE({date_column})
                  >= DATE('now', '-29 day')
            """
        ).fetchone()["count"]

        if amount_column:
            thirty_day_revenue = float(
                cur.execute(
                    f"""
                    SELECT COALESCE(SUM({amount_column}), 0) AS total
                    FROM sales
                    WHERE DATE({date_column})
                          >= DATE('now', '-29 day')
                    """
                ).fetchone()["total"] or 0
            )

    # --------------------------------------------------
    # Status distribution
    # --------------------------------------------------
    completed_sales = total_sales
    cancelled_sales = 0

    if status_column:
        completed_sales = cur.execute(
            f"""
            SELECT COUNT(*) AS count
            FROM sales
            WHERE UPPER(COALESCE({status_column}, '')) IN
                  ('COMPLETED', 'PAID', 'SUCCESS', 'COMPLETED SALE')
            """
        ).fetchone()["count"]

        cancelled_sales = cur.execute(
            f"""
            SELECT COUNT(*) AS count
            FROM sales
            WHERE UPPER(COALESCE({status_column}, '')) IN
                  ('CANCELLED', 'CANCELED', 'VOID')
            """
        ).fetchone()["count"]

    # --------------------------------------------------
    # Sales trend
    # --------------------------------------------------
    trend_status = "INSUFFICIENT DATA"

    if date_column and thirty_day_sales >= 2:

        recent_revenue = 0.0
        previous_revenue = 0.0

        if amount_column:

            recent_revenue = float(
                cur.execute(
                    f"""
                    SELECT COALESCE(SUM({amount_column}), 0) AS total
                    FROM sales
                    WHERE DATE({date_column})
                          >= DATE('now', '-6 day')
                    """
                ).fetchone()["total"] or 0
            )

            previous_revenue = float(
                cur.execute(
                    f"""
                    SELECT COALESCE(SUM({amount_column}), 0) AS total
                    FROM sales
                    WHERE DATE({date_column})
                          BETWEEN DATE('now', '-13 day')
                          AND DATE('now', '-7 day')
                    """
                ).fetchone()["total"] or 0
            )

        if previous_revenue > 0:

            change = (
                (recent_revenue - previous_revenue)
                / previous_revenue
            ) * 100

            if change >= 15:
                trend_status = "🟢 GROWING"

            elif change <= -15:
                trend_status = "🔴 DECLINING"

            else:
                trend_status = "🟡 STABLE"

    # --------------------------------------------------
    # Sales activity status
    # --------------------------------------------------
    if thirty_day_sales == 0:
        activity_status = "🔴 NO RECENT SALES"

    elif thirty_day_sales < 5:
        activity_status = "🟡 LOW SALES ACTIVITY"

    elif thirty_day_sales < 20:
        activity_status = "🟢 ACTIVE SALES"

    else:
        activity_status = "🟢 HIGH SALES ACTIVITY"

    # --------------------------------------------------
    # Data confidence
    # --------------------------------------------------
    if thirty_day_sales >= 30:
        confidence = "🟢 HIGH"

    elif thirty_day_sales >= 10:
        confidence = "🟡 MODERATE"

    elif thirty_day_sales >= 1:
        confidence = "🟠 LIMITED"

    else:
        confidence = "🔴 VERY LIMITED"

    # --------------------------------------------------
    # Management recommendation
    # --------------------------------------------------
    if thirty_day_sales == 0:
        recommendation = (
            "REVIEW SALES ACTIVITY — NO RECENT SALES"
        )

    elif trend_status == "🔴 DECLINING":
        recommendation = (
            "MONITOR SALES DECLINE AND INVESTIGATE CAUSES"
        )

    elif trend_status == "🟢 GROWING":
        recommendation = (
            "MAINTAIN SALES MOMENTUM AND MONITOR PROFIT"
        )

    else:
        recommendation = (
            "NORMAL SALES MONITORING"
        )

    # --------------------------------------------------
    # Output
    # --------------------------------------------------
    print("\n========================================")
    print("        SALES POSITION")
    print("========================================")
    print(f"Total Sales       : {total_sales}")
    print(f"Total Revenue     : ₦{total_revenue:,.2f}")
    print(f"Average Sale      : ₦{average_sale:,.2f}")

    print("\n========================================")
    print("        SALES ACTIVITY")
    print("========================================")
    print(f"Today Sales       : {today_sales}")
    print(f"Today Revenue     : ₦{today_revenue:,.2f}")
    print(f"7-Day Sales       : {seven_day_sales}")
    print(f"7-Day Revenue     : ₦{seven_day_revenue:,.2f}")
    print(f"30-Day Sales      : {thirty_day_sales}")
    print(f"30-Day Revenue    : ₦{thirty_day_revenue:,.2f}")
    print(f"Activity Status   : {activity_status}")

    print("\n========================================")
    print("        SALES STATUS")
    print("========================================")
    print(f"Completed Sales   : {completed_sales}")
    print(f"Cancelled Sales   : {cancelled_sales}")

    print("\n========================================")
    print("        SALES TREND")
    print("========================================")
    print(f"Trend Status      : {trend_status}")

    print("\n========================================")
    print("        DATA CONFIDENCE")
    print("========================================")
    print(f"Confidence        : {confidence}")

    print("\n========================================")
    print("       MANAGEMENT DECISION")
    print("========================================")
    print(f"Recommendation    : {recommendation}")

    print("\n========================================")
    print("       MANAGEMENT SUMMARY")
    print("========================================")
    print(f"• Total revenue is ₦{total_revenue:,.2f}.")
    print(f"• {total_sales} sale(s) are recorded.")
    print(f"• 30-day revenue is ₦{thirty_day_revenue:,.2f}.")
    print(f"• Sales trend is {trend_status}.")
    print(f"• Activity status is {activity_status}.")
    print(f"• Data confidence is {confidence}.")
    print(f"• Recommendation: {recommendation}.")

    print("----------------------------------------")
    print("V31 STATUS : READ-ONLY")
    print("Sales records were NOT modified.")
    print("========================================")

    conn.close()

    input("\nPress Enter to continue...")


if __name__ == "__main__":
    sales_intelligence()
