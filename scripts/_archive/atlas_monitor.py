#!/usr/bin/env python3
"""
Simple Atlas System Monitor
Checks all key Atlas components and provides clear status
"""

import os
import sys
import json
import psutil
import requests
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

def check_api_server():
    """Check if Atlas API is running"""
    try:
        response = requests.get("http://localhost:8001/api/v1/health", timeout=5)
        if response.status_code == 200:
            return {"status": "healthy", "port": 8001}
        else:
            return {"status": "unhealthy", "error": f"HTTP {response.status_code}"}
    except requests.exceptions.ConnectionError:
        try:
            # Try port 8000 as backup
            response = requests.get("http://localhost:8000/api/v1/health", timeout=5)
            if response.status_code == 200:
                return {"status": "healthy", "port": 8000}
            else:
                return {"status": "unhealthy", "error": "No API server found"}
        except:
            return {"status": "down", "error": "API server not responding"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def check_smart_dispatcher():
    """Check smart dispatcher job system"""
    try:
        # Try to get worker status
        for port in [8001, 8000]:
            try:
                response = requests.get(f"http://localhost:{port}/api/v1/worker/jobs?worker_id=test", timeout=5)
                if response.status_code == 200:
                    return {"status": "operational", "port": port}
            except:
                continue
        return {"status": "unavailable", "error": "Worker endpoints not responding"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def check_content_processing():
    """Check recent content processing activity"""
    try:
        base_dir = Path(__file__).parent

        # Check recent podcast processing
        podcast_dir = base_dir / "output" / "podcasts"
        recent_podcasts = 0
        if podcast_dir.exists():
            cutoff = datetime.now() - timedelta(hours=24)
            for file in podcast_dir.glob("*.json"):
                if datetime.fromtimestamp(file.stat().st_mtime) > cutoff:
                    recent_podcasts += 1

        # Check recent article processing
        article_dir = base_dir / "output" / "articles"
        recent_articles = 0
        if article_dir.exists():
            cutoff = datetime.now() - timedelta(hours=24)
            for file in article_dir.glob("**/*.json"):
                if datetime.fromtimestamp(file.stat().st_mtime) > cutoff:
                    recent_articles += 1

        # Check database
        db_path = base_dir / "atlas.db"
        db_exists = db_path.exists()

        return {
            "status": "active" if (recent_podcasts > 0 or recent_articles > 0) else "idle",
            "recent_podcasts_24h": recent_podcasts,
            "recent_articles_24h": recent_articles,
            "database_exists": db_exists
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

def check_transcript_system():
    """Check transcript discovery and fetching"""
    try:
        base_dir = Path(__file__).parent

        # Check if transcript discovery results exist
        discovery_file = base_dir / "transcript_discovery_results.json"
        discovery_status = "completed" if discovery_file.exists() else "pending"

        # Check for actual transcript files
        transcript_count = 0
        for pattern in ["**/*transcript*.json", "**/*transcript*.md", "**/*transcript*.txt"]:
            transcript_count += len(list(Path("output").glob(pattern))) if Path("output").exists() else 0

        return {
            "status": "operational" if transcript_count > 0 else discovery_status,
            "discovery_completed": discovery_status == "completed",
            "transcript_files_found": transcript_count
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

def check_background_processes():
    """Check for running Atlas processes"""
    try:
        atlas_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
            try:
                cmdline = proc.info['cmdline']
                if cmdline and any('atlas' in str(arg).lower() for arg in cmdline):
                    atlas_processes.append({
                        "pid": proc.info['pid'],
                        "name": proc.info['name'],
                        "command": ' '.join(cmdline)[:100],
                        "uptime_hours": round((datetime.now().timestamp() - proc.info['create_time']) / 3600, 1)
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Check for uvicorn processes (API server)
        uvicorn_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info['cmdline']
                if cmdline and 'uvicorn' in str(cmdline) and 'main:app' in str(cmdline):
                    uvicorn_processes.append({
                        "pid": proc.info['pid'],
                        "command": ' '.join(cmdline)[:100]
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return {
            "atlas_processes": len(atlas_processes),
            "api_processes": len(uvicorn_processes),
            "processes": atlas_processes + uvicorn_processes
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

def get_system_summary():
    """Get overall system health summary"""

    print("🎯 Atlas System Monitor")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Check API Server
    api_status = check_api_server()
    print(f"🌐 API Server:")
    if api_status["status"] == "healthy":
        print(f"   ✅ Running on port {api_status['port']}")
    else:
        print(f"   ❌ {api_status['status'].title()}: {api_status.get('error', 'Unknown error')}")
    print()

    # Check Smart Dispatcher
    dispatcher_status = check_smart_dispatcher()
    print(f"🧠 Smart Dispatcher:")
    if dispatcher_status["status"] == "operational":
        print(f"   ✅ Job system operational on port {dispatcher_status['port']}")
    else:
        print(f"   ❌ {dispatcher_status['status'].title()}: {dispatcher_status.get('error', 'Unknown error')}")
    print()

    # Check Content Processing
    content_status = check_content_processing()
    print(f"📊 Content Processing:")
    print(f"   Status: {'✅' if content_status['status'] == 'active' else '🔄'} {content_status['status'].title()}")
    print(f"   Recent activity (24h): {content_status['recent_podcasts_24h']} podcasts, {content_status['recent_articles_24h']} articles")
    print(f"   Database: {'✅' if content_status['database_exists'] else '❌'} {'Present' if content_status['database_exists'] else 'Missing'}")
    print()

    # Check Transcript System
    transcript_status = check_transcript_system()
    print(f"🎙️ Transcript System:")
    print(f"   Status: {'✅' if transcript_status['status'] == 'operational' else '🔄'} {transcript_status['status'].title()}")
    print(f"   Discovery: {'✅' if transcript_status['discovery_completed'] else '🔄'} {'Complete' if transcript_status['discovery_completed'] else 'Pending'}")
    print(f"   Transcript files: {transcript_status['transcript_files_found']}")
    print()

    # Check Background Processes
    process_status = check_background_processes()
    print(f"🔄 Background Processes:")
    print(f"   Atlas processes: {process_status['atlas_processes']}")
    print(f"   API processes: {process_status['api_processes']}")

    if process_status.get('processes'):
        print("   Active processes:")
        for proc in process_status['processes'][:5]:  # Show first 5
            uptime = f" ({proc['uptime_hours']}h)" if 'uptime_hours' in proc else ""
            print(f"     • PID {proc['pid']}: {proc['command'][:80]}...{uptime}")
    print()

    # Overall Status
    healthy_components = 0
    total_components = 4

    if api_status["status"] == "healthy":
        healthy_components += 1
    if dispatcher_status["status"] == "operational":
        healthy_components += 1
    if content_status["status"] in ["active", "idle"]:
        healthy_components += 1
    if transcript_status["status"] in ["operational", "completed"]:
        healthy_components += 1

    health_percentage = (healthy_components / total_components) * 100

    print(f"🎯 Overall Health: {health_percentage:.0f}% ({healthy_components}/{total_components} components healthy)")

    if health_percentage >= 75:
        print("✅ Atlas is running well")
    elif health_percentage >= 50:
        print("⚠️ Atlas has some issues but is functional")
    else:
        print("❌ Atlas needs attention")

    print("=" * 50)

if __name__ == "__main__":
    try:
        get_system_summary()
    except KeyboardInterrupt:
        print("\n⏹️ Monitor stopped by user")
    except Exception as e:
        print(f"❌ Monitor error: {e}")