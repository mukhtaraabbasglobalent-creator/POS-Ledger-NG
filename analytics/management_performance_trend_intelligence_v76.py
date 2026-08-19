"""
POS LEDGER NG V76
MANAGEMENT PERFORMANCE TREND & IMPROVEMENT INTELLIGENCE

READ-ONLY analytics layer.
Does not modify the database.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class KPI:
    name: str
    current: float
    previous: float
    target: float
    unit: str = "%"

    @property
    def change(self) -> float:
        return self.current - self.previous

    @property
    def target_gap(self) -> float:
        return max(self.target - self.current, 0.0)

    @property
    def direction(self) -> str:
        if self.change > 0.01:
            return "IMPROVING"
        if self.change < -0.01:
            return "DECLINING"
        return "STABLE"


def money(value: float) -> str:
    return f"₦{value:,.2f}"


def pct(value: float) -> str:
    return f"{value:.2f}%"


def score(value: float) -> str:
    return f"{max(0.0, min(value, 100.0)):.2f}/100"


def trend_score(kpi: KPI) -> float:
    """
    Trend score:
    - 50 = unchanged
    - >50 = improving
    - <50 = declining
    """
    if kpi.change > 0:
        return min(100.0, 50.0 + abs(kpi.change) * 10)
    if kpi.change < 0:
        return max(0.0, 50.0 - abs(kpi.change) * 10)
    return 50.0


def print_header(title: str) -> None:
    print("=" * 60)
    print("POS LEDGER NG V76")
    print(title)
    print("=" * 60)


def main() -> None:

    # ---------------------------------------------------------
    # CURRENT BUSINESS POSITION
    # ---------------------------------------------------------
    revenue = 21_650.00

    # Corrected reference from V73/V74.
    current_gross_profit = 1_432.17
    current_margin = 6.62

    liquid_funds = 5_800.00
    customer_credit = 4_750.00
    supplier_liability = 9_000.00
    supplier_gap = 3_200.00
    inventory_capital = 20_764.26
    recorded_sales = 14

    # ---------------------------------------------------------
    # PREVIOUS KPI BASELINE
    # V73 KPI values
    # ---------------------------------------------------------
    previous_margin = 6.62
    previous_liquidity_score = 64.44
    previous_credit_score = 0.00
    previous_inventory_score = 80.00
    previous_sales_score = 70.00

    # ---------------------------------------------------------
    # CURRENT KPI VALUES
    # V74/V75 normalized baseline
    # ---------------------------------------------------------
    current_liquidity_score = 64.44
    current_credit_score = 90.30
    current_inventory_score = 72.45
    current_sales_score = 70.00

    target_margin = 10.00

    # ---------------------------------------------------------
    # KPI TREND ANALYSIS
    # ---------------------------------------------------------
    kpis: List[KPI] = [
        KPI(
            "Gross Margin",
            current_margin,
            previous_margin,
            target_margin,
        ),
        KPI(
            "Liquidity Coverage",
            current_liquidity_score,
            previous_liquidity_score,
            100.00,
            unit="score",
        ),
        KPI(
            "Customer Credit",
            current_credit_score,
            previous_credit_score,
            100.00,
            unit="score",
        ),
        KPI(
            "Inventory Efficiency",
            current_inventory_score,
            previous_inventory_score,
            100.00,
            unit="score",
        ),
        KPI(
            "Sales Data",
            current_sales_score,
            previous_sales_score,
            100.00,
            unit="score",
        ),
    ]

    # ---------------------------------------------------------
    # OVERALL TREND
    # ---------------------------------------------------------
    average_change = sum(k.change for k in kpis) / len(kpis)

    improving = [k for k in k in kpis if k.direction == "IMPROVING"]
    declining = [k for k in kpis if k.direction == "DECLINING"]
    stable = [k for k in kpis if k.direction == "STABLE"]

    overall_trend_score = max(
        0.0,
        min(100.0, 50.0 + average_change * 2.0),
    )

    if overall_trend_score >= 60:
        trend_status = "🟢 IMPROVING"
    elif overall_trend_score >= 45:
        trend_status = "🟡 STABLE"
    else:
        trend_status = "🔴 DECLINING"

    # ---------------------------------------------------------
    # MANAGEMENT PRIORITIES
    # ---------------------------------------------------------
    priorities = []

    if current_margin < target_margin:
        priorities.append(
            (
                "URGENT",
                "IMPROVE GROSS MARGIN",
                current_margin,
                f"Margin remains {pct(target_margin - current_margin)} "
                "below the management target.",
            )
        )

    if supplier_gap > 0:
        priorities.append(
            (
                "URGENT",
                "PROTECT LIQUIDITY",
                supplier_gap,
                f"Supplier obligations exceed liquid funds by "
                f"{money(supplier_gap)}.",
            )
        )

    if customer_credit > 0:
        priorities.append(
            (
                "HIGH",
                "COLLECT CUSTOMER CREDIT",
                customer_credit,
                f"{money(customer_credit)} represents potentially "
                "recoverable liquidity.",
            )
        )

    if inventory_capital > revenue * 0.80:
        priorities.append(
            (
                "MEDIUM",
                "CONTROL INVENTORY CAPITAL",
                inventory_capital,
                f"{money(inventory_capital)} is tied up in inventory.",
            )
        )

    if recorded_sales < 20:
        priorities.append(
            (
                "MONITOR",
                "STRENGTHEN SALES DATA",
                20 - recorded_sales,
                f"{20 - recorded_sales} additional recorded sales "
                "are needed for stronger analysis.",
            )
        )

    # ---------------------------------------------------------
    # OUTPUT
    # ---------------------------------------------------------
    print_header("MANAGEMENT PERFORMANCE TREND & IMPROVEMENT INTELLIGENCE")

    print("\n" + "=" * 60)
    print("CURRENT BUSINESS POSITION")
    print("=" * 60)

    print(f"Revenue              : {money(revenue)}")
    print(f"Gross Profit         : {money(current_gross_profit)}")
    print(f"Gross Margin         : {pct(current_margin)}")
    print(f"Liquid Funds         : {money(liquid_funds)}")
    print(f"Customer Credit      : {money(customer_credit)}")
    print(f"Supplier Liability   : {money(supplier_liability)}")
    print(f"Supplier Gap         : {money(supplier_gap)}")
    print(f"Inventory Capital    : {money(inventory_capital)}")
    print(f"Recorded Sales       : {recorded_sales}")

    print("\n" + "=" * 60)
    print("KPI TREND ANALYSIS")
    print("=" * 60)

    for index, kpi in enumerate(kpis, 1):
        print("-" * 40)
        print(f"{index}. {kpi.name}")
        print(f"Previous KPI        : {score(kpi.previous)}")
        print(f"Current KPI         : {score(kpi.current)}")
        print(f"Change              : {kpi.change:+.2f}")
        print(f"Trend               : {kpi.direction}")
        print(f"Target              : {score(kpi.target)}")
        print(f"Target Gap          : {kpi.target_gap:.2f}")

    print("\n" + "=" * 60)
    print("OVERALL PERFORMANCE TREND")
    print("=" * 60)

    print(f"Average KPI Change  : {average_change:+.2f}")
    print(f"Trend Score         : {score(overall_trend_score)}")
    print(f"Trend Status        : {trend_status}")

    print("\n" + "=" * 60)
    print("TREND SUMMARY")
    print("=" * 60)

    print(f"Improving KPIs      : {len(improving)}")
    print(f"Declining KPIs      : {len(declining)}")
    print(f"Stable KPIs         : {len(stable)}")

    if improving:
        print("\nImproving:")
        for kpi in improving:
            print(f"- {kpi.name}: {kpi.change:+.2f}")

    if declining:
        print("\nDeclining:")
        for kpi in declining:
            print(f"- {kpi.name}: {kpi.change:+.2f}")

    if stable:
        print("\nStable:")
        for kpi in stable:
            print(f"- {kpi.name}: {kpi.change:+.2f}")

    print("\n" + "=" * 60)
    print("MANAGEMENT IMPROVEMENT PRIORITIES")
    print("=" * 60)

    for index, item in enumerate(priorities, 1):
        priority, action, value, reason = item

        print("-" * 40)
        print(f"{index}. [{priority}] {action}")
        print(f"Value               : {money(value)}")
        print(f"Reason              : {reason}")

    print("\n" + "=" * 60)
    print("TOP MANAGEMENT SIGNAL")
    print("=" * 60)

    if current_margin < target_margin:
        print("Signal              : ⚠️ PROFITABILITY GAP")
        print(
            "Management should improve product pricing and "
            "gross margin before aggressive expansion."
        )
    elif supplier_gap > 0:
        print("Signal              : ⚠️ LIQUIDITY PRESSURE")
        print(
            "Management should protect cash availability "
            "and control supplier obligations."
        )
    else:
        print("Signal              : 🟢 PERFORMANCE STABLE")

    print("\n" + "=" * 60)
    print("V76 MANAGEMENT INTERPRETATION")
    print("=" * 60)

    print(
        "V76 compares KPI performance across management cycles "
        "to determine whether business performance is improving, "
        "declining or remaining stable."
    )

    print(
        "The system separates KPI movement from the absolute "
        "business position so management can see both current "
        "performance and direction of change."
    )

    print(
        f"Gross margin remains {pct(current_margin)}, compared "
        f"with the {pct(target_margin)} management target."
    )

    if supplier_gap > 0:
        print(
            f"Liquidity remains under pressure because supplier "
            f"obligations exceed available funds by {money(supplier_gap)}."
        )

    print(
        f"Customer credit of {money(customer_credit)} remains "
        "a potential liquidity recovery opportunity."
    )

    print("\n" + "=" * 60)
    print("V76 SAFETY STATUS")
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
