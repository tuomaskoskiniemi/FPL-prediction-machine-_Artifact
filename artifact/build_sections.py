"""Build the data-driven regions of the overview page from current season data.

Every table on the page is regenerated here from the live API payloads, so the
page always shows the season that is actually being played. Each function
returns the HTML for one marked region in fpl_overview.html.

Called by refresh_artifact.py; not usually run directly.
"""

import html as _html

RECENT_WEIGHT = 3   # a match in the last five counts this many times an earlier one
RECENT_N = 5
DEFENCE_MARK = 8    # teams with fewest goals conceded carry the "D" marker

FORMATIONS = {
    "3-4-3": (3, 4, 3), "4-4-2": (4, 4, 2), "4-3-3": (4, 3, 3), "3-5-2": (3, 5, 2),
    "5-3-2": (5, 3, 2), "5-4-1": (5, 4, 1), "4-5-1": (4, 5, 1),
}
POSITIONS = (("GKP", 1, "Goalkeepers"), ("DEF", 2, "Defenders"),
             ("MID", 3, "Midfielders"), ("FWD", 4, "Forwards"))


def esc(text):
    return (_html.escape(str(text), quote=True)
            .encode("ascii", "xmlcharrefreplace").decode("ascii"))


def fdr_class(value):
    return f"f{int(value)}" if 1 <= int(value) <= 5 else "f3"


# --------------------------------------------------------------------- teams
def team_table(bootstrap, fixtures):
    """League table plus the efficiency model, richest-first by league points."""
    teams = {t["id"]: t for t in bootstrap["teams"]}
    played = [f for f in fixtures
              if f.get("finished") and f.get("team_h_score") is not None]
    played.sort(key=lambda f: ((f.get("event") or 0), f.get("kickoff_time") or ""))

    log = {tid: [] for tid in teams}
    for f in played:
        h, a = f["team_h"], f["team_a"]
        hs, as_ = f["team_h_score"], f["team_a_score"]
        for tid, gf, ga, fdr in ((h, hs, as_, f["team_h_difficulty"]),
                                 (a, as_, hs, f["team_a_difficulty"])):
            log[tid].append({"gf": gf, "ga": ga, "fdr": fdr,
                             "pts": 3 if gf > ga else (1 if gf == ga else 0)})

    rows = []
    for tid, games in log.items():
        if not games:
            continue
        weights = ([1] * max(0, len(games) - RECENT_N)
                   + [RECENT_WEIGHT] * min(RECENT_N, len(games)))
        total = sum(weights)
        ppm_w = sum(w * g["pts"] for w, g in zip(weights, games)) / total
        fdr_w = sum(w * g["fdr"] for w, g in zip(weights, games)) / total
        ppm = sum(g["pts"] for g in games) / len(games)
        avg_fdr = sum(g["fdr"] for g in games) / len(games)
        eff = ppm_w / fdr_w if fdr_w else 0
        eff_flat = ppm / avg_fdr if avg_fdr else 0
        gf = sum(g["gf"] for g in games)
        ga = sum(g["ga"] for g in games)
        rows.append({
            "id": tid, "short": teams[tid]["short_name"], "name": teams[tid]["name"],
            "played": len(games),
            "won": sum(1 for g in games if g["pts"] == 3),
            "drawn": sum(1 for g in games if g["pts"] == 1),
            "lost": sum(1 for g in games if g["pts"] == 0),
            "gf": gf, "ga": ga, "gd": gf - ga,
            "pts": sum(g["pts"] for g in games),
            "form": "".join("W" if g["pts"] == 3 else ("D" if g["pts"] == 1 else "L")
                            for g in games[-5:]),
            "pts5": sum(g["pts"] for g in games[-5:]),
            "games5": len(games[-5:]),
            "ppm": ppm, "avg_fdr": avg_fdr, "eff": eff, "eff_flat": eff_flat,
            "adjusted": avg_fdr / eff if eff else None,
        })

    rows.sort(key=lambda r: (-r["pts"], -r["gd"], -r["gf"]))
    for rank, row in enumerate(rows, 1):
        row["rank"] = rank
    for row in sorted(rows, key=lambda r: r["ga"])[:DEFENCE_MARK]:
        row["defence_mark"] = True
    return rows


