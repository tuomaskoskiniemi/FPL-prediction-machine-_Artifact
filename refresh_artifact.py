"""Refresh the published overview page with current data from the FPL API.

Every table on the page is rebuilt from the season that is actually being
played: the league table and efficiency model, the fixture-difficulty outlook,
the player rankings, the formation comparison and the current round's fixtures.

Teams, fixtures and season player totals come straight from the API on each
run. One block needs more than the API's two summary endpoints - each player's
last five matches - and that is read from "FPL Data"/player_details.json, which
fetch_fpl_data.py writes. If that file is missing or belongs to another season,
the last-five block is left as it is and the run says so.

The published page cannot do any of this itself: claude.ai serves it under a
content policy that blocks requests to outside servers, so the fetch has to
happen here. Publish artifact/fpl_overview.html again afterwards.

Usage:
    python refresh_artifact.py
    python refresh_artifact.py --no-players   # skip the last-five player block
"""

import datetime as dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

PROJECT = os.path.dirname(os.path.abspath(__file__))
ARTIFACT = os.path.join(PROJECT, "artifact")
PAGE = os.path.join(ARTIFACT, "fpl_overview.html")
SEASON_DATA = os.path.join(PROJECT, "FPL Data")

sys.path.insert(0, ARTIFACT)
import build_sections as bs  # noqa: E402
from build_browser import browser_payload  # noqa: E402
sys.path.insert(0, PROJECT)
from src.fpl_team import fetch_manager_team, FPLTeamError  # noqa: E402

BASE_URL = "https://fantasy.premierleague.com/api"
HEADERS = {"User-Agent": "Mozilla/5.0"}


# ----------------------------------------------------------------------- API
def fetch_json(url, description):
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except (urllib.error.URLError, OSError, ValueError) as exc:
            if attempt < 2:
                print(f"  Retry {attempt + 1} for {description}...")
                time.sleep(2)
            else:
                print(f"  FAILED: {description} - {exc}")
                return None


def season_label(bootstrap):
    events = bootstrap.get("events") or []
    first = (events[0].get("deadline_time") or "")[:4] if events else ""
    if not first.isdigit():
        return "current season"
    return f"{first}/{str(int(first) + 1)[-2:]}"


# ------------------------------------------------------------ fixtures ahead
def upcoming(bootstrap, fixtures, team_rows):
    teams = {t["id"]: t for t in bootstrap["teams"]}
    next_gw = min((e["id"] for e in bootstrap["events"] if e.get("is_next")), default=None)
    if next_gw is None:
        current = [e["id"] for e in bootstrap["events"] if e.get("is_current")]
        next_gw = max(current) + 1 if current else 1

    per_team = {tid: [] for tid in teams}
    for f in sorted(fixtures, key=lambda x: ((x.get("event") or 99),
                                             x.get("kickoff_time") or "")):
        event = f.get("event")
        if event is None or event < next_gw or f.get("finished"):
            continue
        per_team[f["team_h"]].append((teams[f["team_a"]]["short_name"], True,
                                      f["team_h_difficulty"]))
        per_team[f["team_a"]].append((teams[f["team_h"]]["short_name"], False,
                                      f["team_a_difficulty"]))

    efficiency = {r["short"]: r["eff"] for r in team_rows}
    recent_pts = {r["short"]: (r["pts5"], r["games5"]) for r in team_rows}
    rows = []
    for tid, team in teams.items():
        games = per_team[tid]
        if not games:
            continue
        five, ten = games[:5], games[:10]
        fdr5 = sum(g[2] for g in five) / len(five)
        eff = efficiency.get(team["short_name"])
        rows.append({
            "short": team["short_name"], "name": team["name"], "fdr5": fdr5,
            "fdr10": sum(g[2] for g in ten) / len(ten),
            "home5": sum(1 for g in five if g[1]),
            "adjusted5": (fdr5 / eff) if eff else None,
            "pts5": recent_pts.get(team["short_name"], (None, 0)),
            "fixtures": [(("" if home else "@") + opp, fdr) for opp, home, fdr in five],
        })
    rows.sort(key=lambda r: (r["fdr5"], r["fdr10"]))
    return next_gw, rows


