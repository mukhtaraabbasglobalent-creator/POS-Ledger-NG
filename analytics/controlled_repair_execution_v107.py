import sqlite3
from pathlib import Path
from datetime import datetime


BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "data" / "posledger.db"


AUTHORIZED_CANDIDATES = []


def banner(title):
    print("=" * 60)
    print(title)
    print("=" * 60)


def table_exists(conn, table_name):
    row = conn.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return row is not None


def get_tables(conn):
    rows = conn.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' ORDER BY name"
    ).fetchall()
    return [row[0] for row in rows]


def connect_read_only():
    uri = f"file:{DB_PATH}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def validate_database(conn):
    required = [
        "sales",
        "products",
        "inventory_movements",
    ]

    tables = get_tables(conn)

    for table in required:
        status = "AVAILABLE" if table in tables else "MISSING"
        print(f"{table:<24}: {status}")

    missing = [table for table in required if table not in tables]

    if missing:
        raise RuntimeError(
            "Required database tables are missing: "
            + ", ".join(missing)
        )


def validate_authorization_list():
    if not isinstance(AUTHORIZED_CANDIDATES, list):
        raise RuntimeError(
            "Authorization structure is invalid."
        )

    for candidate in AUTHORIZED_CANDIDATES:
        if not isinstance(candidate, dict):
            raise RuntimeError(
                "Invalid authorization candidate."
            )

        required = {
            "sale_id",
            "movement_id",
            "reference",
        }

        missing = required - set(candidate)

        if missing:
            raise RuntimeError(
                "Authorization candidate missing: "
                + ", ".join(sorted(missing))
            )


def check_candidate(conn, candidate):
    sale_id = candidate["sale_id"]
    movement_id = candidate["movement_id"]
    reference = candidate["reference"]

    sale = conn.execute(
        """
        SELECT
            id,
            product_id,
            quantity,
            sale_date,
            receipt_no,
            status
        FROM sales
        WHERE id=?
        """,
        (sale_id,),
    ).fetchone()

    movement = conn.execute(
        """
        SELECT
            id,
            product_id,
            movement_type,
            quantity,
            reference,
            movement_date
        FROM inventory_movements
        WHERE id=?
        """,
        (movement_id,),
    ).fetchone()

    if sale is None:
        return False, "SALE_NOT_FOUND"

    if movement is None:
        return False, "MOVEMENT_NOT_FOUND"

    sale_id_db, product_id, sale_qty, sale_date, receipt_no, status = sale

    (
        movement_id_db,
        movement_product_id,
        movement_type,
        movement_qty,
        movement_reference,
        movement_date,
    ) = movement

    if sale_id_db != sale_id:
        return False, "SALE_ID_MISMATCH"

    if movement_id_db != movement_id:
        return False, "MOVEMENT_ID_MISMATCH"

    if product_id != movement_product_id:
        return False, "PRODUCT_MISMATCH"

    if float(sale_qty) != float(movement_qty):
        return False, "QUANTITY_MISMATCH"

    if movement_type != "SALE":
        return False, "MOVEMENT_TYPE_MISMATCH"

    if movement_reference != reference:
        return False, "REFERENCE_MISMATCH"

    if receipt_no not in (None, "", reference):
        return False, "SALE_REFERENCE_MISMATCH"

    return True, {
        "sale_id": sale_id,
        "movement_id": movement_id,
        "product_id": product_id,
        "quantity": float(sale_qty),
        "sale_date": sale_date,
        "movement_date": movement_date,
        "reference": reference,
        "status": status,
    }


def main():
    banner("POS LEDGER NG V107")
    print("CONTROLLED REPAIR EXECUTION GATE")
    banner("DATABASE")

    print(f"Database path : {DB_PATH}")
    print("Database mode : READ-ONLY")
    print()

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    conn = connect_read_only()

    try:
        banner("DATABASE TABLES")
        validate_database(conn)

        print()

        banner("V106 AUTHORIZATION")

        validate_authorization_list()

        print(
            f"Authorized candidates : "
            f"{len(AUTHORIZED_CANDIDATES)}"
        )

        if not AUTHORIZED_CANDIDATES:
            print()
            print("No candidates are authorized for V107.")
            print("V107 will perform ZERO database writes.")

        print()

        banner("V107 SAFETY GATE")

        if AUTHORIZED_CANDIDATES:
            for index, candidate in enumerate(
                AUTHORIZED_CANDIDATES,
                start=1,
            ):
                print("-" * 40)
                print(
                    f"Candidate {index}"
                )
                print(
                    f"Sale ID      : "
                    f"{candidate['sale_id']}"
                )
                print(
                    f"Movement ID  : "
                    f"{candidate['movement_id']}"
                )
                print(
                    f"Reference    : "
                    f"{candidate['reference']}"
                )

                valid, result = check_candidate(
                    conn,
                    candidate,
                )

                print(
                    "Authorization check : "
                    + ("PASS" if valid else "FAIL")
                )

                if not valid:
                    print(
                        f"Reason : {result}"
                    )
                    continue

                print(
                    "Candidate is eligible "
                    "for controlled execution."
                )

        else:
            print(
                "Authorization check : PASS"
            )
            print(
                "Execution candidates  : 0"
            )

        print()

        banner("V107 EXECUTION")

        print(
            "Database writes : 0"
        )
        print(
            "INSERT          : 0"
        )
        print(
            "UPDATE          : 0"
        )
        print(
            "DELETE          : 0"
        )

        print()
        print(
            "No repair executed."
        )
        print(
            "No sale modified."
        )
        print(
            "No inventory movement modified."
        )
        print(
            "No purchase modified."
        )
        print(
            "No product modified."
        )

        print()

        banner("V107 RESULT")

        if AUTHORIZED_CANDIDATES:
            print(
                "🟡 AUTHORIZED CANDIDATES DETECTED"
            )
            print(
                "A separate controlled execution "
                "phase is required."
            )
        else:
            print(
                "🟢 NO REPAIR AUTHORIZED"
            )
            print(
                "V107 correctly performed "
                "zero database writes."
            )

        print()

        banner("V107 SAFETY STATUS")

        print("Mode                  : READ-ONLY")
        print("Database modified     : NO")
        print("Sales modified        : NO")
        print("Inventory modified    : NO")
        print("Purchases modified    : NO")
        print("Products modified     : NO")
        print("Balance modified      : NO")
        print("Credit modified       : NO")
        print("Suppliers modified    : NO")
        print("Expenses modified     : NO")

        print()
        banner("V107 COMPLETE")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
