/**
 * Player Analysis Page JavaScript
 * Handles displaying top players by position, team filtering, and player selection
 */

const API_PLAYERS = '/api/players/top-by-position';
const API_LEAGUE_TABLE = '/api/league-table';
const SELECTED_TEAMS_STORAGE_KEY = 'fpl_selected_teams';
const SELECTED_PLAYERS_STORAGE_KEY = 'fpl_selected_players';
const DRAFT_LIST_STORAGE_KEY = 'fpl_draft_list';

// Position limits
const POSITION_LIMITS = {
    1: 2,  // Goalkeepers
    2: 5,  // Defenders
    3: 5,  // Midfielders
    4: 3   // Forwards
};

let selectedPlayers = {
    goalkeepers: [],
    defenders: [],
    midfielders: [],
    forwards: []
};

let isFilterByTeams = false;

document.addEventListener('DOMContentLoaded', () => {
    loadSelectedPlayers();
    fetchAndDisplayData();
    attachFilterToggle();
    attachTransferToFormationButton();
    attachTransferToDraftListButton();
});

/**
 * Load selected players from localStorage
 */
function loadSelectedPlayers() {
    try {
        const stored = localStorage.getItem(SELECTED_PLAYERS_STORAGE_KEY);
        if (stored) {
            selectedPlayers = JSON.parse(stored);
        }
    } catch (error) {
        console.error('Error loading selected players:', error);
        selectedPlayers = {
            goalkeepers: [],
            defenders: [],
            midfielders: [],
            forwards: []
        };
    }
}

/**
 * Save selected players to localStorage
 */
function saveSelectedPlayers() {
    try {
        localStorage.setItem(SELECTED_PLAYERS_STORAGE_KEY, JSON.stringify(selectedPlayers));
        // Also save to draft list
        localStorage.setItem(DRAFT_LIST_STORAGE_KEY, JSON.stringify(selectedPlayers));
    } catch (error) {
        console.error('Error saving selected players:', error);
    }
}

/**
 * Fetch and display all data
 */
async function fetchAndDisplayData() {
    await Promise.all([
        fetchAndDisplayPlayers(),
        fetchAndDisplayLeagueTable()
    ]);
}

/**
 * Fetch and display players by position
 */
async function fetchAndDisplayPlayers() {
    const container = document.getElementById('players-container');
    if (!container) return;
    
    container.innerHTML = '<div class="loading-placeholder">Loading player data...</div>';
    
    try {
        // Get selected teams for filtering
        const selectedTeams = getSelectedTeams();
        let url = API_PLAYERS;
        if (isFilterByTeams && selectedTeams.length > 0) {
            url += `?selected_teams=${selectedTeams.join(',')}`;
        }
        
        const response = await fetch(url);
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.message || 'Failed to load player data');
        }
        
        displayPlayersByPosition(data.players);
    } catch (error) {
        container.innerHTML = `<div class="error-message">Error loading players: ${error.message}</div>`;
        console.error('Error fetching players:', error);
    }
}

/**
 * Get selected teams from localStorage
 */
function getSelectedTeams() {
    try {
        const stored = localStorage.getItem(SELECTED_TEAMS_STORAGE_KEY);
        return stored ? JSON.parse(stored) : [];
    } catch (error) {
        return [];
    }
}

/**
 * Display players organized by position
 */
