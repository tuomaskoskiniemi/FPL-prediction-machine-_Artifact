"""
Flask application for FPL Prediction Machine frontend.

Serves the main page and provides API endpoints for fetching FPL data.
"""

from flask import Flask, render_template, jsonify
from flask_cors import CORS
import time
from src.fpl_api_client import FPLAPIClient
from src.data_processor import (
    get_current_gameweek,
    get_current_gameweek_fixtures,
    process_league_table,
    format_fixture_data,
    get_all_teams_analysis,
    process_player_data_for_display
)

app = Flask(__name__)
CORS(app)

# Cache for API data to avoid excessive calls
_data_cache = {
    'bootstrap_static': None,
    'fixtures': None,
    'last_update': None
}

# Cache timeout (5 minutes)
CACHE_TIMEOUT = 300


@app.route('/')
def index():
    """Serve the main page."""
    return render_template('index.html', current_page='home')


@app.route('/team-analysis')
def team_analysis():
    """Serve the team analysis page."""
    return render_template('team_analysis.html', current_page='team-analysis')


@app.route('/player-analysis')
def player_analysis():
    """Serve the player analysis page."""
    return render_template('player_analysis.html', current_page='player-analysis')


@app.route('/best-formation')
def best_formation():
    """Serve the best formation page."""
    return render_template('best_formation.html', current_page='best-formation')


@app.route('/propose-players')
def propose_players():
    """Serve the propose players page."""
    return render_template('propose_players.html', current_page='propose-players')


@app.route('/current-team')
def current_team():
    """Serve the current team page."""
    return render_template('current_team.html', current_page='current-team')


@app.route('/transfers')
def transfers():
    """Serve the transfers page."""
    return render_template('transfers.html', current_page='transfers')


@app.route('/draft-list')
def draft_list():
    """Serve the draft list page."""
    return render_template('draft_list.html', current_page='draft-list')


@app.route('/adjustments')
def adjustments():
    """Serve the adjustments page."""
    return render_template('adjustments.html', current_page='adjustments')


@app.route('/api/update', methods=['POST'])
def update_data():
    """
    Trigger FPL API data fetch and update cache.
    Returns JSON response indicating success or failure.
    """
    try:
        client = FPLAPIClient()
        data = client.fetch_all_data()
        
        # Update cache
        _data_cache['bootstrap_static'] = data.get('bootstrap_static')
        _data_cache['fixtures'] = data.get('fixtures')
        _data_cache['last_update'] = time.time()
        
        return jsonify({
            'success': True,
            'message': 'Data updated successfully',
            'timestamp': _data_cache['last_update']
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error updating data: {str(e)}'
        }), 500


@app.route('/api/current-gameweek', methods=['GET'])
def current_gameweek():
    """
    Return current gameweek fixtures data.
    Automatically fetches data if cache is empty or stale.
    """
    try:
        # Check if cache needs refresh
        if (_data_cache['bootstrap_static'] is None or 
            _data_cache['fixtures'] is None or
            _should_refresh_cache()):
            client = FPLAPIClient()
            data = client.fetch_all_data()
            _data_cache['bootstrap_static'] = data.get('bootstrap_static')
            _data_cache['fixtures'] = data.get('fixtures')
        
        bootstrap_static = _data_cache['bootstrap_static']
        fixtures = _data_cache['fixtures']
        
        current_gw = get_current_gameweek(bootstrap_static)
        gw_fixtures = get_current_gameweek_fixtures(fixtures, bootstrap_static, current_gw)
        
        formatted_fixtures = format_fixture_data(gw_fixtures, bootstrap_static)
        
        return jsonify({
            'success': True,
            'current_gameweek': current_gw,
            'fixtures': formatted_fixtures
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching gameweek data: {str(e)}'
        }), 500


