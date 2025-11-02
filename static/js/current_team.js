/**
 * Current Team Page JavaScript
 * Handles loading FPL team data, displaying current team, proposed players,
 * potential trade-in players, and managing transfers
 */

const API_EXTRACT_TEAM_ID = '/api/extract-team-id';
const API_TEAM_DATA = '/api/team';
const API_PLAYERS = '/api/players/top-by-position';
const API_TEAM_ANALYSIS = '/api/team-analysis';
const API_LEAGUE_TABLE = '/api/league-table';
const PROPOSED_PLAYERS_STORAGE_KEY = 'fpl_proposed_players';
const CURRENT_TEAM_STORAGE_KEY = 'fpl_current_team_id';
const SELECTED_TEAMS_STORAGE_KEY = 'fpl_selected_teams';

// State
let currentTeamData = null;
let currentTeamPlayers = {};
let proposedPlayers = [];
let allPlayersData = {};
let teamData = {};
let leagueTable = [];
let topDefensiveTeams = []; // Top 8 teams with least goals conceded
let playersToTransferOut = [];
let playersToTransferIn = [];

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadStoredTeamId();
    loadProposedPlayers();
    fetchLeagueTable();
    attachEventListeners();
});

/**
 * Load stored team ID from localStorage
 */
function loadStoredTeamId() {
    try {
        const stored = localStorage.getItem(CURRENT_TEAM_STORAGE_KEY);
        if (stored) {
            document.getElementById('team-link-input').value = stored;
            loadTeam(parseInt(stored));
        }
    } catch (error) {
        console.error('Error loading stored team ID:', error);
    }
}

/**
 * Load proposed players from localStorage
 */
function loadProposedPlayers() {
    try {
        const stored = localStorage.getItem(PROPOSED_PLAYERS_STORAGE_KEY);
        proposedPlayers = stored ? JSON.parse(stored) : [];
    } catch (error) {
        console.error('Error loading proposed players:', error);
        proposedPlayers = [];
    }
}

/**
 * Fetch league table to identify top defensive teams
 */
async function fetchLeagueTable() {
    try {
        const response = await fetch(API_LEAGUE_TABLE);
        const data = await response.json();
        
        if (data.success && data.table) {
            leagueTable = data.table;
            // Get top 8 teams with least goals conceded
            topDefensiveTeams = data.table
                .sort((a, b) => a.goals_against - b.goals_against)
                .slice(0, 8)
                .map(t => t.id);
        }
    } catch (error) {
        console.error('Error fetching league table:', error);
    }
}

/**
 * Attach event listeners
 */
function attachEventListeners() {
    const loadBtn = document.getElementById('load-team-btn');
    const clearBtn = document.getElementById('clear-team-btn');
    const teamLinkInput = document.getElementById('team-link-input');
    const applyTransfersBtn = document.getElementById('apply-transfers-btn');
    
    if (loadBtn) {
        loadBtn.addEventListener('click', handleLoadTeam);
    }
    
    if (clearBtn) {
        clearBtn.addEventListener('click', handleClearTeam);
    }
    
    if (teamLinkInput) {
        teamLinkInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                handleLoadTeam();
            }
        });
    }
    
    if (applyTransfersBtn) {
        applyTransfersBtn.addEventListener('click', handleApplyTransfers);
    }
}

/**
 * Handle load team button click
 */
async function handleLoadTeam() {
    const input = document.getElementById('team-link-input');
    const teamLink = input.value.trim();
    const statusDiv = document.getElementById('team-link-status');
    
    if (!teamLink) {
        showStatus('Please enter a team link or team ID', 'error');
        return;
    }
    
    showStatus('Loading team data...', 'loading');
    
    try {
        // Extract team ID from link
        const extractResponse = await fetch(API_EXTRACT_TEAM_ID, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ team_link: teamLink })
        });
        
        const extractData = await extractResponse.json();
        
        if (!extractData.success) {
            showStatus(extractData.message || 'Failed to extract team ID', 'error');
            return;
        }
        
        const teamId = extractData.team_id;
        
        // Store team ID
        localStorage.setItem(CURRENT_TEAM_STORAGE_KEY, teamId.toString());
        
        // Load team data
        await loadTeam(teamId);
        
    } catch (error) {
        showStatus(`Error loading team: ${error.message}`, 'error');
        console.error('Error loading team:', error);
    }
}

/**
 * Load team data by ID
 */
