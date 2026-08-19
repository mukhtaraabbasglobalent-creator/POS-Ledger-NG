"""
POS LEDGER NG V82
VERIFIED PROFITABILITY INTELLIGENCE

Purpose:
- Uses verified historical cost snapshots from sales
- Calculates verified revenue, COGS, gross profit and margin
- Ranks product profitability
- Identifies products below the management margin target
- READ-ONLY analytics
- Does not modify business transactions
"""

import sqlite3
from pathlib import Path

DB_PATH = Path("data/posledger.db")
TARGET_MARGIN = 10.0


def money(value):
    return f"₦{value:,.2f}"


def pct(value):
    return f"{value:.2f}%"


def get_connection():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")
    return sqlite3.connect(DB_PATH)


def main():
    print("=" * 60)
    print("POS LEDGER NG V82")
    print("VERIFIED PROFITABILITY INTELLIGENCE")
    print("=" * 60)

    conn = get_connection()
    conn.row_factory = sqlite3.Row

    try:
        cur = conn.cursor()

        # --------------------------------------------------
        # VERIFY REQUIRED SALES FIELDS
        # --------------------------------------------------
        sales_columns = {
            row["name"]
            for row in cur.execute("PRAGMA table_info(sales)").fetchall()
        }

        required = {
            "product_id",
            "quantity",
            "total_amount",
            "cost_snapshot",
            "cogs",
            "gross_profit",
            "gross_margin",
        }

        missing = required - sales_columns

        if missing:
            print()
            print("❌ REQUIRED V81 FIELDS MISSING")
            for field in sorted(missing):
                print(f"   - {field}")
            return

        # --------------------------------------------------
        # VERIFIED SALES
        # --------------------------------------------------
        rows = cur.execute(
            """
            SELECT
                s.id,
                s.product_id,
                s.quantity,
                s.total_amount,
                s.cost_snapshot,
                s.cogs,
                s.gross_profit,
                s.gross_margin,
                s.sale_date,
                p.product_name,
                p.sku
            FROM sales s
            LEFT JOIN products p
                ON p.id = s.product_id
            WHERE
                s.status = 'COMPLETED'
                AND s.cost_snapshot IS NOT NULL
                AND s.cogs IS NOT NULL
                AND s.gross_profit IS NOT NULL
            ORDER BY s.id
            """
        ).fetchall()

        print()
        print("=" * 60)
        print("VERIFIED FINANCIAL POSITION")
        print("=" * 60)

        total_revenue = sum(float(r["total_amount"] or 0) for r in rows)
        total_cogs = sum(float(r["cogs"] or 0) for r in rows)
        total_profit = sum(float(r["gross_profit"] or 0) for r in rows)
        total_units = sum(float(r["quantity"] or 0) for r in rows)

        overall_margin = (
            total_profit / total_revenue * 100
            if total_revenue
            else 0
        )

        print(f"Verified Sales       : {len(rows)}")
        print(f"Units Sold           : {total_units:,.2f}")
        print(f"Verified Revenue     : {money(total_revenue)}")
        print(f"Verified COGS        : {money(total_cogs)}")
        print(f"Verified Gross Profit: {money(total_profit)}")
        print(f"Verified Gross Margin: {pct(overall_margin)}")

        # --------------------------------------------------
        # PRODUCT PROFITABILITY
        # --------------------------------------------------
        product_data = {}

        for r in rows:
            pid = r["product_id"]

            if pid not in product_data:
                product_data[pid] = {
                    "name": r["product_name"] or "Unknown Product",
                    "sku": r["sku"] or "N/A",
                    "units": 0.0,
                    "revenue": 0.0,
                    "cogs": 0.0,
                    "profit": 0.0,
                    "sales": 0,
                }

            d = product_data[pid]

            d["units"] += float(r["quantity"] or 0)
            d["revenue"] += float(r["total_amount"] or 0)
            d["cogs"] += float(r["cogs"] or 0)
            d["profit"] += float(r["gross_profit"] or 0)
            d["sales"] += 1

        products = list(product_data.values())

        for d in products:
            d["margin"] = (
                d["profit"] / d["revenue"] * 100
                if d["revenue"]
                else 0
            )

        # --------------------------------------------------
        # PRODUCT PROFITABILITY TABLE
        # --------------------------------------------------
        print()
        print("=" * 60)
        print("PRODUCT PROFITABILITY")
        print("=" * 60)

        ranked = sorted(
            products,
            key=lambda x: x["profit"],
            reverse=True
        )

        for i, d in enumerate(ranked, 1):
            status = (
                "🟢 ABOVE TARGET"
                if d["margin"] >= TARGET_MARGIN
                else "🟠 BELOW TARGET"
            )

            print("-" * 40)
            print(f"{i}. {d['name']}")
            print(f"SKU                 : {d['sku']}")
            print(f"Sales               : {d['sales']}")
            print(f"Units               : {d['units']:,.2f}")
            print(f"Revenue             : {money(d['revenue'])}")
            print(f"COGS                : {money(d['cogs'])}")
            print(f"Gross Profit        : {money(d['profit'])}")
            print(f"Gross Margin        : {pct(d['margin'])}")
            print(f"Target Margin       : {pct(TARGET_MARGIN)}")
            print(f"Status              : {status}")

        # --------------------------------------------------
        # BEST / WORST PRODUCTS
        # --------------------------------------------------
        print()
        print("=" * 60)
        print("PROFITABILITY RANKING")
        print("=" * 60)

        if ranked:
            best = max(products, key=lambda x: x["profit"])
            highest_margin = max(products, key=lambda x: x["margin"])
            lowest_margin = min(products, key=lambda x: x["margin"])

            print(f"Highest Profit Product : {best['name']}")
            print(f"Profit                 : {money(best['profit'])}")

            print()
            print(f"Highest Margin Product : {highest_margin['name']}")
            print(f"Margin                 : {pct(highest_margin['margin'])}")

            print()
            print(f"Lowest Margin Product  : {lowest_margin['name']}")
            print(f"Margin                 : {pct(lowest_margin['margin'])}")

        # --------------------------------------------------
        # BELOW TARGET PRODUCTS
        # --------------------------------------------------
        below_target = [
            d for d in products
            if d["margin"] < TARGET_MARGIN
        ]

        print()
        print("=" * 60)
        print("MARGIN TARGET ANALYSIS")
        print("=" * 60)

        print(f"Management Target     : {pct(TARGET_MARGIN)}")
        print(f"Products Analyzed     : {len(products)}")
        print(f"Below Target          : {len(below_target)}")
        print(f"At/Above Target       : {len(products) - len(below_target)}")

        if below_target:
            print()
            print("PRODUCTS REQUIRING REVIEW")

            for d in sorted(
                below_target,
                key=lambda x: x["margin"]
            ):
                gap = TARGET_MARGIN - d["margin"]

                print("-" * 40)
                print(f"Product              : {d['name']}")
                print(f"Current Margin       : {pct(d['margin'])}")
                print(f"Target Margin        : {pct(TARGET_MARGIN)}")
                print(f"Margin Gap           : {pct(gap)}")
                print(f"Gross Profit         : {money(d['profit'])}")

        # --------------------------------------------------
        # REVENUE CONTRIBUTION
        # --------------------------------------------------
        print()
        print("=" * 60)
        print("REVENUE & PROFIT CONTRIBUTION")
        print("=" * 60)

        for d in ranked:
            revenue_share = (
                d["revenue"] / total_revenue * 100
                if total_revenue
                else 0
            )

            profit_share = (
                d["profit"] / total_profit * 100
                if total_profit
                else 0
            )

            print("-" * 40)
            print(f"Product              : {d['name']}")
            print(f"Revenue Share        : {pct(revenue_share)}")
            print(f"Profit Share         : {pct(profit_share)}")

        # --------------------------------------------------
        # MANAGEMENT SIGNAL
        # --------------------------------------------------
        print()
        print("=" * 60)
        print("V82 MANAGEMENT SIGNAL")
        print("=" * 60)

        if overall_margin >= TARGET_MARGIN:
            print("🟢 PROFITABILITY TARGET ACHIEVED")
        else:
            gap = TARGET_MARGIN - overall_margin
            print("🟠 PROFITABILITY BELOW TARGET")
            print(f"Overall Margin Gap   : {pct(gap)}")

        if below_target:
            print("⚠️ PRODUCT MARGIN REVIEW REQUIRED")
        else:
            print("🟢 ALL PRODUCTS MEET TARGET")

        # --------------------------------------------------
        # FINANCIAL TRUTH
        # --------------------------------------------------
        print()
        print("=" * 60)
        print("V82 FINANCIAL TRUTH STATUS")
        print("=" * 60)

        if rows and len(rows) == len(
            cur.execute(
                """
                SELECT id
                FROM sales
                WHERE status = 'COMPLETED'
                """
            ).fetchall()
        ):
            print("Status : 🟢 VERIFIED PROFITABILITY")
            print("All completed sales have verified V81 profitability data.")
        else:
            print("Status : 🟡 PARTIALLY VERIFIED")
            print("Some completed sales do not yet have verified profitability data.")

        # --------------------------------------------------
        # INTERPRETATION
        # --------------------------------------------------
        print()
        print("=" * 60)
        print("V82 MANAGEMENT INTERPRETATION")
        print("=" * 60)

        print(
            "V82 uses the historical profitability values created by V81 "
            "instead of today's product buying prices."
        )

        print(
            f"Verified gross profit is {money(total_profit)} "
            f"from {money(total_revenue)} verified revenue."
        )

        print(
            f"Verified gross margin is {pct(overall_margin)}."
        )

        if below_target:
            print(
                f"{len(below_target)} product(s) are below the "
                f"{pct(TARGET_MARGIN)} management margin target."
            )

        print(
            "Management should review low-margin products before "
            "using aggressive growth assumptions."
        )

        # --------------------------------------------------
        # SAFETY
        # --------------------------------------------------
        print()
        print("=" * 60)
        print("V82 SAFETY STATUS")
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

    finally:
        conn.close()


if __name__ == "__main__":
    main()
