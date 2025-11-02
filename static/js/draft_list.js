/**
 * Draft List JavaScript
 * Handles displaying all players with filtering and sorting functionality
 */

const API_ALL_PLAYERS = '/api/players/all';
const DRAFT_LIST_STORAGE_KEY = 'fpl_draft_list';

let allPlayers = [];
let filteredPlayers = [];
let proposedPlayers = {
    goalkeepers: [],
    defenders: [],
    midfielders: [],
    forwards: []
};
let currentSort = { column: 'last_5_games_points', order: 'desc' };

const API_SAVE_DRAFT_LIST = '/api/draft-list/save';
const API_LOAD_DRAFT_LIST = '/api/draft-list/load';

document.addEventListener('DOMContentLoaded', () => {
    loadProposedPlayers();
    loadAllPlayers();
    attachFilterListeners();
    attachSortListeners();
    attachSaveLoadListeners();
});

/**
 * Load proposed players from localStorage
 */
function loadProposedPlayers() {
    try {
        const stored = localStorage.getItem(DRAFT_LIST_STORAGE_KEY);
        if (stored) {
            proposedPlayers = JSON.parse(stored);
        }
    } catch (error) {
        console.error('Error loading proposed players:', error);
        proposedPlayers = {
            goalkeepers: [],
            defenders: [],
            midfielders: [],
            forwards: []
        };
    }
}

/**
 * Save proposed players to localStorage
 */
function saveProposedPlayers() {
    try {
        localStorage.setItem(DRAFT_LIST_STORAGE_KEY, JSON.stringify(proposedPlayers));
    } catch (error) {
        console.error('Error saving proposed players:', error);
    }
}

/**
 * Check if a player is proposed
 */
function isPlayerProposed(playerId) {
    return proposedPlayers.goalkeepers.includes(playerId) ||
           proposedPlayers.defenders.includes(playerId) ||
           proposedPlayers.midfielders.includes(playerId) ||
           proposedPlayers.forwards.includes(playerId);
}

/**
 * Remove a player from proposed list
 */
function removeProposedPlayer(playerId) {
    proposedPlayers.goalkeepers = proposedPlayers.goalkeepers.filter(id => id !== playerId);
    proposedPlayers.defenders = proposedPlayers.defenders.filter(id => id !== playerId);
    proposedPlayers.midfielders = proposedPlayers.midfielders.filter(id => id !== playerId);
    proposedPlayers.forwards = proposedPlayers.forwards.filter(id => id !== playerId);
    saveProposedPlayers();
}

/**
 * Load all players from API
 */
async function loadAllPlayers() {
    const container = document.getElementById('draft-list-container');
    
    try {
        const response = await fetch(API_ALL_PLAYERS);
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.message || 'Failed to load player data');
        }
        
        allPlayers = data.players || [];
        filteredPlayers = [...allPlayers];
        
        // Populate team filter dropdown
        populateTeamFilter(allPlayers);
        
        // Apply initial sort and display
        applySort();
        displayPlayers();
        displayProposedPlayers();
        updateStats();
        
    } catch (error) {
        container.innerHTML = `
            <div class="error-message">
                Error loading players: ${error.message}
            </div>
        `;
        console.error('Error loading players:', error);
    }
}

/**
 * Populate team filter dropdown
 */
function populateTeamFilter(players) {
    const teamSelect = document.getElementById('filter-team');
    if (!teamSelect) return;
    
    // Get unique teams
    const teamsMap = new Map();
    players.forEach(player => {
        if (player.team_id && player.team_name) {
            if (!teamsMap.has(player.team_id)) {
                teamsMap.set(player.team_id, {
                    id: player.team_id,
                    name: player.team_name,
                    short_name: player.team_short_name || player.team_name
                });
            }
        }
    });
    
    // Sort teams by name
    const teams = Array.from(teamsMap.values()).sort((a, b) => 
        a.name.localeCompare(b.name)
    );
    
    // Clear existing options except "All Teams"
    teamSelect.innerHTML = '<option value="">All Teams</option>';
    
    // Add team options
    teams.forEach(team => {
        const option = document.createElement('option');
        option.value = team.id;
        option.textContent = `${team.name} (${team.short_name})`;
        teamSelect.appendChild(option);
    });
}

/**
 * Attach filter listeners
 */
