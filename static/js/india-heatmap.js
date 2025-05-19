/**
 * India Renewable Energy Projects Heatmap
 * This script manages the heatmap visualization for projects by state
 */

// Initialize the heatmap when the document is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeStateHeatmap();
});

function initializeStateHeatmap() {
    // Get the map container
    const mapContainer = document.getElementById('india-map');
    if (!mapContainer) return;
    
    // Clear the container
    mapContainer.innerHTML = '';
    
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
    // Define color scale
    const maxProjects = Math.max(...stateData.map(d => d.count));
    
    // Create the map container
    const mapDiv = document.createElement('div');
    mapDiv.className = 'india-map-container';
    container.appendChild(mapDiv);
    
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
    
    // Create a color key
    const colorKeyDiv = document.createElement('div');
    colorKeyDiv.className = 'mt-3';
    colorKeyDiv.innerHTML = `
        <h6 class="mb-2">Project Counts by State</h6>
        <div class="row">
            ${stateData.sort((a, b) => b.count - a.count).slice(0, 10).map(data => `
                <div class="col-md-6">
                    <div class="d-flex justify-content-between">
                        <div>${data.state}</div>
                        <div><strong>${data.count}</strong></div>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
    
    // Fetch and render the India SVG map
    fetch('/static/img/india-map.svg')
        .then(response => {
            if (!response.ok) {
                // If the SVG doesn't exist, create a placeholder
                mapDiv.innerHTML = `
                    <div class="india-map-placeholder p-5 text-center">
                        <div style="height: 300px;" class="d-flex flex-column justify-content-center">
                            <i class="fas fa-map-marked-alt fa-4x mb-3 text-muted"></i>
                            <p>India state heatmap visualization</p>
                            <div class="heatmap-bars">
                                ${stateData.sort((a, b) => b.count - a.count).slice(0, 8).map(data => {
                                    const percentage = (data.count / maxProjects * 100).toFixed(0);
                                    return `
                                        <div class="heatmap-bar-item mb-2">
                                            <div class="d-flex justify-content-between mb-1">
                                                <small>${data.state}</small>
                                                <small>${data.count} projects</small>
                                            </div>
                                            <div class="progress" style="height: 12px;">
                                                <div class="progress-bar bg-success" role="progressbar" 
                                                    style="width: ${percentage}%" 
                                                    aria-valuenow="${data.count}" 
                                                    aria-valuemin="0" 
                                                    aria-valuemax="${maxProjects}">
                                                </div>
                                            </div>
                                        </div>
                                    `;
                                }).join('')}
                            </div>
                        </div>
                    </div>
                `;
                
                // Add the legend and color key
                container.appendChild(legendDiv);
                container.appendChild(colorKeyDiv);
                
                // Create the SVG file for future use
                createIndiaMapSVG();
            } else {
                return response.text()
                    .then(svgText => {
                        // Render the SVG map with the heatmap data
                        mapDiv.innerHTML = svgText;
                        colorizeMapStates(mapDiv, stateData, maxProjects);
                        
                        // Add the legend and color key
                        container.appendChild(legendDiv);
                        container.appendChild(colorKeyDiv);
                    });
            }
        })
        .catch(error => {
            console.error('Error loading India map SVG:', error);
            mapDiv.innerHTML = `
                <div class="alert alert-warning p-5 text-center">
                    <i class="fas fa-map-marked-alt fa-4x mb-3"></i>
                    <p>Unable to load map visualization.</p>
                    <p>Showing state data as a bar chart instead:</p>
                    <div class="heatmap-bars">
                        ${stateData.sort((a, b) => b.count - a.count).map(data => {
                            const percentage = (data.count / maxProjects * 100).toFixed(0);
                            return `
                                <div class="heatmap-bar-item mb-2">
                                    <div class="d-flex justify-content-between mb-1">
                                        <small>${data.state}</small>
                                        <small>${data.count} projects</small>
                                    </div>
                                    <div class="progress" style="height: 10px;">
                                        <div class="progress-bar bg-success" role="progressbar" 
                                            style="width: ${percentage}%" 
                                            aria-valuenow="${data.count}" 
                                            aria-valuemin="0" 
                                            aria-valuemax="${maxProjects}">
                                        </div>
                                    </div>
                                </div>
                            `;
                        }).join('')}
                    </div>
                </div>
            `;
        });
}

