/**
 * Transfers Page JavaScript
 * Handles transfer proposals, budget calculations, and transfer management
 */

const TRANSFER_OUT_STORAGE_KEY = 'fpl_transfers_out';
const TRANSFER_IN_STORAGE_KEY = 'fpl_transfers_in';
const CURRENT_TEAM_STORAGE_KEY = 'fpl_current_team_id';

// State
let playersToTransferOut = [];
let playersToTransferIn = [];
let currentTeamPlayers = {};
let allPlayersData = {};
let currentTeamData = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadTransferData();
    loadCurrentTeam();
    fetchAllPlayersData().then(() => {
        displayPlayerPickMenu();
    });
    attachEventListeners();
    updateTransferDisplay();
    updateBudgetCalculator();
    
    // Listen for storage events (when transfers are updated from other pages)
    window.addEventListener('storage', handleStorageChange);
    
    // Poll for localStorage changes (same-tab detection)
    setInterval(checkLocalStorageChanges, 500);
});

/**
 * Check for localStorage changes
 */
let lastTransferOutData = localStorage.getItem(TRANSFER_OUT_STORAGE_KEY) || '[]';
let lastTransferInData = localStorage.getItem(TRANSFER_IN_STORAGE_KEY) || '[]';

function checkLocalStorageChanges() {
    const currentOut = localStorage.getItem(TRANSFER_OUT_STORAGE_KEY) || '[]';
    const currentIn = localStorage.getItem(TRANSFER_IN_STORAGE_KEY) || '[]';
    
    if (currentOut !== lastTransferOutData || currentIn !== lastTransferInData) {
        console.log('Detected localStorage change, refreshing transfers...');
        loadTransferData();
        updateTransferDisplay();
        lastTransferOutData = currentOut;
        lastTransferInData = currentIn;
    }
}

/**
 * Handle storage change events
 */
function handleStorageChange(e) {
    if (e.key === TRANSFER_OUT_STORAGE_KEY || e.key === TRANSFER_IN_STORAGE_KEY) {
        console.log('Transfer data updated in localStorage, refreshing...');
        loadTransferData();
        updateTransferDisplay();
    }
}

/**
 * Load transfer data from localStorage
 */
function loadTransferData() {
    try {
        const storedOut = localStorage.getItem(TRANSFER_OUT_STORAGE_KEY);
        playersToTransferOut = storedOut ? JSON.parse(storedOut) : [];
        
        const storedIn = localStorage.getItem(TRANSFER_IN_STORAGE_KEY);
        playersToTransferIn = storedIn ? JSON.parse(storedIn) : [];
    } catch (error) {
        console.error('Error loading transfer data:', error);
        playersToTransferOut = [];
        playersToTransferIn = [];
    }
}

/**
 * Save transfer data to localStorage
 */
function saveTransferData() {
    try {
        localStorage.setItem(TRANSFER_OUT_STORAGE_KEY, JSON.stringify(playersToTransferOut));
        localStorage.setItem(TRANSFER_IN_STORAGE_KEY, JSON.stringify(playersToTransferIn));
        lastTransferOutData = JSON.stringify(playersToTransferOut);
        lastTransferInData = JSON.stringify(playersToTransferIn);
    } catch (error) {
        console.error('Error saving transfer data:', error);
    }
}

/**
 * Load current team data if available
 */