def render_form(form):
    chips = "".join(f'<span class="chip chip-{c.lower()}" aria-hidden="true">{c}</span>'
                    for c in form)
    return (f'<span class="form" role="img" aria-label="Last five results: {form}">'
            f"{chips}</span>")


def standings_rows(rows):
    best_eff = max((r["eff"] for r in rows), default=1) or 1
    out = []
    for r in rows:
        mark = ('<span class="dmark" title="One of the eight teams conceding fewest'
                ' goals">D</span>' if r.get("defence_mark")
                else '<span class="dmark-empty">&#8212;</span>')
        adjusted = f'{r["adjusted"]:.2f}' if r["adjusted"] else "&#8212;"
        out.append(
            "<tr>\n"
            f'<td class="num rank">{r["rank"]}</td>\n'
            f'<td class="team"><span class="short">{esc(r["short"])}</span>'
            f' <span class="full">{esc(r["name"])}</span></td>\n'
            f'<td class="mid">{mark}</td>\n'
            f'<td class="num">{r["won"]}&#8211;{r["drawn"]}&#8211;{r["lost"]}</td>\n'
            f'<td class="num">{r["gf"]}</td>\n<td class="num">{r["ga"]}</td>\n'
            f'<td class="num">{"+" if r["gd"] > 0 else ""}{r["gd"]}</td>\n'
            f'<td class="num strong">{r["pts"]}</td>\n'
            f"<td>{render_form(r['form'])}</td>\n"
            f'<td class="num">{r["ppm"]:.2f}</td>\n'
            f'<td class="num">{r["avg_fdr"]:.2f}</td>\n'
            f'<td class="barcell" title="{esc(r["name"])}: {r["eff"]:.3f} points per match'
            f' per unit of fixture difficulty, last five matches weighted triple">\n'
            f'  <span class="barwrap"><span class="bar"><span class="bar-fill"'
            f' style="width:{r["eff"] / best_eff * 100:.1f}%"></span></span>'
            f'<span class="barval">{r["eff"]:.3f}</span></span>\n</td>\n'
            f'<td class="num quiet">{r["eff_flat"]:.3f}</td>\n'
            f'<td class="num strong">{adjusted}</td>\n'
            "</tr>")
    return "\n".join(out)


# ------------------------------------------------------------------- players
def player_rows(bootstrap, defence_ids):
    teams = {t["id"]: t for t in bootstrap["teams"]}
    types = {t["id"]: t for t in bootstrap["element_types"]}
    players = []
    for p in bootstrap["elements"]:
        players.append({
            "id": p["id"], "web": p["web_name"],
            "team": teams[p["team"]]["short_name"], "team_id": p["team"],
            "pos": types[p["element_type"]]["singular_name_short"],
            "pos_id": p["element_type"], "cost": p["now_cost"] / 10,
            "pts": p["total_points"], "minutes": p["minutes"],
            "goals": p["goals_scored"], "assists": p["assists"],
            "status": p["status"], "defence": p["team"] in defence_ids,
        })
    return players


def last5_totals(players, player_details):
    """Add each player's totals over their last five matches, where known."""
    out = []
    for p in players:
        history = (player_details.get(str(p["id"])) or {}).get("history") or []
        history = sorted(history, key=lambda h: ((h.get("round") or 0),
                                                 h.get("kickoff_time") or ""))[-RECENT_N:]
        if not history:
            continue
        q = dict(p)
        q.update(pts5=sum(h["total_points"] for h in history),
                 minutes5=sum(h["minutes"] for h in history),
                 goals5=sum(h["goals_scored"] for h in history),
                 assists5=sum(h["assists"] for h in history),
                 games5=len(history),
                 rounds=[history[0].get("round"), history[-1].get("round")])
        out.append(q)
    return out


