"""
POS Ledger NG
V41 Financial Reconciliation Intelligence

READ-ONLY MODULE

This module analyzes financial consistency without modifying:
- sales
- transactions
- balances
- customers
- customer credit
- creditors
- inventory
- expenses
"""

from datetime import datetime

from database.connection import get_connection


def financial_reconciliation_v41():
    """
    V41 Financial Reconciliation & Data Consistency Intelligence.

    READ-ONLY.
    """

    conn = get_connection()

    try:
        cur = conn.cursor()

        # ====================================================
        # SALES DATA
        # ====================================================

        sales = cur.execute(
            """
            SELECT
                COUNT(*) AS sales_count,
                COALESCE(SUM(total_amount), 0) AS revenue,
                COALESCE(SUM(total_profit), 0) AS profit,
                MAX(sale_date) AS latest_sale_date
            FROM sales
            WHERE status != 'CANCELLED'
            """
        ).fetchone()

        sales_count = int(
            sales["sales_count"] or 0
        )

        revenue = float(
            sales["revenue"] or 0
        )

        profit = float(
            sales["profit"] or 0
        )

        latest_sale_date = sales["latest_sale_date"]

        # ====================================================
        # BALANCE DATA
        # ====================================================

        balance = cur.execute(
            """
            SELECT
                cash_balance,
                wallet_balance,
                opening_balance,
                updated_at
            FROM balance
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()

        if balance:
            cash_balance = float(
                balance["cash_balance"] or 0
            )

            wallet_balance = float(
                balance["wallet_balance"] or 0
            )

            opening_balance = float(
                balance["opening_balance"] or 0
            )

            balance_updated = balance["updated_at"]

        else:
            cash_balance = 0.0
            wallet_balance = 0.0
            opening_balance = 0.0
            balance_updated = None

        liquid_funds = (
            cash_balance
            + wallet_balance
        )

        # ====================================================
        # CUSTOMER CREDIT
        # ====================================================

        credit = cur.execute(
            """
            SELECT
                COALESCE(SUM(balance), 0)
                AS outstanding
            FROM customer_credit
            WHERE balance > 0
            """
        ).fetchone()

        customer_credit = float(
            credit["outstanding"] or 0
        )

        # ====================================================
        # SUPPLIER LIABILITY
        # ====================================================

        supplier = cur.execute(
            """
            SELECT
                COALESCE(SUM(balance), 0)
                AS liability
            FROM creditors
            WHERE balance > 0
            """
        ).fetchone()

        supplier_liability = float(
            supplier["liability"] or 0
        )

        # ====================================================
        # INVENTORY CAPITAL
        # ====================================================

        inventory = cur.execute(
            """
            SELECT
                COALESCE(
                    SUM(
                        current_stock * buying_price
                    ),
                    0
                ) AS inventory_cost
            FROM products
            """
        ).fetchone()

        inventory_capital = float(
            inventory["inventory_cost"] or 0
        )

        # ====================================================
        # DATA FRESHNESS
        # ====================================================

        balance_age_days = None
        freshness_status = "UNKNOWN"

        if (
            balance_updated
            and latest_sale_date
        ):
            try:
                balance_dt = datetime.fromisoformat(
                    str(balance_updated)
                )

                sale_dt = datetime.fromisoformat(
                    str(latest_sale_date)
                )

                balance_age_days = (
                    sale_dt.date()
                    - balance_dt.date()
                ).days

                if balance_age_days <= 0:
                    freshness_status = "CURRENT"

                elif balance_age_days <= 1:
                    freshness_status = (
                        "SLIGHTLY STALE"
                    )

                elif balance_age_days <= 3:
                    freshness_status = "STALE"

                else:
                    freshness_status = (
                        "VERY STALE"
                    )

            except (
                ValueError,
                TypeError
            ):
                freshness_status = (
                    "UNABLE TO DETERMINE"
                )

        # ====================================================
        # FINANCIAL POSITION
        # ====================================================

        total_assets = (
            liquid_funds
            + customer_credit
            + inventory_capital
        )

        net_position = (
            total_assets
            - supplier_liability
        )

        # ====================================================
        # RECONCILIATION RISK
        # ====================================================

        reconciliation_risk = 0
        warnings = []

        # Balance freshness
        if freshness_status in (
            "STALE",
            "VERY STALE"
        ):
            reconciliation_risk += 1

            warnings.append(
                "BALANCE DATA IS OLDER THAN "
                "SALES DATA"
            )

        # Supplier liability
        if supplier_liability > liquid_funds:
            reconciliation_risk += 1

            warnings.append(
                "SUPPLIER LIABILITY EXCEEDS "
                "LIQUID FUNDS"
            )

        # Customer credit
        if customer_credit > liquid_funds:
            reconciliation_risk += 1

            warnings.append(
                "CUSTOMER CREDIT EXCEEDS "
                "LIQUID FUNDS"
            )

        # ====================================================
        # STATUS CLASSIFICATION
        # ====================================================

        if reconciliation_risk == 0:
            reconciliation_status = (
                "CONSISTENT"
            )

        elif reconciliation_risk <= 2:
            reconciliation_status = (
                "REVIEW REQUIRED"
            )

        else:
            reconciliation_status = (
                "RECONCILIATION RISK"
            )

        # ====================================================
        # OUTPUT
        # ====================================================

        print()
        print("========================================")
        print("       POS LEDGER NG V41")
        print(" FINANCIAL RECONCILIATION INTELLIGENCE")
        print("========================================")

        # ----------------------------------------------------
        # DATA FRESHNESS
        # ----------------------------------------------------

        print()
        print("DATA FRESHNESS")
        print("----------------------------------------")

        print(
            f"Latest Sale Date     : "
            f"{latest_sale_date}"
        )

        print(
            f"Balance Updated      : "
            f"{balance_updated}"
        )

        if balance_age_days is not None:
            print(
                f"Balance Age          : "
                f"{balance_age_days} day(s)"
            )

        print(
            f"Freshness Status     : "
            f"{freshness_status}"
        )

        # ----------------------------------------------------
        # SALES RECONCILIATION
        # ----------------------------------------------------

        print()
        print("SALES RECONCILIATION")
        print("----------------------------------------")

        print(
            f"Completed Sales      : "
            f"{sales_count}"
        )

        print(
            f"Sales Revenue        : "
            f"₦{revenue:,.2f}"
        )

        print(
            f"Sales Profit         : "
            f"₦{profit:,.2f}"
        )

        # ----------------------------------------------------
        # LIQUID FUNDS
        # ----------------------------------------------------

        print()
        print("LIQUID FUNDS")
        print("----------------------------------------")

        print(
            f"Opening Balance      : "
            f"₦{opening_balance:,.2f}"
        )

        print(
            f"Cash Balance         : "
            f"₦{cash_balance:,.2f}"
        )

        print(
            f"Wallet Balance       : "
            f"₦{wallet_balance:,.2f}"
        )

        print(
            f"Liquid Funds         : "
            f"₦{liquid_funds:,.2f}"
        )

        # ----------------------------------------------------
        # FINANCIAL EXPOSURE
        # ----------------------------------------------------

        print()
        print("FINANCIAL EXPOSURE")
        print("----------------------------------------")

        print(
            f"Customer Credit      : "
            f"₦{customer_credit:,.2f}"
        )

        print(
            f"Supplier Liability   : "
            f"₦{supplier_liability:,.2f}"
        )

        print(
            f"Inventory Capital    : "
            f"₦{inventory_capital:,.2f}"
        )

        # ----------------------------------------------------
        # FINANCIAL POSITION
        # ----------------------------------------------------

        print()
        print("FINANCIAL POSITION")
        print("----------------------------------------")

        print(
            f"Total Assets         : "
            f"₦{total_assets:,.2f}"
        )

        print(
            f"Net Position         : "
            f"₦{net_position:,.2f}"
        )

        # ----------------------------------------------------
        # RECONCILIATION RISK
        # ----------------------------------------------------

        print()
        print("RECONCILIATION RISK")
        print("----------------------------------------")

        print(
            f"Risk Indicators      : "
            f"{reconciliation_risk}"
        )

        print(
            f"Status               : "
            f"{reconciliation_status}"
        )

        # ----------------------------------------------------
        # WARNINGS
        # ----------------------------------------------------

        if warnings:
            print()
            print("RECONCILIATION WARNINGS")
            print("----------------------------------------")

            for index, warning in enumerate(
                warnings,
                start=1
            ):
                print(
                    f"{index}. {warning}"
                )

        # ----------------------------------------------------
        # MODULE STATUS
        # ----------------------------------------------------

        print()
        print("========================================")
        print("       V41 MODULE STATUS")
        print("========================================")

        print(
            "Mode                : READ-ONLY"
        )

        print(
            "Database modified   : NO"
        )

        print(
            "Sales modified      : NO"
        )

        print(
            "Balance modified    : NO"
        )

        print(
            "Credit modified     : NO"
        )

        print(
            "Inventory modified  : NO"
        )

        print(
            "========================================"
        )

    finally:
        conn.close()


if __name__ == "__main__":
    financial_reconciliation_v41()