function colorizeMapStates(mapDiv, stateData, maxProjects) {
    // Get all state paths from the SVG
    const stateElements = mapDiv.querySelectorAll('path[id], g[id]');
    
    // Create a mapping of state names to their normalized forms
    const stateMapping = {
        'andhra pradesh': 'Andhra Pradesh',
        'arunachal pradesh': 'Arunachal Pradesh',
        'assam': 'Assam',
        'bihar': 'Bihar',
        'chhattisgarh': 'Chhattisgarh',
        'goa': 'Goa',
        'gujarat': 'Gujarat',
        'haryana': 'Haryana',
        'himachal pradesh': 'Himachal Pradesh',
        'jharkhand': 'Jharkhand',
        'karnataka': 'Karnataka',
        'kerala': 'Kerala',
        'madhya pradesh': 'Madhya Pradesh',
        'maharashtra': 'Maharashtra',
        'manipur': 'Manipur',
        'meghalaya': 'Meghalaya',
        'mizoram': 'Mizoram',
        'nagaland': 'Nagaland',
        'odisha': 'Odisha',
        'punjab': 'Punjab',
        'rajasthan': 'Rajasthan',
        'sikkim': 'Sikkim',
        'tamil nadu': 'Tamil Nadu',
        'telangana': 'Telangana',
        'tripura': 'Tripura',
        'uttar pradesh': 'Uttar Pradesh',
        'uttarakhand': 'Uttarakhand',
        'west bengal': 'West Bengal',
        'andaman and nicobar islands': 'Andaman and Nicobar Islands',
        'chandigarh': 'Chandigarh',
        'dadra and nagar haveli': 'Dadra and Nagar Haveli',
        'daman and diu': 'Daman and Diu',
        'delhi': 'Delhi',
        'jammu and kashmir': 'Jammu and Kashmir',
        'ladakh': 'Ladakh',
        'lakshadweep': 'Lakshadweep',
        'puducherry': 'Puducherry'
    };
    
    // Color each state based on project count
    stateElements.forEach(element => {
        // Get the state name from the element id
        const stateId = element.id.toLowerCase().replace(/_/g, ' ');
        
        // Find the normalized state name
        const normalizedState = stateMapping[stateId] || stateId;
        
        // Find the state data
        const stateInfo = stateData.find(d => d.state.toLowerCase() === normalizedState.toLowerCase());
        
        if (stateInfo) {
            // Calculate color based on project count
            const intensity = stateInfo.count / maxProjects;
            const color = getHeatmapColor(intensity);
            
            // Apply color to the state
            element.style.fill = color;
            
            // Add a tooltip with the state name and project count
            element.setAttribute('data-bs-toggle', 'tooltip');
            element.setAttribute('data-bs-title', `${stateInfo.state}: ${stateInfo.count} projects`);
            
            // Add hover effect
            element.addEventListener('mouseover', function() {
                this.style.fillOpacity = 0.8;
                this.style.stroke = '#333';
                this.style.strokeWidth = '2';
            });
            
            element.addEventListener('mouseout', function() {
                this.style.fillOpacity = 1;
                this.style.stroke = '#000';
                this.style.strokeWidth = '1';
            });
        } else {
            // Default color for states with no data
            element.style.fill = '#f8f9fa';
        }
    });
    
    // Initialize tooltips
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        const tooltipTriggerList = [].slice.call(mapDiv.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
    }
}

function getHeatmapColor(intensity) {
    // Generate heatmap color from green (low) to red (high)
    const r = Math.floor(intensity * 255);
    const g = Math.floor(255 - (intensity * 155));
    const b = 50;
    return `rgb(${r}, ${g}, ${b})`;
}

function createIndiaMapSVG() {
    // This function can be expanded to create a basic SVG of India
    // For now, we'll rely on the placeholder bar chart visualization
    console.log('Creating India map SVG is not implemented yet');
}