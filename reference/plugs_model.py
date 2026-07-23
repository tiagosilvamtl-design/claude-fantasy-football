#!/usr/bin/env python3
"""The League of Plugs — one model, encoding the real rules.

Rules verified with Tiago 2026-07-16. If you need a mechanic that isn't
encoded here, ASK — don't infer it and don't rebuild this ad hoc.

    9 keepers max, 26 total cost. Cost +1 per consecutive year kept.
    Released players go back to the draft pool; ANYONE (old team included)
    may re-draft them, and their cost RESETS TO 1.
    Draft: 11 rounds x 12 teams = 132 picks. Order: 1-6 from the golf
    side-game, 7-12 reverse standings. Order locks Aug 1, keepers Aug 31.
    The 26 cap binds ONLY at keeper selection. Never in-season.
    No in-season roster or trade limits.

PRICE vs VALUE — the core method. Do not collapse these into one number.
    PRICE = KTC. Crowdsourced market perception. Its ONLY job is predicting
            whether they'll accept a trade. It is not truth.
    VALUE = ETR + Dynasty Nerds + FantasyPros. Three experts.
    EDGE  = value - price. Buy the gap, sell into the price.

    NEVER maximize KTC — that optimizes the market's opinion and cannot beat
    it. Maximize analyst VALUE subject to KTC parity.
    My keeper-9  -> optimize on analyst value (who's actually best).
    Their bar / will-they-accept -> model on KTC (what they perceive).

THE KEEPER-9 IS NOT A LINEUP. Do not apply positional filters to it.
    Roster = 20. Keepers = 9. The other 11 come from the 11-round draft.
    The starting lineup (QB/RB/RB/WR/WR/TE/FLEX/FLEX/SF/DEF) is drawn from
    all 20, not from the 9.
    => Keep the 9 best ASSETS regardless of position. A positional gap is a
       DRAFT problem, and the draft fills it at cost 1.
    => Rejecting a trade because it leaves "only 1 RB in the keeper-9" is a
       category error. I made it repeatedly on 2026-07-16 and it silently
       killed good trades (options A and B in the Egbukakeeeeee analysis).
    Report positional shape as INFORMATION (see roster_shape) — never as a
    filter.

WHAT THIS MODEL DOES NOT KNOW (state these when reporting output):
  - Positional scarcity/need for the OTHER team. No number here sees that a
    team with one RB desperately needs a second. Tiago's read on his
    leaguemates is better than any of this.
  - Draft availability. The reset rule makes every keeper decision a
    forecast of "would he last until my next pick?" -- a human read.
  - In-season value. The cap is off after Aug 31.
  - Whether ETR/DN/FP are any good. Three experts agreeing may mean shared
    inputs, not correctness.

Usage:
    from plugs_model import load_league, optimal_nine, at_risk, keeper_bar
    from plugs_model import value_table          # price vs value, all sources
"""
import json, pickle, re, subprocess, sys
from pathlib import Path

CAP = 26
SLOTS = 9
LEAGUE_2026 = "1367160708269117440"
ME = "470104804048236544"          # titi153 -> Jaguar Hunter, roster_id 10
HERE = Path(__file__).parent


def norm(n):
    return re.sub(r"[^a-z]", "", re.sub(r"\s+(jr|sr|ii|iii|iv)\.?$", "", n.lower().strip()))


def ktc():
    """{normalized_name: record}. Run fetch-ktc.py first."""
    p = HERE / "ktc-values.json"
    if not p.exists():
        sys.exit("no ktc-values.json — run reference/fetch-ktc.py first")
    d = json.loads(p.read_text())
    return {norm(x["name"]): x for x in d["players"]}, d


