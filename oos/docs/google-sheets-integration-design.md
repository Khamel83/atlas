# Google Sheets Integration Design for Universal Data Access

## 🎯 Vision

Create a universal data backend where all OOS projects live in Google Sheets, accessible from any device with internet access. Projects are organized by GitHub repository names in a dedicated 'dev' folder in Google Drive.

## 📋 Core Concept

- **Single Source of Truth**: All project data lives in Google Sheets
- **Universal Access**: Access projects from any device (phone, tablet, laptop, OCI VM)
- **GitHub-Driven Organization**: Projects organized by repository names
- **Automatic Sync**: Changes sync automatically across all devices
- **Zero Configuration**: Works with existing Google account

## 🏗️ Architecture Overview

```
Google Drive
└── dev/ (auto-created folder)
    ├── project-repo-name-1/ (project folder)
    │   ├── config.json (project settings)
    │   ├── tasks.csv (task management)
    │   ├── notes.md (project notes)
    │   └── data/ (project-specific data)
    ├── project-repo-name-2/
    │   ├── config.json
    │   ├── tasks.csv
    │   └── notes.md
    └── global-settings.json (user preferences)
```

## 🔧 Technical Implementation

### 1. Authentication Setup

```python
# During OOS setup, request Google Sheets/Drive access
def setup_google_integration():
    """Setup Google Sheets/Drive integration"""
    print_info("Connect Google account for universal data access")

    # OAuth2 flow for Google Sheets and Drive APIs
    # Scopes needed:
    # - https://www.googleapis.com/auth/spreadsheets
    # - https://www.googleapis.com/auth/drive.file
    # - https://www.googleapis.com/auth/drive.metadata.readonly

    # Store credentials securely
    # Generate refresh token for persistent access
```

### 2. Project Creation Workflow

```python
async def create_project_with_sheets(project_name, github_repo):
    """Create new project with Google Sheets integration"""

    # Extract repo name from GitHub URL
    repo_name = extract_github_repo_name(github_repo)

    # Create folder structure in Google Drive
    drive_folder = create_drive_folder(f"dev/{repo_name}")

    # Create project spreadsheet
    spreadsheet = create_project_spreadsheet(drive_folder, project_name)

    # Setup standard sheets within the spreadsheet
    sheets = {
        'config': {
            'columns': ['key', 'value', 'type', 'description'],
            'data': [
                ['project_name', project_name, 'string', 'Project display name'],
                ['github_repo', github_repo, 'string', 'GitHub repository URL'],
                ['created_at', datetime.now().isoformat(), 'timestamp', 'Creation time'],
                ['status', 'active', 'string', 'Project status']
            ]
        },
        'tasks': {
            'columns': ['id', 'title', 'status', 'priority', 'created_at', 'completed_at'],
            'data': []
        },
        'notes': {
            'columns': ['id', 'content', 'created_at', 'tags'],
            'data': []
        },
        'resources': {
            'columns': ['type', 'name', 'url', 'description', 'added_at'],
            'data': []
        }
    }

    # Create sheets and populate initial data
    for sheet_name, sheet_config in sheets.items():
        create_sheet(spreadsheet.id, sheet_name, sheet_config)

    return {
        'project_id': spreadsheet.id,
        'drive_folder': drive_folder.id,
        'sheets_url': spreadsheet.url
    }
```

### 3. Data Synchronization Layer

```python
class GoogleSheetsSync:
    """Handles bi-directional sync with Google Sheets"""

    def __init__(self, credentials):
        self.sheets_service = build('sheets', 'v4', credentials=credentials)
        self.drive_service = build('drive', 'v3', credentials=credentials)
        self.cache = {}  # Local cache for offline access

    async def sync_project_data(self, project_id):
        """Sync project data between local and Google Sheets"""

        # Get local changes
        local_changes = self.get_local_changes(project_id)

        # Get remote changes
        remote_changes = await self.get_remote_changes(project_id)

        # Resolve conflicts (last-write-wins or intelligent merge)
        merged_data = self.resolve_conflicts(local_changes, remote_changes)

        # Update both local and remote
        await self.update_sheets(project_id, merged_data)
        self.update_local_cache(project_id, merged_data)

        return merged_data

    async def get_remote_changes(self, project_id):
        """Get changes from Google Sheets"""
        spreadsheet_id = self.get_spreadsheet_id(project_id)

        # Read all sheets
        result = self.sheets_service.spreadsheets().get(
            spreadsheetId=spreadsheet_id,
            includeGridData=True
        ).execute()

        return self.parse_sheets_data(result)
```

### 4. CLI Integration Commands

