// content_safari.js - Safari extension content script
(function() {
    'use strict';

    // Listen for messages from the Safari extension
    safari.self.addEventListener("message", handleMessage, false);

    function handleMessage(event) {
        switch (event.name) {
            case "showPopup":
                showAtlasPopup();
                break;
            case "savePage":
                saveCurrentPage();
                break;
            case "saveSelection":
                saveSelectedText();
                break;
            case "saveArticle":
                saveArticleContent();
                break;
        }
    }

    function showAtlasPopup() {
        // Create a floating popup for Atlas actions
        const existingPopup = document.getElementById('atlas-popup');
        if (existingPopup) {
            existingPopup.remove();
            return;
        }

        const popup = document.createElement('div');
        popup.id = 'atlas-popup';
        popup.innerHTML = `
            <div class="atlas-popup-content">
                <div class="atlas-popup-header">
                    <h3>Atlas Content Capture</h3>
                    <button class="atlas-popup-close">&times;</button>
                </div>
                <div class="atlas-popup-buttons">
                    <button id="atlas-save-page">Save Entire Page</button>
                    <button id="atlas-save-article">Save Article</button>
                    <button id="atlas-save-selection">Save Selection</button>
                </div>
                <div id="atlas-status" class="atlas-status"></div>
            </div>
        `;

        // Add CSS styles
        const style = document.createElement('style');
        style.textContent = `
            #atlas-popup {
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 10000;
                background: white;
                border: 1px solid #ccc;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                font-family: -apple-system, BlinkMacSystemFont, sans-serif;
                width: 280px;
            }
            .atlas-popup-content {
                padding: 16px;
            }
            .atlas-popup-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 12px;
            }
            .atlas-popup-header h3 {
                margin: 0;
                color: #2563eb;
                font-size: 16px;
            }
            .atlas-popup-close {
                background: none;
                border: none;
                font-size: 20px;
                cursor: pointer;
                color: #666;
            }
            .atlas-popup-buttons {
                display: flex;
                flex-direction: column;
                gap: 8px;
            }
            .atlas-popup-buttons button {
                background: #2563eb;
                color: white;
                border: none;
                padding: 10px 16px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 14px;
            }
            .atlas-popup-buttons button:hover {
                background: #1d4ed8;
            }
            .atlas-status {
                margin-top: 12px;
                padding: 8px;
                border-radius: 4px;
                font-size: 12px;
                display: none;
            }
            .atlas-status.success {
                background: #dcfce7;
                color: #166534;
                display: block;
            }
            .atlas-status.error {
                background: #fef2f2;
                color: #dc2626;
                display: block;
            }
        `;

        document.head.appendChild(style);
        document.body.appendChild(popup);

        // Event listeners
        popup.querySelector('.atlas-popup-close').addEventListener('click', () => {
            popup.remove();
        });

        popup.querySelector('#atlas-save-page').addEventListener('click', saveCurrentPage);
        popup.querySelector('#atlas-save-article').addEventListener('click', saveArticleContent);
        popup.querySelector('#atlas-save-selection').addEventListener('click', saveSelectedText);
    }

    function saveCurrentPage() {
        const data = {
            url: window.location.href,
            title: document.title,
            content: document.documentElement.outerHTML,
            source: 'safari-extension-page'
        };

        safari.self.tab.dispatchMessage("saveContent", data);
        showStatus('Page saved to Atlas!', 'success');
    }

    function saveSelectedText() {
        const selection = window.getSelection().toString().trim();
        if (!selection) {
            showStatus('No text selected', 'error');
            return;
        }

        const data = {
            url: window.location.href,
            title: document.title,
            content: selection,
            source: 'safari-extension-selection'
        };

        safari.self.tab.dispatchMessage("saveContent", data);
        showStatus('Selection saved to Atlas!', 'success');
    }

    function saveArticleContent() {
        // Try to extract article content using common selectors
        const articleSelectors = [
            'article',
            '[role="main"]',
            '.article-content',
            '.post-content',
            '.entry-content',
            '.content'
        ];

        let articleContent = '';

        for (const selector of articleSelectors) {
            const element = document.querySelector(selector);
            if (element && element.textContent.length > 100) {
                articleContent = element.textContent;
                break;
            }
        }

        if (!articleContent) {
            // Fallback to body content
            articleContent = document.body.textContent;
        }

        const data = {
            url: window.location.href,
            title: document.title,
            content: articleContent.trim(),
            source: 'safari-extension-article'
        };

        safari.self.tab.dispatchMessage("saveContent", data);
        showStatus('Article saved to Atlas!', 'success');
    }

    function showStatus(message, type) {
        const statusEl = document.querySelector('#atlas-status');
        if (statusEl) {
            statusEl.textContent = message;
            statusEl.className = `atlas-status ${type}`;

            if (type === 'success') {
                setTimeout(() => {
                    const popup = document.getElementById('atlas-popup');
                    if (popup) popup.remove();
                }, 2000);
            }
        }
    }

})();