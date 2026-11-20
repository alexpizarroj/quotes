"""Behaviour of the quote picker: what it reads, which quote it chooses, and what it publishes."""

import datetime
import json
from pathlib import Path

import pytest

import pick


def collection(*blocks: str) -> str:
    """A quotes.md with an introduction followed by the given blocks."""
    return "\n\n---\n\n".join(["# Quotes\n\nAn introduction.", *blocks]) + "\n"


def numbered_quotes(count: int) -> list[pick.Quote]:
    quotes, problems = pick.parse(collection(*(f"Quote {n}\n\n— Author {n}" for n in range(count))))
    assert not problems
    return quotes


def show(quotes: list[pick.Quote], history: list[pick.HistoryEntry], date: str, **options: bool):
    """Pick for a date and record it, as one run of the script does."""
    quote, skipped = pick.pick(quotes, history, date, **options)
    return quote, pick.record(history, date, quote, skipped)


def day(number: int) -> str:
    return (datetime.date(2030, 1, 1) + datetime.timedelta(days=number)).isoformat()


class TestReadingQuotes:
    def test_reads_text_author_source_and_tags(self):
        quotes, problems = pick.parse(
            collection("Useful and joyful.\n\n— James Clear, 3-2-1 Newsletter #purpose #happiness")
        )

        assert problems == []
        assert len(quotes) == 1
        assert quotes[0]["text"] == "Useful and joyful."
        assert quotes[0]["author"] == "James Clear"
        assert quotes[0]["source"] == "3-2-1 Newsletter"
        assert quotes[0]["tags"] == ["purpose", "happiness"]

    def test_source_and_tags_are_optional(self):
        quotes, _ = pick.parse(collection("Success loves speed\n\n— Anonymous"))

        assert quotes[0]["author"] == "Anonymous"
        assert quotes[0]["source"] == ""
        assert quotes[0]["tags"] == []

    def test_keeps_line_breaks_and_blank_lines_inside_a_quote(self):
        text = "First line\nSecond line\n\nNew paragraph"

        quotes, _ = pick.parse(collection(f"{text}\n\n— Someone"))

        assert quotes[0]["text"] == text

    def test_reads_every_quote_in_order(self):
        quotes, _ = pick.parse(collection("One\n\n— A", "Two\n\n— B", "Three\n\n— C"))

        assert [quote["text"] for quote in quotes] == ["One", "Two", "Three"]

    def test_the_introduction_is_not_a_quote(self):
        quotes, problems = pick.parse(collection())

        assert quotes == []
        assert problems == []

    def test_a_quote_keeps_its_identity_when_its_attribution_changes(self):
        before, _ = pick.parse(collection("Same words\n\n— Anonymous"))
        after, _ = pick.parse(collection("Same words\n\n— Alex Hormozi, a tweet #work"))

        assert before[0]["id"] == after[0]["id"]

    def test_different_quotes_have_different_identities(self):
        quotes = numbered_quotes(20)

        assert len({quote["id"] for quote in quotes}) == 20

    def test_reports_a_block_without_an_author_line(self):
        quotes, problems = pick.parse(collection("Good\n\n— A", "Forgot the author"))

        assert [quote["text"] for quote in quotes] == ["Good"]
        assert len(problems) == 1
        assert "Forgot the author" in problems[0]

    def test_reports_a_quote_with_no_text(self):
        _, problems = pick.parse(collection("— Lonely Author"))

        assert len(problems) == 1
        assert "missing" in problems[0]

    def test_reports_an_author_line_with_only_tags(self):
        _, problems = pick.parse(collection("Words\n\n— #tag"))

        assert len(problems) == 1

    def test_reports_a_quote_entered_twice_once(self):
        _, problems = pick.parse(collection("Twice\n\n— A", "Other\n\n— B", "Twice\n\n— C"))

        assert len(problems) == 1
        assert "duplicate" in problems[0]
        assert "Twice" in problems[0]


class TestShortVersion:
    def test_a_short_quote_is_unchanged(self):
        assert pick.shorten("Success loves speed") == "Success loves speed"

    def test_line_breaks_become_spaces(self):
        assert pick.shorten("One\nTwo\n\nThree") == "One Two Three"

    def test_a_long_quote_is_cut_at_a_word_with_an_ellipsis(self):
        text = "word " * 100

        short = pick.shorten(text, limit=22)

        assert short == "word word word word…"

    def test_a_long_quote_never_exceeds_the_limit_plus_the_ellipsis(self):
        short = pick.shorten("abcdefghij " * 50)

        assert len(short) <= pick.SHORT_LIMIT + 1
        assert short.endswith("…")

    def test_punctuation_before_the_ellipsis_is_dropped(self):
        assert pick.shorten("First part, second part", limit=12) == "First part…"

    def test_parsed_quotes_carry_their_short_version(self):
        quotes, _ = pick.parse(collection("One\nTwo\n\n— A"))

        assert quotes[0]["short"] == "One Two"


