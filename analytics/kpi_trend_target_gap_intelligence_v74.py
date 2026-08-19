"""
POS LEDGER NG V74
KPI TREND & TARGET-GAP INTELLIGENCE

READ-ONLY management intelligence.
Does not modify the database.
"""

VERSION = "V74"

# ============================================================
# VERIFIED BUSINESS POSITION FROM V73
# ============================================================

REVENUE = 21650.00
GROSS_PROFIT = 1432.17
LIQUID_FUNDS = 5800.00
CUSTOMER_CREDIT = 4750.00
SUPPLIER_LIABILITY = 9000.00
INVENTORY_CAPITAL = 20764.26
RECORDED_SALES = 14

# ============================================================
# MANAGEMENT TARGETS
# ============================================================

TARGET_MARGIN = 10.00
TARGET_LIQUIDITY_COVERAGE = 100.00
TARGET_CREDIT_EXPOSURE = 20.00
TARGET_SUPPLIER_GAP = 0.00
TARGET_SALES_DATA = 20


def money(value):
    return f"₦{value:,.2f}"


def pct(value):
    return f"{value:.2f}%"


def risk_label(score):
    if score >= 80:
        return "🟢 STRONG"
    elif score >= 60:
        return "🟡 WATCH"
    elif score >= 40:
        return "🟠 AT RISK"
    return "🔴 CRITICAL"


