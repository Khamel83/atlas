#!/usr/bin/env bash
set -euo pipefail

# Create Command Interceptors - Block Development Commands Without Gate

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
INTERCEPTOR_DIR="$PROJECT_ROOT/bin/interceptors"

# Create interceptors directory
mkdir -p "$INTERCEPTOR_DIR"

# List of commands to intercept
commands=("python" "python3" "uv" "pip" "pip3" "pytest" "black" "ruff")

for cmd in "${commands[@]}"; do
    cat > "$INTERCEPTOR_DIR/$cmd" << EOF
#!/usr/bin/env bash

# Command Interceptor for $cmd - Requires Development Gate
SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="\$(cd "\$SCRIPT_DIR/../.." && pwd)"

# Check for emergency bypass
if [[ "\${DEV_GATE_BYPASS:-}" == "true" ]]; then
    exec "\$(command -v $cmd | grep -v interceptors | head -1)" "\$@"
fi

# Check if gate has been passed recently
if [[ -f "\$PROJECT_ROOT/.dev-gate-passed" ]]; then
    # Check if gate is recent (within last hour)
    if command -v stat >/dev/null 2>&1; then
        gate_time=\$(stat -f %m "\$PROJECT_ROOT/.dev-gate-passed" 2>/dev/null || stat -c %Y "\$PROJECT_ROOT/.dev-gate-passed" 2>/dev/null)
        current_time=\$(date +%s)
        age=\$((current_time - gate_time))

        if [[ \$age -lt 3600 ]]; then
            # Gate is recent, allow command
            exec "\$(command -v $cmd | grep -v interceptors | head -1)" "\$@"
        fi
    else
        # No stat command, just check if file exists
        exec "\$(command -v $cmd | grep -v interceptors | head -1)" "\$@"
    fi
fi

# Gate not passed or stale
echo -e "\\033[0;31m❌ Development environment not ready\\033[0m"
echo -e "\\033[0;33mRun: ./bin/dev-gate.sh\\033[0m"
echo
echo "This command ($cmd) is blocked until development environment is validated."
echo "Emergency bypass: DEV_GATE_BYPASS=true $cmd"
exit 1
EOF

    chmod +x "$INTERCEPTOR_DIR/$cmd"
done

echo "Created interceptors for: ${commands[*]}"