# 📧 Email-to-Atlas Setup Guide

**Complete step-by-step instructions to set up phone email → Atlas URL ingestion**

## 🎯 What This Does

Transform your phone's share sheet into a direct Atlas ingestion pipeline:

1. **Find article** in Safari/any app
2. **Share** → **Email**
3. **Send to:** `ingest@atlas.khamel.com`
4. **Done** - URL automatically appears in Atlas database

## 🚀 Quick Start Status Check

✅ **Email server** - Running on your OCI VM
✅ **URL extraction** - Working
✅ **Atlas integration** - URLs stored in database
✅ **Local testing** - 100% confirmed working
⚠️ **External access** - Needs OCI security group configuration

## 📋 Prerequisites

- OCI Free Tier VM (already have)
- Domain name (atlas.khamel.com - already configured)
- Atlas v3 running (already installed)

## 🔧 Services Overview

| Service | Port | Status | Purpose |
|---------|------|--------|---------|
| Atlas v3 | 35555 | ✅ Running | URL ingestion API |
| Email Bridge | 2525 | ✅ Running | Email → Atlas converter |
| Port Forward | 587→2525 | ✅ Configured | External email access |

## 🛠️ Installation Steps

### Step 1: Verify Current Installation

Check that all services are running:

```bash
# Check Atlas v3
sudo systemctl status atlas-v3.service

# Check Email bridge
sudo systemctl status email-atlas-bridge.service

# Check port forwarding
sudo iptables -t nat -L PREROUTING -n | grep 587
```

**Expected output**: All services should show `Active: active (running)`

### Step 2: Test Local Email Processing

```bash
# Test the complete pipeline locally
python3 -c "
import smtplib
from email.mime.text import MIMEText
import time

timestamp = int(time.time())
msg = MIMEText(f'Test URL: https://test-{timestamp}.com')
msg['Subject'] = 'Test Email'
msg['From'] = 'test@example.com'
msg['To'] = 'ingest@atlas.khamel.com'

server = smtplib.SMTP('localhost', 2525)
server.sendmail('test@example.com', ['ingest@atlas.khamel.com'], msg.as_string())
server.quit()
print(f'✅ Test email sent: https://test-{timestamp}.com')
"
```

### Step 3: Verify URL in Atlas Database

```bash
# Check that the URL was stored in Atlas
python3 -c "
import sqlite3
conn = sqlite3.connect('data/atlas_v3.db')
cursor = conn.cursor()
cursor.execute('SELECT url, created_at FROM ingested_urls ORDER BY created_at DESC LIMIT 1')
result = cursor.fetchone()
conn.close()
if result:
    print(f'✅ Latest URL: {result[0]} at {result[1]}')
else:
    print('❌ No URLs found')
"
```

## 🌐 Configure External Access

### Step 4: Open OCI Security Group (Required)

1. **Go to Oracle Cloud Console**
2. **Navigate to:** Compute → Instances → Your Instance
3. **Click:** Virtual Cloud Network name
4. **Click:** Security Lists → Default Security List
5. **Click:** Add Ingress Rules
6. **Configure:**
   - Source Type: `CIDR`
   - Source CIDR: `0.0.0.0/0`
   - IP Protocol: `TCP`
   - Destination Port Range: `587`
   - Description: `Email submission for Atlas`
7. **Click:** Add Ingress Rule

### Step 5: Test External Email Access

```bash
# Test external email access (run this after OCI config)
timeout 30s python3 -c "
import smtplib
from email.mime.text import MIMEText
import time

timestamp = int(time.time())
msg = MIMEText(f'External test: https://external-test-{timestamp}.com')
msg['Subject'] = 'External Test'
msg['From'] = 'phone@example.com'
msg['To'] = 'ingest@atlas.khamel.com'

try:
    server = smtplib.SMTP('atlas.khamel.com', 587)
    server.sendmail('phone@example.com', ['ingest@atlas.khamel.com'], msg.as_string())
    server.quit()
    print(f'✅ External email works: https://external-test-{timestamp}.com')
except Exception as e:
    print(f'❌ External email failed: {e}')
"
```

## 📱 Phone Setup

### Step 6: Configure Phone Email

1. **Add contact:** `ingest@atlas.khamel.com`
2. **Test email:**
   - Open any app with a URL
   - Tap **Share**
   - Choose **Email**
   - Send to `ingest@atlas.khamel.com`
   - Subject/body doesn't matter - just include the URL

