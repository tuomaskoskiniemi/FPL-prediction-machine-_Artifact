# Fantasy Premier League API Documentation

**Generated:** November 2, 2025  
**API Base URL:** `https://fantasy.premierleague.com/api`

This document provides a comprehensive overview of all available data from the Fantasy Premier League (FPL) API.

## Table of Contents

1. [Available Endpoints](#available-endpoints)
2. [Bootstrap Static Data](#bootstrap-static-data)
3. [Fixtures Data](#fixtures-data)
4. [Player Detail Endpoint](#player-detail-endpoint)
5. [Team Detail Endpoint](#team-detail-endpoint)
6. [Event Detail Endpoint](#event-detail-endpoint)
7. [Data Summary](#data-summary)

---

## Available Endpoints

### 1. Bootstrap Static (`/api/bootstrap-static/`)

**Description:** Contains all static game data including players, teams, events, fixtures, game settings, and configuration.

**Status:** ✅ Available

**Response Structure:**
- `chips` - Chip information (8 items)
- `events` - Gameweek/event information (38 items)
- `game_settings` - Game configuration settings
- `game_config` - Game rules and scoring
- `phases` - Season phases (11 items)
- `teams` - Team information (20 items)
- `total_players` - Total number of players in the game
- `element_stats` - Player statistics definitions (26 items)
- `element_types` - Player position types (4 items: Goalkeeper, Defender, Midfielder, Forward)
- `elements` - Player data (746 items)

---

## Bootstrap Static Data

### Chips (8 items)

Chip information for special game chips (Wildcard, Free Hit, Triple Captain, etc.)

**Fields:**
- `id` - Chip ID
- `name` - Chip name
- `number` - Chip number
- `start_event` - First gameweek chip can be used
- `stop_event` - Last gameweek chip can be used
- `chip_type` - Type of chip
- `overrides` - Chip override settings

### Events/Gameweeks (38 items)

Information about each gameweek/event in the season.

**Fields:**
- `id` - Event ID
- `name` - Event name (e.g., "Gameweek 1")
- `deadline_time` - Transfer deadline time
- `release_time` - Data release time
- `average_entry_score` - Average FPL score for the gameweek
- `finished` - Whether the gameweek has finished
- `data_checked` - Whether data has been checked
- `highest_scoring_entry` - Highest scoring entry ID
- `deadline_time_epoch` - Deadline time as epoch timestamp
- `deadline_time_game_offset` - Game offset for deadline
- `highest_score` - Highest score in the gameweek
- `is_previous` - Is this the previous gameweek
- `is_current` - Is this the current gameweek
- `is_next` - Is this the next gameweek
- `cup_leagues_created` - Whether cup leagues have been created
- `h2h_ko_matches_created` - Whether head-to-head knockout matches created
- `can_enter` - Whether transfers can be made
- `can_manage` - Whether gameweek can be managed
- `released` - Whether data is released
- `ranked_count` - Number of ranked teams
- `overrides` - Event overrides
- `chip_plays` - Chip usage statistics
- `most_selected` - Most selected player ID
- `most_transferred_in` - Most transferred in player ID
- `top_element` - Top scoring player ID
- `top_element_info` - Top player information
- `transfers_made` - Total transfers made
- `most_captained` - Most captained player ID
- `most_vice_captained` - Most vice-captained player ID

### Game Settings

Global game configuration and rules.

**Key Fields:**
- `league_join_private_max` - Max private leagues
- `league_join_public_max` - Max public leagues
- `league_max_size_public_classic` - Max size for public classic leagues
- `league_max_size_public_h2h` - Max size for public H2H leagues
- `league_max_size_private_h2h` - Max size for private H2H leagues
- `cup_start_event_id` - Cup start event
- `cup_stop_event_id` - Cup stop event
- `squad_squadplay` - Squad play settings
- `squad_squadsize` - Squad size (15)
- `squad_total_spend` - Maximum total spend (100.0)
- `transfers_cap` - Transfer cap
- `transfers_sell_on_fee` - Transfer fee percentage
- `stats_form_days` - Form calculation period
- `timezone` - Game timezone

### Phases (11 items)

Season phases/periods.

**Fields:**
- `id` - Phase ID
- `name` - Phase name
- `start_event` - Starting gameweek
- `stop_event` - Ending gameweek
- `highest_score` - Highest score in phase

### Teams (20 items)

Premier League team information.

**Fields:**
- `id` - Team ID
- `code` - Team code
- `name` - Full team name
- `short_name` - Short team name (e.g., "ARS", "CHE")
- `played` - Matches played
- `win` - Wins
- `draw` - Draws
- `loss` - Losses
- `points` - League points
- `position` - League position
- `form` - Recent form (last 5 matches)
- `strength` - Overall team strength
- `strength_overall_home` - Home strength rating
- `strength_overall_away` - Away strength rating
- `strength_attack_home` - Home attack strength
- `strength_attack_away` - Away attack strength
- `strength_defence_home` - Home defence strength
- `strength_defence_away` - Away defence strength
- `team_division` - Team division
- `unavailable` - Whether team has unavailable players
- `pulse_id` - Pulse ID for tracking

### Element Types (4 items)

Player position types.

**Fields:**
- `id` - Position ID (1=Goalkeeper, 2=Defender, 3=Midfielder, 4=Forward)
- `plural_name` - Plural position name
- `plural_name_short` - Short plural name
- `singular_name` - Singular position name
- `singular_name_short` - Short singular name
- `squad_select` - Number selectable in squad
- `squad_min_select` - Minimum required in squad
- `squad_max_select` - Maximum allowed in squad
- `squad_min_play` - Minimum to play
- `squad_max_play` - Maximum that can play
- `element_count` - Total players in this position

### Players/Elements (746 items)

Complete player data with statistics, prices, and performance metrics.

**Player Fields:**

#### Identity & Status
- `id` - Player ID
- `code` - Player code
- `first_name` - First name
- `second_name` - Last name
- `web_name` - Display name
- `photo` - Photo URL
- `team` - Team ID
- `team_code` - Team code
- `element_type` - Position ID
- `status` - Availability status (available, unavailable, etc.)
- `squad_number` - Squad number
- `region` - Player region
- `team_join_date` - Date joined current team
- `birth_date` - Date of birth
- `opta_code` - Opta code

#### Availability & Selection
- `can_transact` - Whether player can be transferred
- `can_select` - Whether player can be selected
- `chance_of_playing_this_round` - Chance % this gameweek
- `chance_of_playing_next_round` - Chance % next gameweek
- `news` - Injury/news text
- `news_added` - News timestamp
- `removed` - Whether player removed from game
- `special` - Special flag (e.g., on loan)

#### Pricing & Value
- `now_cost` - Current price (in tenths, divide by 10)
- `cost_change_event` - Price change this gameweek
- `cost_change_event_fall` - Price fall this gameweek
- `cost_change_start` - Price change since start
- `cost_change_start_fall` - Price fall since start
- `value_form` - Value based on form
- `value_season` - Value for season

#### Performance - Points
- `total_points` - Total FPL points
- `event_points` - Points in current gameweek
- `points_per_game` - Average points per game
- `form` - Form (average points last few games)
- `bonus` - Bonus points
- `bps` - Bonus points system score

#### Performance - Goals & Assists
- `goals_scored` - Goals scored
- `assists` - Assists
- `minutes` - Minutes played
- `starts` - Starts

#### Performance - Goalkeeper & Defence
- `clean_sheets` - Clean sheets
- `goals_conceded` - Goals conceded
- `saves` - Saves (for goalkeepers)
- `penalties_saved` - Penalties saved
- `penalties_missed` - Penalties missed

#### Performance - Cards & Discipline
- `yellow_cards` - Yellow cards
- `red_cards` - Red cards
- `own_goals` - Own goals

#### Performance - Advanced Stats
- `influence` - Influence score
- `creativity` - Creativity score
- `threat` - Threat score
- `ict_index` - ICT (Influence, Creativity, Threat) index
- `clearances_blocks_interceptions` - Defensive actions
- `recoveries` - Ball recoveries
- `tackles` - Tackles made
- `defensive_contribution` - Defensive contribution metric

#### Expected Stats
- `expected_goals` (xG) - Expected goals
- `expected_assists` (xA) - Expected assists
- `expected_goal_involvements` (xGI) - Expected goal involvements
- `expected_goals_conceded` (xGC) - Expected goals conceded
- `expected_goals_per_90` - xG per 90 minutes
- `expected_assists_per_90` - xA per 90 minutes
- `expected_goal_involvements_per_90` - xGI per 90 minutes
- `expected_goals_conceded_per_90` - xGC per 90 minutes

#### Set Pieces
- `corners_and_indirect_freekicks_order` - Corner/freekick order
- `corners_and_indirect_freekicks_text` - Corner/freekick text
- `direct_freekicks_order` - Direct freekick order
- `direct_freekicks_text` - Direct freekick text
- `penalties_order` - Penalty order
- `penalties_text` - Penalty text

#### Per 90 Metrics
- `saves_per_90` - Saves per 90 minutes
- `goals_conceded_per_90` - Goals conceded per 90
- `starts_per_90` - Starts per 90
- `clean_sheets_per_90` - Clean sheets per 90
- `defensive_contribution_per_90` - Defensive contribution per 90

#### Rankings
- `influence_rank` - Influence rank
- `influence_rank_type` - Rank type for influence
- `creativity_rank` - Creativity rank
- `creativity_rank_type` - Rank type for creativity
- `threat_rank` - Threat rank
- `threat_rank_type` - Rank type for threat
- `ict_index_rank` - ICT index rank
- `ict_index_rank_type` - Rank type for ICT
- `now_cost_rank` - Price rank
- `now_cost_rank_type` - Rank type for price
- `form_rank` - Form rank
- `form_rank_type` - Rank type for form
- `points_per_game_rank` - Points per game rank
- `points_per_game_rank_type` - Rank type for PPG
- `selected_rank` - Selection percentage rank
- `selected_rank_type` - Rank type for selection

#### Transfers & Selection
- `transfers_in` - Total transfers in
- `transfers_in_event` - Transfers in this gameweek
- `transfers_out` - Total transfers out
- `transfers_out_event` - Transfers out this gameweek
- `selected_by_percent` - % of teams owning player

#### Dream Team
- `in_dreamteam` - In current gameweek dream team
- `dreamteam_count` - Times in dream team

#### Expected Points
- `ep_this` - Expected points this gameweek
- `ep_next` - Expected points next gameweek

---

## Fixtures Data

### Endpoint: `/api/fixtures/`

**Description:** All match/fixture data for the season.

**Status:** ✅ Available

**Total Fixtures:** 380 matches (full season)

**Query Parameters:**
- `?event={event_id}` - Filter by gameweek/event ID

**Fields:**
- `id` - Fixture ID
- `code` - Fixture code
- `event` - Gameweek/event ID
- `finished` - Whether match is finished
- `finished_provisional` - Provisional finish status
- `kickoff_time` - Kickoff time (ISO format)
- `minutes` - Minutes played
- `provisional_start_time` - Provisional start time
- `started` - Whether match has started
- `team_h` - Home team ID
- `team_a` - Away team ID
- `team_h_score` - Home team score (null if not played)
- `team_a_score` - Away team score (null if not played)
- `team_h_difficulty` - Home team difficulty rating (1-5, 5 is hardest)
- `team_a_difficulty` - Away team difficulty rating (1-5, 5 is hardest)
- `stats` - Detailed match statistics (array of stat objects)
- `pulse_id` - Pulse tracking ID

**Stats Object Structure:**
Each fixture contains a `stats` array with detailed statistics for both teams:
- `identifier` - Stat type (e.g., "goals_scored", "assists")
- `a` - Away team stat value (array)
- `h` - Home team stat value (array)

---

## Player Detail Endpoint

### Endpoint: `/api/element-summary/{player_id}/`

**Description:** Detailed information for a specific player including:
- Historical performance by gameweek
- Upcoming fixtures
- Fixture history
- Performance statistics breakdown

**Status:** ✅ Available

**Note:** Structure documented when fetching individual player data.

---

## Team Detail Endpoint

### Endpoint: `/api/entry/{team_id}/`

**Description:** Detailed information for a specific FPL team/entry including:
- Team composition
- Transfers
- History
- Picks for each gameweek

**Status:** ✅ Available

**Note:** Structure documented when fetching individual team data.

---

## Event Detail Endpoint

### Endpoint: `/api/event/{event_id}/live/`

**Description:** Live data for a specific gameweek/event including:
- Live player scores
- Player points breakdown
- Live fixture data

**Status:** ✅ Available

**Note:** Structure documented when fetching event data.

---

## Data Summary

### Current Season Data Counts

- **Players:** 746
- **Teams:** 20 (Premier League clubs)
- **Events/Gameweeks:** 38
- **Fixtures/Matches:** 380

### Key Data Categories

1. **Player Data:** Complete statistics for all 746 players including:
   - Identity and team information
   - Pricing and value metrics
   - Performance statistics (goals, assists, clean sheets, etc.)
   - Advanced metrics (ICT, xG, xA, xGC)
   - Rankings across multiple dimensions
   - Transfer and selection data
   - Set piece responsibilities

2. **Team Data:** Information for all 20 Premier League teams:
   - League standings (wins, draws, losses, points, position)
   - Form (recent results)
   - Strength ratings (overall, attack, defence - home and away)
   - Fixture difficulty ratings

3. **Fixture Data:** Complete match schedule and results:
   - All 380 matches for the season
   - Scores, kickoff times, match status
   - Difficulty ratings for FPL
   - Detailed match statistics

4. **Event Data:** Gameweek information:
   - Transfer deadlines
   - Average scores
   - Top performers
   - Chip usage
   - Most selected/captained players

---

## Usage Notes

### Price Format
- All prices are stored in tenths (e.g., 85 = £8.5m)
- Divide by 10 to get the actual price

### Difficulty Ratings
- Range from 1 (easiest) to 5 (hardest)
- Based on opponent strength and home/away

### Status Codes
- Player status: "a" (available), "u" (unavailable), "d" (doubtful), etc.
- Check `chance_of_playing_this_round` and `chance_of_playing_next_round` for injury probabilities

### Date/Time Format
- All timestamps are in ISO 8601 format
- Times are typically in UTC or with timezone information

### Expected Points (EP)
- `ep_this`: Expected points for current gameweek
- `ep_next`: Expected points for next gameweek
- Used for prediction models

### Expected Stats
- `expected_goals` (xG): Probability-weighted expected goals
- `expected_assists` (xA): Probability-weighted expected assists
- `expected_goals_conceded` (xGC): Expected goals against
- Useful for advanced analytics and prediction models

---

## Example Usage

See `src/fpl_api_client.py` for a complete Python client implementation that:
- Fetches all available data
- Documents the API structure
- Provides methods for accessing specific endpoints
- Handles errors gracefully

---

**Last Updated:** November 2, 2025  
**API Documentation Generated By:** FPL Prediction Machine

