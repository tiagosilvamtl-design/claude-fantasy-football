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

WHAT THIS MODEL DOES NOT KNOW (state these when reporting output):
  - Lineup slots. It maximizes KTC, not starting-lineup points. A nine of
    nine WRs would score great here and be unstartable.
  - Positional scarcity/need for the OTHER team. KTC can't see that a team
    with one RB desperately needs a second.
  - Draft availability. The reset rule makes every keeper decision a
    forecast of "would he last until my next pick?" -- which is a human
    read, not a number this file has.
  - In-season value. The cap is off after Aug 31, so expensive assets are
    worth full market then.

Usage:
    from plugs_model import load_league, optimal_nine, at_risk, keeper_bar
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


def optimal_nine(roster):
    """Best <=9 players maximizing KTC subject to total cost <= 26.

    roster: {name: {"cost": int, "ktc": int, ...}}
    returns (value, cost, set_of_names)

    NOTE: this is the right model for cap feasibility and the WRONG model
    for lineup construction — it has no concept of starting slots.
    """
    dp = {(0, 0): (0, ())}
    for name, p in roster.items():
        nd = dict(dp)
        for (n, c), (v, sel) in dp.items():
            if n >= SLOTS:
                continue
            nc = c + p["cost"]
            if nc > CAP:
                continue
            k = (n + 1, nc)
            if k not in nd or nd[k][0] < v + p["ktc"]:
                nd[k] = (v + p["ktc"], sel + (name,))
        dp = nd
    nine = [(k, v) for k, v in dp.items() if k[0] == SLOTS]
    best = max(nine, key=lambda x: x[1][0]) if nine else max(dp.items(), key=lambda x: x[1][0])
    return best[1][0], best[0][1], set(best[1][1])


def keeper_bar(roster):
    """KTC of the weakest player in the optimal nine. An incoming player is
    worth nothing to this team unless he beats it."""
    _, _, sel = optimal_nine(roster)
    return min(roster[n]["ktc"] for n in sel)


def at_risk(roster):
    """Players outside the optimal nine — released unless traded.

    IMPORTANT: released != worthless. They enter the draft pool at cost 1,
    and the owner may re-draft them. Their value to the owner is
    (what a trade fetches) vs (odds of re-drafting them), which depends on
    draft position. For a team picking late, that's near zero. For a team
    picking early, it may be better to let him go and take him at cost 1.
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
