#!/usr/bin/env python3
"""Pick the quote of the day and write the files the widgets read.

Usage: pick.py [--date YYYY-MM-DD] [--reroll] [--check] [--root DIR]

Reads quotes.md and history.json from the root folder, writes history.json and site/.
The pick for a given date is made once and then reused, so re-running is safe.
--reroll replaces it with a quote not yet shown that day.
A quote is only repeated after every other quote has been shown.
"""

import argparse
import datetime
import hashlib
import json
import random
import sys
import zoneinfo
from pathlib import Path
from typing import NotRequired, TypedDict

TIMEZONE = zoneinfo.ZoneInfo("America/La_Paz")
SHORT_LIMIT = 110
SCRIPTS = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS.parent


class Quote(TypedDict):
    id: str
    text: str
    short: str
    author: str
    source: str
    tags: list[str]


class HistoryEntry(TypedDict):
    date: str
    id: str
    author: str
    short: str
    skipped: NotRequired[list[str]]


def parse(markdown: str) -> tuple[list[Quote], list[str]]:
    """Read the quotes out of quotes.md, along with any problems found in it.

    Blocks are separated by a `---` line. A quote block ends with `— Author[, source] #tag ...`.
    The first block may be a plain introduction; any later block without that line is a problem.
    """
    quotes: list[Quote] = []
    problems: list[str] = []
    blocks = [block.strip() for block in markdown.split("\n---\n") if block.strip()]
    for number, block in enumerate(blocks, 1):
        lines = block.splitlines()
        if not lines[-1].startswith("— "):
            if number > 1:
                problems.append(f"block {number} has no '— Author' line: {lines[0][:50]!r}")
            continue
        text = "\n".join(lines[:-1]).strip()
        words = lines[-1][2:].split()
        tags = [word[1:] for word in words if word.startswith("#")]
        byline = " ".join(word for word in words if not word.startswith("#"))
        author, _, source = byline.partition(", ")
        if not text or not author:
            problems.append(f"block {number} is missing its text or author")
            continue
        quotes.append(
            {
                "id": hashlib.sha1(text.encode()).hexdigest()[:10],
                "text": text,
                "short": shorten(text),
                "author": author,
                "source": source,
                "tags": tags,
            }
        )
    ids = [quote["id"] for quote in quotes]
    problems.extend(
        f"duplicate quote: {quote['text'][:50]!r}" for quote in quotes if ids.count(quote["id"]) > 1
    )
    return quotes, sorted(set(problems))


def shorten(text: str, limit: int = SHORT_LIMIT) -> str:
    """One-line version of a quote for small widgets, cut at a word boundary."""
    flat = " ".join(text.split())
    if len(flat) <= limit:
        return flat
    return flat[:limit].rsplit(" ", 1)[0].rstrip(",.:;") + "…"


def pick(
    quotes: list[Quote], history: list[HistoryEntry], date: str, *, reroll: bool = False
) -> tuple[Quote, list[str]]:
    """Choose the quote for a date. Returns it with the ids rerolled away from that day."""
    by_id = {quote["id"]: quote for quote in quotes}
    entry = next((e for e in history if e["date"] == date), None)
    skipped = list(entry.get("skipped", [])) if entry else []
    if entry and entry["id"] in by_id:
        if not reroll:
            return by_id[entry["id"]], skipped
        skipped.append(entry["id"])
    # When each quote was last on screen; quotes skipped by a reroll count as shown that day.
    last_shown: dict[str, str] = {}
    for past in history:
        if past["date"] < date:
            for quote_id in [*past.get("skipped", []), past["id"]]:
                last_shown[quote_id] = past["date"]
    pool = (
        [quote for quote in quotes if quote["id"] not in skipped]
        or [quote for quote in quotes if quote["id"] != skipped[-1]]
        or quotes
    )
    oldest = min(last_shown.get(quote["id"], "") for quote in pool)
    candidates = [quote for quote in pool if last_shown.get(quote["id"], "") == oldest]
    return random.Random(f"{date}-{len(skipped)}").choice(candidates), skipped


def record(
    history: list[HistoryEntry], date: str, quote: Quote, skipped: list[str]
) -> list[HistoryEntry]:
    """Return the history with the date's entry set to this quote, ordered by date."""
    entry: HistoryEntry = {
        "date": date,
        "id": quote["id"],
        "author": quote["author"],
        "short": quote["short"],
    }
    if skipped:
        entry["skipped"] = skipped
    others = [past for past in history if past["date"] != date]
    return sorted([*others, entry], key=lambda past: past["date"])


def build_site(
    quotes: list[Quote],
    history: list[HistoryEntry],
    today: Quote,
    date: str,
    card_template: str,
) -> dict[str, str]:
    """The published data files and card page, by name."""
    payload = {"date": date, **today, "paragraphs": today["text"].split("\n")}
    # "</" is escaped so quote text can never close the card page's <script> element.
    embedded = to_json(payload).replace("</", "<\\/")
    return {
        "today.json": to_json(payload),
        "today.txt": f"{today['text']}\n\n— {today['author']}\n",
        "quotes.json": to_json(quotes),
        "history.json": to_json(history),
        "card.html": card_template.replace("__QUOTE__", embedded),
    }


def to_json(data: object) -> str:
    return json.dumps(data, indent=1, ensure_ascii=False) + "\n"


def local_date(now: datetime.datetime | None = None) -> str:
    """Today's date where the quotes are read, which decides when the day rolls over."""
    now = now or datetime.datetime.now(datetime.UTC)
    return now.astimezone(TIMEZONE).date().isoformat()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pick the quote of the day.")
    parser.add_argument("--date", default=local_date(), help="defaults to today in Bolivia")
    parser.add_argument("--check", action="store_true", help="only validate quotes.md")
    parser.add_argument("--reroll", action="store_true", help="replace the date's quote")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="folder with quotes.md")
    args = parser.parse_args(argv)

    quotes, problems = parse((args.root / "quotes.md").read_text())
    if not quotes and not problems:
        problems = ["no quotes found"]
    for problem in problems:
        print(f"quotes.md: {problem}", file=sys.stderr)
    if problems:
        return 1
    if args.check:
        print(f"{len(quotes)} quotes OK")
        return 0

    history_path = args.root / "history.json"
    history: list[HistoryEntry] = (
        json.loads(history_path.read_text()) if history_path.exists() else []
    )
    today, skipped = pick(quotes, history, args.date, reroll=args.reroll)
    history = record(history, args.date, today, skipped)
    history_path.write_text(to_json(history))

    site = args.root / "site"
    site.mkdir(exist_ok=True)
    files = build_site(quotes, history, today, args.date, (SCRIPTS / "card.html").read_text())
    files["index.html"] = (SCRIPTS / "index.html").read_text()
    for name, content in files.items():
        (site / name).write_text(content)
    print(f"{args.date}: {today['short']} — {today['author']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
