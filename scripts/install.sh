#!/bin/bash
# OOS One-Line Installer
set -e

echo "🚀 Installing OOS (Organized Operational Setup)..."

# Detect OS
OS="$(uname -s)"
case "${OS}" in
    Linux*)     MACHINE=Linux;;
    Darwin*)    MACHINE=Mac;;
    *)          MACHINE="UNKNOWN:${OS}"
esac

echo "📍 Detected: $MACHINE"

# Check core requirements
echo "🔍 Checking and installing dependencies..."

# Function to run commands with sudo, prompting if needed
run_sudo() {
    if command -v sudo &> /dev/null; then
        sudo "$@"
    else
        echo "⚠️ sudo not found. Please run the following command manually:"
        echo "    $@"
        exit 1
    fi
}

# Function to install packages
install_packages() {
    local packages=("$@")
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        ID_LIKE=${ID_LIKE:-$ID}
        if [[ "$ID_LIKE" == *"debian"* ]]; then
            echo "📦 Detected Debian-based OS. Using apt-get."
            run_sudo apt-get update -y
            run_sudo apt-get install -y "${packages[@]}"
        elif [[ "$ID_LIKE" == *"rhel"* ]] || [[ "$ID_LIKE" == *"fedora"* ]]; then
            echo "📦 Detected RHEL-based OS. Using dnf."
            run_sudo dnf install -y "${packages[@]}"
        else
            echo "⚠️ Unsupported Linux distribution: $ID. Please install dependencies manually: ${packages[*]}"
            exit 1
        fi
    elif [ "$MACHINE" = "Mac" ]; then
        echo "📦 Detected macOS. Using Homebrew."
        if ! command -v brew &> /dev/null; then
            echo "    Homebrew not found. Please install it from https://brew.sh/"
            exit 1
        fi
        brew install "${packages[@]}"
    else
        echo "⚠️ Could not detect OS. Please install dependencies manually: ${packages[*]}"
        exit 1
    fi
}

# Check and install dependencies
DEPS_TO_INSTALL=()
if ! command -v python3 &> /dev/null; then DEPS_TO_INSTALL+=("python3"); fi
if ! command -v git &> /dev/null; then DEPS_TO_INSTALL+=("git"); fi
if ! command -v unzip &> /dev/null; then DEPS_TO_INSTALL+=("unzip"); fi
if ! command -v curl &> /dev/null; then DEPS_TO_INSTALL+=("curl"); fi
if ! command -v rsync &> /dev/null; then DEPS_TO_INSTALL+=("rsync"); fi

if [ ${#DEPS_TO_INSTALL[@]} -gt 0 ]; then
    echo "🔧 The following required tools are missing: ${DEPS_TO_INSTALL[*]}. Attempting to install them..."
    install_packages "${DEPS_TO_INSTALL[@]}"
else
    echo "✅ All required dependencies are already installed."
fi

# Check Python version (need 3.7+)
if ! python3 -c 'import sys; exit(0 if sys.version_info >= (3, 7) else 1)' 2>/dev/null; then
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    echo "❌ Python 3.7+ required, found $PYTHON_VERSION"
    echo "   Please upgrade Python manually."
    exit 1
fi

# Function to install 1Password CLI
install_op_cli() {
    if command -v op &> /dev/null; then
        echo "✅ 1Password CLI is already installed."
        return
    fi

    echo "🔧 1Password CLI not found. Attempting to install it..."

    if [ "$MACHINE" = "Linux" ] && [ -f /etc/os-release ]; then
        . /etc/os-release
        ID_LIKE=${ID_LIKE:-$ID}
        if [[ "$ID_LIKE" == *"rhel"* ]] || [[ "$ID_LIKE" == *"fedora"* ]]; then
            ARCH=$(uname -m)
            case "$ARCH" in
                x86_64) OP_ARCH="amd64";;
                aarch64) OP_ARCH="arm64";;
                *) echo "⚠️ Unsupported architecture for 1Password CLI: $ARCH"; return;;
            esac

            OP_VERSION="v2.29.0" # Specify a recent version
            OP_RPM="op_linux_${OP_ARCH}_${OP_VERSION}.rpm"
            OP_URL="https://downloads.1password.com/linux/rpm/stable/${ARCH}/${OP_RPM}"

            echo "📥 Downloading 1Password CLI from $OP_URL..."
            curl -sSL -o "/tmp/${OP_RPM}" "$OP_URL"

            echo "🔑 Installing 1Password CLI..."
            run_sudo dnf install -y "/tmp/${OP_RPM}"

            echo "🧹 Cleaning up..."
            rm "/tmp/${OP_RPM}"

            if command -v op &> /dev/null; then
                echo "✅ 1Password CLI installed successfully."
            else
                echo "❌ Failed to install 1Password CLI."
            fi
        else
            echo "⚠️ Automatic installation of 1Password CLI is only supported on RHEL-based systems. Please install it manually from https://developer.1password.com/docs/cli/get-started/"
        fi
    elif [ "$MACHINE" = "Mac" ]; then
        echo "    On macOS, please install via Homebrew: brew install --cask 1password-cli"
    else
        echo "⚠️ Please install 1Password CLI manually from https://developer.1password.com/docs/cli/get-started/"
    fi
}

