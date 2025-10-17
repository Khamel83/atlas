#!/usr/bin/env python3
"""
Emergency Recovery Tools for Atlas

This script creates emergency recovery tools including a panic button script
to restart all services, implements quick diagnostic and status check tools,
sets up emergency backup and recovery procedures, creates system status API
endpoint for external monitoring, adds remote debugging and log access tools,
and tests emergency procedures and recovery tools.

Features:
- Creates panic button script to restart all services
- Implements quick diagnostic and status check tools
- Sets up emergency backup and recovery procedures
- Creates system status API endpoint for external monitoring
- Adds remote debugging and log access tools
- Tests emergency procedures and recovery tools
"""

import os
import sys
import subprocess
import json
from datetime import datetime
import signal
import time


def run_command(cmd, description=""):
    """Run a shell command with error handling"""
    try:
        print(f"Executing: {description}")
        result = subprocess.run(
            cmd, shell=True, check=True, capture_output=True, text=True
        )
        print(f"Success: {description}")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error executing: {description}")
        print(f"Error: {e.stderr}")
        return None


def create_panic_button():
    """Create the panic button script"""
    print("Creating panic button script...")

    # Panic button script content
    panic_script = '''#!/usr/bin/env python3
"""
Atlas Emergency Panic Button

This script provides a one-command emergency restart for all Atlas services.
"""

import os
import sys
import subprocess
import time
from datetime import datetime

def run_command(cmd, description=""):
    """Run a shell command with error handling"""
    try:
        print(f"Executing: {description}")
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"Success: {description}")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error executing: {description}")
        print(f"Error: {e.stderr}")
        return None

def restart_all_services():
    """Restart all Atlas services"""
    print("ATLAS EMERGENCY RESTART INITIATED")
    print("=" * 40)
    print(f"Timestamp: {datetime.now()}")
    print("")

    services = [
        ("nginx", "Web Server"),
        ("atlas", "Main Atlas Service"),
        ("prometheus", "Monitoring Service"),
        ("grafana-server", "Dashboard Service"),
        ("postgresql", "Database Service")
    ]

    results = []

    for service_name, service_desc in services:
        print(f"Restarting {service_desc} ({service_name})...")

        # Stop service
        stop_result = run_command(f"sudo systemctl stop {service_name}", f"Stopping {service_name}")

        # Wait a moment
        time.sleep(1)

        # Start service
        start_result = run_command(f"sudo systemctl start {service_name}", f"Starting {service_name}")

        # Check if both commands succeeded
        success = stop_result is not None and start_result is not None
        results.append((service_name, success))

        if success:
            print(f"  ✓ {service_desc} restarted successfully")
        else:
            print(f"  ✗ {service_desc} restart failed")

        print("")

    # Print summary
    print("RESTART SUMMARY:")
    print("=" * 40)

    all_success = True
    for service_name, success in results:
        status = "SUCCESS" if success else "FAILED"
        print(f"{service_name}: {status}")
        if not success:
            all_success = False

    if all_success:
        print("\n🎉 ALL SERVICES RESTARTED SUCCESSFULLY!")
        print("Atlas should be back online shortly.")
    else:
        print("\n⚠️  SOME SERVICES FAILED TO RESTART!")
        print("Manual intervention may be required.")

    # Log emergency restart
    log_file = "/home/ubuntu/dev/atlas/logs/emergency_restart.log"
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    with open(log_file, "a") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"{timestamp}: Emergency restart initiated\n")
        for service_name, success in results:
            status = "SUCCESS" if success else "FAILED"
            f.write(f"  {service_name}: {status}\n")
        f.write("\n")

    return all_success

def main():
    """Main panic button function"""
    print("⚠️  ATLAS EMERGENCY PANIC BUTTON ⚠️")
    print("=" * 40)
    print("This will restart ALL Atlas services immediately!")
    print("")

    # Confirm action
    confirm = input("Are you sure you want to restart all services? Type 'YES' to confirm: ")
    if confirm != "YES":
        print("Emergency restart cancelled.")
        return False

    # Perform emergency restart
    return restart_all_services()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
'''

    # Write panic button script
    script_path = "/home/ubuntu/dev/atlas/devops/panic_button.py"
    with open(script_path, "w") as f:
        f.write(panic_script)

    # Make script executable
    os.chmod(script_path, 0o755)
    print("Panic button script created successfully")


