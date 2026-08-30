import pandas as pd
from .llm import structured
from .prompts import REALITY_CHECK_PROMPT
from .schemas import RealityCheck, UserProfile

def generate(profile: UserProfile) -> RealityCheck:
    journeys = pd.read_csv("data/founder_journeys.csv").to_string(index=False)
    result = structured(RealityCheck, REALITY_CHECK_PROMPT.format(profile=profile.model_dump_json(), similar_journeys=journeys))
    return result or RealityCheck(fit_score=5, fit_rationale="Your fit depends on evidence that the target customer will pay, not on the idea alone.", unfair_advantages=[f"Your stated background can shorten one part of the learning curve.", "You can test demand before committing full resources.", "Your available time gives you a bounded experiment window."], critical_gaps=["The buyer and their urgent problem are not yet proven.", "The first distribution channel is still an assumption.", "The cost of reaching a repeatable sale is unknown."], specific_delusions=[{"belief":"Positive reactions will predict purchases.","reality":"Only a payment, deposit, or repeated use is strong evidence."},{"belief":"You can solve every unknown by building.","reality":"Some unknowns require conversations and observation first."},{"belief":"The initial plan will fit around existing commitments.","reality":"Unplanned sales, support, and recovery time consume the margin."}])

