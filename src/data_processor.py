"""
Data processing utilities for FPL API data.

Provides functions to process, filter, and format FPL API responses.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime


def get_current_gameweek(bootstrap_static: Dict[str, Any]) -> Optional[int]:
    """
    Get the current gameweek ID from bootstrap static data.
    
    Args:
        bootstrap_static: The bootstrap-static API response
        
    Returns:
        Current gameweek ID, or None if not found
    """
    if not bootstrap_static or 'events' not in bootstrap_static:
        return None
    
    events = bootstrap_static['events']
    for event in events:
        if event.get('is_current', False):
            return event.get('id')
    
    # If no current event, try to find the next one
    for event in events:
        if event.get('is_next', False):
            return event.get('id')
    
    return None


def get_current_gameweek_fixtures(
    fixtures: List[Dict[str, Any]],
    bootstrap_static: Dict[str, Any],
    gameweek_id: Optional[int]
) -> List[Dict[str, Any]]:
    """
    Filter fixtures for the current gameweek.
    
    Args:
        fixtures: List of all fixtures
        bootstrap_static: Bootstrap static data (for team information)
        gameweek_id: The current gameweek ID
        
    Returns:
        List of fixtures for the current gameweek
    """
    if not gameweek_id:
        return []
    
    gw_fixtures = [f for f in fixtures if f.get('event') == gameweek_id]
    
    # Sort by kickoff time
    gw_fixtures.sort(key=lambda x: x.get('kickoff_time', ''))
    
    return gw_fixtures


def calculate_team_stats_from_fixtures(fixtures: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    """
    Calculate complete league standings from finished fixtures.
    Includes: played, won, drawn, lost, goals_for, goals_against, goal_difference, points.
    
    Args:
        fixtures: List of all fixtures
        
    Returns:
        Dictionary mapping team_id to complete stats dict
    """
    team_stats = {}
    
    for fixture in fixtures:
        if not fixture.get('finished', False):
            continue
        
        team_h_id = fixture.get('team_h')
        team_a_id = fixture.get('team_a')
        team_h_score = fixture.get('team_h_score', None)
        team_a_score = fixture.get('team_a_score', None)
        
        # Skip if scores are missing or None
        if team_h_id is None or team_a_id is None or team_h_score is None or team_a_score is None:
            continue
        
        team_h_score = int(team_h_score)
        team_a_score = int(team_a_score)
        
        # Initialize team stats if not exists
        if team_h_id not in team_stats:
            team_stats[team_h_id] = {
                'played': 0,
                'won': 0,
                'drawn': 0,
                'lost': 0,
                'goals_for': 0,
                'goals_against': 0,
                'points': 0
            }
        if team_a_id not in team_stats:
            team_stats[team_a_id] = {
                'played': 0,
                'won': 0,
                'drawn': 0,
                'lost': 0,
                'goals_for': 0,
                'goals_against': 0,
                'points': 0
            }
        
        # Update match counts
        team_stats[team_h_id]['played'] += 1
        team_stats[team_a_id]['played'] += 1
        
        # Add goals
        team_stats[team_h_id]['goals_for'] += team_h_score
        team_stats[team_h_id]['goals_against'] += team_a_score
        team_stats[team_a_id]['goals_for'] += team_a_score
        team_stats[team_a_id]['goals_against'] += team_h_score
        
        # Determine result and update win/draw/loss and points
        if team_h_score > team_a_score:
            # Home team wins
            team_stats[team_h_id]['won'] += 1
            team_stats[team_h_id]['points'] += 3
            team_stats[team_a_id]['lost'] += 1
        elif team_a_score > team_h_score:
            # Away team wins
            team_stats[team_a_id]['won'] += 1
            team_stats[team_a_id]['points'] += 3
            team_stats[team_h_id]['lost'] += 1
        else:
            # Draw
            team_stats[team_h_id]['drawn'] += 1
            team_stats[team_h_id]['points'] += 1
            team_stats[team_a_id]['drawn'] += 1
            team_stats[team_a_id]['points'] += 1
    
    # Calculate goal difference for all teams
    for team_id, stats in team_stats.items():
        stats['goal_difference'] = stats['goals_for'] - stats['goals_against']
    
    return team_stats


def process_league_table(
    bootstrap_static: Dict[str, Any],
    fixtures: Optional[List[Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """
    Process and sort league table data from bootstrap static.
    Optionally includes goals for/against if fixtures are provided.
    Now includes last 5 games results.
    
    Args:
        bootstrap_static: The bootstrap-static API response
        fixtures: Optional list of fixtures to calculate GF/GA/GD and last 5 games
        
    Returns:
        List of teams sorted by position (points, then goal difference)
    """
    if not bootstrap_static or 'teams' not in bootstrap_static:
        return []
    
    teams = bootstrap_static['teams']
    teams_dict = {team['id']: team for team in teams}
    
    # Calculate complete stats from fixtures if available
    fixture_stats = {}
    if fixtures:
        fixture_stats = calculate_team_stats_from_fixtures(fixtures)
    
    # Format for frontend
    table = []
    for team in teams:
        team_id = team.get('id')
        
        # Get fixture stats if available, otherwise use team data as fallback
        stats = fixture_stats.get(team_id, {})
        
        # Use fixture stats if available, otherwise fall back to team data from API
        played = stats.get('played', team.get('played', 0))
        win = stats.get('won', team.get('win', 0))
        draw = stats.get('drawn', team.get('draw', 0))
        loss = stats.get('lost', team.get('loss', 0))
        goals_for = stats.get('goals_for', 0)
        goals_against = stats.get('goals_against', 0)
        goal_difference = stats.get('goal_difference', 0)
        points = stats.get('points', team.get('points', 0))
        
        # Get last 5 games results
        last_5_games = []
        if fixtures:
            past_fixtures = get_team_past_fixtures(fixtures, team_id, 5)
            for fixture in past_fixtures:
                is_home = fixture.get('team_h') == team_id
                opponent_id = fixture.get('team_a') if is_home else fixture.get('team_h')
                team_score = fixture.get('team_h_score') if is_home else fixture.get('team_a_score')
                opponent_score = fixture.get('team_a_score') if is_home else fixture.get('team_h_score')
                opponent_name = teams_dict.get(opponent_id, {}).get('short_name', '')
                
                # Determine result
                if team_score is None or opponent_score is None:
                    result = '-'
                elif team_score > opponent_score:
                    result = 'W'
                elif team_score < opponent_score:
                    result = 'L'
                else:
                    result = 'D'
                
                last_5_games.append({
                    'result': result,
                    'opponent': opponent_name,
                    'opponent_id': opponent_id,
                    'team_score': team_score or 0,
                    'opponent_score': opponent_score or 0,
                    'is_home': is_home
                })
        
        table.append({
            'position': 0,  # Will be calculated based on points/GD
            'id': team_id,
            'name': team.get('name'),
            'short_name': team.get('short_name'),
            'played': played,
            'win': win,
            'draw': draw,
            'loss': loss,
            'goals_for': goals_for,
            'goals_against': goals_against,
            'goal_difference': goal_difference,
            'points': points,
            'form': team.get('form', ''),
            'strength_overall_home': team.get('strength_overall_home', 0),
            'strength_overall_away': team.get('strength_overall_away', 0),
            'last_5_games': last_5_games,
        })
    
    # Sort by points (descending), then goal difference (descending), then goals for (descending)
    table.sort(key=lambda x: (-x['points'], -x['goal_difference'], -x['goals_for']))
    
    # Assign positions based on sorted order
    for i, team in enumerate(table, start=1):
        team['position'] = i
    
    return table


def format_fixture_data(
    fixtures: List[Dict[str, Any]],
    bootstrap_static: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Format fixture data with team names, form, and status information.
    
    Args:
        fixtures: List of fixture dictionaries
        bootstrap_static: Bootstrap static data for team information
        
    Returns:
        List of formatted fixture dictionaries
    """
    if not bootstrap_static or 'teams' not in bootstrap_static:
        return []
    
    teams = {team['id']: team for team in bootstrap_static['teams']}
    formatted = []
    
    for fixture in fixtures:
        team_h_id = fixture.get('team_h')
        team_a_id = fixture.get('team_a')
        
        team_h = teams.get(team_h_id, {})
        team_a = teams.get(team_a_id, {})
        
        kickoff_time = fixture.get('kickoff_time')
        started = fixture.get('started', False)
        finished = fixture.get('finished', False)
        
        # Determine match status
        if finished:
            status = 'finished'
        elif started:
            status = 'live'
        else:
            status = 'upcoming'
        
        formatted_fixture = {
            'id': fixture.get('id'),
            'code': fixture.get('code'),
            'event': fixture.get('event'),
            'team_h': {
                'id': team_h_id,
                'name': team_h.get('name', 'Unknown'),
                'short_name': team_h.get('short_name', ''),
                'score': fixture.get('team_h_score'),
                'difficulty': fixture.get('team_h_difficulty', 0),
                'form': team_h.get('form', '')
            },
            'team_a': {
                'id': team_a_id,
                'name': team_a.get('name', 'Unknown'),
                'short_name': team_a.get('short_name', ''),
                'score': fixture.get('team_a_score'),
                'difficulty': fixture.get('team_a_difficulty', 0),
                'form': team_a.get('form', '')
            },
            'kickoff_time': kickoff_time,
            'status': status,
            'started': started,
            'finished': finished,
            'minutes': fixture.get('minutes', 0)
        }
        
        formatted.append(formatted_fixture)
    
    return formatted