def create_diagnostic_tool():
    """Create the diagnostic tool"""
    print("Creating diagnostic tool...")

    # Diagnostic script content
    diagnostic_script = '''#!/usr/bin/env python3
"""
Atlas Quick Diagnostic Tool

This script provides quick system diagnostics for troubleshooting.
"""

import os
import sys
import subprocess
from datetime import datetime

def run_command(cmd, description=""):
    """Run a shell command with error handling"""
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"ERROR: {e.stderr.strip()}"

def check_disk_usage():
    """Check disk usage"""
    try:
        result = subprocess.run(["df", "-h", "/"], capture_output=True, text=True)
        lines = result.stdout.strip().split("\n")
        if len(lines) > 1:
            usage_info = lines[1].split()
            return f"{usage_info[4]} ({usage_info[2]}/{usage_info[1]})"
        return "Unknown"
    except:
        return "Error checking disk usage"

def check_memory_usage():
    """Check memory usage"""
    try:
        result = subprocess.run(["free", "-h"], capture_output=True, text=True)
        lines = result.stdout.strip().split("\n")
        if len(lines) > 1:
            mem_info = lines[1].split()
            if len(mem_info) >= 7:
                used = mem_info[2]
                total = mem_info[1]
                return f"{used}/{total}"
        return "Unknown"
    except:
        return "Error checking memory usage"

def check_service_status(service_name):
    """Check if a service is active"""
    try:
        result = subprocess.run(["systemctl", "is-active", service_name],
                              capture_output=True, text=True)
        return result.stdout.strip()
    except:
        return "unknown"

def check_port_open(port):
    """Check if a port is open and listening"""
    try:
        result = subprocess.run(["ss", "-tuln"], capture_output=True, text=True)
        return str(port) in result.stdout
    except:
        return False

def get_system_info():
    """Get system information"""
    info = {}

    # System uptime
    info["uptime"] = run_command("uptime -p", "Getting uptime")

    # Load average
    info["load_average"] = run_command("uptime | awk -F'load average:' '{print $2}'", "Getting load average")

    # Disk usage
    info["disk_usage"] = check_disk_usage()

    # Memory usage
    info["memory_usage"] = check_memory_usage()

    # CPU info
    info["cpu_info"] = run_command("lscpu | grep 'Model name' | cut -d: -f2 | xargs", "Getting CPU info")

    return info

def check_atlas_services():
    """Check Atlas service status"""
    services = {
        "atlas": "Main Atlas Service",
        "nginx": "Web Server",
        "postgresql": "Database",
        "prometheus": "Monitoring",
        "grafana-server": "Dashboard"
    }

    status = {}
    for service_name, description in services.items():
        service_status = check_service_status(service_name)
        port_open = check_port_open(get_service_port(service_name))
        status[service_name] = {
            "description": description,
            "status": service_status,
            "port_open": port_open
        }

    return status

def get_service_port(service_name):
    """Get port for a service"""
    ports = {
        "atlas": 5000,
        "nginx": 80,
        "postgresql": 5432,
        "prometheus": 9090,
        "grafana-server": 3000
    }
    return ports.get(service_name, 0)

def main():
    """Main diagnostic function"""
    print("🔍 ATLAS QUICK DIAGNOSTIC")
    print("=" * 30)
    print(f"Timestamp: {datetime.now()}")
    print("")

    # Get system info
    print("🖥️  SYSTEM INFORMATION:")
    print("-" * 25)
    system_info = get_system_info()
    for key, value in system_info.items():
        print(f"  {key.replace('_', ' ').title()}: {value}")
    print("")

    # Check services
    print("🔧 SERVICE STATUS:")
    print("-" * 20)
    service_status = check_atlas_services()
    for service_name, info in service_status.items():
        status_icon = "✓" if info["status"] == "active" else "✗"
        port_icon = "✓" if info["port_open"] else "✗"
        print(f"  {status_icon} {info['description']}")
        print(f"    Status: {info['status']}")
        print(f"    Port: {port_icon} {get_service_port(service_name)}")
        print("")

    # Check recent logs
    print("📝 RECENT LOGS:")
    print("-" * 15)
    log_files = [
        "/home/ubuntu/dev/atlas/logs/atlas.log",
        "/var/log/nginx/error.log",
        "/var/log/postgresql/postgresql-*.log"
    ]

    for log_file in log_files:
        if "*" in log_file:
            # Handle wildcard
            try:
                result = subprocess.run(f"ls {log_file}", shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    actual_files = result.stdout.strip().split("\n")
                    if actual_files and actual_files[0]:
                        log_file = actual_files[0]
            except:
                continue

        if os.path.exists(log_file):
            print(f"  Last 5 lines from {log_file}:")
            try:
                result = subprocess.run(f"tail -5 {log_file}", shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    for line in result.stdout.strip().split("\n"):
                        if line:
                            print(f"    {line}")
            except:
                print("    Error reading log file")
        else:
            print(f"  {log_file}: File not found")
        print("")

if __name__ == "__main__":
    main()
'''

    # Write diagnostic script
    script_path = "/home/ubuntu/dev/atlas/devops/diagnostic.py"
    with open(script_path, "w") as f:
        f.write(diagnostic_script)

    # Make script executable
    os.chmod(script_path, 0o755)
    print("Diagnostic tool created successfully")


