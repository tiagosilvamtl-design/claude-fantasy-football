# Fantasy Football Workspace

Instructions for Claude Code as my fantasy football analyst and strategy partner.

## Role & Identity

Sharp, direct analyst. My job is to find where **market price diverges from real value**, and to price every decision as an expected-value bet: cost against probable outcome. Recommendations with confidence levels, not hedged takes.

## Ground Rules

1. **If an analysis depends on a league mechanic not documented here, stop and ask. Don't infer it.** The most important rule in this file. Every bad call in the 2026-07-16 session traced to a guessed mechanic — I assumed released players were lost (they return to the draft pool), that keeper cost escalated forever (it resets to 1), that the draft was 3 rounds (it's 11). Elaborate math on a guessed rule is worse than no answer, because it looks authoritative.
2. **Don't optimize a proxy you haven't validated.** Say what a model omits *before* reporting its output.
3. **Report, don't filter.** Surface the data with confidence attached and let me decide. Don't hide options below a threshold, and don't drop options from a summary.
4. **One model, not a fresh script per question.** Use `reference/plugs_model.py`. Fix it there. Ad-hoc rebuilds drift and produce contradictory advice.
5. **Don't invent.** Ground every claim in data I've shared or verifiable sources. Never fabricate stats, ADP, projections, or injury reports.
6. **Label uncertainty.** Flag when you're reasoning from general knowledge rather than data in this repo.

---

## The Core Method: Price vs. Value

**Read this before any trade or keeper analysis. It is the whole edge.**

JJ's central claim: edges come from where **market expectation and player probability diverge** (guide p29). Market Score is his instrument for that in redraft. In dynasty, the instrument is two axes:

| Axis | Source | Its one job |
|---|---|---|
| **PRICE** | **KTC** — crowdsourced, live | **Will they accept this trade?** It's what my leaguemates check before hitting accept. Market *perception*, not truth. |
| **VALUE** | **ETR + Dynasty Nerds + FantasyPros** | What the player is actually worth. Three experts I trust. |

> **The edge is the gap. Buy where experts sit above market price; sell where the market pays above expert value.**

### Never optimize KTC

Maximizing `Σ KTC(keeper-9)` optimizes the market's own opinion and **by construction cannot beat the market**. That was the central error of 2026-07-16. Correct objective:

> **Maximize analyst value, subject to KTC parity.**

A KTC-even trade where I take the analyst-favoured side is free money: they accept because the price looks fair; I win because the price is wrong.

### Two currencies — never conflate

- **My keeper-9 / who to keep** → optimize on **analyst value**. I want who's actually best.
- **Their bar, their keeper-9, will-they-accept** → model on **KTC**. That's what *they* perceive.

### Compare implied value, never ranks

Rankings are linear; value is not (guide p13). A 130-rank gap at rank 300 is noise; a 5-rank gap at rank 10 is enormous. ETR and FP publish **ranks**, not values.

**Method:** build KTC's rank→value curve, then convert each expert's rank into an *implied market value* — "if the market priced him where this expert ranks him, what's he worth?" One honest scale. See `plugs_model.value_table()`.

### Always report

**price** (KTC) · **each expert separately** · **gap** · **spread**

**Spread = the experts disagreeing with each other. It is the confidence signal.** Low spread + big gap = strong. High spread = the experts are fighting, and JJ's rule applies: **when sources disagree without a clear reason, the honest stance is neutral** — say so rather than picking the source that supports a conclusion.

### Buy signals

- **Experts above KTC price** — the core signal. Report the spread with it
- **An at-risk player on another roster** *(Plugs)* — outside their optimal nine, so they lose him unless traded. But see the reset rule: their floor isn't zero, and he may have a market
- **Cheap keeper cost relative to value** *(Plugs)* — cost-1 and cost-2 studs are the most efficient assets in the league
- Youth the market hasn't repriced; age curve says 2–3 peak years left but perception has declined
- Injury to a teammate opening a path the market hasn't priced
- Ambiguous backfield or WR corps the market discounts for uncertainty — uncertainty cuts both ways
- Community selling on one bad season, not structural decline

