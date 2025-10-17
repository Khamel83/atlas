# OOS Simplification Plan

## Problem: Overcomplicated Scripts
Many OOS scripts are 500+ lines when they should be 5 lines of "if this then that" logic.

## Current Offenders

| Script | Lines | What it Does | Should Be |
|--------|-------|--------------|-----------|
| `template_manager.sh` | 809 | Copy template files | `cp -r template/ $PROJECT/` |
| `diagnose.sh` | 781 | Check system health | 5 basic checks |
| `performance_monitor.sh` | 549 | System stats | `free -h; df -h; uptime` |
| `security_audit.sh` | 503 | Find security issues | `grep` for secrets |
| `key_rotator.sh` | 485 | Rotate API keys | Simple find/replace |
| `health_monitor.sh` | 472 | Monitor services | `ps` and `curl` checks |

## Simple Replacements Created

✅ `simple_diagnose.sh` (5 lines) vs `diagnose.sh` (781 lines)
✅ `simple_template.sh` (5 lines) vs `template_manager.sh` (809 lines)
✅ `simple_performance.sh` (5 lines) vs `performance_monitor.sh` (549 lines)
✅ `simple_security.sh` (5 lines) vs `security_audit.sh` (503 lines)

## Pattern: Most Scripts Do This
1. Parse 20 command line options (ignored 15 times)
2. Set up colors and logging
3. Write help text (50+ lines)
4. Do the actual work (5-10 lines)
5. Generate reports and summaries

## Solution: "If This Then That" Approach
- Replace coordination with simple conditionals
- Remove unused options and features
- Focus on the 5 lines that matter
- Make scripts do one thing well

## Next Steps
1. Test simple versions work as well as complex ones
2. Replace complex scripts with simple ones
3. Archive old scripts as reference
4. Update any dependencies to use simple versions

## Philosophy
"Perfect is the enemy of good. Simple is better than complex."
- 5 working lines > 500 theoretical lines
- Clear intent > comprehensive features
- Maintainable > feature-complete