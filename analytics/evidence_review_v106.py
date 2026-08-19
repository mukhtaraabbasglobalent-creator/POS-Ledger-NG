import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(
    "/data/data/com.termux/files/home/POS-Ledger-NG/data/posledger.db"
)

VERIFIED_SALE_IDS = {15}


def header(title):
    print("=" * 60)
    print(f"POS LEDGER NG V106")
    print(title)
    print("=" * 60)


def table_exists(conn, table):
    row = conn.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None


def get_columns(conn, table):
    return {
        row[1]
        for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
    }


def get_manual_candidates(conn):
    rows = conn.execute(
        """
        SELECT
            s.id,
            s.product_id,
            p.product_name,
            s.quantity,
            s.sale_date,
            s.receipt_no,
            im.id AS movement_id,
            im.quantity AS movement_quantity,
            im.movement_date,
            im.reference AS movement_reference
        FROM sales s
        JOIN products p
          ON p.id = s.product_id
        LEFT JOIN inventory_movements im
          ON im.id = (
              SELECT im2.id
              FROM inventory_movements im2
              WHERE im2.product_id = s.product_id
                AND UPPER(TRIM(im2.movement_type)) = 'SALE'
                AND ABS(im2.quantity) = ABS(s.quantity)
              ORDER BY
                  ABS(
                      strftime('%s', im2.movement_date)
                      - strftime('%s', s.sale_date)
                  ) ASC,
                  im2.id ASC
              LIMIT 1
          )
        WHERE UPPER(COALESCE(s.status, 'COMPLETED')) = 'COMPLETED'
          AND s.id NOT IN ({})
        ORDER BY s.id
        """.format(",".join("?" for _ in VERIFIED_SALE_IDS)),
        tuple(VERIFIED_SALE_IDS),
    ).fetchall()

    candidates = []

    for row in rows:
        (
            sale_id,
            product_id,
            product_name,
            sale_qty,
            sale_date,
            receipt_no,
            movement_id,
            movement_qty,
            movement_date,
            movement_reference,
        ) = row

        # We only want candidates where a product + quantity
        # match exists, but the evidence is not strong enough
        # for automatic repair.
        if movement_id is None:
            continue

        if abs(float(movement_qty)) != abs(float(sale_qty)):
            continue

        sale_ref = (receipt_no or "").strip()
        movement_ref = (movement_reference or "").strip()

        # Strong exact reference matches are intentionally excluded.
        if sale_ref and movement_ref and sale_ref == movement_ref:
            continue

        candidates.append(
            {
                "sale_id": sale_id,
                "product_id": product_id,
                "product_name": product_name,
                "sale_quantity": float(sale_qty),
                "sale_date": sale_date,
                "receipt_no": sale_ref or None,
                "movement_id": movement_id,
                "movement_quantity": float(movement_qty),
                "movement_date": movement_date,
                "movement_reference": movement_ref or None,
            }
        )

    return candidates


def print_candidate(c):
    print("-" * 40)
    print(f"Sale ID             : {c['sale_id']}")
    print(f"Product ID          : {c['product_id']}")
    print(f"Product             : {c['product_name']}")
    print(f"Quantity            : {c['sale_quantity']:.2f}")
    print(f"Sale date           : {c['sale_date']}")
    print(f"Receipt/reference   : {c['receipt_no'] or 'NONE'}")
    print()
    print(f"Existing movement   : {c['movement_id']}")
    print(f"Movement quantity   : {c['movement_quantity']:.2f}")
    print(f"Movement date       : {c['movement_date']}")
    print(f"Movement reference  : {c['movement_reference'] or 'NONE'}")
    print()
    print("Evidence strength   : WEAK")
    print("V105 classification : MANUAL_REVIEW")
    print()
    print("V106 SAFETY WARNING")
    print("Product and quantity match, but the movement is")
    print("not linked by an exact transaction reference.")
    print("A CONFIRM decision will only authorize V107.")
    print("V106 itself will NOT modify the database.")


def ask_decision():
    while True:
        print()
        print("Type one of:")
        print("  CONFIRM  - authorize this candidate for V107 review")
        print("  REJECT   - reject this candidate")
        print("  DEFER    - leave unresolved for later")
        print()

        decision = input("V106 decision > ").strip().upper()

        if decision in {"CONFIRM", "REJECT", "DEFER"}:
            return decision

        print("Invalid decision. Use CONFIRM, REJECT, or DEFER.")


