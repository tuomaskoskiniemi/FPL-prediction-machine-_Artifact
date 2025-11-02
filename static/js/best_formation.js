/**
 * Best Formation Page JavaScript
 * Handles formation comparison, team value calculation, and player selection for formations
 */

const API_PLAYERS = '/api/players/top-by-position';
const SELECTED_PLAYERS_STORAGE_KEY = 'fpl_selected_players';
const PROPOSE_PLAYERS_STORAGE_KEY = 'fpl_propose_players';

// Formation definitions: [GK, DEF, MID, FWD]
const FORMATIONS = {
    '3-4-3': { def: 3, mid: 4, fwd: 3, name: '3-4-3' },
    '4-4-2': { def: 4, mid: 4, fwd: 2, name: '4-4-2' },
    '4-3-3': { def: 4, mid: 3, fwd: 3, name: '4-3-3' },
    '3-5-2': { def: 3, mid: 5, fwd: 2, name: '3-5-2' },
    '5-3-2': { def: 5, mid: 3, fwd: 2, name: '5-3-2' },
    '5-4-1': { def: 5, mid: 4, fwd: 1, name: '5-4-1' },
    '4-5-1': { def: 4, mid: 5, fwd: 1, name: '4-5-1' }
};

let allPlayersData = {};
let selectedPlayersFromAnalysis = {
    goalkeepers: [],
    defenders: [],
    midfielders: [],
    forwards: []
};

let formationSelection = {
    goalkeeper: null,
    defenders: [],
    midfielders: [],
    forwards: [],
    bench: []
};

document.addEventListener('DOMContentLoaded', () => {
    // Load selected players first
    loadSelectedPlayersFromAnalysis();
    // Then fetch player data (which will also trigger display)
    fetchPlayersData().then(() => {
        // After data is loaded, set up UI
        attachFormationSelector();
        attachTransferButton();
        attachRefreshButton();
    });
    
    // Listen for storage changes to update when players are selected on Player Analysis page
    window.addEventListener('storage', handleStorageChange);
    
    // Also listen for visibility change to refresh when navigating back to this page
    document.addEventListener('visibilitychange', () => {
        if (!document.hidden) {
            refreshPlayerData();
        }
    });
    
    // Refresh when page becomes visible (handles same-tab navigation)
    window.addEventListener('pageshow', (event) => {
        if (event.persisted || (performance.getEntriesByType && performance.getEntriesByType('navigation')[0]?.type === 'back_forward')) {
            refreshPlayerData();
        }
    });
    
    // Also use a polling mechanism to detect localStorage changes within the same tab
    // (storage event only fires for cross-tab changes)
    let lastSelectedPlayersData = localStorage.getItem(SELECTED_PLAYERS_STORAGE_KEY) || '{}';
    setInterval(() => {
        const current = localStorage.getItem(SELECTED_PLAYERS_STORAGE_KEY) || '{}';
        if (current !== lastSelectedPlayersData) {
            console.log('Detected localStorage change, refreshing...');
            lastSelectedPlayersData = current;
            refreshPlayerData();
        }
    }, 1000); // Check every second
});

/**
 * Load selected players from Player Analysis page
 */
function loadSelectedPlayersFromAnalysis() {
    try {
        const stored = localStorage.getItem(SELECTED_PLAYERS_STORAGE_KEY);
        console.log('Loading from localStorage:', SELECTED_PLAYERS_STORAGE_KEY, stored);
        
        if (stored) {
            const data = JSON.parse(stored);
            console.log('Parsed localStorage data:', data);
            
            const previousCount = getTotalSelectedCount();
            
            selectedPlayersFromAnalysis = {
                goalkeepers: Array.isArray(data.goalkeepers) ? data.goalkeepers : [],
                defenders: Array.isArray(data.defenders) ? data.defenders : [],
                midfielders: Array.isArray(data.midfielders) ? data.midfielders : [],
                forwards: Array.isArray(data.forwards) ? data.forwards : []
            };
            
            const newCount = getTotalSelectedCount();
            console.log(`Loaded ${newCount} players:`, selectedPlayersFromAnalysis);
            
            // Show notification if new players were added
            if (newCount > previousCount && previousCount > 0) {
                showTransferNotification(newCount - previousCount);
            }
            
            return true;
        } else {
            console.log('No data found in localStorage for', SELECTED_PLAYERS_STORAGE_KEY);
        }
    } catch (error) {
        console.error('Error loading selected players:', error);
        console.error('Error stack:', error.stack);
    }
    return false;
}