def format_datetime(dt_string: Optional[str]) -> str:
    """
    Format datetime string for display.
    
    Args:
        dt_string: ISO format datetime string
        
    Returns:
        Formatted date/time string
    """
    if not dt_string:
        return ''
    
    try:
        dt = datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
        return dt.strftime('%d %b %Y, %H:%M')
    except (ValueError, AttributeError):
        return dt_string


def get_team_upcoming_fixtures(
    fixtures: List[Dict[str, Any]],
    team_id: int,
    current_gameweek: Optional[int],
    num_games: int = 5
) -> List[Dict[str, Any]]:
    """
    Get upcoming fixtures for a specific team.
    
    Args:
        fixtures: List of all fixtures
        team_id: The team ID
        current_gameweek: Current gameweek ID
        num_games: Number of upcoming games to return (default 5)
        
    Returns:
        List of upcoming fixtures for the team, sorted by gameweek
    """
    if not current_gameweek:
        return []
    
    upcoming = []
    for fixture in fixtures:
        # Skip finished fixtures
        if fixture.get('finished', False):
            continue
        
        # Check if team is involved
        if fixture.get('team_h') == team_id or fixture.get('team_a') == team_id:
            # Get fixture gameweek
            event = fixture.get('event')
            if event and event >= current_gameweek:
                upcoming.append(fixture)
    
    # Sort by gameweek and kickoff time
    upcoming.sort(key=lambda x: (x.get('event', 999), x.get('kickoff_time', '')))
    
    # Return only the requested number
    return upcoming[:num_games]


