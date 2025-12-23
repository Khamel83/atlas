# ADR-001: WhisperX Process Watchdog

**Date**: 2025-12-23
**Status**: Accepted

## Context

WhisperX running on Mac Mini M4 for local podcast transcription was experiencing hangs where the process would become unresponsive (0% CPU) but not terminate. This caused the queue to stall indefinitely - one incident saw a single file block processing for 9+ hours.

The watcher script (`whisperx_watcher.py`) had a 3-hour subprocess timeout, but Python's `subprocess.run(timeout=...)` doesn't reliably kill processes stuck in certain system calls on macOS.

## Decision

Implement a watchdog thread that monitors the WhisperX subprocess and kills it if:

1. **Low CPU threshold**: CPU usage stays below 5% for 5 consecutive checks (10 minutes total, checked every 2 minutes)
2. **Hard timeout**: Process exceeds 90 minutes for any single file

The watchdog runs as a daemon thread alongside the main transcription process and uses `ps` to monitor CPU usage.

## Rationale

1. **CPU monitoring is more reliable** than output monitoring for detecting hung processes
2. **5-minute grace period** at startup allows for model loading (which shows low CPU initially)
3. **10-minute low-CPU threshold** prevents false positives from brief pauses
4. **90-minute hard timeout** accommodates longest expected podcasts (~2 hours audio)
5. **Daemon thread** ensures watchdog dies with main process

## Consequences

### Positive
- WhisperX queue no longer blocks indefinitely on problem files
- Failed files are marked and skipped, allowing queue to progress
- Watcher auto-recovers without manual intervention
- Reduces need for monitoring/alerting

### Negative
- Some legitimately long transcriptions may be killed (edge case)
- Files that cause hangs will be marked failed (need manual re-queue if important)
- Slightly more complex watcher code

## Alternatives Considered

1. **Output monitoring** - Watch for output from WhisperX. Rejected because WhisperX doesn't produce streaming output.

2. **Memory monitoring** - Track memory growth. Rejected because memory patterns aren't reliable indicators of progress.

3. **Heartbeat file** - Have WhisperX touch a file periodically. Rejected because it requires modifying WhisperX or wrapping it.

4. **External monitoring (systemd)** - Use systemd watchdog. Rejected because WhisperX runs on macOS (uses launchd).

## Implementation

Key changes in `scripts/mac_mini/whisperx_watcher.py`:

```python
class ProcessWatchdog:
    def __init__(self, process, filename: str):
        self.process = process
        self.filename = filename
        self.low_cpu_count = 0
        self.start_time = time.time()
    
    def _watch(self):
        # 5-minute grace period for model loading
        time.sleep(300)
        
        while self.process.poll() is None:
            elapsed = time.time() - self.start_time
            
            # Hard timeout
            if elapsed > MAX_TRANSCRIPTION_TIME:
                self.process.kill()
                return
            
            # CPU check
            cpu = get_process_cpu(self.process.pid)
            if cpu < LOW_CPU_THRESHOLD:
                self.low_cpu_count += 1
                if self.low_cpu_count >= LOW_CPU_STRIKES:
                    self.process.kill()
                    return
            else:
                self.low_cpu_count = 0
            
            time.sleep(WATCHDOG_INTERVAL)
```

Constants:
- `MAX_TRANSCRIPTION_TIME = 5400` (90 minutes)
- `WATCHDOG_INTERVAL = 120` (2 minutes)
- `LOW_CPU_THRESHOLD = 5.0` (5%)
- `LOW_CPU_STRIKES = 5` (5 consecutive low readings)
