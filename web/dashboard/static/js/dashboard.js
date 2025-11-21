/**
 * OOS Management Dashboard - Main JavaScript
 * Handles real-time updates, UI interactions, and API communication
 */

class OOSDashboard {
    constructor() {
        this.socket = null;
        this.currentSection = 'dashboard';
        this.systemStatus = {};
        this.connectionRetryCount = 0;
        this.maxRetries = 5;

        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupSocketIO();
        this.initializeUI();
        this.loadInitialData();
    }

    setupEventListeners() {
        // Navigation
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const section = link.dataset.section;
                this.navigateToSection(section);
            });
        });

        // Refresh button
        document.getElementById('refresh-btn').addEventListener('click', () => {
            this.refreshCurrentSection();
        });

        // Quick actions
        document.getElementById('run-diagnostics').addEventListener('click', () => {
            this.runDiagnostics();
        });

        document.getElementById('health-check').addEventListener('click', () => {
            this.runHealthCheck();
        });

        // Log controls
        document.getElementById('log-type').addEventListener('change', () => {
            this.loadLogs();
        });

        document.getElementById('log-search').addEventListener('input', () => {
            this.filterLogs();
        });

        document.getElementById('refresh-logs').addEventListener('click', () => {
            this.loadLogs();
        });

        // Environment editor
        document.getElementById('save-env').addEventListener('click', () => {
            this.saveEnvironment();
        });

        document.getElementById('backup-env').addEventListener('click', () => {
            this.backupEnvironment();
        });

        // Projects
        document.getElementById('create-project').addEventListener('click', () => {
            this.showCreateProjectModal();
        });

        // Diagnostics
        document.getElementById('run-selected-tests').addEventListener('click', () => {
            this.runDiagnostics('selected');
        });

        document.getElementById('run-all-tests').addEventListener('click', () => {
            this.runDiagnostics('full');
        });

        // Modal controls
        document.getElementById('modal-close').addEventListener('click', () => {
            this.hideModal();
        });

        document.getElementById('modal-cancel').addEventListener('click', () => {
            this.hideModal();
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.hideModal();
            }
        });
    }

    setupSocketIO() {
        try {
            this.socket = io();

            this.socket.on('connect', () => {
                console.log('Connected to OOS Dashboard');
                this.updateConnectionStatus('connected');
                this.connectionRetryCount = 0;
            });

            this.socket.on('disconnect', () => {
                console.log('Disconnected from OOS Dashboard');
                this.updateConnectionStatus('disconnected');
            });

            this.socket.on('status_update', (data) => {
                this.updateSystemStatus(data);
            });

            this.socket.on('connect_error', () => {
                this.updateConnectionStatus('error');
                if (this.connectionRetryCount < this.maxRetries) {
                    this.connectionRetryCount++;
                    setTimeout(() => this.socket.connect(), 5000 * this.connectionRetryCount);
                }
            });

        } catch (error) {
            console.error('Failed to initialize Socket.IO:', error);
            this.updateConnectionStatus('error');
        }
    }

    updateConnectionStatus(status) {
        const statusEl = document.getElementById('connection-status');
        const dot = statusEl.querySelector('.status-dot');
        const text = statusEl.querySelector('.status-text');

        dot.className = 'status-dot';

        switch (status) {
            case 'connected':
                dot.classList.add('status-connected');
                text.textContent = 'Connected';
                break;
            case 'disconnected':
                dot.classList.add('status-disconnected');
                text.textContent = 'Disconnected';
                break;
            case 'error':
                dot.classList.add('status-error');
                text.textContent = 'Connection Error';
                break;
            default:
                dot.classList.add('status-connecting');
                text.textContent = 'Connecting...';
        }
    }

    navigateToSection(sectionName) {
        // Update navigation
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
        });
        document.querySelector(`[data-section="${sectionName}"]`).classList.add('active');

        // Update content
        document.querySelectorAll('.content-section').forEach(section => {
            section.classList.remove('active');
        });
        document.getElementById(`section-${sectionName}`).classList.add('active');

        this.currentSection = sectionName;
        this.loadSectionData(sectionName);
    }

    initializeUI() {
        // Initialize tooltips, dropdowns, etc.
        this.showLoading(false);
    }

    async loadInitialData() {
        try {
            await Promise.all([
                this.loadSystemStatus(),
                this.loadProjects(),
                this.loadEnvironment(),
                this.loadLogs()
            ]);
        } catch (error) {
            console.error('Failed to load initial data:', error);
            this.showNotification('Failed to load initial data', 'error');
        }
    }

    async loadSectionData(section) {
        switch (section) {
            case 'dashboard':
                await this.loadSystemStatus();
                break;
            case 'status':
                await this.loadDetailedStatus();
                break;
            case 'logs':
                await this.loadLogs();
                break;
            case 'projects':
                await this.loadProjects();
                break;
            case 'environment':
                await this.loadEnvironment();
                break;
        }
    }

    async loadSystemStatus() {
        try {
            const response = await fetch('/api/status');
            const data = await response.json();

            this.systemStatus = data;
            this.updateSystemStatusUI(data);

        } catch (error) {
            console.error('Failed to load system status:', error);
            this.showNotification('Failed to load system status', 'error');
        }
    }

    updateSystemStatusUI(status) {
        // Update health score
        const healthScore = document.getElementById('health-score');
        healthScore.textContent = status.health_score + '%';
        healthScore.className = 'health-score';

        if (status.health_score >= 80) {
            healthScore.classList.add('health-good');
        } else if (status.health_score >= 60) {
            healthScore.classList.add('health-warning');
        } else {
            healthScore.classList.add('health-critical');
        }

        // Update health details
        const healthDetails = document.getElementById('health-details');
        healthDetails.innerHTML = `
            <div class="health-item">
                <span class="health-label">Last Check:</span>
                <span class="health-value">${new Date(status.timestamp).toLocaleString()}</span>
            </div>
        `;

        // Update services
        this.updateServicesList(status.services);

        // Update system info
        this.updateSystemInfo(status.system);
    }

    updateServicesList(services) {
        const servicesList = document.getElementById('services-list');

        if (!services || Object.keys(services).length === 0) {
            servicesList.innerHTML = '<div class="no-data">No service data available</div>';
            return;
        }

        servicesList.innerHTML = Object.entries(services).map(([key, service]) => `
            <div class="service-item">
                <div class="service-status ${service.status}">
                    <span class="service-dot"></span>
                    <span class="service-name">${service.name}</span>
                </div>
                <div class="service-details">${service.details}</div>
            </div>
        `).join('');
    }

    updateSystemInfo(system) {
        const systemInfo = document.getElementById('system-info');

        if (!system) {
            systemInfo.innerHTML = '<div class="no-data">No system data available</div>';
            return;
        }

        systemInfo.innerHTML = `
            <div class="system-item">
                <span class="system-label">Disk Usage:</span>
                <span class="system-value">${system.disk_usage || 'N/A'}</span>
            </div>
            <div class="system-item">
                <span class="system-label">Memory:</span>
                <span class="system-value">${system.memory || 'N/A'}</span>
            </div>
            <div class="system-item">
                <span class="system-label">Load Average:</span>
                <span class="system-value">${system.load_average || 'N/A'}</span>
            </div>
        `;
    }

    async loadProjects() {
        try {
            const response = await fetch('/api/projects');
            const data = await response.json();

            if (data.success) {
                this.updateProjectsList(data.projects);
            } else {
                throw new Error(data.error || 'Failed to load projects');
            }

        } catch (error) {
            console.error('Failed to load projects:', error);
            this.showNotification('Failed to load projects', 'error');
        }
    }

    updateProjectsList(projects) {
        const projectsList = document.getElementById('projects-list');

        if (!projects || projects.length === 0) {
            projectsList.innerHTML = '<div class="no-data">No projects found</div>';
            return;
        }

        projectsList.innerHTML = projects.map(project => `
            <div class="project-item">
                <div class="project-header">
                    <h4>${project.name}</h4>
                    <div class="project-actions">
                        <button class="btn btn-sm btn-secondary" onclick="dashboard.editProject('${project.id}')">Edit</button>
                        <button class="btn btn-sm btn-danger" onclick="dashboard.deleteProject('${project.id}')">Delete</button>
                    </div>
                </div>
                <div class="project-description">${project.description || 'No description'}</div>
                <div class="project-meta">
                    <span class="project-date">Created: ${new Date(project.created_at).toLocaleDateString()}</span>
                    ${project.github_url ? `<a href="${project.github_url}" target="_blank" class="project-link">GitHub</a>` : ''}
                </div>
            </div>
        `).join('');
    }

    async loadEnvironment() {
        try {
            const response = await fetch('/api/environment');
            const data = await response.json();

            if (data.success) {
                this.updateEnvironmentEditor(data.variables);
            } else {
                throw new Error(data.error || 'Failed to load environment');
            }

        } catch (error) {
            console.error('Failed to load environment:', error);
            this.showNotification('Failed to load environment', 'error');
        }
    }

    updateEnvironmentEditor(variables) {
        const editor = document.getElementById('env-editor');

        editor.innerHTML = Object.entries(variables).map(([key, value]) => `
            <div class="env-variable">
                <label class="env-label">${key}</label>
                <input type="text" class="env-input" data-key="${key}" value="${value}"
                       ${value.includes('***') ? 'readonly' : ''}>
            </div>
        `).join('');

        // Add change listeners
        document.querySelectorAll('.env-input').forEach(input => {
            input.addEventListener('input', () => {
                document.getElementById('save-env').disabled = false;
            });
        });
    }

    async loadLogs() {
        const logType = document.getElementById('log-type').value;
        const search = document.getElementById('log-search').value;

        try {
            const response = await fetch(`/api/logs?type=${logType}&search=${encodeURIComponent(search)}&limit=100`);
            const data = await response.json();

            if (data.success) {
                this.updateLogViewer(data.logs);
            } else {
                throw new Error(data.error || 'Failed to load logs');
            }

        } catch (error) {
            console.error('Failed to load logs:', error);
            this.showNotification('Failed to load logs', 'error');
        }
    }

    updateLogViewer(logs) {
        const viewer = document.getElementById('log-viewer');

        if (!logs || logs.length === 0) {
            viewer.innerHTML = '<div class="no-data">No logs found</div>';
            return;
        }

        viewer.innerHTML = logs.map(log => `
            <div class="log-entry">
                <span class="log-timestamp">${log.timestamp}</span>
                <span class="log-level ${log.level.toLowerCase()}">${log.level}</span>
                <span class="log-message">${log.message}</span>
            </div>
        `).join('');
    }

    async runDiagnostics(type = 'quick') {
        const autoFix = document.getElementById('auto-fix')?.checked || false;

        try {
            this.showLoading(true);

            const response = await fetch('/api/diagnostics/run', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    type: type,
                    auto_fix: autoFix
                })
            });

            const data = await response.json();

            if (data.success) {
                this.updateDiagnosticResults(data.output, data.errors);
                this.showNotification('Diagnostics completed successfully', 'success');
            } else {
                throw new Error(data.error || 'Diagnostics failed');
            }

        } catch (error) {
            console.error('Failed to run diagnostics:', error);
            this.showNotification('Failed to run diagnostics', 'error');
        } finally {
            this.showLoading(false);
        }
    }

    updateDiagnosticResults(output, errors) {
        const results = document.getElementById('diagnostic-results');

        results.innerHTML = `
            ${output ? `<div class="diagnostic-output"><pre>${output}</pre></div>` : ''}
            ${errors ? `<div class="diagnostic-errors"><pre>${errors}</pre></div>` : ''}
        `;
    }

    async runHealthCheck() {
        await this.loadSystemStatus();
        this.showNotification('Health check completed', 'info');
    }

    async refreshCurrentSection() {
        await this.loadSectionData(this.currentSection);
        this.showNotification('Data refreshed', 'info');
    }

    showCreateProjectModal() {
        const modal = document.getElementById('modal');
        document.getElementById('modal-title').textContent = 'Create New Project';
        document.getElementById('modal-body').innerHTML = `
            <div class="form-group">
                <label for="project-name">Project Name</label>
                <input type="text" id="project-name" class="form-control" required>
            </div>
            <div class="form-group">
                <label for="project-description">Description</label>
                <textarea id="project-description" class="form-control"></textarea>
            </div>
            <div class="form-group">
                <label for="project-github">GitHub URL</label>
                <input type="url" id="project-github" class="form-control">
            </div>
        `;

        document.getElementById('modal-confirm').onclick = () => this.createProject();
        modal.classList.add('active');
    }

    async createProject() {
        const name = document.getElementById('project-name').value;
        const description = document.getElementById('project-description').value;
        const githubUrl = document.getElementById('project-github').value;

        if (!name) {
            this.showNotification('Project name is required', 'error');
            return;
        }

        try {
            const response = await fetch('/api/projects', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    id: Date.now().toString(),
                    name: name,
                    description: description,
                    github_url: githubUrl
                })
            });

            const data = await response.json();

            if (data.success) {
                this.hideModal();
                await this.loadProjects();
                this.showNotification('Project created successfully', 'success');
            } else {
                throw new Error(data.error || 'Failed to create project');
            }

        } catch (error) {
            console.error('Failed to create project:', error);
            this.showNotification('Failed to create project', 'error');
        }
    }

    async deleteProject(projectId) {
        if (!confirm('Are you sure you want to delete this project?')) {
            return;
        }

        try {
            const response = await fetch(`/api/projects/${projectId}`, {
                method: 'DELETE'
            });

            const data = await response.json();

            if (data.success) {
                await this.loadProjects();
                this.showNotification('Project deleted successfully', 'success');
            } else {
                throw new Error(data.error || 'Failed to delete project');
            }

        } catch (error) {
            console.error('Failed to delete project:', error);
            this.showNotification('Failed to delete project', 'error');
        }
    }

    async saveEnvironment() {
        const variables = {};
        document.querySelectorAll('.env-input').forEach(input => {
            const key = input.dataset.key;
            const value = input.value;
            if (!value.includes('***')) {
                variables[key] = value;
            }
        });

        try {
            const response = await fetch('/api/environment', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ variables })
            });

            const data = await response.json();

            if (data.success) {
                document.getElementById('save-env').disabled = true;
                this.showNotification('Environment saved successfully', 'success');
            } else {
                throw new Error(data.error || 'Failed to save environment');
            }

        } catch (error) {
            console.error('Failed to save environment:', error);
            this.showNotification('Failed to save environment', 'error');
        }
    }

    filterLogs() {
        // Implement client-side log filtering if needed
        this.loadLogs();
    }

    showModal() {
        document.getElementById('modal').classList.add('active');
    }

    hideModal() {
        document.getElementById('modal').classList.remove('active');
    }

    showLoading(show = true) {
        const overlay = document.getElementById('loading-overlay');
        if (show) {
            overlay.classList.add('active');
        } else {
            overlay.classList.remove('active');
        }
    }

    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <span class="notification-message">${message}</span>
            <button class="notification-close">&times;</button>
        `;

        // Add to page
        document.body.appendChild(notification);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);

        // Manual close
        notification.querySelector('.notification-close').onclick = () => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        };
    }

    updateSystemStatus(data) {
        this.systemStatus = data;
        this.updateSystemStatusUI(data);
    }
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new OOSDashboard();
});