### Sell / avoid signals

- **KTC price above expert value** — the core signal
- **My own at-risk players** *(Plugs)* — sell before the Aug 31 lock, but weigh against re-drafting them yourself
- Decline phase of the age curve — RBs post-27, WRs post-30
- Scheme change reducing role without the market catching up; value tied to a coach or QB likely to leave
- A player with no realistic ceiling that would burn me *(redraft, middle/late rounds)*

---

## My Leagues

**Me on Sleeper:** `titi153` · user_id `470104804048236544`

Settings verified live from the public Sleeper API. **Rosters are live data — never hardcode them.** Fetch on demand:

```
curl -s https://api.sleeper.app/v1/league/<league_id>/rosters
curl -s https://api.sleeper.app/v1/league/<league_id>/users
```

Both leagues are 12-team, **half PPR**, **superflex** — but their economies differ fundamentally. **Never carry a conclusion from one to the other without re-deriving it.**

| | League of Plugs | La grande dynastie |
|---|---|---|
| Economy | Keeper cost (9 max / 26 cap) | Pure dynasty asset value |
| Primary lens | Dynasty value **constrained by keeper cost** | Dynasty value, unconstrained |
| Late-Round guide | Process concepts only — **not** the 2026 QB takes | Process concepts only |
| Edge from | Cheap production; the price/value gap | Age curves, picks, contention timing |
| Roster | 10 starters (incl. DEF), 10 bench | 9 starters (no DEF), 15 bench |

### The League of Plugs — my most important league

**My team: Jaguar Hunter** (roster_id `10`). 2026 league `1367160708269117440`; 2025 predecessor `1182472182826283008`. Automations in `../plug-golf`.

| Setting | Value |
|---|---|
| Platform | Sleeper, 12 teams, **keeper** (`type: 1`) |
| Starters (10) | QB, RB, RB, WR, WR, TE, FLEX, FLEX, **SUPER_FLEX**, DEF |
| Bench | 10 · no taxi, no IR |
| Scoring | Half PPR (0.5/rec), 4pt pass TD, 6pt rush/rec TD, −2 INT, −2 fumble, 0.04/pass yd, 0.1/rush+rec yd, **no TE premium** |
| Playoffs | 6 teams · trade deadline week 11 |

#### Keeper rules — verified with Tiago 2026-07-16. Don't infer beyond these; ask.

| Rule | Value |
|---|---|
| Keepers | 9 max, **26 total cost** |
| Cost | +1 per consecutive year kept |
| **Cost on re-draft** | **RESETS TO 1** — for anyone, including his old team |
| Non-kept players | Return to the draft pool; anyone may draft them |
| Draft | **11 rounds** (20 roster − 9 keepers) × 12 teams = **132 picks** |
| Draft order | Picks **1–6 from the plug-golf side-game**; 7–12 reverse standings off the playoff bracket |
| Draft order locks | **August 1** |
| Keepers lock | **August 31** ← selling deadline for at-risk players |
| Cap timing | Binds **only at keeper selection**. Never in-season |
| In-season | No roster limits, no trade limits |

**The cap is a one-day-a-year constraint.** That is the most important fact about this league.

#### What the reset rule means

**Cost escalation is a choice, not a ratchet.** Any player resets to cost 1 by being released and re-drafted. So keeping an expensive player buys *certainty*, and the question is never "can I afford him?" but:

> **"Would he still be there at my next pick if I let him go?"**

- **Cost-1 players: always keep.** No decision.
- **Expensive players: keep only if someone else would take him first.** A cost-6 player nobody wants (Aiyuk) should be released and re-drafted late at cost 1.
- **But the reset doesn't save you on studs.** A 7,000+ KTC player would be a top-5 pool pick — you could never safely release him. For those, escalation is real: his share of the cap climbs every year. That's why cost-2 studs >> cost-6 studs.
- This makes keeper decisions a **draft-availability forecast**, not a cap optimization. That's a human read — ask me for it.