async function loadTeam(teamId) {
    const statusDiv = document.getElementById('team-link-status');
    
    try {
        showStatus('Fetching team data...', 'loading');
        
        // Fetch team data
        const teamResponse = await fetch(`${API_TEAM_DATA}/${teamId}`);
        
        if (!teamResponse.ok) {
            const errorData = await teamResponse.json().catch(() => ({}));
            showStatus(errorData.message || `HTTP error: ${teamResponse.status}`, 'error');
            console.error('Team fetch error:', errorData);
            return;
        }
        
        const teamData = await teamResponse.json();
        
        if (!teamData.success) {
            showStatus(teamData.message || 'Failed to load team data', 'error');
            console.error('Team data error:', teamData);
            return;
        }
        
        currentTeamData = teamData;
        
        // Store all players in a map
        const allPicks = teamData.all_picks || [];
        currentTeamPlayers = {};
        allPicks.forEach(pick => {
            const player = pick.player;
            if (player) {
                currentTeamPlayers[player.id] = {
                    ...player,
                    pick: pick,
                    isInTeam: true
                };
            }
        });
        
        // Fetch additional data needed
        await Promise.all([
            fetchAllPlayersData(),
            fetchTeamAnalysisData()
        ]);
        
        // Display team data
        if (teamData.team) {
            displayTeamOverview(teamData.team);
        }
        
        if (teamData.picks) {
            displayCurrentTeam(teamData.picks);
        } else {
            console.warn('No picks data in team response');
            showStatus('Warning: Team loaded but no picks found', 'error');
        }
        
        displayProposedPlayers();
        displayPotentialTradePlayers();
        displayTransferSection();
        
        showStatus('Team loaded successfully!', 'success');
        document.getElementById('clear-team-btn').style.display = 'inline-block';
        
    } catch (error) {
        showStatus(`Error loading team: ${error.message || 'Unknown error'}`, 'error');
        console.error('Error loading team:', error);
    }
}

/**
 * Fetch all players data
 */
async function fetchAllPlayersData() {
    try {
        const response = await fetch(API_PLAYERS);
        const data = await response.json();
        
        if (data.success && data.players) {
            const allPlayers = [
                ...(data.players.goalkeepers || []),
                ...(data.players.defenders || []),
                ...(data.players.midfielders || []),
                ...(data.players.forwards || [])
            ];
            
            allPlayersData = {};
            allPlayers.forEach(player => {
                allPlayersData[player.id] = player;
            });
        }
    } catch (error) {
        console.error('Error fetching players data:', error);
    }
}

/**
 * Fetch team analysis data
 */
async function fetchTeamAnalysisData() {
    try {
        const response = await fetch(API_TEAM_ANALYSIS);
        const data = await response.json();
        
        if (data.success && data.teams) {
            data.teams.forEach(team => {
                teamData[team.team_id] = team;
            });
        }
    } catch (error) {
        console.error('Error fetching team analysis:', error);
    }
}

/**
 * Show status message
 */
function showStatus(message, type) {
    const statusDiv = document.getElementById('team-link-status');
    if (!statusDiv) return;
    
    statusDiv.textContent = message;
    statusDiv.className = `team-link-status ${type}`;
    
    if (type === 'success' || type === 'error') {
        setTimeout(() => {
            statusDiv.textContent = '';
            statusDiv.className = 'team-link-status';
        }, 5000);
    }
}

/**
 * Display team overview
 */
function displayTeamOverview(team) {
    if (!team) return;
    
    document.getElementById('team-name-value').textContent = team.name || `${team.player_first_name} ${team.player_last_name}`;
    document.getElementById('team-value-value').textContent = `£${parseFloat(team.total_value || 0).toFixed(1)}m`;
    document.getElementById('team-bank-value').textContent = `£${parseFloat(team.bank || 0).toFixed(1)}m`;
    document.getElementById('team-points-value').textContent = team.total_points || 0;
    
    document.getElementById('team-overview-section').style.display = 'block';
}

/**
 * Display current team players
 */
