// Report likes functionality

document.addEventListener('DOMContentLoaded', function() {
    // Cache DOM elements
    const likeButtons = document.querySelectorAll('.like-button');
    const likeCounts = document.querySelectorAll('.like-count');

    // Initialize local storage if not exists
    if (!localStorage.getItem('likedReports')) {
        localStorage.setItem('likedReports', JSON.stringify({}));
    }

    // Function to update UI
    function updateLikeUI(reportId, liked) {
        const button = document.querySelector(`.like-button[data-report-id="${reportId}"]`);
        const count = document.querySelector(`.like-count[data-report-id="${reportId}"]`);
        
        if (button && count) {
            // Toggle heart icon
            const heartIcon = button.querySelector('i');
            if (heartIcon) {
                heartIcon.classList.toggle('fas', liked);
                heartIcon.classList.toggle('far', !liked);
            }
            
            // Update button styling
            button.classList.toggle('btn-outline-primary', !liked);
            button.classList.toggle('btn-primary', liked);
            
            // Update count
            count.textContent = parseInt(count.textContent) + (liked ? 1 : -1);
        }
    }

    // Handle click events
    likeButtons.forEach(button => {
        button.addEventListener('click', async function(e) {
            e.preventDefault();
            const reportId = this.dataset.reportId;
            const likedReports = JSON.parse(localStorage.getItem('likedReports'));
            const isLiked = !likedReports[reportId];
            
            try {
                // Update local storage
                likedReports[reportId] = isLiked;
                localStorage.setItem('likedReports', JSON.stringify(likedReports));
                
                // Update UI immediately
                updateLikeUI(reportId, isLiked);
                
                // Send request to server
                const response = await fetch(`/api/reports/${reportId}/like/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                });

                if (!response.ok) {
                    // If server request fails, revert UI
                    likedReports[reportId] = !isLiked;
                    localStorage.setItem('likedReports', JSON.stringify(likedReports));
                    updateLikeUI(reportId, !isLiked);
                    throw new Error('Failed to update like status');
                }

                const data = await response.json();
                if (data.success) {
                    // Update count from server response
                    const count = document.querySelector(`.like-count[data-report-id="${reportId}"]`);
                    if (count) {
                        count.textContent = data.vote_count;
                    }
                }

            } catch (error) {
                console.error('Error:', error);
                // Revert UI if there's an error
                likedReports[reportId] = !isLiked;
                localStorage.setItem('likedReports', JSON.stringify(likedReports));
                updateLikeUI(reportId, !isLiked);
            }
        });
    });

    // Initialize buttons based on local storage
    Object.entries(JSON.parse(localStorage.getItem('likedReports'))).forEach(([reportId, liked]) => {
        if (liked) {
            updateLikeUI(reportId, true);
        }
    });
});

// Utility function to get CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
