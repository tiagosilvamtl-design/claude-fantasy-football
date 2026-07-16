#!/usr/bin/env bash
# Re-extract searchable text from the Late-Round Draft Guide PDF.
# Manual trigger — run this only when swapping in a newer guide build.
#   usage: reference/extract-guide.sh [path-to-pdf]
# Defaults to the most recent PDF in the repo root.
# Charts, tables, and the cheat sheets (pp. 270-272) are images and are NOT
# captured — read those pages from the PDF directly.
set -euo pipefail

PDF="${1:-$(ls -t ./*.pdf 2>/dev/null | head -1)}"
[ -n "$PDF" ] && [ -f "$PDF" ] || { echo "No PDF found. Pass a path."; exit 1; }
command -v pdftotext >/dev/null || { echo "Need poppler: brew install poppler"; exit 1; }

OUT="reference/late-round-2026-text.md"
PAGES=$(pdfinfo "$PDF" | awk '/^Pages:/{print $2}')
echo "Extracting $PAGES pages from $PDF ..."

{
  echo "# Late-Round Draft Guide 2026 — extracted text"
  echo "Source: $(basename "$PDF")"
  echo "Generated: $(date +%Y-%m-%d)"
  echo "Charts/tables are images in the source and are NOT captured here —"
  echo "read the PDF page directly for those (see late-round-2026-index.md)."
  for p in $(seq 1 "$PAGES"); do
    printf '\n\n=== PAGE %s ===\n' "$p"
    pdftotext -layout -f "$p" -l "$p" "$PDF" - \
      | grep -v 'Late-Round Fantasy Football: 2026 Draft Guide'
  done
} > "$OUT"

echo "Wrote $OUT ($(wc -c < "$OUT" | tr -d ' ') bytes)"
echo "Next: update the build date and any changed 2026 takes in CLAUDE.md."