async function loadCurrentTeam() {
    try {
        const storedTeamId = localStorage.getItem(CURRENT_TEAM_STORAGE_KEY);
        if (storedTeamId) {
            const teamId = parseInt(storedTeamId);
            const response = await fetch(`/api/team/${teamId}`);
            if (response.ok) {
                const teamData = await response.json();
                if (teamData.success) {
                    currentTeamData = teamData;
                    const allPicks = teamData.all_picks || [];
                    currentTeamPlayers = {};
                    allPicks.forEach(pick => {
                        const player = pick.player;
                        if (player) {
                    // Normalize player data: team API returns raw FPL data where now_cost is in tenths
                    // Convert to millions to match the format from /api/players endpoints
                    const normalizedPlayer = {
                        ...player,
                        pick: pick,
                        isInTeam: true
                    };
                    
                    // If now_cost > 20, it's likely in tenths (raw FPL format), convert to millions
                    if (normalizedPlayer.now_cost && normalizedPlayer.now_cost > 20) {
                        normalizedPlayer.now_cost = normalizedPlayer.now_cost / 10.0;
                    }
                    
                    // Ensure team_short_name and web_name exist (from raw data, these might be different)
                    if (!normalizedPlayer.team_short_name && pick.team_short_name) {
                        normalizedPlayer.team_short_name = pick.team_short_name;
                    }
                    if (!normalizedPlayer.team_name && pick.team_name) {
                        normalizedPlayer.team_name = pick.team_name;
                    }
                    
                    currentTeamPlayers[player.id] = normalizedPlayer;
                        }
                    });
                    
                    // Update budget calculator after loading team
                    updateBudgetCalculator();
                }
            }
        }
    } catch (error) {
        console.error('Error loading current team:', error);
    }
}

/**
 * Fetch all players data
 */
async function fetchAllPlayersData() {
    try {
        const response = await fetch('/api/players/all');
        const data = await response.json();
        
        if (data.success && data.players) {
            allPlayersData = {};
            data.players.forEach(player => {
                allPlayersData[player.id] = player;
            });
            return Promise.resolve();
        } else {
            // Fallback to top-by-position endpoint
            const fallbackResponse = await fetch('/api/players/top-by-position');
            const fallbackData = await fallbackResponse.json();
            
            if (fallbackData.success && fallbackData.players) {
                const allPlayers = [
                    ...(fallbackData.players.goalkeepers || []),
                    ...(fallbackData.players.defenders || []),
                    ...(fallbackData.players.midfielders || []),
                    ...(fallbackData.players.forwards || [])
                ];
                
                allPlayersData = {};
                allPlayers.forEach(player => {
                    allPlayersData[player.id] = player;
                });
            }
            return Promise.resolve();
        }
    } catch (error) {
        console.error('Error fetching players data:', error);
        return Promise.reject(error);
    }
}

/**
 * Attach event listeners
 */
function attachEventListeners() {
    const applyBtn = document.getElementById('apply-transfers-btn');
    if (applyBtn) {
        applyBtn.addEventListener('click', handleApplyTransfers);
    }
    
    // Player pick menu filters
    const positionFilter = document.getElementById('position-filter');
    const valueFilter = document.getElementById('value-filter');
    const sortBy = document.getElementById('sort-by');
    const clearFiltersBtn = document.getElementById('clear-filters-btn');
    
    if (positionFilter) {
        positionFilter.addEventListener('change', displayPlayerPickMenu);
    }
    if (valueFilter) {
        valueFilter.addEventListener('change', displayPlayerPickMenu);
    }
    if (sortBy) {
        sortBy.addEventListener('change', displayPlayerPickMenu);
    }
    if (clearFiltersBtn) {
        clearFiltersBtn.addEventListener('click', () => {
            if (positionFilter) positionFilter.value = '';
            if (valueFilter) valueFilter.value = '';
            if (sortBy) sortBy.value = 'value-asc';
            displayPlayerPickMenu();
        });
    }
}

/**
 * Update transfer display
 */
