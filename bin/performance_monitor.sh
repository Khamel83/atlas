#!/usr/bin/env bash
set -euo pipefail

# OOS Performance Monitoring and Optimization Tools
# Usage: ./bin/performance_monitor.sh [COMMAND] [OPTIONS]

VERSION="1.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PERF_LOG_DIR="$PROJECT_ROOT/performance-logs"
BENCHMARK_DIR="$PROJECT_ROOT/benchmarks"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "${BLUE}[INFO]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $*"; }

show_help() {
  cat << 'EOF'
OOS Performance Monitor v1.0.0

Commands:
  profile SCRIPT          Profile script execution time
  benchmark               Run comprehensive benchmarks
  analyze                 Analyze performance data
  monitor                 Start continuous monitoring
  report                  Generate performance report
  optimize                Get optimization recommendations

Options:
  --duration SECONDS      Monitoring duration (default: 300)
  --interval SECONDS      Sample interval (default: 5)
  --output FILE          Output file for results
  --baseline             Create performance baseline
  --compare FILE         Compare with baseline
  --verbose              Show detailed output

Examples:
  ./bin/performance_monitor.sh profile bootstrap_enhanced.sh
  ./bin/performance_monitor.sh benchmark --baseline
  ./bin/performance_monitor.sh monitor --duration 600
EOF
}

# Setup performance monitoring
setup_monitoring() {
  mkdir -p "$PERF_LOG_DIR" "$BENCHMARK_DIR"

  # Create performance baseline if it doesn't exist
  local baseline_file="$BENCHMARK_DIR/baseline.json"
  if [[ ! -f "$baseline_file" ]]; then
    log "Creating performance baseline..."
    create_baseline
  fi
}

# Profile script execution
profile_script() {
  local script_path="$1"
  local output_file="${2:-$PERF_LOG_DIR/profile-$(date +%Y%m%d-%H%M%S).json}"

  if [[ ! -f "$script_path" ]]; then
    error "Script not found: $script_path"
    return 1
  fi

  log "Profiling: $script_path"

  local start_time_ns start_time_s end_time_ns end_time_s
  local cpu_before cpu_after mem_before mem_after

  # Get initial resource usage
  cpu_before=$(cat /proc/loadavg | awk '{print $1}')
  mem_before=$(free -m | awk 'NR==2{print $3}')

  # Profile execution
  start_time_ns=$(date +%s%N)
  start_time_s=$(date +%s)

  # Run with time and resource monitoring
  local exit_code=0
  timeout 300 /usr/bin/time -v bash "$script_path" 2>"$PERF_LOG_DIR/time_output.tmp" || exit_code=$?

  end_time_ns=$(date +%s%N)
  end_time_s=$(date +%s)

  # Get final resource usage
  cpu_after=$(cat /proc/loadavg | awk '{print $1}')
  mem_after=$(free -m | awk '{print $3}')

  # Calculate metrics
  local duration_ms=$(( (end_time_ns - start_time_ns) / 1000000 ))
  local duration_s=$(( end_time_s - start_time_s ))

  # Parse time output
  local time_data=""
  if [[ -f "$PERF_LOG_DIR/time_output.tmp" ]]; then
    time_data=$(cat "$PERF_LOG_DIR/time_output.tmp")
  fi

  # Create JSON report
  cat > "$output_file" <<JSON
{
  "timestamp": "$(date -Iseconds)",
  "script": "$script_path",
  "duration_ms": $duration_ms,
  "duration_s": $duration_s,
  "exit_code": $exit_code,
  "resources": {
    "cpu_load_before": $cpu_before,
    "cpu_load_after": $cpu_after,
    "memory_mb_before": $mem_before,
    "memory_mb_after": $mem_after,
    "memory_delta_mb": $(( mem_after - mem_before ))
  },
  "time_output": $(echo "$time_data" | python3 -c "import sys, json; print(json.dumps(sys.stdin.read()))")
}
JSON

  # Cleanup
  rm -f "$PERF_LOG_DIR/time_output.tmp"

  success "Profile saved to: $output_file"

  # Show summary
  echo
  echo "Performance Summary:"
  echo "==================="
  echo "Duration: ${duration_ms}ms (${duration_s}s)"
  echo "Exit Code: $exit_code"
  echo "CPU Load: $cpu_before → $cpu_after"
  echo "Memory: ${mem_before}MB → ${mem_after}MB (${mem_delta:-0}MB change)"
}

