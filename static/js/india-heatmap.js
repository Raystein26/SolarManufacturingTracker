/**
 * India Renewable Energy Projects Heatmap
 * This script manages the heatmap visualization for projects by state
 */

// Initialize the heatmap when the document is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Add event listener to the map-view-btn to initialize heatmap on click
    const mapViewBtn = document.getElementById('map-view-btn');
    if (mapViewBtn) {
        mapViewBtn.addEventListener('click', initializeStateHeatmap);
    }
});

function initializeStateHeatmap() {
    // Get the map container
    const mapContainer = document.getElementById('india-map');
    if (!mapContainer) return;
    
    // Fetch the state project data
    fetchStateProjectData()
        .then(stateData => {
            // Create and render the heatmap
            renderHeatmap(mapContainer, stateData);
        })
        .catch(error => {
            console.error('Error loading heatmap data:', error);
            mapContainer.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-circle me-2"></i>
                    Error loading map data: ${error.message}
                </div>
            `;
        });
}

function fetchStateProjectData() {
    // Create a promise to fetch state project data
    return new Promise((resolve, reject) => {
        // Extract data from the project by state chart
        const chartElement = document.getElementById('projects-by-state-chart');
        
        if (!chartElement) {
            reject(new Error('Chart element not found'));
            return;
        }
        
        try {
            // Parse the data attributes
            const stateLabels = chartElement.dataset.labels.split(',');
            const stateCounts = chartElement.dataset.values.split(',').map(Number);
            
            // Map to state data objects
            const stateData = stateLabels.map((state, index) => ({
                state: state,
                count: stateCounts[index]
            }));
            
            resolve(stateData);
        } catch (error) {
            reject(error);
        }
    });
}

function renderHeatmap(container, stateData) {
    // Clear the container first
    container.innerHTML = '';
    
    // Define color scale
    const maxProjects = Math.max(...stateData.map(d => d.count));
    
    // Create the heatmap container
    const heatmapContainer = document.createElement('div');
    heatmapContainer.className = 'heatmap-container';
    container.appendChild(heatmapContainer);
    
    // Create the table visualization
    const tableDiv = document.createElement('div');
    tableDiv.className = 'table-responsive mt-3';
    
    // Check if we have any data
    if (stateData.length === 0) {
        tableDiv.innerHTML = `
            <div class="alert alert-info text-center">
                <i class="fas fa-info-circle me-2"></i>
                No project data available for states.
            </div>
        `;
    } else {
        // Sort states by project count (descending)
        const sortedData = [...stateData].sort((a, b) => b.count - a.count);
        
        // Create an HTML table
        let tableHtml = `
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th>State</th>
                        <th>Projects</th>
                        <th>Distribution</th>
                    </tr>
                </thead>
                <tbody>
        `;
        
        // Add rows for each state
        sortedData.forEach(state => {
            const percentage = (state.count / maxProjects * 100).toFixed(0);
            
            // Generate heat color based on percentage
            const red = Math.min(255, Math.floor(percentage * 2.55));
            const green = Math.min(255, Math.floor(255 - percentage * 1.5));
            const blue = 50;
            const colorStyle = `rgb(${red}, ${green}, ${blue})`;
            
            tableHtml += `
                <tr>
                    <td>${state.state}</td>
                    <td>${state.count}</td>
                    <td>
                        <div class="progress" style="height: 15px;">
                            <div class="progress-bar" role="progressbar" 
                                 style="width: ${percentage}%; background-color: ${colorStyle};" 
                                 aria-valuenow="${state.count}" 
                                 aria-valuemin="0" 
                                 aria-valuemax="${maxProjects}">
                                ${percentage}%
                            </div>
                        </div>
                    </td>
                </tr>
            `;
        });
        
        tableHtml += `
                </tbody>
            </table>
        `;
        
        tableDiv.innerHTML = tableHtml;
    }
    
    // Add the table to the container
    heatmapContainer.appendChild(tableDiv);
    
    // Create a legend
    const legendDiv = document.createElement('div');
    legendDiv.className = 'heatmap-legend mt-3';
    legendDiv.innerHTML = `
        <div class="d-flex justify-content-between">
            <div><small>Fewer Projects</small></div>
            <div><small>More Projects</small></div>
        </div>
        <div class="heatmap-legend-gradient"></div>
        <div class="d-flex justify-content-between">
            <div><small>0</small></div>
            <div><small>${maxProjects}</small></div>
        </div>
    `;
    
    // Add the legend
    container.appendChild(legendDiv);
}

// Handle project type filter buttons
function updateHeatmapByProjectType(projectType) {
    // This function would be enhanced to filter the data
    // by project type and update the visualization
    console.log(`Updating heatmap to show ${projectType} projects`);
    
    // For now, just reinitialize the heatmap
    initializeStateHeatmap();
}