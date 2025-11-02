"""
Database models and operations for FPL Prediction Machine.
Uses SQLite for storing user draft lists.
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
import os

# Database file path
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fpl_draft_lists.db')


def get_db_connection():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Initialize database with required tables."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create draft_lists table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS draft_lists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fpl_team_id INTEGER NOT NULL,
            draft_list_data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(fpl_team_id)
        )
    ''')
    
    # Create index on fpl_team_id for faster lookups
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_fpl_team_id 
        ON draft_lists(fpl_team_id)
    ''')
    
    conn.commit()
    conn.close()


def save_draft_list(fpl_team_id: int, draft_list_data: Dict[str, List[int]]) -> bool:
    """
    Save or update draft list for a given FPL team ID.
    
    Args:
        fpl_team_id: The FPL team ID
        draft_list_data: Dictionary with keys 'goalkeepers', 'defenders', 'midfielders', 'forwards'
                        containing lists of player IDs
        
    Returns:
        True if successful, False otherwise
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Convert draft list to JSON string
        draft_list_json = json.dumps(draft_list_data)
        
        # Check if record exists
        cursor.execute('SELECT id FROM draft_lists WHERE fpl_team_id = ?', (fpl_team_id,))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing record
            cursor.execute('''
                UPDATE draft_lists 
                SET draft_list_data = ?, updated_at = CURRENT_TIMESTAMP
                WHERE fpl_team_id = ?
            ''', (draft_list_json, fpl_team_id))
        else:
            # Insert new record
            cursor.execute('''
                INSERT INTO draft_lists (fpl_team_id, draft_list_data, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (fpl_team_id, draft_list_json))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving draft list: {e}")
        return False


def load_draft_list(fpl_team_id: int) -> Optional[Dict[str, List[int]]]:
    """
    Load draft list for a given FPL team ID.
    
    Args:
        fpl_team_id: The FPL team ID
        
    Returns:
        Dictionary with draft list data or None if not found
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT draft_list_data, updated_at 
            FROM draft_lists 
            WHERE fpl_team_id = ?
        ''', (fpl_team_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return json.loads(result['draft_list_data'])
        return None
    except Exception as e:
        print(f"Error loading draft list: {e}")
        return None


def delete_draft_list(fpl_team_id: int) -> bool:
    """
    Delete draft list for a given FPL team ID.
    
    Args:
        fpl_team_id: The FPL team ID
        
    Returns:
        True if successful, False otherwise
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM draft_lists WHERE fpl_team_id = ?', (fpl_team_id,))
        
        conn.commit()
        conn.close()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Error deleting draft list: {e}")
        return False


def get_all_draft_lists() -> List[Dict[str, Any]]:
    """
    Get all draft lists with metadata.
    
    Returns:
        List of dictionaries containing draft list information
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT fpl_team_id, updated_at, 
                   (SELECT COUNT(*) FROM json_each(draft_list_data)) as player_count
            FROM draft_lists
            ORDER BY updated_at DESC
        ''')
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'fpl_team_id': row['fpl_team_id'],
                'updated_at': row['updated_at'],
                'player_count': row['player_count']
            })
        
        conn.close()
        return results
    except Exception as e:
        print(f"Error getting all draft lists: {e}")
        return []


# Initialize database on import
init_database()

