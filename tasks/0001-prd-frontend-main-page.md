# PRD: Frontend Main Page with Data Update Feature

## Introduction/Overview

This feature will create a web-based frontend for the FPL Prediction Machine application. The main page will serve as the entry point for FPL managers to view current gameweek fixtures, Premier League standings, and access data updates. The page will automatically fetch fresh data from the FPL API when loaded, with the option for manual refresh, providing users with up-to-date information for making their player selection decisions.

The goal is to create an engaging, fantasy football-themed landing page that displays essential FPL information and allows seamless data updates from the FPL API.

## Goals

1. Create a responsive, fantasy football-themed main page with modern UI/UX
2. Automatically fetch and display current FPL data when the page loads
3. Provide manual data update functionality with visual feedback (rolling football icon)
4. Display current gameweek fixtures with comprehensive match information
5. Display full Premier League standings table with detailed statistics
6. Integrate the existing FPL API client to fetch real-time data
7. Provide clear visual indicators during data update operations

## User Stories

1. **As an FPL manager**, I want to see the current gameweek fixtures when I open the application, so that I can plan my team selections for upcoming matches.

2. **As an FPL manager**, I want to see the full Premier League table, so that I can understand team standings and form when making player picks.

3. **As an FPL manager**, I want the application to automatically refresh data when I open the page, so that I always see the most current information without manual action.

4. **As an FPL manager**, I want to manually trigger a data update with a button, so that I can refresh information at any time.

5. **As an FPL manager**, I want to see a visual indicator (rolling football icon) during data updates, so that I know the system is actively fetching new data.

6. **As an FPL manager**, I want to see comprehensive match details including team form and difficulty ratings, so that I can make informed player selection decisions.

7. **As an FPL manager**, I want to see match results if games are finished, so that I can review recent performances.

## Functional Requirements

1. The system must display a main page with fantasy football-themed design when users access the root URL.

2. The system must display a site description: "Pick best eleven for FPL. This application is creating player pick process for FPL managers."

3. The system must automatically run the FPL API data fetch program (`src/fpl_api_client.py`) when the main page loads.

4. The system must display a rolling/animated football icon when data update is in progress.

5. The system must provide a manual "Update Data" button that triggers the FPL API data fetch program.

6. The system must display "This Round Games" section showing current gameweek fixtures with:
   - Home team name
   - Away team name
   - Match date and time (kickoff time)
   - Difficulty ratings for both teams
   - Match scores/results (if match is finished)
   - Team form indicators
   - Match status (upcoming, in progress, finished)

7. The system must display "Premier League Table" section showing full league standings with:
   - Position
   - Team name
   - Matches played
   - Wins
   - Draws
   - Losses
   - Goals For (GF)
   - Goals Against (GA)
   - Goal Difference (GD)
   - Points

8. The system must handle errors gracefully if the FPL API is unavailable or returns errors.

9. The system must display appropriate loading states during data fetching operations.

10. The system must cache fetched data to avoid unnecessary API calls on rapid page refreshes.

11. The system must show visual feedback when data update completes successfully or fails.

12. The system must be responsive and work on desktop, tablet, and mobile devices.

## Non-Goals (Out of Scope)

1. User authentication or login functionality
2. User preferences or saved data
3. Player selection/picking interface (this will be a separate feature)
4. Prediction algorithms or ML models (backend functionality only)
5. Historical data visualization beyond current gameweek
6. Real-time live match updates (static data refresh only)
7. Data export functionality
8. Customizable dashboard layouts

## Design Considerations

1. **Fantasy Football Theme:**
   - Use football/soccer-related color schemes (greens for pitch, team colors)
   - Incorporate football-related icons and imagery
   - Use sports-themed fonts and styling
   - Include subtle animations related to football

2. **UI Components:**
   - Header with application title and description
   - Data update button with icon
   - Loading animation (rolling football icon) during updates
   - Fixtures section with card-based layout for matches
   - League table with clear, readable formatting
   - Status indicators (upcoming, live, finished) for matches

3. **Color Scheme:**
   - Primary: Football pitch green (#2d5016 or similar)
   - Secondary: Team colors or neutral grays
   - Accent: Contrast colors for important information
   - Background: Clean, modern design

4. **Responsive Design:**
   - Mobile-first approach
   - Stack sections vertically on mobile
   - Horizontal table layout on desktop
   - Touch-friendly buttons and interactions

5. **Typography:**
   - Clear, readable fonts
   - Appropriate heading hierarchy
   - Team names in bold or distinct styling

## Technical Considerations

1. **Backend Framework:**
   - Use Flask or FastAPI to serve the frontend and handle API calls
   - Create API endpoints that wrap the existing `fpl_api_client.py`
   - Return JSON data for frontend consumption

2. **Frontend Technology:**
   - Use modern JavaScript (ES6+) or a lightweight framework
   - Vanilla HTML/CSS/JavaScript for simplicity, or React for more complex interactions
   - Consider using a CSS framework like Tailwind or Bootstrap for rapid development

3. **Data Fetching:**
   - Integrate with existing `FPLAPIClient` class from `src/fpl_api_client.py`
   - Cache data in memory or file system to avoid rate limiting
   - Handle API errors gracefully

4. **Animation:**
   - Implement rolling football icon using CSS animations or JavaScript
   - Show/hide loading indicator based on fetch status

5. **Data Processing:**
   - Determine current gameweek from event data
   - Filter fixtures for current gameweek
   - Sort league table by points, then goal difference
   - Format dates/times appropriately for user's timezone

6. **File Structure:**
   - Separate frontend assets (HTML, CSS, JS) into appropriate directories
   - Keep backend API routes separate from frontend serving
   - Follow existing project structure patterns

## Success Metrics

1. Page loads and displays data within 3 seconds on initial load
2. Data update completes successfully 95% of the time
3. All fixtures for current gameweek are displayed accurately
4. League table displays all 20 teams with correct data
5. Rolling football icon animation is smooth and visible during updates
6. Manual update button successfully triggers data refresh
7. Page is responsive and functional on mobile devices (screen width >= 320px)
8. Error messages are displayed clearly when API calls fail

## Open Questions

1. Should we implement a rate limiting mechanism for manual updates?
2. How long should data be cached before considered stale?
3. Should we show previous gameweek results alongside current gameweek?
4. Do we need to handle timezone conversion for match times?
5. Should the page refresh automatically after a successful data update, or just update the displayed data?

