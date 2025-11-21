#!/usr/bin/env bash
set -euo pipefail

# OOS Project Template System
# Usage: ./bin/template_manager.sh [COMMAND] [OPTIONS]

VERSION="1.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATES_DIR="$PROJECT_ROOT/templates"
TEMPLATE_REGISTRY="$TEMPLATES_DIR/registry.json"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Utility functions
log() { echo -e "${BLUE}[INFO]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $*"; }

# Show help
show_help() {
  cat << 'EOF'
OOS Project Template System v1.0.0

Commands:
  list                    List available templates
  create NAME             Create new project from template
  add TEMPLATE_PATH       Add new template to registry
  remove TEMPLATE_NAME    Remove template from registry
  validate TEMPLATE       Validate template structure
  init                    Initialize template system
  sync                    Sync templates from remote sources

Options:
  --template, -t NAME     Use specific template
  --output, -o PATH       Output directory for new project
  --vars FILE             Variables file for substitution
  --dry-run               Show what would be done
  --verbose               Show detailed output
  --help, -h              Show this help

Examples:
  ./bin/template_manager.sh list
  ./bin/template_manager.sh create myapp -t web-app -o /path/to/project
  ./bin/template_manager.sh add /path/to/custom-template
EOF
}

# Initialize template system
init_template_system() {
  log "Initializing OOS template system..."

  mkdir -p "$TEMPLATES_DIR/builtin" "$TEMPLATES_DIR/community" "$TEMPLATES_DIR/custom"

  # Create template registry
  if [[ ! -f "$TEMPLATE_REGISTRY" ]]; then
    cat > "$TEMPLATE_REGISTRY" <<'JSON'
{
  "version": "1.0.0",
  "templates": {},
  "sources": [],
  "last_updated": ""
}
JSON
  fi

  create_builtin_templates
  success "Template system initialized"
}

# Create built-in templates
create_builtin_templates() {
  log "Creating built-in templates..."

  # Web Application Template
  create_web_template

  # CLI Tool Template
  create_cli_template

  # API Service Template
  create_api_template

  # Library Template
  create_library_template

  # Update registry
  update_template_registry
}

# Create web application template
create_web_template() {
  local template_dir="$TEMPLATES_DIR/builtin/web-app"
  mkdir -p "$template_dir"

  cat > "$template_dir/template.json" <<'JSON'
{
  "name": "web-app",
  "version": "1.0.0",
  "description": "Modern web application with React/Vue frontend and Node.js backend",
  "category": "web",
  "tags": ["react", "nodejs", "fullstack"],
  "variables": {
    "PROJECT_NAME": {
      "description": "Project name",
      "type": "string",
      "required": true
    },
    "FRONTEND_FRAMEWORK": {
      "description": "Frontend framework",
      "type": "choice",
      "options": ["react", "vue", "svelte"],
      "default": "react"
    },
    "BACKEND_TYPE": {
      "description": "Backend type",
      "type": "choice",
      "options": ["express", "fastify", "koa"],
      "default": "express"
    },
    "DATABASE": {
      "description": "Database type",
      "type": "choice",
      "options": ["postgresql", "mongodb", "sqlite"],
      "default": "postgresql"
    }
  },
  "hooks": {
    "pre_create": ["validate_node_version"],
    "post_create": ["install_dependencies", "setup_database"]
  }
}
JSON

  # Create template structure
  mkdir -p "$template_dir/template/src" "$template_dir/template/public" "$template_dir/template/api"

  cat > "$template_dir/template/package.json" <<'JSON'
{
  "name": "{{PROJECT_NAME}}",
  "version": "1.0.0",
  "description": "Web application created from OOS template",
  "main": "src/index.js",
  "scripts": {
    "dev": "concurrently \"npm run dev:frontend\" \"npm run dev:backend\"",
    "dev:frontend": "{{#if_eq FRONTEND_FRAMEWORK 'react'}}react-scripts start{{/if_eq}}{{#if_eq FRONTEND_FRAMEWORK 'vue'}}vue-cli-service serve{{/if_eq}}",
    "dev:backend": "nodemon api/server.js",
    "build": "npm run build:frontend && npm run build:backend",
    "test": "jest"
  },
  "dependencies": {
    "{{#if_eq BACKEND_TYPE 'express'}}express{{/if_eq}}{{#if_eq BACKEND_TYPE 'fastify'}}fastify{{/if_eq}}": "latest"
  }
}
JSON

  cat > "$template_dir/template/README.md" <<'MD'
# {{PROJECT_NAME}}

Web application built with {{FRONTEND_FRAMEWORK}} and {{BACKEND_TYPE}}.

## Getting Started

1. Install dependencies:
   ```bash
   npm install
   ```

2. Start development server:
   ```bash
   npm run dev
   ```

3. Open http://localhost:3000

## Database

This project uses {{DATABASE}} as the database.

## Architecture

- Frontend: {{FRONTEND_FRAMEWORK}}
- Backend: {{BACKEND_TYPE}}
- Database: {{DATABASE}}
MD
}

