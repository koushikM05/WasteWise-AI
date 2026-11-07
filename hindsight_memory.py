"""Save and look up memories with Hindsight.

Hindsight is the long-term memory for the canteen assistant.
A memory bank is one private notebook for this project.

Three real operations live here:
    RETAIN  - save canteen records (or a note) into the memory bank
    RECALL  - search the bank and get back the matching saved memories
    REFLECT - ask Hindsight to think over the saved memories and answer

Every function raises HindsightMemoryError with a plain-English message when
something goes wrong (no key, no internet, wrong key, ...). The dashboard shows
that message to the user. Nothing here ever returns made-up memories.
"""

import asyncio
import os
import re

from dotenv import load_dotenv

load_dotenv()

CLOUD_URL = "https://api.hindsight.vectorize.io"
LOG_CONTEXT = "WasteWise canteen daily log"

# Banks we already created in this run, so we do not ask every time.
_ready_banks = set()


class HindsightMemoryError(Exception):
    """Something stopped a memory operation. The message is safe to show on screen."""


def get_settings():
    """Read Hindsight settings from the environment.

    Returns a small dictionary. Values stay empty until .env is filled in.
    """
    return {
        "api_key": os.getenv("HINDSIGHT_API_KEY", ""),
        "bank_name": os.getenv("HINDSIGHT_BANK_NAME", "wastewise-canteen"),
        "base_url": os.getenv("HINDSIGHT_BASE_URL", CLOUD_URL),
    }


def setup_problem():
    """Return a short sentence describing what is missing, or None when ready."""
    settings = get_settings()
    key = settings["api_key"].strip()
    if not key or key.startswith("your_"):
        return (
            "No Hindsight API key found. Copy .env.example to .env, put your key "
            "in HINDSIGHT_API_KEY, then restart the app."
        )
    if not settings["base_url"].strip():
        return "HINDSIGHT_BASE_URL is empty in .env."
    if not settings["bank_name"].strip():
        return "HINDSIGHT_BANK_NAME is empty in .env."
    return None


# ---------------------------------------------------------------------------
# Turning canteen rows into memories (no internet needed for this part)
# ---------------------------------------------------------------------------


def record_to_text(row):
    """Write one canteen row as a plain sentence Hindsight can understand."""
    date = row["date"]
    prepared = float(row["portions_prepared"])
    served = float(row["portions_served"])
    wasted = float(row["portions_wasted"])
    waste_pct = (wasted / prepared * 100) if prepared > 0 else 0.0
    cost = wasted * float(row["cost_per_portion"])

    text = (
        f"On {date:%Y-%m-%d} ({date:%A}), at {row['meal']}, the canteen prepared "
        f"{prepared:g} portions of {row['item']} ({row['category']}). "
        f"{served:g} portions were sold and {wasted:g} were wasted "
        f"({waste_pct:.1f}% waste, {float(row['waste_kg']):g} kg, about Rs {cost:,.0f} lost)."
    )
    reason = str(row["reason"]).strip()
    if reason and reason.lower() != "nan":
        text += f" Reason noted: {reason}."
    return text


def build_memory_items(records):
    """Turn the cleaned records table into a list of items for Hindsight.

    Each item has: content, timestamp (the day it happened), context, and a
    document_id that is the same every time for the same day/meal/dish.
    """
    items = []
    for _, row in records.iterrows():
        slug = re.sub(r"[^a-z0-9]+", "-", f"{row['meal']}-{row['item']}".lower()).strip("-")
        items.append(
            {
                "content": record_to_text(row),
                "timestamp": f"{row['date']:%Y-%m-%d}T00:00:00",
                "context": LOG_CONTEXT,
                "document_id": f"wastewise-{row['date']:%Y-%m-%d}-{slug}",
            }
        )
    return items


# ---------------------------------------------------------------------------
# Talking to Hindsight
# ---------------------------------------------------------------------------


def _make_client():
    """Create a Hindsight client from .env settings, or explain what is missing."""
    problem = setup_problem()
    if problem:
        raise HindsightMemoryError(problem)

    try:
        from hindsight_client import Hindsight
    except ImportError:
        raise HindsightMemoryError(
            "The hindsight-client package is not installed. "
            "Run: pip install -r requirements.txt"
        )

    settings = get_settings()
    return Hindsight(
        base_url=settings["base_url"].strip(),
        api_key=settings["api_key"].strip(),
        timeout=120.0,
    )