def main():
    header("HUMAN EVIDENCE REVIEW & REPAIR AUTHORIZATION")

    if not DB_PATH.exists():
        print()
        print("ERROR: Database not found.")
        print(DB_PATH)
        return 1

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)

    try:
        header("DATABASE")

        print(f"Database path : {DB_PATH}")
        print("Database mode : READ-ONLY")
        print()

        required = [
            "sales",
            "products",
            "inventory_movements",
        ]

        for table in required:
            status = "AVAILABLE" if table_exists(conn, table) else "MISSING"
            print(f"{table:<23}: {status}")

            if status != "AVAILABLE":
                print()
                print("ERROR: Required table is missing.")
                return 1

        sales_cols = get_columns(conn, "sales")
        product_cols = get_columns(conn, "products")
        movement_cols = get_columns(conn, "inventory_movements")

        required_sales = {
            "id",
            "product_id",
            "quantity",
            "sale_date",
            "receipt_no",
        }

        required_products = {
            "id",
            "product_name",
        }

        required_movements = {
            "id",
            "product_id",
            "movement_type",
            "quantity",
            "movement_date",
            "reference",
        }

        if not required_sales.issubset(sales_cols):
            print()
            print("ERROR: sales schema is incompatible.")
            print("Missing:", sorted(required_sales - sales_cols))
            return 1

        if not required_products.issubset(product_cols):
            print()
            print("ERROR: products schema is incompatible.")
            print("Missing:", sorted(required_products - product_cols))
            return 1

        if not required_movements.issubset(movement_cols):
            print()
            print("ERROR: inventory_movements schema is incompatible.")
            print("Missing:", sorted(required_movements - movement_cols))
            return 1

        candidates = get_manual_candidates(conn)

        header("V106 MANUAL REVIEW INPUT")

        print(f"Candidates requiring human review : {len(candidates)}")
        print()

        if not candidates:
            print("No manual-review candidates found.")
            print()
            print("V106 EXECUTIVE DECISION")
            print("🟢 NO CANDIDATES REQUIRE HUMAN REVIEW")
            print()
            print("V106 SAFETY STATUS")
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
            print("V106 COMPLETE")
            return 0

        authorized = []
        rejected = []
        deferred = []

        for candidate in candidates:
            header("V106 CANDIDATE FOR HUMAN REVIEW")

            print_candidate(candidate)

            decision = ask_decision()

            if decision == "CONFIRM":
                authorized.append(candidate)
            elif decision == "REJECT":
                rejected.append(candidate)
            else:
                deferred.append(candidate)

            print()
            print("V106 DECISION RESULT")
            print(f"Human decision      : {decision}")

            if decision == "CONFIRM":
                print("Candidate status    : AUTHORIZED_FOR_V107")
            elif decision == "REJECT":
                print("Candidate status    : REJECTED")
            else:
                print("Candidate status    : DEFERRED")

        header("V106 AUTHORIZATION SUMMARY")

        print(f"Candidates reviewed : {len(candidates)}")
        print(f"Authorized for V107 : {len(authorized)}")
        print(f"Rejected            : {len(rejected)}")
        print(f"Deferred            : {len(deferred)}")

        print()
        print("=" * 60)
        print("V106 AUTHORIZED CANDIDATES")
        print("=" * 60)

        if authorized:
            for c in authorized:
                print(
                    f"Sale {c['sale_id']} | "
                    f"Product {c['product_id']} | "
                    f"Qty {c['sale_quantity']:.2f} | "
                    f"Movement {c['movement_id']}"
                )
                print(
                    f"  Sale reference     : "
                    f"{c['receipt_no'] or 'NONE'}"
                )
                print(
                    f"  Movement reference : "
                    f"{c['movement_reference'] or 'NONE'}"
                )
                print("  Status             : AUTHORIZED_FOR_V107")
        else:
            print("None.")

        print()
        print("=" * 60)
        print("V106 IMPORTANT SAFETY CHECK")
        print("=" * 60)
        print("V106 is READ-ONLY.")
        print("No inventory movement was created.")
        print("No inventory movement was changed.")
        print("No sale was changed.")
        print("No purchase was changed.")
        print()
        print("A CONFIRM decision does NOT execute a repair.")
        print("It only permits a separate V107 controlled phase.")

        print()
        print("=" * 60)
        print("V106 EXECUTIVE DECISION")
        print("=" * 60)

        if authorized:
            print("🟡 HUMAN AUTHORIZATION RECORDED")
            print(
                f"{len(authorized)} candidate(s) may proceed "
                "to V107 controlled review."
            )
        elif deferred:
            print("🟡 REVIEW DEFERRED")
            print("No repair is authorized.")
        else:
            print("🔴 NO REPAIR AUTHORIZED")
            print("All reviewed candidates were rejected.")

        print()
        print("=" * 60)
        print("V106 SAFETY STATUS")
        print("=" * 60)
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
        print("=" * 60)
        print("V106 COMPLETE")
        print("=" * 60)

        return 0

    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
