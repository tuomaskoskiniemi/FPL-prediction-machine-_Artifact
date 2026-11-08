"""
FPL Data Fetcher - Hakee kaikki FPL API -datat JSON-tiedostoiksi.
Aja tämä paikallisesti: python fetch_fpl_data.py

The FPL API always serves the season that is currently running, so this script
fetches whichever season is live (2026/27 from August 2026 onwards). The files
in "FPL Data" are therefore always the current season; when the API rolls over
to a new season the previous files are moved to "FPL Data/archive/<season>"
instead of being overwritten, so completed seasons stay available for analysis.

Options:
    --no-archive     overwrite in place, do not archive the previous season
    --skip-players   skip player details (the slow step: one call per player)
    --skip-live      skip per-gameweek live data
"""

import requests
import json
import os
import shutil
import sys
import time

BASE_URL = "https://fantasy.premierleague.com/api"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "FPL Data")
ARCHIVE_DIR = os.path.join(OUTPUT_DIR, "archive")
HEADERS = {"User-Agent": "Mozilla/5.0"}

DATA_FILES = [
    "bootstrap_static.json",
    "fixtures.json",
    "player_details.json",
    "live_gameweeks.json",
]


def fetch_json(url, description=""):
    """Fetch JSON from URL with retry."""
    for attempt in range(3):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if attempt < 2:
                print(f"  Retry {attempt+1} for {description}...")
                time.sleep(2)
            else:
                print(f"  FAILED: {description} - {e}")
                return None


def season_label(bootstrap):
    """Derive a season label such as '2026-27' from the gameweek deadlines."""
    events = bootstrap.get("events") or []
    if not events:
        return "unknown"
    first = (events[0].get("deadline_time") or "")[:4]
    if not first.isdigit():
        return "unknown"
    start = int(first)
    return f"{start}-{str(start + 1)[-2:]}"


def stored_season():
    """Season label of the data currently in "FPL Data", or None if empty."""
    path = os.path.join(OUTPUT_DIR, "bootstrap_static.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return season_label(json.load(f))
    except (ValueError, OSError):
        return None


def archive_previous(previous):
    """Move the existing season's files into "FPL Data/archive/<season>"."""
    target = os.path.join(ARCHIVE_DIR, previous)
    os.makedirs(target, exist_ok=True)

    moved = []
    for name in DATA_FILES:
        source = os.path.join(OUTPUT_DIR, name)
        if not os.path.exists(source):
            continue
        shutil.move(source, os.path.join(target, name))
        moved.append(name)

    with open(os.path.join(target, "season.json"), "w", encoding="utf-8") as f:
        json.dump({"season": previous, "files": moved}, f, indent=2)

    print(f"   Archived {len(moved)} file(s) from {previous} to archive/{previous}/")
    return moved


def write_json(name, payload):
    with open(os.path.join(OUTPUT_DIR, name), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def main():
    argv = sys.argv[1:]
    no_archive = "--no-archive" in argv
    skip_players = "--skip-players" in argv
    skip_live = "--skip-live" in argv

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1. Bootstrap-static (players, teams, events, element_types)
    print("1/4 Fetching bootstrap-static...")
    bootstrap = fetch_json(f"{BASE_URL}/bootstrap-static/", "bootstrap-static")
    if not bootstrap:
        print("Cannot continue without bootstrap-static data!")
        sys.exit(1)

    season = season_label(bootstrap)
    previous = stored_season()
    print(f"   API is serving season {season}")

    if previous and previous != season and not no_archive:
        print(f"   Stored data is season {previous} - archiving it first")
        archive_previous(previous)
    elif previous and previous != season:
        print(f"   Stored data is season {previous} - overwriting (--no-archive)")

    write_json("bootstrap_static.json", bootstrap)
    write_json("season.json", {"season": season})

    player_count = len(bootstrap.get("elements", []))
    team_count = len(bootstrap.get("teams", []))
    event_count = len(bootstrap.get("events", []))
    finished = [e for e in bootstrap.get("events", []) if e.get("finished")]
    print(f"   Players: {player_count}, Teams: {team_count}, Gameweeks: {event_count}"
          f" ({len(finished)} finished)")

    # 2. Fixtures
    print("2/4 Fetching fixtures...")
    fixtures = fetch_json(f"{BASE_URL}/fixtures/", "fixtures")
    if fixtures:
        write_json("fixtures.json", fixtures)
        played = sum(1 for f in fixtures if f.get("finished"))
        print(f"   Fixtures: {len(fixtures)} ({played} played)")

    # 3. Player detail (element-summary) for all players
    if skip_players:
        print("3/4 Skipping player details (--skip-players)")
    else:
        print(f"3/4 Fetching player details for {player_count} players...")
        player_details = {}
        for i, player in enumerate(bootstrap.get("elements", []), 1):
            pid = player["id"]
            if i % 50 == 0 or i == 1:
                print(f"   Player {i}/{player_count} (id={pid})...")
            detail = fetch_json(f"{BASE_URL}/element-summary/{pid}/", f"player {pid}")
            if detail:
                player_details[str(pid)] = detail
            # Be polite to the API
            if i % 10 == 0:
                time.sleep(0.3)

        write_json("player_details.json", player_details)
        print(f"   Fetched details for {len(player_details)} players")

    # 4. Live gameweek data for completed gameweeks
    if skip_live:
        print("4/4 Skipping live gameweek data (--skip-live)")
    elif not finished:
        print("4/4 No finished gameweeks yet - nothing to fetch")
        write_json("live_gameweeks.json", {})
    else:
        print("4/4 Fetching live gameweek data...")
        live_data = {}
        for i, event in enumerate(finished, 1):
            eid = event["id"]
            if i % 5 == 0 or i == 1:
                print(f"   Gameweek {eid} ({i}/{len(finished)})...")
            data = fetch_json(f"{BASE_URL}/event/{eid}/live/", f"GW {eid}")
            if data:
                live_data[str(eid)] = data
            if i % 5 == 0:
                time.sleep(0.5)

        write_json("live_gameweeks.json", live_data)
        print(f"   Fetched data for {len(live_data)} gameweeks")

    print(f"\nSeason {season} data saved to: {OUTPUT_DIR}")
    print("Files:")
    for name in sorted(os.listdir(OUTPUT_DIR)):
        path = os.path.join(OUTPUT_DIR, name)
        if os.path.isfile(path):
            print(f"  {name} ({os.path.getsize(path)/1024/1024:.1f} MB)")

    if os.path.isdir(ARCHIVE_DIR):
        archived = sorted(d for d in os.listdir(ARCHIVE_DIR)
                          if os.path.isdir(os.path.join(ARCHIVE_DIR, d)))
        if archived:
            print(f"Archived seasons: {', '.join(archived)}")

    print("\nDone!")


if __name__ == "__main__":
    main()
