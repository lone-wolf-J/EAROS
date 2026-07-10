"""Executive What-If Simulation.

Given levers (attrition, hiring pace, budget, geo-mix), recompute headcount
trajectory + strategy recommendation. Deterministic + fast so sliders feel live.
"""
from __future__ import annotations

from typing import Any

from foundation import ConfidenceScore, Evidence, ReasoningStep, Recommendation
from platform_core.world import WorldState


async def simulate(world: WorldState, organization_id: str,
                   attrition_pct: float = 0.12,
                   hiring_freeze: bool = False,
                   budget_delta_pct: float = 0.0,
                   bangalore_expansion: bool = False,
                   ai_engineering_doubles: bool = False,
                   horizon_months: int = 12) -> dict[str, Any]:
    departments = await world.list_departments(organization_id)
    teams = await world.list_teams(organization_id)
    jobs = await world.list_jobs(organization_id)
    open_jobs = [j for j in jobs if j.status.value == "open"]
    total_hc = sum(d.headcount for d in departments)
    open_seats = sum(t.open_seats for t in teams)
    monthly_attrition = total_hc * (attrition_pct / 12)
    monthly_hire_rate = 0 if hiring_freeze else max(4, len(open_jobs) * 0.6)
    if ai_engineering_doubles:
        monthly_hire_rate += 3  # extra AI hiring
    if bangalore_expansion:
        monthly_hire_rate += 2

    trajectory = []
    hc = total_hc
    for m in range(horizon_months + 1):
        trajectory.append({"month": m, "headcount": int(round(hc))})
        hc = hc - monthly_attrition + monthly_hire_rate

    ending_hc = trajectory[-1]["headcount"]
    net = ending_hc - total_hc
    net_pct = net / max(1, total_hc)

    risks = []
    if attrition_pct > 0.15:
        risks.append("Attrition above 15% — retention program required.")
    if hiring_freeze and open_seats > 15:
        risks.append("Freeze with >15 open seats will erode delivery capacity.")
    if budget_delta_pct < -0.1:
        risks.append(f"Budget cut of {abs(budget_delta_pct):.0%} constrains "
                     "sourcing spend on scarce skills.")
    if ai_engineering_doubles and attrition_pct > 0.13:
        risks.append("Doubling AI hiring during high attrition raises quality risk.")

    strategy_summary = ""
    if hiring_freeze:
        strategy_summary = (f"Freeze projects a net {net:+d} ({net_pct:+.0%}) "
                            f"in {horizon_months} months. Redirect budget to retention.")
    elif ai_engineering_doubles:
        strategy_summary = (f"Doubling AI Engineering with {attrition_pct:.0%} attrition "
                            f"lands at ~{ending_hc} headcount. Front-load senior IC hiring.")
    elif bangalore_expansion:
        strategy_summary = (f"Bangalore expansion adds ~24 seats over the horizon; "
                            f"net {net:+d} ({net_pct:+.0%}).")
    else:
        strategy_summary = (f"Baseline plan: net {net:+d} ({net_pct:+.0%}) "
                            f"over {horizon_months} months.")

    rec = Recommendation(
        title="What-If Simulation",
        summary=strategy_summary,
        action="human.review_simulation",
        inputs={"attrition_pct": attrition_pct, "hiring_freeze": hiring_freeze,
                "budget_delta_pct": budget_delta_pct,
                "bangalore_expansion": bangalore_expansion,
                "ai_engineering_doubles": ai_engineering_doubles},
        confidence=ConfidenceScore.from_value(0.68),
        reasoning=[
            ReasoningStep(step=1,
                          thought=f"Starting headcount {total_hc}, "
                                  f"attrition {attrition_pct:.0%} annualized, "
                                  f"hiring rate {monthly_hire_rate:.1f}/mo.",
                          conclusion=f"Ending {ending_hc} ({net:+d})."),
            ReasoningStep(step=2,
                          thought="Open seats + priority mix pull sourcing capital "
                                  "toward scarce skills.",
                          conclusion="Route budget to P0 roles first."),
            ReasoningStep(step=3,
                          thought="High-attrition scenarios inflate first-year cost "
                                  "of hire; retention program has better ROI.",
                          conclusion="Balance hire+retention."),
        ],
        evidence=[
            Evidence(source="world.departments", reference="attrition_rate",
                     excerpt=f"avg current attrition ~ {sum(d.attrition_rate for d in departments) / max(1, len(departments)):.0%}"),
            Evidence(source="world.jobs", reference="open",
                     excerpt=f"{len(open_jobs)} open reqs, {open_seats} open seats"),
        ],
        tradeoffs=[
            "Retention spend vs. new hiring spend",
            "Speed of ramp vs. depth of screening under budget pressure",
        ],
        risks=risks,
    )

    return {
        "levers": {
            "attrition_pct": attrition_pct,
            "hiring_freeze": hiring_freeze,
            "budget_delta_pct": budget_delta_pct,
            "bangalore_expansion": bangalore_expansion,
            "ai_engineering_doubles": ai_engineering_doubles,
            "horizon_months": horizon_months,
        },
        "trajectory": trajectory,
        "starting_headcount": total_hc,
        "ending_headcount": ending_hc,
        "net_change": net,
        "net_change_pct": round(net_pct, 3),
        "risks": risks,
        "recommendation": rec.model_dump(),
    }
