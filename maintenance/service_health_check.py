#!/usr/bin/env python3
"""
Atlas Service Health Check Script

This script performs comprehensive health checks on all Atlas services.
"""

import os
import sys
import subprocess
import time
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime


def run_command(cmd, description=""):
    """Run a shell command with error handling"""
    try:
        result = subprocess.run(
            cmd, shell=True, check=True, capture_output=True, text=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return None


def check_service_status(service_name):
    """Check if a service is active"""
    try:
        result = subprocess.run(
            ["systemctl", "is-active", service_name], capture_output=True, text=True
        )
        return result.stdout.strip() == "active"
    except:
        return False


def check_process_running(process_name):
    """Check if a process is running"""
    try:
        result = subprocess.run(
            ["pgrep", "-f", process_name], capture_output=True, text=True
        )
        return result.returncode == 0
    except:
        return False


def check_port_open(port):
    """Check if a port is open and listening"""
    try:
        result = subprocess.run(["ss", "-tuln"], capture_output=True, text=True)
        return f":{port} " in result.stdout
    except:
        return False


def check_disk_space():
    """Check disk space usage"""
    try:
        result = subprocess.run(["df", "/"], capture_output=True, text=True)
        lines = result.stdout.strip().split("\n")
        if len(lines) > 1:
            usage_info = lines[1].split()
            usage_percent = int(usage_info[4].rstrip("%"))
            return usage_percent < 90  # Healthy if less than 90%
        return False
    except:
        return False


def check_memory_usage():
    """Check memory usage"""
    try:
        result = subprocess.run(["free"], capture_output=True, text=True)
        lines = result.stdout.strip().split("\n")
        if len(lines) > 1:
            mem_info = lines[1].split()
            if len(mem_info) >= 7:
                total_mem = int(mem_info[1])
                avail_mem = int(mem_info[6])
                usage_percent = ((total_mem - avail_mem) / total_mem) * 100
                return usage_percent < 90  # Healthy if less than 90%
        return False
    except:
        return False


def send_email_alert(service_name, status):
    """Send email alert for service status change"""
    # Get email configuration from environment variables
    smtp_server = os.environ.get("EMAIL_SMTP_SERVER", "smtp.gmail.com")
    port = int(os.environ.get("EMAIL_SMTP_PORT", 587))
    sender_email = os.environ.get("EMAIL_SENDER")
    sender_password = os.environ.get("EMAIL_PASSWORD")
    recipient_email = os.environ.get("EMAIL_RECIPIENT")

    # Validate required environment variables
    if not all([sender_email, sender_password, recipient_email]):
        print("Email configuration not complete, skipping email alert")
        return False

    try:
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Atlas Service Alert: {service_name}"
        msg["From"] = sender_email
        msg["To"] = recipient_email

        # Create text part
        text = f"""
Atlas Service Alert

Service: {service_name}
Status: {status}
Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

This is an automated message from your Atlas monitoring system.
"""

        text_part = MIMEText(text, "plain")
        msg.attach(text_part)

        # Send email
        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_server, port) as server:
            server.starttls(context=context)
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())

        print(f"Email alert sent for service {service_name}")
        return True
    except Exception as e:
        print(f"Error sending email alert: {str(e)}")
        return False


def log_service_status(service_name, status):
    """Log service status to file"""
    log_file = "/home/ubuntu/dev/atlas/logs/service_health.log"

    # Create log directory if it doesn't exist
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    with open(log_file, "a") as f:
        f.write(f"{datetime.now()}: {service_name} - {status}\n")


def check_atlas_services():
    """Check all Atlas services"""
    print("Checking Atlas services...")

    # Define services to check
    services = {
        "atlas": {"type": "systemd", "port": 5000, "description": "Main Atlas service"},
        "prometheus": {
            "type": "systemd",
            "port": 9090,
            "description": "Prometheus monitoring",
        },
        "grafana-server": {
            "type": "systemd",
            "port": 3000,
            "description": "Grafana dashboard",
        },
        "nginx": {"type": "systemd", "port": 80, "description": "Web server"},
    }

    results = {}

    for service_name, service_info in services.items():
        print(f"\nChecking {service_name}...")

        # Check service status
        if service_info["type"] == "systemd":
            is_active = check_service_status(service_name)
        else:
            is_active = check_process_running(service_name)

        # Check port if specified
        port_open = True
        if "port" in service_info:
            port_open = check_port_open(service_info["port"])

        # Determine overall status
        status = "healthy" if is_active and port_open else "unhealthy"

        # Log status
        log_service_status(service_name, status)

        # Store result
        results[service_name] = {
            "status": status,
            "active": is_active,
            "port_open": port_open,
            "description": service_info["description"],
        }

        print(f"  Status: {status}")
        print(f"  Active: {is_active}")
        print(f"  Port {service_info.get('port', 'N/A')} open: {port_open}")

    return results


def check_system_health():
    """Check overall system health"""
    print("\nChecking system health...")

    # Check disk space
    disk_healthy = check_disk_space()
    print(f"  Disk space healthy: {disk_healthy}")

    # Check memory usage
    memory_healthy = check_memory_usage()
    print(f"  Memory usage healthy: {memory_healthy}")

    return {"disk_space": disk_healthy, "memory_usage": memory_healthy}


def restart_service(service_name):
    """Restart a service"""
    print(f"Restarting service: {service_name}")

    try:
        subprocess.run(
            ["sudo", "systemctl", "restart", service_name],
            check=True,
            capture_output=True,
        )
        print(f"Service {service_name} restarted successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error restarting service {service_name}: {e}")
        return False


def main():
    """Main health check function"""
    print("Starting Atlas service health check...")
    print("=" * 50)

    # Check Atlas services
    service_results = check_atlas_services()

    # Check system health
    system_results = check_system_health()

    # Check for unhealthy services
    unhealthy_services = []
    for service_name, result in service_results.items():
        if result["status"] == "unhealthy":
            unhealthy_services.append(service_name)

    # Handle unhealthy services
    if unhealthy_services:
        print("\n" + "=" * 50)
        print("UNHEALTHY SERVICES DETECTED:")
        print("=" * 50)

        for service_name in unhealthy_services:
            result = service_results[service_name]
            print(f"\n{service_name}:")
            print(f"  Description: {result['description']}")
            print(f"  Active: {result['active']}")
            print(f"  Port open: {result['port_open']}")

            # Attempt to restart service
            print(f"  Attempting to restart {service_name}...")
            if restart_service(service_name):
                # Send email alert
                send_email_alert(service_name, "RESTARTED")
            else:
                # Send email alert
                send_email_alert(service_name, "FAILED TO RESTART")
    else:
        print("\nAll services are healthy!")

    # Print system health
    print("\n" + "=" * 50)
    print("SYSTEM HEALTH:")
    print("=" * 50)
    print(f"  Disk space: {'Healthy' if system_results['disk_space'] else 'Unhealthy'}")
    print(
        f"  Memory usage: {'Healthy' if system_results['memory_usage'] else 'Unhealthy'}"
    )

    # Log overall health check
    overall_status = "healthy" if not unhealthy_services else "unhealthy"
    log_service_status("SYSTEM", overall_status)

    print("\nHealth check completed.")
    return len(unhealthy_services) == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