# Create CLI tool template
create_cli_template() {
  local template_dir="$TEMPLATES_DIR/builtin/cli-tool"
  mkdir -p "$template_dir"

  cat > "$template_dir/template.json" <<'JSON'
{
  "name": "cli-tool",
  "version": "1.0.0",
  "description": "Command-line tool with argument parsing and subcommands",
  "category": "cli",
  "tags": ["cli", "bash", "python"],
  "variables": {
    "PROJECT_NAME": {
      "description": "CLI tool name",
      "type": "string",
      "required": true
    },
    "LANGUAGE": {
      "description": "Implementation language",
      "type": "choice",
      "options": ["bash", "python", "go", "rust"],
      "default": "bash"
    },
    "AUTHOR_NAME": {
      "description": "Author name",
      "type": "string",
      "default": "{{GIT_USER_NAME}}"
    }
  }
}
JSON

  mkdir -p "$template_dir/template/bin" "$template_dir/template/lib" "$template_dir/template/tests"

  cat > "$template_dir/template/bin/{{PROJECT_NAME}}" <<'BASH'
#!/usr/bin/env {{#if_eq LANGUAGE 'bash'}}bash{{/if_eq}}{{#if_eq LANGUAGE 'python'}}python3{{/if_eq}}
{{#if_eq LANGUAGE 'bash'}}
set -euo pipefail

VERSION="1.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

show_help() {
  cat << 'EOF'
{{PROJECT_NAME}} v$VERSION

Usage: {{PROJECT_NAME}} [COMMAND] [OPTIONS]

Commands:
  help        Show this help
  version     Show version

Options:
  --verbose   Show detailed output
  --help, -h  Show help
EOF
}

main() {
  local command="${1:-help}"

  case "$command" in
    help|--help|-h) show_help ;;
    version|--version|-v) echo "{{PROJECT_NAME}} v$VERSION" ;;
    *) echo "Unknown command: $command"; exit 1 ;;
  esac
}

main "$@"
{{/if_eq}}
BASH
}

# Create API service template
create_api_template() {
  local template_dir="$TEMPLATES_DIR/builtin/api-service"
  mkdir -p "$template_dir"

  cat > "$template_dir/template.json" <<'JSON'
{
  "name": "api-service",
  "version": "1.0.0",
  "description": "RESTful API service with authentication and database integration",
  "category": "backend",
  "tags": ["api", "rest", "microservice"],
  "variables": {
    "PROJECT_NAME": {
      "description": "API service name",
      "type": "string",
      "required": true
    },
    "API_FRAMEWORK": {
      "description": "API framework",
      "type": "choice",
      "options": ["express", "fastapi", "gin", "actix-web"],
      "default": "express"
    },
    "AUTH_METHOD": {
      "description": "Authentication method",
      "type": "choice",
      "options": ["jwt", "oauth2", "api-key"],
      "default": "jwt"
    },
    "DATABASE": {
      "description": "Database type",
      "type": "choice",
      "options": ["postgresql", "mongodb", "redis"],
      "default": "postgresql"
    }
  }
}
JSON
}

# Create library template
create_library_template() {
  local template_dir="$TEMPLATES_DIR/builtin/library"
  mkdir -p "$template_dir"

  cat > "$template_dir/template.json" <<'JSON'
{
  "name": "library",
  "version": "1.0.0",
  "description": "Reusable library with comprehensive testing and documentation",
  "category": "library",
  "tags": ["library", "npm", "package"],
  "variables": {
    "PROJECT_NAME": {
      "description": "Library name",
      "type": "string",
      "required": true
    },
    "LANGUAGE": {
      "description": "Programming language",
      "type": "choice",
      "options": ["javascript", "typescript", "python", "go"],
      "default": "typescript"
    }
  }
}
JSON
}

