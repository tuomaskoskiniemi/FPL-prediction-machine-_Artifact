"""Fetch a manager's own FPL team from the API.

Step 6 of the pick process ("Current team") needs the squad a manager actually
owns: who is in it, what it is worth, what is in the bank, who is captain and
which players are carrying an injury flag. This module is that function.

    from src.fpl_team import fetch_manager_team, parse_team_id

    team = fetch_manager_team("https://fantasy.premierleague.com/entry/1234567/")
    print(team["entry"]["team_name"], team["money"]["squad_value"])
    for player in team["starting_xi"]:
        print(player["web_name"], player["position"], player["points"])

Everything here uses public endpoints, so no login is needed. Two consequences:
a player's individual selling price is not available (that needs the manager's
own session), and the squad is the one from the last deadline that has passed -
transfers made for a gameweek that has not locked yet are not visible.

Run it directly to print a squad:

    python -m src.fpl_team 1234567
    python -m src.fpl_team https://fantasy.premierleague.com/entry/1234567/
"""

from typing import Any, Dict, List, Optional
import re

from src.fpl_api_client import FPLAPIClient

DEFENCE_MARK = 8   # players from the N meanest defences are marked "D"

POSITION_KEYS = {1: "goalkeepers", 2: "defenders", 3: "midfielders", 4: "forwards"}


class FPLTeamError(Exception):
    """Raised when a team cannot be identified or fetched."""


# --------------------------------------------------------------------- input
def parse_team_id(value: Any) -> int:
    """Pull a team id out of an FPL link, or accept a bare id.

    Accepts any of:
        1234567
        "1234567"
        "https://fantasy.premierleague.com/entry/1234567/"
        "https://fantasy.premierleague.com/entry/1234567/event/9"
    """
    if isinstance(value, int):
        if value > 0:
            return value
        raise FPLTeamError(f"Team id must be positive, got {value}.")

    text = str(value or "").strip()
    if not text:
        raise FPLTeamError("No team link or id given.")

    for pattern in (r"/entry/(\d+)", r"^(\d+)$"):
        match = re.search(pattern, text)
        if match:
            return int(match.group(1))

    raise FPLTeamError(
        f"Could not find a team id in {text!r}. Paste the link to your team page "
        "(it looks like https://fantasy.premierleague.com/entry/1234567/) or just "
        "the number from it.")


# ------------------------------------------------------------------ helpers
def _current_gameweek(bootstrap: Dict[str, Any]) -> Optional[int]:
    events = bootstrap.get("events") or []
    current = [e["id"] for e in events if e.get("is_current")]
    if current:
        return max(current)
    finished = [e["id"] for e in events if e.get("finished")]
    return max(finished) if finished else None


def _mean_defences(fixtures: List[Dict[str, Any]], limit: int = DEFENCE_MARK) -> set:
    """Team ids of the clubs conceding fewest goals so far."""
    conceded: Dict[int, int] = {}
    for f in fixtures or []:
        if not f.get("finished") or f.get("team_h_score") is None:
            continue
        conceded[f["team_h"]] = conceded.get(f["team_h"], 0) + f["team_a_score"]
        conceded[f["team_a"]] = conceded.get(f["team_a"], 0) + f["team_h_score"]
    return set(sorted(conceded, key=lambda tid: conceded[tid])[:limit])


