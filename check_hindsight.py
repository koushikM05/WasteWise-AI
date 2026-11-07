"""Check that Hindsight really works with your key, using the same code as the app.

Run with:  python check_hindsight.py

It tests, in order: your settings, the connection, RETAIN, RECALL and REFLECT.
It saves a test note and your sample canteen records into your memory bank.
It reads your key from .env (never type keys into this file) and never prints it.
Send me everything it prints if any step says FAILED.
"""

import sys
import time

import hindsight_memory as hm
from data_manager import DataError, load_records

results = []


def report(name, passed, detail=""):
    results.append((name, passed))
    print(f"   {'OK    ' if passed else 'FAILED'} {name}" + (f" - {detail}" if detail else ""))


def main():
    settings = hm.get_settings()
    print("Base URL :", settings["base_url"])
    print("Bank id  :", settings["bank_name"])

    print("\n[1] Canteen data (works without a key)")
    try:
        records, warnings = load_records()
        items = hm.build_memory_items(records)
        report("Read sample_data.csv", True, f"{len(records)} rows -> {len(items)} memories")
        print("   Example memory:", items[0]["content"])
    except DataError as error:
        records = None
        report("Read sample_data.csv", False, str(error))

    print("\n[2] Settings")
    problem = hm.setup_problem()
    report("API key and settings in .env", problem is None, problem or "key found (hidden)")
    if problem:
        return finish()

    print("\n[3] Connect to Hindsight")
    try:
        report("Connection", True, f"API version {hm.check_connection()}")
    except hm.HindsightMemoryError as error:
        report("Connection", False, str(error))
        return finish()

    print("\n[4] RETAIN - save memories")
    try:
        hm.retain_memory("Test note from check_hindsight.py: sports day means fewer students at lunch.")
        report("Retain one note", True)
    except hm.HindsightMemoryError as error:
        report("Retain one note", False, str(error))
        return finish()

    if records is not None:
        try:
            saved = hm.retain_records(
                records,
                progress=lambda done, total: print(f"   ...saved {done} of {total}", end="\r"),
            )
            print()
            report("Retain canteen records", True, f"{saved} records accepted")
        except hm.HindsightMemoryError as error:
            print()
            report("Retain canteen records", False, str(error))

    print("\n[5] RECALL - search memories")
    question = "Which dishes were wasted the most?"
    found = []
    for attempt, wait in enumerate((10, 25), start=1):
        print(f"   Waiting {wait} seconds for Hindsight to finish processing (try {attempt})...")
        time.sleep(wait)
        try:
            found = hm.recall_memories(question)
        except hm.HindsightMemoryError as error:
            report("Recall", False, str(error))
            return finish()
        if found:
            break
    report("Recall returned memories", bool(found), f"{len(found)} found" if found else "none found yet")
    for item in found[:5]:
        print("    -", item["text"])

    print("\n[6] REFLECT - think over memories")
    try:
        answer = hm.reflect_memories("Which dishes are wasted the most, and how should we change how much we prepare?")
        report("Reflect returned an answer", bool(answer["text"]))
        print("   Answer:", answer["text"])
        report(
            "Reflect used saved memories",
            bool(answer["memories"]),
            f"{len(answer['memories'])} memories listed" if answer["memories"] else "no supporting memories listed",
        )
    except hm.HindsightMemoryError as error:
        report("Reflect", False, str(error))

    finish()


def finish():
    print("\n--- Summary ---")
    for name, passed in results:
        print(f"{'OK    ' if passed else 'FAILED'} {name}")
    failed = [name for name, passed in results if not passed]
    print("\nAll steps passed." if not failed else f"\n{len(failed)} step(s) failed. Send me this whole output.")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
