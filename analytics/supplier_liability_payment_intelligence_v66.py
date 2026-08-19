import sqlite3
from pathlib import Path
from dataclasses import dataclass


DB_PATH = Path("data/posledger.db")


@dataclass
class SupplierPosition:
    supplier: str
    liability: float
    concentration: float = 0.0
    priority: str = "MONITOR"
    risk_score: float = 0.0
    recommendation: str = ""
    reason: str = ""


def money(value):
    return f"₦{value:,.2f}"


def get_connection():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    return sqlite3.connect(DB_PATH)


def table_exists(conn, table):
    row = conn.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' AND name=?",
        (table,),
    ).fetchone()

    return row is not None


def get_columns(conn, table):
    if not table_exists(conn, table):
        return []

    try:
        rows = conn.execute(
            f"PRAGMA table_info({table})"
        ).fetchall()

        return [row[1] for row in rows]
    except sqlite3.Error:
        return []


def find_column(columns, candidates):
    for candidate in candidates:
        if candidate in columns:
            return candidate

    return None


def safe_sum(conn, table, column):
    if not table_exists(conn, table):
        return 0.0

    columns = get_columns(conn, table)

    if column not in columns:
        return 0.0

    try:
        row = conn.execute(
            f"SELECT COALESCE(SUM({column}), 0) "
            f"FROM {table}"
        ).fetchone()

        return float(row[0] or 0)

    except sqlite3.Error:
        return 0.0


def get_liquid_funds(conn):
    if not table_exists(conn, "balance"):
        return 0.0

    columns = get_columns(conn, "balance")

    cash_column = find_column(
        columns,
        [
            "cash_balance",
            "cash",
            "cash_amount",
        ],
    )

    wallet_column = find_column(
        columns,
        [
            "wallet_balance",
            "wallet",
            "wallet_amount",
        ],
    )

    if not cash_column and not wallet_column:
        return 0.0

    cash = 0.0
    wallet = 0.0

    try:
        select_parts = []

        if cash_column:
            select_parts.append(
                f"COALESCE({cash_column}, 0)"
            )
        else:
            select_parts.append("0")

        if wallet_column:
            select_parts.append(
                f"COALESCE({wallet_column}, 0)"
            )
        else:
            select_parts.append("0")

        query = (
            "SELECT "
            + ", ".join(select_parts)
            + " FROM balance "
            "ORDER BY id DESC LIMIT 1"
        )

        row = conn.execute(query).fetchone()

        if row:
            cash = float(row[0] or 0)
            wallet = float(row[1] or 0)

    except sqlite3.Error:
        pass

    return cash + wallet


def get_supplier_name(conn, supplier_id):
    if not table_exists(conn, "suppliers"):
        return str(supplier_id)

    columns = get_columns(conn, "suppliers")

    id_column = find_column(
        columns,
        [
            "id",
            "supplier_id",
        ],
    )

    name_column = find_column(
        columns,
        [
            "name",
            "supplier_name",
            "company_name",
            "business_name",
        ],
    )

    if not id_column or not name_column:
        return str(supplier_id)

    try:
        row = conn.execute(
            f"""
            SELECT {name_column}
            FROM suppliers
            WHERE {id_column} = ?
            LIMIT 1
            """,
            (supplier_id,),
        ).fetchone()

        if row and row[0]:
            return str(row[0])

    except sqlite3.Error:
        pass

    return str(supplier_id)


