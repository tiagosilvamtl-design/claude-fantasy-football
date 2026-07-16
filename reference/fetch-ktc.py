#!/usr/bin/env python3
"""Fetch KeepTradeCut dynasty values into reference/ktc-values.json.

KTC renders its rankings client-side, so the HTML table is empty — but the page
ships the full dataset in a `playersArray = [...]` literal in the source. We read
that. Public page, read-only, personal use; cached locally so we hit it once.

    reference/fetch-ktc.py            # refresh
    reference/fetch-ktc.py --show 20  # refresh + print top 20 superflex

Output: {"fetched": iso8601, "players": [{name, pos, team, age, ktc_sf, ktc_1qb,
         rank_sf, posrank_sf, rookie}], "picks": [{name, ktc_sf}]}

WHICH VALUE TO USE — both my leagues are superflex, NO TE premium:
  superflexValues.value  <- THIS ONE. superflex, no TE premium.
  oneQBValues.value      <- 1QB. Not my leagues.
  superflexValues.tep / .tepp / .teppp <- TE-premium variants. NOT my leagues.
"""
import json, re, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

URL = "https://keeptradecut.com/dynasty-rankings"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
OUT = Path(__file__).parent / "ktc-values.json"


def fetch():
    # curl, not urllib: macOS system python is linked against LibreSSL and fails
    # the TLS handshake with KTC (TLSV1_ALERT_PROTOCOL_VERSION).
    r = subprocess.run(["curl", "-sS", "--fail", "-A", UA, URL],
                       capture_output=True, text=True, timeout=90)
    if r.returncode != 0:
        sys.exit(f"curl failed: {r.stderr.strip()}")
    html = r.stdout
    m = re.search(r"playersArray\s*=\s*(\[.*?\]);", html, re.S)
    if not m:
        sys.exit("playersArray not found — KTC changed their page shape. "
                 "Inspect the source and update this regex.")
    arr = json.loads(m.group(1))

    players, picks = [], []
    for p in arr:
        sf = p.get("superflexValues", {}) or {}
        one = p.get("oneQBValues", {}) or {}
        rec = {
            "name": p["playerName"],
            "pos": p["position"],
            "team": p.get("team"),
            "age": p.get("age"),
            "ktc_sf": sf.get("value", 0),
            "ktc_1qb": one.get("value", 0),
            "rank_sf": sf.get("rank"),
            "posrank_sf": sf.get("positionalRank"),
            "rookie": p.get("rookie", False),
        }
        (picks if p["position"] == "RDP" else players).append(rec)

    players.sort(key=lambda x: -x["ktc_sf"])
    picks.sort(key=lambda x: -x["ktc_sf"])
    data = {"fetched": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source": URL, "players": players, "picks": picks}
    OUT.write_text(json.dumps(data, indent=1))
    return data


def norm(n):
    """Match KTC names to Sleeper/FantasyPros/ETR spellings.
    Needed: ETR writes 'Treveyon Henderson', Sleeper 'TreVeyon Henderson';
    suffixes (Jr./III) appear inconsistently across all three sources."""
    return re.sub(r"[^a-z]", "", re.sub(r"\s+(jr|sr|ii|iii|iv)\.?$", "", n.lower().strip()))


def load():
    """Return {normalized_name: record}. Run the script first if missing."""
    d = json.loads(OUT.read_text())
    return {norm(p["name"]): p for p in d["players"]}, d


if __name__ == "__main__":
    d = fetch()
    print(f"wrote {OUT}  ({len(d['players'])} players, {len(d['picks'])} picks)")
    if "--show" in sys.argv:
        n = int(sys.argv[sys.argv.index("--show") + 1])
        print(f"\ntop {n} superflex:")
        for p in d["players"][:n]:
            print(f"  {p['ktc_sf']:>5}  {p['name']:24} {p['pos']:3} age {p['age']}")
        print("\n2026 picks:")
        for p in d["picks"]:
            if p["name"].startswith("2026"):
                print(f"  {p['ktc_sf']:>5}  {p['name']}")
