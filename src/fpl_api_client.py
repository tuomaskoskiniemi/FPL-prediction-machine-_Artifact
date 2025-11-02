"""
Fantasy Premier League API Client

This module provides functionality to fetch data from the Fantasy Premier League API.
It retrieves match, player, and team data, and documents all available endpoints.
"""

import requests
import json
from typing import Dict, List, Any, Optional
from datetime import datetime


class FPLAPIClient:
    """Client for interacting with the Fantasy Premier League API."""
    
    BASE_URL = "https://fantasy.premierleague.com/api"
    
    def __init__(self):
        """Initialize the FPL API client."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'FPL-Prediction-Machine/1.0'
        })
    
    def fetch_bootstrap_static(self) -> Dict[str, Any]:
        """
        Fetch bootstrap-static data containing all static game data.
        
        Returns:
            Dictionary containing events, game_settings, phases, teams, total_players,
            elements (players), element_stats, element_types (positions), and more.
        """
        url = f"{self.BASE_URL}/bootstrap-static/"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()
    
    def fetch_bootstrap_dynamic(self) -> Optional[Dict[str, Any]]:
        """
        Fetch bootstrap-dynamic data containing dynamic game data.
        
        Returns:
            Dictionary containing fixtures, events, and other dynamic data.
            Returns None if endpoint is not available.
        """
        url = f"{self.BASE_URL}/bootstrap-dynamic/"
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError:
            # Endpoint may not be available
            return None
    
    def fetch_fixtures(self, event_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Fetch fixture data.
        
        Args:
            event_id: Optional gameweek/event ID to filter fixtures.
            
        Returns:
            List of fixture dictionaries.
        """
        url = f"{self.BASE_URL}/fixtures/"
        if event_id:
            url += f"?event={event_id}"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()
    
    def fetch_player_detail(self, player_id: int) -> Dict[str, Any]:
        """
        Fetch detailed information for a specific player.
        
        Args:
            player_id: The ID of the player.
            
        Returns:
            Dictionary containing detailed player information.
        """
        url = f"{self.BASE_URL}/element-summary/{player_id}/"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()
    
    def fetch_team_detail(self, team_id: int) -> Dict[str, Any]:
        """
        Fetch detailed information for a specific team.
        
        Args:
            team_id: The ID of the team.
            
        Returns:
            Dictionary containing detailed team information.
        """
        url = f"{self.BASE_URL}/entry/{team_id}/"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()
    
    def fetch_event_detail(self, event_id: int) -> Dict[str, Any]:
        """
        Fetch detailed information for a specific gameweek/event.
        
        Args:
            event_id: The ID of the gameweek/event.
            
        Returns:
            Dictionary containing detailed event information.
        """
        url = f"{self.BASE_URL}/event/{event_id}/live/"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()
    
    def fetch_all_data(self) -> Dict[str, Any]:
        """
        Fetch all available data from the FPL API.
        
        Returns:
            Dictionary containing all fetched data organized by type.
        """
        print("Fetching bootstrap-static data...")
        bootstrap_static = self.fetch_bootstrap_static()
        
        print("Fetching bootstrap-dynamic data...")
        bootstrap_dynamic = self.fetch_bootstrap_dynamic()
        if bootstrap_dynamic is None:
            print("  (bootstrap-dynamic endpoint not available, skipping)")
        
        print("Fetching all fixtures...")
        fixtures = self.fetch_fixtures()
        
        result = {
            'bootstrap_static': bootstrap_static,
            'fixtures': fixtures,
            'fetched_at': datetime.now().isoformat()
        }
        
        if bootstrap_dynamic:
            result['bootstrap_dynamic'] = bootstrap_dynamic
        
        return result
    
    def analyze_and_document_api(self) -> Dict[str, Any]:
        """
        Analyze the FPL API structure and document all available data.
        
        Returns:
            Dictionary containing analysis and documentation of API structure.
        """
        print("Analyzing FPL API structure...")
        
        bootstrap_static = self.fetch_bootstrap_static()
        bootstrap_dynamic = self.fetch_bootstrap_dynamic()
        fixtures = self.fetch_fixtures()
        
        documentation = {
            'api_base_url': self.BASE_URL,
            'analysis_date': datetime.now().isoformat(),
            'available_endpoints': {
                'bootstrap_static': {
                    'url': f"{self.BASE_URL}/bootstrap-static/",
                    'description': 'Contains all static game data including players, teams, events, etc.',
                    'data_structure': {}
                },
                'bootstrap_dynamic': {
                    'url': f"{self.BASE_URL}/bootstrap-dynamic/",
                    'description': 'Contains dynamic game data including fixtures and events',
                    'data_structure': {}
                },
                'fixtures': {
                    'url': f"{self.BASE_URL}/fixtures/",
                    'description': 'Contains all fixture/match data',
                    'data_structure': {}
                },
                'player_detail': {
                    'url': f"{self.BASE_URL}/element-summary/<player_id>/",
                    'description': 'Detailed information for a specific player',
                    'data_structure': {}
                },
                'team_detail': {
                    'url': f"{self.BASE_URL}/entry/<team_id>/",
                    'description': 'Detailed information for a specific team',
                    'data_structure': {}
                },
                'event_detail': {
                    'url': f"{self.BASE_URL}/event/<event_id>/live/",
                    'description': 'Live data for a specific gameweek/event',
                    'data_structure': {}
                }
            },
            'data_summary': {}
        }
        
        # Analyze bootstrap-static structure
        if bootstrap_static:
            documentation['available_endpoints']['bootstrap_static']['data_structure'] = {
                'top_level_keys': list(bootstrap_static.keys()),
                'sample_sizes': {}
            }
            
            for key, value in bootstrap_static.items():
                if isinstance(value, list) and len(value) > 0:
                    documentation['available_endpoints']['bootstrap_static']['data_structure']['sample_sizes'][key] = len(value)
                    if isinstance(value[0], dict):
                        documentation['available_endpoints']['bootstrap_static']['data_structure'][f'{key}_fields'] = list(value[0].keys())
                elif isinstance(value, dict):
                    documentation['available_endpoints']['bootstrap_static']['data_structure'][f'{key}_fields'] = list(value.keys())
            
            # Extract specific data summaries
            documentation['data_summary']['players'] = {
                'count': len(bootstrap_static.get('elements', [])),
                'sample_fields': list(bootstrap_static.get('elements', [{}])[0].keys()) if bootstrap_static.get('elements') else []
            }
            
            documentation['data_summary']['teams'] = {
                'count': len(bootstrap_static.get('teams', [])),
                'sample_fields': list(bootstrap_static.get('teams', [{}])[0].keys()) if bootstrap_static.get('teams') else []
            }
            
            documentation['data_summary']['events'] = {
                'count': len(bootstrap_static.get('events', [])),
                'sample_fields': list(bootstrap_static.get('events', [{}])[0].keys()) if bootstrap_static.get('events') else []
            }
            
            documentation['data_summary']['fixtures'] = {
                'count': len(bootstrap_static.get('fixtures', [])),
                'sample_fields': list(bootstrap_static.get('fixtures', [{}])[0].keys()) if bootstrap_static.get('fixtures') else []
            }
        
        # Analyze bootstrap-dynamic structure
        if bootstrap_dynamic:
            documentation['available_endpoints']['bootstrap_dynamic']['data_structure'] = {
                'top_level_keys': list(bootstrap_dynamic.keys()),
                'sample_sizes': {}
            }
            
            for key, value in bootstrap_dynamic.items():
                if isinstance(value, list) and len(value) > 0:
                    documentation['available_endpoints']['bootstrap_dynamic']['data_structure']['sample_sizes'][key] = len(value)
        else:
            documentation['available_endpoints']['bootstrap_dynamic']['note'] = 'Endpoint not available or returns 404'
        
        # Analyze fixtures structure
        if fixtures and len(fixtures) > 0:
            documentation['available_endpoints']['fixtures']['data_structure'] = {
                'total_count': len(fixtures),
                'sample_fields': list(fixtures[0].keys())
            }
        
        return documentation