def get_supplier_positions(conn):
    positions = []

    if not table_exists(conn, "creditors"):
        return positions

    columns = get_columns(conn, "creditors")

    amount_column = find_column(
        columns,
        [
            "balance",
            "amount",
            "outstanding",
            "outstanding_balance",
            "credit_amount",
            "total_amount",
        ],
    )

    supplier_column = find_column(
        columns,
        [
            "supplier_id",
            "supplier",
            "supplier_name",
            "creditor",
            "creditor_name",
        ],
    )

    if not amount_column:
        return positions

    try:
        if supplier_column:
            rows = conn.execute(
                f"""
                SELECT
                    {supplier_column},
                    COALESCE(SUM({amount_column}), 0)
                FROM creditors
                GROUP BY {supplier_column}
                HAVING COALESCE(SUM({amount_column}), 0) > 0
                ORDER BY
                    COALESCE(SUM({amount_column}), 0) DESC
                """
            ).fetchall()
        else:
            row = conn.execute(
                f"""
                SELECT
                    COALESCE(SUM({amount_column}), 0)
                FROM creditors
                WHERE {amount_column} > 0
                """
            ).fetchone()

            rows = [
                ("ALL SUPPLIERS", float(row[0] or 0))
            ] if row else []

    except sqlite3.Error:
        return positions

    total = sum(float(row[-1] or 0) for row in rows)

    for row in rows:
        raw_supplier = row[0]
        liability = float(row[-1] or 0)

        if supplier_column:
            supplier_name = get_supplier_name(
                conn,
                raw_supplier,
            )
        else:
            supplier_name = str(raw_supplier)

        concentration = (
            liability / total * 100
            if total > 0
            else 0
        )

        positions.append(
            SupplierPosition(
                supplier=supplier_name,
                liability=liability,
                concentration=concentration,
            )
        )

    return positions


def classify_supplier(position, total_liability, liquid):
    liability = position.liability

    if total_liability <= 0:
        position.priority = "MONITOR"
        position.risk_score = 0
        position.recommendation = (
            "No outstanding supplier liability."
        )
        position.reason = (
            "No supplier payment pressure detected."
        )
        return

    liquidity_ratio = (
        liquid / total_liability
        if total_liability > 0
        else 0
    )

    if liability >= total_liability * 0.50:
        risk = 35
        priority = "URGENT"
        recommendation = (
            "Prioritize this supplier because "
            "it represents the largest liability "
            "concentration."
        )
        reason = (
            "High supplier concentration."
        )

    elif liability >= total_liability * 0.25:
        risk = 25
        priority = "HIGH"
        recommendation = (
            "Plan a structured payment for this "
            "supplier and monitor the outstanding balance."
        )
        reason = (
            "Significant supplier exposure."
        )

    else:
        risk = 15
        priority = "MONITOR"
        recommendation = (
            "Continue monitoring and schedule payment "
            "according to cash availability."
        )
        reason = (
            "Smaller supplier liability."
        )

    if liquidity_ratio < 0.50:
        risk += 15

        if priority == "MONITOR":
            priority = "MEDIUM"

        reason += (
            " Liquid funds cover less than half "
            "of total supplier obligations."
        )

    position.priority = priority
    position.risk_score = min(risk, 100)
    position.recommendation = recommendation
    position.reason = reason


