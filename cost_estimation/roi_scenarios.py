"""ROI scenarios for roi_risk_assessment.md, including the commercial costs and the downside cases.

Run: python cost_estimation/roi_scenarios.py
Every ROI number in roi_risk_assessment.md comes from this script, so the
assumptions can be changed in one place and the tables re-generated.
"""

RATE = 95  # EUR/hour, blended consultant/engineer rate (cost_analysis.md)
LAWYER_RATE = 250  # EUR/hour, typical German data protection lawyer rate

# One-time costs
DEVELOPMENT = 5_273  # 55.5 hours, already done (roi_risk_assessment.md)
SECURITY_REVIEW = 16 * RATE  # code, dependency, secrets and data flow review before real client data
ENV_ISOLATION = 12 * RATE  # one isolated workspace per client: own DB folder, own API project, encrypted, deleted after
DPA_SETUP = 4 * LAWYER_RATE + 2 * RATE  # lawyer review of the DPA template, add OpenAI + LangSmith as sub-processors
COMMERCIAL_UPFRONT = SECURITY_REVIEW + ENV_ISOLATION + DPA_SETUP
# Pilot delivery, the remaining story hours in delivery_plan.md's pilot backlog:
# Zahra 24 h (erase tool 8, training 4, Discovery gate 2, fixes 6, decision pack 4),
# Joseph 6 h (baseline 3, success criteria 2, client feedback 1), Chleo 5 h
PILOT_DELIVERY = (24 + 6 + 5) * RATE
UPFRONT = DEVELOPMENT + COMMERCIAL_UPFRONT + PILOT_DELIVERY

# Recurring fixed costs, per month
HOSTING = 30  # small EU-hosted VM for the isolated workspaces
SUPPORT = 2 * RATE  # maintenance: dependency updates, model changes, prompt fixes, bug fixes
FIXED_MONTHLY = HOSTING + SUPPORT

# Per onboarding run
REVIEW = 48  # mandatory 30-minute consultant review, 0.5 x 95 EUR rounded up
LLM = 0.001  # measured, outputs/llm_costs.jsonl
PER_RUN = REVIEW + LLM

SCENARIOS = [
    # name, manual hours today, onboardings per month
    ("Upside", 8, 2),
    ("Base", 6, 2),
    ("Manual work already efficient", 2, 2),
    ("Lower volume", 6, 1),
    ("Both downsides", 2, 1),
]


def total_cost(months, runs_per_month, upfront=UPFRONT, fixed=FIXED_MONTHLY):
    return upfront + fixed * months + PER_RUN * runs_per_month * months


def roi(months, manual_hours, runs_per_month, **kw):
    value = manual_hours * RATE * runs_per_month * months
    cost = total_cost(months, runs_per_month, **kw)
    return value, cost, value - cost, (value - cost) / cost * 100


def break_even_month(manual_hours, runs_per_month, **kw):
    monthly_net = (manual_hours * RATE - PER_RUN) * runs_per_month - kw.get("fixed", FIXED_MONTHLY)
    if monthly_net <= 0:
        return None  # never pays back
    return kw.get("upfront", UPFRONT) / monthly_net


def min_runs_per_month(manual_hours, months=36):
    """Fewest onboardings per month that still break even within `months`."""
    saving_per_run = manual_hours * RATE - PER_RUN
    if saving_per_run <= 0:
        return None
    return (UPFRONT / months + FIXED_MONTHLY) / saving_per_run


if __name__ == "__main__":
    print(f"Commercial readiness: security {SECURITY_REVIEW:,.0f} + isolation {ENV_ISOLATION:,.0f} "
          f"+ DPA {DPA_SETUP:,.0f} = {COMMERCIAL_UPFRONT:,.0f} EUR")
    print(f"Pilot delivery: {PILOT_DELIVERY:,.0f} EUR")
    print(f"Total one-time investment: {UPFRONT:,.0f} EUR | fixed monthly: {FIXED_MONTHLY:,.0f} EUR | per run: {PER_RUN:,.0f} EUR\n")

    print("ROI per scenario:")
    for name, hours, runs in SCENARIOS:
        line = f"  {name:32s} {hours}h, {runs}/month"
        for m in (12, 36):
            v, c, n, r = roi(m, hours, runs)
            line += f" | {m}m: value {v:,.0f} cost {c:,.0f} net {n:,.0f} ROI {r:.0f}%"
        be = break_even_month(hours, runs)
        line += f" | break-even: {'never' if be is None else f'{be:.1f} months'}"
        print(line)

    print("\nMinimum onboardings per month to break even within 36 months:")
    for hours in (1, 2, 3, 4, 6, 8):
        mr = min_runs_per_month(hours)
        print(f"  manual {hours}h today: {'never' if mr is None else f'{mr:.2f} per month'}")
