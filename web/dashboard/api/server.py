#!/usr/bin/env python3
"""
OOS Web Dashboard API Server
Provides REST API for OOS management and monitoring
"""

import os
import sys
import json
import subprocess
import asyncio
import logging
import time
import shlex
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import hashlib
import secrets

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from flask import Flask, request, jsonify, render_template_string, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from werkzeug.security import generate_password_hash, check_password_hash

# Configuration
class Config:
    SECRET_KEY = os.environ.get('DASHBOARD_SECRET_KEY') or secrets.token_hex(32)
    DEBUG = os.environ.get('DASHBOARD_DEBUG', 'false').lower() == 'true'
    HOST = os.environ.get('DASHBOARD_HOST', '127.0.0.1')
    PORT = int(os.environ.get('DASHBOARD_PORT', 8052))
    PROJECT_ROOT = project_root
    LOG_LEVEL = logging.INFO if not DEBUG else logging.DEBUG
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///atlas.db')

def init_db():
    import sqlite3
    conn = sqlite3.connect(Config.DATABASE_URL.replace('sqlite:///', ''))
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            github_url TEXT,
            created_at TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Setup logging
logging.basicConfig(level=Config.LOG_LEVEL)
logger = logging.getLogger(__name__)

# In-memory storage for demo (replace with database in production)
dashboard_data = {
    'system_status': {},
    'projects': [],
    'logs': [],
    'alerts': [],
    'users': {
        # WARNING: Default admin account - change password immediately
        'admin': {
            'password_hash': generate_password_hash(secrets.token_urlsafe(16)),  # Random secure password
            'role': 'admin',
            'created_at': datetime.now().isoformat(),
            'requires_password_change': True
        }
    }
}

# Utility functions
def run_command(cmd: str, cwd: str = None) -> Dict[str, Any]:
    """Run a shell command and return result"""
    try:
        # Use shlex.split for secure command execution
        cmd_list = shlex.split(cmd)
        result = subprocess.run(
            cmd_list,
            cwd=cwd or Config.PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=240
        )
        return {
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'stdout': '',
            'stderr': 'Command timeout',
            'returncode': -1
        }
    except Exception as e:
        return {
            'success': False,
            'stdout': '',
            'stderr': str(e),
            'returncode': -1
        }

def load_env_file(file_path: str) -> Dict[str, str]:
    """Load environment variables from file"""
    env_vars = {}
    try:
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Mask sensitive values
                    if any(sensitive in key.upper() for sensitive in ['KEY', 'TOKEN', 'PASSWORD', 'SECRET']):
                        env_vars[key] = '***REDACTED***'
                    else:
                        env_vars[key] = value
    except Exception as e:
        logger.error(f"Failed to load env file {file_path}: {e}")
    return env_vars