def render_upcoming(rows):
    out = []
    for r in rows:
        chips = "".join(
            f'<span class="fx-chip {bs.fdr_class(fdr)}" title="'
            f'{"away to" if label.startswith("@") else "home to"} '
            f'{bs.esc(label.lstrip("@"))}, difficulty {fdr}">'
            f"{bs.esc(label)}<i>{fdr}</i></span>"
            for label, fdr in r["fixtures"])
        adjusted = f'{r["adjusted5"]:.2f}' if r["adjusted5"] is not None else "&#8212;"
        new_tag = ("" if r["adjusted5"] is not None else
                   ' <span class="newtag" title="Too few matches played to rate">new</span>')
        out.append(
            "<tr>\n"
            f'<td class="team"><span class="short">{bs.esc(r["short"])}</span>'
            f' <span class="full">{bs.esc(r["name"])}</span>{new_tag}</td>\n'
            f'<td class="fxcell">{chips}</td>\n'
            f'<td class="num strong">{r["fdr5"]:.2f}</td>\n'
            f'<td class="num">{r["fdr10"]:.2f}</td>\n'
            f'<td class="num quiet">{r["home5"]}</td>\n'
            f'<td class="num strong">{r["pts5"][0] if r["pts5"][0] is not None else "&#8212;"}'
            f'<span class="quiet"> / {r["pts5"][1] * 3}</span></td>\n'
            f'<td class="num">{adjusted}</td>\n</tr>')
    return "\n".join(out)


def round_fixtures(bootstrap, fixtures, next_gw):
    """The coming round, or the one just played if the season is between rounds."""
    teams = {t["id"]: t for t in bootstrap["teams"]}
    chosen = [f for f in fixtures if f.get("event") == next_gw]
    finished = False
    if not chosen:
        played = [f.get("event") for f in fixtures if f.get("finished")]
        if played:
            next_gw = max(played)
            chosen = [f for f in fixtures if f.get("event") == next_gw]
            finished = True
    chosen.sort(key=lambda f: (f.get("kickoff_time") or "",
                               teams[f["team_h"]]["short_name"]))
    items = []
    for f in chosen[:10]:
        home, away = teams[f["team_h"]]["short_name"], teams[f["team_a"]]["short_name"]
        if f.get("finished") and f.get("team_h_score") is not None:
            middle = f'{f["team_h_score"]}&#8211;{f["team_a_score"]}'
        else:
            middle = "v"
        items.append(f'<li><span class="fx-t">{bs.esc(home)}</span>'
                     f'<span class="fx-s">{middle}</span>'
                     f'<span class="fx-t">{bs.esc(away)}</span></li>')
    return next_gw, finished, "\n".join(items)


# -------------------------------------------------------------------- page
def replace_marked(html, marker, replacement):
    pattern = re.compile(f"(<!--#{marker}-->).*?(<!--/#{marker}-->)", re.S)
    if not pattern.search(html):
        raise SystemExit(f"Marker '{marker}' not found in {PAGE} - page structure changed.")
    return pattern.sub(lambda m: m.group(1) + replacement + m.group(2), html, count=1)


def load_player_details(expected_players):
    path = os.path.join(SEASON_DATA, "player_details.json")
    if not os.path.exists(path):
        return None, "no player_details.json in \"FPL Data\""
    try:
        with open(path, encoding="utf-8") as f:
            details = json.load(f)
    except (ValueError, OSError) as exc:
        return None, f"could not read player_details.json ({exc})"
    if not details:
        return None, "player_details.json is empty"
    overlap = sum(1 for pid in expected_players if str(pid) in details)
    if overlap < len(expected_players) * 0.5:
        return None, ("player_details.json covers a different player set - "
                      "run fetch_fpl_data.py to refresh it")
    return details, None


