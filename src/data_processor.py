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


def calculate_team_stats_from_fixtures(fixtures: List[Dict[str, Any]]) -> Dict[int, Dict[str, int]]:
    """
    Calculate Goals For (GF), Goals Against (GA), and Goal Difference (GD) from fixtures.
    
    Args:
        fixtures: List of all fixtures
        
    Returns:
        Dictionary mapping team_id to stats dict with 'goals_for', 'goals_against', 'goal_difference'
    """
    team_stats = {}
    
    for fixture in fixtures:
        if not fixture.get('finished', False):
            continue
        
        team_h_id = fixture.get('team_h')
        team_a_id = fixture.get('team_a')
        team_h_score = fixture.get('team_h_score', 0) or 0
        team_a_score = fixture.get('team_a_score', 0) or 0
        
        # Initialize team stats if not exists
        if team_h_id not in team_stats:
            team_stats[team_h_id] = {'goals_for': 0, 'goals_against': 0}
        if team_a_id not in team_stats:
            team_stats[team_a_id] = {'goals_for': 0, 'goals_against': 0}
        
        # Add goals
        team_stats[team_h_id]['goals_for'] += team_h_score
        team_stats[team_h_id]['goals_against'] += team_a_score
        team_stats[team_a_id]['goals_for'] += team_a_score
        team_stats[team_a_id]['goals_against'] += team_h_score
    
    # Calculate goal difference
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
    
    Args:
        bootstrap_static: The bootstrap-static API response
        fixtures: Optional list of fixtures to calculate GF/GA/GD
        
    Returns:
        List of teams sorted by position (points, then goal difference)
    """
    if not bootstrap_static or 'teams' not in bootstrap_static:
        return []
    
    teams = bootstrap_static['teams']
    
    # Calculate GF/GA/GD from fixtures if available
    fixture_stats = {}
    if fixtures:
        fixture_stats = calculate_team_stats_from_fixtures(fixtures)
    
    # Format for frontend
    table = []
    for team in teams:
        team_id = team.get('id')
        position = team.get('position', 99)
        
        # Get fixture stats if available
        stats = fixture_stats.get(team_id, {})
        
        table.append({
            'position': position,
            'id': team_id,
            'name': team.get('name'),
            'short_name': team.get('short_name'),
            'played': team.get('played', 0),
            'win': team.get('win', 0),
            'draw': team.get('draw', 0),
            'loss': team.get('loss', 0),
            'goals_for': stats.get('goals_for', 0),
            'goals_against': stats.get('goals_against', 0),
            'goal_difference': stats.get('goal_difference', 0),
            'points': team.get('points', 0),
            'form': team.get('form', ''),
            'strength_overall_home': team.get('strength_overall_home', 0),
            'strength_overall_away': team.get('strength_overall_away', 0),
        })
    
    # Re-sort by position to ensure correct order
    table.sort(key=lambda x: x['position'])
    
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