def get_team_past_fixtures(
    fixtures: List[Dict[str, Any]],
    team_id: int,
    num_games: int = 5
) -> List[Dict[str, Any]]:
    """
    Get past fixtures for a specific team.
    
    Args:
        fixtures: List of all fixtures
        team_id: The team ID
        num_games: Number of past games to return (default 5)
        
    Returns:
        List of past fixtures for the team, sorted by gameweek (most recent first)
    """
    past = []
    for fixture in fixtures:
        # Only finished fixtures
        if not fixture.get('finished', False):
            continue
        
        # Check if team is involved
        if fixture.get('team_h') == team_id or fixture.get('team_a') == team_id:
            past.append(fixture)
    
    # Sort by gameweek (descending) and kickoff time
    past.sort(key=lambda x: (x.get('event', 0), x.get('kickoff_time', '')), reverse=True)
    
    # Return only the requested number
    return past[:num_games]


def calculate_fdr_average(
    fixtures: List[Dict[str, Any]],
    team_id: int
) -> Optional[float]:
    """
    Calculate average FDR (Fixture Difficulty Rating) for a team's fixtures.
    
    Args:
        fixtures: List of fixtures (should be upcoming fixtures)
        team_id: The team ID
        
    Returns:
        Average FDR, or None if no fixtures
    """
    if not fixtures:
        return None
    
    total_fdr = 0
    count = 0
    
    for fixture in fixtures:
        # Determine if team is home or away
        if fixture.get('team_h') == team_id:
            fdr = fixture.get('team_h_difficulty', 0)
        elif fixture.get('team_a') == team_id:
            fdr = fixture.get('team_a_difficulty', 0)
        else:
            continue
        
        if fdr > 0:
            total_fdr += fdr
            count += 1
    
    if count == 0:
        return None
    
    return round(total_fdr / count, 2)