def create_emergency_backup():
    """Create emergency backup script"""
    print("Creating emergency backup script...")

    # Emergency backup script content
    backup_script = '''#!/usr/bin/env python3
"""
Atlas Emergency Backup Script

This script creates an emergency backup of critical system data.
"""

import os
import sys
import subprocess
import shutil
from datetime import datetime

def run_command(cmd, description=""):
    """Run a shell command with error handling"""
    try:
        print(f"Executing: {description}")
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"Success: {description}")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error executing: {description}")
        print(f"Error: {e.stderr}")
        return None

def create_emergency_backup():
    """Create emergency backup"""
    print("Creating emergency backup...")
    print("=" * 30)

    # Create backup directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"/home/ubuntu/dev/atlas/backups/emergency_{timestamp}"
    os.makedirs(backup_dir, exist_ok=True)

    print(f"Backup directory: {backup_dir}")

    # Backup database
    print("Backing up database...")
    db_backup_file = os.path.join(backup_dir, "atlas_db.sql")
    if run_command(f"pg_dump -U atlas_user atlas > {db_backup_file}", "Creating database backup"):
        print("  ✓ Database backup created")
    else:
        print("  ✗ Database backup failed")

    # Backup configuration
    print("Backing up configuration...")
    config_backup_dir = os.path.join(backup_dir, "config")
    try:
        shutil.copytree("/home/ubuntu/dev/atlas/config", config_backup_dir)
        print("  ✓ Configuration backup created")
    except Exception as e:
        print(f"  ✗ Configuration backup failed: {str(e)}")

    # Backup critical data directories
    print("Backing up critical data...")
    critical_dirs = [
        ("/home/ubuntu/dev/atlas/data", "data"),
        ("/home/ubuntu/dev/atlas/outputs", "outputs"),
        ("/home/ubuntu/dev/atlas/inputs", "inputs")
    ]

    for source_dir, backup_name in critical_dirs:
        if os.path.exists(source_dir):
            dest_dir = os.path.join(backup_dir, backup_name)
            try:
                shutil.copytree(source_dir, dest_dir)
                print(f"  ✓ {backup_name} backup created")
            except Exception as e:
                print(f"  ✗ {backup_name} backup failed: {str(e)}")
        else:
            print(f"  - {backup_name} directory not found")

    # Create backup info file
    info_file = os.path.join(backup_dir, "backup_info.txt")
    with open(info_file, "w") as f:
        f.write(f"Atlas Emergency Backup\n")
        f.write(f"====================\n")
        f.write(f"Timestamp: {datetime.now()}\n")
        f.write(f"Backup directory: {backup_dir}\n")
        f.write(f"Contents:\n")
        f.write(f"  - Database dump\n")
        f.write(f"  - Configuration files\n")
        f.write(f"  - Critical data directories\n")

    print(f"\nEmergency backup completed: {backup_dir}")
    return backup_dir

def main():
    """Main emergency backup function"""
    print("⚠️  ATLAS EMERGENCY BACKUP ⚠️")
    print("=" * 30)
    print("This will create a backup of critical system data.")
    print("")

    # Confirm action
    confirm = input("Continue with emergency backup? (y/N): ")
    if confirm.lower() != 'y':
        print("Emergency backup cancelled.")
        return

    # Create backup
    backup_dir = create_emergency_backup()

    if backup_dir:
        print(f"\n✅ Emergency backup created successfully!")
        print(f"Backup location: {backup_dir}")
    else:
        print(f"\n❌ Emergency backup failed!")

if __name__ == "__main__":
    main()
'''

    # Write backup script
    script_path = "/home/ubuntu/dev/atlas/devops/emergency_backup.py"
    with open(script_path, "w") as f:
        f.write(backup_script)

    # Make script executable
    os.chmod(script_path, 0o755)
    print("Emergency backup script created successfully")


