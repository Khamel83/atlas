
// Atlas Web Interface - Interactive Functions
class AtlasWeb {
    constructor() {
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupFormHandlers();
    }

    setupEventListeners() {
        // Form submissions
        document.querySelectorAll('form').forEach(form => {
            form.addEventListener('submit', this.handleFormSubmit.bind(this));
        });

        // Search input
        const searchInput = document.getElementById('search-input');
        if (searchInput) {
            searchInput.addEventListener('input', this.debounce(this.handleSearch.bind(this), 300));
        }

        // Content type filter
        const typeFilter = document.getElementById('type-filter');
        if (typeFilter) {
            typeFilter.addEventListener('change', this.handleTypeFilter.bind(this));
        }
    }

    setupFormHandlers() {
        // Content form
        const contentForm = document.getElementById('content-form');
        if (contentForm) {
            contentForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                await this.addContent();
            });
        }

        // Search form
        const searchForm = document.getElementById('search-form');
        if (searchForm) {
            searchForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                await this.performSearch();
            });
        }
    }

    async addContent() {
        const form = document.getElementById('content-form');
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn.textContent;

        try {
            // Show loading state
            submitBtn.textContent = 'Adding...';
            submitBtn.disabled = true;

            const formData = new FormData(form);
            const data = {
                content: formData.get('content'),
                title: formData.get('title'),
                source: formData.get('source')
            };

            const response = await fetch('/api/content', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (response.ok && result.success) {
                // IMMEDIATE: "Yep, we got it!" feedback
                this.showAlert(`✅ Yep, we got it! Processing: ${result.title}`, 'success');
                form.reset();

                // IMMEDIATE: Refresh content list to show new submission at TOP
                if (window.location.pathname === '/') {
                    await this.refreshContentList();
                }

                // IMMEDIATE: Start processing status checks
                this.showProcessingStatus(result.content_id, result.title);
            } else {
                this.showAlert(`❌ Error: ${result.error || result.detail || 'Unknown error'}`, 'error');
            }
        } catch (error) {
            this.showAlert('Network error: ' + error.message, 'error');
        } finally {
            submitBtn.textContent = originalText;
            submitBtn.disabled = false;
        }
    }

    async performSearch() {
        const query = document.getElementById('search-query').value;
        if (!query.trim()) return;

        const resultsContainer = document.getElementById('search-results');
        if (resultsContainer) {
            resultsContainer.innerHTML = `
                <div class="alert alert-info">
                    🔍 Searching for "${query}"...
                </div>
            `;
        }

        try {
            const response = await fetch(`/api/search?q=${encodeURIComponent(query)}&limit=50`, {
                method: 'GET'
            });

            const result = await response.json();

            if (response.ok && result.success) {
                this.displaySearchResults(result.results, query);
                this.showAlert(`✅ Found ${result.results.length} results for "${query}"`, 'success');
            } else {
                this.showAlert(`❌ Search error: ${result.error || 'Unknown error'}`, 'error');
                if (resultsContainer) {
                    resultsContainer.innerHTML = `
                        <div class="alert alert-danger">
                            Search failed: ${result.error || 'Unknown error'}
                        </div>
                    `;
                }
            }
        } catch (error) {
            this.showAlert('❌ Search error: ' + error.message, 'error');
            if (resultsContainer) {
                resultsContainer.innerHTML = `
                    <div class="alert alert-danger">
                        Network error: ${error.message}
                    </div>
                `;
            }
        }
    }

    displaySearchResults(results, query) {
        const resultsContainer = document.getElementById('search-results');
        if (!resultsContainer) return;

        if (results.length === 0) {
            resultsContainer.innerHTML = `
                <div class="alert alert-warning">
                    🔍 No results found for "${query}"
                    <br><small>Try different keywords or check if content has been processed</small>
                </div>
            `;
            return;
        }

        const resultsHtml = results.map(item => `
            <div class="content-item card">
                <div class="content-title">
                    ${item.url ? `<a href="${this.escapeHtml(item.url)}" target="_blank" rel="noopener">${this.escapeHtml(item.title)}</a>` : this.escapeHtml(item.title)}
                </div>
                <div class="content-meta">
                    <span class="badge bg-primary">${item.content_type || 'Unknown'}</span>
                    <span class="badge bg-secondary">ID: ${item.id}</span>
                    <span class="text-muted">${new Date(item.created_at).toLocaleDateString()}</span>
                </div>
                ${item.content ? `<div class="content-preview">${this.escapeHtml(item.content.substring(0, 200))}${item.content.length > 200 ? '...' : ''}</div>` : ''}
            </div>
        `).join('');

        resultsContainer.innerHTML = resultsHtml;
    }

    async refreshContentList() {
        try {
            const response = await fetch('/api/content?limit=10');
            const result = await response.json();

            if (response.ok) {
                this.updateContentList(result.results);
            }
        } catch (error) {
            console.error('Error refreshing content list:', error);
        }
    }

    updateContentList(contents) {
        const container = document.getElementById('recent-content');
        if (!container) return;

        // PRIORITY: Show processing status for immediate feedback
        const html = contents.map(item => {
            const stageStatus = this.getStageStatus(item.stage);
            return `
            <div class="content-item card" style="border-left: 4px solid ${stageStatus.color};">
                <div class="content-title">
                    ${item.url ? `<a href="${this.escapeHtml(item.url)}" target="_blank" rel="noopener">${this.escapeHtml(item.title)}</a>` : this.escapeHtml(item.title)}
                </div>
                <div class="content-meta">
                    <span class="badge bg-primary">${item.content_type || 'Unknown'}</span>
                    <span class="badge" style="background-color: ${stageStatus.color};">${stageStatus.text}</span>
                    <span class="text-muted">${new Date(item.created_at).toLocaleString()}</span>
                </div>
                ${item.ai_summary ? `<div class="content-preview">${this.escapeHtml(item.ai_summary.substring(0, 150))}${item.ai_summary.length > 150 ? '...' : ''}</div>` : ''}
            </div>
        `}).join('');

        container.innerHTML = html || '<p>No content yet. <a href="/add">Add some content</a> to get started.</p>';
    }

    getStageStatus(stage) {
        // PRIORITY: Clear status indicators for user feedback
        if (stage >= 300) {
            return { text: '✅ Ready', color: '#28a745' };
        } else if (stage >= 100) {
            return { text: '🔄 Processing', color: '#ffc107' };
        } else if (stage >= 5) {
            return { text: '⏳ Queued', color: '#17a2b8' };
        } else {
            return { text: '📝 New', color: '#6c757d' };
        }
    }

    handleSearch(event) {
        const query = event.target.value;
        if (query.length > 2) {
            this.performSearch();
        }
    }

    handleTypeFilter(event) {
        const type = event.target.value;
        // Implement type filtering
        console.log('Filter by type:', type);
    }

    showAlert(message, type = 'info') {
        // IMMEDIATE: Enhanced user feedback with better positioning and persistence
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type}`;
        alertDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            max-width: 400px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            animation: slideIn 0.3s ease-out;
        `;
        alertDiv.innerHTML = `
            <div style="display: flex; align-items: center; gap: 10px;">
                <span>${message}</span>
                <button onclick="this.parentElement.parentElement.remove()" style="
                    background: none;
                    border: none;
                    font-size: 18px;
                    cursor: pointer;
                    opacity: 0.7;
                    margin-left: auto;
                ">&times;</button>
            </div>
        `;

        // Add animation styles if not already added
        if (!document.querySelector('#alert-styles')) {
            const style = document.createElement('style');
            style.id = 'alert-styles';
            style.textContent = `
                @keyframes slideIn {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
            `;
            document.head.appendChild(style);
        }

        document.body.appendChild(alertDiv);

        // Auto-remove after 8 seconds for better visibility
        setTimeout(() => {
            if (alertDiv.parentElement) {
                alertDiv.remove();
            }
        }, 8000);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showProcessingStatus(contentId, title) {
        // IMMEDIATE: Show processing status with updates every 30 seconds, 5 minutes
        const maxChecks = 20; // 10 minutes of checking
        let checks = 0;

        const checkStatus = async () => {
            try {
                const response = await fetch(`/api/content/${contentId}/status`);
                const result = await response.json();

                if (response.ok && result.success) {
                    // Update status based on processing stage
                    if (result.stage >= 300) {
                        this.showAlert(`🎯 ${title} - Ready for search! (Stage ${result.stage})`, 'success');
                        return; // Stop checking when fully processed
                    } else if (result.stage >= 100) {
                        this.showAlert(`📝 ${title} - Processing content... (Stage ${result.stage})`, 'info');
                    } else {
                        this.showAlert(`⏳ ${title} - Queued for processing... (Stage ${result.stage})`, 'info');
                    }
                } else {
                    // Silently continue checking if status fails
                    console.log('Status check failed, continuing...');
                }
            } catch (error) {
                // Silently continue checking on network errors
                console.log('Network error checking status, continuing...');
            }

            checks++;
            if (checks < maxChecks) {
                setTimeout(checkStatus, 30000); // Check every 30 seconds
            } else {
                this.showAlert(`🔄 ${title} - Still processing in background. Check dashboard for updates.`, 'info');
            }
        };

        // IMMEDIATE: Start checking after 5 seconds
        setTimeout(checkStatus, 5000);
    }

    debounce(func, wait) {
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
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new AtlasWeb();
});
