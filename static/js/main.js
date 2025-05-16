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
    const originalText = button.innerHTML;
    const progressContainer = document.getElementById('update-progress-container');
    const progressBar = document.getElementById('update-progress-bar');
    const progressText = document.getElementById('update-progress-text');
    
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
        }
    })
    .then(response => response.json())
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
            alertsContainer.innerHTML = `
                <div class="alert alert-success alert-dismissible fade show" role="alert">
                    Export successful! <a href="${data.filename}" download class="alert-link">Download Excel File</a>
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                </div>
            `;
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
        
        new Chart(projectsByTypeChart, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: [
                        '#ffc107', // Solar - Warning color
                        '#0dcaf0'  // Battery - Info color
                    ],
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
        const labels = ['Solar (GW)', 'Battery (GWh)'];
        const data = [
            parseFloat(capacityChart.dataset.solarCapacity),
            parseFloat(capacityChart.dataset.batteryCapacity)
        ];
        
        new Chart(capacityChart, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Total Capacity',
                    data: data,
                    backgroundColor: [
                        '#ffc107', // Solar - Warning color
                        '#0dcaf0'  // Battery - Info color
                    ],
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
