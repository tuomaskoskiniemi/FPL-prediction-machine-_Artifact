# PRD: Player Analysis Page Enhancement

## Introduction/Overview

This feature enhances the Player Analysis page to display best performing players for the last 5 games, organized by position (Goalkeepers, Defenders, Midfielders, Forwards). It includes filtering by selected teams from Team Analysis, player selection functionality, and integration with Best Formation and Draft List pages.

The goal is to help FPL managers identify top-performing players by position, focus on players from strategically selected teams, and build their draft team selections.

## Goals

1. Display top players by position for last 5 games performance
2. Show comprehensive player data from FPL API
3. Filter players by teams selected in Team Analysis page
4. Enable player selection for each position
5. Transfer selected players to Best Formation page (page 3)
6. Save all selected players to Draft List page (page 7)
7. Maintain league standings table with selected team highlighting

## User Stories

1. **As an FPL manager**, I want to see the best 5 goalkeepers, 20 defenders, 20 midfielders, and 10 forwards for the last 5 games, so that I can identify top performers by position.

2. **As an FPL manager**, I want to see all available player data from the FPL API, so that I can make informed decisions about player selection.

3. **As an FPL manager**, I want to filter players by teams I've selected in Team Analysis, so that I can focus on players from strategically important teams.

4. **As an FPL manager**, I want to select players for each position, so that I can build my proposed team lineup.

5. **As an FPL manager**, I want my selected players to be transferred to the Best Formation page, so that I can visualize my team formation.

6. **As an FPL manager**, I want my selected players to be saved to the Draft List, so that I can review and manage my player picks.

## Functional Requirements

### Player Display by Position

1. The system must display top players organized by position:
   - **Goalkeepers**: Top 5 players
   - **Defenders**: Top 20 players
   - **Midfielders**: Top 20 players
   - **Forwards**: Top 10 players

2. The system must rank players based on total points from the last 5 games.

3. For each player, the system must display all available FPL API data fields including:
   - Identity: name, team, position, photo
   - Pricing: current price, price changes
   - Performance: total points, points per game, form, event points
   - Goals & Assists: goals scored, assists, minutes
   - Goalkeeper stats: clean sheets, saves, goals conceded (for GKs)
   - Defender stats: clean sheets, goals conceded (for DEF)
   - Advanced stats: ICT index, influence, creativity, threat
   - Expected stats: xG, xA, xGI, xGC
   - Availability: status, chance of playing, news
   - Selection: selected_by_percent, transfers in/out
   - Disciplinary: yellow cards, red cards

4. The system must organize player data in clear, readable tables or cards with sortable columns.

### Team Filtering

5. The system must provide a filter option to show only players from teams selected in Team Analysis page.

6. The system must load selected teams from localStorage (key: `fpl_selected_teams`).

7. The system must display a toggle or button to enable/disable the team filter.

8. When filtered, the system must show only players whose team_id matches selected teams.

9. The system must indicate when filtering is active with a visual indicator.

### Player Selection

10. The system must allow users to select players using checkboxes or selection buttons.

11. The system must track selected players organized by position.

12. The system must display selected players count per position.

13. The system must allow deselecting players.

14. The system must highlight selected players visually (e.g., different background, border).

15. The system must enforce position limits:
    - Goalkeepers: Maximum 2 selections (FPL squad limit)
    - Defenders: Maximum 5 selections
    - Midfielders: Maximum 5 selections
    - Forwards: Maximum 3 selections

### Data Transfer and Storage

16. The system must save selected players to localStorage for Best Formation page (key: `fpl_selected_players`).

17. The system must save selected players to localStorage for Draft List page (key: `fpl_draft_list`).

18. The system must store player data in a structured format including:
    - Player ID
    - Player name
    - Position
    - Team
    - Price
    - Key statistics

19. The system must update storage immediately when players are selected/deselected.

20. The system must load saved selections when the page loads.

### League Standings Integration

21. The system must maintain the existing league standings table.

