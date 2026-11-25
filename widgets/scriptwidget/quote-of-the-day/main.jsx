// ScriptWidget widget: shows the quote of the day as a native macOS widget.
// Install with scripts/install_mac_widget.py, then add a ScriptWidget widget to the desktop
// and pick "Quote of the Day" in its settings.

const URL = "https://alexpizarroj.github.io/quotes/today.json";
const PAGE = "https://alexpizarroj.github.io/quotes/";

// Fonts that ship with macOS, by PostScript name. `font="custom,<name>,<size>"` sets an exact
// size; ScriptWidget supports it in its font parser but doesn't document it yet.
// Each font's metrics come from Core Text, as fractions of the font size: how far a line reaches
// above and below its baseline, and how wide each character from " " to "~" is, in thousandths.
const QUOTE_FONT = {
  name: "IowanOldStyle-Roman",
  ascent: 1.0361,
  descent: 0.3291,
  widths: [
    278, 337, 331, 556, 556, 880, 831, 170, 419, 419, 454, 833, 278, 350, 278, 461, 556, 556, 556,
    556, 556, 556, 556, 556, 556, 556, 278, 278, 833, 833, 833, 470, 1000, 722, 622, 707, 781, 634,
    585, 742, 794, 340, 332, 693, 572, 910, 808, 802, 589, 802, 703, 541, 631, 787, 717, 1037, 711,
    659, 667, 419, 461, 419, 1000, 500, 500, 481, 556, 447, 562, 488, 320, 516, 586, 297, 274, 546,
    292, 880, 584, 551, 560, 558, 390, 443, 360, 588, 491, 775, 530, 486, 472, 419, 500, 419, 833,
  ],
};
const DETAIL_FONT = {
  name: "AvenirNext-Medium",
  ascent: 1,
  descent: 0.366,
  widths: [
    250, 334, 423, 574, 595, 870, 723, 262, 315, 315, 454, 666, 260, 320, 260, 380, 595, 595, 595,
    595, 595, 595, 595, 595, 595, 595, 300, 300, 666, 666, 666, 500, 800, 711, 642, 708, 761, 601,
    568, 778, 729, 271, 495, 659, 511, 903, 772, 849, 595, 846, 614, 569, 569, 712, 642, 988, 668,
    624, 592, 315, 380, 315, 666, 500, 250, 542, 636, 494, 635, 573, 310, 632, 584, 259, 260, 527,
    260, 887, 582, 610, 634, 633, 362, 444, 329, 582, 504, 773, 511, 504, 462, 315, 222, 315, 666,
  ],
};
// Curly quotes are this wide or narrower in both fonts. Any other character outside the tables
// counts as a full em, which is at least its real width.
const CURLY_QUOTES = "‘’“”";
const CURLY_QUOTE_WIDTH = 474;

// A dark, warm card that suits the sunset wallpaper.
const BACKGROUND = "#2b1a0c";
const TEXT = "#fdf6ec";
const MUTED = "#c9b8a3";
const PADDING = 16;

// The card macOS draws for each desktop widget size, in points, measured on a desktop (extra
// large is worked out from the others: two large cards and the gap between them). For each size:
// the biggest quote text that looks right, and the smallest at which a quote keeps its paragraphs
// as separate blocks. Below that the paragraphs are joined into one block, which fits bigger text.
const SIZES = {
  small: { width: 164, height: 164, largest: 14, comfortable: 12 },
  medium: { width: 344, height: 164, largest: 16, comfortable: 14 },
  large: { width: 344, height: 344, largest: 20, comfortable: 17 },
  extraLarge: { width: 704, height: 344, largest: 24, comfortable: 20 },
};
// Joined text shrinks to this with the label, then loses the label and may go down to SMALLEST.
const SMALL = 10;
const SMALLEST = 8;
const SPACING = 6;

// macOS rounds a line's ascent and descent to whole points, on any display, so lines sit a
// little further apart than the font's own 1.365 times its size.
const lineHeight = (font, points) =>
  Math.round(points * font.ascent) + Math.round(points * font.descent);
// Lines are counted as if the card were this much narrower, to cover kerning and rounding.
const WRAP_MARGIN = 0.98;