# Update template registry
update_template_registry() {
  local registry_content
  registry_content=$(TEMPLATE_REGISTRY="$TEMPLATE_REGISTRY" TEMPLATES_DIR="$TEMPLATES_DIR" python3 - <<'PY'
import json
import os
from datetime import datetime

registry_file = os.environ.get('TEMPLATE_REGISTRY')
templates_dir = os.environ.get('TEMPLATES_DIR')

# Load existing registry
registry = {"version": "1.0.0", "templates": {}, "sources": [], "last_updated": ""}
if os.path.exists(registry_file):
    with open(registry_file) as f:
        registry = json.load(f)

# Scan for templates
for root, dirs, files in os.walk(templates_dir):
    if 'template.json' in files:
        template_path = os.path.join(root, 'template.json')
        try:
            with open(template_path) as f:
                template_config = json.load(f)

            template_name = template_config['name']
            registry['templates'][template_name] = {
                'path': root,
                'config': template_config,
                'type': 'builtin' if 'builtin' in root else 'custom'
            }
        except Exception as e:
            print(f"Warning: Failed to load template {template_path}: {e}")

registry['last_updated'] = datetime.now().isoformat()

# Write updated registry
with open(registry_file, 'w') as f:
    json.dump(registry, f, indent=2)

print("Template registry updated")
PY
)

  echo "$registry_content"
}

# List available templates
list_templates() {
  if [[ ! -f "$TEMPLATE_REGISTRY" ]]; then
    warn "Template registry not found. Run 'init' first."
    return 1
  fi

  echo -e "${PURPLE}Available Templates:${NC}"
  echo

  TEMPLATE_REGISTRY="$TEMPLATE_REGISTRY" python3 - <<'PY'
import json
import os

registry_file = os.environ.get('TEMPLATE_REGISTRY')
with open(registry_file) as f:
    registry = json.load(f)

templates = registry.get('templates', {})
if not templates:
    print("No templates available.")
else:
    for name, info in templates.items():
        config = info['config']
        print(f"📦 {name}")
        print(f"   Description: {config.get('description', 'No description')}")
        print(f"   Category: {config.get('category', 'general')}")
        print(f"   Tags: {', '.join(config.get('tags', []))}")
        print(f"   Type: {info.get('type', 'unknown')}")
        print()
PY
}

# Variable substitution engine
substitute_template_vars() {
  local template_file="$1"
  local vars_file="$2"
  local output_file="$3"

  python3 - "$template_file" "$vars_file" "$output_file" <<'PY'
import sys
import json
import re
from pathlib import Path

template_file = sys.argv[1]
vars_file = sys.argv[2]
output_file = sys.argv[3]

# Load variables
variables = {}
if Path(vars_file).exists():
    with open(vars_file) as f:
        variables = json.load(f)

# Read template content
with open(template_file) as f:
    content = f.read()

# Simple variable substitution
def substitute(match):
    var_name = match.group(1)
    return str(variables.get(var_name, match.group(0)))

# Handle {{VARIABLE}} syntax
content = re.sub(r'\{\{([A-Z_][A-Z0-9_]*)\}\}', substitute, content)

# Handle conditional blocks {{#if_eq VAR 'value'}}...{{/if_eq}}
def handle_conditional(match):
    var_name = match.group(1)
    expected_value = match.group(2).strip('"\'')
    block_content = match.group(3)

    actual_value = variables.get(var_name, '')
    if str(actual_value) == expected_value:
        return block_content
    return ''

content = re.sub(r'\{\{#if_eq\s+([A-Z_][A-Z0-9_]*)\s+["\']([^"\']*)["\']}\}(.*?)\{\{/if_eq}\}',
                 handle_conditional, content, flags=re.DOTALL)

# Write output
with open(output_file, 'w') as f:
    f.write(content)
PY
}