function displayPlayersByPosition(playersData) {
    const container = document.getElementById('players-container');
    
    const html = `
        <div class="players-filter-section">
            <div class="filter-controls">
                <label class="filter-toggle">
                    <input type="checkbox" id="filter-by-teams" ${isFilterByTeams ? 'checked' : ''}>
                    <span>Filter by Selected Teams</span>
                </label>
                <div class="selected-count-summary">
                    <strong>Selected:</strong>
                    <span>GK: ${selectedPlayers.goalkeepers.length}/${POSITION_LIMITS[1]}</span>
                    <span>DEF: ${selectedPlayers.defenders.length}/${POSITION_LIMITS[2]}</span>
                    <span>MID: ${selectedPlayers.midfielders.length}/${POSITION_LIMITS[3]}</span>
                    <span>FWD: ${selectedPlayers.forwards.length}/${POSITION_LIMITS[4]}</span>
                    <div class="edit-selection-dropdown">
                        <button class="edit-selection-btn" id="edit-selection-btn">
                            Edit Selection
                            <span class="dropdown-arrow">▼</span>
                        </button>
                        <div class="edit-selection-menu" id="edit-selection-menu">
                            <button class="edit-menu-item" data-action="clear-all">Clear All Selections</button>
                            <button class="edit-menu-item" data-action="clear-gk">Clear Goalkeepers</button>
                            <button class="edit-menu-item" data-action="clear-def">Clear Defenders</button>
                            <button class="edit-menu-item" data-action="clear-mid">Clear Midfielders</button>
                            <button class="edit-menu-item" data-action="clear-fwd">Clear Forwards</button>
                            <button class="edit-menu-item" data-action="view-selected">View Selected Players</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div id="selected-players-modal" class="selected-players-modal hidden">
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Selected Players</h3>
                    <button class="modal-close" id="close-modal">&times;</button>
                </div>
                <div class="modal-body" id="selected-players-list">
                    <!-- Selected players will be displayed here -->
                </div>
            </div>
        </div>
        
        <div class="players-by-position">
            ${displayPositionSection('Goalkeepers', playersData.goalkeepers || [], 1)}
            ${displayPositionSection('Defenders', playersData.defenders || [], 2)}
            ${displayPositionSection('Midfielders', playersData.midfielders || [], 3)}
            ${displayPositionSection('Forwards', playersData.forwards || [], 4)}
        </div>
    `;
    
    container.innerHTML = html;
    
    // Attach event listeners
    document.getElementById('filter-by-teams').addEventListener('change', (e) => {
        isFilterByTeams = e.target.checked;
        fetchAndDisplayPlayers();
    });
    
    attachSelectionListeners();
    attachEditSelectionListeners();
    attachSortListeners();
    attachTransferToFormationButtonListener();
    attachTransferToDraftListButtonListener();
}

/**
 * Display a position section
 */
