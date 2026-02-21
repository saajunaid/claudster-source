---
description: "Shell scripting best practices and conventions for bash, sh, zsh"
applyTo: "**/*.sh"
---

# Shell Scripting Guidelines

## General Principles

- Generate code that is clean, simple, and concise
- Ensure scripts are easily readable and understandable
- Add comments where helpful, but don't over-comment obvious lines
- Use shellcheck for static analysis when available
- Prefer safe expansions: double-quote variable references (`"$var"`), use `${var}` for clarity, avoid `eval`
- Use modern Bash features (`[[ ]]`, `local`, arrays) when portability allows; fall back to POSIX when needed
- Choose reliable parsers for structured data (`jq` for JSON, `yq` for YAML)

---

## Error Handling & Safety

### Always Enable Strict Mode

```bash
set -euo pipefail
```

- `set -e` — Exit on any command failure
- `set -u` — Treat unset variables as errors
- `set -o pipefail` — Pipe fails if any command in the pipeline fails

### Validate Inputs

```bash
# Validate required parameters before use
if [[ -z "${INPUT_FILE:-}" ]]; then
    echo "Error: INPUT_FILE is required." >&2
    exit 1
fi

if [[ ! -f "$INPUT_FILE" ]]; then
    echo "Error: File not found: $INPUT_FILE" >&2
    exit 1
fi
```

### Cleanup with Trap

Use `trap` to clean up temporary resources on exit, regardless of how the script terminates.

```bash
cleanup() {
    if [[ -n "${TEMP_DIR:-}" && -d "$TEMP_DIR" ]]; then
        rm -rf "$TEMP_DIR"
    fi
}
trap cleanup EXIT
```

### Use `mktemp` for Temporary Files

Never hardcode temp file paths. Use `mktemp` and clean up via `trap`.

```bash
TEMP_DIR="$(mktemp -d)"
TEMP_FILE="$(mktemp)"

# These will be cleaned up by the EXIT trap
```

### Immutable Values

Declare constants with `readonly` to prevent accidental modification.

```bash
readonly CONFIG_DIR="/etc/myapp"
readonly MAX_RETRIES=3
readonly SCRIPT_NAME="$(basename "$0")"
```

---

## Script Structure

Every script should follow a consistent structure:

1. Shebang line
2. Header comment with purpose
3. Strict mode (`set -euo pipefail`)
4. Cleanup trap
5. Constants and default values
6. Function definitions
7. Argument parsing
8. Main execution

```bash
#!/bin/bash
# ============================================================================
# Script: deploy.sh
# Description: Deploy application to target environment
# ============================================================================

set -euo pipefail

cleanup() {
    if [[ -n "${TEMP_DIR:-}" && -d "$TEMP_DIR" ]]; then
        rm -rf "$TEMP_DIR"
    fi
}
trap cleanup EXIT

# Defaults
readonly SCRIPT_NAME="$(basename "$0")"
ENVIRONMENT="staging"
VERBOSE=false
TEMP_DIR=""

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $*" >&2
}

usage() {
    cat <<EOF
Usage: $SCRIPT_NAME [OPTIONS]

Options:
    -e, --env ENV     Target environment (default: staging)
    -v, --verbose     Enable verbose output
    -h, --help        Show this help message

Examples:
    $SCRIPT_NAME --env production
    $SCRIPT_NAME -e staging -v
EOF
    exit 0
}

main() {
    TEMP_DIR="$(mktemp -d)"
    log "Starting deployment to $ENVIRONMENT..."

    # Main logic here

    log "Deployment complete."
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--env)
            ENVIRONMENT="${2:?'--env requires a value'}"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            ;;
    esac
done

main "$@"
```

---

## Functions

### Use `local` for Function Variables

Prevent variable leakage by declaring function-scoped variables with `local`.

