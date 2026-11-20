# Quotes

A personal collection of quotes, plus a daily job that picks one and publishes it for home-screen widgets.

## How it works

- [`quotes.md`](quotes.md) is the collection. Add quotes by appending to it.
- Every day at 04:00 Bolivia time, the [workflow](.github/workflows/daily.yml) runs [`scripts/pick.py`](scripts/pick.py). It picks one quote, records it in `history.json` and publishes it to GitHub Pages. No quote repeats until all the others have been shown.
- Widgets read the published files:

| File | Contents |
|---|---|
| `today.json` | Today's quote: `text`, `short`, `paragraphs`, `author`, `source`, `tags`, `date` |
| `widget.png` | Today's quote drawn as a card (1140×600, transparent corners), for image widgets |
| `today.txt` | Today's quote as plain text |
| `quotes.json` | Every quote |
| `history.json` | Which quote was shown on which day |
| `index.html` | A page showing today's quote |

Base URL: <https://alexpizarroj.github.io/quotes/>

## Getting a different quote today

Run the workflow by hand: on GitHub, open **Actions → Quote of the day → Run workflow** and leave "Pick a different quote for today" ticked. From a terminal:

```bash
gh workflow run daily.yml -R alexpizarroj/quotes
```

Each run replaces today's quote with one not yet shown today. The widgets pick it up on their next refresh: up to 30 minutes on the Mac, up to an hour on Android.

## Adding a quote

Append a block to `quotes.md`, separated from the previous one by a `---` line:

```markdown
Quote text, with line breaks as they should be displayed.

— Author, optional source #topic #topic
```

Spanish quotes get a `#es` tag. Check the file with `python3 scripts/pick.py --check`.

## Development

The scripts need only Python's standard library to run. The checks use [uv](https://docs.astral.sh/uv/):

```bash
uv run ruff check .          # lint
uv run ruff format .         # format
uv run ty check              # types
uv run pytest                # tests, with 100% coverage required
```

The [Checks workflow](.github/workflows/checks.yml) runs all four on every push. The tests in [`tests/test_pick.py`](tests/test_pick.py) describe the picker's behaviour: what counts as a quote, which quote is chosen each day, how a reroll behaves and what gets published.

## Widgets

| Mac (Übersicht) | Android (KWGT) |
|---|---|
| <img src="docs/mac-widget.png" alt="Quote of the day card above the native macOS desktop widgets" width="300"> | <img src="docs/android-widget.png" alt="Quote of the day card on an Android home screen" width="420"> |

- **Mac:** [`widgets/mac/quote-of-the-day.jsx`](widgets/mac/quote-of-the-day.jsx), an Übersicht widget.
- **Android:** [`widgets/android/README.md`](widgets/android/README.md), a KWGT widget.
