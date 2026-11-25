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
// Punctuation outside the tables, at the wider of its widths in the two fonts.
const PUNCTUATION_WIDTHS = {
  "‘": 278,
  "’": 278,
  "“": 474,
  "”": 474,
  "—": 1000,
  "–": 500,
  "…": 1000,
  "¡": 337,
  "¿": 500,
};
// Any other character is drawn in a font this widget knows nothing about, so it counts as wider
// than nearly every character there is.
const UNKNOWN_WIDTH = 1200;

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
// Joined text shrinks to SMALLEST_WITH_LABEL, then loses the label and may go down to SMALLEST.
const SMALLEST_WITH_LABEL = 10;
const SMALLEST = 8;
const SPACING = 6;
// Lines are counted as if they were this share of their real width, to cover kerning and rounding.
const WRAP_WIDTH = 0.98;
// The author line may take up to this share of the card's height before it is cut short.
const BYLINE_SHARE = 1 / 3;

// macOS rounds a line's ascent and descent to whole points, on any display, so the distance
// between lines is not simply the font's own 1.365 times its size: 28 at 20pt, 13 at 10pt.
const lineHeight = (face, points) =>
  Math.round(points * face.ascent) + Math.round(points * face.descent);

// A size this widget doesn't know is laid out as small, which fits inside every other card.
const size = SIZES[String($getenv("widget-size"))] || SIZES.small;
const textWidth = size.width - 2 * PADDING;
const textHeight = size.height - 2 * PADDING;

// The label and author scale with the quote, so they never look tiny next to it.
const labelSize = (points) => Math.max(9, Math.round(points * 0.6));
const bylineSize = (points) => Math.max(10, Math.round(points * 0.72));

// How wide a character is, in thousandths of the font size.
function charWidth(char, face) {
  if (PUNCTUATION_WIDTHS[char]) return PUNCTUATION_WIDTHS[char];
  // An accented letter is as wide as the letter under the accent.
  const code = char.normalize("NFD").charCodeAt(0);
  return face.widths[code - 32] || UNKNOWN_WIDTH;
}

// Counts the lines a text wraps to. Lines break at spaces only; macOS also breaks after a hyphen,
// so the real text can take fewer lines than this, never more.
function countLines(text, face, points) {
  const limit = (textWidth * WRAP_WIDTH * 1000) / points;
  const space = face.widths[0];
  let lines = 1;
  let used = 0;
  for (const word of text.split(" ")) {
    const width = Array.from(word).reduce((total, char) => total + charWidth(char, face), 0);
    if (width > limit) {
      // A word too long for a line breaks wherever it has to, and again at each hyphen. This
      // assumes the worst: it starts on a new line, each of its lines ends a character short of
      // full, and it leaves no room after it.
      const perLine = Math.max(limit - UNKNOWN_WIDTH, UNKNOWN_WIDTH);
      lines += (used > 0 ? 1 : 0) + Math.ceil(width / perLine) - 1 + word.split("-").length - 1;
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

const bylineHeight = (byline, points) =>
  countLines(byline, DETAIL_FONT, bylineSize(points)) * lineHeight(DETAIL_FONT, bylineSize(points));

// How tall the whole card's content is with the quote set as these blocks at a size.
function contentHeight(blocks, byline, points, withLabel) {
  const quoteLines = blocks.reduce(
    (total, block) => total + countLines(block, QUOTE_FONT, points),
    0
  );
  return (
    (withLabel ? lineHeight(DETAIL_FONT, labelSize(points)) + SPACING : 0) +
    quoteLines * lineHeight(QUOTE_FONT, points) +
    (blocks.length - 1) * SPACING +
    SPACING +
    bylineHeight(byline, points)
  );
}

// The biggest size, down to a floor, at which these blocks fit the card. Null if none does.
function biggestFit(blocks, byline, floor, withLabel) {
  for (let points = size.largest; points >= floor; points--) {
    if (contentHeight(blocks, byline, points, withLabel) <= textHeight) {
      return { blocks, byline, points, withLabel };
    }
  }
  return null;
}

// Drops words from the end of a text, closing it with "…", until it passes a test. It stops at
// the first word, so a single word too big for the card is the one thing that can still be cut
// off by the card's edge.
function shorten(text, fits) {
  const words = text.split(" ");
  let cut = text;
  while (!fits(cut) && words.length > 1) {
    words.pop();
    cut = words.join(" ").replace(/[\s.,;:!?—–-]+$/, "") + "…";
  }
  return cut;
}

// Keeps the paragraphs apart while the text stays comfortably big. Otherwise joins them into one
// block and takes the biggest size that fits, giving up the label before any of the quote. A quote
// too long even for that loses its last words, and so does an author line that would crowd out
// the quote, so that every cut is a clean one.
function layout(paragraphs, fullByline) {
  const byline = shorten(
    fullByline,
    (cut) => bylineHeight(cut, SMALLEST) <= textHeight * BYLINE_SHARE
  );
  const joined = paragraphs.join(" ");
  const fit =
    biggestFit(paragraphs, byline, size.comfortable, true) ||
    biggestFit([joined], byline, SMALLEST_WITH_LABEL, true) ||
    biggestFit([joined], byline, SMALLEST, false);
  if (fit) return fit;
  const cut = shorten(
    joined,
    (text) => contentHeight([text], byline, SMALLEST, false) <= textHeight
  );
  return { blocks: [cut], byline, points: SMALLEST, withLabel: false };
}

// Text arrives as it was typed: a line break inside a paragraph starts a new block, and other
// runs of white space become single spaces, which is what the line counting expects.
const tidy = (text) => String(text).replace(/\s+/g, " ").trim();

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
  const paragraphs = quote.paragraphs
    .flatMap((paragraph) => String(paragraph).split("\n"))
    .map(tidy)
    .filter((line) => line);
  const { blocks, byline, points, withLabel } = layout(
    paragraphs,
    tidy("— " + quote.author + (quote.source ? ", " + quote.source : ""))
  );
  $render(
    <vstack
      frame="max"
      padding={String(PADDING)}
      spacing={String(SPACING)}
      background={BACKGROUND}
      alignment="leading"
      linkurl={PAGE}
    >
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