@app.route('/api/team-analysis', methods=['GET'])
def team_analysis_api():
    """
    Return team analysis data for all teams including FDR and performance metrics.
    """
    try:
        # Check if cache needs refresh
        if (_data_cache['bootstrap_static'] is None or
            _data_cache['fixtures'] is None or
            _should_refresh_cache()):
            client = FPLAPIClient()
            data = client.fetch_all_data()
            _data_cache['bootstrap_static'] = data.get('bootstrap_static')
            _data_cache['fixtures'] = data.get('fixtures')
        
        bootstrap_static = _data_cache['bootstrap_static']
        fixtures = _data_cache.get('fixtures', [])
        
        teams_analysis = get_all_teams_analysis(fixtures, bootstrap_static)
        
        return jsonify({
            'success': True,
            'teams': teams_analysis
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching team analysis data: {str(e)}'
        }), 500


@app.route('/api/players/top-by-position', methods=['GET'])
def top_players_api():
    """API endpoint to get top players by position."""
    from flask import request
    
    try:
        # Check cache
        if (_data_cache['bootstrap_static'] is None or
            _should_refresh_cache()):
            client = FPLAPIClient()
            data = client.fetch_all_data()
            _data_cache['bootstrap_static'] = data.get('bootstrap_static')
            _data_cache['fixtures'] = data.get('fixtures')
        
        bootstrap_static = _data_cache['bootstrap_static']
        
        # Get selected teams from query parameter (optional)
        selected_teams_param = request.args.get('selected_teams')
        selected_teams = None
        if selected_teams_param:
            try:
                selected_teams = [int(t) for t in selected_teams_param.split(',')]
            except ValueError:
                selected_teams = None
        
        # Process player data
        players_by_position = process_player_data_for_display(
            bootstrap_static,
            player_summaries=None,  # Will use form as fallback
            selected_teams=selected_teams
        )
        
        return jsonify({
            'success': True,
            'players': players_by_position
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching player data: {str(e)}'
        }), 500


