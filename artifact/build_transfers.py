"""Transfer proposals: who to take out, who to bring in, and why.

Candidates are ranked by the six picking principles the rest of the tool uses,
in the order the specification puts them:

  form over fixtures      recent points carry the most weight; the fixtures
                          ahead only break ties
  never an injured player flagged players are dropped from the list entirely
  mean defences           keepers and defenders from the eight teams conceding
                          fewest goals get a lift
  attacking midfielders   goals and assists count for more than appearances
  attacking defenders     the same lift applies to defenders who create
  full minutes            a player who finishes matches outranks a substitute

The score is deliberately simple and every part of it is a column in the table,
so a proposal can be argued with rather than taken on trust.
"""

RECENT_MINUTES = 450          # five full matches
CANDIDATES_PER_POSITION = 30
MIN_RECENT_MINUTES = 150      # roughly two matches out of the last five

POSITIONS = (("GKP", 1, "Goalkeepers"), ("DEF", 2, "Defenders"),
             ("MID", 3, "Midfielders"), ("FWD", 4, "Forwards"))


def transfer_score(player, fdr_next5, mean_defence):
    """Points a player is worth bringing in, highest first."""
    recent = player.get("pts5", 0)
    returns = player.get("goals5", 0) + player.get("assists5", 0)
    minutes_share = min(1.0, player.get("minutes5", 0) / RECENT_MINUTES)

    score = recent * minutes_share          # form, weighted by actually playing
    score += returns * 1.5                  # goals and assists, any position
    if mean_defence and player["pos_id"] in (1, 2):
        score += 2.0                        # a defence that keeps clean sheets
    if fdr_next5:
        score += (3.0 - fdr_next5) * 1.5    # fixtures, as a tie-breaker only
    return score


def squad_view(squad, recent_by_id, fdr_by_team):
    """The manager's own players with season and last-five figures together."""
    rows = []
    for player in squad["all_players"]:
        recent = recent_by_id.get(player["id"], {})
        rows.append({
            "id": player["id"],
            "web": player["web_name"],
            "team": player["team_short"],
            "pos": player["position"],
            "pos_id": player["position_id"],
            "price": player["price"],
            "points": player["points"],
            "minutes": player["minutes"],
            "goals": player["goals"],
            "assists": player["assists"],
            "clean_sheets": player["clean_sheets"],
            "pts5": recent.get("pts5"),
            "minutes5": recent.get("minutes5"),
            "returns5": (None if not recent else
                         recent.get("goals5", 0) + recent.get("assists5", 0)),
            "fdr5": fdr_by_team.get(player["team_short"]),
            "flagged": player["flagged"],
            "chance": player["chance_of_playing"],
            "news": player["news"],
            "mean_defence": player["mean_defence"],
            "on_bench": player["on_bench"],
        })
    rows.sort(key=lambda r: (r["pos_id"], -(r["points"] or 0)))
    return rows


def candidates(recent_players, owned_ids, fdr_by_team, defence_shorts,
               limit=CANDIDATES_PER_POSITION):
    """Ranked replacements for every position, excluding players already owned."""
    by_position = {}
    for label, pos_id, title in POSITIONS:
        pool = []
        for player in recent_players:
            if player["pos_id"] != pos_id or player["id"] in owned_ids:
                continue
            if player["status"] != "a":            # never propose an injured player
                continue
            if player.get("minutes5", 0) < MIN_RECENT_MINUTES:
                continue
            fdr = fdr_by_team.get(player["team"])
            entry = dict(player)
            entry["fdr5"] = fdr
            entry["mean_defence"] = player["team"] in defence_shorts
            entry["score"] = transfer_score(player, fdr, entry["mean_defence"])
            entry["returns5"] = player.get("goals5", 0) + player.get("assists5", 0)
            pool.append(entry)
        pool.sort(key=lambda p: (-p["score"], -p.get("pts5", 0)))
        by_position[label] = (title, pool[:limit])
    return by_position