function displayPositionSection(title, players, positionId) {
    if (!players || players.length === 0) {
        return `
            <div class="position-section">
                <h2 class="position-title">${title}</h2>
                <p class="no-players">No players found</p>
            </div>
        `;
    }
    
    const selectedIds = selectedPlayers[getPositionKey(positionId)] || [];
    const isAtLimit = selectedIds.length >= POSITION_LIMITS[positionId];
    
    return `
        <div class="position-section">
            <h2 class="position-title">${title} (${players.length})</h2>
            <div class="players-table-wrapper">
                <table class="players-table sortable-table" data-position-id="${positionId}">
                    <thead>
                        <tr>
                            <th data-sort="select" data-type="none">Select</th>
                            <th class="sortable" data-sort="player" data-type="string">Player <span class="sort-icon">↕</span></th>
                            <th class="sortable" data-sort="team" data-type="string">Team <span class="sort-icon">↕</span></th>
                            <th class="sortable" data-sort="price" data-type="number">Price <span class="sort-icon">↕</span></th>
                            <th class="sortable" data-sort="last3" data-type="number">Last 3 Pts <span class="sort-icon">↕</span></th>
                            <th class="sortable" data-sort="last5" data-type="number">Last 5 Pts <span class="sort-icon">↕</span></th>
                            <th class="sortable" data-sort="total" data-type="number">Total Pts <span class="sort-icon">↕</span></th>
                            <th class="sortable" data-sort="ppg" data-type="number">PPG <span class="sort-icon">↕</span></th>
                            <th class="sortable" data-sort="ppm" data-type="number">Pts/£M <span class="sort-icon">↕</span></th>
                            <th class="sortable" data-sort="goals" data-type="number">Goals <span class="sort-icon">↕</span></th>
                            <th class="sortable" data-sort="assists" data-type="number">Assists <span class="sort-icon">↕</span></th>
                            <th class="sortable" data-sort="cs" data-type="number">CS <span class="sort-icon">↕</span></th>
                            <th class="sortable" data-sort="ict" data-type="number">ICT <span class="sort-icon">↕</span></th>
                            <th class="sortable" data-sort="form" data-type="number">Form <span class="sort-icon">↕</span></th>
                            <th class="sortable" data-sort="selected" data-type="number">Selected By <span class="sort-icon">↕</span></th>
                            <th class="sortable" data-sort="status" data-type="string">Status <span class="sort-icon">↕</span></th>
                        </tr>
                    </thead>
                    <tbody>
                        ${players.map(player => {
                            const isSelected = selectedIds.includes(player.id);
                            const rowClass = isSelected ? 'selected' : '';
                            const canSelect = !isSelected && !isAtLimit;
                            
                            return `
                                <tr class="${rowClass}" data-player-id="${player.id}" data-position-id="${positionId}">
                                    <td>
                                        <input type="checkbox" 
                                               ${isSelected ? 'checked' : ''} 
                                               ${canSelect ? '' : 'disabled'}
                                               data-player-id="${player.id}"
                                               data-position-id="${positionId}">
                                    </td>
                                    <td class="player-name-cell" data-value="${player.web_name.toLowerCase()}">
                                        <strong>${player.web_name}</strong>
                                        <small>${player.first_name} ${player.second_name}</small>
                                    </td>
                                    <td data-value="${player.team_short_name || player.team_name}">${player.team_short_name || player.team_name}</td>
                                    <td data-value="${player.now_cost}">£${safeToFixed(player.now_cost, 1)}m</td>
                                    <td class="points-cell" data-value="${player.last_3_games_points || 0}">${safeToFixed(player.last_3_games_points || 0, 1)}</td>
                                    <td class="points-cell" data-value="${player.last_5_games_points || 0}">${safeToFixed(player.last_5_games_points || 0, 1)}</td>
                                    <td class="points-cell" data-value="${player.total_points || 0}">${player.total_points || 0}</td>
                                    <td data-value="${player.points_per_game || 0}">${safeToFixed(player.points_per_game, 1)}</td>
                                    <td class="value-cell" data-value="${player.points_per_million || 0}">${safeToFixed(player.points_per_million || 0, 2)}</td>
                                    <td data-value="${player.goals_scored || 0}">${player.goals_scored || 0}</td>
                                    <td data-value="${player.assists || 0}">${player.assists || 0}</td>
                                    <td data-value="${player.clean_sheets || 0}">${player.clean_sheets || 0}</td>
                                    <td data-value="${player.ict_index || 0}">${safeToFixed(player.ict_index, 1)}</td>
                                    <td data-value="${parseFloat(player.form) || 0}">${player.form || '0.0'}</td>
                                    <td data-value="${player.selected_by_percent || 0}">${safeToFixed(player.selected_by_percent, 1)}%</td>
                                    <td data-value="${player.status || 'a'}">${getStatusBadge(player)}</td>
                                </tr>
                            `;
                        }).join('')}
                    </tbody>
                </table>
            </div>
        </div>
    `;
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
 * Attach selection listeners
 */
function attachSelectionListeners() {
    const checkboxes = document.querySelectorAll('.players-table input[type="checkbox"]');
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', (e) => {
            const playerId = parseInt(e.target.dataset.playerId);
            const positionId = parseInt(e.target.dataset.positionId);
            const positionKey = getPositionKey(positionId);
            const row = e.target.closest('tr');
            
            if (e.target.checked) {
                selectPlayer(playerId, positionKey);
                row.classList.add('selected');
            } else {
                deselectPlayer(playerId, positionKey);
                row.classList.remove('selected');
            }
            
            // Update UI
            updateSelectionCount();
            updateCheckboxStates(positionId);
            updateTransferButtonState();
            updateTransferToDraftListButtonState();
        });
    });
}

/**
 * Select a player
 */
function selectPlayer(playerId, positionKey) {
    if (!selectedPlayers[positionKey].includes(playerId)) {
        selectedPlayers[positionKey].push(playerId);
        saveSelectedPlayers();
    }
}

/**
 * Deselect a player
 */
function deselectPlayer(playerId, positionKey) {
    const index = selectedPlayers[positionKey].indexOf(playerId);
    if (index > -1) {
        selectedPlayers[positionKey].splice(index, 1);
        saveSelectedPlayers();
    }
}

/**
 * Update selection count display
 */