NL = chr(10)

DATA = os.path.join(ARTIFACT, "data")
TEAM_FILE = os.path.join(DATA, "team.json")


def remembered_team():
    """The team id saved by an earlier --team run, if any."""
    try:
        with open(TEAM_FILE, encoding="utf-8") as f:
            return (json.load(f) or {}).get("team")
    except (OSError, ValueError):
        return None


def remember_team(team_id):
    os.makedirs(DATA, exist_ok=True)
    with open(TEAM_FILE, "w", encoding="utf-8") as f:
        json.dump({"team": team_id}, f)


def squad_rows(players):
    """One table row per player, with the picking principles shown."""
    out = []
    for p in players:
        marks = ""
        if p["is_captain"]:
            marks = '<span class="cap">C</span>'
        elif p["is_vice_captain"]:
            marks = '<span class="cap vcap">V</span>'
        if p["mean_defence"] and p["position_id"] in (1, 2):
            marks += (' <span class="dmark small" title="One of the eight teams conceding'
                      ' fewest goals">D</span>')
        if p["flagged"]:
            chance = p["chance_of_playing"]
            label = "OUT" if chance is None else f"{chance}%"
            title = bs.esc(p["news"] or "Not fully available")
            status = f'<span class="flagwarn" title="{title}">{label}</span>'
        else:
            status = '<span class="ok">Available</span>'
        out.append(
            "<tr>" + NL
            + f'<td class="team"><span class="short">{bs.esc(p["web_name"])}</span>'
              f"{marks}</td>" + NL
            + f'<td class="mid quiet">{bs.esc(p["team_short"])}</td>' + NL
            + f'<td class="mid quiet">{bs.esc(p["position"])}</td>' + NL
            + f'<td class="num">&pound;{p["price"]:.1f}m</td>' + NL
            + f'<td class="num strong">{p["points"]}</td>' + NL
            + f'<td class="num">{p["form"]:.1f}</td>' + NL
            + f'<td class="num quiet">{p["minutes"]:,}</td>' + NL
            + f'<td class="num">{p["goals"]}</td>' + NL
            + f'<td class="num">{p["assists"]}</td>' + NL
            + f"<td>{status}</td>" + NL
            + "</tr>")
    return NL.join(out)


