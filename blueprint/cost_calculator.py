from .schemas import CostLedger, Plan, Step

def compute_initial(plan: Plan) -> CostLedger:
    cash = sum(s.estimated_cost_dollars for s in plan.steps)
    hours = sum(s.estimated_hours for s in plan.steps)
    return CostLedger(cash_dollars=cash, hours_invested=0, relationship_impact_days=0, health_impact_score=0, opportunity_cost_dollars=hours * 20, projected_3yr_total=cash + hours * 20)

def mark_done(step: Step, ledger: CostLedger) -> CostLedger:
    data = ledger.model_dump(); data["hours_invested"] += step.estimated_hours; data["cash_dollars"] += step.estimated_cost_dollars; data["projected_3yr_total"] = data["cash_dollars"] + data["opportunity_cost_dollars"]
    return CostLedger(**data)

def add_delta(ledger: CostLedger, delta: dict) -> CostLedger:
    data = ledger.model_dump()
    for key, value in {"cash_dollars":"cash_dollars", "hours_this_week":"hours_invested", "relationship_days":"relationship_impact_days", "health_score":"health_impact_score"}.items(): data[value] += int(delta.get(key, 0))
    data["projected_3yr_total"] = max(0, data["cash_dollars"] + data["opportunity_cost_dollars"] + data["relationship_impact_days"] * 100)
    return CostLedger(**data)

