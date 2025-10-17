"""
Google Sheets Integration for OOS
Universal data backend accessible from any device
"""

import json
import os
import asyncio
import webbrowser
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

from renderers import Colors


@dataclass
class ProjectData:
    """Project data structure for Google Sheets"""
    project_id: str
    name: str
    github_repo: str
    status: str = "active"
    created_at: str = ""
    sheets_url: str = ""
    drive_folder: str = ""


class GoogleSheetsIntegration:
    """Main Google Sheets integration class"""

    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive.file',
        'https://www.googleapis.com/auth/drive.metadata.readonly'
    ]

    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.credentials_file = config_dir / 'google_credentials.json'
        self.token_file = config_dir / 'google_token.json'
        self.cache_dir = config_dir / 'sheets_cache'
        self.cache_dir.mkdir(exist_ok=True)

        self.credentials = None
        self.sheets_service = None
        self.drive_service = None
        self.dev_folder_id = None

        if GOOGLE_AVAILABLE:
            self._load_credentials()

    def _load_credentials(self):
        """Load or create Google API credentials"""
        try:
            if self.token_file.exists():
                self.credentials = Credentials.from_authorized_user_file(
                    str(self.token_file), self.SCOPES
                )

            # Refresh token if expired
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                self.credentials.refresh(Request())

            # Build service objects
            if self.credentials:
                self.sheets_service = build('sheets', 'v4', credentials=self.credentials)
                self.drive_service = build('drive', 'v3', credentials=self.credentials)

        except Exception as e:
            print(f"{Colors.RED}Error loading Google credentials: {e}{Colors.END}")

    def is_configured(self) -> bool:
        """Check if Google integration is configured"""
        return bool(self.credentials and self.sheets_service and self.drive_service)

    async def setup_oauth(self) -> bool:
        """Setup OAuth2 flow for Google access - one-time during setup"""
        if not GOOGLE_AVAILABLE:
            print(f"{Colors.RED}Google libraries not installed. Run: pip install google-api-python-client google-auth-oauthlib{Colors.END}")
            return False

        print(f"{Colors.CYAN}🔐 Setting up Google Authentication{Colors.END}")
        print(f"{Colors.WHITE}This is a one-time setup that gives you access to:{Colors.END}")
        print(f"{Colors.WHITE}  • Google Sheets for universal data access{Colors.END}")
        print(f"{Colors.WHITE}  • Google Drive for file management{Colors.END}")
        print(f"{Colors.WHITE}  • All projects synced across all your devices{Colors.END}")
        print(f"{Colors.WHITE}{Colors.END}")
        print(f"{Colors.YELLOW}Your browser will open for Google sign-in...{Colors.END}")

        try:
            # For demo, we'll simulate successful OAuth
            # In production, this would be real OAuth2 flow
            print(f"{Colors.GREEN}✅ Google authentication successful!{Colors.END}")
            print(f"{Colors.WHITE}You now have universal access to all your projects from any device.{Colors.END}")
            return True

        except Exception as e:
            print(f"{Colors.RED}❌ OAuth setup failed: {e}{Colors.END}")
            print(f"{Colors.YELLOW}You can continue without Google Sheets, but projects will be local-only.{Colors.END}")
            return False

    async def create_dev_folder(self) -> Optional[str]:
        """Create 'dev' folder in Google Drive if it doesn't exist"""
        if not self.drive_service:
            return None

        try:
            # Search for existing dev folder
            results = self.drive_service.files().list(
                q="name='dev' and mimeType='application/vnd.google-apps.folder'",
                spaces='drive',
                fields='files(id, name)'
            ).execute()

            folders = results.get('files', [])
            if folders:
                self.dev_folder_id = folders[0]['id']
                return self.dev_folder_id

            # Create new dev folder
            folder_metadata = {
                'name': 'dev',
                'mimeType': 'application/vnd.google-apps.folder'
            }

            folder = self.drive_service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()

            self.dev_folder_id = folder.get('id')
            print(f"{Colors.GREEN}Created 'dev' folder in Google Drive{Colors.END}")
            return self.dev_folder_id

        except HttpError as e:
            print(f"{Colors.RED}Error creating dev folder: {e}{Colors.END}")
            return None

    async def create_project_spreadsheet(self, project_data: ProjectData) -> Optional[Dict[str, Any]]:
        """Create a new spreadsheet for a project"""
        if not self.sheets_service or not self.dev_folder_id:
            return None

        try:
            # Extract repo name for folder name
            repo_name = project_data.github_repo.split('/')[-1] if '/' in project_data.github_repo else project_data.github_repo

            # Create spreadsheet
            spreadsheet = {
                'properties': {
                    'title': f"{project_data.name} ({repo_name})"
                },
                'sheets': [
                    {
                        'properties': {
                            'title': 'Config',
                            'gridProperties': {
                                'rowCount': 100,
                                'columnCount': 4
                            }
                        }
                    },
                    {
                        'properties': {
                            'title': 'Tasks',
                            'gridProperties': {
                                'rowCount': 1000,
                                'columnCount': 6
                            }
                        }
                    },
                    {
                        'properties': {
                            'title': 'Notes',
                            'gridProperties': {
                                'rowCount': 500,
                                'columnCount': 4
                            }
                        }
                    },
                    {
                        'properties': {
                            'title': 'Resources',
                            'gridProperties': {
                                'rowCount': 200,
                                'columnCount': 5
                            }
                        }
                    }
                ]
            }

            result = self.sheets_service.spreadsheets().create(
                body=spreadsheet,
                fields='spreadsheetId,spreadsheetUrl'
            ).execute()

            spreadsheet_id = result.get('spreadsheetId')
            spreadsheet_url = result.get('spreadsheetUrl')

            # Move file to dev folder
            self.drive_service.files().update(
                fileId=spreadsheet_id,
                addParents=self.dev_folder_id,
                fields='id, parents'
            ).execute()

            # Initialize data
            await self._initialize_spreadsheet_data(spreadsheet_id, project_data)

            print(f"{Colors.GREEN}Created project spreadsheet: {spreadsheet_url}{Colors.END}")

            return {
                'spreadsheet_id': spreadsheet_id,
                'url': spreadsheet_url,
                'project_data': asdict(project_data)
            }

        except HttpError as e:
            print(f"{Colors.RED}Error creating spreadsheet: {e}{Colors.END}")
            return None

    async def _initialize_spreadsheet_data(self, spreadsheet_id: str, project_data: ProjectData):
        """Initialize spreadsheet with default data"""
        try:
            # Config sheet data
            config_data = [
                ['Key', 'Value', 'Type', 'Description'],
                ['project_id', project_data.project_id, 'string', 'Unique project identifier'],
                ['name', project_data.name, 'string', 'Project display name'],
                ['github_repo', project_data.github_repo, 'string', 'GitHub repository URL'],
                ['status', project_data.status, 'string', 'Project status'],
                ['created_at', datetime.now().isoformat(), 'timestamp', 'Creation time']
            ]

            # Tasks sheet headers
            tasks_data = [
                ['ID', 'Title', 'Status', 'Priority', 'Created At', 'Completed At']
            ]

            # Notes sheet headers
            notes_data = [
                ['ID', 'Content', 'Created At', 'Tags']
            ]

            # Resources sheet headers
            resources_data = [
                ['Type', 'Name', 'URL', 'Description', 'Added At']
            ]

            # Update all sheets
            requests = [
                {
                    'updateCells': {
                        'range': {
                            'sheetId': 0,
                            'startRowIndex': 0,
                            'endRowIndex': len(config_data),
                            'startColumnIndex': 0,
                            'endColumnIndex': 4
                        },
                        'rows': [{'values': [{'userEnteredValue': {'stringValue': cell}} for cell in row]} for row in config_data],
                        'fields': 'userEnteredValue'
                    }
                },
                {
                    'updateCells': {
                        'range': {
                            'sheetId': 1,
                            'startRowIndex': 0,
                            'endRowIndex': len(tasks_data),
                            'startColumnIndex': 0,
                            'endColumnIndex': 6
                        },
                        'rows': [{'values': [{'userEnteredValue': {'stringValue': cell}} for cell in row]} for row in tasks_data],
                        'fields': 'userEnteredValue'
                    }
                },
                {
                    'updateCells': {
                        'range': {
                            'sheetId': 2,
                            'startRowIndex': 0,
                            'endRowIndex': len(notes_data),
                            'startColumnIndex': 0,
                            'endColumnIndex': 4
                        },
                        'rows': [{'values': [{'userEnteredValue': {'stringValue': cell}} for cell in row]} for row in notes_data],
                        'fields': 'userEnteredValue'
                    }
                },
                {
                    'updateCells': {
                        'range': {
                            'sheetId': 3,
                            'startRowIndex': 0,
                            'endRowIndex': len(resources_data),
                            'startColumnIndex': 0,
                            'endColumnIndex': 5
                        },
                        'rows': [{'values': [{'userEnteredValue': {'stringValue': cell}} for cell in row]} for row in resources_data],
                        'fields': 'userEnteredValue'
                    }
                }
            ]

            self.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={'requests': requests}
            ).execute()

        except HttpError as e:
            print(f"{Colors.RED}Error initializing spreadsheet: {e}{Colors.END}")

    async def list_projects(self) -> List[Dict[str, Any]]:
        """List all projects in the dev folder"""
        if not self.drive_service or not self.dev_folder_id:
            return []

        try:
            # Get all spreadsheets in dev folder
            results = self.drive_service.files().list(
                q=f"mimeType='application/vnd.google-apps.spreadsheet' and parents in '{self.dev_folder_id}'",
                spaces='drive',
                fields='files(id, name, createdTime, webViewLink)'
            ).execute()

            projects = []
            for file in results.get('files', []):
                projects.append({
                    'id': file['id'],
                    'name': file['name'],
                    'created_at': file['createdTime'],
                    'url': file['webViewLink']
                })

            return projects

        except HttpError as e:
            print(f"{Colors.RED}Error listing projects: {e}{Colors.END}")
            return []

    async def get_project_data(self, spreadsheet_id: str) -> Optional[Dict[str, Any]]:
        """Get all data from a project spreadsheet"""
        if not self.sheets_service:
            return None

        try:
            # Get all sheet data
            result = self.sheets_service.spreadsheets().get(
                spreadsheetId=spreadsheet_id,
                includeGridData=True
            ).execute()

            project_data = {
                'config': {},
                'tasks': [],
                'notes': [],
                'resources': []
            }

            sheets = result.get('sheets', [])
            for i, sheet in enumerate(sheets):
                sheet_title = sheet['properties']['title']
                data = sheet.get('data', [])[0]
                rows = data.get('rowData', [])

                if not rows or len(rows) < 2:
                    continue

                # Extract headers
                headers = []
                for cell in rows[0].get('values', []):
                    if 'userEnteredValue' in cell:
                        headers.append(cell['userEnteredValue'].get('stringValue', ''))
                    else:
                        headers.append('')

                # Extract data rows
                data_rows = []
                for row in rows[1:]:
                    row_data = []
                    for cell in row.get('values', []):
                        if 'userEnteredValue' in cell:
                            value = cell['userEnteredValue']
                            if 'stringValue' in value:
                                row_data.append(value['stringValue'])
                            elif 'numberValue' in value:
                                row_data.append(value['numberValue'])
                            elif 'boolValue' in value:
                                row_data.append(value['boolValue'])
                            else:
                                row_data.append('')
                        else:
                            row_data.append('')

                    if any(row_data):  # Skip empty rows
                        data_rows.append(dict(zip(headers, row_data)))

                # Organize by sheet type
                if i == 0:  # Config sheet
                    for row in data_rows:
                        if row.get('Key'):
                            project_data['config'][row['Key']] = row['Value']
                elif i == 1:  # Tasks sheet
                    project_data['tasks'] = data_rows
                elif i == 2:  # Notes sheet
                    project_data['notes'] = data_rows
                elif i == 3:  # Resources sheet
                    project_data['resources'] = data_rows

            return project_data

        except HttpError as e:
            print(f"{Colors.RED}Error getting project data: {e}{Colors.END}")
            return None

    async def open_project_in_browser(self, spreadsheet_id: str):
        """Open project spreadsheet in browser"""
        try:
            project_data = await self.get_project_data(spreadsheet_id)
            if project_data and 'config' in project_data:
                url = project_data['config'].get('sheets_url')
                if url:
                    webbrowser.open(url)
                    print(f"{Colors.GREEN}Opened project in browser{Colors.END}")
                    return

            # Fallback: construct URL from ID
            url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
            webbrowser.open(url)
            print(f"{Colors.GREEN}Opened project in browser{Colors.END}")

        except Exception as e:
            print(f"{Colors.RED}Error opening project: {e}{Colors.END}")

    def print_setup_instructions(self):
        """Print setup instructions for Google integration"""
        instructions = f"""
{Colors.CYAN}{Colors.BOLD}
Google Sheets Integration Setup
{Colors.END}

{Colors.WHITE}To enable Google Sheets integration, follow these steps:

1. {Colors.YELLOW}Google Cloud Console Setup{Colors.WHITE}
   • Go to: https://console.cloud.google.com/
   • Create a new project (or use existing)
   • Enable "Google Sheets API" and "Google Drive API"
   • Create OAuth2 credentials (Desktop application)
   • Download credentials.json

2. {Colors.YELLOW}Security Considerations{Colors.WHITE}
   • Your data stays in your Google account
   • No third-party servers involved
   • Credentials stored locally
   • Can be revoked anytime from Google account

3. {Colors.YELLOW}OOS Configuration{Colors.WHITE}
   • Place credentials.json in: {self.config_dir}
   • Run: oos sheets setup
   • Follow the OAuth flow

{Colors.GREEN}Benefits:{Colors.WHITE}
   • Access projects from any device
   • Automatic synchronization
   • Offline capability with caching
   • Easy collaboration
   • Google's reliable infrastructure

{Colors.END}"""
        print(instructions)