function attachFilterListeners() {
    const filters = [
        'filter-position',
        'filter-team',
        'filter-status',
        'filter-price-min',
        'filter-price-max'
    ];
    
    filters.forEach(filterId => {
        const filterElement = document.getElementById(filterId);
        if (filterElement) {
            // Use 'input' for text inputs, 'change' for selects
            const eventType = filterElement.tagName === 'INPUT' ? 'input' : 'change';
            filterElement.addEventListener(eventType, () => {
                applyFilters();
            });
        }
    });
    
    const clearFiltersBtn = document.getElementById('clear-filters');
    if (clearFiltersBtn) {
        clearFiltersBtn.addEventListener('click', () => {
            clearFilters();
        });
    }
}

/**
 * Apply filters to player list
 */
function applyFilters() {
    const positionFilter = document.getElementById('filter-position')?.value || '';
    const teamFilter = document.getElementById('filter-team')?.value || '';
    const statusFilter = document.getElementById('filter-status')?.value || '';
    const priceMin = parseFloat(document.getElementById('filter-price-min')?.value) || 0;
    const priceMax = parseFloat(document.getElementById('filter-price-max')?.value) || Infinity;
    
    filteredPlayers = allPlayers.filter(player => {
        // Position filter
        if (positionFilter && String(player.position_id) !== positionFilter) {
            return false;
        }
        
        // Team filter
        if (teamFilter && String(player.team_id) !== teamFilter) {
            return false;
        }
        
        // Status filter
        if (statusFilter && player.status !== statusFilter) {
            return false;
        }
        
        // Price filter
        const price = player.now_cost || 0;
        if (price < priceMin || price > priceMax) {
            return false;
        }
        
        return true;
    });
    
    // Re-apply sort after filtering
    applySort();
    displayPlayers();
    updateStats();
}

/**
 * Clear all filters
 */
function clearFilters() {
    document.getElementById('filter-position').value = '';
    document.getElementById('filter-team').value = '';
    document.getElementById('filter-status').value = '';
    document.getElementById('filter-price-min').value = '';
    document.getElementById('filter-price-max').value = '';
    
    filteredPlayers = [...allPlayers];
    applySort();
    displayPlayers();
    updateStats();
}

/**
 * Attach sort listeners
 */
function attachSortListeners() {
    const applySortBtn = document.getElementById('apply-sort');
    if (applySortBtn) {
        applySortBtn.addEventListener('click', () => {
            applySort();
            displayPlayers();
        });
    }
}

/**
 * Apply sorting to filtered players
 */
function applySort() {
    const sortColumn = document.getElementById('sort-column')?.value || 'last_5_games_points';
    const sortOrder = document.getElementById('sort-order')?.value || 'desc';
    
    currentSort = { column: sortColumn, order: sortOrder };
    
    filteredPlayers.sort((a, b) => {
        let aValue = getSortValue(a, sortColumn);
        let bValue = getSortValue(b, sortColumn);
        
        // Handle null/undefined values
        if (aValue === null || aValue === undefined) aValue = 0;
        if (bValue === null || bValue === undefined) bValue = 0;
        
        // Numeric comparison for numbers
        if (typeof aValue === 'number' && typeof bValue === 'number') {
            return sortOrder === 'asc' ? aValue - bValue : bValue - aValue;
        }
        
        // String comparison
        const aStr = String(aValue).toLowerCase();
        const bStr = String(bValue).toLowerCase();
        
        if (sortOrder === 'asc') {
            return aStr.localeCompare(bStr);
        } else {
            return bStr.localeCompare(aStr);
        }
    });
}

/**
 * Get sort value for a player based on column name
 */
function getSortValue(player, column) {
    switch(column) {
        case 'last_5_games_points':
            return player.last_5_games_points || 0;
        case 'last_3_games_points':
            return player.last_3_games_points || 0;
        case 'total_points':
            return player.total_points || 0;
        case 'points_per_game':
            return player.points_per_game || 0;
        case 'points_per_million':
            return player.points_per_million || 0;
        case 'goals_scored':
            return player.goals_scored || 0;
        case 'assists':
            return player.assists || 0;
        case 'clean_sheets':
            return player.clean_sheets || 0;
        case 'ict_index':
            return player.ict_index || 0;
        case 'form':
            return parseFloat(player.form) || 0;
        case 'selected_by_percent':
            return player.selected_by_percent || 0;
        case 'now_cost':
            return player.now_cost || 0;
        case 'web_name':
            return player.web_name || '';
        case 'team_name':
            return player.team_name || '';
        default:
            return 0;
    }
}

