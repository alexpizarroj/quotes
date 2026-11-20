#!/bin/sh
# Render site/card.html to site/widget.png (transparent corners, 3x density) with headless Chrome.
set -e
cd "$(dirname "$0")/.."
CHROME="${CHROME:-$(command -v google-chrome || echo "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")}"
"$CHROME" --headless=new --no-sandbox --disable-gpu --hide-scrollbars \
  --window-size=360,236 --force-device-scale-factor=3 \
  --default-background-color=00000000 --virtual-time-budget=8000 \
  --screenshot="$PWD/site/widget.png" "file://$PWD/site/card.html" >/dev/null 2>&1
test -s site/widget.png
