// Study Planner - Main JavaScript File

// Auto-hide messages after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            setTimeout(() => {
                alert.remove();
            }, 300);
        }, 5000);
    });
});

// Confirm delete actions
document.addEventListener('DOMContentLoaded', function() {
    const deleteForms = document.querySelectorAll('form[action*="delete"]');
    deleteForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!confirm('Are you sure you want to delete this? This action cannot be undone.')) {
                e.preventDefault();
            }
        });
    });
});

// Progress bar animation
document.addEventListener('DOMContentLoaded', function() {
    const progressBars = document.querySelectorAll('.progress-bar');
    progressBars.forEach(bar => {
        const width = bar.style.width;
        bar.style.width = '0';
        setTimeout(() => {
            bar.style.width = width;
        }, 100);
    });
});

// Topic reorder functionality (drag and drop)
function initTopicReorder() {
    const topicList = document.querySelector('.topic-list');
    if (!topicList) return;
    
    let draggedElement = null;
    
    const topics = topicList.querySelectorAll('.topic-item');
    topics.forEach((topic, index) => {
        topic.setAttribute('draggable', true);
        topic.dataset.order = index;
        
        topic.addEventListener('dragstart', function(e) {
            draggedElement = this;
            this.style.opacity = '0.5';
        });
        
        topic.addEventListener('dragend', function(e) {
            this.style.opacity = '1';
            saveTopicOrder();
        });
        
        topic.addEventListener('dragover', function(e) {
            e.preventDefault();
        });
        
        topic.addEventListener('drop', function(e) {
            e.preventDefault();
            if (draggedElement !== this) {
                const allTopics = [...topicList.querySelectorAll('.topic-item')];
                const draggedIndex = allTopics.indexOf(draggedElement);
                const droppedIndex = allTopics.indexOf(this);
                
                if (draggedIndex < droppedIndex) {
                    this.parentNode.insertBefore(draggedElement, this.nextSibling);
                } else {
                    this.parentNode.insertBefore(draggedElement, this);
                }
            }
        });
    });
}

function saveTopicOrder() {
    const topics = document.querySelectorAll('.topic-item');
    const order = [];
    
    topics.forEach((topic, index) => {
        const topicId = topic.dataset.topicId;
        if (topicId) {
            order.push({
                id: topicId,
                order: index
            });
        }
    });
    
    // Send AJAX request to save order
    fetch('/ajax/topics/reorder/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({ topics: order })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log('Topic order saved successfully');
        }
    })
    .catch(error => {
        console.error('Error saving topic order:', error);
    });
}

// Get CSRF token from cookies
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

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initTopicReorder();
});

// Form validation enhancement
document.addEventListener('DOMContentLoaded', function() {
    const forms = document.querySelectorAll('form[novalidate]');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const requiredFields = form.querySelectorAll('[required]');
            let isValid = true;
            
            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    isValid = false;
                    field.style.borderColor = 'var(--danger)';
                } else {
                    field.style.borderColor = '';
                }
            });
            
            if (!isValid) {
                e.preventDefault();
                alert('Please fill in all required fields');
            }
        });
    });
});

// Smooth scroll to top
function scrollToTop() {
    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
}

// Add scroll to top button
document.addEventListener('DOMContentLoaded', function() {
    const scrollBtn = document.createElement('button');
    scrollBtn.innerHTML = '↑';
    scrollBtn.className = 'scroll-to-top';
    scrollBtn.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        width: 50px;
        height: 50px;
        border-radius: 50%;
        background: var(--primary-600);
        color: white;
        border: none;
        font-size: 1.5rem;
        cursor: pointer;
        display: none;
        z-index: 1000;
        box-shadow: var(--shadow-lg);
        transition: all var(--transition-base);
    `;
    
    scrollBtn.addEventListener('click', scrollToTop);
    document.body.appendChild(scrollBtn);
    
    window.addEventListener('scroll', function() {
        if (window.pageYOffset > 300) {
            scrollBtn.style.display = 'block';
        } else {
            scrollBtn.style.display = 'none';
        }
    });
});