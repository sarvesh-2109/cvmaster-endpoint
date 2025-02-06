document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const loadingOverlay = document.getElementById('loadingOverlay');
    const uploadForm = document.getElementById('uploadForm');
    const fileInput = document.getElementById('resume_file');
    const deleteModal = document.getElementById('deleteModal');
    const instructionModal = document.getElementById('instructionModal');

    // Utility Functions
    const showLoading = () => loadingOverlay.style.display = 'flex';
    const hideLoading = () => loadingOverlay.style.display = 'none';

    // Dropdown Functions
    function toggleDropdown(button) {
        const dropdown = button.nextElementSibling;
        const allDropdowns = document.querySelectorAll('.dropdown-menu');

        allDropdowns.forEach(menu => {
            if (menu !== dropdown) menu.style.display = 'none';
        });

        dropdown.style.display = dropdown.style.display === 'block' ? 'none' : 'block';
    }

    // Delete Modal Functions
    let currentDeleteForm = null;

    function showDeleteModal(form) {
        currentDeleteForm = form;
        deleteModal.style.display = 'flex';
    }

    function closeDeleteModal() {
        deleteModal.style.display = 'none';
        currentDeleteForm = null;
    }

    function confirmDeleteResume() {
        if (currentDeleteForm) {
            currentDeleteForm.submit();
        }
        closeDeleteModal();
    }

    // Instruction Modal Functions
    function showInstructionModal() {
        instructionModal.style.display = 'flex';
        document.querySelectorAll('.bi-three-dots').forEach(icon => {
            icon.parentElement.classList.add('highlight-dots');
        });
    }

    function closeInstructionModal() {
        instructionModal.style.display = 'none';
        document.querySelectorAll('.bi-three-dots').forEach(icon => {
            icon.parentElement.classList.remove('highlight-dots');
        });
    }

    // Event Listeners
    fileInput.addEventListener('change', function(e) {
        if (this.files.length > 0) {
            showLoading();
            uploadForm.submit();
            sessionStorage.setItem('showInstructionModal', 'true');
        }
    });

// Navigation clicks
document.addEventListener('click', function(e) {

    const link = e.target.closest('a[href*="roast"], a[href*="feedback_resume"], a[href*="edit_resume"], a[href*="cover_letter"], a[href*="ats_analysis"], a[href*="home"], a[href*="feedback"]');

    if (link) {
        e.preventDefault();
        const href = link.getAttribute('href');

        const dropdown = link.closest('.dropdown-menu');
        if (dropdown) dropdown.style.display = 'none';

        showLoading();
        window.location.href = href;
    }
});

    // Delete form submissions
    document.querySelectorAll('form[action*="delete_resume"]').forEach(form => {
        form.onsubmit = function(e) {
            e.preventDefault();
            showDeleteModal(this);
        };
    });

    // Modal outside clicks
    deleteModal.addEventListener('click', function(e) {
        if (e.target === this) closeDeleteModal();
    });

    instructionModal.addEventListener('click', function(e) {
        if (e.target === this) closeInstructionModal();
    });

    // Escape key handler
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeDeleteModal();
            closeInstructionModal();
            document.querySelectorAll('.dropdown-menu').forEach(menu => {
                menu.style.display = 'none';
            });
        }
    });

    // Close dropdowns when clicking outside
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.relative')) {
            document.querySelectorAll('.dropdown-menu').forEach(menu => {
                menu.style.display = 'none';
            });
        }
    });

    // Check for instruction modal after page load
    if (sessionStorage.getItem('showInstructionModal') === 'true') {
        hideLoading();
        showInstructionModal();
        sessionStorage.removeItem('showInstructionModal');
    }

    // Make functions globally available
    window.toggleDropdown = toggleDropdown;
    window.showDeleteModal = showDeleteModal;
    window.closeDeleteModal = closeDeleteModal;
    window.confirmDeleteResume = confirmDeleteResume;
    window.showInstructionModal = showInstructionModal;
    window.closeInstructionModal = closeInstructionModal;
});