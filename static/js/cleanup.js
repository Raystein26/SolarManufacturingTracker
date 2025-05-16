function cleanupData() {
    if (!confirm("This will remove irrelevant projects from the database. Are you sure you want to proceed?")) {
        return;
    }
    
    // Show loading state
    const button = document.getElementById('cleanup-data-button');
    if (!button) return; // Exit if button isn't found
    
    const originalText = button.innerHTML;
    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Cleaning...';
    
    // Call API to clean up data
    fetch('/cleanup-data', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to clean up data');
        }
        return response.text();
    })
    .then(text => {
        // Reload the page to show the cleaned data
        location.reload();
    })
    .catch(error => {
        console.error('Error:', error);
        // Show error message
        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-danger alert-dismissible fade show';
        alertDiv.innerHTML = `
            <strong>Error!</strong> ${error.message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        // Insert at the top of the container
        const container = document.querySelector('.container');
        container.insertBefore(alertDiv, container.firstChild);
        
        // Dismiss after 5 seconds
        setTimeout(() => {
            const alert = bootstrap.Alert.getOrCreateInstance(alertDiv);
            alert.close();
        }, 5000);
    })
    .finally(() => {
        // Reset button state
        button.disabled = false;
        button.innerHTML = originalText;
    });
}