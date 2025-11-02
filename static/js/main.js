/**
 * Main JavaScript for FPL Prediction Machine frontend
 * Handles data fetching, UI updates, and animations
 */

// API endpoints
const API_BASE = '';
const API_UPDATE = `${API_BASE}/api/update`;
const API_GAMEWEEK = `${API_BASE}/api/current-gameweek`;
const API_LEAGUE_TABLE = `${API_BASE}/api/league-table`;

// DOM elements
let updateBtn;
let updateIcon;
let loadingIndicator;
let statusMessage;
let fixturesContainer;
let leagueTableContainer;
let gameweekInfo;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initializeElements();
    setupEventListeners();
    loadInitialData();
});

function initializeElements() {
    updateBtn = document.getElementById('update-btn');
    updateIcon = document.getElementById('update-icon');
    loadingIndicator = document.getElementById('loading-indicator');
    statusMessage = document.getElementById('status-message');
    fixturesContainer = document.getElementById('fixtures-container');
    leagueTableContainer = document.getElementById('league-table-container');
    gameweekInfo = document.getElementById('gameweek-info');
}

function setupEventListeners() {
    updateBtn.addEventListener('click', handleManualUpdate);
}

/**
 * Load initial data when page loads
 */
async function loadInitialData() {
    showLoadingIndicator();
    try {
        await Promise.all([
            loadCurrentGameweek(),
            loadLeagueTable()
        ]);
        hideLoadingIndicator();
        showStatusMessage('Data loaded successfully!', 'success');
    } catch (error) {
        hideLoadingIndicator();
        showStatusMessage('Error loading data: ' + error.message, 'error');
        console.error('Error loading initial data:', error);
    }
}

/**
 * Handle manual update button click
 */
async function handleManualUpdate() {
    updateBtn.disabled = true;
    showLoadingIndicator();
    clearStatusMessage();
    
    try {
        // First update the data
        const updateResponse = await fetch(API_UPDATE, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const updateData = await updateResponse.json();
        
        if (!updateData.success) {
            throw new Error(updateData.message || 'Update failed');
        }
        
        // Then refresh the displayed data
        await Promise.all([
            loadCurrentGameweek(),
            loadLeagueTable()
        ]);
        
        hideLoadingIndicator();
        updateBtn.disabled = false;
        showStatusMessage('Data updated successfully!', 'success');
    } catch (error) {
        hideLoadingIndicator();
        updateBtn.disabled = false;
        showStatusMessage('Error updating data: ' + error.message, 'error');
        console.error('Error updating data:', error);
    }
}

/**
 * Load and display current gameweek fixtures
 */
async function loadCurrentGameweek() {
    try {
        const response = await fetch(API_GAMEWEEK);
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.message || 'Failed to load gameweek data');
        }
        
        displayGameweekInfo(data.current_gameweek);
        displayFixtures(data.fixtures);
    } catch (error) {
        fixturesContainer.innerHTML = `
            <div class="error-message">
                Error loading fixtures: ${error.message}
            </div>
        `;
        throw error;
    }
}

/**
 * Display gameweek information
 */
function displayGameweekInfo(gameweek) {
    if (gameweek) {
        gameweekInfo.textContent = `Gameweek ${gameweek}`;
    } else {
        gameweekInfo.textContent = 'No current gameweek';
    }
}

/**
 * Display fixtures in the fixtures container
 */
function displayFixtures(fixtures) {
    if (!fixtures || fixtures.length === 0) {
        fixturesContainer.innerHTML = `
            <div class="loading-placeholder">
                No fixtures available for current gameweek
            </div>
        `;
        return;
    }
    
    fixturesContainer.innerHTML = fixtures.map(fixture => createFixtureCard(fixture)).join('');
}

/**
 * Create HTML for a fixture card
 */
