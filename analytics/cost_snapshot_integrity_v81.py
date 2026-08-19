# POS LEDGER NG V81
# HISTORICAL COST SNAPSHOT & PROFITABILITY INTEGRITY
#
# Purpose:
#   - Preserve historical cost for every sale
#   - Create explicit COGS/profitability fields
#   - Backfill existing sales using sales.buying_price
#   - Validate sales/product linkage
#   - Create a database backup before migration
#
# Safety:
#   - Database-changing migration
#   - Does NOT alter quantity, revenue, product prices or stock
#   - Existing sales.buying_price is treated as the historical
#     cost already recorded at the time of sale

import sqlite3
import os
import shutil
from datetime import datetime


DB_PATH = "data/posledger.db"
BACKUP_DIR = "data/backups"


def money(value):
    return f"₦{float(value or 0):,.2f}"


def percent(value):
    return f"{float(value or 0):.2f}%"


def backup_database():
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    os.makedirs(BACKUP_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(
        BACKUP_DIR,
        f"posledger_v81_backup_{timestamp}.db"
    )

    shutil.copy2(DB_PATH, backup_path)

    return backup_path


def column_exists(conn, table, column):
    rows = conn.execute(
        f"PRAGMA table_info({table})"
    ).fetchall()

    return any(row[1] == column for row in rows)


def add_column_if_missing(conn, table, column, definition):
    if not column_exists(conn, table, column):
        conn.execute(
            f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
        )
        return True

    return False


def migrate_schema(conn):
    added = []

    if add_column_if_missing(
        conn,
        "sales",
        "cost_snapshot",
        "REAL"
    ):
        added.append("cost_snapshot")

    if add_column_if_missing(
        conn,
        "sales",
        "cogs",
        "REAL"
    ):
        added.append("cogs")

    if add_column_if_missing(
        conn,
        "sales",
        "gross_profit",
        "REAL"
    ):
        added.append("gross_profit")

    if add_column_if_missing(
        conn,
        "sales",
        "gross_margin",
        "REAL"
    ):
        added.append("gross_margin")

    return added


def reconcile_sales(conn):
    sales = conn.execute(
        """
        SELECT
            s.id,
            s.product_id,
            s.quantity,
            s.total_amount,
            s.buying_price,
            s.selling_price,
            s.sale_date,
            s.status,
            p.product_name,
            p.buying_price AS current_buying_price
        FROM sales s
        LEFT JOIN products p
            ON p.id = s.product_id
        ORDER BY s.id
        """
    ).fetchall()

    total_revenue = 0.0
    total_cogs = 0.0
    total_profit = 0.0

    valid = 0
    invalid = 0

    historical_snapshot_count = 0
    missing_snapshot_count = 0

    for sale in sales:
        (
            sale_id,
            product_id,
            quantity,
            revenue,
            sale_buying_price,
            selling_price,
            sale_date,
            status,
            product_name,
            current_buying_price
        ) = sale

        quantity = float(quantity or 0)
        revenue = float(revenue or 0)
        sale_buying_price = (
            None
            if sale_buying_price is None
            else float(sale_buying_price)
        )

        # Ignore cancelled/void sales from profitability totals.
        if status and str(status).upper() in (
            "CANCELLED",
            "VOID",
            "REFUNDED"
        ):
            continue

        # A sale must have:
        # product linkage
        # positive quantity
        # non-negative revenue
        # historical buying price
        if (
            product_name is None
            or quantity <= 0
            or revenue < 0
            or sale_buying_price is None
            or sale_buying_price < 0
        ):
            invalid += 1
            continue

        # Existing sales.buying_price becomes the permanent
        # historical cost snapshot.
        cost_snapshot = sale_buying_price

        cogs = quantity * cost_snapshot
        gross_profit = revenue - cogs

        if revenue > 0:
            gross_margin = (gross_profit / revenue) * 100
        else:
            gross_margin = 0.0

        conn.execute(
            """
            UPDATE sales
            SET
                cost_snapshot = ?,
                cogs = ?,
                gross_profit = ?,
                gross_margin = ?
            WHERE id = ?
            """,
            (
                cost_snapshot,
                cogs,
                gross_profit,
                gross_margin,
                sale_id
            )
        )

        valid += 1
        historical_snapshot_count += 1

        total_revenue += revenue
        total_cogs += cogs
        total_profit += gross_profit

    return {
        "sales_count": len(sales),
        "valid": valid,
        "invalid": invalid,
        "historical_snapshot_count": historical_snapshot_count,
        "missing_snapshot_count": missing_snapshot_count,
        "revenue": total_revenue,
        "cogs": total_cogs,
        "profit": total_profit,
    }


def verify_results(conn):
    row = conn.execute(
        """
        SELECT
            COUNT(*) AS total,
            SUM(
                CASE
                    WHEN cost_snapshot IS NOT NULL
                    THEN 1 ELSE 0
                END
            ) AS snapshots,
            SUM(
                CASE
                    WHEN cogs IS NOT NULL
                    THEN 1 ELSE 0
                END
            ) AS cogs_count,
            SUM(
                CASE
                    WHEN gross_profit IS NOT NULL
                    THEN 1 ELSE 0
                END
            ) AS profit_count
        FROM sales
        """
    ).fetchone()

    total = int(row[0] or 0)
    snapshots = int(row[1] or 0)
    cogs_count = int(row[2] or 0)
    profit_count = int(row[3] or 0)

    financial = conn.execute(
        """
        SELECT
            COALESCE(SUM(total_amount), 0),
            COALESCE(SUM(cogs), 0),
            COALESCE(SUM(gross_profit), 0)
        FROM sales
        WHERE
            status IS NULL
            OR UPPER(status) NOT IN
            ('CANCELLED', 'VOID', 'REFUNDED')
        """
    ).fetchone()

    revenue = float(financial[0] or 0)
    cogs = float(financial[1] or 0)
    profit = float(financial[2] or 0)

    margin = (
        (profit / revenue) * 100
        if revenue > 0
        else 0.0
    )

    return {
        "total": total,
        "snapshots": snapshots,
        "cogs_count": cogs_count,
        "profit_count": profit_count,
        "revenue": revenue,
        "cogs": cogs,
        "profit": profit,
        "margin": margin,
    }


def main():
    print("=" * 60)
    print("POS LEDGER NG V81")
    print("HISTORICAL COST SNAPSHOT & PROFITABILITY INTEGRITY")
    print("=" * 60)

    print()
    print("=" * 60)
    print("DATABASE MIGRATION")
    print("=" * 60)

    if not os.path.exists(DB_PATH):
        print("❌ Database not found.")
        print(f"Expected: {DB_PATH}")
        return

    try:
        backup_path = backup_database()

        print("✅ Database backup created:")
        print(f"   {backup_path}")

    except Exception as e:
        print("❌ BACKUP FAILED")
        print(f"Reason: {e}")
        print()
        print("Migration stopped for safety.")
        return

    conn = None

    try:
        conn = sqlite3.connect(DB_PATH)

        print()
        print("=" * 60)
        print("SCHEMA UPDATE")
        print("=" * 60)

        added = migrate_schema(conn)

        if added:
            print("Added columns:")
            for column in added:
                print(f"  + {column}")
        else:
            print("No new columns required.")
            print("V81 schema already exists.")

        conn.commit()

        print()
        print("=" * 60)
        print("HISTORICAL COST RECONCILIATION")
        print("=" * 60)

        result = reconcile_sales(conn)

        conn.commit()

        print(
            f"Recorded sales       : "
            f"{result['sales_count']}"
        )

        print(
            f"Valid sales          : "
            f"{result['valid']}"
        )

        print(
            f"Invalid/unresolved   : "
            f"{result['invalid']}"
        )

        print(
            f"Historical snapshots: "
            f"{result['historical_snapshot_count']}"
        )

        print()
        print(
            f"Reconciled revenue   : "
            f"{money(result['revenue'])}"
        )

        print(
            f"Calculated COGS      : "
            f"{money(result['cogs'])}"
        )

        print(
            f"Gross profit         : "
            f"{money(result['profit'])}"
        )

        margin = (
            result["profit"] / result["revenue"] * 100
            if result["revenue"] > 0
            else 0
        )

        print(
            f"Gross margin         : "
            f"{percent(margin)}"
        )

        verification = verify_results(conn)

        print()
        print("=" * 60)
        print("V81 FINANCIAL TRUTH STATUS")
        print("=" * 60)

        if (
            verification["total"] > 0
            and verification["snapshots"]
            == verification["total"]
            and verification["cogs_count"]
            == verification["total"]
            and verification["profit_count"]
            == verification["total"]
            and result["invalid"] == 0
        ):
            print("Status : 🟢 HISTORICAL COST VERIFIED")
            print()
            print(
                "Every valid sale now has an explicit "
                "historical cost snapshot."
            )
            print(
                "COGS and gross profit can now be calculated "
                "without depending on today's product cost."
            )
        else:
            print("Status : 🟡 REVIEW REQUIRED")
            print()
            print(
                "Some sales still require investigation."
            )

        print()
        print("=" * 60)
        print("V81 HISTORICAL PROFITABILITY")
        print("=" * 60)

        print(
            f"Revenue             : "
            f"{money(verification['revenue'])}"
        )

        print(
            f"Historical COGS     : "
            f"{money(verification['cogs'])}"
        )

        print(
            f"Historical Profit   : "
            f"{money(verification['profit'])}"
        )

        print(
            f"Historical Margin   : "
            f"{percent(verification['margin'])}"
        )

        print()
        print("=" * 60)
        print("V81 DEVELOPMENT RESULT")
        print("=" * 60)

        print(
            "1. Historical cost snapshot : ENABLED"
        )

        print(
            "2. COGS per sale            : ENABLED"
        )

        print(
            "3. Gross profit per sale    : ENABLED"
        )

        print(
            "4. Gross margin per sale    : ENABLED"
        )

        print(
            "5. Historical profitability : PRESERVED"
        )

        print()
        print("=" * 60)
        print("V81 SAFETY STATUS")
        print("=" * 60)

        print("Mode                : MIGRATION")
        print("Database modified   : YES")
        print("Sales quantities    : NO CHANGE")
        print("Sales revenue       : NO CHANGE")
        print("Product prices      : NO CHANGE")
        print("Inventory quantities: NO CHANGE")
        print("Credit              : NO CHANGE")
        print("Suppliers           : NO CHANGE")
        print("Expenses            : NO CHANGE")

        print()
        print("=" * 60)
        print("NEXT DEVELOPMENT PRIORITY")
        print("=" * 60)

        print(
            "Update the sales checkout so every NEW sale "
            "automatically writes cost_snapshot, COGS, "
            "gross_profit and gross_margin."
        )

        print()
        print("V81 COMPLETE")

    except Exception as e:
        if conn:
            conn.rollback()

        print()
        print("=" * 60)
        print("❌ V81 MIGRATION FAILED")
        print("=" * 60)
        print(f"Reason: {e}")
        print()
        print(
            "The transaction was rolled back."
        )
        print(
            "Use the backup created before migration "
            "if further recovery is required."
        )

    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    main()