def get_system_status() -> Dict[str, Any]:
    """Get current system status"""
    status = {
        'timestamp': datetime.now().isoformat(),
        'services': {},
        'system': {},
        'health_score': 100
    }

    # Check services
    archon_url = os.environ.get('ARCHON_URL', 'http://localhost:8051/mcp')
    services_to_check = [
        ('archon_mcp', f'curl -sI {archon_url}'),
        ('github_cli', 'gh auth status'),
        ('onepassword_cli', 'op whoami'),
        ('claude_cli', 'claude --version')
    ]

    failed_services = 0
    for service_name, check_cmd in services_to_check:
        result = run_command(check_cmd)
        service_status = {
            'name': service_name,
            'status': 'healthy' if result['success'] else 'unhealthy',
            'last_check': datetime.now().isoformat(),
            'details': result['stderr'] if not result['success'] else 'OK'
        }
        status['services'][service_name] = service_status
        if not result['success']:
            failed_services += 1

    # Get system info
    try:
        # Disk usage
        df_result = run_command('df -h .')
        if df_result['success']:
            status['system']['disk_usage'] = df_result['stdout'].split('\n')[1] if len(df_result['stdout'].split('\n')) > 1 else 'N/A'

        # Load average
        uptime_result = run_command('uptime')
        if uptime_result['success']:
            status['system']['load_average'] = uptime_result['stdout'].strip()

        # Memory usage
        free_result = run_command('free -h')
        if free_result['success']:
            status['system']['memory'] = free_result['stdout'].split('\n')[1] if len(free_result['stdout'].split('\n')) > 1 else 'N/A'

    except Exception as e:
        logger.error(f"Failed to get system info: {e}")

    # Calculate health score
    total_services = len(services_to_check)
    if total_services > 0:
        status['health_score'] = max(0, 100 - (failed_services * 100 // total_services))

    return status

# API Routes
@app.route('/api/status')
def api_status():
    """Get system status"""
    try:
        status = get_system_status()
        dashboard_data['system_status'] = status
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health')
def api_health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

@app.route('/api/environment')
def api_environment():
    """Get environment configuration"""
    try:
        env_file = Config.PROJECT_ROOT / '.env'
        if env_file.exists():
            env_vars = load_env_file(str(env_file))
            return jsonify({
                'success': True,
                'variables': env_vars,
                'file_path': str(env_file),
                'last_modified': datetime.fromtimestamp(env_file.stat().st_mtime).isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Environment file not found',
                'variables': {}
            })
    except Exception as e:
        logger.error(f"Error reading environment: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/environment', methods=['POST'])
def api_update_environment():
    """Update environment variables"""
    try:
        data = request.get_json()
        if not data or 'variables' not in data:
            return jsonify({'error': 'Invalid request data'}), 400

        env_file = Config.PROJECT_ROOT / '.env'
        backup_file = Config.PROJECT_ROOT / f'.env.backup.{int(time.time())}'

        # Backup existing file
        if env_file.exists():
            with open(env_file, 'r') as src, open(backup_file, 'w') as dst:
                dst.write(src.read())

        # Write new environment file
        with open(env_file, 'w') as f:
            f.write("# OOS Environment Configuration\n")
            f.write(f"# Updated: {datetime.now().isoformat()}\n\n")
            for key, value in data['variables'].items():
                if not value.startswith('***'):  # Don't write back redacted values
                    f.write(f"{key}={value}\n")

        return jsonify({
            'success': True,
            'message': 'Environment updated successfully',
            'backup_file': str(backup_file)
        })

    except Exception as e:
        logger.error(f"Error updating environment: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs')
def api_logs():
    """Get system logs"""
    try:
        log_type = request.args.get('type', 'diagnostic')
        limit = int(request.args.get('limit', 100))
        search = request.args.get('search', '')

        log_files = {
            'diagnostic': Config.PROJECT_ROOT / 'diagnostic.log',
            'health': Config.PROJECT_ROOT / 'health_monitor.log',
            'alerts': Config.PROJECT_ROOT / 'health_alerts.log'
        }

        log_file = log_files.get(log_type)
        if not log_file or not log_file.exists():
            return jsonify({
                'success': False,
                'error': f'Log file not found: {log_type}',
                'logs': []
            })

        # Read and filter logs
        logs = []
        with open(log_file, 'r') as f:
            lines = f.readlines()
            for line in reversed(lines[-limit:]):  # Get last N lines
                line = line.strip()
                if not search or search.lower() in line.lower():
                    logs.append({
                        'timestamp': line[:19] if len(line) > 19 else '',
                        'message': line[21:] if len(line) > 21 else line,
                        'level': 'INFO'  # Could parse this from the log format
                    })

        return jsonify({
            'success': True,
            'logs': logs[:limit],
            'total': len(logs),
            'log_file': str(log_file)
        })

    except Exception as e:
        logger.error(f"Error reading logs: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/diagnostics/run', methods=['POST'])
def api_run_diagnostics():
    """Run diagnostic tests"""
    try:
        data = request.get_json() or {}
        test_type = data.get('type', 'quick')
        auto_fix = data.get('auto_fix', False)

        # Build diagnostic command
        cmd = str(Config.PROJECT_ROOT / 'bin' / 'diagnose.sh')
        if test_type == 'full':
            cmd += ' --auto --verbose'
        if auto_fix:
            cmd += ' --fix'

        # Run diagnostics
        result = run_command(cmd)

        return jsonify({
            'success': result['success'],
            'output': result['stdout'],
            'errors': result['stderr'],
            'test_type': test_type,
            'auto_fix': auto_fix
        })

    except Exception as e:
        logger.error(f"Error running diagnostics: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects', methods=['GET', 'POST'])
def api_projects():
    import sqlite3
    conn = sqlite3.connect(Config.DATABASE_URL.replace('sqlite:///', ''))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if request.method == 'POST':
        data = request.get_json()
        new_project = {
            'id': data.get('id'),
            'name': data.get('name'),
            'description': data.get('description'),
            'github_url': data.get('github_url'),
            'created_at': datetime.now().isoformat()
        }
        cursor.execute('INSERT INTO projects (id, name, description, github_url, created_at) VALUES (?, ?, ?, ?, ?)',
                       (new_project['id'], new_project['name'], new_project['description'], new_project['github_url'], new_project['created_at']))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'project': new_project})

    cursor.execute('SELECT * FROM projects')
    projects = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify({'success': True, 'projects': projects})

@app.route('/api/projects/<project_id>', methods=['DELETE'])
def api_delete_project(project_id):
    import sqlite3
    conn = sqlite3.connect(Config.DATABASE_URL.replace('sqlite:///', ''))
    cursor = conn.cursor()
    cursor.execute('DELETE FROM projects WHERE id = ?', (project_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    """User authentication"""
    try:
        data = request.get_json()
        username = data.get('username', '')
        password = data.get('password', '')

        if username in dashboard_data['users']:
            user = dashboard_data['users'][username]
            if check_password_hash(user['password_hash'], password):
                # Generate cryptographically secure session token
                token = secrets.token_urlsafe(32)
                return jsonify({
                    'success': True,
                    'token': token,
                    'user': {
                        'username': username,
                        'role': user['role']
                    }
                })

        return jsonify({
            'success': False,
            'error': 'Invalid credentials'
        }), 401

    except Exception as e:
        logger.error(f"Error during login: {e}")
        return jsonify({'error': str(e)}), 500

# WebSocket events for real-time updates
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info('Client connected')
    emit('connected', {'message': 'Connected to OOS Dashboard'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info('Client disconnected')

@socketio.on('subscribe_status')
def handle_subscribe_status():
    """Subscribe to status updates"""
    def send_status():
        while True:
            try:
                status = get_system_status()
                socketio.emit('status_update', status)
                time.sleep(30)  # Update every 30 seconds
            except Exception as e:
                logger.error(f"Error sending status update: {e}")
                break

    # Start background task
    socketio.start_background_task(send_status)

# Static file serving
@app.route('/')
def dashboard_index():
    """Serve main dashboard"""
    return send_from_directory(Config.PROJECT_ROOT / 'dashboard' / 'static', 'index.html')

@app.route('/<path:filename>')
def dashboard_static(filename):
    """Serve static files"""
    return send_from_directory(Config.PROJECT_ROOT / 'dashboard' / 'static', filename)

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    init_db()
    logger.info(f"Starting OOS Dashboard server on {Config.HOST}:{Config.PORT}")
    logger.info(f"Project root: {Config.PROJECT_ROOT}")
    logger.info(f"Debug mode: {Config.DEBUG}")

    try:
        socketio.run(app,
                    host=Config.HOST,
                    port=Config.PORT,
                    debug=Config.DEBUG,
                    allow_unsafe_werkzeug=True)
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)