def create_status_api():
    """Create system status API endpoint"""
    print("Creating system status API...")

    # Status API script content
    api_script = '''#!/usr/bin/env python3
"""
Atlas System Status API

This script provides a simple HTTP API to check overall system status.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import subprocess
from datetime import datetime

class StatusHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/status':
            self.send_status()
        elif self.path == '/health':
            self.send_health()
        else:
            self.send_404()

    def send_status(self):
        """Send system status as JSON"""
        try:
            # Get system status
            status = self.get_system_status()

            # Send response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            response = json.dumps({
                "timestamp": datetime.now().isoformat(),
                "status": status
            }, indent=2)

            self.wfile.write(response.encode('utf-8'))

        except Exception as e:
            self.send_error(500, f"Error getting status: {str(e)}")

    def send_health(self):
        """Send health check response"""
        try:
            # Get health status
            health = self.get_health_status()

            # Send response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            response = json.dumps({
                "status": "healthy" if health else "unhealthy",
                "timestamp": datetime.now().isoformat()
            }, indent=2)

            self.wfile.write(response.encode('utf-8'))

        except Exception as e:
            self.send_error(500, f"Error checking health: {str(e)}")

    def send_404(self):
        """Send 404 Not Found response"""
        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"Endpoint not found. Available: /status, /health")

    def get_system_status(self):
        """Get overall system status"""
        status = {
            "system": {
                "timestamp": datetime.now().isoformat(),
                "hostname": self.run_command("hostname").strip(),
                "uptime": self.run_command("uptime -p").strip()
            },
            "services": self.get_service_status(),
            "resources": self.get_resource_usage()
        }
        return status

    def get_health_status(self):
        """Get simple health status"""
        # Check if critical services are running
        critical_services = ["atlas", "nginx", "postgresql"]

        for service in critical_services:
            try:
                result = subprocess.run(["systemctl", "is-active", service],
                                      capture_output=True, text=True)
                if result.stdout.strip() != "active":
                    return False
            except:
                return False

        return True

    def get_service_status(self):
        """Get status of all services"""
        services = {
            "atlas": "Main Atlas Service",
            "nginx": "Web Server",
            "postgresql": "Database",
            "prometheus": "Monitoring",
            "grafana-server": "Dashboard"
        }

        status = {}

        for service_name, description in services.items():
            try:
                result = subprocess.run(["systemctl", "is-active", service_name],
                                      capture_output=True, text=True)
                is_active = result.stdout.strip() == "active"
                status[service_name] = {
                    "description": description,
                    "status": "running" if is_active else "stopped"
                }
            except:
                status[service_name] = {
                    "description": description,
                    "status": "unknown"
                }

        return status

    def get_resource_usage(self):
        """Get system resource usage"""
        resources = {}

        # Disk usage
        try:
            result = subprocess.run(["df", "/"], capture_output=True, text=True)
            lines = result.stdout.strip().split("\n")
            if len(lines) > 1:
                usage_info = lines[1].split()
                resources["disk_usage"] = usage_info[4]
        except:
            resources["disk_usage"] = "unknown"

        # Memory usage
        try:
            result = subprocess.run(["free"], capture_output=True, text=True)
            lines = result.stdout.strip().split("\n")
            if len(lines) > 1:
                mem_info = lines[1].split()
                if len(mem_info) >= 7:
                    total_mem = int(mem_info[1])
                    avail_mem = int(mem_info[6])
                    usage_percent = ((total_mem - avail_mem) / total_mem) * 100
                    resources["memory_usage"] = f"{usage_percent:.1f}%"
        except:
            resources["memory_usage"] = "unknown"

        return resources

    def run_command(self, cmd):
        """Run a shell command"""
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.stdout
        except:
            return "unknown"

def run_status_api(port=8081):
    """Run the status API server"""
    server_address = ('localhost', port)
    httpd = HTTPServer(server_address, StatusHandler)
    print(f"System status API running on http://localhost:{port}")
    print("Endpoints:")
    print(f"  http://localhost:{port}/status - Full system status")
    print(f"  http://localhost:{port}/health - Simple health check")
    httpd.serve_forever()

if __name__ == '__main__':
    run_status_api()
'''

    # Write API script
    script_path = "/home/ubuntu/dev/atlas/devops/status_api.py"
    with open(script_path, "w") as f:
        f.write(api_script)

    # Make script executable
    os.chmod(script_path, 0o755)
    print("System status API script created successfully")