function updateTransferDisplay() {
    updateTransferOutDisplay();
    updateTransferInDisplay();
    updateTransferSummary();
    updateBudgetCalculator();
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
    
    container.innerHTML = playersToTransferOut.map(playerData => {
        // Handle both player ID (number) and player object formats
        const playerId = typeof playerData === 'number' ? playerData : playerData.id;
        const player = typeof playerData === 'object' && playerData !== null 
            ? playerData 
            : (currentTeamPlayers[playerId] || allPlayersData[playerId]);
        
        if (!player) return '';
        
        const team = player.team_name ? { team_name: player.team_name, short_name: player.team_short_name } : {};
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
    
    container.innerHTML = playersToTransferIn.map(playerData => {
        // Handle both player ID (number) and player object formats
        const playerId = typeof playerData === 'number' ? playerData : playerData.id;
        const player = typeof playerData === 'object' && playerData !== null 
            ? playerData 
            : allPlayersData[playerId];
        
        if (!player) return '';
        
        const team = player.team_name ? { team_name: player.team_name, short_name: player.team_short_name } : {};
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
    
    playersToTransferOut.forEach(playerData => {
        const playerId = typeof playerData === 'number' ? playerData : playerData.id;
        const player = typeof playerData === 'object' && playerData !== null 
            ? playerData 
            : (currentTeamPlayers[playerId] || allPlayersData[playerId]);
        
        if (player) {
            // Normalize: ensure now_cost is in millions (data processor format)
            let costInMillions = parseFloat(player.now_cost || 0);
            if (costInMillions > 20) {
                // Raw FPL format (tenths), convert to millions
                costInMillions = costInMillions / 10.0;
            }
            // Convert to tenths for budget calculation
            budgetImpact += costInMillions * 10;
        }
    });
    
    playersToTransferIn.forEach(playerData => {
        const playerId = typeof playerData === 'number' ? playerData : playerData.id;
        const player = typeof playerData === 'object' && playerData !== null 
            ? playerData 
            : allPlayersData[playerId];
        
        if (player) {
            // Normalize: ensure now_cost is in millions (data processor format)
            let costInMillions = parseFloat(player.now_cost || 0);
            if (costInMillions > 20) {
                // Raw FPL format (tenths), convert to millions
                costInMillions = costInMillions / 10.0;
            }
            // Convert to tenths for budget calculation
            budgetImpact -= costInMillions * 10;
        }
    });
    
    const budgetImpactFormatted = (Math.abs(budgetImpact) / 10.0).toFixed(1);
    const budgetColor = budgetImpact >= 0 ? 'success' : 'error';
    
    const budgetEl = document.getElementById('budget-impact');
    if (budgetEl) {
        budgetEl.textContent = `£${budgetImpactFormatted}m`;
        budgetEl.className = `summary-value ${budgetColor}`;
    }
    
    // Update budget impact display
    const budgetImpactDisplay = document.getElementById('budget-impact-display');
    if (budgetImpactDisplay) {
        budgetImpactDisplay.textContent = `£${budgetImpactFormatted}m`;
        budgetImpactDisplay.className = `budget-value ${budgetColor === 'success' ? 'budget-value-success' : 'budget-value-error'}`;
    }
    
    // Enable/disable apply button
    const applyBtn = document.getElementById('apply-transfers-btn');
    if (applyBtn) {
        // Enable if we have transfers and they match in count (one-to-one transfers)
        applyBtn.disabled = (outCount === 0 && inCount === 0) || outCount !== inCount;
    }
}

/**
 * Update budget calculator
 */
function updateBudgetCalculator() {
    // Get current team data
    const currentBudget = currentTeamData && currentTeamData.team ? currentTeamData.team.bank : 0;
    const currentTeamValue = currentTeamData && currentTeamData.team ? currentTeamData.team.total_value : 0;
    
    // Calculate budget impact
    // Note: now_cost is already in millions from the data processor, but budget calculations need tenths
    // So we multiply by 10 to convert back to tenths for budget calculations
    let budgetImpact = 0;
    let transferOutValue = 0;
    let transferInValue = 0;
    
    playersToTransferOut.forEach(playerData => {
        const playerId = typeof playerData === 'number' ? playerData : playerData.id;
        const player = typeof playerData === 'object' && playerData !== null 
            ? playerData 
            : (currentTeamPlayers[playerId] || allPlayersData[playerId]);
        
        if (player) {
            // Normalize: ensure now_cost is in millions
            let valueInMillions = parseFloat(player.now_cost || 0);
            if (valueInMillions > 20) {
                // Raw FPL format (tenths), convert to millions
                valueInMillions = valueInMillions / 10.0;
            }
            transferOutValue += valueInMillions;
            budgetImpact += valueInMillions * 10; // Convert to tenths for budget calculation
        }
    });
    
    playersToTransferIn.forEach(playerData => {
        const playerId = typeof playerData === 'number' ? playerData : playerData.id;
        const player = typeof playerData === 'object' && playerData !== null 
            ? playerData 
            : allPlayersData[playerId];
        
        if (player) {
            // Normalize: ensure now_cost is in millions
            let valueInMillions = parseFloat(player.now_cost || 0);
            if (valueInMillions > 20) {
                // Raw FPL format (tenths), convert to millions
                valueInMillions = valueInMillions / 10.0;
            }
            transferInValue += valueInMillions;
            budgetImpact -= valueInMillions * 10; // Convert to tenths for budget calculation
        }
    });
    
    // Calculate projected values
    const projectedBudget = currentBudget + (budgetImpact / 10.0);
    const projectedTeamValue = currentTeamValue - transferOutValue + transferInValue;
    
    // Update displays
    const currentBudgetEl = document.getElementById('current-budget');
    if (currentBudgetEl) {
        currentBudgetEl.textContent = `£${parseFloat(currentBudget).toFixed(1)}m`;
    }
    
    const currentTeamValueEl = document.getElementById('current-team-value');
    if (currentTeamValueEl) {
        currentTeamValueEl.textContent = `£${parseFloat(currentTeamValue).toFixed(1)}m`;
    }
    
    const projectedBudgetEl = document.getElementById('projected-budget');
    if (projectedBudgetEl) {
        projectedBudgetEl.textContent = `£${projectedBudget.toFixed(1)}m`;
        projectedBudgetEl.className = `budget-value budget-value-highlight ${projectedBudget < 0 ? 'budget-value-error' : 'budget-value-success'}`;
    }
    
    const projectedTeamValueEl = document.getElementById('projected-team-value');
    if (projectedTeamValueEl) {
        projectedTeamValueEl.textContent = `£${projectedTeamValue.toFixed(1)}m`;
    }
}

/**
 * Create transfer card
 */
function createTransferCard(player, team, direction) {
    if (!player) return '';
    
    const positionName = getPositionName(player.element_type || 4);
    // Normalize cost: handle both formats (tenths from team API, millions from player API)
    let costInMillions = parseFloat(player.now_cost || 0);
    if (costInMillions > 20) {
        costInMillions = costInMillions / 10.0; // Convert from tenths to millions
    }
    const price = costInMillions.toFixed(1);
    const teamName = player.team_short_name || player.team_name || (team && (team.short_name || team.team_name)) || '';
    const playerName = player.web_name || 'Unknown';
    
    return `
        <div class="transfer-card ${direction}" data-player-id="${player.id}">
            <div class="transfer-card-header">
                <h4 class="transfer-player-name">${playerName}</h4>
                <button class="remove-transfer-btn" data-player-id="${player.id}" data-direction="${direction}" title="Remove player">×</button>
            </div>
            <div class="transfer-card-info">
                <span class="transfer-player-position">${positionName}</span>
                ${teamName ? `<span class="transfer-player-team">${teamName}</span>` : ''}
                <span class="transfer-player-price">£${price}m</span>
            </div>
        </div>
    `;
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
                removeTransferOut(playerId);
            } else if (dir === 'in') {
                removeTransferIn(playerId);
            }
        });
    });
}

