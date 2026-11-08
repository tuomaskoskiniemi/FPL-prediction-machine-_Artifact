"""Build the player browser payload: every player, every stat the API publishes.

The FPL API defines its own list of statistics in bootstrap-static under
"element_stats" (26 of them). That list is used here verbatim, so whenever the
API adds a statistic the browser picks it up without a code change. A handful of
core fields the API keeps outside that list - price, form, points, ownership,
availability - are added in front of it.

The payload is embedded in the page as JSON and rendered in the browser, which
keeps the HTML small and the filtering instant.
"""

import json

# Fields the API keeps outside element_stats but that a manager picks on.
CORE = [
    ("total_points", "Total points"),
    ("event_points", "Points this GW"),
    ("form", "Form"),
    ("points_per_game", "Points per game"),
    ("selected_by_percent", "Owned %"),
    ("cost_change_start", "Price change"),
    ("ep_next", "Expected pts next"),
    ("transfers_in_event", "Transfers in (GW)"),
    ("transfers_out_event", "Transfers out (GW)"),
    ("value_season", "Value (pts per m)"),
]

TENTHS = {"cost_change_start"}          # API reports these in tenths of a million


def _number(value):
    """Coerce the API's strings-that-are-numbers into numbers, leave the rest."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return text
    return int(number) if number.is_integer() else number


def browser_payload(bootstrap, defence_ids):
    """A compact JSON blob: column definitions, teams, positions and players."""
    stats = [(s["name"], s["label"]) for s in bootstrap.get("element_stats", [])]
    columns = CORE + [s for s in stats if s[0] not in {c[0] for c in CORE}]

    teams = sorted(
        ({"id": t["id"], "short": t["short_name"], "name": t["name"]}
         for t in bootstrap.get("teams", [])),
        key=lambda t: t["name"])
    positions = [{"id": t["id"], "short": t["singular_name_short"],
                  "name": t["plural_name"]}
                 for t in sorted(bootstrap.get("element_types", []),
                                 key=lambda t: t["id"])]

    players = []
    for element in bootstrap.get("elements", []):
        values = []
        for key, _label in columns:
            value = _number(element.get(key))
            if key in TENTHS and isinstance(value, (int, float)):
                value = value / 10
            values.append(value)
        players.append({
            "i": element["id"],
            "w": element["web_name"],
            "n": f"{element.get('first_name', '')} "
                 f"{element.get('second_name', '')}".strip(),
            "t": element["team"],
            "p": element["element_type"],
            "c": element["now_cost"] / 10,
            "st": element.get("status", "a"),
            "cp": element.get("chance_of_playing_next_round"),
            "news": (element.get("news") or "")[:160],
            "d": 1 if element["team"] in defence_ids else 0,
            "v": values,
        })

    payload = {
        "columns": [{"key": k, "label": l} for k, l in columns],
        "teams": teams,
        "positions": positions,
        "players": players,
    }
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=True)