def squad_section(html, squad, problem, season):
    """Fill the Current team tab, or explain how to point it at a team."""
    if problem or not squad:
        html = replace_marked(html, "squad-eyebrow", "Not connected yet")
        html = replace_marked(html, "squad-heading", "Point this at your team")
        html = replace_marked(
            html, "squad-lede",
            "This tab shows your real squad &#8212; the eleven, the bench, what it is worth "
            "and who is carrying a knock &#8212; read straight from the Fantasy Premier "
            "League API. It just needs to know which team is yours."
            + (f" <strong>{bs.esc(problem)}</strong>" if problem else ""))
        html = replace_marked(
            html, "squad-tiles",
            '<div class="tile"><b>&#8212;</b><span>Squad value</span></div>'
            '<div class="tile"><b>&#8212;</b><span>In the bank</span></div>'
            '<div class="tile"><b>&#8212;</b><span>Overall points</span></div>'
            '<div class="tile"><b>&#8212;</b><span>Flagged players</span></div>')
        setup = ('<tr><td colspan="10"><div class="setup">'
                 "<p>Run this once with your team link or id, and every refresh from then on "
                 "keeps the squad current:</p>"
                 "<code>python refresh_artifact.py --team 1234567</code>"
                 "<p>The id is the number in your team's address on the Fantasy Premier "
                 "League site. The link works too.</p>"
                 "</div></td></tr>")
        html = replace_marked(html, "squad-xi", setup)
        html = replace_marked(html, "squad-bench", "")
        html = replace_marked(html, "xi-sub", "not loaded")
        html = replace_marked(html, "bench-sub", "not loaded")
        html = replace_marked(
            html, "squad-caption",
            "Nothing about your team is sent anywhere: the squad is read from the public API "
            "when you refresh, and written into this page as ordinary text.")
        return html

    entry, money, gw = squad["entry"], squad["money"], squad["gameweek"]
    flagged = squad["flagged"]

    html = replace_marked(html, "squad-eyebrow", "Your squad")
    html = replace_marked(html, "squad-heading", bs.esc(entry["team_name"] or "Current team"))
    html = replace_marked(
        html, "squad-lede",
        f"{bs.esc(entry['manager'])}&#8217;s squad as it stood at the gameweek "
        f"{entry['gameweek']} deadline, read from the Fantasy Premier League API. "
        + (f"{len(flagged)} player{'s' if len(flagged) != 1 else ''} carrying a flag."
           if flagged else "Nobody is carrying an injury flag."))
    rank = f"{entry['overall_rank']:,}" if entry.get("overall_rank") else "&#8212;"
    html = replace_marked(
        html, "squad-tiles",
        f'<div class="tile"><b>&pound;{money["squad_value"]:.1f}m</b>'
        "<span>Squad value</span></div>"
        f'<div class="tile"><b>&pound;{money["bank"]:.1f}m</b><span>In the bank</span></div>'
        f'<div class="tile"><b>{entry["overall_points"]}</b><span>Overall points</span></div>'
        f'<div class="tile"><b>{rank}</b><span>Overall rank</span></div>')
    html = replace_marked(html, "squad-xi", NL + squad_rows(squad["starting_xi"]) + NL)
    html = replace_marked(html, "squad-bench", NL + squad_rows(squad["bench"]) + NL)
    captain = squad["captain"]["web_name"] if squad["captain"] else "nobody"
    html = replace_marked(
        html, "xi-sub",
        f"gameweek {entry['gameweek']} &#183; {gw['points']} pts &#183; captain "
        f"{bs.esc(captain)}")
    html = replace_marked(
        html, "bench-sub",
        f"{gw['points_on_bench']} points left on it" if gw.get("points_on_bench") is not None
        else "four players")
    names = ", ".join(bs.esc(p["web_name"]) for p in flagged)
    html = replace_marked(
        html, "squad-caption",
        "<strong>C</strong> is the captain and <strong>V</strong> the vice. "
        '<span class="dmark small">D</span> marks a defender or keeper from one of the eight '
        "meanest defences. "
        + (f"Held back by the pick process: {names}. " if flagged else "")
        + f"Squad value is what the game says your players are worth, not the sum of "
          f"today&#8217;s prices (&pound;{money['value_at_today_prices']:.1f}m) &#8212; the "
          "game values each player at what you paid plus half of any rise.")
    return html