```python
# Extensions to oos_cli.py
class OOSCommandProcessor:
    # ... existing code ...

    async def handle_sheets_command(self, command: str) -> int:
        """Handle Google Sheets-related commands"""

        if command.startswith('sheets setup'):
            return await self.setup_google_sheets()

        elif command.startswith('sheets list'):
            return await self.list_projects_in_sheets()

        elif command.startswith('sheets open'):
            project_name = command.replace('sheets open', '').strip()
            return await self.open_project_sheets(project_name)

        elif command.startswith('sheets sync'):
            return await self.sync_project_data()

        else:
            print_info("Google Sheets commands:")
            print_info("  oos sheets setup      - Setup Google integration")
            print_info("  oos sheets list      - List all projects in Sheets")
            print_info("  oos sheets open <name> - Open project in browser")
            print_info("  oos sheets sync      - Sync current project")
            return 0

    async def setup_google_sheets(self):
        """Setup Google Sheets integration"""
        print_step("Google Sheets Setup", "Universal data access")

        # Check if already configured
        if self.config.get('google_credentials'):
            print_info("Google Sheets already configured")
            return 0

        # OAuth flow
        credentials = await self.google_oauth_flow()

        # Create dev folder if needed
        dev_folder = self.create_dev_folder()

        # Store credentials
        self.config['google_credentials'] = credentials
        self.config['google_dev_folder'] = dev_folder.id
        save_config(self.config)

        print_success("Google Sheets integration ready!")
        return 0
```

### 5. Offline Support and Caching

```python
class LocalCache:
    """Local cache for offline access to Sheets data"""

    def __init__(self, cache_dir):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

    def get_cached_project(self, project_id):
        """Get cached project data"""
        cache_file = self.cache_dir / f"{project_id}.json"
        if cache_file.exists():
            with open(cache_file, 'r') as f:
                return json.load(f)
        return None

    def cache_project_data(self, project_id, data):
        """Cache project data locally"""
        cache_file = self.cache_dir / f"{project_id}.json"
        with open(cache_file, 'w') as f:
            json.dump(data, f, indent=2)

    def get_pending_changes(self, project_id):
        """Get changes made while offline"""
        pending_file = self.cache_dir / f"{project_id}_pending.json"
        if pending_file.exists():
            with open(pending_file, 'r') as f:
                return json.load(f)
        return []
```

## 📱 Mobile/Web Access

### Browser Extension (Chrome/Firefox)
```javascript
// Browser extension for quick access
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: 'open-oos-project',
    title: 'Open in OOS Sheets',
    contexts: ['selection']
  });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === 'open-oos-project') {
    // Extract project name and open in Google Sheets
    const projectName = extractProjectName(info.selectionText);
    chrome.tabs.create({ url: `https://sheets.google.com/${projectName}` });
  }
});
```

### Mobile Web Interface
```python
# Simple web interface for mobile access
@app.route('/mobile')
def mobile_interface():
    """Simple mobile interface for OOS projects"""
    projects = get_all_projects_from_sheets()
    return render_template('mobile.html', projects=projects)

@app.route('/mobile/project/<project_id>')
def mobile_project(project_id):
    """View and edit project on mobile"""
    project_data = get_project_from_sheets(project_id)
    return render_template('mobile_project.html', project=project_data)
```

## 🔒 Security and Privacy

### Data Security
- **OAuth2 Authentication**: Secure token-based access
- **Scope Limitation**: Only access specific folders, not entire Drive
- **Data Encryption**: All data encrypted in transit (HTTPS)
- **Local Cache**: Encrypted local storage for offline access

### Privacy Controls
- **User Data Ownership**: Data stays in user's Google account
- **No Third-Party Servers**: Direct Google API access
- **Selective Sync**: Choose what data to sync
- **Audit Trail**: Log all access and changes

## 📊 Usage Examples

### Basic Workflow
```bash
# Setup Google integration
oos sheets setup

# Create new project (automatically creates Sheets)
oos create chatbot "Customer Service Bot"

# Open project in browser
oos sheets open customer-service-bot

# Sync changes from mobile
oos sheets sync

# List all projects
oos sheets list
```

### Mobile Access
1. Open browser on phone
2. Go to Google Sheets
3. Navigate to 'dev' folder
4. Open any project
5. Make changes
6. Changes sync to all devices

### Collaboration
```bash
# Share project with team member
oos share customer-service-bot with colleague@gmail.com

# Set permissions
oos permissions customer-service-bot --read-only team@company.com
```

## 🚀 Implementation Phases

### Phase 1: Core Integration
- [ ] Google OAuth2 setup
- [ ] Basic Sheets API integration
- [ ] Project creation in Sheets
- [ ] CLI commands for Sheets access

### Phase 2: Synchronization
- [ ] Bi-directional sync
- [ ] Conflict resolution
- [ ] Offline caching
- [ ] Auto-sync on changes

### Phase 3: Enhanced Features
- [ ] Mobile web interface
- [ ] Browser extension
- [ ] Collaboration features
- [ ] Advanced permissions

### Phase 4: Integration
- [ ] Deep integration with existing OOS features
- [ ] Automated backups
- [ ] Data analytics
- [ ] Performance optimization

## 📈 Benefits

1. **Universal Access**: Projects available from any device
2. **Zero Infrastructure**: No servers to maintain
3. **Familiar Interface**: Google Sheets is widely known
4. **Automatic Backup**: Google's robust infrastructure
5. **Offline Access**: Local caching for offline work
6. **Collaboration**: Easy sharing and teamwork
7. **Cost Effective**: Uses free Google quota
8. **Scalable**: Handles large projects easily

## 🎉 User Experience

**Before:**
- Projects stuck on local machine
- No access from mobile devices
- Manual backup and sync required
- Difficult collaboration

**After:**
- Open project on any device instantly
- Changes sync automatically
- Easy sharing with team members
- Work offline seamlessly
- Everything backed up by Google

This integration transforms OOS from a local tool into a universal platform accessible from anywhere, making AI project development truly portable and collaborative.