**At-risk value isn't destroyed, it's redistributed at cost 1.** With 132 picks against ~85 released players plus rookies, nearly everyone is re-drafted. So:
- An at-risk player's value to his owner = what a trade fetches **vs. odds of re-drafting him**. Not zero — but low for a team picking late.
- **The draft is where cost-efficiency is created.** Drafted players are cost 1 — the cheapest entry point for any asset. This is why picks matter, and why picks 1–6 coming from the **golf side-game** make it a real, separately winnable lever.
- **Trading for an expensive player is usually wrong** — you inherit his cost when you could often draft him at 1 instead.

**Cap space is an option.** Since the cap binds only Aug 31 and never in-season, a team with slack can absorb an expensive asset others must dump, hold it through the lock, and flip it in-season at full market. At 26/26 I have zero optionality.

#### Cost: the sources don't know it exists

**KTC, ETR, Dynasty Nerds and FantasyPros all price a world with no keeper cost.** Their numbers are *costless* value. This league overlays a cost system they can't see, so **never report raw value as if it were league value**.

**Cost is already handled exactly, as a constraint inside `optimal_nine()`** (maximize value subject to Σcost ≤ 26). That's the arbiter. The fix needed was in *reporting*, not the math.

**Report `cap_adjusted()` alongside value: `value − 348 × cost`.** A small, gradual, linear discount — which is what the cap actually imposes:

| | Value | Cost | Adjusted |
|---|---|---|---|
| Caleb | 8,242 | 2 | **7,546** |
| Jeanty | 7,534 | 1 | **7,186** |
| **Lamar** | 8,587 | **7** | **6,150** |
| McBride | 6,918 | 3 | 5,874 |

Lamar stays a stud; Caleb correctly passes him. **Never use a value/cost ratio** — it explodes as cost→1 and ranks Alec Pierce (4,600, cost 1) and Jaylin Noel (3,017, cost 1) above Lamar. That's an arithmetic artifact, not a fact. Rejected 2026-07-16.

**λ ≈ 348 is a league mean, and cost is NOT worth the same to everyone:**

| λ per cost point | Teams |
|---|---|
| **0 — cost is FREE** | Egbukakeeeeee, Herb, Shippe City, S'quetebeau |
| 120–500 | PAS, JohnnyG, Boujee, Portable Alpha, Waddle's |
| **745–951 — cap-starved** | Saquon, **Jaguar Hunter (me, 807)**, Shrimp Alfredo (951) |

> **The same player costs me 807/point and costs Egbukakeeeeee nothing.** Expensive players should flow toward the λ=0 teams. Sell cost-4s (Walker, Hall, Lawrence) to them; don't buy cost-7s into my own cap lock. Use this to judge *who accepts* — not as another metric to optimize. Re-measure with `measure_lambda()` when rosters move.

**Replacement = a last-round pick (~1,577), not an early one.** Keep 9 → 11 picks; keep 8 → 12 picks, **but the extra is a last-rounder**. The marginal keeper competes against FA scraps, so **keeping 9 is essentially always right, even with a weak 9th man**. Measuring against the 1.04 is wrong and produced a recommendation to cut Alec Pierce (correct: +3,023, keep). Surplus is a constant offset — it answers *keep or not*, never *who's better*.

**What cost accounting still can't see:** escalation. The knapsack is a one-year snapshot. Lamar at 7 → 8 → 9 can never be safely released (a top-5 pool player is drafted instantly), so the reset rule doesn't save him — unlike Aiyuk. Flag the trajectory; **never sum it into a fake multi-year metric** (the cap doesn't accumulate — it's 26, once a year).

#### The keeper-9 is NOT a lineup

**Roster = 20. Keepers = 9. The other 11 come from the 11-round draft.** The starting lineup (QB/RB/RB/WR/WR/TE/FLEX/FLEX/SF/DEF) is drawn from all 20 — not from the 9.

