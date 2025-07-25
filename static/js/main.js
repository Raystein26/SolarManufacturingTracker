document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Run manual source check
    const manualCheckButton = document.getElementById('manual-check-button');
    if (manualCheckButton) {
        manualCheckButton.addEventListener('click', function() {
            runManualCheck();
        });
    }

    // Export to Excel 
    const exportExcelButton = document.getElementById('export-excel-button');
    if (exportExcelButton) {
        exportExcelButton.addEventListener('click', function() {
            exportToExcel();
        });
    }
    
    // Data cleanup
    const cleanupDataButton = document.getElementById('cleanup-data-button');
    if (cleanupDataButton) {
        cleanupDataButton.addEventListener('click', function() {
            cleanupData();
        });
    }

    // Filter projects by type
    const projectTypeFilter = document.getElementById('project-type-filter');
    if (projectTypeFilter) {
        projectTypeFilter.addEventListener('change', function() {
            window.location.href = '/projects?type=' + this.value;
        });
    }

    // Initialize charts on dashboard
    initializeCharts();
});

function runManualCheck() {
    // Show loading state
    const button = document.getElementById('manual-check-button');
    if (!button) return; // Exit if button isn't found
    
    const originalText = button.innerHTML;
    const progressContainer = document.getElementById('update-progress-container');
    const progressBar = document.getElementById('update-progress-bar');
    const progressText = document.getElementById('update-progress-text');
    
    // Check if the progress elements exist
    if (!progressContainer || !progressBar || !progressText) return;
    
    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Running...';
    
    // Show progress container
    progressContainer.style.display = 'block';
    progressBar.style.width = '0%';
    progressText.textContent = 'Initializing...';
    
    // Make API call to run check
    fetch('/api/run-check', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({}) // Add empty JSON body
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        // Show success/error message
        const alertsContainer = document.getElementById('alerts-container');
        
        if (data.status === 'success') {
            alertsContainer.innerHTML = `
                <div class="alert alert-success alert-dismissible fade show" role="alert">
                    Check started in background. This may take several minutes.
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                </div>
            `;
            
            // Start progress checking
            let sourceCount = 0;
            let processedCount = 0;
            let progressInterval;
            
            // Get the total number of sources first
            fetch('/api/sources')
                .then(response => response.json())
                .then(sources => {
                    sourceCount = sources.length;
                    progressText.textContent = `Processing sources: 0/${sourceCount}`;
                    
                    // Check progress periodically
                    progressInterval = setInterval(() => {
                        fetch('/api/check-progress')
                            .then(response => response.json())
                            .then(progress => {
                                if (progress.completed) {
                                    clearInterval(progressInterval);
                                    progressBar.style.width = '100%';
                                    progressText.textContent = `Completed: ${progress.processed_sources}/${sourceCount} sources, ${progress.projects_added} projects added`;
                                    
                                    setTimeout(() => {
                                        // Hide progress after a delay
                                        progressContainer.style.display = 'none';
                                    }, 5000);
                                } else {
                                    processedCount = progress.processed_sources;
                                    const percent = Math.round((processedCount / sourceCount) * 100);
                                    progressBar.style.width = `${percent}%`;
                                    progressText.textContent = `Processing sources: ${processedCount}/${sourceCount}, ${progress.projects_added} projects added`;
                                }
                            })
                            .catch(error => {
                                console.error('Error checking progress:', error);
                            });
                    }, 2000); // Check every 2 seconds
                });
        } else {
            progressContainer.style.display = 'none';
            
            alertsContainer.innerHTML = `
                <div class="alert alert-danger alert-dismissible fade show" role="alert">
                    Error: ${data.message}
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                </div>
            `;
        }
        
        // Reset button
        button.disabled = false;
        button.innerHTML = originalText;
    })
    .catch(error => {
        // Show error message
        progressContainer.style.display = 'none';
        
        const alertsContainer = document.getElementById('alerts-container');
        alertsContainer.innerHTML = `
            <div class="alert alert-danger alert-dismissible fade show" role="alert">
                Error: ${error.message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
        
        // Reset button
        button.disabled = false;
        button.innerHTML = originalText;
    });
}

function exportToExcel() {
    // Show loading state
    const button = document.getElementById('export-excel-button');
    const originalText = button.innerHTML;
    
    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Exporting...';
    
    // Make API call to export
    fetch('/api/export-excel')
    .then(response => response.json())
    .then(data => {
        // Reset button
        button.disabled = false;
        button.innerHTML = originalText;
        
        // Show success/error message
        const alertsContainer = document.getElementById('alerts-container');
        
        if (data.status === 'success') {
            // Create an absolute URL for the download
            const downloadUrl = window.location.origin + data.filename;
            
            alertsContainer.innerHTML = `
                <div class="alert alert-success alert-dismissible fade show" role="alert">
                    Export successful! <a href="${downloadUrl}" class="alert-link">Download Excel File</a>
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                </div>
            `;
            
            // Automatically open the download in a new window/tab
            window.open(downloadUrl, '_blank');
        } else {
            alertsContainer.innerHTML = `
                <div class="alert alert-danger alert-dismissible fade show" role="alert">
                    Error: ${data.message}
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                </div>
            `;
        }
    })
    .catch(error => {
        // Reset button
        button.disabled = false;
        button.innerHTML = originalText;
        
        // Show error message
        const alertsContainer = document.getElementById('alerts-container');
        alertsContainer.innerHTML = `
            <div class="alert alert-danger alert-dismissible fade show" role="alert">
                Error: ${error.message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
    });
}

