# Portable POSIX Shell Guide

This document explains OOS's approach to portable POSIX shell scripting across macOS and Linux systems.

## Why POSIX Shell?

We use portable POSIX `sh` instead of bash/zsh/fish for several reasons:

- **Portability**: Works on macOS, Linux, BSD, and other Unix-like systems
- **Compatibility**: Available on all systems by default
- **Fewer Footguns**: Avoids bash-specific features that differ between systems
- **Simplicity**: Forces cleaner, more maintainable scripts

## macOS vs Linux Differences

The main differences between macOS (BSD) and Linux (GNU) systems:

- **macOS**: Uses BSD versions of core utilities (sed, awk, find, etc.)
- **Linux**: Uses GNU versions with different command-line options
- **Paths**: GNU tools on macOS are typically prefixed with 'g' (gsed, gawk, etc.)

## GNU Coreutils on macOS

To make macOS behave like Linux, we front-load GNU coreutils in the PATH:

```bash
# These paths are added to ~/.zshrc by the bootstrap script
/opt/homebrew/opt/coreutils/libexec/gnubin
/opt/homebrew/opt/findutils/libexec/gnubin
/opt/homebrew/opt/gnu-sed/libexec/gnubin
/opt/homebrew/opt/grep/libexec/gnubin
```

This gives us GNU versions of commands while maintaining compatibility.

## Using the Portable Helpers

### scripts/posix/portable.sh

This script provides cross-platform helper functions:

```sh
# Load the portable helpers
. scripts/posix/portable.sh

# Use the portable functions
p_date "+%Y-%m-%d"           # GNU/BSD compatible date
p_sedi 's/old/new/g' file   # GNU/BSD compatible sed -i
p_realpath "./file.txt"     # Cross-platform realpath
p_mktemp                    # Creates temporary file
```

### templates/sh/template.sh

Use this as a starting point for new shell scripts:

```sh
#!/usr/bin/env sh
# shellcheck shell=sh
set -eu
[ -f "$HOME/.config/sh/portable.sh" ] && . "$HOME/.config/sh/portable.sh" || true
[ -f "$(dirname "$0")/../../scripts/posix/portable.sh" ] && . "$(dirname "$0")/../../scripts/posix/portable.sh" || true

# Your script logic here
```

## Available Commands

### Setup and Bootstrap

```bash
# Bootstrap your environment (install tools, configure PATH)
make posix-bootstrap
# or
./bin/oos-posix-bootstrap
```

### Validation and Testing

```bash
# Check your POSIX environment
./bin/oos-doctor-posix-check

# Run shell linting
make lint-sh

# Format shell scripts
make format-sh

# Test portable template
make test-posix
```

## Writing Portable Scripts

### Shebang and ShellCheck

Always use:
```sh
#!/usr/bin/env sh
# shellcheck shell=sh
```

### Key Portable Patterns

#### Command Existence
```sh
if command -v cmd >/dev/null 2>&1; then
    # command exists
fi
```

#### Safe Options Parsing
```sh
while getopts ":hvf:" opt; do
    case "$opt" in
        h) usage; exit 0 ;;
        v) verbose=1 ;;
        f) file="$OPTARG" ;;
        \?) usage; exit 2 ;;
    esac
done
```

#### Safe Temporary Files
```sh
tmpfile=$(mktemp "${TMPDIR:-/tmp}/script.XXXXXX")
trap 'rm -f "$tmpfile"' EXIT
```

#### Safe Directory Creation
```sh
mkdir -p -- "$directory"  # Use -- to handle filenames starting with -
```

#### Safe File Operations
```sh
# Use null delimiters for filenames with spaces
find . -type f -print0 | xargs -0 command

# Portable echo
printf '%s\n' "message"

# Portable test
[ "$var" = "value" ]  # not ==
```

## Shell Linting and Formatting

We use two tools for shell code quality:

### ShellCheck
Static analysis tool for shell scripts:
```bash
shellcheck -s sh script.sh
```

### shfmt
Shell script formatter:
```bash
shfmt -ln posix -w script.sh
```

## CI/CD Integration

The `.github/workflows/shell-portability.yml` workflow automatically:
- Runs ShellCheck on all `.sh` files
- Checks formatting with shfmt
- Tests the portable template script
- Ensures cross-platform compatibility

## Pre-commit Hooks

The `.githooks/pre-commit` hook automatically:
- Runs ShellCheck on committed shell scripts
- Formats scripts with shfmt if available
- Adds formatted files back to the commit

## Environment Setup

### macOS
1. Run `./bin/oos-posix-bootstrap` to install Homebrew and GNU tools
2. PATH is updated in `~/.zshrc` to prioritize GNU utilities
3. `portable.sh` is copied to `~/.config/sh/`

### Linux
1. Run `./bin/oos-posix-bootstrap` to install required packages
2. Standard GNU utilities are used
3. `portable.sh` is copied to `~/.config/sh/`

## Troubleshooting

### Common Issues

**Missing GNU tools on macOS:**
```bash
brew install coreutils findutils gnu-sed gawk grep
```

**ShellCheck not found:**
```bash
# macOS
brew install shellcheck

# Linux (Ubuntu/Debian)
sudo apt-get install shellcheck
```

**shfmt not found:**
```bash
# macOS
brew install shfmt

# Linux (Go package)
go install mvdan.cc/sh/v3/cmd/shfmt@latest
```

### Testing Your Scripts

Always test scripts on both platforms:
```bash
# Test with dash (strict POSIX)
dash your-script.sh

# Test with bash in POSIX mode
bash --posix your-script.sh

# Test the template
make test-posix
```

## Best Practices

1. **Always test on both platforms** when possible
2. **Use ShellCheck** (`shellcheck -s sh`) on all scripts
3. **Format with shfmt** (`shfmt -ln posix`) for consistency
4. **Use the template** as a starting point for new scripts
5. **Prefer portable functions** from `portable.sh` over raw commands
6. **Write defensive code** - assume tools might behave differently
7. **Use explicit paths** when tool behavior varies
8. **Test with multiple shells** (sh, dash, bash --posix)