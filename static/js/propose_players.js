/**
 * Propose Players Page JavaScript
 * Displays players transferred from Best Formation page
 */

const API_PLAYERS = '/api/players/top-by-position';
const PROPOSE_PLAYERS_STORAGE_KEY = 'fpl_propose_players';

let allPlayersData = {};
let proposedPlayersData = null;

document.addEventListener('DOMContentLoaded', () => {
    loadProposedPlayers();
    
    // Listen for storage changes to update when players are transferred from Best Formation
    window.addEventListener('storage', handleStorageChange);
    
    // Refresh when page becomes visible
    document.addEventListener('visibilitychange', () => {
        if (!document.hidden) {
            loadProposedPlayers();
        }
    });
    
    // Poll for localStorage changes (same-tab detection)
    let lastProposedPlayersData = localStorage.getItem(PROPOSE_PLAYERS_STORAGE_KEY) || '{}';
    setInterval(() => {
        const current = localStorage.getItem(PROPOSE_PLAYERS_STORAGE_KEY) || '{}';
        if (current !== lastProposedPlayersData) {
            lastProposedPlayersData = current;
            loadProposedPlayers();
        }
    }, 1000);
});

/**
 * Handle storage change events
 */
function handleStorageChange(e) {
    if (e.key === PROPOSE_PLAYERS_STORAGE_KEY) {
        console.log('Proposed players updated in localStorage, refreshing...');
        loadProposedPlayers();
    }
}

/**
 * Load proposed players from localStorage
 */
function loadProposedPlayers() {
    try {
        const stored = localStorage.getItem(PROPOSE_PLAYERS_STORAGE_KEY);
        if (stored) {
            const parsed = JSON.parse(stored);
            // Validate data structure
            if (parsed && (parsed.goalkeeper || parsed.defenders || parsed.midfielders || parsed.forwards || parsed.bench)) {
                proposedPlayersData = parsed;
                // Only fetch if we don't have player data yet, or if we need to refresh
                if (Object.keys(allPlayersData).length === 0) {
                    fetchPlayersData();
                } else {
                    displayProposedPlayers();
                }
            } else {
                showNoPlayersMessage();
            }
        } else {
            showNoPlayersMessage();
        }
    } catch (error) {
        console.error('Error loading proposed players:', error);
        showErrorMessage('Error loading proposed players data.');
    }
}

/**
 * Fetch all players data from API
 */
async function fetchPlayersData() {
    const container = document.getElementById('propose-players-container');
    
    try {
        const response = await fetch(API_PLAYERS);
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.message || 'Failed to load player data');
        }
        
        // Create a map of all players by ID
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
        
        displayProposedPlayers();
    } catch (error) {
        console.error('Error fetching players:', error);
        showErrorMessage(`Error loading player data: ${error.message}`);
    }
}

/**
 * Display proposed players
 */
function displayProposedPlayers() {
    if (!proposedPlayersData) {
        showNoPlayersMessage();
        return;
    }
    
    const container = document.getElementById('propose-players-container');
    
    // Get all player IDs
    const allPlayerIds = [
        proposedPlayersData.goalkeeper,
        ...(proposedPlayersData.defenders || []),
        ...(proposedPlayersData.midfielders || []),
        ...(proposedPlayersData.forwards || []),
        ...(proposedPlayersData.bench || [])
    ].filter(id => id !== null && id !== undefined);
    
    if (allPlayerIds.length === 0) {
        showNoPlayersMessage();
        return;
    }
    
    // Calculate total value
    const totalValue = calculateTotalValue(allPlayerIds);
    const startingXICount = 1 + // GK
        (proposedPlayersData.defenders?.length || 0) +
        (proposedPlayersData.midfielders?.length || 0) +
        (proposedPlayersData.forwards?.length || 0);
    
    const html = `
        <div class="propose-players-section">
            <!-- Formation Info -->
            <div class="section-header">
                <div>
                    <h2>Proposed Formation: ${proposedPlayersData.formation || 'N/A'}</h2>
                    <p class="section-subtitle">Players selected from Best Formation page</p>
                </div>
                <button id="clear-proposal-btn" class="clear-btn">Clear Proposal</button>
            </div>
            
            <!-- Summary -->
            <div class="proposed-count">
                <div>
                    <strong>Total Players:</strong> ${allPlayerIds.length}
                    <span style="margin-left: 20px;">Starting XI: ${startingXICount}</span>
                    <span style="margin-left: 20px;">Bench: ${proposedPlayersData.bench?.length || 0}</span>
                </div>
                <div>
                    <strong>Total Value:</strong> £${totalValue.toFixed(1)}m
                </div>
            </div>
            
            <!-- Goalkeeper -->
            ${displayPositionSection('Goalkeeper', [proposedPlayersData.goalkeeper].filter(id => id), 1)}
            
            <!-- Defenders -->
            ${displayPositionSection('Defenders', proposedPlayersData.defenders || [], 2)}
            
            <!-- Midfielders -->
            ${displayPositionSection('Midfielders', proposedPlayersData.midfielders || [], 3)}
            
            <!-- Forwards -->
            ${displayPositionSection('Forwards', proposedPlayersData.forwards || [], 4)}
            
            <!-- Bench -->
            ${displayPositionSection('Bench', proposedPlayersData.bench || [], null)}
        </div>
    `;
    
    container.innerHTML = html;
    
    // Attach clear button listener
    attachClearButton();
}

/**
 * Display a position section
 */
