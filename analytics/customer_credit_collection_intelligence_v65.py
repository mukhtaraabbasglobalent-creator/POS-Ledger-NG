import sqlite3
from pathlib import Path
from dataclasses import dataclass


DB_PATH = Path("data/posledger.db")


@dataclass
class CreditAccount:
    customer: str
    balance: float
    priority: str = "MONITOR"
    risk_score: float = 0.0
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

    rows = conn.execute(
        f"PRAGMA table_info({table})"
    ).fetchall()

    return [row[1] for row in rows]


def find_column(columns, candidates):
    for candidate in candidates:
        if candidate in columns:
            return candidate

    return None


def load_credit_accounts(conn):
    table = "customer_credit"

    if not table_exists(conn, table):
        return []

    columns = get_columns(conn, table)

    customer_col = find_column(
        columns,
        [
            "customer_name",
            "customer",
            "name",
            "customer_id",
        ],
    )

    balance_col = find_column(
        columns,
        [
            "balance",
            "credit_balance",
            "amount",
            "outstanding",
            "amount_due",
        ],
    )

    if not balance_col:
        return []

    if customer_col:
        query = f"""
            SELECT
                COALESCE({customer_col}, 'UNKNOWN'),
                COALESCE({balance_col}, 0)
            FROM {table}
            WHERE COALESCE({balance_col}, 0) > 0
            ORDER BY {balance_col} DESC
        """
    else:
        query = f"""
            SELECT
                'UNKNOWN CUSTOMER',
                COALESCE({balance_col}, 0)
            FROM {table}
            WHERE COALESCE({balance_col}, 0) > 0
            ORDER BY {balance_col} DESC
        """

    try:
        rows = conn.execute(query).fetchall()
    except sqlite3.Error:
        return []

    accounts = []

    for customer, balance in rows:
        try:
            balance = float(balance or 0)
        except (TypeError, ValueError):
            continue

        if balance <= 0:
            continue

        accounts.append(
            CreditAccount(
                str(customer),
                balance,
            )
        )

    return accounts


def classify_account(account, total_credit):
    balance = account.balance

    if balance >= 50000:
        priority = "CRITICAL"
        risk = 90
        reason = "Very large outstanding customer balance."

    elif balance >= 20000:
        priority = "URGENT"
        risk = 75
        reason = "Large outstanding customer balance."

    elif balance >= 10000:
        priority = "HIGH"
        risk = 60
        reason = "Significant outstanding customer balance."

    elif balance >= 5000:
        priority = "MEDIUM"
        risk = 45
        reason = "Moderate outstanding customer balance."

    else:
        priority = "MONITOR"
        risk = 25
        reason = "Smaller outstanding customer balance."

    if total_credit > 0:
        concentration = balance / total_credit

        if concentration >= 0.50:
            risk = min(risk + 10, 100)
            reason += " High concentration of total credit."

    account.priority = priority
    account.risk_score = float(risk)
    account.reason = reason


def collection_action(priority):
    actions = {
        "CRITICAL":
            "Immediate collection contact and payment plan.",
        "URGENT":
            "Prioritize collection and confirm payment date.",
        "HIGH":
            "Contact customer and request settlement.",
        "MEDIUM":
            "Follow up and schedule collection.",
        "MONITOR":
            "Continue monitoring outstanding balance.",
    }

    return actions.get(
        priority,
        "Monitor account.",
    )


def calculate_recovery(accounts):
    return sum(account.balance for account in accounts)