function displayCurrentTeam(picksByPosition) {
    const container = document.getElementById('current-team-container');
    if (!container) return;
    
    if (!picksByPosition) {
        container.innerHTML = '<p class="no-players-message">No team data available</p>';
        document.getElementById('current-team-section').style.display = 'block';
        return;
    }
    
    const positions = [
        { key: 'goalkeepers', title: 'Goalkeepers', posId: 1 },
        { key: 'defenders', title: 'Defenders', posId: 2 },
        { key: 'midfielders', title: 'Midfielders', posId: 3 },
        { key: 'forwards', title: 'Forwards', posId: 4 }
    ];
    
    let hasPlayers = false;
    let html = '<div class="players-by-position">';
    
    positions.forEach(({ key, title, posId }) => {
        const players = picksByPosition[key] || [];
        if (players.length === 0) return;
        
        hasPlayers = true;
        
        html += `
            <div class="position-section">
                <h2 class="position-title">${title} (${players.length})</h2>
                <div class="players-table-wrapper">
                    <table class="players-table">
                        <thead>
                            <tr>
                                <th>Action</th>
                                <th>Player</th>
                                <th>Team</th>
                                <th>Price</th>
                                <th>Last 3 Pts</th>
                                <th>Last 5 Pts</th>
                                <th>Total Pts</th>
                                <th>PPG</th>
                                <th>Pts/£M</th>
                                <th>Goals</th>
                                <th>Assists</th>
                                <th>CS</th>
                                <th>ICT</th>
                                <th>Form</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${players.map(pick => {
                                const player = pick.player;
                                if (!player) {
                                    console.warn('Pick without player data:', pick);
                                    return '';
                                }
                                
                                // Ensure element_type is correct
                                if (!player.element_type && pick.element_type !== undefined) {
                                    player.element_type = pick.element_type;
                                }
                                
                                const isInTransferOut = playersToTransferOut.includes(player.id);
                                const rowClass = isInTransferOut ? 'selected-transfer-out' : '';
                                
                                return `
                                    <tr class="${rowClass}" data-player-id="${player.id}" data-position-id="${posId}">
                                        <td>
                                            <button class="transfer-action-btn transfer-out" 
                                                    data-player-id="${player.id}" 
                                                    data-action="transfer-out">
                                                ${isInTransferOut ? 'Remove' : 'Transfer Out'}
                                            </button>
                                        </td>
                                        <td class="player-name-cell">
                                            <strong>${player.web_name || 'N/A'}</strong>
                                            ${player.first_name && player.second_name ? `<small>${player.first_name} ${player.second_name}</small>` : ''}
                                            ${pick.multiplier > 1 ? `<span class="multiplier-badge">x${pick.multiplier}</span>` : ''}
                                        </td>
                                        <td>${pick.team_short_name || pick.team_name || player.team_short_name || player.team_name || 'N/A'}</td>
                                        <td>${formatPlayerCost(player.now_cost)}</td>
                                        <td class="points-cell">${safeToFixed(player.last_3_games_points || 0, 1)}</td>
                                        <td class="points-cell">${safeToFixed(player.last_5_games_points || 0, 1)}</td>
                                        <td class="points-cell">${player.total_points || 0}</td>
                                        <td>${safeToFixed(player.points_per_game || 0, 1)}</td>
                                        <td class="value-cell">${safeToFixed(player.points_per_million || 0, 2)}</td>
                                        <td>${player.goals_scored || 0}</td>
                                        <td>${player.assists || 0}</td>
                                        <td>${player.clean_sheets || 0}</td>
                                        <td>${safeToFixed(player.ict_index || 0, 1)}</td>
                                        <td>${player.form || '0.0'}</td>
                                        <td>${getStatusBadge(player)}</td>
                                    </tr>
                                `;
                            }).filter(row => row !== '').join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    
    if (!hasPlayers) {
        container.innerHTML = '<p class="no-players-message">No players found in current team</p>';
    } else {
        container.innerHTML = html;
    }
    
    document.getElementById('current-team-section').style.display = 'block';
    
    // Attach transfer out listeners
    attachTransferListeners('current-team');
}

/**
 * Display proposed players
 */
function displayProposedPlayers() {
    const container = document.getElementById('proposed-players-container');
    if (!container) return;
    
    if (proposedPlayers.length === 0) {
        container.innerHTML = '<p class="no-players-message">No players proposed yet. Go to the Propose Players page to select players.</p>';
        document.getElementById('proposed-players-section').style.display = 'block';
        return;
    }
    
    // Group by position
    const playersByPosition = {
        goalkeepers: [],
        defenders: [],
        midfielders: [],
        forwards: []
    };
    
    proposedPlayers.forEach(playerId => {
        const player = allPlayersData[playerId];
        if (player) {
            // Ensure element_type exists
            if (!player.element_type) {
                console.warn(`Player ${playerId} missing element_type`);
                return;
            }
            const positionKey = getPositionKey(player.element_type);
            if (playersByPosition[positionKey]) {
                playersByPosition[positionKey].push(player);
            }
        }
    });
    
    const positions = [
        { key: 'goalkeepers', title: 'Goalkeepers', posId: 1 },
        { key: 'defenders', title: 'Defenders', posId: 2 },
        { key: 'midfielders', title: 'Midfielders', posId: 3 },
        { key: 'forwards', title: 'Forwards', posId: 4 }
    ];
    
    let html = '<div class="players-by-position">';
    let hasPlayers = false;
    
    positions.forEach(({ key, title, posId }) => {
        const players = playersByPosition[key] || [];
        if (players.length === 0) return;
        
        hasPlayers = true;
        
        html += `
            <div class="position-section">
                <h2 class="position-title">${title} (${players.length})</h2>
                <div class="players-table-wrapper">
                    <table class="players-table">
                        <thead>
                            <tr>
                                <th>Action</th>
                                <th>Player</th>
                                <th>Team</th>
                                <th>Price</th>
                                <th>Last 3 Pts</th>
                                <th>Last 5 Pts</th>
                                <th>Total Pts</th>
                                <th>PPG</th>
                                <th>Pts/£M</th>
                                <th>Goals</th>
                                <th>Assists</th>
                                <th>CS</th>
                                <th>ICT</th>
                                <th>Form</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${players.map(player => {
                                const isInTransferIn = playersToTransferIn.includes(player.id);
                                const rowClass = isInTransferIn ? 'selected-transfer-in' : '';
                                const team = teamData[player.team] || {};
                                
                                return `
                                    <tr class="${rowClass}" data-player-id="${player.id}" data-position-id="${posId}">
                                        <td>
                                            <button class="transfer-action-btn transfer-in" 
                                                    data-player-id="${player.id}" 
                                                    data-action="transfer-in">
                                                ${isInTransferIn ? 'Remove' : 'Transfer In'}
                                            </button>
                                        </td>
                                        <td class="player-name-cell">
                                            <strong>${player.web_name || 'N/A'}</strong>
                                            ${player.first_name && player.second_name ? `<small>${player.first_name} ${player.second_name}</small>` : ''}
                                        </td>
                                        <td>${player.team_short_name || player.team_name || 'N/A'}</td>
                                        <td>${formatPlayerCost(player.now_cost)}</td>
                                        <td class="points-cell">${safeToFixed(player.last_3_games_points || 0, 1)}</td>
                                        <td class="points-cell">${safeToFixed(player.last_5_games_points || 0, 1)}</td>
                                        <td class="points-cell">${player.total_points || 0}</td>
                                        <td>${safeToFixed(player.points_per_game || 0, 1)}</td>
                                        <td class="value-cell">${safeToFixed(player.points_per_million || 0, 2)}</td>
                                        <td>${player.goals_scored || 0}</td>
                                        <td>${player.assists || 0}</td>
                                        <td>${player.clean_sheets || 0}</td>
                                        <td>${safeToFixed(player.ict_index || 0, 1)}</td>
                                        <td>${player.form || '0.0'}</td>
                                        <td>${getStatusBadge(player)}</td>
                                    </tr>
                                `;
                            }).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    
    if (!hasPlayers) {
        container.innerHTML = '<p class="no-players-message">No players found</p>';
    } else {
        container.innerHTML = html;
    }
    
    document.getElementById('proposed-players-section').style.display = 'block';
    
    // Attach transfer in listeners
    attachTransferListeners('proposed');
}

/**
 * Display potential trade-in players
 */
function displayPotentialTradePlayers() {
    const container = document.getElementById('potential-trade-container');
    if (!container) return;
    
    // Analyze current team and propose improvements based on principles
    const potentialPlayers = analyzePotentialTrades();
    
    if (potentialPlayers.length === 0) {
        container.innerHTML = '<p class="no-players-message">No potential trade-in players found based on current analysis.</p>';
        document.getElementById('potential-trade-section').style.display = 'block';
        return;
    }
    
    // Group by position
    const playersByPosition = {
        goalkeepers: [],
        defenders: [],
        midfielders: [],
        forwards: []
    };
    
    potentialPlayers.forEach(player => {
        const positionKey = getPositionKey(player.element_type);
        if (playersByPosition[positionKey]) {
            playersByPosition[positionKey].push(player);
        }
    });
    
    const positions = [
        { key: 'goalkeepers', title: 'Goalkeepers', posId: 1 },
        { key: 'defenders', title: 'Defenders', posId: 2 },
        { key: 'midfielders', title: 'Midfielders', posId: 3 },
        { key: 'forwards', title: 'Forwards', posId: 4 }
    ];
    
    let html = '<div class="players-by-position">';
    let hasPlayers = false;
    
    positions.forEach(({ key, title, posId }) => {
        const players = playersByPosition[key] || [];
        if (players.length === 0) return;
        
        hasPlayers = true;
        
        html += `
            <div class="position-section">
                <h2 class="position-title">${title} (${players.length})</h2>
                <div class="players-table-wrapper">
                    <table class="players-table">
                        <thead>
                            <tr>
                                <th>Action</th>
                                <th>Player</th>
                                <th>Team</th>
                                <th>Price</th>
                                <th>Last 3 Pts</th>
                                <th>Last 5 Pts</th>
                                <th>Total Pts</th>
                                <th>PPG</th>
                                <th>Pts/£M</th>
                                <th>Goals</th>
                                <th>Assists</th>
                                <th>CS</th>
                                <th>ICT</th>
                                <th>Form</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${players.map(player => {
                                const isInTransferIn = playersToTransferIn.includes(player.id);
                                const rowClass = isInTransferIn ? 'selected-transfer-in' : '';
                                const team = teamData[player.team] || {};
                                
                                return `
                                    <tr class="${rowClass}" data-player-id="${player.id}" data-position-id="${posId}">
                                        <td>
                                            <button class="transfer-action-btn transfer-in" 
                                                    data-player-id="${player.id}" 
                                                    data-action="transfer-in">
                                                ${isInTransferIn ? 'Remove' : 'Transfer In'}
                                            </button>
                                        </td>
                                        <td class="player-name-cell">
                                            <strong>${player.web_name || 'N/A'}</strong>
                                            ${player.first_name && player.second_name ? `<small>${player.first_name} ${player.second_name}</small>` : ''}
                                        </td>
                                        <td>${player.team_short_name || player.team_name || 'N/A'}</td>
                                        <td>${formatPlayerCost(player.now_cost)}</td>
                                        <td class="points-cell">${safeToFixed(player.last_3_games_points || 0, 1)}</td>
                                        <td class="points-cell">${safeToFixed(player.last_5_games_points || 0, 1)}</td>
                                        <td class="points-cell">${player.total_points || 0}</td>
                                        <td>${safeToFixed(player.points_per_game || 0, 1)}</td>
                                        <td class="value-cell">${safeToFixed(player.points_per_million || 0, 2)}</td>
                                        <td>${player.goals_scored || 0}</td>
                                        <td>${player.assists || 0}</td>
                                        <td>${player.clean_sheets || 0}</td>
                                        <td>${safeToFixed(player.ict_index || 0, 1)}</td>
                                        <td>${player.form || '0.0'}</td>
                                        <td>${getStatusBadge(player)}</td>
                                    </tr>
                                `;
                            }).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    
    if (!hasPlayers) {
        container.innerHTML = '<p class="no-players-message">No players found</p>';
    } else {
        container.innerHTML = html;
    }
    
    document.getElementById('potential-trade-section').style.display = 'block';
    
    // Attach transfer in listeners
    attachTransferListeners('potential-trade');
}

/**
 * Analyze potential trades based on principles
 */
function analyzePotentialTrades() {
    const potential = [];
    const currentPlayerIds = Object.keys(currentTeamPlayers).map(id => parseInt(id));
    
    // Get all players and filter based on principles
    Object.values(allPlayersData).forEach(player => {
        // Skip if already in team
        if (currentPlayerIds.includes(player.id)) return;
        
        // Ensure element_type exists
        if (!player.element_type) {
            console.warn(`Player ${player.id} missing element_type, skipping`);
            return;
        }
        
        // Skip injured players
        if (player.chance_of_playing_this_round === 0 || player.chance_of_playing_next_round === 0) {
            return;
        }
        
        let score = 0;
        const team = teamData[player.team] || {};
        
        // Form over fixtures (weight: high)
        score += (parseFloat(player.form) || 0) * 3;
        
        // Points per game (weight: high)
        score += (parseFloat(player.points_per_game) || 0) * 2;
        
        // Attacking players (goals + assists)
        const playerElementType = player.element_type;
        if (playerElementType === 3 || playerElementType === 4) { // Midfielders or Forwards
            score += (player.goals_scored || 0) * 2;
            score += (player.assists || 0) * 1.5;
        }
        
        // Attacking defenders
        if (playerElementType === 2) { // Defenders
            score += (player.goals_scored || 0) * 3;
            score += (player.assists || 0) * 2;
            // Prefer defenders from top defensive teams
            if (topDefensiveTeams.includes(player.team)) {
                score += 5;
            }
        }
        
        // Full minutes players (prefer players who play full minutes)
        const minutes = player.minutes || 0;
        if (minutes > 2700) { // ~30 games worth
            score += 3;
        }
        
        // Recent form (last 5 games)
        score += (player.last_5_games_points || 0) * 0.5;
        
        // FDR consideration (lighter weight as form over fixtures)
        if (team.adjusted_fdr_next_5 !== null && team.adjusted_fdr_next_5 !== undefined) {
            score += (5 - team.adjusted_fdr_next_5) * 0.5;
        }
        
        // Selected by % (popularity indicator)
        score += (parseFloat(player.selected_by_percent) || 0) * 0.1;
        
        player.tradeScore = score;
        potential.push(player);
    });
    
    // Sort by score and return top 20
    return potential
        .sort((a, b) => b.tradeScore - a.tradeScore)
        .slice(0, 20);
}

/**
 * Display transfer section
 */
function displayTransferSection() {
    document.getElementById('transfer-section').style.display = 'block';
    updateTransferDisplay();
}

/**
 * Update transfer display
 */
function updateTransferDisplay() {
    updateTransferOutDisplay();
    updateTransferInDisplay();
    updateTransferSummary();
}

/**
 * Update transfer out display
 */
function updateTransferOutDisplay() {
    const container = document.getElementById('transfer-out-container');
    if (!container) return;
    
    if (playersToTransferOut.length === 0) {
        container.innerHTML = '<p class="empty-transfer-list">No players selected to transfer out. Click on players from your current team to transfer them out.</p>';
        return;
    }
    
    container.innerHTML = playersToTransferOut.map(playerId => {
        const player = currentTeamPlayers[playerId];
        if (!player) return '';
        
        const team = teamData[player.team] || {};
        return createTransferCard(player, team, 'out');
    }).join('');
    
    attachTransferRemoveListeners('out');
}

/**
 * Update transfer in display
 */
function updateTransferInDisplay() {
    const container = document.getElementById('transfer-in-container');
    if (!container) return;
    
    if (playersToTransferIn.length === 0) {
        container.innerHTML = '<p class="empty-transfer-list">No players selected to transfer in. Click on players from potential trades or proposed players to transfer them in.</p>';
        return;
    }
    
    container.innerHTML = playersToTransferIn.map(playerId => {
        const player = allPlayersData[playerId];
        if (!player) return '';
        
        const team = teamData[player.team] || {};
        return createTransferCard(player, team, 'in');
    }).join('');
    
    attachTransferRemoveListeners('in');
}

/**
 * Update transfer summary
 */
function updateTransferSummary() {
    const outCount = playersToTransferOut.length;
    const inCount = playersToTransferIn.length;
    
    document.getElementById('transfer-out-count').textContent = outCount;
    document.getElementById('transfer-in-count').textContent = inCount;
    
    // Calculate budget impact
    let budgetImpact = 0;
    
    playersToTransferOut.forEach(playerId => {
        const player = currentTeamPlayers[playerId];
        if (player) {
            budgetImpact += parseFloat(player.now_cost || 0);
        }
    });
    
    playersToTransferIn.forEach(playerId => {
        const player = allPlayersData[playerId];
        if (player) {
            budgetImpact -= parseFloat(player.now_cost || 0);
        }
    });
    
    const budgetImpactFormatted = (Math.abs(budgetImpact) / 10.0).toFixed(1);
    const budgetColor = budgetImpact >= 0 ? 'success' : 'error';
    
    const budgetEl = document.getElementById('budget-impact');
    budgetEl.textContent = `£${budgetImpactFormatted}m`;
    budgetEl.className = `summary-value ${budgetColor}`;
    
    // Enable/disable apply button
    const applyBtn = document.getElementById('apply-transfers-btn');
    if (applyBtn) {
        applyBtn.disabled = (outCount === 0 && inCount === 0) || outCount !== inCount;
    }
}

/**
 * Create player card (same format as propose players page)
 */
function createPlayerCard(player, team, context, pick = null) {
    if (!player) return '';
    
    // Ensure element_type is available
    let elementType = player.element_type;
    if (!elementType && pick && pick.element_type !== undefined) {
        elementType = pick.element_type;
        player.element_type = elementType;
    }
    
    // Ensure we have a valid elementType
    if (!elementType) {
        elementType = 4; // Default to forward if missing
    }
    
    const isInjured = (player.chance_of_playing_this_round === 0 || player.chance_of_playing_next_round === 0);
    const isInTransferOut = playersToTransferOut.includes(player.id);
    const isInTransferIn = playersToTransferIn.includes(player.id);
    const isTopDefensiveTeam = topDefensiveTeams.includes(player.team) && elementType === 2;
    
    // Format team data
    const fdr5Color = getFDRColor(team.fdr_next_5);
    const fdr10Color = getFDRColor(team.fdr_next_10);
    const adjFdr5Color = getFDRColor(team.adjusted_fdr_next_5);
    
    // Check if player is in current team
    const isCurrentPlayer = currentTeamPlayers[player.id] !== undefined;
    const transferAction = isCurrentPlayer ? 'transfer-out' : 'transfer-in';
    const transferLabel = isCurrentPlayer ? 'Transfer Out' : 'Transfer In';
    
    let cardClasses = `player-card ${context}`;
    if (isInjured) cardClasses += ' injured';
    if (isInTransferOut) cardClasses += ' selected-transfer-out';
    if (isInTransferIn) cardClasses += ' selected-transfer-in';
    
    return `
        <div class="${cardClasses}" data-player-id="${player.id}">
            <div class="player-card-header">
                <div class="player-main-info">
                    <h4 class="player-name">
                        ${player.web_name}
                        ${isInjured ? '<span class="injury-badge">⚠️ INJURED</span>' : ''}
                        ${isTopDefensiveTeam ? '<span class="defensive-badge">D</span>' : ''}
                    </h4>
                    <span class="player-team-name">${player.team_short_name || player.team_name}</span>
                    <span class="player-position">${getPositionName(elementType || player.element_type || 4)}</span>
                    ${pick ? `<span class="player-multiplier">${pick.multiplier > 1 ? `x${pick.multiplier}` : ''}</span>` : ''}
                </div>
                <div class="player-actions">
                    ${context === 'current-team' || context === 'proposed' || context === 'potential-trade' ? `
                        <button class="transfer-action-btn ${transferAction}" 
                                data-player-id="${player.id}" 
                                data-action="${transferAction}">
                            ${transferLabel}
                        </button>
                    ` : ''}
                </div>
            </div>
            
            <div class="player-stats-grid">
                <div class="stat-item">
                    <span class="stat-label">Price:</span>
                    <span class="stat-value">£${(parseFloat(player.now_cost || 0) / 10).toFixed(1)}m</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Total Points:</span>
                    <span class="stat-value">${player.total_points || 0}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Last 5 Games:</span>
                    <span class="stat-value">${player.last_5_games_points || 0}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">PPG:</span>
                    <span class="stat-value">${parseFloat(player.points_per_game || 0).toFixed(1)}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Goals:</span>
                    <span class="stat-value">${player.goals_scored || 0}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Assists:</span>
                    <span class="stat-value">${player.assists || 0}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Form:</span>
                    <span class="stat-value">${player.form || '0.0'}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Selected By:</span>
                    <span class="stat-value">${parseFloat(player.selected_by_percent || 0).toFixed(1)}%</span>
                </div>
            </div>
            
            ${team.team_id ? `
                <div class="team-data-card">
                    <h5 class="team-data-title">
                        Team Data: ${team.team_name || player.team_short_name || 'Unknown'}
                    </h5>
                    <div class="team-metrics-grid">
                        <div class="team-metric">
                            <span class="team-metric-label">FDR (Next 5):</span>
                            <span class="team-metric-value" style="color: ${fdr5Color}">
                                ${team.fdr_next_5 !== null && team.fdr_next_5 !== undefined ? parseFloat(team.fdr_next_5).toFixed(2) : 'N/A'}
                            </span>
                        </div>
                        <div class="team-metric">
                            <span class="team-metric-label">FDR (Next 10):</span>
                            <span class="team-metric-value" style="color: ${fdr10Color}">
                                ${team.fdr_next_10 !== null && team.fdr_next_10 !== undefined ? parseFloat(team.fdr_next_10).toFixed(2) : 'N/A'}
                            </span>
                        </div>
                        <div class="team-metric">
                            <span class="team-metric-label">Adjusted FDR (5):</span>
                            <span class="team-metric-value" style="color: ${adjFdr5Color}">
                                ${team.adjusted_fdr_next_5 !== null && team.adjusted_fdr_next_5 !== undefined ? parseFloat(team.adjusted_fdr_next_5).toFixed(2) : 'N/A'}
                            </span>
                        </div>
                    </div>
                </div>
            ` : ''}
        </div>
    `;
}

/**
 * Create transfer card
 */
function createTransferCard(player, team, direction) {
    if (!player) return '';
    
    return `
        <div class="transfer-card ${direction}" data-player-id="${player.id}">
            <div class="transfer-card-header">
                <h4 class="transfer-player-name">${player.web_name}</h4>
                <button class="remove-transfer-btn" data-player-id="${player.id}" data-direction="${direction}">×</button>
            </div>
            <div class="transfer-card-info">
                <span class="transfer-player-position">${getPositionName(player.element_type)}</span>
                <span class="transfer-player-team">${player.team_short_name || player.team_name}</span>
                <span class="transfer-player-price">£${(parseFloat(player.now_cost || 0) / 10).toFixed(1)}m</span>
            </div>
        </div>
    `;
}

/**
 * Attach transfer listeners
 */
function attachTransferListeners(context) {
    const buttons = document.querySelectorAll(`.player-card.${context} .transfer-action-btn`);
    buttons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const playerId = parseInt(e.target.dataset.playerId);
            const action = e.target.dataset.action;
            
            if (action === 'transfer-out') {
                toggleTransferOut(playerId);
            } else if (action === 'transfer-in') {
                toggleTransferIn(playerId);
            }
        });
    });
}

/**
 * Attach transfer remove listeners
 */
function attachTransferRemoveListeners(direction) {
    const buttons = document.querySelectorAll(`.remove-transfer-btn[data-direction="${direction}"]`);
    buttons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const playerId = parseInt(e.target.dataset.playerId);
            const dir = e.target.dataset.direction;
            
            if (dir === 'out') {
                toggleTransferOut(playerId);
            } else if (dir === 'in') {
                toggleTransferIn(playerId);
            }
        });
    });
}

/**
 * Toggle transfer out
 */
function toggleTransferOut(playerId) {
    const index = playersToTransferOut.indexOf(playerId);
    if (index > -1) {
        playersToTransferOut.splice(index, 1);
    } else {
        playersToTransferOut.push(playerId);
    }
    updateTransferDisplay();
    refreshPlayerCards();
}

/**
 * Toggle transfer in
 */
function toggleTransferIn(playerId) {
    const index = playersToTransferIn.indexOf(playerId);
    if (index > -1) {
        playersToTransferIn.splice(index, 1);
    } else {
        playersToTransferIn.push(playerId);
    }
    updateTransferDisplay();
    refreshPlayerCards();
}

/**
 * Refresh player cards to update selected state
 */
function refreshPlayerCards() {
    // Update current team display
    if (currentTeamData && currentTeamData.picks) {
        displayCurrentTeam(currentTeamData.picks);
    }
    
    // Update potential trade display
    displayPotentialTradePlayers();
    
    // Update proposed players display
    displayProposedPlayers();
}

/**
 * Handle apply transfers
 */
function handleApplyTransfers() {
    if (playersToTransferOut.length !== playersToTransferIn.length) {
        alert('Number of players to transfer out must equal number of players to transfer in.');
        return;
    }
    
    if (playersToTransferOut.length === 0) {
        alert('Please select players to transfer.');
        return;
    }
    
    // Calculate budget impact
    let budgetImpact = 0;
    playersToTransferOut.forEach(playerId => {
        const player = currentTeamPlayers[playerId];
        if (player) budgetImpact += player.now_cost || 0;
    });
    playersToTransferIn.forEach(playerId => {
        const player = allPlayersData[playerId];
        if (player) budgetImpact -= player.now_cost || 0;
    });
    
    const currentBank = currentTeamData.team.bank * 10; // Convert to tenths
    const newBank = currentBank + budgetImpact;
    
    if (newBank < 0) {
        alert(`Insufficient budget. You would need £${Math.abs(newBank / 10).toFixed(1)}m more.`);
        return;
    }
    
    // Show confirmation
    const confirmMsg = `Transfer ${playersToTransferOut.length} player(s) out and ${playersToTransferIn.length} player(s) in?\n\nBudget impact: £${(budgetImpact / 10).toFixed(1)}m\nNew bank: £${(newBank / 10).toFixed(1)}m`;
    
    if (confirm(confirmMsg)) {
        // In a real application, this would send the transfers to the FPL API
        alert('Transfers would be applied here. In the actual implementation, this would call the FPL API to make the transfers.');
        
        // For now, just clear the selections
        playersToTransferOut = [];
        playersToTransferIn = [];
        updateTransferDisplay();
        refreshPlayerCards();
    }
}

/**
 * Handle clear team
 */
function handleClearTeam() {
    if (confirm('Are you sure you want to clear the current team?')) {
        localStorage.removeItem(CURRENT_TEAM_STORAGE_KEY);
        document.getElementById('team-link-input').value = '';
        document.getElementById('clear-team-btn').style.display = 'none';
        document.getElementById('team-overview-section').style.display = 'none';
        document.getElementById('current-team-section').style.display = 'none';
        document.getElementById('proposed-players-section').style.display = 'none';
        document.getElementById('potential-trade-section').style.display = 'none';
        document.getElementById('transfer-section').style.display = 'none';
        currentTeamData = null;
        currentTeamPlayers = {};
        playersToTransferOut = [];
        playersToTransferIn = [];
    }
}

/**
 * Get position key from position ID
 */
function getPositionKey(positionId) {
    const mapping = {
        1: 'goalkeepers',
        2: 'defenders',
        3: 'midfielders',
        4: 'forwards'
    };
    return mapping[positionId] || 'forwards';
}

/**
 * Get position name from position ID
 */
function getPositionName(positionId) {
    const mapping = {
        1: 'GK',
        2: 'DEF',
        3: 'MID',
        4: 'FWD'
    };
    return mapping[positionId] || 'FWD';
}

/**
 * Get FDR color based on rating
 */
function getFDRColor(fdr) {
    if (fdr === null || fdr === undefined) return '#6c757d';
    if (fdr <= 2) return '#28a745'; // Green (easy)
    if (fdr <= 3) return '#ffc107'; // Yellow (medium)
    return '#dc3545'; // Red (hard)
}

/**
 * Safely format a number to fixed decimal places
 */
function safeToFixed(value, decimals = 1) {
    if (value === null || value === undefined || value === '') {
        return '0.0';
    }
    const num = typeof value === 'string' ? parseFloat(value) : Number(value);
    if (isNaN(num)) {
        return '0.0';
    }
    return num.toFixed(decimals);
}

/**
 * Format player cost (handles both tenths and millions)
 */
function formatPlayerCost(cost) {
    if (!cost) return '£0.0m';
    // If cost is greater than 20, it's likely in tenths, otherwise already in millions
    const costInMillions = cost > 20 ? cost / 10.0 : cost;
    return `£${safeToFixed(costInMillions, 1)}m`;
}

/**
 * Get status badge HTML
 */
function getStatusBadge(player) {
    if (player.status && player.status !== 'a') {
        return `<span class="status-badge unavailable">${player.status.toUpperCase()}</span>`;
    }
    if (player.chance_of_playing_this_round && player.chance_of_playing_this_round < 100) {
        return `<span class="status-badge uncertain">${player.chance_of_playing_this_round}%</span>`;
    }
    if (player.news) {
        return `<span class="status-badge news" title="${player.news}">⚠</span>`;
    }
    return '<span class="status-badge available">Available</span>';
}