function updateSelectionCount() {
    const summary = document.querySelector('.selected-count-summary');
    if (summary) {
        summary.innerHTML = `
            <strong>Selected:</strong>
            <span>GK: ${selectedPlayers.goalkeepers.length}/${POSITION_LIMITS[1]}</span>
            <span>DEF: ${selectedPlayers.defenders.length}/${POSITION_LIMITS[2]}</span>
            <span>MID: ${selectedPlayers.midfielders.length}/${POSITION_LIMITS[3]}</span>
            <span>FWD: ${selectedPlayers.forwards.length}/${POSITION_LIMITS[4]}</span>
        `;
        // Re-attach edit selection dropdown listeners
        attachEditSelectionListeners();
    }
}

/**
 * Update checkbox states when limit reached
 */
function updateCheckboxStates(positionId) {
    const positionKey = getPositionKey(positionId);
    const selectedIds = selectedPlayers[positionKey] || [];
    const isAtLimit = selectedIds.length >= POSITION_LIMITS[positionId];
    
    const checkboxes = document.querySelectorAll(
        `.players-table tr[data-position-id="${positionId}"] input[type="checkbox"]`
    );
    
    checkboxes.forEach(checkbox => {
        const playerId = parseInt(checkbox.dataset.playerId);
        const isSelected = selectedIds.includes(playerId);
        checkbox.disabled = !isSelected && isAtLimit;
    });
}

/**
 * Attach edit selection button listeners
 */
function attachEditSelectionListeners() {
    const editBtn = document.getElementById('edit-selection-btn');
    const editMenu = document.getElementById('edit-selection-menu');
    const closeModal = document.getElementById('close-modal');
    const modal = document.getElementById('selected-players-modal');
    
    if (!editBtn || !editMenu) return;
    
    // Toggle dropdown menu
    editBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        const isActive = editMenu.classList.toggle('active');
        editBtn.classList.toggle('active', isActive);
    });
    
    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
        if (!editBtn.contains(e.target) && !editMenu.contains(e.target)) {
            editMenu.classList.remove('active');
            editBtn.classList.remove('active');
        }
    });
    
    // Handle menu item clicks
    const menuItems = editMenu.querySelectorAll('.edit-menu-item');
    menuItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.stopPropagation();
            const action = item.dataset.action;
            handleEditSelectionAction(action);
            editMenu.classList.remove('active');
            editBtn.classList.remove('active');
        });
    });
    
    // Close modal
    if (closeModal && modal) {
        closeModal.addEventListener('click', () => {
            modal.classList.add('hidden');
        });
        
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.add('hidden');
            }
        });
    }
}

/**
 * Handle edit selection actions
 */
function handleEditSelectionAction(action) {
    switch(action) {
        case 'clear-all':
            if (confirm('Are you sure you want to clear all player selections?')) {
                clearAllSelections();
            }
            break;
        case 'clear-gk':
            if (confirm('Clear all goalkeeper selections?')) {
                clearPositionSelections('goalkeepers');
            }
            break;
        case 'clear-def':
            if (confirm('Clear all defender selections?')) {
                clearPositionSelections('defenders');
            }
            break;
        case 'clear-mid':
            if (confirm('Clear all midfielder selections?')) {
                clearPositionSelections('midfielders');
            }
            break;
        case 'clear-fwd':
            if (confirm('Clear all forward selections?')) {
                clearPositionSelections('forwards');
            }
            break;
        case 'view-selected':
            showSelectedPlayersModal();
            break;
    }
}

/**
 * Clear all selections
 */
function clearAllSelections() {
    selectedPlayers = {
        goalkeepers: [],
        defenders: [],
        midfielders: [],
        forwards: []
    };
    saveSelectedPlayers();
    fetchAndDisplayPlayers();
    updateSelectionCount();
    updateTransferButtonState();
}

/**
 * Clear selections for a specific position
 */
function clearPositionSelections(positionKey) {
    selectedPlayers[positionKey] = [];
    saveSelectedPlayers();
    fetchAndDisplayPlayers();
    updateSelectionCount();
    updateTransferButtonState();
}

/**
 * Show selected players modal
 */