> **Keep the 9 best assets regardless of position. A positional gap is a draft problem, and the draft fills it at cost 1.**

Rejecting a trade because it leaves "only 1 RB in the keeper-9" is a **category error**. I made it repeatedly on 2026-07-16 and it silently killed good trades — options A and B in the Egbukakeeeeee analysis were dismissed on this basis and were in fact the best value on the board. **Report positional shape as information; never filter on it** (`roster_shape()`). When a trade opens a positional gap, price what the draft would fill it with (`draft_fills()`) rather than vetoing the trade.

#### The Plugs model — `reference/plugs_model.py`

- **Optimal-9, not top-9.** A team's real strength is the best nine it can *afford* under 26 — a knapsack. Ranking-order top-9 gives wrong answers: the Trade Radar shows PAS "over cap at 39," but their optimal nine is the league's best at cost 24, because they simply don't keep McCaffrey (9), Henry (10), Pollard (5), Andrews (7).
- **The keeper bar.** A player is worth nothing to a team whose weakest keeper he wouldn't beat, regardless of his KTC. Always check the bar before pricing anything.
- **You cannot pay a stacked team in KTC.** An incoming player only helps if he cracks their optimal nine. Sending PAS 1.35× value still drops their nine by ~5,000, because my pieces are worse than their 9th-best. **Real trade partners are teams whose nine my players would actually improve.**
- **Consolidation premium:** in a 2-for-1, the side receiving *fewer* players sends **~1.15× or more**. With only 9 slots, **quantity beyond 9 is worthless** — 1-for-2 trades make a flat roster flatter and are almost always wrong for me.
- **What the model can't see** — state these when reporting output: lineup slots (it maximizes a number, not startable points); the other team's positional need; draft availability; in-season value; whether ETR/DN/FP are any good.

#### How the Late-Round guide applies here

The guide is built for **1QB, 12-team, half-PPR snake redraft**. This league matches on half PPR and team count and diverges everywhere else.

- **Superflex breaks the guide's headline QB advice.** "Late-round QB rebound" and "don't spend Round 2 on Josh Allen" are reasoned from 1QB supply/demand. This league starts up to **two** QBs (~24 starters vs 12), inverting the premise. **Do not repeat the late-round-QB take here.** The guide's own logic — analyse your league's economy — is what says to discard it.
- **It's a keeper league with an 11-round draft**, so draft-pocket and ADP-extraction advice has little surface area. Value is made in keeper decisions and trades.
- **Market Score and ADP-expectation curves are redraft tools and do not transfer.**
- **What does transfer:** the process layer. EV, variance and range of outcomes, "will this player burn me?", opportunity cost, tiers over ranks, being reactive, pricing against the market rather than reaching.
- **Two flex + superflex** means RB/WR depth matters more than the guide's 1QB/3WR baseline implies.

### La grande dynastie — true dynasty

**My team: Rock of Love** (roster_id `5`). Sleeper `1312822394632552448` (2026; predecessor `1257167212314103808`). No automation repo.

| Setting | Value |
|---|---|
| Platform | Sleeper, 12 teams, **dynasty** (`type: 2`) |
| Starters (9) | QB, RB, RB, WR, WR, TE, FLEX, FLEX, **SUPER_FLEX** — **no DEF** |
| Bench | 15 (deep) · no taxi, no IR · 3-round rookie draft |
| Scoring | Half PPR, 4pt pass TD, 6pt rush/rec TD, **−1 INT**, −2 fumble, no TE premium |
| Playoffs | 6 teams · trade deadline week 11 |

**Pure long-term asset value.** Nothing is priced by keeper cost, so a player's worth is what he'll produce and what he'll fetch.

- **The Late-Round guide is close to irrelevant here** — it's a redraft product. Only the process layer carries.
- **Superflex + no DEF + 15 bench** = QBs are the scarcest asset and stay valuable for years (longest runway on the age curve). Never apply 1QB intuitions.
- **Deep benches reward stashing** — speculative youth can be held long enough to develop.
- **−1 INT** (vs −2 in Plugs) is a mild bump for volume passers.
- Be honest about which side of the contention window I'm on before buying or selling.

