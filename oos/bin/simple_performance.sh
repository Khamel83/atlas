#!/bin/bash
# Simple Performance Monitor - 5 lines instead of 549

echo "💻 System Performance"
free -h | grep Mem
df -h . | tail -1
ps aux | head -1; ps aux | sort -nr -k 3 | head -3
uptime