/**
 * Display players in table
 */
function displayPlayers() {
    const container = document.getElementById('draft-list-container');
    if (!container) return;
    
    // Check if proposed section exists, keep it if it does
    const existingProposedSection = container.querySelector('.proposed-players-section');
    
    if (filteredPlayers.length === 0) {
        // Keep proposed section if it exists
        if (!existingProposedSection) {
            container.innerHTML = `
                <div class="no-players-message">
                    No players match the current filters.
                </div>
            `;
        } else {
            // Clear everything except proposed section
            const tableWrapper = container.querySelector('.draft-list-table-wrapper');
            if (tableWrapper) tableWrapper.remove();
        }
        return;
    }
    
    const tableHTML = `
        <div class="draft-list-table-wrapper">
            <table class="draft-list-table">
                <thead>
                    <tr>
                        <th>Player</th>
                        <th>Position</th>
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
                        <th>Selected By</th>
                        <th>Status</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    ${filteredPlayers.map(player => createPlayerRow(player)).join('')}
                </tbody>
            </table>
        </div>
    `;
    
    // If proposed section exists, insert table after it, otherwise replace content
    if (existingProposedSection) {
        const existingTable = container.querySelector('.draft-list-table-wrapper');
        if (existingTable) {
            existingTable.outerHTML = tableHTML;
        } else {
            existingProposedSection.insertAdjacentHTML('afterend', tableHTML);
        }
    } else {
        container.innerHTML = tableHTML;
    }
    
    // Attach delete button listeners
    attachDeleteButtonListeners();
}

/**
 * Display proposed players section
 */
function displayProposedPlayers() {
    const container = document.getElementById('draft-list-container');
    if (!container) return;
    
    const totalProposed = proposedPlayers.goalkeepers.length +
                         proposedPlayers.defenders.length +
                         proposedPlayers.midfielders.length +
                         proposedPlayers.forwards.length;
    
    // Remove existing proposed section if no proposed players
    const existingProposedSection = container.querySelector('.proposed-players-section');
    if (totalProposed === 0) {
        if (existingProposedSection) {
            existingProposedSection.remove();
        }
        return;
    }
    
    // Get proposed player details
    const proposedPlayerIds = [
        ...proposedPlayers.goalkeepers,
        ...proposedPlayers.defenders,
        ...proposedPlayers.midfielders,
        ...proposedPlayers.forwards
    ];
    
    const proposedPlayersList = allPlayers.filter(p => proposedPlayerIds.includes(p.id));
    
    const proposedSectionHTML = `
        <div class="proposed-players-section">
            <h3>Proposed Players (${totalProposed})</h3>
            <div class="proposed-players-list">
                ${proposedPlayersList.map(player => {
                    const positionName = player.position_short_name || getPositionName(player.position_id);
                    return `
                        <div class="proposed-player-card" data-player-id="${player.id}">
                            <div class="proposed-player-info">
                                <strong>${player.web_name || 'N/A'}</strong>
                                <span class="proposed-player-position">${positionName}</span>
                                <span class="proposed-player-team">${player.team_short_name || player.team_name}</span>
                                <span class="proposed-player-price">£${safeToFixed(player.now_cost, 1)}m</span>
                                <span class="proposed-player-points">${player.total_points || 0} pts</span>
                            </div>
                            <button class="delete-proposed-card-btn" data-player-id="${player.id}" title="Remove from proposed players">✕</button>
                        </div>
                    `;
                }).join('')}
            </div>
        </div>
    `;
    
    // Replace or add proposed section
    if (existingProposedSection) {
        existingProposedSection.outerHTML = proposedSectionHTML;
    } else {
        // Insert at the beginning of container
        container.insertAdjacentHTML('afterbegin', proposedSectionHTML);
    }
    
    // Attach delete button listeners
    attachDeleteButtonListeners();
}

/**
 * Attach delete button listeners
 */
function attachDeleteButtonListeners() {
    // Delete buttons in table rows
    const deleteButtons = document.querySelectorAll('.delete-proposed-btn');
    deleteButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const playerId = parseInt(e.target.dataset.playerId);
            removeProposedPlayerFromView(playerId);
        });
    });
    
    // Delete buttons in proposed players cards
    const deleteCardButtons = document.querySelectorAll('.delete-proposed-card-btn');
    deleteCardButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const playerId = parseInt(e.target.dataset.playerId);
            removeProposedPlayerFromView(playerId);
        });
    });
}

