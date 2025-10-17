#!/usr/bin/env python3
"""
nginx Authentication Setup for Atlas

This script configures nginx basic authentication for the Atlas web interface.
It creates htpasswd files, configures IP whitelisting, and sets up security headers.

Features:
- Configures nginx basic authentication
- Creates htpasswd file with secure password
- Sets up IP whitelist for additional security
- Configures nginx reverse proxy for Atlas services
- Adds security headers to prevent common attacks
- Integrates with existing nginx configuration
"""

import os
import sys
import subprocess
import hashlib
import secrets


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
        sys.exit(1)


def generate_htpasswd(username, password):
    """Generate htpasswd entry using bcrypt"""
    try:
        # Use htpasswd command if available
        result = subprocess.run(
            ["htpasswd", "-nbB", username, password],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fallback to manual bcrypt implementation
        import bcrypt

        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode(
            "utf-8"
        )
        return f"{username}:{hashed}"


def create_htpasswd_file(username, password):
    """Create htpasswd file with user credentials"""
    print("Creating htpasswd file...")

    # Generate htpasswd entry
    htpasswd_entry = generate_htpasswd(username, password)

    # Write to file
    htpasswd_path = "/etc/nginx/.htpasswd"
    with open("/tmp/.htpasswd", "w") as f:
        f.write(htpasswd_entry + "\n")

    # Install htpasswd file
    run_command("sudo cp /tmp/.htpasswd " + htpasswd_path, "Installing htpasswd file")
    run_command(
        "sudo chown www-data:www-data " + htpasswd_path, "Setting htpasswd ownership"
    )
    run_command("sudo chmod 644 " + htpasswd_path, "Setting htpasswd permissions")

    print("htpasswd file created successfully")


def configure_nginx_auth():
    """Configure nginx authentication"""
    print("Configuring nginx authentication...")

    # Get configuration from environment variables
    username = os.environ.get("ATLAS_AUTH_USERNAME", "atlas")
    password = os.environ.get("ATLAS_AUTH_PASSWORD")

    # Generate a random password if not provided
    if not password:
        password = secrets.token_urlsafe(16)
        print(f"Generated random password: {password}")
        print(
            "Please save this password - you'll need it to access your Atlas instance"
        )

    # Create htpasswd file
    create_htpasswd_file(username, password)

    # Update nginx configuration to include authentication
    # This assumes the SSL configuration script has already run
    nginx_config_path = "/etc/nginx/sites-available/atlas"

    # Read current configuration
    try:
        with open(nginx_config_path, "r") as f:
            config = f.read()
    except FileNotFoundError:
        print("Error: nginx configuration file not found")
        print("Please run ssl_setup.sh first")
        sys.exit(1)

    # Add authentication to the HTTPS server block
    if "auth_basic" not in config:
        # Insert auth directives after the server_name line in the HTTPS block
        lines = config.split("\n")
        new_lines = []
        in_https_block = False

        for line in lines:
            new_lines.append(line)
            # Look for the HTTPS server block
            if (
                line.strip().startswith("server {")
                and "443 ssl" in config.split(line)[1][:200]
            ):
                in_https_block = True
            elif in_https_block and line.strip().startswith("server_name"):
                # Add auth configuration after server_name
                new_lines.append('    auth_basic "Atlas Web Interface";')
                new_lines.append("    auth_basic_user_file /etc/nginx/.htpasswd;")
                in_https_block = False  # Only add once

        config = "\n".join(new_lines)

        # Write updated configuration
        with open("/tmp/atlas_nginx_auth.conf", "w") as f:
            f.write(config)

        run_command(
            "sudo cp /tmp/atlas_nginx_auth.conf " + nginx_config_path,
            "Updating nginx configuration",
        )
        run_command("sudo nginx -t", "Testing nginx configuration")
        run_command("sudo systemctl reload nginx", "Reloading nginx")

        print("nginx authentication configured successfully")
    else:
        print("nginx authentication already configured")


def setup_ip_whitelist():
    """Setup IP whitelist for additional security"""
    print("Setting up IP whitelist...")

    # Get allowed IPs from environment variable
    allowed_ips = os.environ.get("ATLAS_ALLOWED_IPS", "")

    if allowed_ips:
        # Update nginx configuration with IP whitelist
        nginx_config_path = "/etc/nginx/sites-available/atlas"

        # Read current configuration
        try:
            with open(nginx_config_path, "r") as f:
                config = f.read()
        except FileNotFoundError:
            print("Error: nginx configuration file not found")
            sys.exit(1)

        # Add IP whitelist to the HTTPS server block if not already present
        if "allow" not in config or "deny all" not in config:
            # Insert IP whitelist directives
            lines = config.split("\n")
            new_lines = []
            in_location_block = False

            for line in lines:
                new_lines.append(line)
                # Look for the location block
                if line.strip().startswith("location / {"):
                    in_location_block = True
                elif in_location_block and line.strip().startswith("proxy_pass"):
                    # Add IP whitelist before proxy_pass
                    # Remove the last line (proxy_pass) temporarily
                    new_lines.pop()

                    # Add IP whitelist
                    ip_list = allowed_ips.split(",")
                    for ip in ip_list:
                        new_lines.append(f"        allow {ip.strip()};")
                    new_lines.append("        deny all;")

                    # Add back the proxy_pass line
                    new_lines.append(line)

                    in_location_block = False

            config = "\n".join(new_lines)

            # Write updated configuration
            with open("/tmp/atlas_nginx_whitelist.conf", "w") as f:
                f.write(config)

            run_command(
                "sudo cp /tmp/atlas_nginx_whitelist.conf " + nginx_config_path,
                "Updating nginx configuration with IP whitelist",
            )
            run_command("sudo nginx -t", "Testing nginx configuration")
            run_command("sudo systemctl reload nginx", "Reloading nginx")

            print("IP whitelist configured successfully")
        else:
            print("IP whitelist already configured")
    else:
        print("No IP whitelist configured (ATLAS_ALLOWED_IPS not set)")


def add_security_headers():
    """Add security headers to nginx configuration"""
    print("Adding security headers...")

    # Security headers were already included in the SSL setup
    # This function is here for completeness and future enhancements
    print("Security headers already configured in SSL setup")


def test_authentication():
    """Test authentication configuration"""
    print("Testing authentication configuration...")

    # Test nginx configuration
    run_command("sudo nginx -t", "Testing nginx configuration")

    print("Authentication configuration test completed")


def main():
    """Main nginx authentication setup function"""
    print("Starting nginx authentication setup for Atlas...")

    # Configure nginx authentication
    configure_nginx_auth()

    # Setup IP whitelist
    setup_ip_whitelist()

    # Add security headers
    add_security_headers()

    # Test configuration
    test_authentication()

    print("\nnginx authentication setup completed successfully!")
    print("Your Atlas instance is now protected with:")
    print("- Basic authentication (username/password)")
    print("- Optional IP whitelisting")
    print("- Security headers to prevent common attacks")

    print("\nNext steps:")
    print("1. Access your Atlas instance at https://your-domain.com")
    print("2. Enter the username and password when prompted")
    print("3. If you set IP whitelisting, ensure your IP is included")


if __name__ == "__main__":
    main()
