// Bambili Connect JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Form validation enhancement
    const forms = document.querySelectorAll('.needs-validation');
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });

    // File upload preview
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(input => {
        input.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    // Create preview if it's an image
                    if (file.type.startsWith('image/')) {
                        let preview = document.getElementById(input.id + '-preview');
                        if (!preview) {
                            preview = document.createElement('img');
                            preview.id = input.id + '-preview';
                            preview.className = 'img-thumbnail mt-2';
                            preview.style.maxWidth = '200px';
                            input.parentNode.appendChild(preview);
                        }
                        preview.src = e.target.result;
                    }
                };
                reader.readAsDataURL(file);
            }
        });
    });

    // Vote functionality
    const voteButtons = document.querySelectorAll('.vote-btn');
    voteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const reportId = this.dataset.reportId;
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
            
            // Show loading state
            const originalText = this.innerHTML;
            this.innerHTML = '<span class="loading-spinner"></span> Voting...';
            this.disabled = true;
            
            fetch(`/vote/${reportId}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({})
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Update vote count
                    const voteCount = document.querySelector(`#vote-count-${reportId}`);
                    if (voteCount) {
                        voteCount.textContent = data.vote_count;
                    }
                    
                    // Update button state
                    if (data.voted) {
                        this.classList.remove('btn-outline-success');
                        this.classList.add('btn-success');
                        this.innerHTML = '<i class="fas fa-check"></i> Voted';
                    } else {
                        this.classList.remove('btn-success');
                        this.classList.add('btn-outline-success');
                        this.innerHTML = '<i class="fas fa-thumbs-up"></i> Vote';
                    }
                } else {
                    // Show error message
                    showAlert('error', data.message || 'An error occurred while voting.');
                    this.innerHTML = originalText;
                }
                this.disabled = false;
            })
            .catch(error => {
                console.error('Error:', error);
                showAlert('error', 'An error occurred while voting.');
                this.innerHTML = originalText;
                this.disabled = false;
            });
        });
    });

    // Search functionality
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        let searchTimeout;
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                performSearch(this.value);
            }, 300);
        });
    }

    // Geolocation for reports
    const locationBtn = document.getElementById('get-location-btn');
    if (locationBtn) {
        locationBtn.addEventListener('click', function() {
            if (navigator.geolocation) {
                this.innerHTML = '<span class="loading-spinner"></span> Getting location...';
                this.disabled = true;
                
                navigator.geolocation.getCurrentPosition(
                    function(position) {
                        const lat = position.coords.latitude;
                        const lng = position.coords.longitude;
                        
                        // Update hidden form fields
                        document.getElementById('id_latitude').value = lat;
                        document.getElementById('id_longitude').value = lng;
                        
                        // Show success message
                        showAlert('success', 'Location captured successfully!');
                        locationBtn.innerHTML = '<i class="fas fa-map-marker-alt"></i> Location Captured';
                        locationBtn.classList.remove('btn-outline-primary');
                        locationBtn.classList.add('btn-success');
                    },
                    function(error) {
                        showAlert('error', 'Unable to get your location. Please enter it manually.');
                        locationBtn.innerHTML = '<i class="fas fa-map-marker-alt"></i> Get Location';
                        locationBtn.disabled = false;
                    }
                );
            } else {
                showAlert('error', 'Geolocation is not supported by this browser.');
            }
        });
    }
});

// Utility functions
function showAlert(type, message) {
    const alertContainer = document.getElementById('alert-container') || document.body;
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    if (alertContainer === document.body) {
        alertContainer.insertBefore(alertDiv, alertContainer.firstChild);
    } else {
        alertContainer.appendChild(alertDiv);
    }
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}

function performSearch(query) {
    if (query.length < 2) return;
    
    const searchResults = document.getElementById('search-results');
    if (!searchResults) return;
    
    // Show loading state
    searchResults.innerHTML = '<div class="text-center"><span class="loading-spinner"></span> Searching...</div>';
    
    fetch(`/search/?q=${encodeURIComponent(query)}`)
        .then(response => response.text())
        .then(html => {
            searchResults.innerHTML = html;
        })
        .catch(error => {
            console.error('Search error:', error);
            searchResults.innerHTML = '<div class="text-center text-muted">Search failed. Please try again.</div>';
        });
}

// Map functionality
function initializeMap(containerId, reports = []) {
    const mapContainer = document.getElementById(containerId);
    if (!mapContainer) return;
    
    // Default center on Bambili
    const map = L.map(containerId).setView([5.9631, 10.2471], 13);
    
    // Add tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);
    
    // Add reports as markers
    reports.forEach(report => {
        if (report.latitude && report.longitude) {
            const marker = L.marker([report.latitude, report.longitude]).addTo(map);
            
            const popupContent = `
                <div class="map-popup">
                    <h6>${report.title}</h6>
                    <p class="small text-muted">${report.category} - ${report.urgency}</p>
                    <p class="small">${report.description.substring(0, 100)}...</p>
                    <a href="/report/${report.id}/" class="btn btn-sm btn-primary">View Details</a>
                </div>
            `;
            
            marker.bindPopup(popupContent);
        }
    });
    
    return map;
}

// Progressive Web App functionality
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        navigator.serviceWorker.register('/sw.js')
            .then(function(registration) {
                console.log('ServiceWorker registration successful');
            })
            .catch(function(error) {
                console.log('ServiceWorker registration failed');
            });
    });
}

// Performance monitoring
function measurePerformance() {
    if ('performance' in window) {
        window.addEventListener('load', function() {
            setTimeout(function() {
                const perfData = performance.getEntriesByType('navigation')[0];
                if (perfData) {
                    console.log('Page load time:', perfData.loadEventEnd - perfData.loadEventStart);
                }
            }, 0);
        });
    }
}

measurePerformance();