# Run comprehensive benchmarks
run_benchmarks() {
  local baseline_mode="${1:-false}"
  local output_file="$BENCHMARK_DIR/benchmark-$(date +%Y%m%d-%H%M%S).json"

  if [[ "$baseline_mode" == "true" ]]; then
    output_file="$BENCHMARK_DIR/baseline.json"
  fi

  log "Running comprehensive benchmarks..."

  local results=()

  # Bootstrap performance
  if [[ -f "bootstrap_enhanced.sh" ]]; then
    log "Benchmarking bootstrap (dry-run)..."
    local bootstrap_start=$(date +%s%N)
    ./bootstrap_enhanced.sh --dry-run --no-preflight test-bench /tmp/test-bench >/dev/null 2>&1 || true
    local bootstrap_end=$(date +%s%N)
    local bootstrap_ms=$(( (bootstrap_end - bootstrap_start) / 1000000 ))
    results+=("\"bootstrap_dry_run_ms\": $bootstrap_ms")
  fi

  # Environment loading performance
  if [[ -f ".env" && -f "bin/safe_source_env.sh" ]]; then
    log "Benchmarking environment loading..."
    local env_total=0
    for i in {1..5}; do
      local env_start=$(date +%s%N)
      bash bin/safe_source_env.sh .env >/dev/null 2>&1 || true
      local env_end=$(date +%s%N)
      env_total=$(( env_total + (env_end - env_start) ))
    done
    local env_avg_ms=$(( env_total / 5000000 ))
    results+=("\"env_loading_avg_ms\": $env_avg_ms")
  fi

  # Key selection performance
  if [[ -f "bin/select_or_key.sh" && -f ".env" ]]; then
    log "Benchmarking key selection..."
    local key_start=$(date +%s%N)
    VERBOSE=false bin/select_or_key.sh .env .env.bench 2>/dev/null || true
    local key_end=$(date +%s%N)
    local key_ms=$(( (key_end - key_start) / 1000000 ))
    results+=("\"key_selection_ms\": $key_ms")
    rm -f .env.bench
  fi

  # Diagnostic performance
  if [[ -f "bin/diagnose.sh" ]]; then
    log "Benchmarking diagnostics..."
    local diag_start=$(date +%s%N)
    timeout 60 ./bin/diagnose.sh --auto >/dev/null 2>&1 || true
    local diag_end=$(date +%s%N)
    local diag_ms=$(( (diag_end - diag_start) / 1000000 ))
    results+=("\"diagnostics_ms\": $diag_ms")
  fi

  # Health check performance
  if [[ -f "bin/health_monitor.sh" ]]; then
    log "Benchmarking health check..."
    local health_start=$(date +%s%N)
    timeout 30 ./bin/health_monitor.sh 2>/dev/null || true
    local health_end=$(date +%s%N)
    local health_ms=$(( (health_end - health_start) / 1000000 ))
    results+=("\"health_check_ms\": $health_ms")
  fi

  # System info
  local cpu_count=$(nproc)
  local memory_gb=$(( $(free -m | awk 'NR==2{print $2}') / 1024 ))
  local disk_gb=$(df -BG . | awk 'NR==2{gsub(/G/, "", $2); print $2}')

  # Create benchmark report
  cat > "$output_file" <<JSON
{
  "timestamp": "$(date -Iseconds)",
  "version": "$VERSION",
  "baseline": $baseline_mode,
  "system": {
    "cpu_cores": $cpu_count,
    "memory_gb": $memory_gb,
    "disk_gb": $disk_gb,
    "kernel": "$(uname -r)",
    "load_avg": "$(cat /proc/loadavg | awk '{print $1, $2, $3}')"
  },
  "benchmarks": {
    $(IFS=','; echo "${results[*]}")
  }
}
JSON

  success "Benchmark results saved to: $output_file"

  # Show results
  echo
  echo "Benchmark Results:"
  echo "=================="
  python3 - "$output_file" <<'PY'
import json
import sys

with open(sys.argv[1]) as f:
    data = json.load(f)

benchmarks = data.get('benchmarks', {})
for name, value in benchmarks.items():
    clean_name = name.replace('_', ' ').replace('ms', '').strip()
    if 'ms' in name:
        print(f"{clean_name}: {value}ms")
    else:
        print(f"{clean_name}: {value}")
PY
}

