#!/bin/bash
# Universal Port Assignment Script
# Assigns unique ports to projects based on project name hash

PROJECT_NAME=${PWD##*/}
echo "🔧 Setting up unique port for project: $PROJECT_NAME"

# Generate unique port based on project name (7000-9999 range)
UNIQUE_PORT=$((7000 + $(echo $PROJECT_NAME | md5sum | cut -c1-3 | python3 -c "import sys; print(int(sys.stdin.read().strip(), 16) % 3000)")))

# Check if .env already has a port configured
if grep -q "API_PORT=" .env 2>/dev/null; then
    CURRENT_PORT=$(grep "API_PORT=" .env | cut -d= -f2)
    echo "📍 Current port: $CURRENT_PORT"
    echo "🎯 Generated port: $UNIQUE_PORT"

    read -p "Replace current port with generated unique port? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sed -i "s/API_PORT=.*/API_PORT=$UNIQUE_PORT/" .env
        echo "✅ Updated .env with unique port $UNIQUE_PORT"
    else
        echo "⏭️  Keeping existing port $CURRENT_PORT"
    fi
else
    # No existing port, add it
    echo "API_PORT=$UNIQUE_PORT" >> .env
    echo "✅ Added unique port $UNIQUE_PORT to .env"
fi

echo ""
echo "🌐 Your project will run on: http://localhost:$UNIQUE_PORT"
echo "📝 Port is stable and based on project name '$PROJECT_NAME'"