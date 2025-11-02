# PRD: Top Navigation Menu with Multiple Pages

## Introduction/Overview

This feature will add a top navigation menu to the FPL Prediction Machine application, providing access to 8 different functional areas: Team Analysis, Player Analysis, Best Formation, Propose Players, Current Team, Transfers, Draft List, and Adjustments. The navigation will be persistent across all pages and allow users to easily navigate between different features of the application.

The goal is to create an intuitive navigation structure that makes all features accessible from any page, improving the user experience and making the application more organized and professional.

## Goals

1. Create a persistent top navigation menu visible on all pages
2. Implement navigation structure for 8 different functional areas
3. Ensure the menu matches the fantasy football theme
4. Make the navigation responsive for mobile devices
5. Provide visual indication of the current active page
6. Ensure smooth navigation between pages
7. Maintain existing functionality on the main/home page

## User Stories

1. **As an FPL manager**, I want to see a top navigation menu on every page, so that I can easily switch between different features of the application.

2. **As an FPL manager**, I want to click on "Team Analysis" in the menu, so that I can view detailed team statistics and analysis.

3. **As an FPL manager**, I want to click on "Player Analysis" in the menu, so that I can view detailed player statistics and analysis.

4. **As an FPL manager**, I want to click on "Best Formation" in the menu, so that I can see recommended team formations.

5. **As an FPL manager**, I want to click on "Propose Players" in the menu, so that I can view player recommendations.

6. **As an FPL manager**, I want to click on "Current Team" in the menu, so that I can view my current FPL team.

7. **As an FPL manager**, I want to click on "Transfers" in the menu, so that I can manage player transfers.

8. **As an FPL manager**, I want to click on "Draft List" in the menu, so that I can view and manage my draft list.

9. **As an FPL manager**, I want to click on "Adjustments" in the menu, so that I can adjust settings and preferences.

10. **As an FPL manager**, I want the menu to show which page I'm currently on, so that I know my location in the application.

11. **As an FPL manager**, I want the menu to work on mobile devices, so that I can navigate the application from my phone.

## Functional Requirements

1. The system must display a top navigation menu on all pages of the application.

2. The system must include the following menu items:
   - Home (or Main/Overview - links to current main page)
   - Team Analysis
   - Player Analysis
   - Best Formation
   - Propose Players
   - Current Team
   - Transfers
   - Draft List
   - Adjustments

3. The system must highlight the currently active page in the navigation menu.

4. The system must make all menu items clickable links that navigate to their respective pages.

5. The system must maintain the fantasy football theme in the navigation design.

6. The system must make the navigation responsive for mobile devices (collapsible hamburger menu on small screens).

7. The system must ensure the navigation menu remains visible when scrolling (sticky/fixed positioning).

8. The system must create placeholder pages for each menu item (content can be added in later features).

9. The system must integrate the navigation into the existing main page without breaking current functionality.

10. The system must update Flask routes to handle navigation to different pages.

11. The system must ensure the navigation works correctly with the existing CSS and JavaScript.

12. The system must maintain the existing header/description area on the main page.

## Non-Goals (Out of Scope)

1. Full implementation of content for each page (Team Analysis, Player Analysis, etc.) - these are placeholders for now
2. Backend functionality for each page section
3. User authentication or login (for Current Team features)
4. Data fetching specific to each page (basic structure only)
5. Complex interactions within each page
6. Saved state or session management
7. Mobile app version
8. Deep linking to specific page sections

## Design Considerations

1. **Navigation Style:**
   - Match the fantasy football theme (pitch green colors)
   - Use clear, readable fonts
   - Include icons or visual indicators for each menu item
   - Active page indicator (e.g., underline, background color, or bold text)

2. **Layout:**
   - Fixed or sticky positioning at the top
   - Horizontal menu on desktop
   - Collapsible hamburger menu on mobile
   - Logo/title on the left, menu items on the right (or centered)

3. **Responsive Design:**
   - Desktop: Full horizontal menu visible
   - Tablet: Horizontal menu with smaller spacing
   - Mobile: Hamburger menu that expands/collapses
   - Touch-friendly button sizes on mobile

4. **Visual Hierarchy:**
   - Navigation should be visually distinct but not overpower the content
   - Active page should be clearly highlighted
   - Hover states for menu items

5. **Integration:**
   - Navigation should appear above or replace part of the existing header
   - Main page description and update button should remain accessible
   - Footer should remain at the bottom

## Technical Considerations

1. **Flask Routes:**
   - Create routes for each menu item: `/team-analysis`, `/player-analysis`, `/best-formation`, `/propose-players`, `/current-team`, `/transfers`, `/draft-list`, `/adjustments`
   - Keep existing `/` route for the main page
   - Each route should render a template with the navigation included

2. **Template Structure:**
   - Create a base template (`base.html`) that includes the navigation
   - Update `index.html` to extend the base template
   - Create placeholder templates for each new page
   - Use Jinja2 template inheritance

3. **Navigation Component:**
   - Create a reusable navigation partial/inclusion
   - Pass the current page identifier to highlight active item
   - Use Flask's `url_for()` for route generation

4. **CSS:**
   - Add navigation styles to existing `style.css`
   - Ensure navigation styles work with existing theme
   - Add responsive breakpoints for mobile menu
   - Implement active state styling

5. **JavaScript:**
   - Add hamburger menu toggle functionality for mobile
   - Ensure navigation doesn't conflict with existing JavaScript
   - Optional: Add smooth scrolling or animation

6. **File Structure:**
   - `templates/base.html` - Base template with navigation
   - `templates/index.html` - Main page (extends base)
   - `templates/team_analysis.html` - Team analysis page
   - `templates/player_analysis.html` - Player analysis page
   - `templates/best_formation.html` - Best formation page
   - `templates/propose_players.html` - Propose players page
   - `templates/current_team.html` - Current team page
   - `templates/transfers.html` - Transfers page
   - `templates/draft_list.html` - Draft list page
   - `templates/adjustments.html` - Adjustments page

## Success Metrics

1. Navigation menu is visible on all pages
2. All 8 menu items are accessible and navigate to their respective pages
3. Active page is clearly highlighted in the navigation
4. Navigation works correctly on desktop, tablet, and mobile devices
5. Hamburger menu functions properly on mobile devices
6. Existing main page functionality remains intact
7. Navigation matches the fantasy football theme
8. No JavaScript errors when navigating between pages
9. Pages load quickly and smoothly

## Open Questions

1. Should the main page be called "Home" or "Overview" or "Dashboard" in the navigation?
2. Should we include icons for each menu item, and if so, which icons?
3. Should the navigation be fixed at the top (always visible) or scroll with the page?
4. Should we include a logo or just text in the navigation?
5. Do we need breadcrumbs in addition to the top menu?
6. Should the mobile menu slide in from the side or drop down from the top?