function initializeCharts() {
    // Initialize projects by type chart
    const projectsByTypeChart = document.getElementById('projects-by-type-chart');
    if (projectsByTypeChart) {
        const labels = Array.from(projectsByTypeChart.dataset.labels.split(','));
        const data = Array.from(projectsByTypeChart.dataset.values.split(','), Number);
        
        // Create dynamic color array based on the number of project types
        const backgroundColors = [];
        for (let i = 0; i < labels.length; i++) {
            // Assign standard colors based on project type
            if (labels[i].toLowerCase().includes('solar')) {
                backgroundColors.push('#ffc107'); // Solar - Yellow/Warning
            } else if (labels[i].toLowerCase().includes('battery')) {
                backgroundColors.push('#0dcaf0'); // Battery - Cyan/Info
            } else if (labels[i].toLowerCase().includes('wind')) {
                backgroundColors.push('#20c997'); // Wind - Teal
            } else if (labels[i].toLowerCase().includes('hydro')) {
                backgroundColors.push('#0d6efd'); // Hydro - Blue/Primary
            } else if (labels[i].toLowerCase().includes('hydrogen')) {
                backgroundColors.push('#6f42c1'); // Hydrogen - Purple
            } else if (labels[i].toLowerCase().includes('biogas')) {
                backgroundColors.push('#198754'); // Biogas - Green/Success
            } else if (labels[i].toLowerCase().includes('ethanol')) {
                backgroundColors.push('#fd7e14'); // Ethanol - Orange
            } else {
                backgroundColors.push('#6c757d'); // Default - Gray/Secondary
            }
        }
        
        new Chart(projectsByTypeChart, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: backgroundColors,
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }
    
    // Initialize projects by state chart
    const projectsByStateChart = document.getElementById('projects-by-state-chart');
    if (projectsByStateChart) {
        const labels = Array.from(projectsByStateChart.dataset.labels.split(','));
        const data = Array.from(projectsByStateChart.dataset.values.split(','), Number);
        
        new Chart(projectsByStateChart, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Projects',
                    data: data,
                    backgroundColor: '#6f42c1', // Purple color
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            precision: 0
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }
    
    // Initialize capacity chart
    const capacityChart = document.getElementById('capacity-chart');
    if (capacityChart) {
        // Get all capacity data from data attributes
        const rawLabels = [
            'Solar (GW)', 
            'Wind (GW)', 
            'Hydro (GW)', 
            'Storage (GWh)', 
            'H₂ (MW)', 
            'Biofuel (ML)'
        ];
        
        const rawData = [
            parseFloat(capacityChart.dataset.solarCapacity || 0),
            parseFloat(capacityChart.dataset.windCapacity || 0),
            parseFloat(capacityChart.dataset.hydroCapacity || 0),
            parseFloat(capacityChart.dataset.storageCapacity || 0),
            parseFloat(capacityChart.dataset.hydrogenCapacity || 0),
            parseFloat(capacityChart.dataset.biofuelCapacity || 0)
        ];
        
        // Filter out zero values for cleaner visualization
        // but always show at least the primary categories (Solar/Battery)
        const labels = [];
        const data = [];
        
        for (let i = 0; i < rawLabels.length; i++) {
            // Include if it has data or is one of the main categories
            if (rawData[i] > 0 || i < 2) {
                labels.push(rawLabels[i]);
                data.push(rawData[i]);
            }
        }
        
        // Colors for different energy types
        const backgroundColors = [
            '#ffc107', // Solar - Yellow/Warning
            '#20c997', // Wind - Teal 
            '#0d6efd', // Hydro - Blue/Primary
            '#0dcaf0', // Storage - Cyan/Info
            '#6f42c1', // Hydrogen - Purple
            '#198754', // Biogas - Green/Success
            '#fd7e14'  // Ethanol - Orange
        ];
        
        new Chart(capacityChart, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Total Capacity',
                    data: data,
                    backgroundColor: backgroundColors,
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }
}