# Validate template structure and requirements
validate_template() {
  local template_name="$1"

  if [[ ! -f "$TEMPLATE_REGISTRY" ]]; then
    error "Template registry not found. Run 'init' first."
    return 1
  fi

  log "Validating template '$template_name'..."

  # Check if template exists in registry
  if ! grep -q "^$template_name:" "$TEMPLATE_REGISTRY"; then
    error "Template '$template_name' not found in registry"
    return 1
  fi

  # Get template directory
  local template_dir
  template_dir=$(grep "^$template_name:" "$TEMPLATE_REGISTRY" | cut -d: -f2)

  if [[ ! -d "$template_dir" ]]; then
    error "Template directory '$template_dir' does not exist"
    return 1
  fi

  # Check required files
  local required_files=("template.yaml" "README.md")
  for file in "${required_files[@]}"; do
    if [[ ! -f "$template_dir/$file" ]]; then
      error "Required file '$file' missing from template"
      return 1
    fi
  done

  # Validate template.yaml structure
  if ! python3 -c "
import yaml
import sys
try:
    with open('$template_dir/template.yaml') as f:
        data = yaml.safe_load(f)
    required = ['name', 'description', 'type', 'files']
    for field in required:
        if field not in data:
            sys.exit(1)
    print('Template structure is valid')
except Exception as e:
    sys.exit(1)
"; then
    error "Template.yaml structure is invalid"
    return 1
  fi

  # Check template files exist
  if ! python3 -c "
import yaml
import sys
import os
try:
    with open('$template_dir/template.yaml') as f:
        data = yaml.safe_load(f)
    for file_info in data.get('files', []):
        if not os.path.exists('$template_dir/' + file_info['path']):
            sys.exit(1)
    print('All template files exist')
except Exception as e:
    sys.exit(1)
"; then
    error "Some template files are missing"
    return 1
  fi

  success "Template '$template_name' is valid ✓"
  return 0
}

# Create project from template
create_from_template() {
  local project_name="$1"
  local template_name="${2:-web-app}"
  local output_dir="${3:-$(pwd)/$project_name}"
  local vars_file="${4:-}"
  local dry_run="${5:-false}"

  if [[ ! -f "$TEMPLATE_REGISTRY" ]]; then
    error "Template registry not found. Run 'init' first."
    return 1
  fi

  log "Creating project '$project_name' from template '$template_name'..."

  # Get template info
  local template_info
  template_info=$(python3 - "$template_name" <<'PY'
import json
import sys
import os

template_name = sys.argv[1]
registry_file = os.environ.get('TEMPLATE_REGISTRY')

with open(registry_file) as f:
    registry = json.load(f)

templates = registry.get('templates', {})
if template_name not in templates:
    print(f"ERROR: Template '{template_name}' not found")
    sys.exit(1)

template_info = templates[template_name]
print(json.dumps(template_info))
PY
)

  if [[ $? -ne 0 ]]; then
    error "$template_info"
    return 1
  fi

  local template_path
  template_path=$(echo "$template_info" | python3 -c "import sys, json; info=json.load(sys.stdin); print(info['path'])")

  if [[ "$dry_run" == "true" ]]; then
    log "Would create project at: $output_dir"
    log "Using template at: $template_path"
    return 0
  fi

  # Create output directory
  mkdir -p "$output_dir"

  # Collect variables
  local collected_vars_file
  collected_vars_file=$(mktemp)

  collect_template_variables "$template_path/template.json" "$project_name" "$collected_vars_file" "$vars_file"

  # Copy and process template files
  process_template_files "$template_path/template" "$output_dir" "$collected_vars_file"

  # Run post-creation hooks
  run_template_hooks "$template_path/template.json" "post_create" "$output_dir" "$collected_vars_file"

  rm -f "$collected_vars_file"

  success "Project '$project_name' created successfully at $output_dir"
}