class TestDailyPick:
    def test_the_same_day_always_gets_the_same_quote(self):
        quotes = numbered_quotes(10)
        first, history = show(quotes, [], day(0))

        again, history = show(quotes, history, day(0))

        assert again == first
        assert len(history) == 1

    def test_the_first_pick_does_not_depend_on_when_it_runs(self):
        quotes = numbered_quotes(10)

        assert pick.pick(quotes, [], day(0)) == pick.pick(quotes, [], day(0))

    def test_no_quote_repeats_until_all_have_been_shown(self):
        quotes = numbered_quotes(12)
        history: list[pick.HistoryEntry] = []
        shown = []

        for number in range(12):
            quote, history = show(quotes, history, day(number))
            shown.append(quote["id"])

        assert sorted(shown) == sorted(quote["id"] for quote in quotes)

    def test_a_second_round_also_shows_every_quote_once(self):
        quotes = numbered_quotes(5)
        history: list[pick.HistoryEntry] = []
        shown = []

        for number in range(10):
            quote, history = show(quotes, history, day(number))
            shown.append(quote["id"])

        assert len(set(shown[:5])) == 5
        assert len(set(shown[5:])) == 5

    def test_a_newly_added_quote_is_shown_before_any_repeat(self):
        quotes = numbered_quotes(6)
        history: list[pick.HistoryEntry] = []
        for number in range(5):
            _, history = show(quotes[:5], history, day(number))

        quote, _ = show(quotes, history, day(5))

        assert quote == quotes[5]

    def test_adding_a_quote_does_not_change_todays_pick(self):
        quotes = numbered_quotes(6)
        today, history = show(quotes[:5], [], day(0))

        after_adding, _ = show(quotes, history, day(0))

        assert after_adding == today

    def test_a_new_quote_is_picked_if_todays_was_removed(self):
        quotes = numbered_quotes(5)
        today, history = show(quotes, [], day(0))
        remaining = [quote for quote in quotes if quote != today]

        replacement, history = show(remaining, history, day(0))

        assert replacement in remaining
        assert [entry["id"] for entry in history] == [replacement["id"]]

    def test_history_stays_in_date_order_when_an_earlier_day_is_filled_in(self):
        quotes = numbered_quotes(5)
        _, history = show(quotes, [], day(3))

        _, history = show(quotes, history, day(1))

        assert [entry["date"] for entry in history] == [day(1), day(3)]

    def test_a_single_quote_is_shown_every_day(self):
        quotes = numbered_quotes(1)
        history: list[pick.HistoryEntry] = []

        for number in range(3):
            quote, history = show(quotes, history, day(number))
            assert quote == quotes[0]


class TestReroll:
    def test_gives_a_different_quote(self):
        quotes = numbered_quotes(10)
        first, history = show(quotes, [], day(0))

        second, history = show(quotes, history, day(0), reroll=True)

        assert second != first
        assert len(history) == 1

    def test_the_new_quote_then_stays_for_the_day(self):
        quotes = numbered_quotes(10)
        _, history = show(quotes, [], day(0))
        rerolled, history = show(quotes, history, day(0), reroll=True)

        later, _ = show(quotes, history, day(0))

        assert later == rerolled

    def test_repeated_rerolls_go_through_every_other_quote(self):
        quotes = numbered_quotes(8)
        first, history = show(quotes, [], day(0))
        seen = [first["id"]]

        for _ in range(7):
            quote, history = show(quotes, history, day(0), reroll=True)
            seen.append(quote["id"])

        assert sorted(seen) == sorted(quote["id"] for quote in quotes)

    def test_still_changes_the_quote_after_every_quote_was_seen_today(self):
        quotes = numbered_quotes(3)
        current, history = show(quotes, [], day(0))

        for _ in range(10):
            previous = current
            current, history = show(quotes, history, day(0), reroll=True)
            assert current != previous

    def test_on_a_day_with_no_pick_yet_just_picks(self):
        quotes = numbered_quotes(5)

        quote, history = show(quotes, [], day(0), reroll=True)

        assert quote in quotes
        assert "skipped" not in history[0]

    def test_with_a_single_quote_keeps_showing_it(self):
        quotes = numbered_quotes(1)
        _, history = show(quotes, [], day(0))

        quote, _ = show(quotes, history, day(0), reroll=True)

        assert quote == quotes[0]

    def test_a_skipped_quote_does_not_come_back_before_unseen_ones(self):
        quotes = numbered_quotes(6)
        skipped, history = show(quotes, [], day(0))
        kept, history = show(quotes, history, day(0), reroll=True)
        shown = []

        for number in range(1, 5):
            quote, history = show(quotes, history, day(number))
            shown.append(quote["id"])

        assert skipped["id"] not in shown
        assert kept["id"] not in shown
        assert len(set(shown)) == 4


