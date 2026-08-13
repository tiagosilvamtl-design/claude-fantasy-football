#!/usr/bin/env python3
"""Once-a-day refresh for the Plugs model.

Pulls the volatile data ONCE and writes two artifacts every later question reads:

    reference/snapshot.json    <- the only thing load_league() reads
    reference/league-brief.md  <- human-readable "state of the league"

Sources (rosters/cost/picks come from the SHEET the daily plug-golf Action
refreshes — never the Sleeper API from here):

    sheet "Roster Costs"  -> who's on each team + keeper cost, and each team's
                             draft picks as PICK rows under its players
    sheet "FP Rankings"   -> FantasyPros expert ranks (3rd VALUE source)
    fetch-ktc.py          -> KTC price (regenerates ktc-values.json)
    local CSVs            -> ETR / Dynasty Nerds / Market Score (via value_table)

Run it directly, or let plugs_model.load_league() run it automatically when the
snapshot is >24h stale. Reads the Google Sheet with ../plug-golf/credentials.json
(local, gitignored).
"""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials

from plugs_model import (CAP, LEAGUE_2026, ME, SLOTS, at_risk, keeper_bar, norm,
                         optimal_nine, value_table)

HERE = Path(__file__).parent
CREDS = HERE.parent.parent / "plug-golf" / "credentials.json"
SHEET_ID = "1Au0mnk2i76NZ1bF4v_V3YMeDtEUso0VEE7IXV12w8O4"
SNAPSHOT = HERE / "snapshot.json"
BRIEF = HERE / "league-brief.md"
# My team is identified by stable user_id (ME), NOT by display name — the name
# changes when Tiago renames the team on Sleeper. This is only a last-known
# fallback if the live lookup fails; resolve_my_team() is the source of truth.
MY_TEAM_FALLBACK = "Des Jaguars pis Bowser"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive.readonly"]


def resolve_my_team():
    """My current team NAME, looked up from Sleeper by stable user_id so a rename
    can't silently empty the brief. Uses the same team_name-or-display_name rule
    roster_costs.py uses to build the sheet, so the two match. Falls back to the
    last-known name on any failure."""
    import urllib.request
    try:
        with urllib.request.urlopen(
                f"https://api.sleeper.app/v1/league/{LEAGUE_2026}/users", timeout=30) as r:
            for u in json.load(r):
                if u.get("user_id") == ME:
                    return ((u.get("metadata") or {}).get("team_name")
                            or u.get("display_name") or MY_TEAM_FALLBACK)
    except Exception as e:
        print(f"warn: couldn't resolve my team from Sleeper ({e}); using fallback "
              f"'{MY_TEAM_FALLBACK}'", file=sys.stderr)
    return MY_TEAM_FALLBACK


# ── Sheet reads (stride-4 side-by-side blocks; see CLAUDE.md) ─────────────────

def _open_sheet():
    gc = gspread.authorize(Credentials.from_service_account_file(str(CREDS), scopes=SCOPES))
    return gc.open_by_key(SHEET_ID)


def parse_blocks(vals, fields):
    """Parse a Player|... side-by-side layout into {team_label: [dict per row]}.

    row 0 = team labels every 4 cols; row 1 = subheaders; rows 2+ = data.
    `fields` maps output key -> column offset within the 4-wide block.
    """
    if not vals:
        return {}
    row0 = vals[0]
    out = {}
    for base in range(0, len(row0), 4):
        label = row0[base].strip()
        if not label:
            continue
        rows = []
        for r in vals[2:]:
            if base >= len(r) or not str(r[base]).strip():
                continue
            rec = {}
            for key, off in fields.items():
                col = base + off
                rec[key] = r[col].strip() if col < len(r) else ""
            rows.append(rec)
        out[label] = rows
    return out


def fp_ranks_from_sheet(sh):
    """{norm(name): rank} from the FP Rankings tab (columns Rank, Player, ...)."""
    vals = sh.worksheet("FP Rankings").get_all_values()
    out = {}
    for r in vals[1:]:
        if len(r) >= 2 and r[0].strip().isdigit() and r[1].strip():
            out[norm(r[1])] = int(r[0])
    return out


# ── Build ────────────────────────────────────────────────────────────────────

