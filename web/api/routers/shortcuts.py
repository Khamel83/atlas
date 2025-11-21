from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse, HTMLResponse
import os
from pathlib import Path
import json
from typing import List, Dict

router = APIRouter()

# Get the shortcuts directory path
SHORTCUTS_DIR = Path(__file__).parent.parent.parent / "quick_start_package" / "shortcuts"

@router.get("/")
async def list_shortcuts():
    """List all available iOS shortcuts"""
    try:
        shortcuts = []
        if SHORTCUTS_DIR.exists():
            for shortcut_file in SHORTCUTS_DIR.glob("*.shortcut"):
                shortcuts.append({
                    "name": shortcut_file.stem,
                    "filename": shortcut_file.name,
                    "download_url": f"/api/v1/shortcuts/download/{shortcut_file.name}"
                })

        return {"shortcuts": shortcuts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing shortcuts: {str(e)}")

@router.get("/download/{filename}")
async def download_shortcut(filename: str):
    """Download a specific iOS shortcut file"""
    try:
        # Security check - only allow .shortcut files
        if not filename.endswith('.shortcut'):
            raise HTTPException(status_code=400, detail="Invalid file type")

        file_path = SHORTCUTS_DIR / filename

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Shortcut not found")

        # Return the file with proper headers for iOS shortcuts
        return FileResponse(
            path=str(file_path),
            media_type='application/octet-stream',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"'
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading shortcut: {str(e)}")

@router.get("/install")
async def shortcuts_install_page():
    """Serve a mobile-friendly page for installing shortcuts"""
    try:
        shortcuts = []
        if SHORTCUTS_DIR.exists():
            for shortcut_file in SHORTCUTS_DIR.glob("*.shortcut"):
                # Clean up the name for display
                display_name = shortcut_file.stem.replace('_', ' ').title()
                shortcuts.append({
                    "name": display_name,
                    "filename": shortcut_file.name,
                    "download_url": f"/api/v1/shortcuts/download/{shortcut_file.name}"
                })

        # Create a mobile-friendly HTML page
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Atlas iOS Shortcuts</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f7;
            line-height: 1.6;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #1d1d1f;
            text-align: center;
            margin-bottom: 10px;
        }}
        .subtitle {{
            text-align: center;
            color: #6e6e73;
            margin-bottom: 30px;
        }}
        .shortcut-card {{
            border: 1px solid #e5e5e7;
            border-radius: 8px;
            margin-bottom: 15px;
            overflow: hidden;
        }}
        .shortcut-header {{
            padding: 15px;
            background: #f9f9f9;
            border-bottom: 1px solid #e5e5e7;
        }}
        .shortcut-name {{
            font-weight: 600;
            color: #1d1d1f;
            margin-bottom: 5px;
        }}
        .shortcut-description {{
            color: #6e6e73;
            font-size: 14px;
        }}
        .download-btn {{
            display: block;
            width: 100%;
            padding: 15px;
            background: #007AFF;
            color: white;
            text-decoration: none;
            text-align: center;
            font-weight: 600;
            border: none;
            cursor: pointer;
        }}
        .download-btn:hover {{
            background: #0056CC;
        }}
        .instructions {{
            background: #e8f4fd;
            border-left: 4px solid #007AFF;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        .instructions h3 {{
            margin-top: 0;
            color: #1d1d1f;
        }}
        .step {{
            margin: 10px 0;
        }}
        .install-all {{
            text-align: center;
            margin: 30px 0;
        }}
        .install-all-btn {{
            display: inline-block;
            padding: 15px 30px;
            background: #34C759;
            color: white;
            text-decoration: none;
            border-radius: 8px;
            font-weight: 600;
        }}
        @media (max-width: 480px) {{
            body {{ padding: 10px; }}
            .container {{ padding: 15px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Atlas iOS Shortcuts</h1>
        <p class="subtitle">Tap to install shortcuts directly on your iPhone</p>

        <div class="instructions">
            <h3>📱 Installation Instructions</h3>
            <div class="step">1. Tap the "Download" button for any shortcut</div>
            <div class="step">2. iOS will ask if you want to "Get Shortcut"</div>
            <div class="step">3. Tap "Get Shortcut" then "Add Shortcut"</div>
            <div class="step">4. Enable "Hey Siri" by saying the shortcut name</div>
        </div>

        <div class="install-all">
            <a href="/install_shortcuts.sh" class="install-all-btn" download>
                📦 Download Install Script
            </a>
            <div style="margin-top: 10px; font-size: 14px; color: #6e6e73;">
                For computer installation
            </div>
        </div>

        {_generate_shortcut_cards(shortcuts)}

        <div style="text-align: center; margin-top: 30px; color: #6e6e73; font-size: 14px;">
            <p>🧠 Atlas: Where Your Knowledge Meets AI Intelligence</p>
        </div>
    </div>

    <script>
        // Track downloads for analytics
        document.querySelectorAll('.download-btn').forEach(btn => {{
            btn.addEventListener('click', function() {{
                const shortcutName = this.dataset.shortcut;
                console.log('Downloaded shortcut:', shortcutName);
            }});
        }});
    </script>
</body>
</html>
        """

        return HTMLResponse(content=html_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating install page: {str(e)}")

def _generate_shortcut_cards(shortcuts: List[Dict]) -> str:
    """Generate HTML cards for shortcuts"""
    cards_html = ""

    # Descriptions for each shortcut
    descriptions = {
        "save_to_atlas": "🌐 Save Safari web pages directly to Atlas - Use with Share Sheet",
        "Capture Thought": "Quickly save any thought or idea to Atlas",
        "Capture Evening Thought": "Log your evening reflections and thoughts",
        "Log Meal": "Track your meals for health insights",
        "Log Mood": "Record your mood and emotional state",
        "Start Focus": "Begin a focused work session",
        "Log Home Activity Context": "Track activities when at home",
        "Log Work Task Context": "Log work tasks and productivity context"
    }

    for shortcut in shortcuts:
        # Format display name
        display_name = shortcut["name"].replace("_", " ").title()
        if shortcut["name"] == "save_to_atlas":
            display_name = "🌐 Save to Atlas (Safari Share Sheet)"

        # Special handling for save_to_atlas
        original_name = shortcut["name"]
        print(f"DEBUG: Processing shortcut original='{original_name}'")
        if original_name == "save_to_atlas" or original_name == "Save To Atlas":
            description = "🌐 Save Safari web pages directly to Atlas - Use with Share Sheet"
            print(f"DEBUG: Applied Safari description for save_to_atlas")
        else:
            description = descriptions.get(shortcut["name"], "Atlas cognitive enhancement shortcut")
            print(f"DEBUG: Used fallback description for {shortcut['name']}")
        cards_html += f"""
        <div class="shortcut-card">
            <div class="shortcut-header">
                <div class="shortcut-name">{display_name}</div>
                <div class="shortcut-description">{description}</div>
            </div>
            <a href="{shortcut['download_url']}"
               class="download-btn"
               data-shortcut="{display_name}">
                📥 Download & Install
            </a>
        </div>
        """

    return cards_html

@router.get("/install-script")
async def download_install_script():
    """Download the install_shortcuts.sh script"""
    try:
        script_path = Path(__file__).parent.parent.parent / "install_shortcuts.sh"

        if not script_path.exists():
            raise HTTPException(status_code=404, detail="Install script not found")

        return FileResponse(
            path=str(script_path),
            media_type='text/plain',
            headers={
                'Content-Disposition': 'attachment; filename="install_shortcuts.sh"'
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading install script: {str(e)}")