def _explain(error, action):
    """Turn a raw error into one friendly sentence. Never includes the API key."""
    settings = get_settings()
    status = getattr(error, "status", None)
    name = type(error).__name__

    if status == 401:
        return (
            f"Hindsight rejected the API key while trying to {action} (401). "
            "Check HINDSIGHT_API_KEY in .env for typos or an expired key."
        )
    if status == 403:
        return f"Hindsight says this key is not allowed to {action} (403). Check your Hindsight plan or key."
    if status == 404:
        return (
            f"Hindsight could not find what it needed to {action} (404). "
            f"Check HINDSIGHT_BASE_URL ({settings['base_url']}) and the bank name."
        )
    if status in (400, 422):
        return f"Hindsight did not accept the request to {action} ({status}). Details: {_clean(error)}"
    if status == 429:
        return f"Hindsight says too many requests while trying to {action} (429). Wait a minute and try again."
    if isinstance(status, int) and status >= 500:
        return f"Hindsight had a server problem while trying to {action} ({status}). Try again shortly."

    looks_like_network = isinstance(error, (OSError, asyncio.TimeoutError)) or any(
        word in name for word in ("Connect", "Timeout", "ClientError", "Connection", "Network")
    )
    if looks_like_network:
        return (
            f"Could not reach Hindsight at {settings['base_url']} while trying to {action}. "
            "Check your internet connection and HINDSIGHT_BASE_URL."
        )

    return f"Could not {action}. {name}: {_clean(error)}"


def _clean(error):
    """Short error text with the API key removed, in case it appears in it."""
    text = str(error).strip().splitlines()[0] if str(error).strip() else "no details"
    key = get_settings()["api_key"].strip()
    if key:
        text = text.replace(key, "***")
    return text[:300]


def _run(action, work):
    """Open a client, run work(client, bank_id), and turn any failure into HindsightMemoryError."""
    client = _make_client()
    bank_id = get_settings()["bank_name"].strip()
    try:
        with client:
            return work(client, bank_id)
    except HindsightMemoryError:
        raise
    except Exception as error:
        raise HindsightMemoryError(_explain(error, action)) from None


def _ensure_bank(client, bank_id):
    """Create the memory bank the first time. If it already exists, carry on."""
    if bank_id in _ready_banks:
        return
    try:
        client.create_bank(
            bank_id=bank_id,
            name="WasteWise canteen",
            mission=(
                "Remember canteen food preparation, sales and waste so we can "
                "suggest better portion amounts and spot wasteful dishes."
            ),
        )
    except Exception as error:
        status = getattr(error, "status", None)
        # Wrong key or no network must stop us. Anything else usually means
        # "bank already exists", and retain/recall will show any real problem.
        if status in (401, 403) or isinstance(error, (OSError, asyncio.TimeoutError)):
            raise
    _ready_banks.add(bank_id)


def check_connection():
    """Ask Hindsight for its version. Returns the version text if it answers."""

    def work(client, bank_id):
        return str(client.get_version().api_version)

    return _run("connect", work)


def retain_records(records, progress=None, batch_size=10):
    """RETAIN: save every canteen row as a memory. Returns how many were saved.

    progress: optional function called as progress(done, total) after each batch.
    """
    items = build_memory_items(records)
    if not items:
        raise HindsightMemoryError("There are no canteen records to save.")

    def work(client, bank_id):
        _ensure_bank(client, bank_id)
        done = 0
        for start in range(0, len(items), batch_size):
            chunk = items[start : start + batch_size]
            client.retain_batch(bank_id=bank_id, items=chunk)
            done += len(chunk)
            if progress:
                progress(done, len(items))
        return done

    return _run("save the canteen records", work)


def retain_memory(text):
    """RETAIN: store one canteen observation (for example a staff note)."""
    text = (text or "").strip()
    if not text:
        raise HindsightMemoryError("Type a note first.")

    def work(client, bank_id):
        _ensure_bank(client, bank_id)
        client.retain(bank_id=bank_id, content=text, context="Canteen staff note")
        return True

    return _run("save the note", work)


def recall_memories(question, max_results=10):
    """RECALL: search the bank. Returns a list of dicts: text, type, when.

    The list is empty when Hindsight has nothing related. That is a real
    answer, not an error, and the caller should tell the user.
    """
    question = (question or "").strip()
    if not question:
        raise HindsightMemoryError("Type a question first.")

    def work(client, bank_id):
        response = client.recall(bank_id=bank_id, query=question, budget="mid", max_tokens=2048)
        found = []
        for item in (response.results or [])[:max_results]:
            when = str(item.occurred_start)[:10] if item.occurred_start else ""
            found.append({"text": item.text, "type": item.type or "", "when": when})
        return found

    return _run("recall memories", work)


def reflect_memories(question):
    """REFLECT: let Hindsight think over saved memories and answer.

    Returns a dict: text (the answer) and memories (the saved facts it used).
    If memories is empty, Hindsight had nothing to base the answer on.
    """
    question = (question or "").strip()
    if not question:
        raise HindsightMemoryError("Type a question first.")

    def work(client, bank_id):
        response = client.reflect(
            bank_id=bank_id,
            query=question,
            budget="low",
            include_facts=True,
            context=(
                "This memory bank holds a college canteen's daily records of food "
                "prepared, sold and wasted. Give practical advice for preparing "
                "the right amount of food."
            ),
        )
        used = []
        if response.based_on and response.based_on.memories:
            used = [fact.text for fact in response.based_on.memories if fact.text]
        return {"text": (response.text or "").strip(), "memories": used}

    return _run("reflect on the memories", work)
