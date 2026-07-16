# Late-Round Draft Guide 2026 — lookup index

Source PDF: `LateRoundDraftGuide2026_July10-update.pdf` (273pp, July 10 2026 update)
Extracted text: `reference/late-round-2026-text.md` (page-marked as `=== PAGE N ===`)

## How to answer a question about the guide

1. **Prose / concepts / player takes** → grep `reference/late-round-2026-text.md`. Page markers give the citation.
2. **Charts, tables, rankings, Market Scores** → these are **images**; grep will not find them. Use `Read` on the PDF with the `pages` parameter (e.g. `pages: "272"`). This renders the page visually and works well.
3. Cite the page number in any answer.

## Contents → page

| Section | Page |
|---|---|
| Introduction | 5 |
| **Part One: The Setup** | 7 |
| — Establishing Process (EV, process vs. results, regression) | 8 |
| — Rankings Aren't Everything (variance, range of outcomes, supply/demand) | 12 |
| — The Draft Game (ADP expectation, VORP, opportunity cost, Market Score intro) | 19 |
| **Part Two: Player Evaluation** | 31 |
| — Quarterback | 32 |
| — Running Back | 64 |
| — Wide Receiver | 112 |
| — Tight End | 154 |
| **Part Three: Your Draft Plan** | 178 |
| — Know Your League (scoring vs. lineup requirements, VORP research) | 179 |
| — Tiers Over Rankings | 187 |
| — Attacking the Draft (league size, waivers, onesie risk, stacking, flexibility) | 191 |
| — Your 2026 Approach (early RB, R3–5 WR, Bowers-or-bust, late-round QB) | 196 |
| **Part Four: Player Selection** | 205 |
| — Update Tracker | 206 |
| — Players to Target | 207 |
| — Players to Avoid | 237 |
| — Late-Round Dart Throws | 254 |
| **Cheat Sheets** | 267 |
| — Auction values explained | 269 |
| — Top-250 rankings + tiers (IMAGE) | 270 |
| — Positional cheat sheet (IMAGE) | 271 |
| — Market Score cheat sheet (IMAGE) | 272 |
| — Trends cheat sheet (text) | 273 |

## Key visual-only pages

`Read` the PDF directly for these — grep returns nothing useful:

- **270** — top-250 rankings and tiers (half PPR, 12-team, 1QB/2RB/3WR/1TE/1FLEX)
- **271** — positional cheat sheet
- **272** — Market Score cheat sheet (QB/RB/WR/TE with ADP + score)
- **23** — ADP expectation curves by position, 2014–2025 (prose on page, data in image)
- **180–183** — positional rank change between scoring settings; positional rank averages
- Market Score hit-rate tables live in each Part Two position section

Other low-text pages (1–2, 4, 7, 31, 178, 191, 204–206) are section dividers — nothing lost.

## Per-position Market Score notes

Each Part Two position chapter contains its own Market Score subsection (methodology, historical hit rates, and that position's 2026 read). Grep `"Market Score"` within the position's page range.

## Build / refresh

Current build: **July 10 2026 update**. This is the working baseline — answer from it directly and with confidence.

The guide publishes weekly updates, but this copy only changes when Tiago drops in a new PDF and asks for a refresh:

```
reference/extract-guide.sh <new-guide.pdf>
```

Then update the date stamps and any changed 2026 takes in `CLAUDE.md`. Until then, this build stands — don't caveat answers against editions that aren't here.

The one thing genuinely worth raising unprompted: Market Score is computed off ADP, so if a live ADP move, injury, or trade conflicts with the guide's assumption for a specific player, that specific call is worth re-examining. That's a targeted flag, not a blanket disclaimer.