```bash
process_file() {
    local input_file="$1"
    local output_file="$2"
    local line_count

    line_count=$(wc -l < "$input_file")
    log "Processing $input_file ($line_count lines)..."

    # Process...
    cp "$input_file" "$output_file"
}
```

### Return Values

Use return codes for success/failure. Use stdout for data output. Use stderr for messages.

```bash
get_config_value() {
    local key="$1"
    local config_file="${2:-config.ini}"

    if [[ ! -f "$config_file" ]]; then
        echo "Config file not found: $config_file" >&2
        return 1
    fi

    grep "^${key}=" "$config_file" | cut -d'=' -f2-
}

# Usage
if value=$(get_config_value "database_host"); then
    echo "Host: $value"
else
    echo "Failed to read config" >&2
fi
```

---

## Working with JSON and YAML

### Prefer `jq` for JSON, `yq` for YAML

Avoid parsing structured data with `grep`, `awk`, or `sed`. Use proper parsers.

```bash
# Check for required tools at script start
for cmd in jq curl; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "Error: Required command '$cmd' not found. Please install it." >&2
        exit 1
    fi
done
```

### JSON with `jq`

```bash
# Extract a field
name=$(jq -r '.name' config.json)

# Filter an array
active_users=$(jq -r '.users[] | select(.active == true) | .email' users.json)

# Transform data
jq '{
    total: (.items | length),
    names: [.items[].name]
}' data.json

# Handle missing fields safely
value=$(jq -r '.settings.timeout // 30' config.json)
```

### YAML with `yq`

```bash
# Extract a value
db_host=$(yq -r '.database.host' config.yaml)

# Update a value
yq -i '.version = "2.0.0"' config.yaml

# Handle missing fields
port=$(yq -r '.database.port // 5432' config.yaml)
```

### Best Practices

- Quote `jq`/`yq` filters to prevent shell expansion
- Use `--raw-output` (`-r`) for plain strings (no JSON quotes)
- Document parser dependencies at the top of the script
- Fail fast with a helpful message if `jq`/`yq` is not installed

---

## Common Patterns

### Retry Logic

```bash
retry() {
    local max_attempts="${1:-3}"
    local delay="${2:-5}"
    shift 2
    local attempt=1

    while [[ $attempt -le $max_attempts ]]; do
        if "$@"; then
            return 0
        fi
        log "Attempt $attempt/$max_attempts failed. Retrying in ${delay}s..."
        sleep "$delay"
        ((attempt++))
    done

    log_error "All $max_attempts attempts failed."
    return 1
}

# Usage
retry 3 5 curl -sf "https://api.example.com/health"
```

### Parallel Execution

```bash
# Run tasks in parallel and wait for all to complete
pids=()
for host in "${HOSTS[@]}"; do
    deploy_to_host "$host" &
    pids+=($!)
done

# Wait and check results
failures=0
for pid in "${pids[@]}"; do
    if ! wait "$pid"; then
        ((failures++))
    fi
done

if [[ $failures -gt 0 ]]; then
    log_error "$failures deployment(s) failed."
    exit 1
fi
```

### Safe File Operations

```bash
# Atomic write: write to temp, then move
write_config() {
    local target="$1"
    local content="$2"
    local tmp_file

    tmp_file="$(mktemp "${target}.XXXXXX")"
    echo "$content" > "$tmp_file"
    mv "$tmp_file" "$target"
}

# Safe directory creation
ensure_dir() {
    local dir="$1"
    if [[ ! -d "$dir" ]]; then
        mkdir -p "$dir"
        log "Created directory: $dir"
    fi
}
```

---

## Style Conventions

- Indent with 4 spaces (no tabs)
- Use `snake_case` for variables and functions
- Use `UPPER_SNAKE_CASE` for constants and environment variables
- Keep lines under 100 characters; use `\` for continuation
- Use `[[ ]]` instead of `[ ]` for conditionals (Bash)
- Use `$(command)` instead of backticks for command substitution
- Redirect errors to stderr: `echo "Error: ..." >&2`
