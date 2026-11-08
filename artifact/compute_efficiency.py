"""Compute each team's FDR efficiency rating from the stored season data.

Efficiency = points per match / average fixture difficulty faced, with each
team's last five matches weighted at RECENT_WEIGHT times an earlier match, so
the rating follows current form rather than treating August as evidence about
next Saturday.

Reads:  "FPL Data"/bootstrap_static.json, "FPL Data"/fixtures.json
Writes: artifact/data/efficiency.json

Run directly:  python artifact/compute_efficiency.py
"""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
DATA_IN = os.path.join(PROJECT, "FPL Data")
DATA_OUT = os.path.join(HERE, "data")

RECENT_WEIGHT = 3   # a match in the last five counts this many times an earlier one
RECENT_N = 5


def load(name):
    with open(os.path.join(DATA_IN, name), encoding="utf-8") as f:
        return json.load(f)


def main():
    bootstrap = load("bootstrap_static.json")
    fixtures = load("fixtures.json")

    teams = {t["id"]: t for t in bootstrap["teams"]}
    played = [f for f in fixtures
              if f.get("finished") and f.get("team_h_score") is not None]

    if not played:
        print("No finished fixtures in the stored data - efficiency.json left unchanged.")
        print("(A new season has no results yet; keep last season's ratings until it does.)")
        return

    # per-team match log, oldest first
    log = {tid: [] for tid in teams}
    for f in sorted(played, key=lambda x: ((x.get("event") or 0), x.get("kickoff_time") or "")):
        h, a = f["team_h"], f["team_a"]
        hs, as_ = f["team_h_score"], f["team_a_score"]
        for tid, gf, ga, fdr in ((h, hs, as_, f["team_h_difficulty"]),
                                 (a, as_, hs, f["team_a_difficulty"])):
            pts = 3 if gf > ga else (1 if gf == ga else 0)
            log[tid].append({"pts": pts, "fdr": fdr})

    out = {
        "season_matches": max(len(v) for v in log.values()),
        "recent_weight": RECENT_WEIGHT,
        "recent_n": RECENT_N,
        "teams": {},
    }

    for tid, games in log.items():
        if not games:
            continue
        weights = ([1] * max(0, len(games) - RECENT_N)
                   + [RECENT_WEIGHT] * min(RECENT_N, len(games)))
        total = sum(weights)
        ppm_w = sum(w * g["pts"] for w, g in zip(weights, games)) / total
        fdr_w = sum(w * g["fdr"] for w, g in zip(weights, games)) / total
        ppm = sum(g["pts"] for g in games) / len(games)
        fdr = sum(g["fdr"] for g in games) / len(games)
        out["teams"][teams[tid]["short_name"]] = {
            "name": teams[tid]["name"],
            "efficiency": round(ppm_w / fdr_w, 3) if fdr_w else 0,
            "efficiency_flat": round(ppm / fdr, 3) if fdr else 0,
            "points_per_match": round(ppm, 2),
            "avg_fdr": round(fdr, 2),
            "matches": len(games),
        }

    os.makedirs(DATA_OUT, exist_ok=True)
    path = os.path.join(DATA_OUT, "efficiency.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)

    print(f"Efficiency ratings for {len(out['teams'])} teams -> {path}")
    ranked = sorted(out["teams"].items(), key=lambda kv: -kv[1]["efficiency"])
    for short, r in ranked:
        print(f"  {short:4s} {r['efficiency']:.3f}  (flat {r['efficiency_flat']:.3f})")


if __name__ == "__main__":
    main()