async function showSelectedPlayersModal() {
    const modal = document.getElementById('selected-players-modal');
    const listContainer = document.getElementById('selected-players-list');
    
    if (!modal || !listContainer) return;
    
    // Get all player data
    try {
        const response = await fetch(API_PLAYERS);
        const data = await response.json();
        
        if (!data.success) {
            listContainer.innerHTML = '<p>Error loading player data</p>';
            modal.classList.remove('hidden');
            return;
        }
        
        const allPlayers = [
            ...(data.players.goalkeepers || []),
            ...(data.players.defenders || []),
            ...(data.players.midfielders || []),
            ...(data.players.forwards || [])
        ];
        
        const playerMap = {};
        allPlayers.forEach(player => {
            playerMap[player.id] = player;
        });
        
        // For players not in top lists, we'll show their ID (user can still remove them)
        // Build selected players list
        const html = `
            <div class="selected-players-by-position">
                ${displaySelectedPosition('Goalkeepers', selectedPlayers.goalkeepers, playerMap, 1)}
                ${displaySelectedPosition('Defenders', selectedPlayers.defenders, playerMap, 2)}
                ${displaySelectedPosition('Midfielders', selectedPlayers.midfielders, playerMap, 3)}
                ${displaySelectedPosition('Forwards', selectedPlayers.forwards, playerMap, 4)}
            </div>
        `;
        
        listContainer.innerHTML = html;
        modal.classList.remove('hidden');
        
        // Attach remove buttons
        attachRemovePlayerListeners();
    } catch (error) {
        listContainer.innerHTML = `<p>Error: ${error.message}</p>`;
        modal.classList.remove('hidden');
    }
}

/**
 * Display selected players for a position
 */
function displaySelectedPosition(title, selectedIds, playerMap, positionId) {
    if (!selectedIds || selectedIds.length === 0) {
        return `
            <div class="selected-position-section">
                <h4>${title}</h4>
                <p class="no-selected">No ${title.toLowerCase()} selected</p>
            </div>
        `;
    }
    
    const players = selectedIds.map(id => {
        const player = playerMap[id];
        if (player) {
            return { ...player, found: true };
        }
        // Player not found in current top lists
        return { id, web_name: `Player #${id}`, found: false };
    });
    
    return `
        <div class="selected-position-section">
            <h4>${title} (${players.length})</h4>
            <div class="selected-players-list">
                ${players.map(player => {
                    if (player.found) {
                        return `
                            <div class="selected-player-item">
                                <div class="player-info">
                                    <strong>${player.web_name}</strong>
                                    <span class="player-team">${player.team_short_name || player.team_name}</span>
                                    <span class="player-price">£${safeToFixed(player.now_cost, 1)}m</span>
                                    <span class="player-points">${player.total_points} pts</span>
                                </div>
                                <button class="remove-player-btn" data-player-id="${player.id}" data-position-id="${positionId}">
                                    Remove
                                </button>
                            </div>
                        `;
                    } else {
                        return `
                            <div class="selected-player-item">
                                <div class="player-info">
                                    <strong>${player.web_name}</strong>
                                    <span class="player-team">Not in current top lists</span>
                                </div>
                                <button class="remove-player-btn" data-player-id="${player.id}" data-position-id="${positionId}">
                                    Remove
                                </button>
                            </div>
                        `;
                    }
                }).join('')}
            </div>
        </div>
    `;
}

/**
 * Attach remove player listeners
 */
function attachRemovePlayerListeners() {
    const removeButtons = document.querySelectorAll('.remove-player-btn');
    removeButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const playerId = parseInt(e.target.dataset.playerId);
            const positionId = parseInt(e.target.dataset.positionId);
            const positionKey = getPositionKey(positionId);
            
            deselectPlayer(playerId, positionKey);
            showSelectedPlayersModal(); // Refresh modal
            fetchAndDisplayPlayers(); // Refresh main view
            updateSelectionCount();
        });
    });
}

/**
 * Attach sort listeners for table columns
 */
function attachSortListeners() {
    const sortableHeaders = document.querySelectorAll('.sortable-table th.sortable');
    
    sortableHeaders.forEach(header => {
        header.addEventListener('click', (e) => {
            const table = header.closest('.sortable-table');
            const sortColumn = header.dataset.sort;
            const sortType = header.dataset.type;
            
            if (sortColumn === 'select' || sortType === 'none' || !table) return;
            
            // Get current sort state
            const currentSort = table.dataset.sortColumn;
            const currentOrder = table.dataset.sortOrder || 'desc';
            
            // Determine new sort order
            let newOrder = 'desc';
            if (currentSort === sortColumn && currentOrder === 'desc') {
                newOrder = 'asc';
            }
            
            // Update sort state
            table.dataset.sortColumn = sortColumn;
            table.dataset.sortOrder = newOrder;
            
            // Sort table rows
            sortTable(table, sortColumn, sortType, newOrder);
            
            // Update sort icons
            updateSortIcons(table, sortColumn, newOrder);
        });
    });
}