def market_scores():
    """JJ's Market Score, {normalized_name: (pos, score)}, from market-score-2026.csv.

    REDRAFT / 1QB signal — a 0-100 within-position bet on 2026 season value from
    ADP + predictive inputs. NOT dynasty value. It is a SEPARATE axis: it tells
    you "good this year", KTC/experts tell you "cheap". Never fold it into the
    value consensus (that would mix redraft and dynasty). Compare within position
    only; coverage is RB/WR top-120, QB/TE top-180.

    The CSV mirrors the guide's page-272 layout: four position blocks laid side by
    side (QB|RB|WR|TE) with a two-row header. We detect the blocks from the header
    rather than hardcode columns, so it survives reordering. It updates weekly.
    """
    import csv as _csv
    POS = {"QUARTERBACK": "QB", "RUNNING BACK": "RB", "WIDE RECEIVER": "WR", "TIGHT END": "TE"}
    rows = list(_csv.reader(open(HERE.parent / "market-score-2026.csv")))
    blocks = {i: POS[c.strip().upper()] for i, c in enumerate(rows[0]) if c.strip().upper() in POS}
    out = {}
    for c0, pos in blocks.items():
        sub = [rows[1][c] if c < len(rows[1]) else "" for c in range(c0, c0 + 5)]
        pcol = c0 + sub.index("Player")
        scol = c0 + [x.strip().lower() for x in sub].index("market score")
        for r in rows[2:]:
            if pcol < len(r) and r[pcol].strip() and scol < len(r) and r[scol].strip():
                try:
                    out[norm(r[pcol])] = (pos, float(r[scol]))
                except ValueError:
                    pass
    if len(out) < 130:   # loud failure: the export shape changed, don't fail silently
        sys.exit(f"market_scores() parsed only {len(out)} players — check the CSV layout")
    return out


def value_table(fp_ranks=None):
    """Merge all sources onto one honest scale.

    Returns {normalized_name: {name, pos, age, price, etr, dn, fp, value,
                               gap, spread, market_score}}
      price  = KTC value (market perception)
      etr/dn/fp = each expert's rank converted to an IMPLIED market value via
                  KTC's own rank->value curve ("if the market priced him where
                  this expert ranks him, what's he worth?"). Ranks are linear
                  and value is not (JJ p13) — never average raw ranks.
      value  = mean of the three experts' implied values  [DYNASTY]
      gap    = value - price. Positive => experts above market => BUY.
      spread = max-min across experts. THE CONFIDENCE SIGNAL. Low spread +
               big gap = strong. High spread = experts disagree => be neutral.
      market_score = JJ's 0-100 REDRAFT bet on 2026 (separate axis, may be None).
                  The keeper-league edge is the OVERLAP: underpriced on gap
                  (cheap) AND high market_score (good this year).

    fp_ranks: {normalized_name: rank} from the shared Plug Golf Tracker
              'FP Rankings' tab (top 150 only). Optional; omitted -> 2 experts.
    """
    import bisect, csv as _csv
    K, _ = ktc()
    curve = sorted([(p["rank_sf"], p["ktc_sf"]) for p in K.values() if p["rank_sf"]])
    ranks = [c[0] for c in curve]
    vals = [c[1] for c in curve]

    def implied(rank):
        return vals[min(bisect.bisect_left(ranks, rank), len(vals) - 1)]

    dn, dnr = {}, {}
    for r in _csv.DictReader(open(HERE.parent / "dynasty_rankings_sflex.csv")):
        if r["Value"].strip().isdigit():
            dnr[norm(r["Player"])] = int(r["Rank"])
    rows = list(_csv.DictReader(open(HERE.parent / "Dynasty Rankings.csv")))
    pk = list(rows[0].keys())[0]
    etr = {norm(r[pk]): int(r["SF/TE Prem"]) for r in rows if r["SF/TE Prem"].isdigit()}

    ms = market_scores()

    out = {}
    for n, p in K.items():
        srcs = {}
        if n in etr: srcs["etr"] = implied(etr[n])
        if n in dnr: srcs["dn"] = implied(dnr[n])
        if fp_ranks and n in fp_ranks: srcs["fp"] = implied(fp_ranks[n])
        if not srcs: continue
        iv = list(srcs.values())
        val = sum(iv) / len(iv)
        out[n] = {"name": p["name"], "pos": p["pos"], "age": p["age"],
                  "price": p["ktc_sf"], "value": round(val),
                  "gap": round(val - p["ktc_sf"]), "spread": max(iv) - min(iv),
                  "n_sources": len(iv),
                  "market_score": ms[n][1] if n in ms else None, **srcs}
    return out