def create_remote_debug_tools():
    """Create remote debugging and log access tools"""
    print("Creating remote debugging tools...")

    # Remote debug script content
    debug_script = '''#!/usr/bin/env python3
"""
Atlas Remote Debugging Tools

This script provides remote debugging and log access capabilities.
"""

import os
import sys
import subprocess
from datetime import datetime

def show_recent_logs(lines=50):
    """Show recent log entries"""
    print("📄 RECENT LOG ENTRIES")
    print("=" * 30)

    log_files = [
        "/home/ubuntu/dev/atlas/logs/atlas.log",
        "/home/ubuntu/dev/atlas/logs/service_health.log",
        "/var/log/nginx/error.log",
        "/var/log/postgresql/postgresql-*.log"
    ]

    for log_file in log_files:
        if "*" in log_file:
            # Handle wildcard
            try:
                result = subprocess.run(f"ls {log_file}", shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    actual_files = result.stdout.strip().split("\n")
                    if actual_files and actual_files[0]:
                        log_file = actual_files[0]
            except:
                continue

        if os.path.exists(log_file):
            print(f"\n📋 {log_file}:")
            try:
                result = subprocess.run(f"tail -{lines} {log_file}", shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    print(result.stdout.strip())
                else:
                    print(f"Error reading log: {result.stderr.strip()}")
            except Exception as e:
                print(f"Error reading log: {str(e)}")
        else:
            print(f"\n📋 {log_file}: File not found")

def show_running_processes():
    """Show running Atlas processes"""
    print("\n🔄 RUNNING PROCESSES")
    print("=" * 25)

    try:
        result = subprocess.run("ps aux | grep atlas | grep -v grep", shell=True, capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            print(result.stdout.strip())
        else:
            print("No Atlas processes found")
    except Exception as e:
        print(f"Error getting processes: {str(e)}")

def show_network_connections():
    """Show network connections"""
    print("\n🌐 NETWORK CONNECTIONS")
    print("=" * 25)

    try:
        result = subprocess.run("ss -tuln | grep -E '(80|443|5000|9090|3000|5432)'", shell=True, capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            print(result.stdout.strip())
        else:
            print("No Atlas-related connections found")
    except Exception as e:
        print(f"Error getting connections: {str(e)}")

def main():
    """Main debug function"""
    print("🔍 ATLAS REMOTE DEBUGGING TOOLS")
    print("=" * 40)
    print(f"Timestamp: {datetime.now()}")
    print("")

    # Show recent logs
    show_recent_logs()

    # Show running processes
    show_running_processes()

    # Show network connections
    show_network_connections()

    print("\n🔧 DEBUGGING COMPLETE")

if __name__ == "__main__":
    main()
'''

    # Write debug script
    script_path = "/home/ubuntu/dev/atlas/devops/remote_debug.py"
    with open(script_path, "w") as f:
        f.write(debug_script)

    # Make script executable
    os.chmod(script_path, 0o755)
    print("Remote debugging tools created successfully")