def position_blocks(players, key_pts, key_min, key_goals, key_assists, limit=10):
    blocks = []
    for label, pos_id, title in POSITIONS:
        ranked = sorted((p for p in players if p["pos_id"] == pos_id),
                        key=lambda p: (-p[key_pts], -p[key_min]))[:limit]
        trs = []
        for i, p in enumerate(ranked, 1):
            mark = (' <span class="dmark small" title="Plays for one of the eight teams'
                    ' conceding fewest goals">D</span>'
                    if p["defence"] and label in ("DEF", "GKP") else "")
            trs.append(
                "<tr>\n"
                f'<td class="num rank">{i}</td>\n'
                f'<td class="team"><span class="short">{esc(p["web"])}</span>{mark}</td>\n'
                f'<td class="mid quiet">{esc(p["team"])}</td>\n'
                f'<td class="num">&pound;{p["cost"]:.1f}m</td>\n'
                f'<td class="num strong">{p[key_pts]}</td>\n'
                f'<td class="num">{p[key_min]:,}</td>\n'
                f'<td class="num">{p[key_goals]}</td>\n'
                f'<td class="num">{p[key_assists]}</td>\n'
                "</tr>")
        blocks.append(
            '<div class="pos-block">\n'
            f"<h4>{title}</h4>\n"
            '<div class="scroll">\n<table class="data compact">\n'
            '<thead><tr><th class="num">#</th><th>Player</th><th>Team</th>'
            '<th class="num">Price</th><th class="num">Pts</th><th class="num">Mins</th>'
            '<th class="num">G</th><th class="num">A</th></tr></thead>\n'
            f"<tbody>\n{''.join(trs)}\n</tbody>\n</table>\n</div>\n</div>")
    return "\n".join(blocks)


# ---------------------------------------------------------------- formations
def formation_table(players, key="pts"):
    by_pos = {label: sorted((p for p in players if p["pos_id"] == pos_id),
                            key=lambda p: -p[key])
              for label, pos_id, _ in POSITIONS}
    shapes = []
    for name, (d, m, f) in FORMATIONS.items():
        xi = (by_pos["GKP"][:1] + by_pos["DEF"][:d]
              + by_pos["MID"][:m] + by_pos["FWD"][:f])
        if len(xi) < 11:
            continue
        shapes.append({"name": name, "xi": xi,
                       "pts": sum(p[key] for p in xi),
                       "value": sum(p["cost"] for p in xi)})
    shapes.sort(key=lambda s: -s["pts"])
    return shapes


def formation_rows(shapes):
    best = shapes[0]["pts"] if shapes else 1
    out = []
    for i, s in enumerate(shapes):
        delta = s["pts"] - best
        tag = ' <span class="tag">best</span>' if i == 0 else ""
        out.append(
            f'<tr class="{"formation-best" if i == 0 else ""}">\n'
            f'<td class="fname">{esc(s["name"])}{tag}</td>\n'
            f'<td class="barcell wide" title="Best possible eleven in {esc(s["name"])}:'
            f' {s["pts"]} points">\n'
            f'  <span class="barwrap"><span class="bar"><span class="bar-fill"'
            f' style="width:{s["pts"] / best * 100 if best else 0:.1f}%"></span></span>'
            f'<span class="barval">{s["pts"]}</span></span>\n</td>\n'
            f'<td class="num">{"&#8212;" if delta == 0 else delta}</td>\n'
            f'<td class="num">{"&#8212;" if delta == 0 else f"{delta / best * 100:.1f}%"}</td>\n'
            f'<td class="num">&pound;{s["value"]:.1f}m</td>\n'
            "</tr>")
    return "\n".join(out)


def xi_list(shape):
    return "\n".join(
        f'<li><span class="xi-pos">{esc(p["pos"])}</span>\n'
        f'<span class="xi-name">{esc(p["web"])}</span>\n'
        f'<span class="xi-team">{esc(p["team"])}</span>\n'
        f'<span class="xi-pts">{p["pts"]}</span></li>'
        for p in shape["xi"])


# ------------------------------------------------- difficulty against reality
def match_log(bootstrap, fixtures):
    """Every played team-match: who, against whom, at what difficulty, for what."""
    teams = {t["id"]: t for t in bootstrap["teams"]}
    played = [f for f in fixtures
              if f.get("finished") and f.get("team_h_score") is not None]
    played.sort(key=lambda f: ((f.get("event") or 0), f.get("kickoff_time") or ""))
    log = []
    for f in played:
        h, a = f["team_h"], f["team_a"]
        hs, as_ = f["team_h_score"], f["team_a_score"]
        for tid, opp, home, gf, ga, fdr in (
                (h, a, True, hs, as_, f["team_h_difficulty"]),
                (a, h, False, as_, hs, f["team_a_difficulty"])):
            log.append({
                "team": tid, "short": teams[tid]["short_name"],
                "opp": teams[opp]["short_name"], "home": home,
                "gf": gf, "ga": ga, "fdr": fdr, "gw": f.get("event"),
                "pts": 3 if gf > ga else (1 if gf == ga else 0),
            })
    return log


