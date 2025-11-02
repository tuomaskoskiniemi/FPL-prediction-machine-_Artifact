## Relevant Files

- `src/data_processor.py` - Add functions for FDR calculations, points per game, and fixture filtering
- `app.py` - Add API endpoints for team analysis data
- `templates/team_analysis.html` - Team analysis page template with FDR displays and team selection
- `static/js/team_analysis.js` - JavaScript for team selection, localStorage, and dynamic updates
- `static/css/style.css` - Add styles for team analysis page, selection indicators, and FDR displays
- `templates/player_analysis.html` - Update to show full league table with selected team highlighting
- `static/js/player_analysis.js` - JavaScript for highlighting selected teams in league table
- `static/css/style.css` - Add styles for selected team highlighting

### Notes

- Use localStorage key `fpl_selected_teams` to store array of team IDs
- FDR calculations should use fixture difficulty ratings from FPL API (1-5 scale)
- Points per game = Total FPL points (3 for win, 1 for draw) / games played
- Selected teams should be shared between Team Analysis and Player Analysis pages via localStorage

## Tasks

- [x] 1.0 Add data processing functions for team analysis
  - [x] 1.1 Add function to get upcoming fixtures for a team (next N games)
  - [x] 1.2 Add function to calculate FDR average for upcoming fixtures (next 5 and 10)
  - [x] 1.3 Add function to calculate adjusted FDR (account for home/away and opponent strength)
  - [x] 1.4 Add function to get past fixtures for a team (last N games)
  - [x] 1.5 Add function to calculate points per game from past fixtures (last 5 and 10 games)
  - [x] 1.6 Add function to get all teams with their analysis data (FDR, performance metrics)
- [x] 2.0 Create API endpoint for team analysis data
  - [x] 2.1 Create /api/team-analysis endpoint that returns analysis data for all teams
  - [x] 2.2 Include next 5 and 10 games FDR (average and individual)
  - [x] 2.3 Include adjusted FDR for next 5 and 10 games
  - [x] 2.4 Include last 5 and 10 games points per game
  - [x] 2.5 Include upcoming fixture details (opponent, date, difficulty)
  - [x] 2.6 Handle edge cases (teams with less than 5/10 games played)
- [x] 3.0 Implement Team Analysis page frontend
  - [x] 3.1 Create HTML structure for team analysis display (grid or table)
  - [x] 3.2 Add sections for FDR metrics (next 5, next 10, adjusted versions)
  - [x] 3.3 Add sections for performance metrics (last 5, last 10 games PPG)
  - [x] 3.4 Add team selection checkboxes/toggle buttons
  - [x] 3.5 Create JavaScript to fetch and display team analysis data
  - [x] 3.6 Implement team selection handlers
  - [x] 3.7 Implement localStorage save/load for selected teams
  - [x] 3.8 Add visual indicators for selected teams
  - [x] 3.9 Display upcoming fixtures with opponent names and dates
- [x] 4.0 Style Team Analysis page
  - [x] 4.1 Style team analysis grid/table layout
  - [x] 4.2 Add color coding for FDR ratings (1-2 green, 3 yellow, 4-5 red)
  - [x] 4.3 Style selected team indicators
  - [x] 4.4 Add responsive design for mobile devices
  - [x] 4.5 Style performance metrics display
  - [x] 4.6 Add visual distinction for teams with favorable/unfavorable fixtures
- [x] 5.0 Update Player Analysis page with full league table
  - [x] 5.1 Ensure league table displays all required columns (Pos, Team, Played, W, D, L, GF, GA, GD, Points, Form)
  - [x] 5.2 Add form column with color-coded W/D/L badges (already exists, verify)
  - [x] 5.3 Create JavaScript to load selected teams from localStorage
  - [x] 5.4 Implement highlighting for selected teams in league table
  - [x] 5.5 Add visual indicator (icon, badge, or different styling) for selected teams
  - [x] 5.6 Ensure table remains responsive on mobile devices
- [x] 6.0 Test and verify functionality
  - [x] 6.1 Test FDR calculations for accuracy
  - [x] 6.2 Test points per game calculations
  - [x] 6.3 Test team selection and localStorage persistence
  - [x] 6.4 Test selected team highlighting across pages
  - [x] 6.5 Verify data accuracy against FPL API
  - [x] 6.6 Test edge cases (teams with incomplete game history)