def main():

    # ========================================================
    # CURRENT METRICS
    # ========================================================

    margin = (
        GROSS_PROFIT / REVENUE * 100
        if REVENUE > 0 else 0
    )

    liquidity_coverage = (
        LIQUID_FUNDS / SUPPLIER_LIABILITY * 100
        if SUPPLIER_LIABILITY > 0 else 100
    )

    credit_exposure = (
        CUSTOMER_CREDIT / REVENUE * 100
        if REVENUE > 0 else 0
    )

    supplier_gap = max(
        SUPPLIER_LIABILITY - LIQUID_FUNDS,
        0
    )

    inventory_ratio = (
        INVENTORY_CAPITAL / REVENUE * 100
        if REVENUE > 0 else 0
    )

    # ========================================================
    # TARGET GAPS
    # ========================================================

    margin_gap = max(
        TARGET_MARGIN - margin,
        0
    )

    liquidity_gap = max(
        TARGET_LIQUIDITY_COVERAGE - liquidity_coverage,
        0
    )

    credit_gap = max(
        credit_exposure - TARGET_CREDIT_EXPOSURE,
        0
    )

    sales_data_gap = max(
        TARGET_SALES_DATA - RECORDED_SALES,
        0
    )

    # ========================================================
    # KPI SCORES
    # ========================================================

    margin_score = min(
        margin / TARGET_MARGIN * 100,
        100
    )

    liquidity_score = min(
        liquidity_coverage,
        100
    )

    # Graduated credit scoring.
    # 20% exposure or below = 100.
    # Higher exposure reduces score gradually.
    if credit_exposure <= TARGET_CREDIT_EXPOSURE:
        credit_score = 100.0
    else:
        excess = credit_exposure - TARGET_CREDIT_EXPOSURE
        credit_score = max(
            0,
            100 - (excess * 5)
        )

    supplier_score = liquidity_score

    if inventory_ratio <= 100:
        inventory_score = 80.0
    elif inventory_ratio <= 150:
        inventory_score = 60.0
    else:
        inventory_score = 40.0

    sales_score = min(
        RECORDED_SALES / TARGET_SALES_DATA * 100,
        100
    )

    overall_score = (
        margin_score * 0.25
        + liquidity_score * 0.20
        + credit_score * 0.15
        + supplier_score * 0.15
        + inventory_score * 0.15
        + sales_score * 0.10
    )

    # ========================================================
    # MANAGEMENT PRIORITY
    # ========================================================

    priorities = []

    if supplier_gap > 0:
        priorities.append(
            (
                1,
                "PROTECT LIQUIDITY",
                supplier_gap,
                "Supplier obligations exceed available liquid funds."
            )
        )

    if margin_gap > 0:
        priorities.append(
            (
                2,
                "IMPROVE GROSS MARGIN",
                margin_gap,
                "Gross margin remains below the 10% target."
            )
        )

    if CUSTOMER_CREDIT > 0:
        priorities.append(
            (
                3,
                "COLLECT CUSTOMER CREDIT",
                CUSTOMER_CREDIT,
                "Customer credit represents recoverable liquidity."
            )
        )

    if inventory_ratio > 80:
        priorities.append(
            (
                4,
                "CONTROL INVENTORY CAPITAL",
                INVENTORY_CAPITAL,
                "Significant capital is tied up in inventory."
            )
        )

    if sales_data_gap > 0:
        priorities.append(
            (
                5,
                "STRENGTHEN SALES DATA",
                sales_data_gap,
                "More recorded sales are required for stronger intelligence."
            )
        )

    # ========================================================
    # REPORT
    # ========================================================

    print("=" * 60)
    print(f"POS LEDGER NG {VERSION}")
    print("KPI TREND & TARGET-GAP INTELLIGENCE")
    print("=" * 60)

    print()
    print("=" * 60)
    print("CURRENT BUSINESS POSITION")
    print("=" * 60)

    print(f"Revenue              : {money(REVENUE)}")
    print(f"Gross Profit         : {money(GROSS_PROFIT)}")
    print(f"Gross Margin         : {pct(margin)}")
    print(f"Liquid Funds         : {money(LIQUID_FUNDS)}")
    print(f"Customer Credit      : {money(CUSTOMER_CREDIT)}")
    print(f"Supplier Liability   : {money(SUPPLIER_LIABILITY)}")
    print(f"Supplier Gap         : {money(supplier_gap)}")
    print(f"Inventory Capital    : {money(INVENTORY_CAPITAL)}")
    print(f"Recorded Sales       : {RECORDED_SALES}")

    print()
    print("=" * 60)
    print("KPI TARGET-GAP ANALYSIS")
    print("=" * 60)

    print("-" * 40)
    print("1. GROSS MARGIN")
    print(f"Current              : {pct(margin)}")
    print(f"Target               : {pct(TARGET_MARGIN)}")
    print(f"Gap                  : {pct(margin_gap)}")
    print(f"KPI Score            : {margin_score:.2f}/100")
    print(f"Status               : {risk_label(margin_score)}")

    print("-" * 40)
    print("2. LIQUIDITY COVERAGE")
    print(f"Current Coverage     : {pct(liquidity_coverage)}")
    print(f"Target Coverage      : {pct(TARGET_LIQUIDITY_COVERAGE)}")
    print(f"Gap                  : {pct(liquidity_gap)}")
    print(f"Supplier Gap         : {money(supplier_gap)}")
    print(f"KPI Score            : {liquidity_score:.2f}/100")
    print(f"Status               : {risk_label(liquidity_score)}")

    print("-" * 40)
    print("3. CUSTOMER CREDIT")
    print(f"Outstanding Credit   : {money(CUSTOMER_CREDIT)}")
    print(f"Current Exposure     : {pct(credit_exposure)}")
    print(f"Target Exposure      : {pct(TARGET_CREDIT_EXPOSURE)}")
    print(f"Exposure Gap         : {pct(credit_gap)}")
    print(f"KPI Score            : {credit_score:.2f}/100")

    if credit_gap > 0:
        print("Status               : 🟠 ABOVE TARGET")
    else:
        print("Status               : 🟢 WITHIN TARGET")

    print("-" * 40)
    print("4. SUPPLIER PRESSURE")
    print(f"Liability            : {money(SUPPLIER_LIABILITY)}")
    print(f"Liquid Funds         : {money(LIQUID_FUNDS)}")
    print(f"Current Gap          : {money(supplier_gap)}")
    print(f"Target Gap           : {money(TARGET_SUPPLIER_GAP)}")
    print(f"KPI Score            : {supplier_score:.2f}/100")

    if supplier_gap > 0:
        print("Status               : 🔴 GAP REMAINS")
    else:
        print("Status               : 🟢 TARGET MET")

    print("-" * 40)
    print("5. INVENTORY CAPITAL")
    print(f"Inventory Capital    : {money(INVENTORY_CAPITAL)}")
    print(f"Inventory/Revenue    : {pct(inventory_ratio)}")
    print(f"KPI Score            : {inventory_score:.2f}/100")
    print(f"Status               : {risk_label(inventory_score)}")

    print("-" * 40)
    print("6. SALES DATA")
    print(f"Recorded Sales       : {RECORDED_SALES}")
    print(f"Reference Target     : {TARGET_SALES_DATA}")
    print(f"Data Gap             : {sales_data_gap}")
    print(f"KPI Score            : {sales_score:.2f}/100")

    if sales_data_gap > 0:
        print("Status               : 🟡 BUILD MORE DATA")
    else:
        print("Status               : 🟢 SUFFICIENT")

    print()
    print("=" * 60)
    print("OVERALL KPI POSITION")
    print("=" * 60)

    print(f"Overall KPI Score    : {overall_score:.2f}/100")
    print(f"KPI Health Status    : {risk_label(overall_score)}")

    print()
    print("=" * 60)
    print("MANAGEMENT PRIORITY")
    print("=" * 60)

    for number, action, value, reason in priorities:
        print("-" * 40)
        print(f"{number}. {action}")

        if action == "IMPROVE GROSS MARGIN":
            print(f"Target Gap           : {pct(value)}")
        elif action == "STRENGTHEN SALES DATA":
            print(f"Data Gap             : {value}")
        elif action == "CONTROL INVENTORY CAPITAL":
            print(f"Capital Tied Up      : {money(value)}")
        elif action == "COLLECT CUSTOMER CREDIT":
            print(f"Recoverable Liquidity: {money(value)}")
        else:
            print(f"Financial Gap        : {money(value)}")

        print(f"Reason               : {reason}")

    print()
    print("=" * 60)
    print("TOP MANAGEMENT DECISION")
    print("=" * 60)

    if supplier_gap > 0:
        print("Priority             : URGENT")
        print("Decision             : PROTECT LIQUIDITY")
        print(f"Required Gap         : {money(supplier_gap)}")
    elif margin_gap > 0:
        print("Priority             : HIGH")
        print("Decision             : IMPROVE GROSS MARGIN")
        print(f"Margin Gap           : {pct(margin_gap)}")
    elif CUSTOMER_CREDIT > 0:
        print("Priority             : HIGH")
        print("Decision             : COLLECT CUSTOMER CREDIT")
    else:
        print("Priority             : MONITOR")
        print("Decision             : MAINTAIN KPI PERFORMANCE")

    print()
    print("=" * 60)
    print("V74 MANAGEMENT INTERPRETATION")
    print("=" * 60)

    print(
        "V74 compares current business KPIs against management targets "
        "to identify measurable performance gaps."
    )

    if supplier_gap > 0:
        print(
            f"Liquidity remains the largest immediate pressure, "
            f"with a supplier gap of {money(supplier_gap)}."
        )

    if margin_gap > 0:
        print(
            f"Gross margin requires improvement by "
            f"{pct(margin_gap)} to reach the 10% target."
        )

    print(
        f"Customer credit of {money(CUSTOMER_CREDIT)} "
        "remains a potential liquidity recovery opportunity."
    )

    print(
        "Management should close the largest financial gaps "
        "before pursuing aggressive expansion."
    )

    print()
    print("=" * 60)
    print("V74 SAFETY STATUS")
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


if __name__ == "__main__":
    main()