def calculate_adjusted_fdr(
    fixtures: List[Dict[str, Any]],
    team_id: int,
    bootstrap_static: Dict[str, Any]
) -> Optional[float]:
    """
    Calculate adjusted FDR accounting for home/away advantage and opponent strength.
    
    Adjusted FDR = Base FDR - (home_advantage) + (opponent_strength_factor)
    
    Args:
        fixtures: List of fixtures (should be upcoming fixtures)
        team_id: The team ID
        bootstrap_static: Bootstrap static data for team strength ratings
        
    Returns:
        Adjusted average FDR, or None if no fixtures
    """
    if not fixtures:
        return None
    
    if not bootstrap_static or 'teams' not in bootstrap_static:
        return calculate_fdr_average(fixtures, team_id)
    
    teams = {team['id']: team for team in bootstrap_static['teams']}
    team_data = teams.get(team_id, {})
    team_strength = team_data.get('strength', 1000) / 1000.0  # Normalize
    
    total_adjusted_fdr = 0
    count = 0
    
    for fixture in fixtures:
        # Determine if team is home or away
        is_home = fixture.get('team_h') == team_id
        opponent_id = fixture.get('team_a') if is_home else fixture.get('team_h')
        
        if not opponent_id:
            continue
        
        opponent_data = teams.get(opponent_id, {})
        opponent_strength = opponent_data.get('strength', 1000) / 1000.0
        
        # Get base FDR
        if is_home:
            base_fdr = fixture.get('team_h_difficulty', 0)
        else:
            base_fdr = fixture.get('team_a_difficulty', 0)
        
        if base_fdr <= 0:
            continue
        
        # Adjust for home advantage (reduce FDR by 0.5 for home games)
        home_adj = 0.5 if is_home else 0
        
        # Adjust for opponent strength relative to team strength
        # Stronger opponent increases difficulty
        strength_diff = opponent_strength - team_strength
        strength_adj = strength_diff * 0.5  # Scale the adjustment
        
        # Calculate adjusted FDR (clamp between 1 and 5)
        adjusted_fdr = base_fdr - home_adj + strength_adj
        adjusted_fdr = max(1.0, min(5.0, adjusted_fdr))
        
        total_adjusted_fdr += adjusted_fdr
        count += 1
    
    if count == 0:
        return None
    
    return round(total_adjusted_fdr / count, 2)