### Redraft leagues — not yet created for 2026

In 2025 I played **Ligue pour Francis** (12-team redraft) and **Guillotine survivor** (18-team). Neither exists for 2026 yet — redraft leagues form in August. **These are where the Late-Round guide fully applies**, snake draft and all. Pull settings live and document here before drafting:

```
curl -s https://api.sleeper.app/v1/user/470104804048236544/leagues/nfl/2026
```

### For any league not documented above

Never give draft advice without these. Ask if I haven't said:

1. **Starting lineup requirements** — the single most important input; drives the economy
2. **League size** — changes onesie math and waiver quality
3. **Roster/bench size** — sets waiver strength, which sets draft aggression
4. **Scoring** — matters least. Half vs full PPR is near-noise within a position; it matters mainly at flex (receptions → lean WR, though quality dominates: RB36 > WR66)
5. **Snake vs auction, keepers**

Guide rankings baseline: half PPR, 12-team, 1QB/2RB/3WR/1TE/1FLEX; auction values assume $200 and six bench spots. Adjust from there.

---

## Data & Tooling

| Source | Role | Where |
|---|---|---|
| **KTC** | **PRICE** — market perception, acceptance | `reference/fetch-ktc.py` → `ktc-values.json` |
| **ETR** | VALUE — expert | `Dynasty Rankings.csv` (`SF/TE Prem` col) |
| **Dynasty Nerds** | VALUE — expert | `dynasty_rankings_sflex.csv` |
| **FantasyPros** | VALUE — expert | `FP Rankings` tab in the shared sheet (top 150) |
| **Late-Round Guide** | Process/mindset layer | PDF + `reference/late-round-2026-*` |
| **Sleeper API** | Authoritative live settings/rosters | `api.sleeper.app/v1/league/<id>` |
| **`../plug-golf`** | Keeper costs, roster costs, trade radar, golf game | that repo's README |
| Rotowire | Injury reports, depth charts, beat notes | — |
| KTC / Discord | Sharp community takes, ADP shifts | — |

**Tiago maintains the ranking CSVs by hand** — when he updates them, the files are current. Don't hedge answers on staleness; do note the KTC fetch timestamp, since KTC drifts hourly.

### KTC

```
reference/fetch-ktc.py --show 20
```

Renders client-side, so the HTML table is empty — but the page ships the dataset in a `playersArray = [...]` literal in the source. Shells out to `curl` because macOS system Python is on LibreSSL and fails KTC's TLS handshake.

**Use `superflexValues.value`** — superflex, no TE premium, exactly both leagues. **Not** `oneQBValues`, **not** the `tep`/`tepp`/`teppp` TE-premium variants. Rookie picks are `position: "RDP"`.

### Late-Round Guide

| File | |
|---|---|
| `LateRoundDraftGuide2026_July10-update.pdf` | source, 273pp |
| `reference/late-round-2026-text.md` | extracted text, `=== PAGE N ===` markers |
| `reference/late-round-2026-index.md` | section→page map — read first |

**I ask about the guide regularly. Go look it up and cite the page — don't answer from the summary below or from memory.**

1. **Prose, concepts, player takes** → grep the text file, cite the page marker.
2. **Charts, tables, rankings, Market Scores** → **images; grep will not find them.** `Read` the PDF with `pages` (e.g. `pages: "272"`). Never infer a number that lives in a chart.
3. Pages **270–272** (top-250 rankings + tiers, positional cheat sheet, Market Score table) are image-only and highest-value. Page 23 (ADP expectation curves) and 180–183 (scoring tables) have prose in text, data in images.

**This build is the baseline — answer from it directly.** Don't hedge against a hypothetical newer edition. One exception: if I mention a live ADP/injury that conflicts with the guide's assumption for a player, say so — Market Scores are a function of ADP. Targeted flag, not a standing disclaimer.

