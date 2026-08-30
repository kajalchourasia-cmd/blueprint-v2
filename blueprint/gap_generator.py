from .llm import structured
from .prompts import GAP_LAYER_PROMPT
from .schemas import GapLayer, Step, UserProfile

def generate(step: Step, layer_type: str, profile: UserProfile) -> GapLayer:
    result = structured(GapLayer, GAP_LAYER_PROMPT.format(step=step.model_dump_json(), layer_type=layer_type, profile=profile.model_dump_json(), library_examples="Bundled gap examples"))
    if result: return result
    coffee = "coffee" in profile.idea.lower() or "cafe" in profile.idea.lower()
    if layer_type == "unseen": content = ("1. What morning behavior are you assuming instead of observing?\n2. Which cost changes when the shop is busy?\n3. What would make a customer return next week?" if coffee else "1. What evidence would change your mind about this step?\n2. Which buyer has the strongest reason to say no?\n3. What must be true for this to work next month?")
    elif layer_type == "missing_voice": content = "> I am the person affected by this step every day. Show me how it removes work or risk; I will not adopt it because the founder wants it to exist.\n\n— The person who must live with the outcome"
    else: content = "This step will take more calendar time than the task itself because follow-ups and recovery are part of the work. Budget a small cash buffer and protect one block of rest."
    return GapLayer(layer_type=layer_type, content=content, ledger_delta={"cash_dollars":50,"hours_this_week":2,"hours_total":5,"relationship_days":0,"health_score":-1} if layer_type == "real_cost" else None)
