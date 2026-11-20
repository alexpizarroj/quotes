#!/usr/bin/env python3
"""Pick the quote of the day and write the files the widgets read.

Usage: pick.py [--date YYYY-MM-DD] [--check]

Reads quotes.md and history.json, writes history.json and site/.
The pick for a given date is made once and then reused, so re-running is safe.
A quote is only repeated after every other quote has been shown.
"""
import argparse
import datetime
import hashlib
import json
import pathlib
import random
import sys
import zoneinfo

ROOT = pathlib.Path(__file__).resolve().parent.parent
TIMEZONE = zoneinfo.ZoneInfo("America/La_Paz")
SHORT_LIMIT = 110


def parse(markdown):
    quotes, problems = [], []
    blocks = [b.strip() for b in markdown.split("\n---\n") if b.strip()]
    for number, block in enumerate(blocks, 1):
        lines = block.splitlines()
        if not lines[-1].startswith("— "):
            if number > 1:
                problems.append(f"block {number} has no '— Author' line: {lines[0][:50]!r}")
            continue
        text = "\n".join(lines[:-1]).strip()
        words = lines[-1][2:].split()
        tags = [w[1:] for w in words if w.startswith("#")]
        byline = " ".join(w for w in words if not w.startswith("#"))
        author, _, source = byline.partition(", ")
        if not text or not author:
            problems.append(f"block {number} is missing its text or author")
            continue
        quotes.append({
            "id": hashlib.sha1(text.encode()).hexdigest()[:10],
            "text": text,
            "short": shorten(text),
            "author": author,
            "source": source,
            "tags": tags,
        })
    ids = [q["id"] for q in quotes]
    for q in quotes:
        if ids.count(q["id"]) > 1:
            problems.append(f"duplicate quote: {q['text'][:50]!r}")
    return quotes, sorted(set(problems))


def shorten(text):
    """One-line version for small widgets."""
    flat = " ".join(text.split())
    if len(flat) <= SHORT_LIMIT:
        return flat
    return flat[:SHORT_LIMIT].rsplit(" ", 1)[0].rstrip(",.:;") + "…"


def pick(quotes, history, date):
    by_id = {q["id"]: q for q in quotes}
    for entry in history:
        if entry["date"] == date and entry["id"] in by_id:
            return by_id[entry["id"]]
    last_shown = {e["id"]: e["date"] for e in history if e["date"] < date}
    oldest = min(last_shown.get(q["id"], "") for q in quotes)
    candidates = [q for q in quotes if last_shown.get(q["id"], "") == oldest]
    return random.Random(date).choice(candidates)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=datetime.datetime.now(TIMEZONE).date().isoformat())
    parser.add_argument("--check", action="store_true", help="only validate quotes.md")
    args = parser.parse_args()

    quotes, problems = parse((ROOT / "quotes.md").read_text())
    for problem in problems:
        print(f"quotes.md: {problem}", file=sys.stderr)
    if problems or not quotes:
        sys.exit(1)
    if args.check:
        print(f"{len(quotes)} quotes OK")
        return

    history_path = ROOT / "history.json"
    history = json.loads(history_path.read_text()) if history_path.exists() else []
    today = pick(quotes, history, args.date)
    history = [e for e in history if e["date"] != args.date]
    history.append({"date": args.date, "id": today["id"], "author": today["author"], "short": today["short"]})
    history.sort(key=lambda e: e["date"])
    history_path.write_text(json.dumps(history, indent=1, ensure_ascii=False) + "\n")

    site = ROOT / "site"
    site.mkdir(exist_ok=True)
    payload = {"date": args.date, **today, "paragraphs": today["text"].split("\n")}
    dump = lambda data: json.dumps(data, indent=1, ensure_ascii=False) + "\n"
    (site / "today.json").write_text(dump(payload))
    (site / "today.txt").write_text(f"{today['text']}\n\n— {today['author']}\n")
    (site / "quotes.json").write_text(dump(quotes))
    (site / "history.json").write_text(dump(history))
    (site / "index.html").write_text((ROOT / "scripts" / "index.html").read_text())
    print(f"{args.date}: {today['short']} — {today['author']}")


if __name__ == "__main__":
    main()