/**
 * Remove proposed player from view and localStorage
 */
function removeProposedPlayerFromView(playerId) {
    if (confirm('Remove this player from proposed players list?')) {
        removeProposedPlayer(playerId);
        
        // Remove proposed badge from table row if exists
        const row = document.querySelector(`tr[data-player-id="${playerId}"]`);
        if (row) {
            row.classList.remove('proposed-player');
            const badge = row.querySelector('.proposed-badge');
            if (badge) badge.remove();
            
            // Update action cell
            const actionCell = row.querySelector('td:last-child');
            if (actionCell) {
                actionCell.innerHTML = '';
            }
        }
        
        // Refresh proposed players section and display
        displayProposedPlayers();
        displayPlayers();
        updateStats();
    }
}

/**
 * Create a table row for a player
 */
function createPlayerRow(player) {
    const statusBadge = getStatusBadge(player);
    const positionName = player.position_short_name || getPositionName(player.position_id);
    const isProposed = isPlayerProposed(player.id);
    const rowClass = isProposed ? 'proposed-player' : '';
    
    return `
        <tr class="${rowClass}" data-player-id="${player.id}">
            <td class="player-name-cell">
                <strong>${player.web_name || 'N/A'}</strong>
                ${player.first_name && player.second_name ? `<small>${player.first_name} ${player.second_name}</small>` : ''}
                ${isProposed ? '<span class="proposed-badge" title="Proposed player from Player Analysis">📋 Proposed</span>' : ''}
            </td>
            <td>${positionName}</td>
            <td>${player.team_short_name || player.team_name || 'N/A'}</td>
            <td>£${safeToFixed(player.now_cost, 1)}m</td>
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
            <td>${safeToFixed(player.selected_by_percent || 0, 1)}%</td>
            <td>${statusBadge}</td>
            ${isProposed ? `<td><button class="delete-proposed-btn" data-player-id="${player.id}" title="Remove from proposed players">✕</button></td>` : '<td></td>'}
        </tr>
    `;
}

/**
 * Get position name from position ID
 */