const family = String($getenv("widget-size") || "medium");
const size = SIZES[family] || SIZES.medium;
const textWidth = size.width - 2 * PADDING;
const textHeight = size.height - 2 * PADDING;

// The label and author scale with the quote, so they never look tiny next to it.
const labelSize = (points) => Math.max(9, Math.round(points * 0.6));
const bylineSize = (points) => Math.max(10, Math.round(points * 0.72));

function charWidth(char, font) {
  if (CURLY_QUOTES.includes(char)) return CURLY_QUOTE_WIDTH;
  // An accented letter is as wide as the letter under the accent.
  const code = char.normalize("NFD").charCodeAt(0);
  return font.widths[code - 32] || 1000;
}

// Counts the lines a text wraps to, breaking between words the way macOS does.
function countLines(text, font, points) {
  const limit = (textWidth * WRAP_MARGIN * 1000) / points;
  const space = font.widths[0];
  let lines = 1;
  let used = 0;
  for (const word of text.split(" ")) {
    const width = Array.from(word).reduce((total, char) => total + charWidth(char, font), 0);
    if (width > limit) {
      // A word too long for a line breaks wherever it has to, and again at each hyphen. This
      // assumes the worst: it starts on a new line and leaves no room after it.
      lines += (used > 0 ? 1 : 0) + Math.ceil(width / limit) - 1 + word.split("-").length - 1;
      used = limit;
    } else if (used > 0 && used + space + width > limit) {
      lines += 1;
      used = width;
    } else {
      used += (used > 0 ? space : 0) + width;
    }
  }
  return lines;
}

// How tall the whole card's content is with the quote set as these blocks at a size.
function contentHeight(blocks, byline, points, withLabel) {
  const quoteLines = blocks.reduce((total, block) => total + countLines(block, QUOTE_FONT, points), 0);
  const bylineLines = countLines(byline, DETAIL_FONT, bylineSize(points));
  return (
    (withLabel ? lineHeight(DETAIL_FONT, labelSize(points)) + SPACING : 0) +
    quoteLines * lineHeight(QUOTE_FONT, points) +
    (blocks.length - 1) * SPACING +
    SPACING +
    bylineLines * lineHeight(DETAIL_FONT, bylineSize(points))
  );
}

// The biggest size, down to a floor, at which these blocks fit the card. Null if none does.
function biggestFit(blocks, byline, floor, withLabel) {
  for (let points = size.largest; points >= floor; points--) {
    if (contentHeight(blocks, byline, points, withLabel) <= textHeight) {
      return { blocks, points, withLabel };
    }
  }
  return null;
}

// Keeps the paragraphs apart while the text stays comfortably big. Otherwise joins them into one
// block and takes the biggest size that fits, giving up the label before any of the quote. A quote
// too long even for that loses its last words, so that the cut is clean and the author stays.
function layout(paragraphs, byline) {
  const joined = [paragraphs.join(" ")];
  const fit =
    biggestFit(paragraphs, byline, size.comfortable, true) ||
    biggestFit(joined, byline, SMALL, true) ||
    biggestFit(joined, byline, SMALLEST, false);
  if (fit) return fit;
  const words = joined[0].split(" ");
  while (words.length > 1) {
    words.pop();
    const cut = [words.join(" ") + "…"];
    if (contentHeight(cut, byline, SMALLEST, false) <= textHeight) {
      return { blocks: cut, points: SMALLEST, withLabel: false };
    }
  }
  return { blocks: joined, points: SMALLEST, withLabel: false };
}

const font = (face, points) => `custom,${face.name},${points}`;

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
  const byline = "— " + quote.author + (quote.source ? ", " + quote.source : "");
  const { blocks, points, withLabel } = layout(quote.paragraphs.filter((line) => line), byline);
  $render(
    <vstack frame="max" padding={String(PADDING)} spacing={String(SPACING)} background={BACKGROUND} alignment="leading" linkurl={PAGE}>
      {withLabel ? (
        <text font={font(DETAIL_FONT, labelSize(points))} color={MUTED}>QUOTE OF THE DAY</text>
      ) : null}
      {blocks.map((block) => (
        <text font={font(QUOTE_FONT, points)} color={TEXT}>{block}</text>
      ))}
      <text font={font(DETAIL_FONT, bylineSize(points))} color={MUTED}>{byline}</text>
    </vstack>
  );
}
