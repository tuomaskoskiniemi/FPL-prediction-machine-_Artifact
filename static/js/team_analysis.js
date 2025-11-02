/**
 * Team Analysis JavaScript
 * Handles team analysis data display, FDR calculations, and team selection
 */

const API_TEAM_ANALYSIS = '/api/team-analysis';
const STORAGE_KEY = 'fpl_selected_teams';

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadTeamAnalysis();
});

/**
 * Load team analysis data
 */
async function loadTeamAnalysis() {
    const container = document.getElementById('team-analysis-container');
    
    try {
        const response = await fetch(API_TEAM_ANALYSIS);
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.message || 'Failed to load team analysis data');
        }
        
        displayTeamAnalysis(data.teams);
    } catch (error) {
        container.innerHTML = `
            <div class="error-message">
                Error loading team analysis: ${error.message}
            </div>
        `;
        console.error('Error loading team analysis:', error);
    }
}

/**
 * Display team analysis data
 */
function displayTeamAnalysis(teams) {
    const container = document.getElementById('team-analysis-container');
    
    if (!teams || teams.length === 0) {
        container.innerHTML = '<div class="loading-placeholder">No team data available</div>';
        return;
    }
    
    // Load saved selections
    const selectedTeams = loadSelectedTeams();
    
    // Sort teams by FDR (smallest first)
    // Use adjusted_fdr_next_5 as primary, fallback to fdr_next_5, then fdr_next_10
    const sortedTeams = [...teams].sort((a, b) => {
        const getFDRValue = (team) => {
            // Prioritize adjusted FDR next 5, then regular FDR next 5, then FDR next 10
            if (team.adjusted_fdr_next_5 !== null && team.adjusted_fdr_next_5 !== undefined) {
                return team.adjusted_fdr_next_5;
            }
            if (team.fdr_next_5 !== null && team.fdr_next_5 !== undefined) {
                return team.fdr_next_5;
            }
            if (team.fdr_next_10 !== null && team.fdr_next_10 !== undefined) {
                return team.fdr_next_10;
            }
            return 999; // Teams with no FDR go to the end
        };
        
        const fdrA = getFDRValue(a);
        const fdrB = getFDRValue(b);
        return fdrA - fdrB;
    });
    
    // Create analysis cards for each team
    const teamsHTML = sortedTeams.map(team => createTeamCard(team, selectedTeams.includes(team.team_id))).join('');
    
    container.innerHTML = `
        <div class="team-analysis-intro">
            <p>Select teams you plan to pick players from. Your selections will be highlighted in the Player Analysis page.</p>
        </div>
        <div class="teams-analysis-grid">
            ${teamsHTML}
        </div>
    `;
    
    // Attach event listeners for team selection
    attachSelectionListeners();
}

/**
 * Create HTML card for a team
 */