def optimal_nine(roster, key="ktc"):
    """Best <=9 players maximizing `key` subject to total cost <= 26.

    roster: {name: {"cost": int, "ktc": int, "value": int, ...}}
    key:    "value" for MY keeper decisions (who's actually best).
            "ktc"   for modelling THEIR behaviour (what they perceive).
    returns (total, cost, set_of_names)

    Ignoring position is CORRECT, not a limitation: the keeper-9 is not a
    lineup (see module docstring). Don't "fix" this by adding positional
    constraints.
    """
    dp = {(0, 0): (0, ())}
    for name, p in roster.items():
        w = p.get(key, p["ktc"])
        nd = dict(dp)
        for (n, c), (v, sel) in dp.items():
            if n >= SLOTS:
                continue
            nc = c + p["cost"]
            if nc > CAP:
                continue
            k = (n + 1, nc)
            if k not in nd or nd[k][0] < v + w:
                nd[k] = (v + w, sel + (name,))
        dp = nd
    nine = [(k, v) for k, v in dp.items() if k[0] == SLOTS]
    best = max(nine, key=lambda x: x[1][0]) if nine else max(dp.items(), key=lambda x: x[1][0])
    return best[1][0], best[0][1], set(best[1][1])


# COST IS A CONSTRAINT, NOT A VALUE DISCOUNT. (Tiago, 2026-07-23.)
#
# A player's value is his raw expert value — Kyler Murray is a 4934 QB whether
# he costs 1 or 7. Do NOT discount value by cost. Every attempt to fold cost
# into a single per-player number has distorted reality and made studs look
# like scraps: a 3-year cap sum, a value/cost ratio, a per-team lambda, and
# cap_adjusted (value - 348*cost) — all retired.
#
# Cost is priced EXACTLY, and only, by the knapsack: optimal_nine() maximizes
# raw value subject to sum(cost) <= 26. That already captures everything a
# penalty was trying to approximate — a cost-7 player forces cheaper players
# into the other 8 slots, so a nine built around him scores lower, and the
# knapsack shows it. The Lamar(c7) vs Caleb(c2) tradeoff falls out correctly
# with no linear haircut.
#
# So: compare players by VALUE. Decide keepers/trades by the KNAPSACK delta.
# Never report a cost-adjusted value as if it were the player's worth.


def surplus(player, replacement=1577):
    """Value over a LAST-ROUND pick. Answers KEEP-OR-NOT, never WHO'S-BETTER.

    Keep 9 -> 11 picks. Keep 8 -> 12 picks, but THE EXTRA IS A LAST-ROUNDER
    (Tiago, 2026-07-16) — so the marginal keeper competes against FA scraps,
    not against my 1.04. Keeping 9 is therefore essentially always right, even
    with a weak 9th man.

    Measuring against an early pick is WRONG and made me recommend cutting
    Alec Pierce (correct: +3023, keep).

    A fixed baseline is a constant offset — it cannot reorder players. This is
    NOT a cost adjustment (cost is the knapsack's job); it only answers whether
    a 9th keeper beats a last-round pick.
    """
    return player["value"] - replacement


def roster_shape(roster, selection=None):
    """Positional composition — REPORT THIS, never filter on it.

    A gap here is a draft problem, not a reason to reject a trade: 11 draft
    rounds fill the other 11 roster spots, and drafted players cost 1.

    Returns {"QB": n, "RB": n, "WR": n, "TE": n} for the selection (default:
    the whole roster).
    """
    names = selection if selection is not None else roster.keys()
    out = {}
    for n in names:
        p = roster[n]["pos"]
        out[p] = out.get(p, 0) + 1
    return out