/**
 * Sort table by column
 */
function sortTable(table, column, type, order) {
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    // Get column index
    const headers = Array.from(table.querySelectorAll('th'));
    const columnIndex = headers.findIndex(h => h.dataset.sort === column);
    
    rows.sort((a, b) => {
        const aCell = a.querySelector(`td:nth-child(${columnIndex + 1})`);
        const bCell = b.querySelector(`td:nth-child(${columnIndex + 1})`);
        
        if (!aCell || !bCell) return 0;
        
        let aValue = aCell.dataset.value !== undefined ? aCell.dataset.value : aCell.textContent.trim();
        let bValue = bCell.dataset.value !== undefined ? bCell.dataset.value : bCell.textContent.trim();
        
        if (type === 'number') {
            aValue = parseFloat(aValue) || 0;
            bValue = parseFloat(bValue) || 0;
            return order === 'asc' ? aValue - bValue : bValue - aValue;
        } else if (type === 'string') {
            aValue = String(aValue).toLowerCase();
            bValue = String(bValue).toLowerCase();
            if (order === 'asc') {
                return aValue.localeCompare(bValue);
            } else {
                return bValue.localeCompare(aValue);
            }
        }
        
        return 0;
    });
    
    // Re-append sorted rows
    rows.forEach(row => tbody.appendChild(row));
}

/**
 * Update sort icons
 */
function updateSortIcons(table, activeColumn, order) {
    const headers = table.querySelectorAll('th.sortable');
    headers.forEach(header => {
        const icon = header.querySelector('.sort-icon');
        if (header.dataset.sort === activeColumn) {
            icon.textContent = order === 'asc' ? '↑' : '↓';
            header.classList.add('sorted');
        } else {
            icon.textContent = '↕';
            header.classList.remove('sorted');
        }
    });
}

/**
 * Attach filter toggle
 */
function attachFilterToggle() {
    // This is handled in displayPlayersByPosition after rendering
}

/**
 * Attach transfer to Best Formation button
 */
function attachTransferToFormationButton() {
    // The button is added dynamically, so we'll attach listener when it's created
    // We'll call this from displayPlayersByPosition after rendering
}

/**
 * Attach transfer to Best Formation button listener (called after rendering)
 */
function attachTransferToFormationButtonListener() {
    const btn = document.getElementById('transfer-to-formation-btn');
    if (btn) {
        btn.addEventListener('click', () => {
            transferToBestFormation();
            // Update button state to show transfer was successful
            updateTransferButtonState();
        });
        updateTransferButtonState();
    }
}

/**
 * Update transfer button state based on selected players
 */
function updateTransferButtonState() {
    const btn = document.getElementById('transfer-to-formation-btn');
    if (!btn) return;
    
    const totalSelected = getTotalSelectedCount();
    
    if (totalSelected === 0) {
        btn.disabled = true;
        btn.style.opacity = '0.6';
        btn.title = 'Select players first to transfer to Best Formation';
    } else {
        btn.disabled = false;
        btn.style.opacity = '1';
        btn.title = `Transfer ${totalSelected} selected player(s) to Best Formation page`;
    }
}

/**
 * Transfer selected players to Best Formation page
 */
function transferToBestFormation() {
    const totalSelected = getTotalSelectedCount();
    
    if (totalSelected === 0) {
        alert('No players selected. Please select players first before transferring to Best Formation.');
        return;
    }
    
    // Save players - they're already saved in localStorage via saveSelectedPlayers()
    // But we can trigger a notification or redirect
    
    const confirmMessage = `Transfer ${totalSelected} selected player(s) to Best Formation page?`;
    if (confirm(confirmMessage)) {
        // Players are already in localStorage, just show success message
        // and optionally redirect
        alert(`Successfully transferred ${totalSelected} player(s) to Best Formation!\n\nYou can now go to the Best Formation page to see them.`);
        
        // Optional: redirect to Best Formation page
        // window.location.href = '/best-formation';
    }
}