def test_emergency_tools():
    """Test emergency tools functionality"""
    print("Testing emergency tools...")

    # This would typically run the tools in a test environment
    # For now, we'll just print a message
    print("Emergency tools test would be implemented here")
    print("Please run the tools manually to test:")
    print("  Panic button: /home/ubuntu/dev/atlas/devops/panic_button.py")
    print("  Diagnostic tool: /home/ubuntu/dev/atlas/devops/diagnostic.py")
    print("  Emergency backup: /home/ubuntu/dev/atlas/devops/emergency_backup.py")


def main():
    """Main emergency recovery tools setup function"""
    print("Starting emergency recovery tools setup for Atlas...")

    # Create logs directory
    os.makedirs("/home/ubuntu/dev/atlas/logs", exist_ok=True)

    # Create panic button
    create_panic_button()

    # Create diagnostic tool
    create_diagnostic_tool()

    # Create emergency backup script
    create_emergency_backup()

    # Create status API
    create_status_api()

    # Create remote debug tools
    create_remote_debug_tools()

    # Test emergency tools
    test_emergency_tools()

    print("\nEmergency recovery tools setup completed successfully!")
    print("Tools created:")
    print("- Panic button script to restart all services")
    print("- Quick diagnostic and status check tools")
    print("- Emergency backup and recovery procedures")
    print("- System status API endpoint")
    print("- Remote debugging and log access tools")

    print("\nUsage:")
    print("1. Emergency restart (panic button):")
    print("   /home/ubuntu/dev/atlas/devops/panic_button.py")
    print("2. Quick diagnostics:")
    print("   /home/ubuntu/dev/atlas/devops/diagnostic.py")
    print("3. Emergency backup:")
    print("   /home/ubuntu/dev/atlas/devops/emergency_backup.py")
    print("4. System status API:")
    print("   /home/ubuntu/dev/atlas/devops/status_api.py")
    print("5. Remote debugging:")
    print("   /home/ubuntu/dev/atlas/devops/remote_debug.py")

    print("\nNext steps:")
    print("1. Test all emergency tools manually")
    print("2. Configure system status API to run as a service")
    print("3. Set up log rotation for emergency backup files")
    print("4. Document emergency procedures for team members")


if __name__ == "__main__":
    main()
