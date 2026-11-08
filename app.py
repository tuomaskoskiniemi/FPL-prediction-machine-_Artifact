"""
Flask application for FPL Prediction Machine frontend.

Serves the main page and provides API endpoints for fetching FPL data.
"""

from flask import Flask, render_template, jsonify
from flask_cors import CORS
import time
from src.fpl_api_client import FPLAPIClient
from src.fpl_team import fetch_manager_team, FPLTeamError
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
    Fetch a manager's squad for a team id.

    The work is done by src.fpl_team.fetch_manager_team; this route adapts it to
    the shape the Current Team page has always consumed, and adds the richer
    structure under 'detail' for anything new.
    """
    try:
        client = FPLAPIClient()

        if (_data_cache['bootstrap_static'] is None or _should_refresh_cache()):
            data = client.fetch_all_data()
            _data_cache['bootstrap_static'] = data.get('bootstrap_static')
            _data_cache['fixtures'] = data.get('fixtures')
            _data_cache['last_update'] = time.time()

        bootstrap_static = _data_cache['bootstrap_static']
        fixtures = _data_cache.get('fixtures') or []

        detail = fetch_manager_team(team_id, client=client,
                                    bootstrap=bootstrap_static, fixtures=fixtures)

        # --- the shape static/js/current_team.js expects ------------------
        elements = {e['id']: e for e in bootstrap_static.get('elements', [])}
        clubs = {t['id']: t for t in bootstrap_static.get('teams', [])}
        element_types = {et['id']: et for et in bootstrap_static.get('element_types', [])}

        picks_by_position = {'goalkeepers': [], 'defenders': [],
                             'midfielders': [], 'forwards': []}
        enriched_picks = []
        for player in detail['all_players']:
            raw = elements.get(player['id'])
            if not raw:
                continue
            club = clubs.get(raw['team'], {})
            kind = element_types.get(raw['element_type'], {})
            pick = {
                'element': player['id'],
                'position': player['squad_position'],
                'multiplier': player['multiplier'],
                'is_captain': player['is_captain'],
                'is_vice_captain': player['is_vice_captain'],
                'element_type': raw['element_type'],
                'player': raw,
                'team': club,
                'team_name': club.get('name', 'Unknown'),
                'team_short_name': club.get('short_name', 'UNK'),
                'position_name': kind.get('plural_name_short', 'FWD'),
                # from the picking principles
                'flagged': player['flagged'],
                'mean_defence': player['mean_defence'],
                'on_bench': player['on_bench'],
            }
            enriched_picks.append(pick)
            key = {1: 'goalkeepers', 2: 'defenders',
                   3: 'midfielders', 4: 'forwards'}.get(raw['element_type'], 'forwards')
            picks_by_position[key].append(pick)

        entry = detail['entry']
        return jsonify({
            'success': True,
            'team': {
                'id': entry['id'],
                'player_first_name': entry['manager'].split(' ')[0] if entry['manager'] else '',
                'player_last_name': ' '.join(entry['manager'].split(' ')[1:]),
                'name': entry['team_name'],
                'entry': entry['id'],
                'total_value': detail['money']['squad_value'],
                'bank': detail['money']['bank'],
                'budget': detail['money']['budget'],
                'total_points': entry['overall_points'],
                'overall_rank': entry['overall_rank'],
                'current_gameweek': entry['gameweek'],
            },
            'picks': picks_by_position,
            'all_picks': enriched_picks,
            'detail': detail,
        }), 200

    except FPLTeamError as e:
        return jsonify({'success': False, 'message': str(e)}), 404
    except Exception as e:
        import traceback
        response = {'success': False, 'message': f'Error fetching team data: {str(e)}'}
        if app.debug:
            response['trace'] = traceback.format_exc()
        return jsonify(response), 500


@app.route('/api/my-team', methods=['POST'])
def my_team():
    """
    Fetch a manager's squad from a team link (or a bare id).

    Body: {"team_link": "https://fantasy.premierleague.com/entry/1234567/"}
    Optional: {"gameweek": 9}

    Returns the full structure from src.fpl_team.fetch_manager_team: entry
    details, money, the gameweek summary, the squad by position, the starting
    eleven, the bench, the captain and every flagged player.
    """
    from flask import request

    try:
        payload = request.get_json(silent=True) or {}
        team_link = payload.get('team_link') or payload.get('team_id')
        gameweek = payload.get('gameweek')

        client = FPLAPIClient()
        if (_data_cache['bootstrap_static'] is None or _should_refresh_cache()):
            data = client.fetch_all_data()
            _data_cache['bootstrap_static'] = data.get('bootstrap_static')
            _data_cache['fixtures'] = data.get('fixtures')
            _data_cache['last_update'] = time.time()

        detail = fetch_manager_team(
            team_link, gameweek=gameweek, client=client,
            bootstrap=_data_cache['bootstrap_static'],
            fixtures=_data_cache.get('fixtures') or [])

        return jsonify({'success': True, 'team': detail}), 200

    except FPLTeamError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False,
                        'message': f'Error fetching team: {str(e)}'}), 500


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