22. The system must continue to highlight selected teams in the league table.

23. The system must display the league table alongside the player analysis sections.

## Non-Goals (Out of Scope)

1. Historical performance comparison beyond last 5 games
2. Player comparison charts or graphs
3. Advanced filtering beyond team selection
4. Sorting by custom metrics beyond default (total points last 5 games)
5. Player detail modals or popups
6. Price trend visualization
7. Expected points projections beyond API data
8. Multiple draft list versions
9. Sharing selections with other users
10. Export functionality for player lists

## Design Considerations

1. **Page Layout:**
   - Section for each position (GK, DEF, MID, FWD)
   - Team filter toggle/button at top of page
   - Selected players summary section
   - League standings table (existing)
   - Clear visual separation between sections

2. **Player Tables:**
   - Sortable columns for key metrics
   - Responsive table design
   - Checkbox column for selection
   - Visual highlight for selected players
   - Team badge/logo display
   - Price display with formatting (£X.Xm)

3. **Filtering UI:**
   - Prominent filter button/toggle
   - Visual indicator when filter is active
   - Count of filtered players
   - Clear indication of selected teams being filtered

4. **Selection UI:**
   - Checkboxes aligned with each player row
   - Selection count per position
   - Total selected players counter
   - Visual feedback on selection
   - Disable checkbox when position limit reached

5. **Data Display:**
   - Prioritize most relevant stats (points, goals, assists, price)
   - Show advanced stats in expandable sections if needed
   - Color code availability status
   - Display team name with team color/badge

## Technical Considerations

1. **Data Source:**
   - Use FPL API `/bootstrap-static/` endpoint for player data
   - Use `/element-summary/{player_id}/` for detailed historical gameweek data
   - Calculate last 5 games points from historical gameweek data

2. **Last 5 Games Calculation:**
   - Fetch player summary data for each player
   - Extract gameweek points from `history` array
   - Sort by gameweek ID descending
   - Sum points from last 5 finished gameweeks
   - Handle cases where player hasn't played 5 games

3. **Player Ranking:**
   - Primary sort: Total points last 5 games (descending)
   - Secondary sort: Points per game (descending)
   - Tertiary sort: Total season points (descending)

4. **Storage Structure:**
   ```javascript
   {
     goalkeepers: [player_id1, player_id2, ...],
     defenders: [player_id1, player_id2, ...],
     midfielders: [player_id1, player_id2, ...],
     forwards: [player_id1, player_id2, ...]
   }
   ```

5. **API Endpoints:**
   - Create `/api/players/top-by-position` endpoint
   - Create `/api/players/last-5-games` endpoint
   - Extend existing `/api/league-table` endpoint

6. **Performance:**
   - Cache player summary data to avoid excessive API calls
   - Fetch player summaries in batches
   - Use client-side filtering for team selection
   - Lazy load player details if needed

7. **Data Processing:**
   - Add functions to `src/data_processor.py` for:
     - Calculating last 5 games points
     - Filtering players by position
     - Filtering players by team
     - Ranking players by performance

## Success Metrics

1. All player positions display with correct top players (5 GK, 20 DEF, 20 MID, 10 FWD)
2. Player data from FPL API displays accurately
3. Team filtering works correctly and shows only players from selected teams
4. Player selection works with position limits enforced
5. Selected players are saved to localStorage correctly
6. Selected players transfer to Best Formation page
7. Selected players appear in Draft List page
8. League standings table continues to function correctly
9. Page loads and updates within acceptable time (<5 seconds for initial load)

## Open Questions

1. Should we show only players who have played in at least 3 of the last 5 games, or include all players?
2. Should we allow sorting by different metrics (price, form, total points, etc.)?
3. Should player selection limits match FPL squad limits (15 players) or starting XI limits?
4. Should we show player photos in the tables or just names?
5. Should we display all player data fields or only the most important ones in the main view?
6. How should we handle players who have transferred teams during the season?