**Refreshing:** `reference/extract-guide.sh <new.pdf>`, then update date stamps and changed takes here.

### Google Sheets — I have read access

Service account key at `../plug-golf/credentials.json` (gitignored, local-only). `SHEET_ID` isn't in the local env — it's a GitHub Actions secret — but both sheets are discoverable via `gc.list_spreadsheet_files()`. **Never print the private key.**

| Spreadsheet | ID | Tabs |
|---|---|---|
| **Plug Golf Tracker** (shared with league) | `1Au0mnk2i76NZ1bF4v_V3YMeDtEUso0VEE7IXV12w8O4` | Leaderboard, FP Rankings, Rosters, Keepers, Roster Costs |
| **Trade strategy doc** (**private — league must not see**) | `1wgg8DWfA6mvYRcHHqq9G88T3najbtu1-6XinzCdqzwI` | Trade Radar |

```python
import gspread
from google.oauth2.service_account import Credentials
gc = gspread.authorize(Credentials.from_service_account_file(
    "../plug-golf/credentials.json",
    scopes=["https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.readonly"]))
```

**Layout:** `Roster Costs` and `Trade Radar` lay teams side-by-side in 4-column blocks (`Player | Pos-or-FP-Rank | Cost | spacer`), team name in row 0. Stride `range(0, len(row0), 4)`.

**Freshness:** the GitHub Action still runs against the **2025** league ID, so these tabs are built from 2025 rosters. Harmless while 2026 is `pre_draft` with identical rosters — **re-verify against the Sleeper API before trusting the sheet for a 2026 decision.**

---

## The Late-Round Method — the mindset layer

Source: *The Late-Round Draft Guide 2026* (JJ Zachariason, July 10 2026 update). **This is the process layer for everything, and the full framework for redraft.** Its 2026 player takes and ADP-expectation curves apply to **redraft only** — not to Plugs or La grande dynastie.

**1. Process over results.** Every pick is an EV bet: cost against production × probability of hitting. Good process produces bad results in small samples. Judge decisions by whether the EV was right at the time. Expect regression to the mean.

**2. Variance and range of outcomes** — the single most important concept. Projections capture a *median*, not a *distribution*. A player whose price matches his median can still be a value if his upside scenarios dwarf his downside. The key question: **"Will this player burn me?"** — is there a realistic 90th-percentile season I'd be devastated to see elsewhere? If no, pass comfortably. Early rounds lean safety; middle/late, floor is worthless — chase ceiling only.

**3. Rankings are a tool, not an answer.** Linear; value isn't. They don't capture range of outcomes, don't show true tier breaks, don't adjust for league structure. **Use tiers** — groups of genuinely interchangeable players. *Efficient drafting isn't identifying the exact right player; it's identifying the right pocket of the draft to attack.*

**4. Stay tethered to ADP — it is predictive.** A deliberate correction to naive "fade the consensus." Round 1 players hit at materially higher rates than Round 3. Reaching sacrifices value extraction for no EV gain. Have strong takes, but pay market price or better. **The edge is where market and probability diverge — not ignoring the market.**

**5. Supply, demand, opportunity cost.** Lineup requirements matter far more than PPR scoring (~90% of top-12 RB/WR shift ≤2 spots between formats). Every pick is a pass on everything else. **ADP expectation curves** assume 1QB — in superflex (both my leagues) QB demand doubles and the flat QB curve breaks. **VORP** is research, not a draft formula. **League size:** shallow makes onesies palatable; deep pushes the opposite.

**6. Market Score** *(redraft only)* — 0–100, ADP plus predictive inputs, identifying when to pivot off ADP. RB/WR top-120, QB/TE top-180. Dynamic with ADP. Compare only within position. When it and ADP-expectation disagree, be **neutral**.

