// Übersicht widget: shows the quote of the day on the desktop.
// Install: copy this file into ~/Library/Application Support/Übersicht/widgets/

const URL = "https://alexpizarroj.github.io/quotes/today.json";

export const command = `curl -sf --max-time 10 "${URL}"`;

// The quote changes once a day; check every 30 minutes so a late publish or a wake from sleep catches up.
export const refreshFrequency = 30 * 60 * 1000;

// Position and size: top-left corner of the desktop, as wide as a medium native widget.
// `top` is measured from below the menu bar.
export const className = `
  top: 10px;
  left: 10px;
  width: 345px;
  height: 240px;
  box-sizing: border-box;
  padding: 14px 18px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  justify-content: center;
  border-radius: 22px;
  background: rgba(28, 32, 44, 0.55);
  -webkit-backdrop-filter: blur(30px) saturate(160%);
  border: 0.5px solid rgba(255, 255, 255, 0.18);
  color: rgba(255, 255, 255, 0.95);
  font-family: -apple-system, "SF Pro Text", sans-serif;

  .label { font-size: 11px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: rgba(255, 255, 255, 0.55); margin-bottom: 8px; }
  .line { font-family: "New York", "Iowan Old Style", Georgia, serif; font-size: 18px; line-height: 1.4; margin: 0 0 4px; }
  .medium .line { font-size: 15.5px; line-height: 1.35; margin-bottom: 3px; }
  .long .line { font-size: 13.5px; line-height: 1.32; margin-bottom: 2px; }
  .long .label { display: none; }
  .gap { height: 5px; }
  .by { margin-top: 10px; font-size: 12px; color: rgba(255, 255, 255, 0.6); }
  .long .by { margin-top: 6px; }
`;

export const render = ({ output }) => {
  let quote;
  try {
    quote = JSON.parse(output);
  } catch (e) {
    return <div className="by">Quote of the day is unavailable right now.</div>;
  }
  // Shrink the text for longer quotes so every quote fits the fixed card.
  const length = quote.text.length;
  const lines = quote.paragraphs.length;
  const size = length > 240 || lines >= 4 ? "long" : length > 150 || lines >= 2 ? "medium" : "";
  return (
    <div className={size}>
      <div className="label">Quote of the day</div>
      {quote.paragraphs.map((line, i) =>
        line ? <p key={i} className="line">{line}</p> : <div key={i} className="gap" />
      )}
      <div className="by">{[quote.author, quote.source].filter(Boolean).join(", ")}</div>
    </div>
  );
};
