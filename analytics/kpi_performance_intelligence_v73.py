"""
POS LEDGER NG V73
KPI & PERFORMANCE INTELLIGENCE

READ-ONLY KPI layer.
No database modifications.
"""

VERSION = "V73"

# ------------------------------------------------------------
# VERIFIED POS LEDGER NG BUSINESS POSITION
# ------------------------------------------------------------
REVENUE = 21650.00
GROSS_PROFIT = 1432.17
LIQUID_FUNDS = 5800.00
CUSTOMER_CREDIT = 4750.00
SUPPLIER_LIABILITY = 9000.00
INVENTORY_CAPITAL = 20764.26
RECORDED_EXPENSES = 0.00
RECORDED_SALES = 14

# Management targets
TARGET_MARGIN = 10.00
TARGET_LIQUIDITY_COVERAGE = 100.00
MAX_CREDIT_EXPOSURE = 20.00


def money(value):
    return f"₦{value:,.2f}"


def percent(value):
    return f"{value:.2f}%"


def status(score):
    if score >= 80:
        return "🟢 STRONG"
    elif score >= 60:
        return "🟡 WATCH"
    elif score >= 40:
        return "🟠 AT RISK"
    return "🔴 CRITICAL"


def main():

    # --------------------------------------------------------
    # CORE CALCULATIONS
    # --------------------------------------------------------

    gross_margin = (
        GROSS_PROFIT / REVENUE * 100
        if REVENUE > 0
        else 0
    )

    supplier_gap = max(
        SUPPLIER_LIABILITY - LIQUID_FUNDS,
        0
    )

    liquidity_coverage = (
        LIQUID_FUNDS / SUPPLIER_LIABILITY * 100
        if SUPPLIER_LIABILITY > 0
        else 100
    )

    credit_exposure = (
        CUSTOMER_CREDIT / REVENUE * 100
        if REVENUE > 0
        else 0
    )

    inventory_ratio = (
        INVENTORY_CAPITAL / REVENUE * 100
        if REVENUE > 0
        else 0
    )

    # --------------------------------------------------------
    # KPI SCORES
    # --------------------------------------------------------

    margin_score = min(
        gross_margin / TARGET_MARGIN * 100,
        100
    )

    liquidity_score = min(
        liquidity_coverage,
        100
    )

    credit_score = max(
        0,
        100 - (
            credit_exposure
            / MAX_CREDIT_EXPOSURE
            * 100
        )
    )

    supplier_score = min(
        liquidity_coverage,
        100
    )

    if inventory_ratio <= 50:
        inventory_score = 100
    elif inventory_ratio <= 100:
        inventory_score = 80
    elif inventory_ratio <= 150:
        inventory_score = 60
    else:
        inventory_score = 40

    sales_score = min(
        RECORDED_SALES / 20 * 100,
        100
    )

    # --------------------------------------------------------
    # OVERALL KPI SCORE
    # --------------------------------------------------------

    overall_score = (
        margin_score * 0.25
        + liquidity_score * 0.20
        + credit_score * 0.15
        + supplier_score * 0.15
        + inventory_score * 0.15
        + sales_score * 0.10
    )

    # --------------------------------------------------------
    # REPORT
    # --------------------------------------------------------

    print("=" * 60)
    print(f"POS LEDGER NG {VERSION}")
    print("KPI & PERFORMANCE INTELLIGENCE")
    print("=" * 60)

    print()
    print("=" * 60)
    print("CURRENT BUSINESS POSITION")
    print("=" * 60)

    print(f"Revenue              : {money(REVENUE)}")
    print(f"Gross Profit         : {money(GROSS_PROFIT)}")
    print(f"Gross Margin         : {percent(gross_margin)}")
    print(f"Liquid Funds         : {money(LIQUID_FUNDS)}")
    print(f"Customer Credit      : {money(CUSTOMER_CREDIT)}")
    print(f"Supplier Liability   : {money(SUPPLIER_LIABILITY)}")
    print(f"Supplier Gap         : {money(supplier_gap)}")
    print(f"Inventory Capital    : {money(INVENTORY_CAPITAL)}")
    print(f"Recorded Expenses    : {money(RECORDED_EXPENSES)}")
    print(f"Recorded Sales       : {RECORDED_SALES}")

    print()
    print("=" * 60)
    print("KPI PERFORMANCE")
    print("=" * 60)

    print("-" * 40)
    print("1. GROSS MARGIN KPI")
    print(f"Current Margin       : {percent(gross_margin)}")
    print(f"Target Margin        : {percent(TARGET_MARGIN)}")
    print(f"KPI Score            : {margin_score:.2f}/100")
    print(f"Status               : {status(margin_score)}")

    print("-" * 40)
    print("2. LIQUIDITY COVERAGE KPI")
    print(f"Liquid Funds         : {money(LIQUID_FUNDS)}")
    print(f"Supplier Liability   : {money(SUPPLIER_LIABILITY)}")
    print(f"Coverage             : {percent(liquidity_coverage)}")
    print(f"KPI Score            : {liquidity_score:.2f}/100")
    print(f"Status               : {status(liquidity_score)}")

    print("-" * 40)
    print("3. CUSTOMER CREDIT KPI")
    print(f"Outstanding Credit   : {money(CUSTOMER_CREDIT)}")
    print(f"Credit Exposure      : {percent(credit_exposure)}")
    print(f"KPI Score            : {credit_score:.2f}/100")

    if credit_exposure > MAX_CREDIT_EXPOSURE:
        print("Status               : 🟠 COLLECTION REQUIRED")
    else:
        print("Status               : 🟡 MONITOR")

    print("-" * 40)
    print("4. SUPPLIER PRESSURE KPI")
    print(f"Supplier Liability   : {money(SUPPLIER_LIABILITY)}")
    print(f"Liquid Funds         : {money(LIQUID_FUNDS)}")
    print(f"Supplier Coverage    : {percent(liquidity_coverage)}")
    print(f"Payment Gap          : {money(supplier_gap)}")
    print(f"KPI Score            : {supplier_score:.2f}/100")

    if supplier_gap > 0:
        print("Status               : 🔴 PAYMENT PRESSURE")
    else:
        print("Status               : 🟢 COVERED")

    print("-" * 40)
    print("5. INVENTORY CAPITAL KPI")
    print(f"Inventory Capital    : {money(INVENTORY_CAPITAL)}")
    print(f"Inventory/Revenue    : {percent(inventory_ratio)}")
    print(f"KPI Score            : {inventory_score:.2f}/100")
    print(f"Status               : {status(inventory_score)}")

    print("-" * 40)
    print("6. SALES DATA KPI")
    print(f"Recorded Sales       : {RECORDED_SALES}")
    print("Reference Level      : 20")
    print(f"KPI Score            : {sales_score:.2f}/100")

    if RECORDED_SALES >= 20:
        print("Status               : 🟢 SUFFICIENT DATA")
    else:
        print("Status               : 🟡 BUILD MORE DATA")

    print()
    print("=" * 60)
    print("OVERALL KPI PERFORMANCE")
    print("=" * 60)

    print(f"Overall KPI Score    : {overall_score:.2f}/100")
    print(f"KPI Health Status    : {status(overall_score)}")

    print()
    print("=" * 60)
    print("MANAGEMENT ACTIONS")
    print("=" * 60)

    action_number = 1

    if supplier_gap > 0:
        print(
            f"{action_number}. "
            f"Protect liquidity and manage supplier gap "
            f"of {money(supplier_gap)}."
        )
        action_number += 1

    if CUSTOMER_CREDIT > 0:
        print(
            f"{action_number}. "
            f"Collect customer credit of "
            f"{money(CUSTOMER_CREDIT)}."
        )
        action_number += 1

    if gross_margin < TARGET_MARGIN:
        print(
            f"{action_number}. "
            "Improve product pricing and low-margin products."
        )
        action_number += 1

    if INVENTORY_CAPITAL > LIQUID_FUNDS:
        print(
            f"{action_number}. "
            "Monitor inventory turnover and slow-moving stock."
        )
        action_number += 1

    if RECORDED_SALES < 20:
        print(
            f"{action_number}. "
            "Continue recording sales to strengthen "
            "management data."
        )

    print()
    print("=" * 60)
    print("V73 MANAGEMENT INTERPRETATION")
    print("=" * 60)

    print(
        f"Gross margin is {percent(gross_margin)}, "
        f"below the {percent(TARGET_MARGIN)} target."
    )

    print(
        f"Supplier obligations exceed liquid funds by "
        f"{money(supplier_gap)}."
    )

    print(
        f"Customer credit of {money(CUSTOMER_CREDIT)} "
        "represents potential recoverable liquidity."
    )

    print(
        f"{money(INVENTORY_CAPITAL)} is tied up in inventory."
    )

    print(
        "The KPI layer converts the business position "
        "into measurable management indicators."
    )

    print()
    print("=" * 60)
    print("V73 SAFETY STATUS")
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
