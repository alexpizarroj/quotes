// ScriptWidget widget: shows the quote of the day as a native macOS widget.
// Install with scripts/install_mac_widget.py, then add a ScriptWidget widget to the desktop
// and pick "Quote of the Day" in its settings.

const URL = "https://alexpizarroj.github.io/quotes/today.json";
const PAGE = "https://alexpizarroj.github.io/quotes/";

// Fonts that ship with macOS, by PostScript name. `font="custom,<name>,<size>"` sets an exact
// size; ScriptWidget supports it in its font parser but doesn't document it yet.
const QUOTE_FONT = "IowanOldStyle-Roman";
const DETAIL_FONT = "AvenirNext-Medium";

// A dark, warm card that suits the sunset wallpaper.
const BACKGROUND = "#2b1a0c";
const TEXT = "#fdf6ec";
const MUTED = "#c9b8a3";
const PADDING = 16;

// Approximate macOS widget sizes in points, and the biggest quote text that looks right in each.
const SIZES = {
  small: { width: 158, height: 158, largest: 14 },
  medium: { width: 338, height: 158, largest: 16 },
  large: { width: 338, height: 354, largest: 20 },
  extraLarge: { width: 715, height: 354, largest: 24 },
};
const SMALLEST = 10;

const family = String($getenv("widget-size") || "medium");
const size = SIZES[family] || SIZES.medium;

// The label and author scale with the quote, so they never look tiny next to it.
const labelSize = (points) => Math.max(9, Math.round(points * 0.6));
const bylineSize = (points) => Math.max(10, Math.round(points * 0.72));

// Estimates how tall the quote is at a size, wrapping each paragraph to the widget's width.
// Text averages about half its point size per character; the extra covers word wrapping.
function quoteHeight(paragraphs, points) {
  const width = size.width - 2 * PADDING;
  const perLine = Math.max(1, Math.floor(width / (points * 0.52)));
  const lines = paragraphs.reduce((total, line) => total + Math.max(1, Math.ceil(line.length / perLine)), 0);
  return lines * points * 1.3;
}

// Picks the biggest size the whole card fits at, keeping the label when there is room for it.
function layout(paragraphs) {
  for (const withLabel of [true, false]) {
    for (let points = size.largest; points >= SMALLEST; points--) {
      const label = withLabel ? labelSize(points) * 1.3 + 6 : 0;
      const byline = bylineSize(points) * 1.3 + 6;
      if (quoteHeight(paragraphs, points) + label + byline <= size.height - 2 * PADDING) {
        return { points, withLabel };
      }
    }
  }
  return { points: SMALLEST, withLabel: false };
}

const font = (name, points) => `custom,${name},${points}`;

let quote = null;
try {
  quote = JSON.parse(await fetch(URL));
} catch (e) {
  quote = null;
}

if (!quote || !Array.isArray(quote.paragraphs)) {
  $render(
    <vstack frame="max" padding={String(PADDING)} background={BACKGROUND} alignment="leading">
      <text font={font(DETAIL_FONT, 11)} color={MUTED}>Quote of the day is unavailable right now.</text>
    </vstack>
  );
} else {
  const paragraphs = quote.paragraphs.filter((line) => line);
  const { points, withLabel } = layout(paragraphs);
  const byline = "— " + quote.author + (quote.source ? ", " + quote.source : "");
  $render(
    <vstack frame="max" padding={String(PADDING)} spacing="6" background={BACKGROUND} alignment="leading" linkurl={PAGE}>
      {withLabel ? (
        <text font={font(DETAIL_FONT, labelSize(points))} color={MUTED}>QUOTE OF THE DAY</text>
      ) : null}
      {paragraphs.map((line) => (
        <text font={font(QUOTE_FONT, points)} color={TEXT}>{line}</text>
      ))}
      <text font={font(DETAIL_FONT, bylineSize(points))} color={MUTED}>{byline}</text>
    </vstack>
  );
}
