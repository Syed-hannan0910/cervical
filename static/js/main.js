// ============================================
// Cervical Cancer Risk Assessment - JavaScript
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    
    // ============================================
    // LOGIN FORM HANDLING
    // ============================================
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            const btn = this.querySelector('button[type="submit"]');
            const spinner = btn.querySelector('.spinner-border');
            
            btn.disabled = true;
            if (spinner) spinner.style.display = 'inline-block';
        });
    }

    // ============================================
    // SIGNUP FORM HANDLING
    // ============================================
    const signupForm = document.getElementById('signupForm');
    if (signupForm) {
        const password = document.getElementById('password');
        const confirmPassword = document.getElementById('confirmPassword');
        const passwordMatch = document.getElementById('passwordMatch');

        // Password match validation
        function checkPasswordMatch() {
            if (confirmPassword.value === '') {
                passwordMatch.textContent = '';
                passwordMatch.className = 'text-gray-500 text-xs mt-1';
                return;
            }

            if (password.value === confirmPassword.value) {
                passwordMatch.textContent = '✓ Passwords match';
                passwordMatch.className = 'text-green-600 text-xs mt-1';
                confirmPassword.classList.remove('border-red-500');
                confirmPassword.classList.add('border-green-500');
            } else {
                passwordMatch.textContent = '✗ Passwords do not match';
                passwordMatch.className = 'text-red-600 text-xs mt-1';
                confirmPassword.classList.remove('border-green-500');
                confirmPassword.classList.add('border-red-500');
            }
        }

        if (password && confirmPassword) {
            password.addEventListener('input', checkPasswordMatch);
            confirmPassword.addEventListener('input', checkPasswordMatch);
        }

        // Form submission
        signupForm.addEventListener('submit', function(e) {
            if (password.value !== confirmPassword.value) {
                e.preventDefault();
                alert('Passwords do not match!');
                return false;
            }

            const btn = document.getElementById('signupBtn');
            const spinner = btn.querySelector('.spinner-border, i.bi-arrow-repeat');
            
            btn.disabled = true;
            if (spinner) spinner.style.display = 'inline-block';
        });
    }

    // ============================================
    // AUTO-DISMISS ALERTS
    // ============================================
    const alerts = document.querySelectorAll('.alert, [class*="bg-green-50"], [class*="bg-red-50"]');
    alerts.forEach(alert => {
        // Only auto-dismiss flash messages, not static alerts
        if (alert.querySelector('.bi-check-circle-fill, .bi-exclamation-circle-fill')) {
            setTimeout(() => {
                alert.style.transition = 'opacity 0.5s';
                alert.style.opacity = '0';
                setTimeout(() => alert.remove(), 500);
            }, 5000); // Auto-dismiss after 5 seconds
        }
    });

    // ============================================
    // FORM VALIDATION
    // ============================================
    const forms = document.querySelectorAll('.needs-validation');
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });

    // ============================================
    // NUMBER INPUT VALIDATION
    // ============================================
    const numberInputs = document.querySelectorAll('input[type="number"]');
    numberInputs.forEach(input => {
        input.addEventListener('input', function() {
            const min = parseInt(this.getAttribute('min'));
            const max = parseInt(this.getAttribute('max'));
            let value = parseInt(this.value);

            if (isNaN(value)) {
                this.value = min;
                return;
            }

            if (value < min) this.value = min;
            if (value > max) this.value = max;
        });
    });

    // ============================================
    // SMOOTH SCROLLING
    // ============================================
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const href = this.getAttribute('href');
            if (href !== '#') {
                e.preventDefault();
                const target = document.querySelector(href);
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            }
        });
    });

    // ============================================
    // IMAGE PREVIEW
    // ============================================
    const imageInput = document.getElementById('imageInput');
    if (imageInput) {
        imageInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                // Validate file type
                const validTypes = ['image/jpeg', 'image/png', 'image/bmp', 'image/jpg'];
                if (!validTypes.includes(file.type)) {
                    alert('Please upload a valid image file (JPG, PNG, or BMP)');
                    this.value = '';
                    return;
                }

                // Validate file size (16MB max)
                const maxSize = 16 * 1024 * 1024; // 16MB
                if (file.size > maxSize) {
                    alert('File size must be less than 16MB');
                    this.value = '';
                    return;
                }

                // Show file name
                const fileName = file.name;
                const fileSize = (file.size / 1024 / 1024).toFixed(2);
                console.log(`Selected file: ${fileName} (${fileSize}MB)`);
            }
        });
    }

    // ============================================
    // LOADING STATES
    // ============================================
    function showLoading(button) {
        const spinner = button.querySelector('.spinner-border, i.bi-arrow-repeat');
        button.disabled = true;
        if (spinner) {
            spinner.style.display = 'inline-block';
            if (spinner.classList.contains('bi-arrow-repeat')) {
                spinner.classList.add('animate-spin');
            }
        }
    }

    function hideLoading(button) {
        const spinner = button.querySelector('.spinner-border, i.bi-arrow-repeat');
        button.disabled = false;
        if (spinner) {
            spinner.style.display = 'none';
            if (spinner.classList.contains('bi-arrow-repeat')) {
                spinner.classList.remove('animate-spin');
            }
        }
    }

    // ============================================
    // PRINT REPORT
    // ============================================
    const printButtons = document.querySelectorAll('.print-report');
    printButtons.forEach(button => {
        button.addEventListener('click', function() {
            window.print();
        });
    });

    // ============================================
    // COPY TO CLIPBOARD
    // ============================================
    function copyToClipboard(text) {
        navigator.clipboard.writeText(text).then(() => {
            showNotification('Copied to clipboard!', 'success');
        }).catch(err => {
            console.error('Failed to copy:', err);
        });
    }

    // ============================================
    // KEYBOARD SHORTCUTS
    // ============================================
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + P for print
        if ((e.ctrlKey || e.metaKey) && e.key === 'p') {
            const resultsPage = document.querySelector('h3, h1');
            if (resultsPage && resultsPage.textContent.includes('Risk Detected')) {
                e.preventDefault();
                window.print();
            }
        }
    });

    // ============================================
    // ANIMATION ON SCROLL
    // ============================================
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '0';
                entry.target.style.transform = 'translateY(20px)';
                entry.target.style.transition = 'opacity 0.5s, transform 0.5s';
                setTimeout(() => {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }, 100);
            }
        });
    }, observerOptions);

    // Observe cards for animation
    document.querySelectorAll('[class*="rounded-3xl"], [class*="rounded-2xl"]').forEach(card => {
        observer.observe(card);
    });

    // ============================================
    // FORM DATA PERSISTENCE (Local Storage)
    // ============================================
    const assessmentForm = document.getElementById('assessmentForm');
    if (assessmentForm) {
        // Load saved data
        const savedData = localStorage.getItem('assessmentFormData');
        if (savedData) {
            try {
                const data = JSON.parse(savedData);
                Object.keys(data).forEach(key => {
                    const input = document.querySelector(`[name="${key}"]`);
                    if (input) {
                        if (input.type === 'radio') {
                            const radio = document.querySelector(`[name="${key}"][value="${data[key]}"]`);
                            if (radio) radio.checked = true;
                        } else {
                            input.value = data[key];
                        }
                    }
                });
            } catch (e) {
                console.error('Error loading saved data:', e);
            }
        }

        // Save data on input change
        const formInputs = assessmentForm.querySelectorAll('input, select');
        formInputs.forEach(input => {
            input.addEventListener('change', function() {
                const formData = new FormData(assessmentForm);
                const data = Object.fromEntries(formData.entries());
                localStorage.setItem('assessmentFormData', JSON.stringify(data));
            });
        });

        // Clear saved data after submission
        assessmentForm.addEventListener('submit', function() {
            localStorage.removeItem('assessmentFormData');
        });
    }

    // ============================================
    // CLEAR FORM BUTTON
    // ============================================
    const clearFormBtn = document.getElementById('clearFormBtn');
    if (clearFormBtn) {
        clearFormBtn.addEventListener('click', function() {
            if (confirm('Are you sure you want to clear all form data?')) {
                assessmentForm.reset();
                localStorage.removeItem('assessmentFormData');
                location.reload();
            }
        });
    }

    // ============================================
    // RESPONSIVE NAVBAR
    // ============================================
    const navbarToggler = document.querySelector('.navbar-toggler');
    if (navbarToggler) {
        navbarToggler.addEventListener('click', function() {
            this.classList.toggle('active');
        });
    }

    // ============================================
    // CONFIRM BEFORE LEAVING PAGE
    // ============================================
    let formModified = false;
    if (assessmentForm) {
        assessmentForm.addEventListener('input', function() {
            formModified = true;
        });

        window.addEventListener('beforeunload', function(e) {
            if (formModified) {
                e.preventDefault();
                e.returnValue = '';
                return '';
            }
        });

        assessmentForm.addEventListener('submit', function() {
            formModified = false;
        });
    }

    // ============================================
    // PROGRESS INDICATOR
    // ============================================
    function updateProgress() {
        const totalFields = document.querySelectorAll('#assessmentForm input[required], #assessmentForm select[required]').length;
        let filledFields = 0;

        document.querySelectorAll('#assessmentForm input[required], #assessmentForm select[required]').forEach(field => {
            if (field.type === 'radio') {
                const radioGroup = document.querySelectorAll(`input[name="${field.name}"]`);
                if (Array.from(radioGroup).some(radio => radio.checked)) {
                    filledFields++;
                }
            } else if (field.value !== '') {
                filledFields++;
            }
        });

        const progress = (filledFields / totalFields) * 100;
        const progressBar = document.getElementById('formProgress');
        if (progressBar) {
            progressBar.style.width = progress + '%';
            progressBar.setAttribute('aria-valuenow', progress);
        }
    }

    if (assessmentForm) {
        assessmentForm.addEventListener('input', updateProgress);
        assessmentForm.addEventListener('change', updateProgress);
        updateProgress(); // Initial update
    }

    // ============================================
    // ACCESSIBILITY ENHANCEMENTS
    // ============================================
    // Add aria-labels to increment/decrement buttons
    document.querySelectorAll('button[onclick*="increment"], button[onclick*="decrement"]').forEach(button => {
        if (button.textContent.includes('+') || button.querySelector('.bi-plus-lg')) {
            button.setAttribute('aria-label', 'Increment value');
        } else if (button.textContent.includes('−') || button.querySelector('.bi-dash-lg')) {
            button.setAttribute('aria-label', 'Decrement value');
        }
    });

    // ============================================
    // ERROR HANDLING
    // ============================================
    window.addEventListener('error', function(e) {
        console.error('Global error:', e.error);
    });

    // ============================================
    // UTILITY FUNCTIONS
    // ============================================
    function formatDate(date) {
        return new Date(date).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // ============================================
    // ANALYTICS (Optional - for tracking)
    // ============================================
    function trackEvent(eventName, eventData) {
        console.log('Event:', eventName, eventData);
        // Add your analytics tracking code here
        // Example: gtag('event', eventName, eventData);
    }

    // Track form submissions
    if (assessmentForm) {
        assessmentForm.addEventListener('submit', function() {
            trackEvent('assessment_submitted', {
                timestamp: new Date().toISOString()
            });
        });
    }

    // ============================================
    // INITIALIZATION COMPLETE
    // ============================================
    console.log('Cervical Cancer Risk Assessment System Initialized ✓');
});

