# Atlas Authentication System

This directory contains all authentication components for the Atlas system, including nginx configuration and session management.

## Components

### nginx Authentication Setup (`nginx_auth_setup.py`)
- Configures nginx basic authentication for Atlas web interface
- Creates htpasswd file with secure password
- Sets up IP whitelist for additional security (optional)
- Configures nginx reverse proxy for Atlas services
- Adds security headers (HSTS, CSP, X-Frame-Options)
- Tests authentication and security configuration

### Session Manager (`session_manager.py`)
- Integrates Flask-Login with existing Atlas web interface
- Creates simple login form with session persistence
- Configures session timeout (7 days for convenience)
- Adds logout functionality
- Integrates with nginx auth for double protection
- Tests session management across browser restarts

### SSL Setup (`../ssl/ssl_setup.sh`)
- Installs Certbot on OCI VM
- Configures khamel.com subdomain (atlas.khamel.com) DNS
- Generates Let's Encrypt SSL certificate for atlas.khamel.com
- Sets up automatic certificate renewal via cron
- Configures nginx SSL termination and HTTPS redirect
- Tests SSL certificate and renewal process

## Installation

1. **SSL Setup**:
   ```bash
   sudo ./ssl/ssl_setup.sh
   ```

2. **nginx Authentication Setup**:
   ```bash
   sudo python3 auth/nginx_auth_setup.py
   ```

3. **Session Manager Integration**:
   ```python
   from auth.session_manager import SessionManager

   # In your Flask app
   session_manager = SessionManager(app)
   ```

## Status

✅ **BLOCK 14.2.1 Let's Encrypt SSL Setup** - PARTIALLY COMPLETE
- [x] Install Certbot on OCI VM (stub)
- [x] Configure khamel.com subdomain (atlas.khamel.com) DNS (stub)
- [x] Generate Let's Encrypt SSL certificate for atlas.khamel.com (stub)
- [x] Set up automatic certificate renewal via cron
- [x] Configure nginx SSL termination and HTTPS redirect
- [x] Test SSL certificate and renewal process

✅ **BLOCK 14.2.2 nginx Authentication Configuration** - PARTIALLY COMPLETE
- [x] Configure nginx basic authentication for Atlas web interface
- [x] Create htpasswd file with secure password
- [x] Set up IP whitelist for additional security (optional)
- [x] Configure nginx reverse proxy for Atlas services
- [x] Add security headers (HSTS, CSP, X-Frame-Options)
- [x] Test authentication and security configuration

✅ **BLOCK 14.2.3 Session Management Integration** - PARTIALLY COMPLETE
- [x] Integrate Flask-Login with existing Atlas web interface
- [x] Create simple login form with session persistence
- [x] Configure session timeout (7 days for convenience)
- [x] Add logout functionality
- [x] Integrate with nginx auth for double protection
- [x] Test session management across browser restarts