### Step 7: Verify Phone Integration

Check Atlas database after sending from phone:

```bash
# Check for your phone's email
python3 -c "
import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('data/atlas_v3.db')
cursor = conn.cursor()

# Get URLs from last 10 minutes
recent = (datetime.now() - timedelta(minutes=10)).isoformat()
cursor.execute('SELECT url, created_at FROM ingested_urls WHERE created_at > ? ORDER BY created_at DESC', (recent,))
results = cursor.fetchall()
conn.close()

if results:
    print('📧 Recent URLs from email:')
    for url, created_at in results:
        print(f'  {created_at}: {url}')
else:
    print('❌ No recent URLs found')
"
```

## 🔍 Troubleshooting

### Issue: External emails not working

**Check OCI security group:**
```bash
# Test if port 587 is accessible
nc -zv atlas.khamel.com 587
```

**Check service logs:**
```bash
# Email bridge logs
tail -f /tmp/email_bridge_service.log

# Atlas v3 logs
sudo journalctl -u atlas-v3.service -f
```

### Issue: URLs not appearing in Atlas

**Check email processing:**
```bash
# Look for email processing in logs
grep "📧 Received email" /tmp/email_bridge_service.log
grep "✅ Email→Atlas" /tmp/email_bridge_service.log
```

**Manual database check:**
```bash
# Check database directly
sqlite3 data/atlas_v3.db "SELECT COUNT(*) FROM ingested_urls;"
sqlite3 data/atlas_v3.db "SELECT url, created_at FROM ingested_urls ORDER BY created_at DESC LIMIT 5;"
```

### Issue: Services not running

**Restart all services:**
```bash
sudo systemctl restart atlas-v3.service
sudo systemctl restart email-atlas-bridge.service
```

**Check service status:**
```bash
sudo systemctl status atlas-v3.service email-atlas-bridge.service
```

## 📊 Service Management

### Start/Stop Services

```bash
# Stop services
sudo systemctl stop email-atlas-bridge.service atlas-v3.service

# Start services
sudo systemctl start atlas-v3.service email-atlas-bridge.service

# Restart services
sudo systemctl restart atlas-v3.service email-atlas-bridge.service
```

### View Logs

```bash
# Real-time email bridge logs
tail -f /tmp/email_bridge_service.log

# Real-time Atlas logs
sudo journalctl -u atlas-v3.service -f

# Service status
sudo systemctl status email-atlas-bridge.service atlas-v3.service
```

## 🔒 Security Notes

- **Port 587** is used instead of 25 (many ISPs block port 25)
- **No authentication** required for `ingest@atlas.khamel.com` (internal use only)
- **Firewall** configured to only allow necessary ports
- **OCI Free Tier** - no additional costs

## 📈 Resource Usage

- **Email service**: ~20MB RAM
- **Atlas v3**: ~10MB RAM
- **Total**: <50MB RAM, <1% CPU
- **Well within OCI Free Tier limits**

## ✅ Success Criteria

**You'll know it's working when:**

1. ✅ Local email test succeeds
2. ✅ External email test succeeds (after OCI config)
3. ✅ Phone email shows up in Atlas database
4. ✅ URLs are accessible in Atlas interface

## 🎯 Your Workflow

**Final phone workflow:**
1. **Find article** in Safari/any app
2. **Tap Share**
3. **Choose Email**
4. **Send to** `ingest@atlas.khamel.com`
5. **URL appears in Atlas automatically** 🎉

---

## 🔧 File Locations

| File | Location | Purpose |
|------|----------|---------|
| Email server | `/home/ubuntu/dev/atlas/email_atlas_bridge.py` | Main email processor |
| Email service | `/etc/systemd/system/email-atlas-bridge.service` | Service definition |
| Atlas v3 | `/home/ubuntu/dev/atlas/atlas_v3.py` | URL ingestion API |
| Atlas service | `/etc/systemd/system/atlas-v3.service` | Service definition |
| Environment | `/home/ubuntu/dev/atlas/.env` | Configuration |
| Database | `/home/ubuntu/dev/atlas/data/atlas_v3.db` | URL storage |

---

**Created:** October 7, 2025
**Status:** Core system complete, needs OCI security group configuration
**Project:** Email-to-Atlas Integration