function createFixtureCard(fixture) {
    const { team_h, team_a, kickoff_time, status, minutes } = fixture;
    const formattedTime = formatDateTime(kickoff_time);
    
    // Determine if score should be shown
    const showScore = status === 'finished' || status === 'live';
    const homeScore = showScore && fixture.team_h.score !== null ? fixture.team_h.score : '-';
    const awayScore = showScore && fixture.team_a.score !== null ? fixture.team_a.score : '-';
    
    // Get team form (last 5 results)
    const homeForm = formatTeamForm(fixture.team_h.form);
    const awayForm = formatTeamForm(fixture.team_a.form);
    
    return `
        <div class="fixture-card ${status}">
            <div class="match-teams">
                <div class="team">
                    <div class="team-name">${team_h.name}</div>
                    <div class="team-short">${team_h.short_name}</div>
                    <div class="team-score">${homeScore}</div>
                    <div class="difficulty-badge difficulty-${fixture.team_h.difficulty}">${fixture.team_h.difficulty}</div>
                    ${homeForm ? `<div class="team-form">Form: ${homeForm}</div>` : ''}
                </div>
                <div class="vs-divider">vs</div>
                <div class="team">
                    <div class="team-name">${team_a.name}</div>
                    <div class="team-short">${team_a.short_name}</div>
                    <div class="team-score">${awayScore}</div>
                    <div class="difficulty-badge difficulty-${fixture.team_a.difficulty}">${fixture.team_a.difficulty}</div>
                    ${awayForm ? `<div class="team-form">Form: ${awayForm}</div>` : ''}
                </div>
            </div>
            <div class="match-info">
                <div class="match-time">${formattedTime}</div>
                <span class="match-status ${status}">${status}</span>
                ${status === 'live' && minutes ? `<div style="margin-top: 5px; font-size: 0.85rem;">${minutes}'</div>` : ''}
            </div>
        </div>
    `;
}

/**
 * Load and display league table
 */
async function loadLeagueTable() {
    try {
        const response = await fetch(API_LEAGUE_TABLE);
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.message || 'Failed to load league table');
        }
        
        displayLeagueTable(data.table);
    } catch (error) {
        leagueTableContainer.innerHTML = `
            <div class="error-message">
                Error loading league table: ${error.message}
            </div>
        `;
        throw error;
    }
}

/**
 * Display league table
 */
function displayLeagueTable(table) {
    if (!table || table.length === 0) {
        leagueTableContainer.innerHTML = `
            <div class="loading-placeholder">
                No league table data available
            </div>
        `;
        return;
    }
    
    console.log('Displaying league table with', table.length, 'teams');
    console.log('Sample team data:', table[0]);
    
    const tableHTML = `
        <table class="league-table">
            <thead>
                <tr>
                    <th>Pos</th>
                    <th>Team</th>
                    <th>Played</th>
                    <th>Won</th>
                    <th>Drawn</th>
                    <th>Lost</th>
                    <th>GF</th>
                    <th>GA</th>
                    <th>GD</th>
                    <th>Points</th>
                    <th>Form</th>
                </tr>
            </thead>
            <tbody>
                ${table.map((team, index) => {
                    // Ensure all values are present, handle null/undefined
                    const win = (team.win !== undefined && team.win !== null) ? team.win : 0;
                    const draw = (team.draw !== undefined && team.draw !== null) ? team.draw : 0;
                    const loss = (team.loss !== undefined && team.loss !== null) ? team.loss : 0;
                    const form = (team.form !== undefined && team.form !== null) ? String(team.form) : '';
                    
                    // Debug log for first team
                    if (index === 0) {
                        console.log('First team data:', { win, draw, loss, form, team });
                    }
                    
                    return `
                    <tr>
                        <td class="position">${team.position || ''}</td>
                        <td class="team-name-cell">
                            ${team.name || ''}
                            <span class="short-name">(${team.short_name || ''})</span>
                        </td>
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
                        <td class="stats-cell form-badge">${formatTeamForm(form)}</td>
                    </tr>
                `;
                }).join('')}
            </tbody>
        </table>
    `;
    
    leagueTableContainer.innerHTML = tableHTML;
    console.log('League table rendered');
}

/**
 * Format datetime string for display
 */
function formatDateTime(dtString) {
    if (!dtString) return 'TBD';
    
    try {
        const dt = new Date(dtString);
        return dt.toLocaleString('en-US', {
            weekday: 'short',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch (error) {
        return dtString;
    }
}

/**
 * Format team form string (e.g., "WWDLW") for display
 */
function formatTeamForm(form) {
    if (!form || form.length === 0) {
        return '<span style="color: #6c757d;">-</span>';
    }
    
    // Ensure form is a string
    const formStr = String(form);
    
    // Map form characters to colors
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
 * Show loading indicator with rolling football animation
 */
function showLoadingIndicator() {
    loadingIndicator.classList.remove('hidden');
    updateIcon.textContent = '⚽';
}

/**
 * Hide loading indicator
 */
function hideLoadingIndicator() {
    loadingIndicator.classList.add('hidden');
}

/**
 * Show status message
 */
function showStatusMessage(message, type = 'success') {
    statusMessage.textContent = message;
    statusMessage.className = `status-message ${type}`;
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        clearStatusMessage();
    }, 5000);
}

/**
 * Clear status message
 */
function clearStatusMessage() {
    statusMessage.textContent = '';
    statusMessage.className = 'status-message';
}