def build():
    print("Refreshing KTC (fetch-ktc.py)...", file=sys.stderr)
    subprocess.run([sys.executable, str(HERE / "fetch-ktc.py")], check=True)

    print("Reading sheet (Roster Costs [+picks], FP Rankings)...", file=sys.stderr)
    sh = _open_sheet()
    # Roster Costs holds players AND picks: pick rows are marked pos == "PICK",
    # with the round in the Player cell (e.g. "R5") and origin in the Cost cell.
    raw = parse_blocks(sh.worksheet("Roster Costs").get_all_values(),
                       {"name": 0, "pos": 1, "cost": 2})
    fp = fp_ranks_from_sheet(sh)

    vt = value_table(fp_ranks=fp)
    with open(HERE / "ktc-values.json") as f:
        ktc_fetched = json.load(f)["fetched"]

    teams, picks, unmatched = {}, {}, {}
    for team, entries in raw.items():
        merged = {}
        tpicks = []
        miss = []
        for e in entries:
            if e["pos"].strip().upper() == "PICK":
                label = e["name"].strip()  # "1.04" (board locked) or "R5" (fallback)
                rnd = int(label.split(".")[0]) if "." in label else int(label.lstrip("Rr"))
                tpicks.append({"round": rnd, "board": label, "from": e["cost"]})
                continue
            v = vt.get(norm(e["name"]))
            if not v:
                if e["pos"].strip().upper() != "DEF":  # DEFs have no KTC dynasty value; expected
                    miss.append(e["name"])
                continue
            try:
                cost = int(e["cost"])
            except ValueError:
                cost = 1
            merged[v["name"]] = {
                "pos": v["pos"], "age": v["age"], "cost": cost,
                "ktc": v["price"], "value": v["value"], "gap": v["gap"],
                "spread": v["spread"], "market_score": v["market_score"],
                "rank": v.get("rank"),
            }
        teams[team] = merged
        picks[team] = tpicks
        if miss:
            unmatched[team] = miss

    snap = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "ktc_fetched": ktc_fetched,
        "teams": teams,
        "picks": picks,
        "unmatched": unmatched,
    }
    SNAPSHOT.write_text(json.dumps(snap, indent=1))
    print(f"Wrote {SNAPSHOT.name}", file=sys.stderr)

    if unmatched:
        n = sum(len(v) for v in unmatched.values())
        print(f"note: {n} non-DEF players outside KTC's ranked pool (deep bench; "
              f"can't make an optimal nine, so dropped). Check for a name mismatch if a "
              f"starter appears here:", file=sys.stderr)
        for team, names in unmatched.items():
            print(f"  {team}: {', '.join(names)}", file=sys.stderr)

    my_team = resolve_my_team()
    if my_team not in teams:
        print(f"warn: my team '{my_team}' not in the snapshot (sheet may predate a "
              f"rename) — brief's roster/picks sections will be empty this run", file=sys.stderr)
    write_brief(snap, my_team)
    print(f"Wrote {BRIEF.name}", file=sys.stderr)
    return snap


def write_brief(snap, my_team):
    teams = {t: {n: p for n, p in ps.items()} for t, ps in snap["teams"].items()}
    lines = [f"# League of Plugs — brief",
             f"_snapshot {snap['fetched_at']} · KTC {snap['ktc_fetched']}_", "",
             "## Optimal nine by team (value; cost/slack/bar/at-risk)", "",
             "| Team | opt9 | cost | slack | bar | at-risk KTC |",
             "|---|--:|--:|--:|--:|--:|"]
    ranked = sorted(teams.items(), key=lambda x: -optimal_nine(x[1])[0]) if teams else []
    for t, ps in ranked:
        if not ps:
            continue
        v, c, _ = optimal_nine(ps)
        ar = at_risk(ps)
        me = " ⭐" if t == my_team else ""
        lines.append(f"| {t}{me} | {v} | {c} | {CAP - c:+d} | {keeper_bar(ps)} | "
                     f"{sum(p['ktc'] for p in ar.values())} |")

    mine = teams.get(my_team, {})
    if mine:
        _, _, nine = optimal_nine(mine)
        lines += ["", f"## {my_team} — roster (KEEP = optimal nine)", "",
                  "| Keep | Player | Pos | Cost | KTC | Value | Gap |",
                  "|:--:|---|:--:|--:|--:|--:|--:|"]
        for n, p in sorted(mine.items(), key=lambda x: (x[1]["cost"], -x[1]["ktc"])):
            keep = "✅" if n in nine else ""
            lines.append(f"| {keep} | {n} | {p['pos']} | {p['cost']} | {p['ktc']} | "
                         f"{p['value']} | {p['gap']:+d} |")

    mypicks = snap["picks"].get(my_team, [])
    if mypicks:
        held = ", ".join(p.get("board", f"R{p['round']}")
                         + ("" if p["from"] in ("own", "") else f" (from {p['from']})")
                         for p in mypicks)
        lines += ["", f"## {my_team} — picks held", "", held]

    BRIEF.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    build()
