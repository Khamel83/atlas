# Atlas Resource Policy

**Last Updated:** December 2025

## The Problem We Solved

Atlas had 7+ systemd services running simultaneously, each spawning their own Playwright browsers:
- `atlas-daemon.service` (the master)
- `atlas-content-retry.service`
- `atlas-continuous-fetcher.service`
- `atlas-simple-fetcher.service`
- `atlas-url-fetcher.service`
- `atlas-transcripts.service`
- `atlas-backlog-fetcher.service`

On a 4-core machine, this caused:
- Load averages of 13-15 (3x overloaded)
- 5GB+ swap usage
- DNS timeouts (Pi-hole couldn't respond)
- General system instability

## The Solution: One Daemon to Rule Them All

**ONLY `atlas-daemon.service` should run for content ingestion.**

The daemon handles ALL content types:
- URLs
- Podcasts
- Transcripts
- Retries

### Allowed Services

| Service | Purpose | Auto-start |
|---------|---------|------------|
| `atlas-daemon.service` | Master content ingestion | YES |
| `atlas-api.service` | API server (optional) | NO |
| `atlas-backup.service` | Database backups | Timer only |

### Prohibited Services (DO NOT ENABLE)

These are **redundant** - the daemon does their job:
- `atlas-content-retry.service`
- `atlas-continuous-fetcher.service`
- `atlas-simple-fetcher.service`
- `atlas-url-fetcher.service`
- `atlas-transcripts.service`
- `atlas-backlog-fetcher.service`

## Browser Concurrency Limit

**Maximum 1 browser instance at a time.**

This is enforced in `modules/browser/headless.py` via a global semaphore.

## CPU/Memory Limits

The daemon service includes resource limits:
```ini
CPUQuota=50%
MemoryMax=2G
Nice=10
```

## Enforcement

### Automatic (on boot)
The lockdown script runs automatically via `cron @reboot`:
```bash
@reboot /home/khamel83/github/atlas/systemd/lockdown.sh
```

### Manual
```bash
./systemd/lockdown.sh
```

This script:
1. Kills any atlas Python process not managed by systemd
2. Starts the daemon if not running
3. Reports current resource usage
4. Logs to `/tmp/atlas-lockdown.log`

### Script Guard
`atlas_daemon.py` refuses to run unless invoked by systemd:
```python
if os.environ.get('INVOCATION_ID') is None:
    sys.exit(1)  # Must run via systemd
```

### Archived Scripts
The following scripts were moved to `scripts/.archive/` as they bypass resource limits:
- `simple_url_fetcher.py`
- `simple_transcript_fetcher.py`

**DO NOT restore these.** The daemon handles all their functions.

## If You're Tempted to Add Another Service

**DON'T.**

Instead:
1. Add the task type to `atlas_daemon.py`
2. Add it to the manifest system
3. Let the daemon handle it sequentially

The whole point is **controlled, sequential processing** - not parallel chaos.

## Quick Commands

```bash
# Check what's running
systemctl list-units --type=service | grep atlas

# Stop everything except daemon
./systemd/lockdown.sh

# Check resource usage
systemctl status atlas-daemon.service
```

## History

- **Dec 2025:** Discovered 7 services running, load avg 14, system unusable
- **Dec 2025:** Consolidated to single daemon, load dropped to 4
- **Dec 2025:** Added this policy and lockdown script
- **Dec 25, 2025:** Added systemd guard to daemon, archived rogue scripts, auto-lockdown on boot
