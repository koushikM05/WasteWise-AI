
"""Groq-powered food-waste advisor for WasteWise AI."""

import os

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

DEFAULT_MODEL = "llama-3.3-70b-versatile"


def get_groq_api_key():
    """Read the Groq API key from the environment."""
    return os.getenv("GROQ_API_KEY", "").strip()


def ask_agent(question, waste_summary="", memories=""):
    """Ask Groq for canteen advice using analytics and Hindsight context."""

    api_key = get_groq_api_key()

    if not api_key:
        raise ValueError(
            "GROQ_API_KEY is missing. Add it to your .env file."
        )

    if not question or not question.strip():
        raise ValueError("Please enter a question for the AI advisor.")

    model = os.getenv("GROQ_MODEL", DEFAULT_MODEL).strip()

    client = Groq(api_key=api_key)

    system_prompt = """
You are WasteWise AI, an assistant that helps college canteens
reduce food waste.

Give practical, clear and actionable recommendations.

Rules:
1. Use the supplied waste analytics and memories as context.
2. Never invent statistics, records or historical events.
3. Clearly state when information is insufficient.
4. Suggest realistic food preparation and inventory improvements.
5. Prioritize reducing food waste without causing food shortages.
6. Use simple language and organize longer answers into bullet points.
"""

    context = f"""
WASTE ANALYTICS SUMMARY:
{waste_summary if waste_summary else "No analytics data supplied."}

HINDSIGHT MEMORY:
{memories if memories else "No recalled memories supplied."}

USER QUESTION:
{question.strip()}
"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context},
            ],
            temperature=0.3,
            max_completion_tokens=800,
        )

        answer = response.choices[0].message.content

        if not answer:
            raise RuntimeError("Groq returned an empty response.")

        return answer.strip()

    except Exception as exc:
        raise RuntimeError(f"Groq AI request failed: {exc}") from exc
