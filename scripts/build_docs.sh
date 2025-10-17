#!/bin/bash
"""
Atlas Documentation Build Script

This script builds the complete Atlas documentation including:
- API reference from docstrings
- User guides and tutorials
- Developer documentation
- Testing documentation
"""

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCS_DIR="$PROJECT_ROOT/docs"

echo -e "${GREEN}🔨 Building Atlas Documentation${NC}"
echo "Project root: $PROJECT_ROOT"
echo "Docs directory: $DOCS_DIR"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check dependencies
echo -e "\n${YELLOW}📋 Checking dependencies...${NC}"

if ! command_exists python; then
    echo -e "${RED}❌ Python is not installed${NC}"
    exit 1
fi

if ! command_exists pip; then
    echo -e "${RED}❌ pip is not installed${NC}"
    exit 1
fi

# Check if we're in a virtual environment
if [[ -z "${VIRTUAL_ENV:-}" ]]; then
    echo -e "${YELLOW}⚠️  Warning: Not in a virtual environment${NC}"
    echo "Consider activating a virtual environment before building docs"
fi

# Install documentation dependencies
echo -e "\n${YELLOW}📦 Installing documentation dependencies...${NC}"
cd "$PROJECT_ROOT"

# Check if Sphinx is installed
if ! python -c "import sphinx" 2>/dev/null; then
    echo "Installing Sphinx and documentation dependencies..."
    pip install -r requirements.txt
else
    echo "Sphinx already installed"
fi

# Navigate to docs directory
cd "$DOCS_DIR"

# Clean previous builds
echo -e "\n${YELLOW}🧹 Cleaning previous builds...${NC}"
if [ -d "_build" ]; then
    rm -rf _build
    echo "Cleaned _build directory"
fi

# Create necessary directories
mkdir -p _static
mkdir -p _templates
mkdir -p api-reference

# Build the documentation
echo -e "\n${YELLOW}🔨 Building HTML documentation...${NC}"

# Run Sphinx build with proper error handling
if sphinx-build -b html -W --keep-going . _build/html; then
    echo -e "\n${GREEN}✅ Documentation built successfully!${NC}"

    # Check if documentation was actually created
    if [ -f "_build/html/index.html" ]; then
        echo -e "${GREEN}📄 Main documentation file: $(pwd)/_build/html/index.html${NC}"

        # Calculate documentation size
        DOC_SIZE=$(du -sh _build/html | cut -f1)
        echo -e "${GREEN}📊 Documentation size: $DOC_SIZE${NC}"

        # Count generated pages
        HTML_COUNT=$(find _build/html -name "*.html" | wc -l)
        echo -e "${GREEN}📑 Generated pages: $HTML_COUNT${NC}"

    else
        echo -e "${RED}❌ Documentation build completed but index.html not found${NC}"
        exit 1
    fi
else
    echo -e "\n${RED}❌ Documentation build failed${NC}"
    echo "Check the output above for errors"
    exit 1
fi

# Optional: Build additional formats
if [ "${1:-}" = "--pdf" ] || [ "${1:-}" = "--all" ]; then
    echo -e "\n${YELLOW}📄 Building PDF documentation...${NC}"
    if command_exists latexmk; then
        sphinx-build -b latex . _build/latex
        cd _build/latex
        latexmk -pdf *.tex
        echo -e "${GREEN}✅ PDF documentation built${NC}"
        cd "$DOCS_DIR"
    else
        echo -e "${YELLOW}⚠️  LaTeX not available, skipping PDF build${NC}"
    fi
fi

# Generate coverage report
echo -e "\n${YELLOW}📊 Generating documentation coverage report...${NC}"
if sphinx-build -b coverage . _build/coverage; then
    if [ -f "_build/coverage/python.txt" ]; then
        echo -e "${GREEN}📈 Coverage report generated${NC}"

        # Show coverage summary
        UNDOC_COUNT=$(grep -c "UNDOC" _build/coverage/python.txt || true)
        if [ "$UNDOC_COUNT" -gt 0 ]; then
            echo -e "${YELLOW}⚠️  Found $UNDOC_COUNT undocumented items${NC}"
            echo "See _build/coverage/python.txt for details"
        else
            echo -e "${GREEN}🎉 All items are documented!${NC}"
        fi
    fi
fi

# Optional: Serve documentation locally
if [ "${1:-}" = "--serve" ] || [ "${2:-}" = "--serve" ]; then
    echo -e "\n${YELLOW}🌐 Starting local documentation server...${NC}"
    echo -e "${GREEN}📖 Documentation available at: http://localhost:8000${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"

    cd _build/html
    python -m http.server 8000
fi

# Success message
echo -e "\n${GREEN}🎉 Documentation build completed successfully!${NC}"
echo -e "${GREEN}📖 Open the following file in your browser:${NC}"
echo -e "${GREEN}   file://$(pwd)/_build/html/index.html${NC}"

if [ "${1:-}" != "--serve" ] && [ "${2:-}" != "--serve" ]; then
    echo -e "\n${YELLOW}💡 Tip: Use --serve flag to start a local server${NC}"
    echo -e "${YELLOW}💡 Example: $0 --serve${NC}"
fi