/**
 * Attach transfer to Draft List button
 */
function attachTransferToDraftListButton() {
    // The button is added dynamically, so we'll attach listener when it's created
    // We'll call this from displayPlayersByPosition after rendering
}

/**
 * Attach transfer to Draft List button listener (called after rendering)
 */
function attachTransferToDraftListButtonListener() {
    const btn = document.getElementById('transfer-to-draft-list-btn');
    if (btn) {
        btn.addEventListener('click', () => {
            transferToDraftList();
            // Update button state to show transfer was successful
            updateTransferToDraftListButtonState();
        });
        updateTransferToDraftListButtonState();
    }
}

/**
 * Update transfer to Draft List button state based on selected players
 */
function updateTransferToDraftListButtonState() {
    const btn = document.getElementById('transfer-to-draft-list-btn');
    if (!btn) return;
    
    const totalSelected = getTotalSelectedCount();
    
    if (totalSelected === 0) {
        btn.disabled = true;
        btn.style.opacity = '0.6';
        btn.title = 'Select players first to transfer to Draft List';
    } else {
        btn.disabled = false;
        btn.style.opacity = '1';
        btn.title = `Transfer ${totalSelected} selected player(s) to Draft List page`;
    }
}

/**
 * Transfer selected players to Draft List page
 */
function transferToDraftList() {
    const totalSelected = getTotalSelectedCount();
    
    if (totalSelected === 0) {
        alert('No players selected. Please select players first before transferring to Draft List.');
        return;
    }
    
    // Players are already saved to draft list in localStorage via saveSelectedPlayers()
    // which saves to DRAFT_LIST_STORAGE_KEY
    
    const confirmMessage = `Transfer ${totalSelected} selected player(s) to Draft List page?`;
    if (confirm(confirmMessage)) {
        // Players are already in localStorage, just show success message
        alert(`Successfully transferred ${totalSelected} player(s) to Draft List!\n\nYou can now go to the Draft List page to see them.`);
        
        // Optional: redirect to Draft List page
        // window.location.href = '/draft-list';
    }
}

/**
 * Get total count of selected players
 */
function getTotalSelectedCount() {
    return (selectedPlayers.goalkeepers?.length || 0) +
           (selectedPlayers.defenders?.length || 0) +
           (selectedPlayers.midfielders?.length || 0) +
           (selectedPlayers.forwards?.length || 0);
}

/**
 * Fetch and display league table
 */
async function fetchAndDisplayLeagueTable() {
    const container = document.getElementById('league-table-container');
    if (!container) return;
    
    container.innerHTML = '<div class="loading-placeholder">Loading league table...</div>';
    
    try {
        const response = await fetch(API_LEAGUE_TABLE);
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.message || 'Failed to load league table');
        }
        
        displayLeagueTable(data.table);
        updateSelectedTeamsBanner();
    } catch (error) {
        container.innerHTML = `<div class="error-message">Error loading league table: ${error.message}</div>`;
        console.error('Error fetching league table:', error);
    }
}

/**
 * Display league table
 */