function displayPositionSection(title, playerIds, positionId) {
    if (!playerIds || playerIds.length === 0) {
        return '';
    }
    
    const players = playerIds
        .map(id => allPlayersData[id])
        .filter(p => p !== undefined && p !== null);
    
    if (players.length === 0) {
        return `
            <div class="position-section">
                <h3 class="position-title">${title}</h3>
                <p class="no-players">No players found for this position</p>
            </div>
        `;
    }
    
    const playersList = players.map(player => createPlayerCard(player, positionId)).join('');
    
    return `
        <div class="position-section">
            <h3 class="position-title">${title} (${players.length})</h3>
            <div class="players-proposal-list">
                ${playersList}
            </div>
        </div>
    `;
}

/**
 * Create a player card
 */
function createPlayerCard(player, positionId) {
    const positionNames = {
        1: 'GK',
        2: 'DEF',
        3: 'MID',
        4: 'FWD',
        null: 'BENCH'
    };
    
    const positionName = positionNames[positionId] || 'UNK';
    
    // Calculate value metrics
    const price = (player.now_cost || 0) * 0.1;
    const pointsPerMillion = player.total_points && price > 0 
        ? (player.total_points / price).toFixed(2) 
        : '0.00';
    
    return `
        <div class="player-proposal-card">
            <div class="player-card-header">
                <div class="player-main-info">
                    <h4 class="player-name">${player.web_name || player.first_name + ' ' + player.second_name}</h4>
                    <div style="margin-top: 8px;">
                        <span class="player-team-name">${player.team_short_name || player.team_name}</span>
                        <span class="player-position">${positionName}</span>
                    </div>
                </div>
                <div class="propose-controls">
                    <label class="propose-checkbox">
                        <input type="checkbox" class="propose-player-checkbox" data-player-id="${player.id}" checked>
                        <span>Propose</span>
                    </label>
                </div>
            </div>
            
            <div class="player-stats-grid">
                <div class="stat-item">
                    <span class="stat-label">Price</span>
                    <span class="stat-value">£${price.toFixed(1)}m</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Total Points</span>
                    <span class="stat-value">${player.total_points || 0}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Last 5 Games</span>
                    <span class="stat-value">${player.last_5_games_points || 0}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Points/£M</span>
                    <span class="stat-value">${pointsPerMillion}</span>
                </div>
            </div>
            
            <div class="player-stats-grid" style="margin-top: 10px;">
                <div class="stat-item">
                    <span class="stat-label">Goals</span>
                    <span class="stat-value">${player.goals_scored || 0}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Assists</span>
                    <span class="stat-value">${player.assists || 0}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Clean Sheets</span>
                    <span class="stat-value">${player.clean_sheets || 0}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Form</span>
                    <span class="stat-value">${player.form || '0.0'}</span>
                </div>
            </div>
            
            ${player.ict_index ? `
                <div class="player-stats-grid" style="margin-top: 10px;">
                    <div class="stat-item">
                        <span class="stat-label">ICT Index</span>
                        <span class="stat-value">${parseFloat(player.ict_index || 0).toFixed(1)}</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Selected By</span>
                        <span class="stat-value">${parseFloat(player.selected_by_percent || 0).toFixed(1)}%</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Points Per Game</span>
                        <span class="stat-value">${parseFloat(player.points_per_game || 0).toFixed(1)}</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Status</span>
                        <span class="stat-value">${getStatusText(player)}</span>
                    </div>
                </div>
            ` : ''}
        </div>
    `;
}

/**
 * Get status text for player
 */
function getStatusText(player) {
    if (player.status && player.status !== 'a') {
        return player.status.toUpperCase();
    }
    if (player.chance_of_playing_this_round && player.chance_of_playing_this_round < 100) {
        return `${player.chance_of_playing_this_round}%`;
    }
    if (player.news) {
        return '⚠ News';
    }
    return 'Available';
}

/**
 * Calculate total value of players
 */
function calculateTotalValue(playerIds) {
    return playerIds.reduce((total, id) => {
        const player = allPlayersData[id];
        if (player && player.now_cost) {
            return total + (player.now_cost * 0.1);
        }
        return total;
    }, 0);
}

/**
 * Show no players message
 */
function showNoPlayersMessage() {
    const container = document.getElementById('propose-players-container');
    container.innerHTML = `
        <div class="info-message">
            <h3>No Players Proposed Yet</h3>
            <p>
                Go to <a href="/best-formation">Best Formation</a> page to select players and transfer them here.
            </p>
            <p style="margin-top: 15px;">
                Select your formation and players, then click "Transfer Selected Players to Propose Players Page".
            </p>
        </div>
    `;
}

/**
 * Show error message
 */
function showErrorMessage(message) {
    const container = document.getElementById('propose-players-container');
    container.innerHTML = `
        <div class="error-message">
            ${message}
        </div>
    `;
}

/**
 * Attach clear button listener
 */
function attachClearButton() {
    const btn = document.getElementById('clear-proposal-btn');
    if (btn) {
        btn.addEventListener('click', () => {
            if (confirm('Are you sure you want to clear the proposed players? This will remove all selections.')) {
                localStorage.removeItem(PROPOSE_PLAYERS_STORAGE_KEY);
                proposedPlayersData = null;
                showNoPlayersMessage();
            }
        });
    }
    
    // Attach refresh button
    const refreshBtn = document.getElementById('refresh-proposal-btn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            refreshBtn.disabled = true;
            refreshBtn.innerHTML = '<span>⏳</span> Refreshing...';
            loadProposedPlayers();
            setTimeout(() => {
                refreshBtn.disabled = false;
                refreshBtn.innerHTML = '<span>🔄</span> Refresh from Best Formation';
            }, 1000);
        });
    }
}