@app.route('/api/players/all', methods=['GET'])
def all_players_api():
    """API endpoint to get all players with their statistics."""
    from src.data_processor import get_top_players_by_position
    
    try:
        # Check cache
        if (_data_cache['bootstrap_static'] is None or
            _should_refresh_cache()):
            client = FPLAPIClient()
            data = client.fetch_all_data()
            _data_cache['bootstrap_static'] = data.get('bootstrap_static')
            _data_cache['fixtures'] = data.get('fixtures')
        
        bootstrap_static = _data_cache['bootstrap_static']
        
        # Get all players (no limit)
        goalkeepers = get_top_players_by_position(bootstrap_static, player_summaries=None, position_id=1, limit=None)
        defenders = get_top_players_by_position(bootstrap_static, player_summaries=None, position_id=2, limit=None)
        midfielders = get_top_players_by_position(bootstrap_static, player_summaries=None, position_id=3, limit=None)
        forwards = get_top_players_by_position(bootstrap_static, player_summaries=None, position_id=4, limit=None)
        
        # Combine all players into a single list
        all_players = goalkeepers + defenders + midfielders + forwards
        
        return jsonify({
            'success': True,
            'players': all_players,
            'players_by_position': {
                'goalkeepers': goalkeepers,
                'defenders': defenders,
                'midfielders': midfielders,
                'forwards': forwards
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching player data: {str(e)}'
        }), 500


@app.route('/api/league-table', methods=['GET'])
def league_table():
    """
    Return full Premier League table data.
    Automatically fetches data if cache is empty or stale.
    """
    try:
        # Check if cache needs refresh
        if (_data_cache['bootstrap_static'] is None or
            _should_refresh_cache()):
            client = FPLAPIClient()
            data = client.fetch_all_data()
            _data_cache['bootstrap_static'] = data.get('bootstrap_static')
            _data_cache['fixtures'] = data.get('fixtures')
        
        bootstrap_static = _data_cache['bootstrap_static']
        fixtures = _data_cache.get('fixtures', [])
        table = process_league_table(bootstrap_static, fixtures)
        
        return jsonify({
            'success': True,
            'table': table
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching league table: {str(e)}'
        }), 500


@app.route('/api/team/<int:team_id>', methods=['GET'])
def get_team_data(team_id):
    """
    Fetch FPL team data for a given team ID.
    Returns team information including picks, transfers, and player data.
    """
    from flask import request
    import requests
    
    try:
        client = FPLAPIClient()
        
        # Get bootstrap static for player information
        if (_data_cache['bootstrap_static'] is None or _should_refresh_cache()):
            data = client.fetch_all_data()
            _data_cache['bootstrap_static'] = data.get('bootstrap_static')
            _data_cache['fixtures'] = data.get('fixtures')
        
        bootstrap_static = _data_cache['bootstrap_static']
        
        # Get current gameweek
        current_gw = get_current_gameweek(bootstrap_static)
        
        # Fetch team detail from FPL API
        team_data = client.fetch_team_detail(team_id)
        
        # Try to get picks from current gameweek endpoint
        picks = []
        if current_gw:
            try:
                picks_url = f"{client.BASE_URL}/entry/{team_id}/event/{current_gw}/picks/"
                picks_response = client.session.get(picks_url)
                if picks_response.status_code == 200:
                    picks_data = picks_response.json()
                    picks = picks_data.get('picks', [])
            except:
                # Fallback to team_data picks if available
                picks = team_data.get('picks', [])
        else:
            # Fallback to team_data picks if current_gw not available
            picks = team_data.get('picks', [])
        
        # If still no picks, try to get from different structure
        if not picks:
            # Check if picks are in a different structure
            if 'current' in team_data and 'picks' in team_data['current']:
                picks = team_data['current']['picks']
            elif 'squad' in team_data:
                picks = team_data['squad']
        
        # Map player IDs to full player data
        players_map = {player['id']: player for player in bootstrap_static.get('elements', [])}
        teams_map = {team['id']: team for team in bootstrap_static.get('teams', [])}
        
        # Get position type mapping
        element_types = {et['id']: et for et in bootstrap_static.get('element_types', [])}
        
        # Enrich picks with player and team data
        enriched_picks = []
        for pick in picks:
            player_id = pick.get('element')
            player = players_map.get(player_id)
            if player:
                team_id_player = player.get('team')
                team = teams_map.get(team_id_player, {})
                
                # Get position type from element_type
                element_type_id = player.get('element_type')
                element_type = element_types.get(element_type_id, {})
                
                enriched_picks.append({
                    **pick,
                    'player': player,
                    'team': team,
                    'team_name': team.get('name', 'Unknown'),
                    'team_short_name': team.get('short_name', 'UNK'),
                    'element_type': element_type_id,  # Ensure element_type is included
                    'position_name': element_type.get('plural_name_short', 'FWD')
                })
        
        # Group by position - use element_type from player data
        positions_map = {1: 'goalkeepers', 2: 'defenders', 3: 'midfielders', 4: 'forwards'}
        picks_by_position = {
            'goalkeepers': [],
            'defenders': [],
            'midfielders': [],
            'forwards': []
        }
        
        for pick in enriched_picks:
            player = pick.get('player', {})
            position_id = player.get('element_type')
            if position_id is None:
                # Try to get from pick itself
                position_id = pick.get('element_type')
            
            position_key = positions_map.get(position_id, 'forwards')
            if position_key in picks_by_position:
                picks_by_position[position_key].append(pick)
        
        # Calculate team value
        total_value = sum((p.get('player', {}).get('now_cost', 0) for p in enriched_picks)) / 10.0
        
        # Get bank from team data (convert from tenths)
        bank_value = 0
        if 'last_deadline_bank' in team_data:
            bank_value = team_data['last_deadline_bank'] / 10.0
        elif 'bank' in team_data:
            bank_value = team_data['bank'] / 10.0 if isinstance(team_data['bank'], int) else team_data['bank']
        
        return jsonify({
            'success': True,
            'team': {
                'id': team_data.get('id'),
                'player_first_name': team_data.get('player_first_name', ''),
                'player_last_name': team_data.get('player_last_name', ''),
                'name': team_data.get('name', ''),
                'entry': team_data.get('entry'),
                'total_value': total_value,
                'bank': bank_value,
                'total_points': team_data.get('summary_overall_points', 0),
                'current_gameweek': current_gw
            },
            'picks': picks_by_position,
            'all_picks': enriched_picks
        }), 200
        
    except Exception as e:
        import traceback
        # Only include trace in debug mode
        error_trace = None
        if app.debug:
            error_trace = traceback.format_exc()
        
        response = {
            'success': False,
            'message': f'Error fetching team data: {str(e)}'
        }
        
        if error_trace:
            response['trace'] = error_trace
            
        return jsonify(response), 500


@app.route('/api/extract-team-id', methods=['POST'])
def extract_team_id():
    """
    Extract team ID from FPL team link/URL.
    Accepts team link in request body and returns team ID.
    """
    from flask import request
    
    try:
        data = request.get_json()
        team_link = data.get('team_link', '').strip()
        
        if not team_link:
            return jsonify({
                'success': False,
                'message': 'Team link is required'
            }), 400
        
        # Extract team ID from various FPL link formats
        import re
        
        # Pattern for FPL URLs like:
        # https://fantasy.premierleague.com/entry/{team_id}/event/{gameweek}
        # https://fantasy.premierleague.com/entry/{team_id}/
        # {team_id} (just the number)
        patterns = [
            r'/entry/(\d+)',
            r'^(\d+)$'
        ]
        
        team_id = None
        for pattern in patterns:
            match = re.search(pattern, team_link)
            if match:
                team_id = int(match.group(1))
                break
        
        if not team_id:
            return jsonify({
                'success': False,
                'message': 'Could not extract team ID from link. Please provide a valid FPL team link or team ID.'
            }), 400
        
        return jsonify({
            'success': True,
            'team_id': team_id
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error extracting team ID: {str(e)}'
        }), 500


@app.route('/api/draft-list/save', methods=['POST'])
def save_draft_list_api():
    """API endpoint to save draft list to database."""
    from flask import request
    from src.database import save_draft_list
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400
        
        fpl_team_id = data.get('fpl_team_id')
        draft_list_data = data.get('draft_list')
        
        if not fpl_team_id:
            return jsonify({
                'success': False,
                'message': 'FPL team ID is required'
            }), 400
        
        try:
            fpl_team_id = int(fpl_team_id)
        except (ValueError, TypeError):
            return jsonify({
                'success': False,
                'message': 'Invalid FPL team ID'
            }), 400
        
        if not draft_list_data:
            return jsonify({
                'success': False,
                'message': 'Draft list data is required'
            }), 400
        
        # Validate draft list structure
        required_keys = ['goalkeepers', 'defenders', 'midfielders', 'forwards']
        if not all(key in draft_list_data for key in required_keys):
            return jsonify({
                'success': False,
                'message': 'Invalid draft list format'
            }), 400
        
        # Save to database
        success = save_draft_list(fpl_team_id, draft_list_data)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Draft list saved successfully for team ID {fpl_team_id}'
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to save draft list'
            }), 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error saving draft list: {str(e)}'
        }), 500