# Create performance baseline
create_baseline() {
  run_benchmarks true
  success "Performance baseline created"
}

# Analyze performance data
analyze_performance() {
  local baseline_file="$BENCHMARK_DIR/baseline.json"
  local latest_file=""

  # Find latest benchmark file
  if [[ -d "$BENCHMARK_DIR" ]]; then
    latest_file=$(find "$BENCHMARK_DIR" -name "benchmark-*.json" -type f | sort | tail -1)
  fi

  if [[ ! -f "$baseline_file" ]]; then
    warn "No baseline found. Run 'benchmark --baseline' first."
    return 1
  fi

  if [[ ! -f "$latest_file" ]]; then
    warn "No recent benchmarks found. Run 'benchmark' first."
    return 1
  fi

  log "Analyzing performance: baseline vs latest"

  python3 - "$baseline_file" "$latest_file" <<'PY'
import json
import sys

def load_benchmark(file_path):
    with open(file_path) as f:
        return json.load(f)

baseline_file = sys.argv[1]
latest_file = sys.argv[2]

baseline = load_benchmark(baseline_file)
latest = load_benchmark(latest_file)

baseline_bench = baseline.get('benchmarks', {})
latest_bench = latest.get('benchmarks', {})

print("Performance Analysis:")
print("====================")
print(f"Baseline: {baseline.get('timestamp', 'Unknown')}")
print(f"Latest:   {latest.get('timestamp', 'Unknown')}")
print()

improvements = []
regressions = []

for metric, latest_value in latest_bench.items():
    if metric in baseline_bench:
        baseline_value = baseline_bench[metric]
        if baseline_value > 0:
            change_percent = ((latest_value - baseline_value) / baseline_value) * 100

            clean_name = metric.replace('_', ' ').replace('ms', '').strip()

            if change_percent > 5:  # Regression
                regressions.append((clean_name, baseline_value, latest_value, change_percent))
                print(f"🔴 {clean_name}: {baseline_value} → {latest_value} (+{change_percent:.1f}%)")
            elif change_percent < -5:  # Improvement
                improvements.append((clean_name, baseline_value, latest_value, change_percent))
                print(f"🟢 {clean_name}: {baseline_value} → {latest_value} ({change_percent:.1f}%)")
            else:
                print(f"⚪ {clean_name}: {baseline_value} → {latest_value} ({change_percent:.1f}%)")

print()
if improvements:
    print("✨ Improvements:")
    for name, old, new, pct in improvements:
        print(f"  • {name}: {abs(pct):.1f}% faster")

if regressions:
    print("⚠️ Regressions:")
    for name, old, new, pct in regressions:
        print(f"  • {name}: {pct:.1f}% slower")

if not improvements and not regressions:
    print("📊 Performance is stable")
PY
}

# Continuous monitoring
monitor_performance() {
  local duration="${1:-300}"
  local interval="${2:-5}"
  local output_file="$PERF_LOG_DIR/monitor-$(date +%Y%m%d-%H%M%S).json"

  log "Starting continuous monitoring (${duration}s duration, ${interval}s interval)"

  local end_time=$(( $(date +%s) + duration ))
  local samples=()

  while [[ $(date +%s) -lt $end_time ]]; do
    local timestamp=$(date +%s)
    local cpu_load=$(cat /proc/loadavg | awk '{print $1}')
    local memory_used=$(free -m | awk 'NR==2{print $3}')
    local disk_io=$(iostat -d 1 1 | awk 'NR==4{print $4}' 2>/dev/null || echo "0")

    samples+=("{\"timestamp\": $timestamp, \"cpu_load\": $cpu_load, \"memory_mb\": $memory_used, \"disk_io\": $disk_io}")

    echo -ne "\rMonitoring... CPU: $cpu_load, Memory: ${memory_used}MB"
    sleep "$interval"
  done

  echo

  # Save monitoring data
  cat > "$output_file" <<JSON
{
  "start_time": "$(date -d "@$((end_time - duration))" -Iseconds)",
  "end_time": "$(date -d "@$end_time" -Iseconds)",
  "duration": $duration,
  "interval": $interval,
  "samples": [
    $(IFS=','; echo "${samples[*]}")
  ]
}
JSON

  success "Monitoring data saved to: $output_file"

  # Show summary statistics
  python3 - "$output_file" <<'PY'
import json
import sys

with open(sys.argv[1]) as f:
    data = json.load(f)

samples = data.get('samples', [])
if not samples:
    print("No monitoring data available")
    sys.exit(1)

cpu_values = [s['cpu_load'] for s in samples]
mem_values = [s['memory_mb'] for s in samples]

print(f"\nMonitoring Summary:")
print(f"==================")
print(f"Samples: {len(samples)}")
print(f"CPU Load - Min: {min(cpu_values):.2f}, Max: {max(cpu_values):.2f}, Avg: {sum(cpu_values)/len(cpu_values):.2f}")
print(f"Memory - Min: {min(mem_values)}MB, Max: {max(mem_values)}MB, Avg: {sum(mem_values)/len(mem_values):.0f}MB")
PY
}