def draft_fills(pool, pos, top=5):
    """What the draft could give me at `pos`, at cost 1.

    Use this INSTEAD of rejecting a trade for a positional gap. pool is the
    league-wide at-risk list (see at_risk across all teams) plus rookies.
    """
    c = [(p["ktc"], n) for n, p in pool.items() if p["pos"] == pos]
    return sorted(c, reverse=True)[:top]


def keeper_bar(roster):
    """KTC of the weakest player in the optimal nine. An incoming player is
    worth nothing to this team unless he beats it."""
    _, _, sel = optimal_nine(roster)
    return min(roster[n]["ktc"] for n in sel)


def at_risk(roster):
    """Players outside the optimal nine.

    DO NOT read this as "free value they'll lose for nothing" — that was
    wrong (Tiago, 2026-07-16). Owners CONVERT at-risk value: they keep him,
    sell him to a weaker team for picks, or package him 2-for-1 to upgrade.

      cheap + wanted  -> gets TRADED, never reaches the pool. An auction, and
                         my bar is the league's 2nd-highest so I usually lose
                         it (Shough: 11 takers; I bid +855, Shrimp +2275).
      expensive       -> genuinely stranded; the COST strands him. This is
                         what actually hits the pool (McCaffrey c9: 3 takers,
                         DJ Moore c8: 1 taker). Better DRAFTED at cost 1 than
                         traded for at cost 9.
      near the bar    -> NOISE. Pearsall was 76 KTC below JohnnyG's #9 and
                         clearly better by expert value. Owner preference
                         decides; ask Tiago.

    Even stranded players have a buyer: a REBUILDING team with cap slack can
    absorb them cheap, hold through the Aug 31 lock, and flip them in-season
    when the cap no longer binds.
    """
    _, _, sel = optimal_nine(roster)
    return {n: p for n, p in roster.items() if n not in sel}


def keep_or_redraft(player, my_next_pick_overall, pool_rank):
    """The real keeper question under the reset rule.

    Keeping costs `player['cost']`. Releasing costs 0 but risks losing him.
    Returns a string verdict — deliberately not a number, because the input
    that matters (will he last?) is a human read, not a KTC lookup.
    """
    if player["cost"] <= 1:
        return "KEEP — cost 1, no decision to make"
    if pool_rank is None:
        return "ASK — need a read on whether he'd last to your next pick"
    if pool_rank < my_next_pick_overall:
        return f"KEEP — he'd be gone by pick {my_next_pick_overall}; cost {player['cost']} buys certainty"
    return (f"RELEASE + RE-DRAFT — likely available at your pick; "
            f"re-acquiring resets him to cost 1, saving {player['cost'] - 1}")


def load_league(costs_pkl="/tmp/k2.pkl"):
    """Merge live KTC onto rosters+costs.

    Roster costs come from the plug-golf 'Roster Costs' sheet, which is built
    from the 2025 league id (the GH Action is stale). Harmless while 2026 is
    pre_draft with identical rosters — re-verify against the Sleeper API
    before trusting for a real 2026 decision.
    """
    K, meta = ktc()
    teams = pickle.load(open(costs_pkl, "rb"))
    out = {}
    for t, ps in teams.items():
        r = {}
        for n, tup in ps.items():
            k = K.get(norm(n))
            if not k:
                continue
            r[k["name"]] = {"pos": k["pos"], "ktc": k["ktc_sf"], "cost": tup[2],
                            "age": k["age"], "rank": k["rank_sf"]}
        out[t] = r
    return out, meta["fetched"]


if __name__ == "__main__":
    league, fetched = load_league()
    print(f"KTC fetched {fetched}\n")
    print(f"{'team':30} {'opt9':>7} {'cost':>5} {'bar':>5} {'at-risk':>8}")
    for t, ps in sorted(league.items(), key=lambda x: -optimal_nine(x[1])[0]):
        v, c, sel = optimal_nine(ps)
        ar = at_risk(ps)
        me = " *" if "Jaguar" in t else "  "
        print(f"{t:28}{me} {v:>7} {c:>5} {keeper_bar(ps):>5} {sum(p['ktc'] for p in ar.values()):>8}")
