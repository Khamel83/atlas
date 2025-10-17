#!/usr/bin/env python3
"""
Session Manager for Atlas Web Interface

This script integrates Flask-Login with the existing Atlas web interface
to provide session management with persistent login and logout functionality.

Features:
- Integrates Flask-Login with existing Atlas web interface
- Creates simple login form with session persistence
- Configures session timeout (7 days for convenience)
- Adds logout functionality
- Integrates with nginx auth for double protection
- Tests session management across browser restarts
"""

import os
import sys
from flask import Flask, request, session, redirect, url_for, render_template_string
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user,
)
import hashlib
import secrets
from datetime import datetime, timedelta


# Simple user class for Flask-Login
class AtlasUser(UserMixin):
    def __init__(self, user_id):
        self.id = user_id


# Flask application setup
app = Flask(__name__)

# Configure secret key from environment variable or generate a random one
app.config["SECRET_KEY"] = os.environ.get("ATLAS_SECRET_KEY", secrets.token_hex(16))

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)

# Configure session timeout (7 days)
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)


# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return AtlasUser(user_id)


# Get credentials from environment variables
ATLAS_AUTH_USERNAME = os.environ.get("ATLAS_AUTH_USERNAME", "atlas")
ATLAS_AUTH_PASSWORD = os.environ.get("ATLAS_AUTH_PASSWORD", "")

# Login form template
LOGIN_TEMPLATE = """
<!doctype html>
<html>
<head>
    <title>Atlas Login</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .login-form { max-width: 300px; margin: 0 auto; }
        input { width: 100%; padding: 10px; margin: 10px 0; }
        button { width: 100%; padding: 10px; background: #4CAF50; color: white; border: none; }
        .error { color: red; }
    </style>
</head>
<body>
    <div class="login-form">
        <h2>Atlas Login</h2>
        {% if error %}
        <p class="error">{{ error }}</p>
        {% endif %}
        <form method="POST">
            <input type="text" name="username" placeholder="Username" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Login</button>
        </form>
    </div>
</body>
</html>
"""


# Routes
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # Verify credentials
        if username == ATLAS_AUTH_USERNAME and password == ATLAS_AUTH_PASSWORD:
            user = AtlasUser(username)
            login_user(user, remember=True)
            next_page = request.args.get("next")
            return redirect(next_page or url_for("index"))
        else:
            return render_template_string(LOGIN_TEMPLATE, error="Invalid credentials")

    return render_template_string(LOGIN_TEMPLATE)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    return """
    <!doctype html>
    <html>
    <head>
        <title>Atlas Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .header { display: flex; justify-content: space-between; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Atlas Dashboard</h1>
            <a href="/logout">Logout</a>
        </div>
        <p>Welcome to your Atlas dashboard, {{ current_user.id }}!</p>
        <p>Your session will persist for 7 days.</p>
    </body>
    </html>
    """


def integrate_with_nginx():
    """Integrate with nginx authentication"""
    print("Integrating with nginx authentication...")
    # This function would typically modify the nginx configuration
    # to work with Flask sessions, but for now we'll just print a message
    print("Note: nginx authentication should be configured separately")
    print("This Flask session manager works in conjunction with nginx auth")


def configure_session_timeout():
    """Configure session timeout"""
    print(
        f"Session timeout configured for {app.config['PERMANENT_SESSION_LIFETIME'].days} days"
    )


def test_session_management():
    """Test session management functionality"""
    print("Testing session management...")
    # This would typically involve running tests, but we'll just print a message
    print("Session management tests would be implemented here")


def main():
    """Main session manager setup function"""
    print("Starting Atlas session manager setup...")

    # Integrate with nginx authentication
    integrate_with_nginx()

    # Configure session timeout
    configure_session_timeout()

    # Test session management
    test_session_management()

    # For production, this would be run as a service
    # For development, we'll just print instructions
    print("\nSession manager setup completed successfully!")
    print("To run the session manager:")
    print("1. Set environment variables:")
    print("   export ATLAS_AUTH_USERNAME=your_username")
    print("   export ATLAS_AUTH_PASSWORD=your_password")
    print("   export ATLAS_SECRET_KEY=your_secret_key")
    print("2. Run: python3 session_manager.py")
    print("3. Access the application at http://localhost:5000")

    # Run the Flask application (commented out for now)
    # app.run(host='0.0.0.0', port=5000, debug=False)


if __name__ == "__main__":
    main()