function createTeamCard(team, isSelected) {
    const selectedClass = isSelected ? 'selected' : '';
    const fdr5Color = getFDRColor(team.fdr_next_5);
    const fdr10Color = getFDRColor(team.fdr_next_10);
    const adjFdr5Color = getFDRColor(team.adjusted_fdr_next_5);
    const adjFdr10Color = getFDRColor(team.adjusted_fdr_next_10);
    
    return `
        <div class="team-analysis-card ${selectedClass}" data-team-id="${team.team_id}">
            <div class="team-card-header">
                <h3 class="team-card-name">${team.team_name}</h3>
                <label class="team-select-checkbox">
                    <input type="checkbox" ${isSelected ? 'checked' : ''} data-team-id="${team.team_id}">
                    <span class="checkbox-label">Select Team</span>
                </label>
            </div>
            
            <div class="team-metrics">
                <div class="metric-section">
                    <h4>Fixture Difficulty (FDR)</h4>
                    <div class="metric-row">
                        <div class="metric-item">
                            <span class="metric-label">Next 5 Games:</span>
                            <span class="metric-value fdr-value" style="color: ${fdr5Color}">
                                ${team.fdr_next_5 !== null ? team.fdr_next_5.toFixed(2) : 'N/A'}
                            </span>
                        </div>
                        <div class="metric-item">
                            <span class="metric-label">Next 10 Games:</span>
                            <span class="metric-value fdr-value" style="color: ${fdr10Color}">
                                ${team.fdr_next_10 !== null ? team.fdr_next_10.toFixed(2) : 'N/A'}
                            </span>
                        </div>
                    </div>
                    <div class="metric-row">
                        <div class="metric-item">
                            <span class="metric-label">Adjusted FDR (5):</span>
                            <span class="metric-value fdr-value" style="color: ${adjFdr5Color}">
                                ${team.adjusted_fdr_next_5 !== null ? team.adjusted_fdr_next_5.toFixed(2) : 'N/A'}
                            </span>
                        </div>
                        <div class="metric-item">
                            <span class="metric-label">Adjusted FDR (10):</span>
                            <span class="metric-value fdr-value" style="color: ${adjFdr10Color}">
                                ${team.adjusted_fdr_next_10 !== null ? team.adjusted_fdr_next_10.toFixed(2) : 'N/A'}
                            </span>
                        </div>
                    </div>
                </div>
                
                <div class="metric-section">
                    <h4>Performance (Points Per Game)</h4>
                    <div class="metric-row">
                        <div class="metric-item">
                            <span class="metric-label">Last 5 Games:</span>
                            <span class="metric-value">
                                ${team.ppg_last_5 !== null ? team.ppg_last_5.toFixed(2) : 'N/A'}
                                ${team.games_played_last_5 < 5 ? `(${team.games_played_last_5} games)` : ''}
                            </span>
                        </div>
                        <div class="metric-item">
                            <span class="metric-label">Last 10 Games:</span>
                            <span class="metric-value">
                                ${team.ppg_last_10 !== null ? team.ppg_last_10.toFixed(2) : 'N/A'}
                                ${team.games_played_last_10 < 10 ? `(${team.games_played_last_10} games)` : ''}
                            </span>
                        </div>
                    </div>
                </div>
                
                <div class="upcoming-fixtures">
                    <h4>Next 5 Fixtures</h4>
                    <div class="fixtures-list">
                        ${team.next_5_fixtures.map(fixture => {
                            const isHome = fixture.team_h.id === team.team_id;
                            const homeAway = isHome ? 'Home' : 'Away';
                            const homeAwayClass = isHome ? 'home' : 'away';
                            return `
                            <div class="fixture-item">
                                <div class="fixture-main-info">
                                    <span class="fixture-opponent">${getOpponentName(fixture, team.team_id)}</span>
                                    <span class="fixture-home-away ${homeAwayClass}">${homeAway}</span>
                                </div>
                                <div class="fixture-secondary-info">
                                    <span class="fixture-difficulty difficulty-${getFixtureDifficulty(fixture, team.team_id)}">
                                        ${getFixtureDifficulty(fixture, team.team_id)}
                                    </span>
                                    <span class="fixture-date">${formatFixtureDate(fixture.kickoff_time)}</span>
                                </div>
                            </div>
                        `;
                        }).join('')}
                    </div>
                </div>
            </div>
        </div>
    `;
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
 * Get opponent name from fixture
 */
function getOpponentName(fixture, teamId) {
    if (fixture.team_h.id === teamId) {
        return fixture.team_a.short_name || fixture.team_a.name;
    }
    return fixture.team_h.short_name || fixture.team_h.name;
}

/**
 * Get fixture difficulty for a team
 */
function getFixtureDifficulty(fixture, teamId) {
    if (fixture.team_h.id === teamId) {
        return fixture.team_h.difficulty || 3;
    }
    return fixture.team_a.difficulty || 3;
}

/**
 * Format fixture date
 */
function formatFixtureDate(dtString) {
    if (!dtString) return 'TBD';
    try {
        const dt = new Date(dtString);
        return dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    } catch {
        return dtString;
    }
}

/**
 * Attach selection listeners
 */
function attachSelectionListeners() {
    const checkboxes = document.querySelectorAll('.team-select-checkbox input[type="checkbox"]');
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', (e) => {
            const teamId = parseInt(e.target.dataset.teamId);
            const card = e.target.closest('.team-analysis-card');
            
            if (e.target.checked) {
                selectTeam(teamId);
                card.classList.add('selected');
            } else {
                deselectTeam(teamId);
                card.classList.remove('selected');
            }
        });
    });
}

/**
 * Select a team
 */
function selectTeam(teamId) {
    const selected = loadSelectedTeams();
    if (!selected.includes(teamId)) {
        selected.push(teamId);
        saveSelectedTeams(selected);
    }
}

/**
 * Deselect a team
 */
function deselectTeam(teamId) {
    const selected = loadSelectedTeams();
    const index = selected.indexOf(teamId);
    if (index > -1) {
        selected.splice(index, 1);
        saveSelectedTeams(selected);
    }
}

/**
 * Load selected teams from localStorage
 */
function loadSelectedTeams() {
    try {
        const stored = localStorage.getItem(STORAGE_KEY);
        return stored ? JSON.parse(stored) : [];
    } catch {
        return [];
    }
}

/**
 * Save selected teams to localStorage
 */
function saveSelectedTeams(teams) {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(teams));
    } catch (error) {
        console.error('Error saving selected teams:', error);
    }
}