def print_report():
    conn = get_connection()

    try:
        liquid = get_liquid_funds(conn)

        positions = get_supplier_positions(conn)

        total_liability = sum(
            p.liability for p in positions
        )

        for position in positions:
            classify_supplier(
                position,
                total_liability,
                liquid,
            )

        print("=" * 60)
        print("POS LEDGER NG V66")
        print("SUPPLIER LIABILITY & PAYMENT INTELLIGENCE")
        print("=" * 60)

        print("\n" + "=" * 60)
        print("SUPPLIER POSITION")
        print("=" * 60)

        print(
            f"Total Supplier Liability : "
            f"{money(total_liability)}"
        )

        print(
            f"Available Liquid Funds   : "
            f"{money(liquid)}"
        )

        payment_gap = max(
            total_liability - liquid,
            0,
        )

        print(
            f"Payment Liquidity Gap    : "
            f"{money(payment_gap)}"
        )

        if total_liability > 0:
            coverage = (
                liquid / total_liability * 100
            )
        else:
            coverage = 100

        print(
            f"Supplier Coverage        : "
            f"{coverage:.2f}%"
        )

        print(
            f"Supplier Accounts        : "
            f"{len(positions)}"
        )

        print("\n" + "=" * 60)
        print("SUPPLIER PAYMENT PRIORITY")
        print("=" * 60)

        if not positions:
            print(
                "No outstanding supplier liabilities "
                "were found."
            )

        for index, position in enumerate(
            positions,
            1,
        ):
            print("-" * 40)

            print(
                f"Priority Rank      : {index}"
            )

            print(
                f"Supplier            : "
                f"{position.supplier}"
            )

            print(
                f"Outstanding Liability: "
                f"{money(position.liability)}"
            )

            print(
                f"Priority            : "
                f"{position.priority}"
            )

            print(
                f"Risk Score          : "
                f"{position.risk_score:.2f}/100"
            )

            print(
                f"Liability Concentration: "
                f"{position.concentration:.2f}%"
            )

            print(
                f"Recommended Action  : "
                f"{position.recommendation}"
            )

            print(
                f"Reason              : "
                f"{position.reason}"
            )

        print("\n" + "=" * 60)
        print("PAYMENT RISK SUMMARY")
        print("=" * 60)

        urgent = sum(
            p.priority == "URGENT"
            for p in positions
        )

        high = sum(
            p.priority == "HIGH"
            for p in positions
        )

        medium = sum(
            p.priority == "MEDIUM"
            for p in positions
        )

        monitor = sum(
            p.priority == "MONITOR"
            for p in positions
        )

        print(f"Urgent Accounts  : {urgent}")
        print(f"High Accounts    : {high}")
        print(f"Medium Accounts  : {medium}")
        print(f"Monitor Accounts : {monitor}")

        print("\n" + "=" * 60)
        print("LIQUIDITY & PAYMENT OPPORTUNITY")
        print("=" * 60)

        print(
            f"Liquid Funds             : "
            f"{money(liquid)}"
        )

        print(
            f"Supplier Liability       : "
            f"{money(total_liability)}"
        )

        print(
            f"Liquidity Payment Gap    : "
            f"{money(payment_gap)}"
        )

        if payment_gap > 0:
            print(
                "Management Signal       : "
                "Supplier obligations exceed available "
                "liquid funds."
            )
        else:
            print(
                "Management Signal       : "
                "Current liquid funds can cover supplier "
                "obligations."
            )

        print("\n" + "=" * 60)
        print("TOP PAYMENT ACTION")
        print("=" * 60)

        if positions:
            top = positions[0]

            print(
                f"Supplier            : "
                f"{top.supplier}"
            )

            print(
                f"Outstanding Liability: "
                f"{money(top.liability)}"
            )

            print(
                f"Priority            : "
                f"{top.priority}"
            )

            print(
                f"Action              : "
                f"{top.recommendation}"
            )

        else:
            print(
                "No supplier payment action required."
            )

        print("\n" + "=" * 60)
        print("MANAGEMENT INTERPRETATION")
        print("=" * 60)

        if total_liability <= 0:
            print(
                "No outstanding supplier liability "
                "was detected."
            )

        elif payment_gap > 0:
            print(
                "Supplier obligations currently exceed "
                "available liquid funds."
            )
            print(
                "Management should protect liquidity and "
                "avoid unnecessary cash withdrawals."
            )
            print(
                "Payments should be prioritized according "
                "to supplier concentration and cash availability."
            )

        else:
            print(
                "Current liquid funds are sufficient to "
                "cover recorded supplier obligations."
            )
            print(
                "Management should still monitor payment "
                "timing and preserve operating liquidity."
            )

        print("\n" + "=" * 60)
        print("V66 SAFETY STATUS")
        print("=" * 60)

        print("Mode                : READ-ONLY")
        print("Database modified   : NO")
        print("Sales modified      : NO")
        print("Products modified   : NO")
        print("Inventory modified  : NO")
        print("Balance modified    : NO")
        print("Credit modified     : NO")
        print("Suppliers modified  : NO")
        print("Expenses modified   : NO")

        print("=" * 60)

    finally:
        conn.close()


def main():
    try:
        print_report()

    except Exception as exc:
        print("=" * 60)
        print("V66 ERROR")
        print("=" * 60)
        print(str(exc))


if __name__ == "__main__":
    main()