class TestLocalDate:
    def test_the_day_rolls_over_at_midnight_in_bolivia_not_utc(self):
        just_after_midnight_utc = datetime.datetime(2026, 11, 21, 3, 0, tzinfo=datetime.UTC)
        just_after_midnight_bolivia = datetime.datetime(2026, 11, 21, 4, 0, tzinfo=datetime.UTC)

        assert pick.local_date(just_after_midnight_utc) == "2026-11-20"
        assert pick.local_date(just_after_midnight_bolivia) == "2026-11-21"

    def test_defaults_to_now(self):
        today = pick.local_date()

        assert datetime.date.fromisoformat(today)


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """A folder holding a small quotes.md, standing in for the repository."""
    (tmp_path / "quotes.md").write_text(
        collection(
            "Line one\nLine two\n\n— Ada Lovelace, Notes #maths",
            "Second quote\n\n— Grace Hopper",
            "Third quote\n\n— Alan Turing",
        )
    )
    return tmp_path


def run(root: Path, *arguments: str) -> int:
    return pick.main(["--root", str(root), *arguments])


def published(root: Path, name: str):
    return json.loads((root / "site" / name).read_text())


class TestCommandLine:
    def test_publishes_todays_quote_for_the_widgets(self, root: Path):
        assert run(root, "--date", "2030-05-01") == 0

        today = published(root, "today.json")
        assert today["date"] == "2030-05-01"
        assert today["text"] in {"Line one\nLine two", "Second quote", "Third quote"}
        assert today["paragraphs"] == today["text"].split("\n")
        assert {"author", "source", "tags", "short", "id"} <= today.keys()

    def test_publishes_the_plain_text_version(self, root: Path):
        run(root, "--date", "2030-05-01")

        today = published(root, "today.json")
        text = (root / "site" / "today.txt").read_text()
        assert text == f"{today['text']}\n\n— {today['author']}\n"

    def test_publishes_the_whole_collection_and_the_history(self, root: Path):
        run(root, "--date", "2030-05-01")
        run(root, "--date", "2030-05-02")

        assert [quote["author"] for quote in published(root, "quotes.json")] == [
            "Ada Lovelace",
            "Grace Hopper",
            "Alan Turing",
        ]
        assert [entry["date"] for entry in published(root, "history.json")] == [
            "2030-05-01",
            "2030-05-02",
        ]

    def test_publishes_the_pages(self, root: Path):
        run(root, "--date", "2030-05-01")

        today = published(root, "today.json")
        card = (root / "site" / "card.html").read_text()
        assert "__QUOTE__" not in card
        assert json.dumps(today["author"]) in card
        assert "today.json" in (root / "site" / "index.html").read_text()

    def test_quote_text_cannot_break_out_of_the_card_page(self, root: Path):
        (root / "quotes.md").write_text(collection("</script><b>bold</b>\n\n— Mallory"))

        run(root, "--date", "2030-05-01")

        card = (root / "site" / "card.html").read_text()
        assert "</script><b>" not in card
        assert published(root, "today.json")["text"] == "</script><b>bold</b>"

    def test_running_twice_on_one_day_keeps_the_quote(self, root: Path):
        run(root, "--date", "2030-05-01")
        first = published(root, "today.json")

        run(root, "--date", "2030-05-01")

        assert published(root, "today.json") == first

    def test_remembers_picks_between_runs(self, root: Path):
        shown = []
        for date in ("2030-05-01", "2030-05-02", "2030-05-03"):
            run(root, "--date", date)
            shown.append(published(root, "today.json")["id"])

        assert len(set(shown)) == 3

    def test_reroll_replaces_todays_quote(self, root: Path):
        run(root, "--date", "2030-05-01")
        first = published(root, "today.json")

        assert run(root, "--date", "2030-05-01", "--reroll") == 0

        assert published(root, "today.json")["id"] != first["id"]
        assert published(root, "history.json")[0]["skipped"] == [first["id"]]

    def test_uses_todays_date_by_default(self, root: Path):
        run(root)

        assert published(root, "today.json")["date"] == pick.local_date()

    def test_reports_the_pick(self, root: Path, capsys: pytest.CaptureFixture[str]):
        run(root, "--date", "2030-05-01")

        today = published(root, "today.json")
        output = capsys.readouterr().out
        assert "2030-05-01" in output
        assert today["author"] in output

    def test_check_accepts_a_valid_collection_without_publishing(
        self, root: Path, capsys: pytest.CaptureFixture[str]
    ):
        assert run(root, "--check") == 0

        assert "3 quotes OK" in capsys.readouterr().out
        assert not (root / "site").exists()
        assert not (root / "history.json").exists()

    def test_refuses_a_collection_with_problems(
        self, root: Path, capsys: pytest.CaptureFixture[str]
    ):
        (root / "quotes.md").write_text(collection("Fine\n\n— A", "No author here"))

        assert run(root, "--date", "2030-05-01") == 1

        assert "No author here" in capsys.readouterr().err
        assert not (root / "site").exists()

    def test_refuses_an_empty_collection(self, root: Path, capsys: pytest.CaptureFixture[str]):
        (root / "quotes.md").write_text(collection())

        assert run(root, "--check") == 1

        assert "no quotes" in capsys.readouterr().err


def test_the_real_collection_is_valid():
    quotes, problems = pick.parse((pick.REPO_ROOT / "quotes.md").read_text())

    assert problems == []
    assert quotes
