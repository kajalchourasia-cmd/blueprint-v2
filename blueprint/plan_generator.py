from .llm import structured
from .prompts import PLAN_GENERATOR_PROMPT
from .schemas import Plan, Step, UserProfile

def generate(profile: UserProfile) -> Plan:
    result = structured(Plan, PLAN_GENERATOR_PROMPT.format(profile=profile.model_dump_json(), similar_journeys="Bundled journey references"))
    if result: return result
    names = [("Define the buyer", "research"), ("Interview 10 target users", "interview"), ("Map the painful workflow", "research"), ("Run a 48-hour online test", "validate"), ("Price a paid pilot", "sell"), ("Deliver the smallest digital version", "build"), ("Review evidence and costs", "measure"), ("Choose the next commitment", "operate")]
    generic_people = ["Person currently experiencing the problem", "Recent buyer of an alternative", "Person who stopped using a competing solution", "Budget owner who can approve payment", "Front-line worker who sees the workflow daily"]
    generic_places = ["Google search using the customer's exact problem language", "LinkedIn role and location filters", "Relevant Reddit and local community searches", "Competitor review pages", "Industry association or marketplace directories"]
    steps = []
    for i, (name, step_type) in enumerate(names, 1):
        validation_step = step_type in {"interview", "research", "validate", "measure"}
        people = generic_people[:4]
        places = generic_places[:4]
        checklist = [
            f"Write the single assumption that {name.lower()} must test.",
            f"Create a one-page evidence sheet for {name.lower()}.",
            "Contact or observe at least five relevant people before changing the plan.",
            "Record exact words, behaviour, price reactions, and contradictions.",
            "Compare the result with the pass/fail signal and choose continue, change, or stop.",
        ]
        evidence = ["Who was contacted and why they were relevant", "Exact customer words or observed behaviour", "Price, frequency, and current alternative", "Evidence that contradicts the idea", "A dated continue/change/stop decision"]
        steps.append(Step(
            number=i,
            name=name,
            what_to_do=f"Complete {name.lower()} for {profile.idea}. Use the checklist, people, and field locations below so this produces evidence rather than opinions.",
            why_it_matters="This turns an assumption into evidence before the next commitment and prevents expensive work from being justified by enthusiasm alone.",
            resources=["A simple interview and observation log", "A spreadsheet with one row per conversation", "A phone voice-note template for immediate field notes"],
            done_criteria="Record what happened, what changed, and a written continue/change/stop decision supported by evidence.",
            estimated_time_days=2 + i,
            estimated_cost_dollars=50 * (i % 4),
            estimated_hours=3 + i,
            step_type=step_type,
            action_checklist=checklist,
            people_to_contact=people if validation_step else people[:3],
            places_or_channels=places,
            evidence_to_capture=evidence,
            decision_signal="Continue only if at least 5 of 10 relevant people show the same unmet need or complete a real commitment such as a booking, deposit, introduction, or paid trial.",
            likely_blocker="Polite interest may be mistaken for demand. Treat compliments as zero evidence unless they lead to observable behaviour or commitment.",
        ))
    return Plan(steps=steps, total_estimated_days=sum(s.estimated_time_days for s in steps), goal_reached_description=f"A tested first version of {profile.idea} with a decision grounded in customer evidence.")
