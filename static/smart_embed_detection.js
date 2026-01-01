/**
 * Oracle Health (Cerner) PowerChart Embedding Detection
 * Based on Oracle Health SMART Developer Documentation
 */

(function () {
    'use strict';

    // Function to detect if running in PowerChart embedded environment
    function isEmbeddedInPowerChart() {
        try {
            // Check if we're in an iframe
            if (window.self !== window.top) {
                // Additional checks for PowerChart specific environment
                var userAgent = navigator.userAgent;
                var isIE = userAgent.indexOf('MSIE') !== -1 || userAgent.indexOf('Trident') !== -1;
                var isEdge = userAgent.indexOf('Edge') !== -1 || userAgent.indexOf('Edg/') !== -1;

                // Check for PowerChart specific indicators
                try {
                    // If we can't access parent window properties, likely embedded
                    var parentUrl = window.parent.location.href;
                } catch (e) {
                    // Cross-origin iframe, likely embedded in PowerChart
                    return true;
                }

                return true; // In iframe
            }
            return false;
        } catch (e) {
            // If there's an error, assume we're embedded for safety
            return true;
        }
    }

    // Function to configure app behavior based on embedding context
    function configureForEmbedding() {
        var isEmbedded = isEmbeddedInPowerChart();

        if (isEmbedded) {
            console.log('Detected PowerChart embedded environment');

            // Add embedded class to body for CSS targeting
            if (document.body) {
                document.body.classList.add('embedded-powerchart');
            }

            // Disable navigation that would open new windows
            document.addEventListener('click', function (e) {
                var target = e.target.closest('a');
                if (target && target.target === '_blank') {
                    // In embedded mode, open in same window instead
                    target.target = '_self';
                }
            });

            // Configure forms to submit in same window
            var forms = document.querySelectorAll('form');
            forms.forEach(function (form) {
                if (form.target === '_blank') {
                    form.target = '_self';
                }
            });

        } else {
            console.log('Detected standalone mode');
            if (document.body) {
                document.body.classList.add('standalone-mode');
            }
        }

        // Store embedding status globally
        window.SMART_EMBEDDED = isEmbedded;
    }

    // Function to add loading indicator
    function addLoadingIndicator() {
        var loadingHTML = `
            <div id="smart-loading-overlay" style="
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(255, 255, 255, 0.9);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 9999;
                font-family: Arial, sans-serif;
            ">
                <div style="text-align: center;">
                    <div style="
                        border: 4px solid #f3f3f3;
                        border-top: 4px solid #007bff;
                        border-radius: 50%;
                        width: 40px;
                        height: 40px;
                        animation: spin 1s linear infinite;
                        margin: 0 auto 20px;
                    "></div>
                    <div style="color: #333; font-size: 16px;">Loading...</div>
                </div>
            </div>
            <style>
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
            </style>
        `;

        document.body.insertAdjacentHTML('afterbegin', loadingHTML);
    }

    // Function to remove loading indicator
    function removeLoadingIndicator() {
        var overlay = document.getElementById('smart-loading-overlay');
        if (overlay) {
            overlay.remove();
        }
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            configureForEmbedding();
            addLoadingIndicator();

            // Remove loading indicator after page is fully loaded
            setTimeout(removeLoadingIndicator, 1000);
        });
    } else {
        configureForEmbedding();
    }

    // Export functions for global use
    window.SMARTEmbedding = {
        isEmbedded: isEmbeddedInPowerChart,
        showLoading: addLoadingIndicator,
        hideLoading: removeLoadingIndicator
    };

})(); 