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
    format_fixture_data
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
    return render_template('index.html')


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