function getPositionName(positionId) {
    const positions = {
        1: 'GK',
        2: 'DEF',
        3: 'MID',
        4: 'FWD'
    };
    return positions[positionId] || 'N/A';
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
 * Update statistics display
 */
function updateStats() {
    const totalPlayersEl = document.getElementById('total-players');
    const filteredPlayersEl = document.getElementById('filtered-players');
    
    if (totalPlayersEl) {
        totalPlayersEl.textContent = allPlayers.length;
    }
    if (filteredPlayersEl) {
        filteredPlayersEl.textContent = filteredPlayers.length;
    }
    
    // Update proposed players count if section exists
    const proposedCount = proposedPlayers.goalkeepers.length +
                         proposedPlayers.defenders.length +
                         proposedPlayers.midfielders.length +
                         proposedPlayers.forwards.length;
    
    const proposedSection = document.querySelector('.proposed-players-section h3');
    if (proposedSection && proposedCount > 0) {
        proposedSection.textContent = `Proposed Players (${proposedCount})`;
    } else if (proposedCount === 0) {
        const proposedSectionEl = document.querySelector('.proposed-players-section');
        if (proposedSectionEl) {
            proposedSectionEl.remove();
        }
    }
}

/**
 * Attach save and load button listeners
 */
function attachSaveLoadListeners() {
    const saveBtn = document.getElementById('save-draft-btn');
    const loadBtn = document.getElementById('load-draft-btn');
    const copyBtn = document.getElementById('copy-team-id-btn');
    const teamIdInput = document.getElementById('fpl-team-id-input');
    
    if (saveBtn) {
        saveBtn.addEventListener('click', () => {
            saveDraftList();
        });
    }
    
    if (loadBtn) {
        loadBtn.addEventListener('click', () => {
            loadDraftList();
        });
    }
    
    if (copyBtn && teamIdInput) {
        copyBtn.addEventListener('click', () => {
            teamIdInput.select();
            teamIdInput.setSelectionRange(0, 99999); // For mobile devices
            document.execCommand('copy');
            
            // Show feedback
            const originalText = copyBtn.innerHTML;
            copyBtn.innerHTML = '✓';
            setTimeout(() => {
                copyBtn.innerHTML = originalText;
            }, 1000);
        });
    }
}

/**
 * Save draft list to database
 */
async function saveDraftList() {
    const teamIdInput = document.getElementById('fpl-team-id-input');
    const statusEl = document.getElementById('save-status');
    
    if (!teamIdInput || !statusEl) return;
    
    const fplTeamId = teamIdInput.value.trim();
    
    if (!fplTeamId) {
        showSaveStatus('Please enter your FPL Team ID', 'error');
        return;
    }
    
    // Validate team ID is numeric
    if (!/^\d+$/.test(fplTeamId)) {
        showSaveStatus('Invalid FPL Team ID. Please enter a number.', 'error');
        return;
    }
    
    // Get current proposed players
    const draftListData = {
        goalkeepers: [...proposedPlayers.goalkeepers],
        defenders: [...proposedPlayers.defenders],
        midfielders: [...proposedPlayers.midfielders],
        forwards: [...proposedPlayers.forwards]
    };
    
    const totalPlayers = draftListData.goalkeepers.length +
                        draftListData.defenders.length +
                        draftListData.midfielders.length +
                        draftListData.forwards.length;
    
    if (totalPlayers === 0) {
        showSaveStatus('No players in draft list to save', 'error');
        return;
    }
    
    try {
        showSaveStatus('Saving draft list...', 'info');
        
        const response = await fetch(API_SAVE_DRAFT_LIST, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                fpl_team_id: parseInt(fplTeamId),
                draft_list: draftListData
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showSaveStatus(
                `✓ Draft list saved successfully for Team ID ${fplTeamId} (${totalPlayers} players)`,
                'success'
            );
        } else {
            showSaveStatus(`Error: ${data.message}`, 'error');
        }
    } catch (error) {
        showSaveStatus(`Error saving draft list: ${error.message}`, 'error');
        console.error('Error saving draft list:', error);
    }
}

/**
 * Load draft list from database
 */
async function loadDraftList() {
    const teamIdInput = document.getElementById('fpl-team-id-input');
    const statusEl = document.getElementById('save-status');
    
    if (!teamIdInput || !statusEl) return;
    
    const fplTeamId = teamIdInput.value.trim();
    
    if (!fplTeamId) {
        showSaveStatus('Please enter your FPL Team ID', 'error');
        return;
    }
    
    // Validate team ID is numeric
    if (!/^\d+$/.test(fplTeamId)) {
        showSaveStatus('Invalid FPL Team ID. Please enter a number.', 'error');
        return;
    }
    
    try {
        showSaveStatus('Loading draft list...', 'info');
        
        const response = await fetch(`${API_LOAD_DRAFT_LIST}?fpl_team_id=${fplTeamId}`);
        const data = await response.json();
        
        if (data.success && data.draft_list) {
            // Update proposed players
            proposedPlayers = {
                goalkeepers: [...(data.draft_list.goalkeepers || [])],
                defenders: [...(data.draft_list.defenders || [])],
                midfielders: [...(data.draft_list.midfielders || [])],
                forwards: [...(data.draft_list.forwards || [])]
            };
            
            // Save to localStorage
            saveProposedPlayers();
            
            // Refresh display
            displayProposedPlayers();
            displayPlayers();
            updateStats();
            
            const totalPlayers = proposedPlayers.goalkeepers.length +
                                proposedPlayers.defenders.length +
                                proposedPlayers.midfielders.length +
                                proposedPlayers.forwards.length;
            
            showSaveStatus(
                `✓ Draft list loaded successfully for Team ID ${fplTeamId} (${totalPlayers} players)`,
                'success'
            );
        } else {
            showSaveStatus(`Error: ${data.message || 'No draft list found'}`, 'error');
        }
    } catch (error) {
        showSaveStatus(`Error loading draft list: ${error.message}`, 'error');
        console.error('Error loading draft list:', error);
    }
}

/**
 * Show save status message
 */
function showSaveStatus(message, type) {
    const statusEl = document.getElementById('save-status');
    if (!statusEl) return;
    
    statusEl.textContent = message;
    statusEl.className = `save-status ${type}`;
    
    // Auto-hide success messages after 5 seconds
    if (type === 'success') {
        setTimeout(() => {
            statusEl.textContent = '';
            statusEl.className = 'save-status';
        }, 5000);
    }
}