install_op_cli


# Install directory
INSTALL_DIR="$HOME/oos"

# Remove existing installation
if [ -d "$INSTALL_DIR" ]; then
    echo "🔄 Updating existing OOS installation..."
    cd "$INSTALL_DIR"
    git pull
else
    echo "📥 Cloning OOS repository..."
    git clone https://github.com/Khamel83/oos.git "$INSTALL_DIR"
fi

# Make executable
chmod +x "$INSTALL_DIR/run.py"

# Try to create global command
if command -v sudo &> /dev/null; then
    echo "🔗 Creating global 'oos' command..."
    if sudo ln -sf "$INSTALL_DIR/run.py" /usr/local/bin/oos 2>/dev/null; then
        echo "✅ Global 'oos' command created"
        GLOBAL_INSTALL=true
    else
        echo "⚠️  Could not create global command (sudo failed)"
        GLOBAL_INSTALL=false
    fi
else
    echo "⚠️  No sudo available, skipping global installation"
    GLOBAL_INSTALL=false
fi

# Create personal alias if global install failed
if [ "$GLOBAL_INSTALL" = false ]; then
    echo "🔗 Adding personal alias..."

    # Detect shell
    SHELL_RC=""
    if [ -n "$BASH_VERSION" ]; then
        SHELL_RC="$HOME/.bashrc"
    elif [ -n "$ZSH_VERSION" ]; then
        SHELL_RC="$HOME/.zshrc"
    else
        SHELL_RC="$HOME/.profile"
    fi

    # Add alias if not already present
    ALIAS_LINE='alias oos="$HOME/oos/run.py"'
    if ! grep -q "alias oos=" "$SHELL_RC" 2>/dev/null; then
        echo "$ALIAS_LINE" >> "$SHELL_RC"
        echo "✅ Added 'oos' alias to $SHELL_RC"
        echo "   Run: source $SHELL_RC (or restart terminal)"
    else
        echo "✅ Alias already exists in $SHELL_RC"
    fi
fi

# Check optional dependencies
echo ""
echo "🔍 Checking optional dependencies..."

if command -v op &> /dev/null; then
    echo "✅ 1Password CLI found"
else
    echo "⚠️  1Password CLI not found (optional for secure environments)"
    echo "   Install: https://developer.1password.com/docs/cli/get-started/"
fi

if command -v gh &> /dev/null; then
    echo "✅ GitHub CLI found"
else
    echo "⚠️  GitHub CLI not found (optional for GitHub integration)"
    echo "   Install: https://cli.github.com/"
fi

echo ""
echo "🎉 OOS installation complete!"
echo ""
echo "📖 Usage:"
if [ "$GLOBAL_INSTALL" = true ]; then
    echo "  oos              # Interactive setup from any directory"
    echo "  oos --help       # Show help"
else
    echo "  $HOME/oos/run.py # Interactive setup"
    echo "  oos              # If you restart your terminal/source shell config"
fi
echo ""
echo "🚀 Try it now:"
echo "  mkdir /tmp/test-project && cd /tmp/test-project"
if [ "$GLOBAL_INSTALL" = true ]; then
    echo "  oos"
else
    echo "  $HOME/oos/run.py"
fi
echo ""
echo "📚 Full documentation: $INSTALL_DIR/docs/README_NEW_INTERFACE.md"