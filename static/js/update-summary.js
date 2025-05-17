// Show update summary dialog
function showUpdateSummary(projectsAdded, sourcesWithProjects) {
    // Create a modal element
    const modalDiv = document.createElement('div');
    modalDiv.classList.add('modal', 'fade');
    modalDiv.id = 'updateSummaryModal';
    modalDiv.tabIndex = '-1';
    modalDiv.setAttribute('aria-labelledby', 'updateSummaryModalLabel');
    modalDiv.setAttribute('aria-hidden', 'true');
    
    // Generate source list HTML if any sources added projects
    let sourcesList = '';
    if (sourcesWithProjects && sourcesWithProjects.length > 0) {
        sourcesList = '<ul class="list-group mt-3">';
        sourcesWithProjects.forEach(source => {
            sourcesList += `<li class="list-group-item d-flex justify-content-between align-items-center">
                ${source.name}
                <span class="badge bg-primary rounded-pill">${source.projects} project${source.projects > 1 ? 's' : ''}</span>
            </li>`;
        });
        sourcesList += '</ul>';
    }
    
    // Populate the modal
    modalDiv.innerHTML = `
        <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content">
                <div class="modal-header bg-success text-white">
                    <h5 class="modal-title" id="updateSummaryModalLabel">
                        <i class="fas fa-check-circle me-2"></i>Update Complete
                    </h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <h4 class="text-center mb-3">
                        <strong>${projectsAdded}</strong> new project${projectsAdded !== 1 ? 's' : ''} added
                    </h4>
                    ${sourcesWithProjects && sourcesWithProjects.length > 0 ? 
                        `<p class="text-center">Projects found in the following sources:</p>
                        ${sourcesList}` : 
                        ''}
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-primary" data-bs-dismiss="modal">View Projects</button>
                </div>
            </div>
        </div>
    `;
    
    // Add the modal to the document
    document.body.appendChild(modalDiv);
    
    // Show the modal
    const modal = new bootstrap.Modal(modalDiv);
    modal.show();
    
    // Add event listener to navigate to projects page when clicking "View Projects"
    modalDiv.querySelector('.btn-primary').addEventListener('click', function() {
        window.location.href = '/projects';
    });
}