def difficulty_baseline(log):
    """What each difficulty level has actually been worth, league-wide."""
    levels = {}
    for m in log:
        d = levels.setdefault(m["fdr"], {"fdr": m["fdr"], "n": 0, "w": 0, "d": 0,
                                         "l": 0, "pts": 0, "gf": 0, "ga": 0})
        d["n"] += 1
        d["pts"] += m["pts"]
        d["gf"] += m["gf"]
        d["ga"] += m["ga"]
        d["w" if m["pts"] == 3 else ("d" if m["pts"] == 1 else "l")] += 1
    rows = sorted(levels.values(), key=lambda r: r["fdr"])
    for r in rows:
        r["ppm"] = r["pts"] / r["n"]
        r["gf_avg"] = r["gf"] / r["n"]
        r["ga_avg"] = r["ga"] / r["n"]
    return rows


def baseline_rows(rows):
    out = []
    for r in rows:
        total = r["n"]
        segs = "".join(
            f'<span class="seg seg-{cls}" style="width:{r[k] / total * 100:.1f}%"'
            f' title="{r[k]} {name}"></span>'
            for k, cls, name in (("w", "w", "won"), ("d", "d", "drawn"), ("l", "l", "lost"))
            if r[k])
        out.append(
            "<tr>\n"
            f'<td><span class="fx-chip {fdr_class(r["fdr"])}">Difficulty <i>{r["fdr"]}</i>'
            "</span></td>\n"
            f'<td class="num">{r["n"]}</td>\n'
            f'<td class="barcell wide"><span class="stack">{segs}</span></td>\n'
            f'<td class="num">{r["w"]}</td>\n<td class="num">{r["d"]}</td>\n'
            f'<td class="num">{r["l"]}</td>\n'
            f'<td class="num strong">{r["ppm"]:.2f}</td>\n'
            f'<td class="num quiet">{r["gf_avg"]:.2f}</td>\n'
            f'<td class="num quiet">{r["ga_avg"]:.2f}</td>\n'
            "</tr>")
    return "\n".join(out)


def team_vs_difficulty(log, baseline):
    """Each team's return set against par for the fixtures it actually faced."""
    par = {r["fdr"]: r["ppm"] for r in baseline}
    teams = {}
    for m in log:
        t = teams.setdefault(m["short"], {"short": m["short"], "matches": []})
        t["matches"].append(m)
    rows = []
    for t in teams.values():
        games = t["matches"]
        actual = sum(g["pts"] for g in games) / len(games)
        expected = sum(par.get(g["fdr"], 0) for g in games) / len(games)
        rows.append({"short": t["short"], "matches": games,
                     "avg_fdr": sum(g["fdr"] for g in games) / len(games),
                     "actual": actual, "expected": expected,
                     "delta": actual - expected})
    rows.sort(key=lambda r: -r["delta"])
    return rows


def actual_rows(rows, teams_by_short):
    out = []
    for r in rows:
        chips = "".join(
            f'<span class="res {fdr_class(g["fdr"])} res-{"w" if g["pts"] == 3 else ("d" if g["pts"] == 1 else "l")}"'
            f' title="Gameweek {g["gw"]}, {"home to" if g["home"] else "away to"} {esc(g["opp"])},'
            f' difficulty {g["fdr"]}, {g["gf"]}-{g["ga"]}">'
            f'{"" if g["home"] else "@"}{esc(g["opp"])}<i>{g["fdr"]}</i>'
            f'<b>{"W" if g["pts"] == 3 else ("D" if g["pts"] == 1 else "L")}</b></span>'
            for g in r["matches"])
        cls = "delta-up" if r["delta"] > 0.15 else ("delta-down" if r["delta"] < -0.15 else "quiet")
        name = teams_by_short.get(r["short"], r["short"])
        out.append(
            "<tr>\n"
            f'<td class="team"><span class="short">{esc(r["short"])}</span>'
            f' <span class="full">{esc(name)}</span></td>\n'
            f'<td class="histcell">{chips}</td>\n'
            f'<td class="num">{r["avg_fdr"]:.2f}</td>\n'
            f'<td class="num strong">{r["actual"]:.2f}</td>\n'
            f'<td class="num quiet">{r["expected"]:.2f}</td>\n'
            f'<td class="num {cls}">{"+" if r["delta"] > 0 else ""}{r["delta"]:.2f}</td>\n'
            "</tr>")
    return "\n".join(out)