def main():
    argv = sys.argv[1:]
    skip_players = "--no-players" in argv
    team_arg = None
    if "--team" in argv:
        i = argv.index("--team")
        if i + 1 >= len(argv):
            raise SystemExit("--team needs a team id or a link to the team page.")
        team_arg = argv[i + 1]

    print("1/3 Fetching bootstrap-static...")
    bootstrap = fetch_json(f"{BASE_URL}/bootstrap-static/", "bootstrap-static")
    if not bootstrap:
        raise SystemExit("Cannot refresh without bootstrap-static data.")

    print("2/3 Fetching fixtures...")
    fixtures = fetch_json(f"{BASE_URL}/fixtures/", "fixtures")
    if not fixtures:
        raise SystemExit("Cannot refresh without the fixture list.")
    fetched_at = dt.datetime.now(dt.timezone.utc)
    season = season_label(bootstrap)

    print("3/3 Rebuilding the page...")
    teams = bs.team_table(bootstrap, fixtures)
    if not teams:
        raise SystemExit(f"No matches played yet in {season} - nothing to rebuild.")

    matches = sum(r["played"] for r in teams) // 2
    rounds = max(r["played"] for r in teams)
    defence_ids = {r["id"] for r in teams if r.get("defence_mark")}
    defence_names = ", ".join(r["short"] for r in sorted(teams, key=lambda r: r["ga"])
                             [:bs.DEFENCE_MARK])

    players = bs.player_rows(bootstrap, defence_ids)
    flagged = sum(1 for p in players if p["status"] in ("i", "d", "s"))
    shapes = bs.formation_table(players)
    spread = shapes[0]["pts"] - shapes[-1]["pts"] if shapes else 0

    next_gw, ahead = upcoming(bootstrap, fixtures, teams)
    round_gw, round_done, round_html = round_fixtures(bootstrap, fixtures, next_gw)

    with open(PAGE, encoding="utf-8") as f:
        html = f.read()

    # --- the live season, everywhere -------------------------------------
    html = replace_marked(html, "tiles",
                          '\n      <div class="tile"><b>20</b><span>Teams rated</span></div>'
                          f'\n      <div class="tile"><b>{len(players)}</b>'
                          "<span>Players tracked</span></div>"
                          f'\n      <div class="tile"><b>{matches}</b>'
                          "<span>Matches played</span></div>"
                          '\n      <div class="tile"><b>8</b>'
                          "<span>Steps in the process</span></div>\n    ")
    html = replace_marked(
        html, "provenance",
        f"Every figure on this page comes from the live Fantasy Premier League feed "
        f"&#8212; the {bs.esc(season)} season as it stands after {matches} matches, "
        f"{rounds} gameweeks in.")
    html = replace_marked(
        html, "principles-caption",
        f"{flagged} players currently carry an injury, doubt or suspension flag and are "
        f"held back from proposals. The eight meanest defences so far are {defence_names}.")

    html = replace_marked(html, "standings-subhead",
                          "Efficiency, measured on the season so far "
                          f"<span>{bs.esc(season)} &#183; {matches} matches played</span>")
    html = replace_marked(html, "standings-rows", "\n" + bs.standings_rows(teams) + "\n")

    leader, tail = teams[0], teams[-1]
    movers = sorted(teams, key=lambda r: ((r["avg_fdr"] / r["eff"]) if r["eff"] else 0)
                    - ((r["avg_fdr"] / r["eff_flat"]) if r["eff_flat"] else 0))
    up, down = movers[0], movers[-1]

    def adj(row, key):
        value = row[key]
        return row["avg_fdr"] / value if value else 0

    html = replace_marked(
        html, "standings-caption",
        f"Each team has played {rounds} gameweeks. <strong>Pts / match</strong> uses league "
        "points (3 for a win, 1 for a draw). <span class=\"dmark\">D</span> marks the eight "
        "teams that have conceded fewest goals &#8212; the defenders and goalkeepers to "
        "prefer. <strong>Efficiency</strong> weights each team's last five matches at triple "
        "an earlier match; the flat season rating sits beside it so the effect of that choice "
        "is visible. <strong>Adjusted FDR</strong> is average fixture difficulty divided by "
        "the weighted rating: a comparative index where a higher number means the same "
        f"fixtures are effectively harder for that team. Read it against the rest of the "
        f"column &#8212; {bs.esc(leader['name'])} at {adj(leader, 'eff'):.2f} face their "
        f"fixtures far more comfortably than {bs.esc(tail['name'])} at "
        f"{adj(tail, 'eff'):.2f}. The weighting matters: it moves {bs.esc(up['name'])} from "
        f"{adj(up, 'eff_flat'):.2f} to {adj(up, 'eff'):.2f} on recent form, and "
        f"{bs.esc(down['name'])} the other way, from {adj(down, 'eff_flat'):.2f} to "
        f"{adj(down, 'eff'):.2f}.")

    html = replace_marked(html, "season",
                          f"{bs.esc(season)} &#183; from gameweek {next_gw}")
    html = replace_marked(html, "next-rows", "\n" + render_upcoming(ahead) + "\n")
    html = replace_marked(
        html, "extremes",
        f'Easiest run from here: <strong>{bs.esc(ahead[0]["name"])}</strong> at '
        f'{ahead[0]["fdr5"]:.2f} over five. Hardest: '
        f'<strong>{bs.esc(ahead[-1]["name"])}</strong> at {ahead[-1]["fdr5"]:.2f}.')
    html = replace_marked(
        html, "fixtures-caption-tail",
        " Fixtures are shown opponent by opponent &#8212; <code>@</code> means away, and the "
        "small number on each chip is that fixture's difficulty, 1 (easiest, green) to 5 "
        "(hardest, red). The final column divides the five-match average by the weighted "
        "efficiency rating from the table above, on the same comparative scale &#8212; lower "
        "is a kinder run for that particular team.")

    # --- difficulty against reality (Team analysis) ----------------------
    log = bs.match_log(bootstrap, fixtures)
    baseline = bs.difficulty_baseline(log)
    against = bs.team_vs_difficulty(log, baseline)
    names = {r["short"]: r["name"] for r in teams}
    easiest_level = min(baseline, key=lambda r: r["fdr"])
    hardest_level = max(baseline, key=lambda r: r["fdr"])
    best, worst = against[0], against[-1]

    html = replace_marked(
        html, "team-lede",
        "Every fixture carries a difficulty rating from 1 (easy) to 5 (hard). These are the "
        "next five and ten for all twenty teams, easiest run first.")
    html = replace_marked(
        html, "history-lede",
        "A difficulty rating is a forecast. These two tables check it against what has "
        f"actually happened across the {matches} matches played so far.")
    html = replace_marked(html, "baseline-sub",
                          f"{bs.esc(season)} &#183; {len(log)} team-matches")
    html = replace_marked(html, "baseline-rows", "\n" + bs.baseline_rows(baseline) + "\n")
    html = replace_marked(
        html, "baseline-caption",
        "Each match appears twice here, once from each side, because the two teams are "
        "rarely given the same difficulty. A difficulty-"
        f"{easiest_level['fdr']} fixture has returned {easiest_level['ppm']:.2f} points a "
        f"match on average; a difficulty-{hardest_level['fdr']} fixture "
        f"{hardest_level['ppm']:.2f}. "
        + ("The rating is ordered the way it should be: the harder the fixture, the fewer "
           "the points."
           if all(baseline[i]["ppm"] >= baseline[i + 1]["ppm"]
                  for i in range(len(baseline) - 1))
           else "The ladder is not strictly ordered yet &#8212; at this stage of the season "
                "some levels are decided by a handful of matches, so read the thinner rows "
                "with care."))
    html = replace_marked(html, "actual-sub",
                          f"{bs.esc(season)} &#183; {rounds} gameweeks")
    html = replace_marked(html, "actual-rows", "\n" + bs.actual_rows(against, names) + "\n")
    html = replace_marked(
        html, "actual-caption",
        "Each match is shown with its opponent, the difficulty it was given and how it "
        "finished &#8212; the underline is the result, the tint is the difficulty. "
        "<strong>Par</strong> is what the league as a whole has taken from that exact set of "
        "difficulties, so <strong>difference</strong> is the points a team has won or lost "
        "against its own fixture list rather than against the table. "
        f"{bs.esc(names.get(best['short'], best['short']))} are the furthest ahead of their "
        f"fixtures at {best['delta']:+.2f} points a match; "
        f"{bs.esc(names.get(worst['short'], worst['short']))} the furthest behind at "
        f"{worst['delta']:+.2f}. This is the same idea the efficiency rating measures, shown "
        "match by match.")

    html = replace_marked(
        html, "formation-lede",
        f"For each legal formation, the best possible eleven from the season so far. The "
        f"spread between the best and worst shape is {spread} points.")
    html = replace_marked(html, "formation-rows", "\n" + bs.formation_rows(shapes) + "\n")
    html = replace_marked(html, "xi", "\n" + bs.xi_list(shapes[0]) + "\n    ")
    html = replace_marked(
        html, "xi-caption",
        f'Total cost &pound;{shapes[0]["value"]:.1f}m for {shapes[0]["pts"]} points.')

    html = replace_marked(html, "players-season-subhead",
                          f"Season so far <span>{rounds} gameweeks</span>")
    html = replace_marked(
        html, "players-season",
        "\n" + bs.position_blocks(players, "pts", "minutes", "goals", "assists") + "\n    ")

    # --- the last-five block needs the stored per-player history ----------
    note = None
    if skip_players:
        note = "skipped (--no-players)"
    else:
        details, problem = load_player_details([p["id"] for p in players])
        if problem:
            note = problem
        else:
            recent = bs.last5_totals(players, details)
            rounds_seen = [p["rounds"] for p in recent if p.get("rounds")]
            first = min(r[0] for r in rounds_seen if r[0])
            last = max(r[1] for r in rounds_seen if r[1])
            html = replace_marked(
                html, "players-last5",
                "\n" + bs.position_blocks(recent, "pts5", "minutes5", "goals5",
                                          "assists5") + "\n    ")
            html = replace_marked(
                html, "players-last5-subhead",
                f"Last five matches <span>gameweeks {first}&#8211;{last}</span>")
            season_top = {p["id"] for label, pos, _ in bs.POSITIONS
                          for p in sorted((q for q in players if q["pos_id"] == pos),
                                          key=lambda q: -q["pts"])[:10]}
            recent_top = {p["id"] for label, pos, _ in bs.POSITIONS
                          for p in sorted((q for q in recent if q["pos_id"] == pos),
                                          key=lambda q: -q["pts5"])[:10]}
            html = replace_marked(
                html, "players-caption",
                "The same ten-deep ranking over each player's last five matches only "
                "&#8212; the <strong>form over fixtures</strong> principle in its rawest "
                f"form. Only {len(season_top & recent_top)} of the 40 places are held by the "
                "same players in both tables, which is the whole argument for shortlisting "
                "on recent form rather than on the season total. Prices are current. "
                '<span class="dmark small">D</span> marks a player from one of the eight '
                "meanest defences.")

    # --- price moves and value (Player analysis) -------------------------
    risers, fallers, moved = bs.price_moves(bootstrap, defence_ids)
    up_total = sum(1 for p in moved if p["change"] > 0)
    html = replace_marked(
        html, "price-lede",
        "Prices move as managers buy and sell, so a player's price is the crowd's running "
        f"verdict on him. {len(moved)} of the {len(players)} players have moved since the "
        f"season opened, {up_total} of them upwards.")
    html = replace_marked(html, "risers-sub", f"top {len(risers)} by price gained")
    html = replace_marked(html, "risers-rows", "\n" + bs.price_rows(risers) + "\n")
    html = replace_marked(html, "fallers-sub", f"top {len(fallers)} by price lost")
    html = replace_marked(html, "fallers-rows", "\n" + bs.price_rows(fallers) + "\n")
    top_riser, top_faller = risers[0], fallers[0]
    html = replace_marked(
        html, "price-caption",
        "<strong>Start</strong> is the price the player opened the season at. "
        f"{bs.esc(top_riser['web'])} has gained the most at "
        f"&pound;{top_riser['change']:.1f}m on {top_riser['pts']} points; "
        f"{bs.esc(top_faller['web'])} has lost the most at "
        f"&pound;{abs(top_faller['change']):.1f}m. A rising price is a squad already late to "
        "the party &#8212; it costs more and sells for less than it did &#8212; while a "
        "falling one is either a warning or a discount, which is what the rest of this page "
        "is for.")

    value_html, floor = bs.value_blocks(players, rounds)
    html = replace_marked(
        html, "value-lede",
        "Total points reward the expensive. Points for every million spent reward the "
        "players who free up money for somewhere else &#8212; the ones that make a squad "
        "of fifteen fit inside the budget.")
    html = replace_marked(html, "value-blocks", "\n" + value_html + "\n    ")
    html = replace_marked(
        html, "value-caption",
        f"Only players with at least {floor:.0f} minutes are ranked &#8212; "
        f"{bs.MIN_MINUTES_SHARE:.0%} of the minutes available so far &#8212; because a cheap "
        "player with one good cameo otherwise tops every one of these tables. Prices are "
        "current, not starting prices, so a player who has already risen is rated at what he "
        "would cost you today.")

    # --- the player browser and the watchlist ----------------------------
    html = replace_marked(html, "browser-data", browser_payload(bootstrap, defence_ids))
    html = replace_marked(
        html, "browser-lede",
        f"All {len(players)} players in the game, filtered by team and position, with every "
        f"statistic the API publishes &#8212; {len(bootstrap.get('element_stats', []))} of "
        "them, plus price, form, ownership and availability. Sort on any column by clicking "
        "its heading, and star anyone worth watching to send them to the next tab.")
    html = replace_marked(
        html, "browser-caption",
        "Columns come from the API's own list of statistics, so anything it starts "
        "publishing turns up here without a change to this page. A dash means the API "
        "reports nothing for that player. Players carrying an injury or doubt are marked "
        "beside their name, and defenders and keepers from the eight meanest defences keep "
        'their <span class="dmark small">D</span>.')

    # --- the manager's own squad (Current team) --------------------------
    squad, squad_problem = None, None
    wanted = team_arg or remembered_team()
    if wanted:
        try:
            squad = fetch_manager_team(wanted, client=None, bootstrap=bootstrap,
                                       fixtures=fixtures)
            remember_team(squad["entry"]["id"])
        except FPLTeamError as exc:
            squad_problem = str(exc)
    html = squad_section(html, squad, squad_problem, season)

    # --- the current round ------------------------------------------------
    html = replace_marked(html, "round-eyebrow", "The coming round")
    html = replace_marked(html, "round-heading",
                          f"Gameweek {round_gw}" + (" as it finished" if round_done else ""))
    html = replace_marked(
        html, "round-lede",
        "The home page opens on this round &#8212; the fixtures a manager is picking for "
        "right now." if not round_done else
        "The most recent round to be played in full.")
    html = replace_marked(html, "round-fixtures", "\n" + round_html + "\n")

    html = replace_marked(
        html, "footer-note",
        f"Data: official Fantasy Premier League feed &#183; {bs.esc(season)}, "
        f"gameweek {rounds} played")

    shown = fetched_at.strftime("%d %B %Y, %H:%M UTC").lstrip("0")
    html = re.sub(r'<time id="refresh-time"[^>]*>.*?</time>',
                  f'<time id="refresh-time" datetime="{fetched_at.strftime("%Y-%m-%dT%H:%MZ")}">'
                  f"{shown}</time>", html, count=1, flags=re.S)

    with open(PAGE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n{season}: {matches} matches played, {rounds} gameweeks in.")
    print(f"  Table leader:      {teams[0]['short']} {teams[0]['pts']} pts")
    print(f"  Best efficiency:   {max(teams, key=lambda r: r['eff'])['short']} "
          f"{max(r['eff'] for r in teams):.3f}")
    print(f"  Easiest next five: {ahead[0]['short']} {ahead[0]['fdr5']:.2f}")
    print(f"  Hardest next five: {ahead[-1]['short']} {ahead[-1]['fdr5']:.2f}")
    print(f"  Top scorer:        {max(players, key=lambda p: p['pts'])['web']} "
          f"{max(p['pts'] for p in players)} pts")
    if squad:
        print(f"  Your squad:        {squad['entry']['team_name']} "
              f"({squad['money']['squad_value']:.1f}m, {len(squad['flagged'])} flagged)")
    elif squad_problem:
        print(f"  Current team tab NOT filled: {squad_problem}")
    else:
        print("  Current team tab:  no team set - run with --team <id-or-link>")
    if note:
        print(f"  Last-five player block NOT refreshed: {note}")
    print(f"\nUpdated {PAGE}")
    print("Publish that file again to update the shared link.")


if __name__ == "__main__":
    main()
