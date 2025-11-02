## Relevant Files

- `app.py` - Flask application server that serves the frontend and provides API endpoints
- `src/fpl_api_client.py` - Existing FPL API client (already exists, may need minor modifications)
- `src/data_processor.py` - Utility functions to process FPL API data (get current gameweek, filter fixtures, process league table)
- `static/css/style.css` - Fantasy football themed CSS styles
- `static/js/main.js` - Frontend JavaScript for data fetching, UI updates, and animations
- `templates/index.html` - Main page HTML template
- `static/images/football-icon.svg` or `static/images/football-icon.png` - Football icon for rolling animation
- `tests/test_data_processor.py` - Unit tests for data processing utilities
- `tests/test_api_endpoints.py` - Unit tests for API endpoints

### Notes

- Unit tests should typically be placed alongside the code files they are testing
- Use `pytest` to run tests
- Flask will serve static files from `static/` directory and templates from `templates/` directory

## Tasks

- [x] 1.0 Set up Flask backend server and project structure
  - [x] 1.1 Install Flask and update requirements.txt
  - [x] 1.2 Create app.py with Flask application setup
  - [x] 1.3 Create static/ and templates/ directories
  - [x] 1.4 Set up basic route for serving main page
- [x] 2.0 Create data processing utilities
  - [x] 2.1 Create src/data_processor.py with functions to get current gameweek
  - [x] 2.2 Add function to filter fixtures for current gameweek
  - [x] 2.3 Add function to process and sort league table data
  - [x] 2.4 Add function to format match dates and times
  - [x] 2.5 Add function to determine match status (upcoming, live, finished)
  - [x] 2.6 Add function to get team form from team data
- [x] 3.0 Create API endpoints for frontend
  - [x] 3.1 Create /api/update endpoint that triggers FPL API data fetch
  - [x] 3.2 Create /api/current-gameweek endpoint that returns current gameweek fixtures
  - [x] 3.3 Create /api/league-table endpoint that returns sorted league table
  - [x] 3.4 Implement caching mechanism to avoid excessive API calls
  - [x] 3.5 Add error handling for API failures
- [x] 4.0 Create frontend HTML structure
  - [x] 4.1 Create templates/index.html with basic structure
  - [x] 4.2 Add header with site description
  - [x] 4.3 Add "This Round Games" section with placeholder content
  - [x] 4.4 Add "Premier League Table" section with table structure
  - [x] 4.5 Add update button and loading indicator area
- [x] 5.0 Create fantasy football themed CSS styling
  - [x] 5.1 Design color scheme with football pitch green and team colors
  - [x] 5.2 Style header, sections, and table with responsive design
  - [x] 5.3 Create card-based layout for fixtures
  - [x] 5.4 Style league table with clear formatting
  - [x] 5.5 Add responsive breakpoints for mobile, tablet, desktop
  - [x] 5.6 Create rolling football icon animation CSS
- [x] 6.0 Implement frontend JavaScript functionality
  - [x] 6.1 Create function to fetch and display current gameweek fixtures
  - [x] 6.2 Create function to fetch and display league table
  - [x] 6.3 Implement automatic data fetch on page load
  - [x] 6.4 Implement manual update button functionality
  - [x] 6.5 Add rolling football icon animation during data updates
  - [x] 6.6 Add error handling and user feedback for failed API calls
  - [x] 6.7 Format dates/times for display
  - [x] 6.8 Display match status indicators and scores