/**
 * Remove player from transfer out
 */
function removeTransferOut(playerId) {
    playersToTransferOut = playersToTransferOut.filter(p => {
        const id = typeof p === 'number' ? p : p.id;
        return id !== playerId;
    });
    saveTransferData();
    updateTransferDisplay();
}

/**
 * Remove player from transfer in
 */
function removeTransferIn(playerId) {
    playersToTransferIn = playersToTransferIn.filter(p => {
        const id = typeof p === 'number' ? p : p.id;
        return id !== playerId;
    });
    saveTransferData();
    updateTransferDisplay();
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
    playersToTransferOut.forEach(playerData => {
        const playerId = typeof playerData === 'number' ? playerData : playerData.id;
        const player = typeof playerData === 'object' && playerData !== null 
            ? playerData 
            : (currentTeamPlayers[playerId] || allPlayersData[playerId]);
        if (player) {
            // Normalize: ensure now_cost is in millions
            let costInMillions = parseFloat(player.now_cost || 0);
            if (costInMillions > 20) {
                costInMillions = costInMillions / 10.0; // Convert from tenths to millions
            }
            // Convert to tenths for budget calculation
            budgetImpact += costInMillions * 10;
        }
    });
    playersToTransferIn.forEach(playerData => {
        const playerId = typeof playerData === 'number' ? playerData : playerData.id;
        const player = typeof playerData === 'object' && playerData !== null 
            ? playerData 
            : allPlayersData[playerId];
        if (player) {
            // Normalize: ensure now_cost is in millions
            let costInMillions = parseFloat(player.now_cost || 0);
            if (costInMillions > 20) {
                costInMillions = costInMillions / 10.0; // Convert from tenths to millions
            }
            // Convert to tenths for budget calculation
            budgetImpact -= costInMillions * 10;
        }
    });
    
    const currentBank = currentTeamData && currentTeamData.team ? currentTeamData.team.bank * 10 : 0; // Convert to tenths
    const newBank = currentBank + budgetImpact;
    
    if (newBank < 0) {
        alert(`Insufficient budget. You would need £${Math.abs(newBank / 10).toFixed(1)}m more.`);
        return;
    }
    
    // Show confirmation
    const confirmMsg = `Transfer ${playersToTransferOut.length} player(s) out and ${playersToTransferIn.length} player(s) in?\n\nBudget impact: £${(budgetImpact / 10).toFixed(1)}m\n${currentTeamData && currentTeamData.team ? `New bank: £${(newBank / 10).toFixed(1)}m` : ''}`;
    
    if (confirm(confirmMsg)) {
        // In a real application, this would send the transfers to the FPL API
        alert('Transfers would be applied here. In the actual implementation, this would call the FPL API to make the transfers.');
        
        // For now, just clear the selections
        playersToTransferOut = [];
        playersToTransferIn = [];
        saveTransferData();
        updateTransferDisplay();
    }
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
 * Public API to add players to transfer lists (can be called from other pages)
 */
window.addToTransferOut = function(playerId) {
    const player = currentTeamPlayers[playerId] || allPlayersData[playerId];
    if (!player) {
        console.warn(`Player ${playerId} not found`);
        return;
    }
    
    // Check if already added
    const exists = playersToTransferOut.some(p => {
        const id = typeof p === 'number' ? p : p.id;
        return id === playerId;
    });
    
    if (!exists) {
        playersToTransferOut.push(player);
        saveTransferData();
        updateTransferDisplay();
    }
};

window.addToTransferIn = function(playerId) {
    const player = allPlayersData[playerId];
    if (!player) {
        console.warn(`Player ${playerId} not found`);
        return;
    }
    
    // Check if already added
    const exists = playersToTransferIn.some(p => {
        const id = typeof p === 'number' ? p : p.id;
        return id === playerId;
    });
    
    if (!exists) {
        playersToTransferIn.push(player);
        saveTransferData();
        updateTransferDisplay();
        displayPlayerPickMenu(); // Refresh to show updated state
    }
};

/**
 * Display player pick menu
 */
function displayPlayerPickMenu() {
    const container = document.getElementById('player-pick-container');
    if (!container) return;
    
    if (Object.keys(allPlayersData).length === 0) {
        container.innerHTML = '<div class="loading-placeholder">Loading players...</div>';
        return;
    }
    
    // Get filter values
    const positionFilter = document.getElementById('position-filter');
    const valueFilter = document.getElementById('value-filter');
    const sortBy = document.getElementById('sort-by');
    
    const selectedPosition = positionFilter ? positionFilter.value : '';
    const selectedValueRange = valueFilter ? valueFilter.value : '';
    const sortOrder = sortBy ? sortBy.value : 'value-asc';
    
    // Filter players
    let filteredPlayers = Object.values(allPlayersData);
    
    // Filter by position
    if (selectedPosition) {
        filteredPlayers = filteredPlayers.filter(player => 
            player.element_type && player.element_type.toString() === selectedPosition
        );
    }
    
    // Filter by value range
    if (selectedValueRange) {
        const [min, max] = selectedValueRange.split('-').map(v => parseFloat(v));
        filteredPlayers = filteredPlayers.filter(player => {
            // now_cost is already in millions from data processor
            const value = parseFloat(player.now_cost || 0);
            if (max === 99) {
                return value >= min;
            }
            return value >= min && value < max;
        });
    }
    
    // Sort players
    filteredPlayers.sort((a, b) => {
        switch(sortOrder) {
            case 'value-asc':
                // now_cost is already in millions
                return (parseFloat(a.now_cost || 0)) - (parseFloat(b.now_cost || 0));
            case 'value-desc':
                // now_cost is already in millions
                return (parseFloat(b.now_cost || 0)) - (parseFloat(a.now_cost || 0));
            case 'points-desc':
                return (parseFloat(b.total_points || 0)) - (parseFloat(a.total_points || 0));
            case 'form-desc':
                return (parseFloat(b.form || 0)) - (parseFloat(a.form || 0));
            case 'ppg-desc':
                return (parseFloat(b.points_per_game || 0)) - (parseFloat(a.points_per_game || 0));
            default:
                return 0;
        }
    });
    
    // Check which players are already in transfer in
    const transferInIds = playersToTransferIn.map(p => {
        const id = typeof p === 'number' ? p : p.id;
        return id;
    });
    
    // Group by position
    const playersByPosition = {
        1: [],
        2: [],
        3: [],
        4: []
    };
    
    filteredPlayers.forEach(player => {
        const posId = player.element_type || 4;
        if (playersByPosition[posId]) {
            playersByPosition[posId].push(player);
        }
    });
    
    // Build HTML
    let html = '';
    const positions = [
        { id: 1, name: 'Goalkeepers', short: 'GK' },
        { id: 2, name: 'Defenders', short: 'DEF' },
        { id: 3, name: 'Midfielders', short: 'MID' },
        { id: 4, name: 'Forwards', short: 'FWD' }
    ];
    
    positions.forEach(({ id, name, short }) => {
        const players = playersByPosition[id] || [];
        if (players.length === 0) return;
        
        html += `
            <div class="position-pick-section">
                <h3 class="position-pick-title">${name} (${players.length})</h3>
                <div class="players-pick-list">
                    ${players.map(player => {
                        // now_cost is already in millions from data processor
                        const playerValue = parseFloat(player.now_cost || 0).toFixed(1);
                        const isAlreadyAdded = transferInIds.includes(player.id);
                        const playerName = player.web_name || 'Unknown';
                        const teamName = player.team_short_name || player.team_name || '';
                        
                        return `
                            <div class="player-pick-card ${isAlreadyAdded ? 'already-added' : ''}" data-player-id="${player.id}">
                                <div class="player-pick-info">
                                    <span class="player-pick-name">${playerName}</span>
                                    <span class="player-pick-position">${short}</span>
                                    ${teamName ? `<span class="player-pick-team">${teamName}</span>` : ''}
                                    <span class="player-pick-value">£${playerValue}m</span>
                                </div>
                                <button class="add-to-transfer-btn ${isAlreadyAdded ? 'disabled' : ''}" 
                                        data-player-id="${player.id}" 
                                        ${isAlreadyAdded ? 'disabled' : ''}>
                                    ${isAlreadyAdded ? '✓ Added' : '+ Add'}
                                </button>
                            </div>
                        `;
                    }).join('')}
                </div>
            </div>
        `;
    });
    
    if (html === '') {
        html = '<div class="no-players-message">No players found matching the selected filters.</div>';
    }
    
    container.innerHTML = html;
    
    // Attach event listeners
    attachPlayerPickListeners();
}

/**
 * Attach event listeners to player pick cards
 */
function attachPlayerPickListeners() {
    const buttons = document.querySelectorAll('.add-to-transfer-btn:not(.disabled)');
    buttons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const playerId = parseInt(e.target.dataset.playerId);
            addPlayerToTransferIn(playerId);
        });
    });
}

/**
 * Add player to transfer in
 */
function addPlayerToTransferIn(playerId) {
    const player = allPlayersData[playerId];
    if (!player) {
        console.warn(`Player ${playerId} not found`);
        return;
    }
    
    // Check if already added
    const exists = playersToTransferIn.some(p => {
        const id = typeof p === 'number' ? p : p.id;
        return id === playerId;
    });
    
    if (!exists) {
        playersToTransferIn.push(player);
        saveTransferData();
        updateTransferDisplay();
        displayPlayerPickMenu(); // Refresh to show updated state
    }
}