/**
 * Get total count of selected players
 */
function getTotalSelectedCount() {
    return (selectedPlayersFromAnalysis.goalkeepers?.length || 0) +
           (selectedPlayersFromAnalysis.defenders?.length || 0) +
           (selectedPlayersFromAnalysis.midfielders?.length || 0) +
           (selectedPlayersFromAnalysis.forwards?.length || 0);
}

/**
 * Handle storage change events (when localStorage is updated from another tab/window)
 */
function handleStorageChange(e) {
    if (e.key === SELECTED_PLAYERS_STORAGE_KEY) {
        console.log('Player selection updated in localStorage, refreshing...');
        refreshPlayerData();
    }
}

/**
 * Refresh player data from localStorage and update display
 */
function refreshPlayerData() {
    const hadData = Object.keys(allPlayersData).length > 0;
    
    if (loadSelectedPlayersFromAnalysis() || hadData) {
        // If we already have player data, just refresh the display
        if (Object.keys(allPlayersData).length > 0) {
            displayFormations();
            displaySelectedPlayers();
            updateTeamValue();
            
            // Re-render formation builder if it exists
            const formationSelect = document.getElementById('formation-select');
            if (formationSelect) {
                renderFormationBuilder(formationSelect.value);
            }
        } else {
            // Otherwise fetch all data
            fetchPlayersData();
        }
    }
}

/**
 * Show notification when players are transferred
 */