def calculate_points_per_game(
    fixtures: List[Dict[str, Any]],
    team_id: int
) -> Optional[float]:
    """
    Calculate average points per game from FPL fixtures.
    FPL points: 3 for win, 1 for draw, 0 for loss.
    
    Args:
        fixtures: List of past fixtures (should be finished)
        team_id: The team ID
        
    Returns:
        Average points per game, or None if no fixtures
    """
    if not fixtures:
        return None
    
    total_points = 0
    count = 0
    
    for fixture in fixtures:
        if not fixture.get('finished', False):
            continue
        
        team_h_id = fixture.get('team_h')
        team_a_id = fixture.get('team_a')
        team_h_score = fixture.get('team_h_score') or 0
        team_a_score = fixture.get('team_a_score') or 0
        
        if team_h_id == team_id:
            # Team is home
            if team_h_score > team_a_score:
                points = 3  # Win
            elif team_h_score == team_a_score:
                points = 1  # Draw
            else:
                points = 0  # Loss
            total_points += points
            count += 1
        elif team_a_id == team_id:
            # Team is away
            if team_a_score > team_h_score:
                points = 3  # Win
            elif team_a_score == team_h_score:
                points = 1  # Draw
            else:
                points = 0  # Loss
            total_points += points
            count += 1
    
    if count == 0:
        return None
    
    return round(total_points / count, 2)


def get_team_analysis_data(
    fixtures: List[Dict[str, Any]],
    bootstrap_static: Dict[str, Any],
    team_id: int
) -> Dict[str, Any]:
    """
    Get comprehensive analysis data for a team.
    
    Args:
        fixtures: List of all fixtures
        bootstrap_static: Bootstrap static data
        team_id: The team ID
        
    Returns:
        Dictionary with team analysis metrics
    """
    current_gw = get_current_gameweek(bootstrap_static)
    
    # Get upcoming fixtures
    next_5_fixtures = get_team_upcoming_fixtures(fixtures, team_id, current_gw, 5)
    next_10_fixtures = get_team_upcoming_fixtures(fixtures, team_id, current_gw, 10)
    
    # Get past fixtures
    last_5_fixtures = get_team_past_fixtures(fixtures, team_id, 5)
    last_10_fixtures = get_team_past_fixtures(fixtures, team_id, 10)
    
    # Calculate FDR averages
    fdr_next_5 = calculate_fdr_average(next_5_fixtures, team_id)
    fdr_next_10 = calculate_fdr_average(next_10_fixtures, team_id)
    
    # Calculate adjusted FDR
    adj_fdr_next_5 = calculate_adjusted_fdr(next_5_fixtures, team_id, bootstrap_static)
    adj_fdr_next_10 = calculate_adjusted_fdr(next_10_fixtures, team_id, bootstrap_static)
    
    # Calculate points per game
    ppg_last_5 = calculate_points_per_game(last_5_fixtures, team_id)
    ppg_last_10 = calculate_points_per_game(last_10_fixtures, team_id)
    
    # Get team info
    teams = {team['id']: team for team in bootstrap_static.get('teams', [])}
    team_data = teams.get(team_id, {})
    
    return {
        'team_id': team_id,
        'team_name': team_data.get('name', 'Unknown'),
        'short_name': team_data.get('short_name', ''),
        'next_5_fixtures': format_fixture_data(next_5_fixtures, bootstrap_static),
        'next_10_fixtures': format_fixture_data(next_10_fixtures, bootstrap_static),
        'fdr_next_5': fdr_next_5,
        'fdr_next_10': fdr_next_10,
        'adjusted_fdr_next_5': adj_fdr_next_5,
        'adjusted_fdr_next_10': adj_fdr_next_10,
        'ppg_last_5': ppg_last_5,
        'ppg_last_10': ppg_last_10,
        'games_played_last_5': len(last_5_fixtures),
        'games_played_last_10': len(last_10_fixtures)
    }