function displayLeagueTable(table) {
    const container = document.getElementById('league-table-container');
    if (!table || table.length === 0) {
        container.innerHTML = '<div class="loading-placeholder">No league table data available</div>';
        return;
    }
    
    const selectedTeams = new Set(getSelectedTeams());
    
    const tableHTML = `
        <table class="league-table">
            <thead>
                <tr>
                    <th>Pos</th><th>Team</th><th>Played</th><th>Won</th><th>Drawn</th><th>Lost</th>
                    <th>GF</th><th>GA</th><th>GD</th><th>Points</th><th>Last 5 Games</th><th>Form</th>
                </tr>
            </thead>
            <tbody>
                ${table.map(team => {
                    const isSelected = selectedTeams.has(team.id);
                    const rowClass = isSelected ? 'selected-team' : '';
                    const win = (team.win !== undefined && team.win !== null) ? team.win : 0;
                    const draw = (team.draw !== undefined && team.draw !== null) ? team.draw : 0;
                    const loss = (team.loss !== undefined && team.loss !== null) ? team.loss : 0;
                    const form = (team.form !== undefined && team.form !== null) ? String(team.form) : '';
                    const last5Games = team.last_5_games || [];
                    
                    return `
                        <tr class="${rowClass}">
                            <td class="position">${isSelected ? '<span class="selected-indicator">✓</span>' : ''}${team.position || ''}</td>
                            <td class="team-name-cell">${team.name || ''}<span class="short-name">(${team.short_name || ''})</span></td>
                            <td class="stats-cell">${team.played || 0}</td>
                            <td class="stats-cell" style="font-weight: 600;">${win}</td>
                            <td class="stats-cell" style="font-weight: 600;">${draw}</td>
                            <td class="stats-cell" style="font-weight: 600;">${loss}</td>
                            <td class="stats-cell">${team.goals_for || 0}</td>
                            <td class="stats-cell">${team.goals_against || 0}</td>
                            <td class="stats-cell ${team.goal_difference > 0 ? 'positive' : team.goal_difference < 0 ? 'negative' : ''}">
                                ${team.goal_difference > 0 ? '+' : ''}${team.goal_difference || 0}
                            </td>
                            <td class="stats-cell points">${team.points || 0}</td>
                            <td class="stats-cell last-5-games">${formatLast5Games(last5Games)}</td>
                            <td class="stats-cell form-badge">${formatTeamForm(form)}</td>
                        </tr>
                    `;
                }).join('')}
            </tbody>
        </table>
    `;
    container.innerHTML = tableHTML;
}

/**
 * Format team form string
 */
function formatTeamForm(form) {
    if (!form || form.length === 0) {
        return '<span style="color: #6c757d;">-</span>';
    }
    const formStr = String(form);
    return formStr.split('').map(char => {
        switch(char) {
            case 'W': return '<span style="color: #28a745; font-weight: bold;">W</span>';
            case 'D': return '<span style="color: #ffc107; font-weight: bold;">D</span>';
            case 'L': return '<span style="color: #dc3545; font-weight: bold;">L</span>';
            default: return `<span style="color: #6c757d;">${char}</span>`;
        }
    }).join('');
}

/**
 * Format last 5 games results
 */
function formatLast5Games(games) {
    if (!games || games.length === 0) {
        return '<span style="color: #6c757d;">-</span>';
    }
    
    // Games array has most recent first (index 0), but for display we want
    // oldest on left, newest on right (like typical form: "W W L D W")
    const reversedGames = [...games].reverse();
    
    return reversedGames.map(game => {
        const result = game.result || '-';
        const opponent = game.opponent || '';
        const teamScore = game.team_score || 0;
        const opponentScore = game.opponent_score || 0;
        const isHome = game.is_home || false;
        
        let resultColor;
        let resultBg;
        switch(result) {
            case 'W':
                resultColor = '#28a745';
                resultBg = '#d4edda';
                break;
            case 'D':
                resultColor = '#ffc107';
                resultBg = '#fff3cd';
                break;
            case 'L':
                resultColor = '#dc3545';
                resultBg = '#f8d7da';
                break;
            default:
                resultColor = '#6c757d';
                resultBg = '#e9ecef';
        }
        
        const scoreText = game.result === '-' ? '' : ` ${teamScore}-${opponentScore}`;
        const venue = isHome ? 'H' : 'A';
        
        return `<span class="last-game-result" style="background-color: ${resultBg}; color: ${resultColor}; font-weight: bold; padding: 2px 6px; border-radius: 3px; margin: 0 2px; display: inline-block; min-width: 40px; text-align: center;" title="${opponent}${scoreText} (${venue})">${result}</span>`;
    }).join('');
}

/**
 * Update selected teams banner
 */
function updateSelectedTeamsBanner() {
    const banner = document.getElementById('selected-teams-info');
    if (!banner) return;
    
    const selectedTeams = getSelectedTeams();
    if (selectedTeams.length > 0) {
        banner.innerHTML = `
            <div class="selected-teams-message">
                <span class="selected-count">You have ${selectedTeams.length} team(s) picked for analysis.</span>
                <a href="/team-analysis" class="edit-selection-link">Edit Selection</a>
            </div>
        `;
    } else {
        banner.innerHTML = `
            <div class="info-message">
                No teams currently picked for analysis. Go to <a href="/team-analysis">Team Analysis</a> to pick teams.
            </div>
        `;
    }
}