function showTransferNotification(count) {
    // Create a temporary notification banner
    const notification = document.createElement('div');
    notification.className = 'transfer-notification';
    notification.innerHTML = `
        <div class="transfer-notification-content">
            <span class="transfer-notification-icon">✓</span>
            <span class="transfer-notification-text">${count} new player(s) loaded from Player Analysis!</span>
            <button class="transfer-notification-close">&times;</button>
        </div>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        notification.classList.add('fade-out');
        setTimeout(() => notification.remove(), 300);
    }, 5000);
    
    // Manual close
    notification.querySelector('.transfer-notification-close').addEventListener('click', () => {
        notification.classList.add('fade-out');
        setTimeout(() => notification.remove(), 300);
    });
}

/**
 * Fetch all players data
 */
async function fetchPlayersData() {
    const container = document.getElementById('formations-container');
    
    try {
        console.log('Fetching players from API:', API_PLAYERS);
        const response = await fetch(API_PLAYERS);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
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
            if (player && player.id !== undefined && player.id !== null) {
                allPlayersData[player.id] = player;
            }
        });
        
        console.log(`Loaded ${Object.keys(allPlayersData).length} players from API`);
        console.log('Selected players from analysis:', selectedPlayersFromAnalysis);
        console.log('Player IDs in selected players:', {
            goalkeepers: selectedPlayersFromAnalysis.goalkeepers,
            defenders: selectedPlayersFromAnalysis.defenders,
            midfielders: selectedPlayersFromAnalysis.midfielders,
            forwards: selectedPlayersFromAnalysis.forwards
        });
        
        // Display everything
        displayFormations();
        displaySelectedPlayers();
        updateTeamValue();
        
        return true;
    } catch (error) {
        console.error('Error fetching players:', error);
        if (container) {
            container.innerHTML = 
                `<div class="error-message">Error loading data: ${error.message}</div>`;
        }
        return false;
    }
}

/**
 * Display formation comparison cards
 */
function displayFormations() {
    const container = document.getElementById('formations-container');
    
    if (!container) {
        console.error('Formations container not found');
        return;
    }
    
    // Check if we have player data
    if (Object.keys(allPlayersData).length === 0) {
        container.innerHTML = '<div class="loading-placeholder">Loading player data to calculate formations...</div>';
        return;
    }
    
    try {
        // Calculate points for each formation
        const formationsData = Object.keys(FORMATIONS).map(formationKey => {
            const formation = FORMATIONS[formationKey];
            const points = calculateFormationPoints(formation);
            return {
                key: formationKey,
                name: formation.name,
                def: formation.def,
                mid: formation.mid,
                fwd: formation.fwd,
                points: points
            };
        });
        
        // Sort by points descending
        formationsData.sort((a, b) => b.points - a.points);
        
        const html = formationsData.map(formation => {
            const isBest = formation.points === formationsData[0].points;
            return `
                <div class="formation-card ${isBest ? 'best-formation' : ''}">
                    <div class="formation-card-header">
                        <h3>${formation.name}</h3>
                        ${isBest ? '<span class="best-badge">Best</span>' : ''}
                    </div>
                    <div class="formation-structure">
                        <div class="formation-stats">
                            <span class="stat-item">DEF: ${formation.def}</span>
                            <span class="stat-item">MID: ${formation.mid}</span>
                            <span class="stat-item">FWD: ${formation.fwd}</span>
                        </div>
                    </div>
                    <div class="formation-points">
                        <div class="points-label">Total Points</div>
                        <div class="points-value">${formation.points.toFixed(1)}</div>
                    </div>
                </div>
            `;
        }).join('');
        
        container.innerHTML = html;
        console.log('Formations displayed:', formationsData.length);
    } catch (error) {
        console.error('Error displaying formations:', error);
        container.innerHTML = `<div class="error-message">Error calculating formations: ${error.message}</div>`;
    }
}

/**
 * Calculate formation points based on selected players
 */
function calculateFormationPoints(formation) {
    let totalPoints = 0;
    
    try {
        // Get top players for each position
        const topGK = getTopPlayersByPosition(1, 1);
        const topDEF = getTopPlayersByPosition(2, formation.def);
        const topMID = getTopPlayersByPosition(3, formation.mid);
        const topFWD = getTopPlayersByPosition(4, formation.fwd);
        
        // Sum points from last 5 games (or total points if not available)
        topGK.forEach(player => {
            if (player) {
                totalPoints += parseFloat(player.last_5_games_points) || parseFloat(player.total_points) || 0;
            }
        });
        
        topDEF.forEach(player => {
            if (player) {
                totalPoints += parseFloat(player.last_5_games_points) || parseFloat(player.total_points) || 0;
            }
        });
        
        topMID.forEach(player => {
            if (player) {
                totalPoints += parseFloat(player.last_5_games_points) || parseFloat(player.total_points) || 0;
            }
        });
        
        topFWD.forEach(player => {
            if (player) {
                totalPoints += parseFloat(player.last_5_games_points) || parseFloat(player.total_points) || 0;
            }
        });
    } catch (error) {
        console.error('Error calculating formation points:', error);
        return 0;
    }
    
    return totalPoints;
}

/**
 * Get top players by position from available players
 */
function getTopPlayersByPosition(positionId, count) {
    if (!positionId || count <= 0) {
        return [];
    }
    
    try {
        const positionKey = getPositionKey(positionId);
        const selectedIds = selectedPlayersFromAnalysis[positionKey] || [];
        
        // Get player objects for selected IDs
        let selectedPlayers = selectedIds
            .map(id => {
                const player = allPlayersData[id];
                if (player && player.element_type === positionId) {
                    return player;
                }
                return null;
            })
            .filter(p => p !== null)
            .sort((a, b) => {
                const pointsA = parseFloat(a.last_5_games_points) || parseFloat(a.total_points) || 0;
                const pointsB = parseFloat(b.last_5_games_points) || parseFloat(b.total_points) || 0;
                return pointsB - pointsA;
            })
            .slice(0, count);
        
        // If we don't have enough selected, get top players from all data
        if (selectedPlayers.length < count) {
            const allPositionPlayers = Object.values(allPlayersData)
                .filter(p => p && p.element_type === positionId)
                .sort((a, b) => {
                    const pointsA = parseFloat(a.last_5_games_points) || parseFloat(a.total_points) || 0;
                    const pointsB = parseFloat(b.last_5_games_points) || parseFloat(b.total_points) || 0;
                    return pointsB - pointsA;
                });
            
            // Combine selected and top available, remove duplicates
            const combined = [...selectedPlayers];
            const selectedIdsSet = new Set(selectedPlayers.map(p => p.id));
            
            for (const player of allPositionPlayers) {
                if (combined.length >= count) break;
                if (!selectedIdsSet.has(player.id)) {
                    combined.push(player);
                }
            }
            return combined.slice(0, count);
        }
        
        return selectedPlayers;
    } catch (error) {
        console.error(`Error getting top players for position ${positionId}:`, error);
        return [];
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
 * Display selected players from Player Analysis
 */
function displaySelectedPlayers() {
    const container = document.getElementById('selected-players-display');
    
    if (!container) {
        console.error('Selected players display container not found');
        return;
    }
    
    // Check if we have selected players
    const hasSelectedPlayers = selectedPlayersFromAnalysis && (
        (selectedPlayersFromAnalysis.goalkeepers && selectedPlayersFromAnalysis.goalkeepers.length > 0) ||
        (selectedPlayersFromAnalysis.defenders && selectedPlayersFromAnalysis.defenders.length > 0) ||
        (selectedPlayersFromAnalysis.midfielders && selectedPlayersFromAnalysis.midfielders.length > 0) ||
        (selectedPlayersFromAnalysis.forwards && selectedPlayersFromAnalysis.forwards.length > 0)
    );
    
    if (!hasSelectedPlayers) {
        container.innerHTML = `
            <div class="info-message">
                No players selected yet. Go to <a href="/player-analysis">Player Analysis</a> to select players.
            </div>
        `;
        return;
    }
    
    // Check if we have player data loaded
    if (Object.keys(allPlayersData).length === 0) {
        container.innerHTML = `
            <div class="loading-placeholder">Loading player details...</div>
        `;
        // Fetch player data if not loaded yet (async, will update display when done)
        fetchPlayersData();
        return;
    }
    
    const html = `
        <div class="selected-players-by-position-grid">
            ${displayPositionPlayers('Goalkeepers', selectedPlayersFromAnalysis.goalkeepers || [], 1)}
            ${displayPositionPlayers('Defenders', selectedPlayersFromAnalysis.defenders || [], 2)}
            ${displayPositionPlayers('Midfielders', selectedPlayersFromAnalysis.midfielders || [], 3)}
            ${displayPositionPlayers('Forwards', selectedPlayersFromAnalysis.forwards || [], 4)}
        </div>
    `;
    
    container.innerHTML = html;
}

/**
 * Display players for a position
 */
function displayPositionPlayers(title, playerIds, positionId) {
    if (!playerIds || playerIds.length === 0) {
        return `
            <div class="selected-position-card">
                <h4>${title}</h4>
                <p class="no-players-text">No ${title.toLowerCase()} selected</p>
            </div>
        `;
    }
    
    // Ensure playerIds is an array
    const idsArray = Array.isArray(playerIds) ? playerIds : [];
    
    // Get players from allPlayersData
    const players = idsArray
        .map(id => {
            const player = allPlayersData[id];
            if (!player) {
                console.warn(`Player with ID ${id} not found in allPlayersData`);
                return null;
            }
            // Verify position matches (but be flexible if positionId is not available)
            if (positionId && player.element_type !== positionId) {
                console.warn(`Player ${player.web_name} (ID: ${id}) position mismatch. Expected: ${positionId}, Got: ${player.element_type}`);
                // Still include the player if position matches (might be a data issue)
            }
            return player;
        })
        .filter(p => p !== null && p !== undefined);
    
    if (players.length === 0) {
        // Show message indicating which player IDs were not found
        return `
            <div class="selected-position-card">
                <h4>${title}</h4>
                <p class="no-players-text">No ${title.toLowerCase()} found in player data</p>
                <p class="no-players-text" style="font-size: 0.85rem; color: #999;">Looking for IDs: ${idsArray.join(', ')}</p>
            </div>
        `;
    }
    
    const playersList = players.map(player => `
        <div class="selected-player-item-card">
            <div class="player-card-info">
                <strong>${player.web_name || player.first_name + ' ' + player.second_name}</strong>
                <span class="player-card-team">${player.team_short_name || player.team_name || ''}</span>
            </div>
            <div class="player-card-stats">
                <span class="player-card-price">£${safeToFixed(player.now_cost, 1)}m</span>
                <span class="player-card-points">${safeToFixed(player.last_5_games_points || player.total_points || 0, 1)} pts</span>
            </div>
        </div>
    `).join('');
    
    return `
        <div class="selected-position-card">
            <h4>${title} (${players.length})</h4>
            <div class="selected-players-list-cards">
                ${playersList}
            </div>
        </div>
    `;
}

/**
 * Safely format a number to fixed decimal places (same as Player Analysis)
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
 * Update team value display
 */
function updateTeamValue() {
    // Calculate from formation selection
    let totalValue = 0;
    let startingXIValue = 0;
    
    if (formationSelection.goalkeeper) {
        const player = allPlayersData[formationSelection.goalkeeper];
        if (player) {
            const value = parseFloat(player.now_cost || 0);
            totalValue += value;
            startingXIValue += value;
        }
    }
    
    [...formationSelection.defenders, ...formationSelection.midfielders, ...formationSelection.forwards].forEach(playerId => {
        const player = allPlayersData[playerId];
        if (player) {
            const value = parseFloat(player.now_cost || 0);
            totalValue += value;
            startingXIValue += value;
        }
    });
    
    formationSelection.bench.forEach(playerId => {
        const player = allPlayersData[playerId];
        if (player) {
            totalValue += parseFloat(player.now_cost || 0);
        }
    });
    
    const benchValue = totalValue - startingXIValue;
    
    document.getElementById('total-team-value').textContent = `£${totalValue.toFixed(1)}m`;
    document.getElementById('starting-xi-value').textContent = `£${startingXIValue.toFixed(1)}m`;
    document.getElementById('bench-value').textContent = `£${benchValue.toFixed(1)}m`;
}

/**
 * Attach formation selector listener
 */
function attachFormationSelector() {
    const selector = document.getElementById('formation-select');
    if (selector) {
        selector.addEventListener('change', (e) => {
            renderFormationBuilder(e.target.value);
        });
        
        // Initial render
        renderFormationBuilder(selector.value);
    }
}

/**
 * Render formation builder interface
 */
function renderFormationBuilder(formationKey) {
    const container = document.getElementById('formation-builder');
    const formation = FORMATIONS[formationKey];
    
    if (!formation) return;
    
    // Get available players for each position
    const availableGK = getPlayersForPosition(1);
    const availableDEF = getPlayersForPosition(2);
    const availableMID = getPlayersForPosition(3);
    const availableFWD = getPlayersForPosition(4);
    
    const html = `
        <div class="formation-builder-content">
            <div class="formation-pitch">
                <div class="position-slot-group">
                    <h4>Goalkeeper (1)</h4>
                    ${renderPositionSlot('goalkeeper', availableGK, 1)}
                </div>
                
                <div class="position-slot-group">
                    <h4>Defenders (${formation.def})</h4>
                    ${Array.from({ length: formation.def }, (_, i) => 
                        renderPositionSlot(`defender-${i}`, availableDEF, 2, i)
                    ).join('')}
                </div>
                
                <div class="position-slot-group">
                    <h4>Midfielders (${formation.mid})</h4>
                    ${Array.from({ length: formation.mid }, (_, i) => 
                        renderPositionSlot(`midfielder-${i}`, availableMID, 3, i)
                    ).join('')}
                </div>
                
                <div class="position-slot-group">
                    <h4>Forwards (${formation.fwd})</h4>
                    ${Array.from({ length: formation.fwd }, (_, i) => 
                        renderPositionSlot(`forward-${i}`, availableFWD, 4, i)
                    ).join('')}
                </div>
                
                <div class="position-slot-group">
                    <h4>Bench (4 players)</h4>
                    ${Array.from({ length: 4 }, (_, i) => 
                        renderPositionSlot(`bench-${i}`, [...availableGK, ...availableDEF, ...availableMID, ...availableFWD], null, i)
                    ).join('')}
                </div>
            </div>
        </div>
    `;
    
    container.innerHTML = html;
    
    // Attach slot selection listeners
    attachSlotSelectionListeners();
}

/**
 * Get players for a position
 */
function getPlayersForPosition(positionId) {
    const positionKey = getPositionKey(positionId);
    const selectedIds = selectedPlayersFromAnalysis[positionKey] || [];
    
    // Start with selected players
    const players = selectedIds
        .map(id => allPlayersData[id])
        .filter(p => p && p.element_type === positionId);
    
    // Add top players from all data if needed
    const allPositionPlayers = Object.values(allPlayersData)
        .filter(p => p && p.element_type === positionId)
        .sort((a, b) => {
            const pointsA = a.last_5_games_points || a.total_points || 0;
            const pointsB = b.last_5_games_points || b.total_points || 0;
            return pointsB - pointsA;
        });
    
    // Combine, removing duplicates
    const combined = [...players];
    for (const player of allPositionPlayers) {
        if (combined.length >= 20) break; // Limit to 20 options
        if (!combined.find(p => p.id === player.id)) {
            combined.push(player);
        }
    }
    
    return combined.slice(0, 20);
}

/**
 * Render a position slot
 */
function renderPositionSlot(slotKey, availablePlayers, positionId, index) {
    const currentSelection = getCurrentSelectionForSlot(slotKey);
    const selectedPlayer = currentSelection ? allPlayersData[currentSelection] : null;
    
    return `
        <div class="position-slot" data-slot="${slotKey}" data-position-id="${positionId || ''}">
            <select class="player-slot-select" data-slot="${slotKey}">
                <option value="">-- Select Player --</option>
                ${availablePlayers.map(player => {
                    const selected = currentSelection === player.id ? 'selected' : '';
                    return `<option value="${player.id}" ${selected}>${player.web_name || player.first_name + ' ' + player.second_name} (${player.team_short_name || player.team_name}) - £${safeToFixed(player.now_cost, 1)}m</option>`;
                }).join('')}
            </select>
            ${selectedPlayer ? `
                <div class="selected-player-display">
                    <strong>${selectedPlayer.web_name || selectedPlayer.first_name + ' ' + selectedPlayer.second_name}</strong>
                    <span>${selectedPlayer.team_short_name || selectedPlayer.team_name || ''}</span>
                    <span class="player-price-display">£${safeToFixed(selectedPlayer.now_cost, 1)}m</span>
                </div>
            ` : ''}
        </div>
    `;
}

/**
 * Get current selection for a slot
 */
function getCurrentSelectionForSlot(slotKey) {
    if (slotKey === 'goalkeeper') {
        return formationSelection.goalkeeper;
    }
    if (slotKey.startsWith('defender-')) {
        const index = parseInt(slotKey.split('-')[1]);
        return formationSelection.defenders[index];
    }
    if (slotKey.startsWith('midfielder-')) {
        const index = parseInt(slotKey.split('-')[1]);
        return formationSelection.midfielders[index];
    }
    if (slotKey.startsWith('forward-')) {
        const index = parseInt(slotKey.split('-')[1]);
        return formationSelection.forwards[index];
    }
    if (slotKey.startsWith('bench-')) {
        const index = parseInt(slotKey.split('-')[1]);
        return formationSelection.bench[index];
    }
    return null;
}

/**
 * Attach slot selection listeners
 */
function attachSlotSelectionListeners() {
    const selects = document.querySelectorAll('.player-slot-select');
    selects.forEach(select => {
        select.addEventListener('change', (e) => {
            const slotKey = e.target.dataset.slot;
            const playerId = e.target.value ? parseInt(e.target.value) : null;
            
            updateSlotSelection(slotKey, playerId);
            updateTeamValue();
            renderFormationBuilder(document.getElementById('formation-select').value);
        });
    });
}

/**
 * Update slot selection
 */
function updateSlotSelection(slotKey, playerId) {
    if (slotKey === 'goalkeeper') {
        formationSelection.goalkeeper = playerId;
    } else if (slotKey.startsWith('defender-')) {
        const index = parseInt(slotKey.split('-')[1]);
        if (!formationSelection.defenders) formationSelection.defenders = [];
        formationSelection.defenders[index] = playerId;
    } else if (slotKey.startsWith('midfielder-')) {
        const index = parseInt(slotKey.split('-')[1]);
        if (!formationSelection.midfielders) formationSelection.midfielders = [];
        formationSelection.midfielders[index] = playerId;
    } else if (slotKey.startsWith('forward-')) {
        const index = parseInt(slotKey.split('-')[1]);
        if (!formationSelection.forwards) formationSelection.forwards = [];
        formationSelection.forwards[index] = playerId;
    } else if (slotKey.startsWith('bench-')) {
        const index = parseInt(slotKey.split('-')[1]);
        if (!formationSelection.bench) formationSelection.bench = [];
        formationSelection.bench[index] = playerId;
    }
}

/**
 * Attach transfer button listener
 */
function attachTransferButton() {
    const btn = document.getElementById('transfer-to-propose-btn');
    if (btn) {
        btn.addEventListener('click', () => {
            transferToProposePlayers();
        });
    }
}

/**
 * Attach refresh button listener
 */
function attachRefreshButton() {
    const btn = document.getElementById('refresh-players-btn');
    if (btn) {
        btn.addEventListener('click', () => {
            btn.disabled = true;
            btn.innerHTML = '<span>⏳</span> Refreshing...';
            refreshPlayerData();
            setTimeout(() => {
                btn.disabled = false;
                btn.innerHTML = '<span>🔄</span> Refresh';
            }, 1000);
        });
    }
}

/**
 * Transfer selected players to Propose Players page
 */
function transferToProposePlayers() {
    // Collect all selected players
    const proposePlayers = {
        formation: document.getElementById('formation-select').value,
        goalkeeper: formationSelection.goalkeeper,
        defenders: formationSelection.defenders.filter(id => id),
        midfielders: formationSelection.midfielders.filter(id => id),
        forwards: formationSelection.forwards.filter(id => id),
        bench: formationSelection.bench.filter(id => id),
        selectedAt: new Date().toISOString()
    };
    
    try {
        localStorage.setItem(PROPOSE_PLAYERS_STORAGE_KEY, JSON.stringify(proposePlayers));
        alert('Formation selections have been transferred to Propose Players page!');
    } catch (error) {
        console.error('Error transferring players:', error);
        alert('Error transferring players. Please try again.');
    }
}