def _describe_player(pick: Dict[str, Any], element: Dict[str, Any],
                     teams: Dict[int, Dict[str, Any]],
                     types: Dict[int, Dict[str, Any]],
                     mean_defences: set) -> Dict[str, Any]:
    club = teams.get(element["team"], {})
    kind = types.get(element["element_type"], {})
    available = element.get("status") == "a"
    return {
        "id": element["id"],
        "web_name": element["web_name"],
        "name": f"{element.get('first_name', '')} {element.get('second_name', '')}".strip(),
        "team": club.get("name", "Unknown"),
        "team_short": club.get("short_name", "UNK"),
        "team_id": element["team"],
        "position": kind.get("singular_name_short", "?"),
        "position_id": element["element_type"],
        "price": element["now_cost"] / 10,
        "points": element.get("total_points", 0),
        "form": float(element.get("form") or 0),
        "points_per_game": float(element.get("points_per_game") or 0),
        "minutes": element.get("minutes", 0),
        "goals": element.get("goals_scored", 0),
        "assists": element.get("assists", 0),
        "clean_sheets": element.get("clean_sheets", 0),
        "selected_by_percent": float(element.get("selected_by_percent") or 0),
        # squad role
        "squad_position": pick.get("position"),
        "on_bench": (pick.get("position") or 0) > 11,
        "is_captain": bool(pick.get("is_captain")),
        "is_vice_captain": bool(pick.get("is_vice_captain")),
        "multiplier": pick.get("multiplier", 1),
        # the picking principles
        "available": available,
        "status": element.get("status"),
        "chance_of_playing": element.get("chance_of_playing_next_round"),
        "news": element.get("news") or "",
        "flagged": not available or (element.get("chance_of_playing_next_round") not in
                                     (None, 100)),
        "mean_defence": element["team"] in mean_defences,
    }