def main():
    """Main function to fetch and document FPL API data."""
    print("=" * 80)
    print("FPL API Data Fetcher and Documentation Tool")
    print("=" * 80)
    print()
    
    client = FPLAPIClient()
    
    try:
        # Analyze and document API structure
        documentation = client.analyze_and_document_api()
        
        # Save documentation
        doc_filename = 'fpl_api_documentation.json'
        with open(doc_filename, 'w', encoding='utf-8') as f:
            json.dump(documentation, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ API documentation saved to: {doc_filename}")
        
        # Fetch all data
        print("\n" + "=" * 80)
        print("Fetching all available data...")
        print("=" * 80)
        
        all_data = client.fetch_all_data()
        
        # Save all data
        data_filename = 'fpl_data_complete.json'
        with open(data_filename, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Complete data saved to: {data_filename}")
        
        # Print summary
        print("\n" + "=" * 80)
        print("Data Summary")
        print("=" * 80)
        print(f"\nPlayers: {documentation['data_summary']['players']['count']}")
        print(f"Teams: {documentation['data_summary']['teams']['count']}")
        print(f"Events (Gameweeks): {documentation['data_summary']['events']['count']}")
        print(f"Fixtures (Matches): {documentation['available_endpoints']['fixtures']['data_structure'].get('total_count', 0)}")
        
        print("\n" + "=" * 80)
        print("Player Data Fields (Sample):")
        print("=" * 80)
        player_fields = documentation['data_summary']['players'].get('sample_fields', [])
        for i, field in enumerate(player_fields[:20], 1):
            print(f"  {i}. {field}")
        if len(player_fields) > 20:
            print(f"  ... and {len(player_fields) - 20} more fields")
        
        print("\n" + "=" * 80)
        print("Team Data Fields (Sample):")
        print("=" * 80)
        team_fields = documentation['data_summary']['teams'].get('sample_fields', [])
        for i, field in enumerate(team_fields, 1):
            print(f"  {i}. {field}")
        
        print("\n" + "=" * 80)
        print("Fixture/Match Data Fields (Sample):")
        print("=" * 80)
        fixture_fields = documentation['available_endpoints']['fixtures']['data_structure'].get('sample_fields', [])
        for i, field in enumerate(fixture_fields, 1):
            print(f"  {i}. {field}")
        
        print("\n" + "=" * 80)
        print("✅ Data fetch and documentation complete!")
        print("=" * 80)
        
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Error fetching data from FPL API: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