# Generate optimization recommendations
generate_recommendations() {
  log "Analyzing system for optimization opportunities..."

  local recommendations=()

  # Check if baseline exists
  if [[ -f "$BENCHMARK_DIR/baseline.json" ]]; then
    local slow_operations
    slow_operations=$(python3 - "$BENCHMARK_DIR/baseline.json" <<'PY'
import json
import sys

with open(sys.argv[1]) as f:
    data = json.load(f)

benchmarks = data.get('benchmarks', {})
slow_ops = []

for name, value in benchmarks.items():
    if 'ms' in name and value > 5000:  # Slower than 5 seconds
        clean_name = name.replace('_', ' ').replace('ms', '').strip()
        slow_ops.append(f"{clean_name} ({value}ms)")

if slow_ops:
    print("Slow operations detected:")
    for op in slow_ops:
        print(f"  - {op}")
else:
    print("No significantly slow operations detected")
PY
    )

    if [[ "$slow_operations" != "No significantly slow operations detected" ]]; then
      recommendations+=("$slow_operations")
    fi
  fi

  # Check system resources
  local memory_gb=$(( $(free -m | awk 'NR==2{print $2}') / 1024 ))
  local cpu_count=$(nproc)

  if [[ $memory_gb -lt 4 ]]; then
    recommendations+=("Consider increasing system memory (current: ${memory_gb}GB)")
  fi

  if [[ $cpu_count -lt 2 ]]; then
    recommendations+=("Consider using a multi-core system for better performance")
  fi

  # Check for large log files
  local large_logs
  large_logs=$(find . -name "*.log" -size +10M 2>/dev/null | head -5)
  if [[ -n "$large_logs" ]]; then
    recommendations+=("Large log files detected - consider log rotation")
  fi

  # Generate report
  echo
  echo "🚀 Optimization Recommendations:"
  echo "================================"

  if [[ ${#recommendations[@]} -eq 0 ]]; then
    success "System performance looks good! No specific recommendations."
  else
    for rec in "${recommendations[@]}"; do
      echo -e "${YELLOW}💡${NC} $rec"
    done
  fi

  echo
  echo "General Best Practices:"
  echo "• Run diagnostics regularly to catch issues early"
  echo "• Monitor resource usage during peak operations"
  echo "• Keep environment files (.env) small and focused"
  echo "• Use SSD storage for better I/O performance"
  echo "• Consider caching frequently accessed data"
}

# Main command dispatcher
main() {
  setup_monitoring

  local command="${1:-help}"

  case "$command" in
    profile)
      if [[ $# -lt 2 ]]; then
        error "Usage: profile SCRIPT [OUTPUT_FILE]"
        exit 1
      fi
      profile_script "$2" "${3:-}"
      ;;
    benchmark)
      local baseline=false
      shift
      while [[ $# -gt 0 ]]; do
        case $1 in
          --baseline) baseline=true; shift ;;
          *) error "Unknown option: $1"; exit 1 ;;
        esac
      done
      run_benchmarks "$baseline"
      ;;
    analyze)
      analyze_performance
      ;;
    monitor)
      local duration=300
      local interval=5
      shift
      while [[ $# -gt 0 ]]; do
        case $1 in
          --duration) duration="$2"; shift 2 ;;
          --interval) interval="$2"; shift 2 ;;
          *) error "Unknown option: $1"; exit 1 ;;
        esac
      done
      monitor_performance "$duration" "$interval"
      ;;
    optimize)
      generate_recommendations
      ;;
    report)
      # Generate comprehensive performance report
      log "Generating performance report..."
      analyze_performance
      generate_recommendations
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