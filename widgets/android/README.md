# Android home-screen widget (KWGT)

The phone widget shows `widget.png`, an image of today's quote drawn with the same card design as the Mac widget. The workflow renders it once a day, so there is nothing to style on the phone.

1. Install **KWGT Kustom Widget Maker** from the Play Store.
2. Long-press the home screen, add a KWGT widget and resize it to the full width of the screen and about two rows tall (4×2). Tap it to edit.
3. Delete any items already in the widget.
4. Add an **Image** item (the + button, then Image).
5. In the item's **Bitmap** field, tick the checkbox on the right and tap the calculator icon to switch the field to a formula. Enter:

   ```
   https://alexpizarroj.github.io/quotes/widget.png?t=$df(yyyyMMddHH)$
   ```

   The `?t=` part changes every hour, which makes KWGT download the image again instead of keeping yesterday's.
6. Increase the item's **Size** until the card fills the widget's width.
7. Save with the disk icon.

## Text instead of an image

`today.json` has the same quote as text, if you would rather build the layout in KWGT:

```
$wg("https://alexpizarroj.github.io/quotes/today.json", json, .text)$
$wg("https://alexpizarroj.github.io/quotes/today.json", json, .author)$
```

`.short` is a one-line version of at most 110 characters.
