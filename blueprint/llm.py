import os
from dotenv import load_dotenv

load_dotenv()
MODEL = "llama-3.3-70b-versatile"

def configured() -> bool:
    return bool(os.getenv("GROQ_API_KEY"))

def structured(model_class, prompt: str):
    if not configured():
        return None
    import instructor
    from groq import Groq
    client = instructor.from_groq(Groq(api_key=os.environ["GROQ_API_KEY"]), mode=instructor.Mode.JSON)
    return client.chat.completions.create(model=MODEL, response_model=model_class, messages=[{"role": "user", "content": prompt}], temperature=0.4)

def text(prompt: str) -> str:
    if not configured():
        return ""
    from groq import Groq
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    response = client.chat.completions.create(model=MODEL, messages=[{"role": "user", "content": prompt}], temperature=0.4)
    return response.choices[0].message.content or ""