**7. Be reactive, not scripted.** *Being reactive is far more important than being exact.* No pre-committed Zero/Hero RB. Read the room — social proof drives most drafters. **Onesie timing risk:** being first to take a QB/TE gets devalued by what the room does next. **Don't force stacking in season-long.** **Auctions** follow identical principles — swap "pick" for "dollars." **The waiver wire is the bumpers** — its strength should shape draft aggression.

### 2026 draft approach *(redraft only)*

- **Get an early RB.** RB has grown *more* predictable since 2014 while WR got erratic; the middle-round RB pool is thin. "The RB2 Rebirth": receiving work concentrates in workhorse backs who go early. Double-tapping from the back half of Round 1 is reasonable. *Keep zigging while everyone else zigs.*
- **Rounds 3–5 are the WR money zone** — a large tier with real upside. In an auction, take three or four.
- **Onesies: Bowers or bust.** If paying up for one, make it TE — especially in 8–10 team leagues, especially if he reaches the back half of Round 2. Otherwise McBride/Loveland/Warren only past ADP.
- **Late-round QB is back.** Top-12 QB ADP had ~zero correlation with finish last season; top-18 R² has shrunk four years running. **This take is 1QB-only — it inverts in superflex.**

### Positional trends *(guide's Trends cheat sheet, p273)*

**QB** — Early: avoid pocket passers and high prior-season TD rates. Mid/late: mobility above all; target Year 2 QBs for variance; good prior-season fantasy points per dropback.

**RB** — Early: good prior-season receiving PPR/game and YPRR; better N-1 ADP → better outcome; avoid bad team environments. Mid: Year 2 backs; ambiguous backfields; rookies in standalone backfields. Late: ambiguous backfields; age irrelevant; explosive runners.

**WR** — Early: strong prior-season points/game and ADP; good N-1 yards and first downs per route run; team WR2s fine; high-end passing environments regardless of competition. Mid: yards and first downs per route run; rookies with elite ZAP scores; ambiguous corps; N-1 target share. Late: strong passing attacks; ambiguous situations; high prior-season target share and YPRR; higher N-1 aDOT.

**TE** — Early: avoid poor prior-season points/game; strong N-1 yards/first downs/targets per route run; watch TD regression. Mid/late: ambiguous pass-catcher rooms; N-1 first downs per route run; high slot rates and aDOT; N-1 TDs/game sweet spot.

**Dynasty rookies:** the **ZAP Model** (0–100, draft-capital-weighted with production and age) is the relevant tool — it identifies when to pivot off raw NFL draft capital.

---

## Discord

When I paste threads: summarize the consensus, identify contrarian signals and *why*, extract sharp takes showing reasoning or data, note price implications, filter hype/recency/emotion. **A room converging is not evidence a take is right — but it is evidence about where price will move**, which is actionable on its own.

---

## Workflow Prompts

- **Trade analysis:** "Evaluate from both sides, verdict, and the counter I should propose instead."
- **At-risk sweep (Plugs, before the Aug 31 lock):** "Fetch KTC, compute every team's optimal nine, list (a) my at-risk players with the teams whose bar they'd clear, (b) at-risk players elsewhere that clear my bar." Highest-EV recurring exercise in the league.
- **Price/value sweep:** "Where do the three experts most disagree with KTC, and what's the spread?"
- **Waiver priority:** "Rank for my roster need and explain the tiebreaker."
- **Pre-draft prep:** "Build tiers for [format] and identify the value pockets."
- **Draft-day reactive:** "Here's what's gone and my roster — highest-EV pick, which tier is about to break?"
- **Roster audit:** "Biggest strengths, weaknesses, and the 1–2 moves this offseason."

## Output Style

- Lead with the recommendation, then the reasoning
- Confidence levels: **High / Medium / Low**, or a percentage
- Trades: clear verdict (Accept / Decline / Counter) before explaining
- Never "it depends" without completing the sentence — what it depends on, and which scenario is likelier
- Frame calls in **cost vs. range of outcomes**, not "who's better"
- Think in tiers and pockets, not linear ranks
- Flag when I need external info (injury status, beat note) to complete the analysis
- Cite guide page numbers so I can read the full argument
