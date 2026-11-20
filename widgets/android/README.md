# Android home-screen widget (KWGT)

1. Install **KWGT Kustom Widget Maker** from the Play Store.
2. Long-press the home screen, add a KWGT widget (4×2 or larger) and tap it to edit.
3. Add a **Text** item and set its text to this formula:

   ```
   $wg("https://alexpizarroj.github.io/quotes/today.json", json, .text)$
   ```

4. Add a second, smaller **Text** item for the author:

   ```
   $wg("https://alexpizarroj.github.io/quotes/today.json", json, .author)$
   ```

5. For a small widget, use `.short` instead of `.text`: it is a one-line version of at most 110 characters.

KWGT refreshes web content on its own schedule (Settings → Advanced → update mode), so the new quote can take a while to appear in the morning.