// ============================================
// GLOBAL HELPER FUNCTIONS
// ============================================

// Number spinner functions (accessible globally)
window.incrementValue = function(id, min, max) {
    const input = document.getElementById(id);
    if (!input) return;
    
    let value = parseInt(input.value) || min;
    if (value < max) {
        input.value = value + 1;
        input.dispatchEvent(new Event('input', { bubbles: true }));
    }
};

window.decrementValue = function(id, min, max) {
    const input = document.getElementById(id);
    if (!input) return;
    
    let value = parseInt(input.value) || min;
    if (value > min) {
        input.value = value - 1;
        input.dispatchEvent(new Event('input', { bubbles: true }));
    }
};

// Format number with commas
window.formatNumber = function(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
};

// Validate email
window.isValidEmail = function(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
};

// Show notification (Tailwind-compatible)
window.showNotification = function(message, type = 'info') {
    const typeColors = {
        'info': 'bg-blue-500',
        'success': 'bg-green-500',
        'warning': 'bg-yellow-500',
        'danger': 'bg-red-500',
        'error': 'bg-red-500'
    };
    
    const alertDiv = document.createElement('div');
    alertDiv.className = `${typeColors[type]} text-white px-6 py-4 rounded-xl shadow-lg fixed top-4 left-1/2 transform -translate-x-1/2 z-50 flex items-center gap-3`;
    alertDiv.style.minWidth = '300px';
    alertDiv.innerHTML = `
        <span>${message}</span>
        <button type="button" onclick="this.parentElement.remove()" class="ml-auto text-white hover:text-gray-200">
            <i class="bi bi-x-lg"></i>
        </button>
    `;
    
    document.body.appendChild(alertDiv);
    
    setTimeout(() => {
        alertDiv.style.transition = 'opacity 0.3s';
        alertDiv.style.opacity = '0';
        setTimeout(() => alertDiv.remove(), 300);
    }, 5000);
};

// ============================================
// SERVICE WORKER (Optional - for offline support)
// ============================================
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        // navigator.serviceWorker.register('/sw.js')
        //     .then(reg => console.log('Service Worker registered'))
        //     .catch(err => console.log('Service Worker registration failed:', err));
    });
}