// Function to handle any update button click
function handleUpdateButtonClick(event) {
    // Find the nearest update button (could be the clicked element or its parent)
    const button = event.target.closest('button');
    if (!button) return;

    // Store original content
    const originalText = button.innerHTML;
    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Running...';
    
    // Get or create progress elements
    let progressContainer = document.getElementById('update-progress-container');
    let progressBar = document.getElementById('update-progress-bar');
    let progressText = document.getElementById('update-progress-text');
    
    // Create progress elements if they don't exist
    if (!progressContainer) {
        progressContainer = document.createElement('div');
        progressContainer.id = 'update-progress-container';
        progressContainer.className = 'mt-3 p-3 border rounded bg-dark';
        progressContainer.style.display = 'none';
        
        progressContainer.innerHTML = `
            <h6 class="mb-2">Update Progress</h6>
            <div class="progress" style="height: 20px;">
                <div id="update-progress-bar" class="progress-bar progress-bar-striped progress-bar-animated" 
                    role="progressbar" style="width: 0%;" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100"></div>
            </div>
            <div class="mt-2">
                <small id="update-progress-text" class="text-muted">Starting update...</small>
            </div>
        `;
        
        // Find a suitable container to append progress to
        const container = document.querySelector('.container');
        if (container) {
            container.insertBefore(progressContainer, container.firstChild);
        } else {
            document.body.appendChild(progressContainer);
        }
        
        progressBar = document.getElementById('update-progress-bar');
        progressText = document.getElementById('update-progress-text');
    }
    
    // Show progress container
    progressContainer.style.display = 'block';
    
    // Call API to run check
    fetch('/api/run-check', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // Show the alerts container
            const alertsContainer = document.getElementById('alerts-container');
            if (alertsContainer) {
                alertsContainer.innerHTML = `
                    <div class="alert alert-success alert-dismissible fade show" role="alert">
                        Check started in background. This may take several minutes.
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    </div>
                `;
            }
            
            // Start progress checking
            let sourceCount = 0;
            let processedCount = 0;
            let projectsAdded = 0;
            let sourcesWithProjects = [];
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
                                    
                                    // Use the total sources count from the backend
                                    const totalSourcesCount = progress.total_sources || sourceCount;
                                    const displayProcessedSources = progress.processed_sources;
                                    
                                    progressText.textContent = `Completed: ${displayProcessedSources}/${totalSourcesCount} sources, ${progress.projects_added} projects added`;
                                    
                                    // Store the final numbers
                                    projectsAdded = progress.projects_added;
                                    processedCount = displayProcessedSources;
                                    
                                    // Show summary dialog after completion
                                    setTimeout(() => {
                                        // Hide progress
                                        progressContainer.style.display = 'none';
                                        
                                        // Create a summary modal
                                        if (projectsAdded > 0) {
                                            showUpdateSummary(projectsAdded, sourcesWithProjects);
                                        } else {
                                            // Just show a notification if no projects were added
                                            if (alertsContainer) {
                                                alertsContainer.innerHTML = `
                                                    <div class="alert alert-info alert-dismissible fade show" role="alert">
                                                        Update complete: No new projects found in ${processedCount} sources.
                                                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                                                    </div>
                                                `;
                                            }
                                        }
                                        
                                        // Refresh the page after a short delay to show new projects
                                        if (projectsAdded > 0) {
                                            setTimeout(() => {
                                                location.reload();
                                            }, 3000);
                                        }
                                    }, 1000);
                                } else {
                                    // Use the total sources count from the backend
                                    const totalSourcesCount = progress.total_sources || sourceCount;
                                    processedCount = progress.processed_sources;
                                    
                                    // Calculate progress percent and ensure it's capped at 100%
                                    const percent = Math.min(100, Math.round((processedCount / totalSourcesCount) * 100));
                                    progressBar.style.width = `${percent}%`;
                                    
                                    // Check if new projects were added
                                    if (progress.projects_added > projectsAdded) {
                                        // New projects were added since last check
                                        const newProjects = progress.projects_added - projectsAdded;
                                        projectsAdded = progress.projects_added;
                                        
                                        // Add the source to the list of sources with projects
                                        if (sources[processedCount-1]) {
                                            sourcesWithProjects.push({
                                                name: sources[processedCount-1].name,
                                                projects: newProjects
                                            });
                                        }
                                    }
                                    
                                    progressText.textContent = `Processing sources: ${processedCount}/${totalSourcesCount}, ${progress.projects_added} projects added`;
                                }
                            })
                            .catch(error => {
                                console.error('Error checking progress:', error);
                            });
                    }, 2000); // Check every 2 seconds
                });
        } else {
            progressContainer.style.display = 'none';
            
            const alertsContainer = document.getElementById('alerts-container');
            if (alertsContainer) {
                alertsContainer.innerHTML = `
                    <div class="alert alert-danger alert-dismissible fade show" role="alert">
                        Error: ${data.message}
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    </div>
                `;
            }
        }
    })
    .catch(error => {
        console.error('Error:', error);
        
        // Show error message
        const alertsContainer = document.getElementById('alerts-container');
        if (alertsContainer) {
            alertsContainer.innerHTML = `
                <div class="alert alert-danger alert-dismissible fade show" role="alert">
                    Error: ${error.message}
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                </div>
            `;
        }
        
        // Hide progress
        if (progressContainer) {
            progressContainer.style.display = 'none';
        }
    })
    .finally(() => {
        // Reset button state
        button.disabled = false;
        button.innerHTML = originalText;
    });
}

// Initialize update buttons on page load
document.addEventListener('DOMContentLoaded', function() {
    // Find all update buttons
    const updateButtons = document.querySelectorAll('[id$="manual-check-button"], [id$="update-button"]');
    
    // Add click handler to each
    updateButtons.forEach(button => {
        button.addEventListener('click', handleUpdateButtonClick);
    });
});