def print_report(accounts):
    total_credit = calculate_recovery(accounts)

    for account in accounts:
        classify_account(account, total_credit)

    ranked = sorted(
        accounts,
        key=lambda x: (
            x.risk_score,
            x.balance,
        ),
        reverse=True,
    )

    critical = sum(
        1 for x in ranked
        if x.priority == "CRITICAL"
    )

    urgent = sum(
        1 for x in ranked
        if x.priority == "URGENT"
    )

    high = sum(
        1 for x in ranked
        if x.priority == "HIGH"
    )

    medium = sum(
        1 for x in ranked
        if x.priority == "MEDIUM"
    )

    monitor = sum(
        1 for x in ranked
        if x.priority == "MONITOR"
    )

    print("=" * 60)
    print("POS LEDGER NG V65")
    print("CUSTOMER CREDIT & COLLECTION INTELLIGENCE")
    print("=" * 60)

    print("\n" + "=" * 60)
    print("CREDIT POSITION")
    print("=" * 60)

    print(
        f"Outstanding Customer Credit : "
        f"{money(total_credit)}"
    )

    print(
        f"Credit Accounts             : "
        f"{len(ranked)}"
    )

    print(
        f"Potential Liquidity Recovery: "
        f"{money(total_credit)}"
    )

    print("\n" + "=" * 60)
    print("COLLECTION PRIORITY ANALYSIS")
    print("=" * 60)

    if not ranked:
        print(
            "No outstanding customer credit "
            "accounts were found."
        )

    for i, account in enumerate(ranked, 1):
        print("-" * 40)

        print(
            f"Priority Rank      : {i}"
        )

        print(
            f"Customer           : "
            f"{account.customer}"
        )

        print(
            f"Outstanding Credit : "
            f"{money(account.balance)}"
        )

        print(
            f"Priority           : "
            f"{account.priority}"
        )

        print(
            f"Risk Score         : "
            f"{account.risk_score:.2f}/100"
        )

        if total_credit > 0:
            concentration = (
                account.balance / total_credit
            ) * 100
        else:
            concentration = 0

        print(
            f"Credit Concentration: "
            f"{concentration:.2f}%"
        )

        print(
            f"Recommended Action : "
            f"{collection_action(account.priority)}"
        )

        print(
            f"Reason             : "
            f"{account.reason}"
        )

    print("\n" + "=" * 60)
    print("COLLECTION RISK SUMMARY")
    print("=" * 60)

    print(
        f"Critical Accounts : {critical}"
    )

    print(
        f"Urgent Accounts   : {urgent}"
    )

    print(
        f"High Accounts     : {high}"
    )

    print(
        f"Medium Accounts   : {medium}"
    )

    print(
        f"Monitor Accounts  : {monitor}"
    )

    print("\n" + "=" * 60)
    print("LIQUIDITY RECOVERY OPPORTUNITY")
    print("=" * 60)

    print(
        f"Recoverable Credit : "
        f"{money(total_credit)}"
    )

    if total_credit > 0:
        print(
            "Management Signal : "
            "Customer credit is tying up "
            "business liquidity."
        )
    else:
        print(
            "Management Signal : "
            "No outstanding customer credit."
        )

    print("\n" + "=" * 60)
    print("TOP COLLECTION ACTION")
    print("=" * 60)

    if ranked:
        top = ranked[0]

        print(
            f"Customer           : "
            f"{top.customer}"
        )

        print(
            f"Outstanding Credit : "
            f"{money(top.balance)}"
        )

        print(
            f"Priority            : "
            f"{top.priority}"
        )

        print(
            f"Action              : "
            f"{collection_action(top.priority)}"
        )
    else:
        print(
            "No collection action required."
        )

    print("\n" + "=" * 60)
    print("MANAGEMENT INTERPRETATION")
    print("=" * 60)

    if total_credit > 0:
        print(
            "Outstanding customer credit "
            "represents potential liquidity "
            "that can be recovered through "
            "effective collection."
        )

        if critical or urgent:
            print(
                "High-priority collection should "
                "be addressed before aggressive "
                "business expansion."
            )

        elif high:
            print(
                "Several customer balances require "
                "active follow-up."
            )

        else:
            print(
                "Credit exposure exists but is "
                "currently manageable."
            )
    else:
        print(
            "No outstanding customer credit "
            "exposure was detected."
        )

    print("\n" + "=" * 60)
    print("V65 SAFETY STATUS")
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


def main():
    try:
        conn = get_connection()

        try:
            accounts = load_credit_accounts(conn)
            print_report(accounts)

        finally:
            conn.close()

    except Exception as exc:
        print("=" * 60)
        print("V65 ERROR")
        print("=" * 60)
        print(str(exc))
        print("=" * 60)


if __name__ == "__main__":
    main()
