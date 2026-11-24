# Quotes

A personal collection of quotes, plus a daily job that picks one and publishes it for home-screen widgets.

## How it works

- [`quotes.md`](quotes.md) is the collection. Add quotes by appending to it.
- Every hour, the [workflow](.github/workflows/daily.yml) runs [`scripts/pick.py`](scripts/pick.py). The first run of the day, Bolivia time, picks one quote, records it in `history.json` and publishes it to GitHub Pages; later runs reuse that pick. No quote repeats until all the others have been shown.
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

The [Checks workflow](.github/workflows/checks.yml) runs all four on every push.

## Widgets

| Mac (ScriptWidget) | Android (KWGT) |
|---|---|
| <img src="docs/mac-widget.png" alt="Quote of the day as a large macOS desktop widget, above the Weather, Stocks and Calendar widgets" width="300"> | <img src="docs/android-widget.png" alt="Quote of the day card on an Android home screen" width="420"> |

- **Mac:** [`widgets/scriptwidget/quote-of-the-day`](widgets/scriptwidget/quote-of-the-day), a native desktop widget for the [ScriptWidget](https://github.com/everettjf/ScriptWidget) app. It comes in small, medium, large and extra large, and picks the biggest text size that fits the quote. **Large** is the recommended size: most quotes fit comfortably, as in the screenshot. Set it up with one command; it needs macOS 26 or later, Homebrew and Python:

  ```bash
  python3 -c "$(curl -fsSL https://raw.githubusercontent.com/alexpizarroj/quotes/main/scripts/install_mac_widget.py)"
  ```

  Or, from a clone, `python3 scripts/install_mac_widget.py`. It installs the ScriptWidget command-line tool, opens the app's App Store page if the app is missing (install it, open it once and run the command again), then checks the widget and copies it into the app's iCloud library, so it also reaches your other Macs. Run it again after changing the widget to update it. Adding the widget to the desktop is the one step macOS can't automate; the script prints how. To preview changes to the widget, run `scriptwidget preview widgets/scriptwidget/quote-of-the-day`.
- **Android:** [`widgets/android/README.md`](widgets/android/README.md), a KWGT widget.
