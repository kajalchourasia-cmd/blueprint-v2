from typing import Literal
from pydantic import BaseModel, Field

IdeaType = Literal["physical_business", "retail_store", "service", "saas", "ai_product", "marketplace", "creator", "consumer_product", "other"]
Goal = Literal["get_job", "side_income", "small_business", "startup", "raise_money", "just_explore"]

class UserProfile(BaseModel):
    idea: str
    idea_type: IdeaType = "other"
    location: str = ""
    target_customer: str = ""
    background: str = ""
    life_context: list[str] = Field(default_factory=list)
    goal: str = "test_whether_idea_can_work"
    success_definition: str = ""
    launch_timeline: str = "Not sure"
    current_work: str = ""
    constraints: list[str] = Field(default_factory=list)
    hours_per_week: int = 5
    money_available: int = 500

class RealityCheck(BaseModel):
    fit_score: int = Field(ge=1, le=10)
    fit_rationale: str
    unfair_advantages: list[str] = Field(min_length=3, max_length=3)
    critical_gaps: list[str] = Field(min_length=3, max_length=3)
    specific_delusions: list[dict]

class Step(BaseModel):
    number: int
    name: str
    what_to_do: str
    why_it_matters: str
    resources: list[str]
    done_criteria: str
    estimated_time_days: int
    estimated_cost_dollars: int
    estimated_hours: int
    step_type: str
    action_checklist: list[str] = Field(default_factory=list)
    people_to_contact: list[str] = Field(default_factory=list)
    places_or_channels: list[str] = Field(default_factory=list)
    evidence_to_capture: list[str] = Field(default_factory=list)
    decision_signal: str = ""
    likely_blocker: str = ""

class Plan(BaseModel):
    steps: list[Step] = Field(min_length=8, max_length=15)
    total_estimated_days: int
    goal_reached_description: str

class GapLayer(BaseModel):
    layer_type: Literal["unseen", "missing_voice", "real_cost"]
    content: str
    ledger_delta: dict | None = None

class CostLedger(BaseModel):
    cash_dollars: int
    hours_invested: int
    relationship_impact_days: int
    health_impact_score: int
    opportunity_cost_dollars: int
    projected_3yr_total: int