def get_all_teams_analysis(
    fixtures: List[Dict[str, Any]],
    bootstrap_static: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Get analysis data for all teams.
    
    Args:
        fixtures: List of all fixtures
        bootstrap_static: Bootstrap static data
        
    Returns:
        List of team analysis dictionaries
    """
    if not bootstrap_static or 'teams' not in bootstrap_static:
        return []
    
    teams_analysis = []
    for team in bootstrap_static['teams']:
        team_id = team.get('id')
        if team_id:
            analysis = get_team_analysis_data(fixtures, bootstrap_static, team_id)
            teams_analysis.append(analysis)
    
    return teams_analysis


def get_top_players_by_position(
    bootstrap_static: Dict[str, Any],
    player_summaries: Optional[Dict[int, Dict[str, Any]]] = None,
    position_id: Optional[int] = None,
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Get top players by position based on last 5 games performance.
    
    Args:
        bootstrap_static: Bootstrap static data
        player_summaries: Optional dict of player_id -> player summary data
        position_id: Optional position ID to filter (1=GK, 2=DEF, 3=MID, 4=FWD)
        limit: Optional limit for number of players to return
        
    Returns:
        List of player dictionaries sorted by last 5 games points
    """
    if not bootstrap_static or 'elements' not in bootstrap_static:
        return []
    
    players = bootstrap_static['elements']
    teams = {team['id']: team for team in bootstrap_static.get('teams', [])}
    element_types = {et['id']: et for et in bootstrap_static.get('element_types', [])}
    
    # Filter by position if specified
    if position_id:
        players = [p for p in players if p.get('element_type') == position_id]
    
    # Calculate last 5 and last 3 games points for each player
    player_scores = []
    for player in players:
        last_5_points = 0
        last_3_points = 0
        last_5_games_count = 0
        last_3_games_count = 0
        
        # If player summaries provided, calculate from history
        if player_summaries and player['id'] in player_summaries:
            history = player_summaries[player['id']].get('history', [])
            # Sort by gameweek descending and take last 5 and last 3
            sorted_history = sorted(history, key=lambda x: x.get('round', 0), reverse=True)
            last_5_games = sorted_history[:5]
            last_3_games = sorted_history[:3]
            last_5_points = sum(game.get('total_points', 0) for game in last_5_games)
            last_3_points = sum(game.get('total_points', 0) for game in last_3_games)
            last_5_games_count = len(last_5_games)
            last_3_games_count = len(last_3_games)
        else:
            # Fallback to form or event_points if available
            form = player.get('form', '0')
            try:
                form_float = float(form) if form else 0.0
                last_5_points = form_float * 5  # Approximate
                last_3_points = form_float * 3  # Approximate
            except (ValueError, TypeError):
                event_points = player.get('event_points', 0)
                last_5_points = event_points
                last_3_points = event_points * 0.6  # Rough estimate
            starts = player.get('starts', 0)
            last_5_games_count = starts if starts <= 5 else 5
            last_3_games_count = starts if starts <= 3 else 3
        
        # Prepare player data
        team_id = player.get('team')
        team_data = teams.get(team_id, {})
        position_data = element_types.get(player.get('element_type', 0), {})
        
        player_data = {
            'id': player.get('id'),
            'code': player.get('code'),
            'first_name': player.get('first_name', ''),
            'second_name': player.get('second_name', ''),
            'web_name': player.get('web_name', ''),
            'photo': player.get('photo', ''),
            'team_id': team_id,
            'team_name': team_data.get('name', ''),
            'team_short_name': team_data.get('short_name', ''),
            'position_id': player.get('element_type'),
            'position_name': position_data.get('singular_name', ''),
            'position_short_name': position_data.get('singular_name_short', ''),
            'status': player.get('status', ''),
            'now_cost': float(player.get('now_cost', 0)) / 10.0,  # Convert from tenths
            'total_points': int(player.get('total_points', 0)),
            'points_per_game': float(player.get('points_per_game') or 0),
            'form': str(player.get('form', '0')),
            'event_points': int(player.get('event_points', 0)),
            'goals_scored': int(player.get('goals_scored', 0)),
            'assists': int(player.get('assists', 0)),
            'clean_sheets': int(player.get('clean_sheets', 0)),
            'goals_conceded': int(player.get('goals_conceded', 0)),
            'saves': int(player.get('saves', 0)),
            'minutes': int(player.get('minutes', 0)),
            'starts': int(player.get('starts', 0)),
            'yellow_cards': int(player.get('yellow_cards', 0)),
            'red_cards': int(player.get('red_cards', 0)),
            'selected_by_percent': float(player.get('selected_by_percent') or 0),
            'transfers_in': int(player.get('transfers_in', 0)),
            'transfers_out': int(player.get('transfers_out', 0)),
            'ict_index': float(player.get('ict_index') or 0),
            'influence': float(player.get('influence', 0) or 0),
            'creativity': float(player.get('creativity', 0) or 0),
            'threat': float(player.get('threat', 0) or 0),
            'expected_goals': float(player.get('expected_goals', 0) or 0),
            'expected_assists': float(player.get('expected_assists', 0) or 0),
            'expected_goal_involvements': float(player.get('expected_goal_involvements', 0) or 0),
            'expected_goals_conceded': float(player.get('expected_goals_conceded', 0) or 0),
            'chance_of_playing_this_round': player.get('chance_of_playing_this_round', None),
            'chance_of_playing_next_round': player.get('chance_of_playing_next_round', None),
            'news': player.get('news', ''),
            'last_5_games_points': float(last_5_points),
            'last_5_games_count': int(last_5_games_count),
            'last_3_games_points': float(last_3_points),
            'last_3_games_count': int(last_3_games_count),
            'points_per_million': float((player.get('total_points', 0) or 0) / (player.get('now_cost', 10) / 10.0)) if (player.get('now_cost', 0) > 0) else 0.0
        }
        player_scores.append(player_data)
    
    # Sort by last 5 games points (descending), then by total points, then by points per game
    player_scores.sort(
        key=lambda x: (x['last_5_games_points'], x['total_points'], x['points_per_game']),
        reverse=True
    )
    
    # Apply limit if specified
    if limit:
        player_scores = player_scores[:limit]
    
    return player_scores


def process_player_data_for_display(
    bootstrap_static: Dict[str, Any],
    player_summaries: Optional[Dict[int, Dict[str, Any]]] = None,
    selected_teams: Optional[List[int]] = None
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Process and organize player data by position for display.
    
    Args:
        bootstrap_static: Bootstrap static data
        player_summaries: Optional dict of player_id -> player summary data
        selected_teams: Optional list of team IDs to filter by
        
    Returns:
        Dictionary with keys 'goalkeepers', 'defenders', 'midfielders', 'forwards'
    """
    # Get top players for each position
    goalkeepers = get_top_players_by_position(bootstrap_static, player_summaries, position_id=1, limit=5)
    defenders = get_top_players_by_position(bootstrap_static, player_summaries, position_id=2, limit=20)
    midfielders = get_top_players_by_position(bootstrap_static, player_summaries, position_id=3, limit=20)
    forwards = get_top_players_by_position(bootstrap_static, player_summaries, position_id=4, limit=10)
    
    # Filter by selected teams if provided
    if selected_teams:
        goalkeepers = [p for p in goalkeepers if p['team_id'] in selected_teams]
        defenders = [p for p in defenders if p['team_id'] in selected_teams]
        midfielders = [p for p in midfielders if p['team_id'] in selected_teams]
        forwards = [p for p in forwards if p['team_id'] in selected_teams]
    
    return {
        'goalkeepers': goalkeepers,
        'defenders': defenders,
        'midfielders': midfielders,
        'forwards': forwards
    }