@app.route('/api/draft-list/load', methods=['GET'])
def load_draft_list_api():
    """API endpoint to load draft list from database."""
    from flask import request
    from src.database import load_draft_list
    
    try:
        fpl_team_id = request.args.get('fpl_team_id')
        
        if not fpl_team_id:
            return jsonify({
                'success': False,
                'message': 'FPL team ID is required'
            }), 400
        
        try:
            fpl_team_id = int(fpl_team_id)
        except (ValueError, TypeError):
            return jsonify({
                'success': False,
                'message': 'Invalid FPL team ID'
            }), 400
        
        draft_list = load_draft_list(fpl_team_id)
        
        if draft_list:
            return jsonify({
                'success': True,
                'draft_list': draft_list,
                'message': f'Draft list loaded successfully for team ID {fpl_team_id}'
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': f'No draft list found for team ID {fpl_team_id}'
            }), 404
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error loading draft list: {str(e)}'
        }), 500


def _should_refresh_cache():
    """Check if cache should be refreshed based on timeout."""
    if _data_cache['last_update'] is None:
        return True
    
    import time
    elapsed = time.time() - _data_cache['last_update']
    return elapsed > CACHE_TIMEOUT


if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5001
    print(f"Starting FPL Prediction Machine on http://localhost:{port}")
    app.run(debug=True, host='0.0.0.0', port=port)