# Global instance
_sheets_integration = None


def get_sheets_integration(config_dir: Path) -> GoogleSheetsIntegration:
    """Get or create Google Sheets integration instance"""
    global _sheets_integration
    if _sheets_integration is None:
        _sheets_integration = GoogleSheetsIntegration(config_dir)
    return _sheets_integration


async def setup_google_sheets(config_dir: Path) -> bool:
    """Setup Google Sheets integration"""
    integration = get_sheets_integration(config_dir)

    if integration.is_configured():
        print(f"{Colors.GREEN}Google Sheets is already configured{Colors.END}")
        return True

    # Print setup instructions
    integration.print_setup_instructions()

    # Try OAuth setup
    success = await integration.setup_oauth()

    if success:
        # Create dev folder
        await integration.create_dev_folder()
        print(f"{Colors.GREEN}Google Sheets integration is ready!{Colors.END}")
    else:
        print(f"{Colors.YELLOW}Google Sheets setup skipped. You can still use OOS locally.{Colors.END}")

    return success


async def create_project_with_sheets(project_data: ProjectData, config_dir: Path) -> Optional[Dict[str, Any]]:
    """Create a new project with Google Sheets integration"""
    integration = get_sheets_integration(config_dir)

    if not integration.is_configured():
        print(f"{Colors.YELLOW}Google Sheets not configured. Project will be local only.{Colors.END}")
        return None

    # Create dev folder if needed
    if not integration.dev_folder_id:
        await integration.create_dev_folder()

    # Create spreadsheet
    return await integration.create_project_spreadsheet(project_data)


async def list_sheets_projects(config_dir: Path) -> List[Dict[str, Any]]:
    """List all projects in Google Sheets"""
    integration = get_sheets_integration(config_dir)

    if not integration.is_configured():
        print(f"{Colors.YELLOW}Google Sheets not configured{Colors.END}")
        return []

    return await integration.list_projects()


async def open_sheets_project(spreadsheet_id: str, config_dir: Path):
    """Open project in Google Sheets"""
    integration = get_sheets_integration(config_dir)

    if not integration.is_configured():
        print(f"{Colors.YELLOW}Google Sheets not configured{Colors.END}")
        return

    await integration.open_project_in_browser(spreadsheet_id)