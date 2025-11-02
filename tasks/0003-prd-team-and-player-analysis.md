# PRD: Team Analysis and Player Analysis Features

## Introduction/Overview

This feature will implement comprehensive functionality for the Team Analysis and Player Analysis pages. The Team Analysis page will display fixture difficulty ratings (FDR), team performance metrics, and allow users to select teams for player picking. The Player Analysis page will show a detailed league standings table with all statistics and highlight the teams selected in Team Analysis.

The goal is to provide FPL managers with data-driven insights for team selection and player analysis, making it easier to identify favorable fixtures and track team performance.

## Goals

1. Display next 5 and 10 games FDR (Fixture Difficulty Rating) for all teams
2. Display adjusted FDR calculations for upcoming fixtures
3. Calculate and display team performance metrics for last 5 and 10 games (total points per game)
4. Allow users to select/pick teams for player selection strategy
5. Persist selected teams across sessions (localStorage)
6. Display full league standings table with comprehensive statistics on Player Analysis page
7. Highlight selected teams in the league standings table

## User Stories

1. **As an FPL manager**, I want to see the next 5 and 10 games FDR for all teams, so that I can identify teams with favorable upcoming fixtures.

2. **As an FPL manager**, I want to see adjusted FDR values, so that I can get a more nuanced view of fixture difficulty beyond the standard ratings.

3. **As an FPL manager**, I want to see team performance in the last 5 and 10 games (points per game), so that I can identify teams in good form.

4. **As an FPL manager**, I want to select teams that I plan to pick players from, so that I can focus my player analysis on relevant teams.

5. **As an FPL manager**, I want my team selections to be saved, so that they persist when I navigate between pages.

6. **As an FPL manager**, I want to see a detailed league standings table with all statistics, so that I can make informed decisions about team strength.

7. **As an FPL manager**, I want to see which teams I've selected highlighted in the league table, so that I can easily reference my strategy while analyzing players.

## Functional Requirements

### Team Analysis Page

1. The system must display a table or grid showing all 20 Premier League teams.

2. For each team, the system must display:
   - Next 5 games FDR (average and individual fixture ratings)
   - Next 10 games FDR (average and individual fixture ratings)
   - Adjusted FDR for next 5 games (calculated with team form/strength adjustments)
   - Adjusted FDR for next 10 games
   - Last 5 games total points per game (calculated from actual FPL points)
   - Last 10 games total points per game (calculated from actual FPL points)

3. The system must allow users to select/deselect teams using checkboxes or toggle buttons.

4. The system must save selected teams to browser localStorage.

5. The system must display a visual indicator (e.g., checkmark, highlight) for selected teams.

6. The system must load saved team selections when the page loads.

7. The system must update the display when teams are selected/deselected.

8. The system must calculate FDR averages correctly (sum of difficulty ratings / number of fixtures).

9. The system must fetch fixture data from the FPL API to determine upcoming games.

10. The system must calculate points per game from historical fixture data.

### Player Analysis Page

11. The system must display a comprehensive league standings table with all columns:
    - Position
    - Team name
    - Played (matches)
    - Won
    - Drawn
    - Lost
    - Goals For (GF)
    - Goals Against (GA)
    - Goal Difference (GD)
    - Points
    - Form (last 5 games: W/D/L format)

12. The system must highlight selected teams (from Team Analysis) in the league table with visual distinction (different background color, border, or icon).

13. The system must load team selections from localStorage when the page loads.

14. The system must display form data with color-coded indicators (green for W, yellow for D, red for L).

15. The system must ensure all data is accurate and matches FPL API data.

## Non-Goals (Out of Scope)

1. Advanced FDR calculation algorithms beyond basic adjustments
2. Historical FDR comparison or trends
3. Team comparison charts or graphs (can be added later)
4. Export functionality for selected teams
5. Multiple team selection strategies (single selection set only)
6. Team selection sharing between users
7. Advanced filtering or sorting beyond default table sorting
8. Player recommendations based on team selections (separate feature)

## Design Considerations

1. **Team Analysis Layout:**
   - Grid or table layout showing all teams
   - Clear sections for FDR metrics (next 5, next 10, adjusted versions)
   - Performance metrics section (last 5, last 10 games)
   - Prominent selection controls (checkboxes or toggle buttons)
   - Selected teams should be visually distinct

2. **FDR Display:**
   - Show individual fixture ratings (1-5 scale) with color coding
   - Display averages prominently
   - Include opponent team names for upcoming fixtures
   - Date/time information for fixtures

3. **Performance Metrics:**
   - Clear labeling of "Points Per Game" calculations
   - Visual indicators for strong/weak form
   - Comparison with league average if helpful

4. **Player Analysis Table:**
   - Full table with all required columns
   - Highlight selected teams with different background color
   - Maintain existing table styling and responsiveness
   - Form column with color-coded badges

5. **Visual Indicators:**
   - Selected teams: border, background highlight, or checkmark icon
   - FDR ratings: color-coded (green=easy, yellow=medium, red=hard)
   - Form: color-coded W/D/L badges

## Technical Considerations

1. **Data Sources:**
   - Use existing FPL API client to fetch fixture data
   - Use bootstrap-static for team data and fixtures
   - Calculate points per game from finished fixtures
   - Determine upcoming fixtures from current gameweek

2. **FDR Calculation:**
   - FDR = Fixture Difficulty Rating (1-5 scale from FPL API)
   - Adjusted FDR = Account for home/away and opponent strength
   - Average FDR = Sum of ratings / number of fixtures

3. **Points Per Game Calculation:**
   - Extract finished fixtures for each team
   - Calculate FPL points (3 for win, 1 for draw, 0 for loss)
   - Divide by number of games played
   - Handle cases where teams haven't played enough games

4. **Storage:**
   - Use browser localStorage to persist selected teams
   - Key: `fpl_selected_teams`
   - Value: Array of team IDs
   - Update storage on selection change

5. **API Endpoints:**
   - Create `/api/team-analysis` endpoint to provide team analysis data
   - Create `/api/team-fixtures/<team_id>` for detailed fixture data if needed
   - Reuse existing `/api/league-table` endpoint or extend it

6. **Frontend:**
   - Create JavaScript functions to calculate FDR averages
   - Implement team selection handlers
   - Update display dynamically when selections change
   - Load and apply saved selections on page load

7. **Data Processing:**
   - Add functions to `src/data_processor.py` for:
     - Calculating FDR averages
     - Calculating adjusted FDR
     - Calculating points per game
     - Filtering upcoming fixtures
     - Filtering past fixtures

## Success Metrics

1. All 20 teams display with accurate FDR data for next 5 and 10 games
2. Adjusted FDR calculations are displayed correctly
3. Points per game metrics are accurate for last 5 and 10 games
4. Team selection works and persists across page navigations
5. Selected teams are highlighted correctly in Player Analysis table
6. League table displays all required columns accurately
7. Form data displays correctly with color coding
8. Page loads and updates data within acceptable time (<3 seconds)

## Open Questions

1. How should adjusted FDR be calculated? (Simple home/away multiplier, or more complex algorithm?)
2. Should we show individual fixture details in expandable rows, or just summaries?
3. Should selected teams be highlighted with a specific color or just with a checkmark/badge?
4. Do we need to support deselecting all teams, or should at least one always be selected?
5. Should team selections be shared with other pages (Best Formation, Propose Players, etc.)?
6. How should we handle teams that haven't played 5 or 10 games yet?