# ------------------------------------------------------------ price & value
MIN_MINUTES_SHARE = 0.4   # of the minutes available so far, to qualify for value tables


def price_moves(bootstrap, defence_ids, limit=10):
    """Biggest risers and fallers against each player's starting price."""
    players = player_rows(bootstrap, defence_ids)
    by_id = {p["id"]: p for p in bootstrap["elements"]}
    for p in players:
        raw = by_id[p["id"]]
        p["change"] = raw["cost_change_start"] / 10
        p["start"] = (raw["now_cost"] - raw["cost_change_start"]) / 10
        p["owned"] = float(raw.get("selected_by_percent") or 0)
    moved = [p for p in players if p["change"]]
    risers = sorted(moved, key=lambda p: (-p["change"], -p["pts"]))[:limit]
    fallers = sorted(moved, key=lambda p: (p["change"], -p["pts"]))[:limit]
    return risers, fallers, moved


def price_rows(players):
    out = []
    for p in players:
        up = p["change"] > 0
        out.append(
            "<tr>\n"
            f'<td class="team"><span class="short">{esc(p["web"])}</span></td>\n'
            f'<td class="mid quiet">{esc(p["team"])}</td>\n'
            f'<td class="mid quiet">{esc(p["pos"])}</td>\n'
            f'<td class="num quiet">&pound;{p["start"]:.1f}m</td>\n'
            f'<td class="num">&pound;{p["cost"]:.1f}m</td>\n'
            f'<td class="num {"delta-up" if up else "delta-down"}">'
            f'{"+" if up else "&#8722;"}&pound;{abs(p["change"]):.1f}m</td>\n'
            f'<td class="num strong">{p["pts"]}</td>\n'
            f'<td class="num quiet">{p["owned"]:.1f}%</td>\n'
            "</tr>")
    return "\n".join(out)


def value_blocks(players, rounds, limit=10):
    """Points per million, by position, for players with real minutes."""
    floor = rounds * 90 * MIN_MINUTES_SHARE
    blocks = []
    for label, pos_id, title in POSITIONS:
        pool = [p for p in players
                if p["pos_id"] == pos_id and p["minutes"] >= floor and p["cost"]]
        for p in pool:
            p["ratio"] = p["pts"] / p["cost"]
        ranked = sorted(pool, key=lambda p: -p["ratio"])[:limit]
        best = ranked[0]["ratio"] if ranked else 1
        trs = []
        for i, p in enumerate(ranked, 1):
            mark = (' <span class="dmark small" title="Plays for one of the eight teams'
                    ' conceding fewest goals">D</span>'
                    if p["defence"] and label in ("DEF", "GKP") else "")
            trs.append(
                "<tr>\n"
                f'<td class="num rank">{i}</td>\n'
                f'<td class="team"><span class="short">{esc(p["web"])}</span>{mark}</td>\n'
                f'<td class="mid quiet">{esc(p["team"])}</td>\n'
                f'<td class="num">&pound;{p["cost"]:.1f}m</td>\n'
                f'<td class="num">{p["pts"]}</td>\n'
                f'<td class="barcell" title="{esc(p["web"])}: {p["ratio"]:.1f} points per'
                f' &pound;1m">\n'
                f'  <span class="barwrap"><span class="bar"><span class="bar-fill"'
                f' style="width:{p["ratio"] / best * 100:.1f}%"></span></span>'
                f'<span class="barval">{p["ratio"]:.1f}</span></span>\n</td>\n'
                "</tr>")
        blocks.append(
            '<div class="pos-block">\n'
            f"<h4>{title}</h4>\n"
            '<div class="scroll">\n<table class="data compact">\n'
            '<thead><tr><th class="num">#</th><th>Player</th><th>Team</th>'
            '<th class="num">Price</th><th class="num">Pts</th>'
            '<th>Pts per &pound;1m</th></tr></thead>\n'
            f"<tbody>\n{''.join(trs)}\n</tbody>\n</table>\n</div>\n</div>")
    return "\n".join(blocks), floor