# Collect template variables
collect_template_variables() {
  local template_config="$1"
  local project_name="$2"
  local output_file="$3"
  local input_vars_file="${4:-}"

  python3 - "$template_config" "$project_name" "$output_file" "$input_vars_file" <<'PY'
import json
import sys
import os
from pathlib import Path

template_config_file = sys.argv[1]
project_name = sys.argv[2]
output_file = sys.argv[3]
input_vars_file = sys.argv[4] if len(sys.argv) > 4 else None

# Load template config
with open(template_config_file) as f:
    config = json.load(f)

# Start with provided variables
variables = {}
if input_vars_file and Path(input_vars_file).exists():
    with open(input_vars_file) as f:
        variables = json.load(f)

# Add built-in variables
variables['PROJECT_NAME'] = project_name
variables['GIT_USER_NAME'] = os.popen('git config user.name 2>/dev/null').read().strip() or 'Unknown'
variables['GIT_USER_EMAIL'] = os.popen('git config user.email 2>/dev/null').read().strip() or 'unknown@example.com'

# Process template variables
template_vars = config.get('variables', {})
for var_name, var_config in template_vars.items():
    if var_name in variables:
        continue  # Already provided

    if var_config.get('default'):
        variables[var_name] = var_config['default']
    elif var_config.get('required', False):
        # For now, use placeholder values
        var_type = var_config.get('type', 'string')
        if var_type == 'choice':
            options = var_config.get('options', [])
            variables[var_name] = options[0] if options else 'default'
        else:
            variables[var_name] = f'PLACEHOLDER_{var_name}'

# Write variables
with open(output_file, 'w') as f:
    json.dump(variables, f, indent=2)
PY
}

# Process template files
process_template_files() {
  local src_dir="$1"
  local dest_dir="$2"
  local vars_file="$3"

  find "$src_dir" -type f | while read -r file; do
    local rel_path="${file#$src_dir/}"
    local dest_file="$dest_dir/$rel_path"

    # Create destination directory
    mkdir -p "$(dirname "$dest_file")"

    # Process file based on type
    if [[ "$file" =~ \.(md|json|js|py|sh|yml|yaml|toml|txt)$ ]]; then
      # Text files: apply variable substitution
      substitute_template_vars "$file" "$vars_file" "$dest_file"
    else
      # Binary files: copy as-is
      cp "$file" "$dest_file"
    fi
  done
}

# Run template hooks
run_template_hooks() {
  local template_config="$1"
  local hook_type="$2"
  local project_dir="$3"
  local vars_file="$4"

  python3 - "$template_config" "$hook_type" "$project_dir" "$vars_file" <<'PY'
import json
import sys
import os
import subprocess

template_config_file = sys.argv[1]
hook_type = sys.argv[2]
project_dir = sys.argv[3]
vars_file = sys.argv[4]

# Load template config
with open(template_config_file) as f:
    config = json.load(f)

hooks = config.get('hooks', {}).get(hook_type, [])
if not hooks:
    sys.exit(0)

# Change to project directory
original_dir = os.getcwd()
os.chdir(project_dir)

try:
    for hook in hooks:
        print(f"Running hook: {hook}")
        if hook == 'install_dependencies':
            if os.path.exists('package.json'):
                subprocess.run(['npm', 'install'], check=True)
        elif hook == 'setup_database':
            print("Database setup hook (placeholder)")
        elif hook == 'validate_node_version':
            subprocess.run(['node', '--version'], check=True)
        else:
            print(f"Unknown hook: {hook}")
finally:
    os.chdir(original_dir)
PY
}

# Main command dispatcher
main() {
  local command="${1:-help}"

  case "$command" in
    init)
      init_template_system
      ;;
    list)
      list_templates
      ;;
    create)
      if [[ $# -lt 2 ]]; then
        error "Usage: create PROJECT_NAME [OPTIONS]"
        exit 1
      fi

      local project_name="$2"
      local template_name="web-app"
      local output_dir=""
      local vars_file=""
      local dry_run=false

      shift 2
      while [[ $# -gt 0 ]]; do
        case $1 in
          --template|-t) template_name="$2"; shift 2 ;;
          --output|-o) output_dir="$2"; shift 2 ;;
          --vars) vars_file="$2"; shift 2 ;;
          --dry-run) dry_run=true; shift ;;
          *) error "Unknown option: $1"; exit 1 ;;
        esac
      done

      create_from_template "$project_name" "$template_name" "$output_dir" "$vars_file" "$dry_run"
      ;;
    validate)
      shift
      local template_name="$1"
      if [[ -z "$template_name" ]]; then
        error "Template name required for validation"
        exit 1
      fi

      validate_template "$template_name"
      ;;
    sync)
      update_template_registry
      ;;
    help|--help|-h)
      show_help
      ;;
    *)
      error "Unknown command: $command"
      show_help
      exit 1
      ;;
  esac
}

main "$@"