# ----------------------------------------------------------------- the thing
def fetch_manager_team(team: Any, gameweek: Optional[int] = None,
                       client: Optional[FPLAPIClient] = None,
                       bootstrap: Optional[Dict[str, Any]] = None,
                       fixtures: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Fetch one manager's squad from the FPL API.

    Args:
        team: a team id, or any FPL link containing one.
        gameweek: which gameweek's squad to read; defaults to the current one.
        client: an existing FPLAPIClient, if you already have one.
        bootstrap: bootstrap-static data, if you have already fetched it.
        fixtures: the fixture list, used only to mark the meanest defences.

    Returns:
        A dictionary with entry details, money, the gameweek summary, the squad
        grouped by position, the starting eleven, the bench and the captain.

    Raises:
        FPLTeamError: if the team id cannot be parsed, or the team does not exist.
    """
    team_id = parse_team_id(team)
    client = client or FPLAPIClient()

    try:
        entry = client.fetch_team_detail(team_id)
    except Exception as exc:                      # network, 404, bad JSON
        raise FPLTeamError(
            f"Could not fetch team {team_id} from the FPL API: {exc}") from exc
    if not entry or "id" not in entry:
        raise FPLTeamError(f"The FPL API returned no team for id {team_id}.")

    if bootstrap is None:
        bootstrap = client.fetch_bootstrap_static()
    if fixtures is None:
        try:
            fixtures = client.fetch_fixtures()
        except Exception:
            fixtures = []

    event = gameweek or _current_gameweek(bootstrap)
    if not event:
        raise FPLTeamError("The season has not started yet - there is no squad to read.")

    picks_url = f"{client.BASE_URL}/entry/{team_id}/event/{event}/picks/"
    response = client.session.get(picks_url)
    if response.status_code != 200:
        raise FPLTeamError(
            f"No squad found for team {team_id} in gameweek {event}. The manager may "
            "have joined later, or that gameweek's deadline may not have passed yet.")
    picks_payload = response.json()

    elements = {e["id"]: e for e in bootstrap.get("elements", [])}
    teams = {t["id"]: t for t in bootstrap.get("teams", [])}
    types = {t["id"]: t for t in bootstrap.get("element_types", [])}
    mean_defences = _mean_defences(fixtures)

    squad = {key: [] for key in POSITION_KEYS.values()}
    everyone: List[Dict[str, Any]] = []
    for pick in picks_payload.get("picks", []):
        element = elements.get(pick.get("element"))
        if not element:
            continue
        player = _describe_player(pick, element, teams, types, mean_defences)
        everyone.append(player)
        squad[POSITION_KEYS[player["position_id"]]].append(player)

    if not everyone:
        raise FPLTeamError(f"Team {team_id} returned an empty squad for gameweek {event}.")

    everyone.sort(key=lambda p: p["squad_position"] or 99)
    history = picks_payload.get("entry_history") or {}

    return {
        "entry": {
            "id": entry.get("id", team_id),
            "team_name": entry.get("name", ""),
            "manager": f"{entry.get('player_first_name', '')} "
                       f"{entry.get('player_last_name', '')}".strip(),
            "started_event": entry.get("started_event"),
            "overall_points": entry.get("summary_overall_points"),
            "overall_rank": entry.get("summary_overall_rank"),
            "gameweek": event,
        },
        "money": {
            # the API reports tenths of a million
            "squad_value": (history.get("value") or entry.get("last_deadline_value") or 0) / 10,
            "bank": (history.get("bank") if history.get("bank") is not None
                     else entry.get("last_deadline_bank") or 0) / 10,
            "budget": ((history.get("value") or 0) + (history.get("bank") or 0)) / 10,
            "value_at_today_prices": round(sum(p["price"] for p in everyone), 1),
        },
        "gameweek": {
            "event": event,
            "points": history.get("points"),
            "total_points": history.get("total_points"),
            "overall_rank": history.get("overall_rank"),
            "transfers": history.get("event_transfers"),
            "transfer_cost": history.get("event_transfers_cost"),
            "points_on_bench": history.get("points_on_bench"),
            "chip": picks_payload.get("active_chip"),
        },
        "squad": squad,
        "starting_xi": [p for p in everyone if not p["on_bench"]],
        "bench": [p for p in everyone if p["on_bench"]],
        "captain": next((p for p in everyone if p["is_captain"]), None),
        "vice_captain": next((p for p in everyone if p["is_vice_captain"]), None),
        "flagged": [p for p in everyone if p["flagged"]],
        "all_players": everyone,
    }


# ----------------------------------------------------------------------- CLI
def _print_team(team: Dict[str, Any]) -> None:
    entry, money, gw = team["entry"], team["money"], team["gameweek"]
    print(f"\n{entry['team_name']}  ({entry['manager']})")
    print(f"Gameweek {entry['gameweek']}  -  {gw['points']} pts this week, "
          f"{entry['overall_points']} overall")
    if entry.get("overall_rank"):
        print(f"Overall rank {entry['overall_rank']:,}")
    print(f"Squad value {money['squad_value']:.1f}m, bank {money['bank']:.1f}m, "
          f"budget {money['budget']:.1f}m")
    if gw.get("chip"):
        print(f"Chip played: {gw['chip']}")

    def line(player):
        marks = []
        if player["is_captain"]:
            marks.append("(C)")
        if player["is_vice_captain"]:
            marks.append("(V)")
        if player["mean_defence"] and player["position_id"] in (1, 2):
            marks.append("D")
        if player["flagged"]:
            chance = player["chance_of_playing"]
            marks.append(f"FLAG{'' if chance is None else f' {chance}%'}")
        return (f"  {player['position']:<4} {player['web_name']:<18} "
                f"{player['team_short']:<4} {player['price']:>5.1f}m "
                f"{player['points']:>4} pts  form {player['form']:>4.1f}  "
                f"{' '.join(marks)}")

    print("\nStarting eleven")
    for player in team["starting_xi"]:
        print(line(player))
    print("\nBench")
    for player in team["bench"]:
        print(line(player))

    if team["flagged"]:
        print(f"\n{len(team['flagged'])} player(s) carrying a flag - "
              "the pick process will hold these back:")
        for player in team["flagged"]:
            note = player["news"] or "no detail given"
            print(f"  {player['web_name']} ({player['team_short']}): {note}")


def main(argv: Optional[List[str]] = None) -> int:
    import sys
    args = list(argv if argv is not None else sys.argv[1:])
    if not args:
        print(__doc__)
        print("Give a team id or a link to the team page.")
        return 1

    gameweek = None
    if "--gameweek" in args:
        i = args.index("--gameweek")
        try:
            gameweek = int(args[i + 1])
        except (IndexError, ValueError):
            print("--gameweek needs a number, for example --gameweek 9")
            return 1
        del args[i:i + 2]

    try:
        team = fetch_manager_team(args[0], gameweek=gameweek)
    except FPLTeamError as exc:
        print(f"Error: {exc}")
        return 1

    _print_team(team)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
