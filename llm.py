import os
import time
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

MAX_RETRIES = 3
MODEL = "openai/gpt-oss-120b"

def call_llm(system: str, user: str, temperature: float = 0.3) -> str:
    if not os.getenv("GROQ_API_KEY"):
        raise RuntimeError("GROQ_API_KEY missing. Add it to your .env file.")

    llm = ChatGroq(model=MODEL, temperature=temperature)
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = llm.invoke([("system", system), ("human", user)])
            return response.content
        except Exception as e:  # network, rate limit, etc.
            last_error = e
            if attempt < MAX_RETRIES:
                time.sleep(2 ** attempt)

    raise RuntimeError(f"LLM failed after {MAX_RETRIES} attempts: {last_error}")