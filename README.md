# FPL Prediction Machine

A Python-based backend application for fetching and analyzing data from the Fantasy Premier League (FPL) API to build prediction models.

## Overview

This project provides tools to:
- Fetch match, player, and team data from the Fantasy Premier League API
- Document all available data from the FPL API
- Build prediction models for FPL performance

## Project Structure

```
FPL-prediction-machine/
├── ai-dev-tasks/          # AI Agent Instructions for structured development
│   ├── create-prd.md
│   ├── generate-tasks.md
│   └── process-task-list.md
├── src/                    # Source code
│   └── fpl_api_client.py  # FPL API client
├── tasks/                  # PRDs and task lists for features
├── tests/                  # Test files
├── requirements.txt       # Python dependencies
└── README.md
```

## Setup

1. **Clone the repository** (if not already done):
   ```bash
   git clone https://github.com/tuomaskoskiniemi/FPL-prediction-machine-.git
   cd FPL-prediction-machine
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Run the Web Application

Start the Flask server:

```bash
python app.py
```

Then open your browser and navigate to:
```
http://localhost:5000
```

The main page will automatically fetch and display:
- Current gameweek fixtures
- Full Premier League table
- Team form and statistics

### Fetch FPL API Data (Standalone)

Run the FPL API client to fetch and document all available data:

```bash
python src/fpl_api_client.py
```

This will:
- Fetch all available data from the FPL API (players, teams, matches, etc.)
- Generate comprehensive documentation of the API structure
- Save the data to `fpl_data_complete.json`
- Save the documentation to `fpl_api_documentation.json`
- Print a summary of available data fields

### Using the API Client in Your Code

```python
from src.fpl_api_client import FPLAPIClient

# Initialize client
client = FPLAPIClient()

# Fetch bootstrap static data (players, teams, events)
bootstrap_static = client.fetch_bootstrap_static()

# Fetch fixtures
fixtures = client.fetch_fixtures()

# Fetch player details
player_data = client.fetch_player_detail(player_id=1)

# Fetch all data at once
all_data = client.fetch_all_data()
```

## Development Workflow

This project uses the AI Agent Instructions workflow for structured development:

1. **Create a PRD**: Use `@ai-dev-tasks/create-prd.md` to create a Product Requirements Document
2. **Generate Tasks**: Use `@ai-dev-tasks/generate-tasks.md` to break down the PRD into tasks
3. **Process Tasks**: Use `@ai-dev-tasks/process-task-list.md` to implement tasks one at a time

See the [AI Agent Instructions repository](https://github.com/tuomaskoskiniemi/AI_Agent_Instructions) for more details.

## FPL API Endpoints

The main endpoints used:

- `GET /api/bootstrap-static/` - All static game data (players, teams, events, etc.)
- `GET /api/bootstrap-dynamic/` - Dynamic game data (fixtures, events)
- `GET /api/fixtures/` - All fixture/match data
- `GET /api/fixtures/?event={event_id}` - Fixtures for a specific gameweek
- `GET /api/element-summary/{player_id}/` - Detailed player information
- `GET /api/entry/{team_id}/` - Detailed team information
- `GET /api/event/{event_id}/live/` - Live data for a specific gameweek

## Data Available

The FPL API provides:

- **Players**: Detailed statistics, prices, positions, teams, and performance data
- **Teams**: Team information, strengths, and fixtures
- **Matches/Fixtures**: Complete fixture list with scores, dates, and status
- **Events**: Gameweek information and deadlines
- **Player Details**: Historical performance, upcoming fixtures, and statistics

See `fpl_api_documentation.json` for a complete breakdown of all available fields.

## License

Apache-2.0

