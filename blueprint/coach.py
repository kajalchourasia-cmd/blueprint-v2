from .llm import text
from .prompts import COACH_CHAT_PROMPT
from .schemas import CostLedger, Plan, UserProfile

def chat(message: str, profile: UserProfile, plan: Plan, ledger: CostLedger, history: list[dict]) -> str:
    result = text(COACH_CHAT_PROMPT.format(message=message, profile=profile.model_dump_json(), plan=plan.model_dump_json(), ledger=ledger.model_dump_json(), history=history[-6:]))
    if result: return result
    if "weekend" in message.lower(): return f"Run a 48-hour test for {profile.idea}: send the offer to 15 likely buyers. Pass if at least 3 reply and 1 agrees to a paid next step. Stop if nobody will commit to a conversation. Should I add anything to your ledger?"
    if "10 users" in message.lower(): return "Use three targeted communities, five direct messages, and two warm introductions. Ask for the current workaround, not whether people like the idea. Should I add anything to your ledger?"
    return f"For {profile.idea}, make the next move small enough to finish this week: speak to one target user, record the exact problem, and decide what evidence would justify continuing. Should I add anything to your ledger?"

