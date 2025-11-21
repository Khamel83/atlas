# Atlas API Key Management Guide

## 🚨 PROBLEM SOLVED: No More Unauthorized API Usage

### **The Issue (Fixed)**
- **Distributed global instances** cached API keys at import time
- **No single point of control** for API authorization
- **Environment variable changes** were ignored after initialization
- **Immediate revocation** was impossible

### **The Solution: Centralized API Management**
- **Single point of control** via `helpers.api_manager`
- **Permission checking BEFORE every API call**
- **No caching of API keys** or permissions
- **Immediate revocation capability**

---

## 🔧 **NEW API Management System**

### **Core Components**

1. **`helpers/api_manager.py`** - SINGLE POINT OF CONTROL
   - Centralized API permission checking
   - 1Password integration
   - Service authorization management
   - No global instances

2. **`helpers/podcast_transcript_lookup_v2.py`** - NEW Transcript System
   - Uses centralized API manager
   - No unauthorized API usage
   - Always checks permissions first

### **Service Authorization**

#### **Expensive Services (Require Authorization)**
- **Google Search API** (high cost)
- **OpenAI API** (premium cost)
- **Anthropic API** (premium cost)

#### **Low-Cost Services**
- **YouTube API** (low cost, high quota)

---

## 📋 **API Management Commands**

### **Check All Services**
```bash
python3 -c "
from helpers.api_manager import api_manager
services = api_manager.list_all_services()
for name, info in services.items():
    status = '✅' if info['status'] == 'enabled' else '🚫'
    print(f'{status} {name}: {info[\"status\"]} ({info[\"cost_level\"]})')
"
```

### **Enable a Service**
```bash
python3 -c "
from helpers.api_manager import api_manager
api_manager.enable_service('google_search', 'Testing transcript search')
"
```

### **Disable a Service**
```bash
python3 -c "
from helpers.api_manager import api_manager
api_manager.disable_service('google_search', 'Cost control')
"
```

### **Disable All Expensive Services**
```bash
python3 -c "
from helpers.api_manager import api_manager
api_manager.disable_all_expensive_services()
"
```

### **Clear Permission Cache**
```bash
python3 -c "
from helpers.api_manager import api_manager
api_manager._clear_permission_cache()
"
```

---

## 🔒 **How It Works**

### **Permission Checking Flow**
1. **Check Authorization File** (`config/{service}_enabled`)
2. **Load Credentials** from 1Password (if configured)
3. **Check API Keys** availability
4. **Grant/Deny** based on configuration

### **Runtime Authorization**
```python
from helpers.api_manager import api_manager

# Check permission BEFORE using any API
status = api_manager.check_service_permission("google_search")
if status.value == "enabled":
    # Use the API
    credentials = api_manager.get_service_credentials("google_search")
    # ... make API calls
else:
    # Skip or use fallback
    pass
```

---

## 🚀 **Migration Guide**

### **For Developers**

#### **OLD Way (Distributed, Problematic)**
```python
# PROBLEM: Global instance caches API keys at import time
from helpers.google_search_fallback import get_google_search_fallback
google = get_google_search_fallback()  # Caches keys forever
```

#### **NEW Way (Centralized, Secure)**
```python
# SOLUTION: Always check permissions first
from helpers.api_manager import api_manager

status = api_manager.check_service_permission("google_search")
if status.value == "enabled":
    credentials = api_manager.get_service_credentials("google_search")
    # Use API temporarily
```

### **For Transcript Lookup**

#### **OLD System (Avoid)**
```python
from helpers.podcast_transcript_lookup import PodcastTranscriptLookup  # Uses cached instances
```

#### **NEW System (Use This)**
```python
from helpers.podcast_transcript_lookup_v2 import PodcastTranscriptLookupV2  # Uses centralized manager
lookup = PodcastTranscriptLookupV2()
result = lookup.lookup_transcript("Podcast", "Episode")
```

---

## 🛡️ **Security Features**

### **1. No Global Caching**
- API keys are loaded fresh for each operation
- Permission cache expires after 60 seconds
- Immediate revocation capability

### **2. 1Password Integration**
- Secure credential storage
- Automatic loading when needed
- No environment variable pollution

### **3. Authorization Files**
- Explicit approval required for expensive services
- Audit trail of enable/disable actions
- Reason tracking for compliance

### **4. Runtime Checks**
- Permissions checked BEFORE every API call
- Environment isolation during API operations
- Automatic cleanup after use

---

## 📊 **Monitoring and Auditing**

### **Check Current Status**
```bash
# Show all service status
python3 helpers/api_manager.py --list

# Check specific service
python3 -c "
from helpers.api_manager import api_manager
print(api_manager.get_service_status('google_search'))
"
```

### **Audit Trail**
```bash
# Check authorization files
ls -la /home/ubuntu/dev/atlas/config/*_enabled

# View authorization reasons
cat /home/ubuntu/dev/atlas/config/google_search_enabled
```

### **Usage Monitoring**
```bash
# View API permission logs
tail -f /home/ubuntu/dev/atlas/logs/api_permissions.log
```

---

## 🎯 **Best Practices**

### **1. Always Use Centralized Manager**
```python
# ✅ DO - Use centralized manager
from helpers.api_manager import api_manager

# ❌ DON'T - Use old global instances
from helpers.google_search_fallback import get_google_search_fallback
```

### **2. Check Permissions Before Using APIs**
```python
# ✅ DO - Check first
status = api_manager.check_service_permission("google_search")
if status.value == "enabled":
    # Use API

# ❌ DON'T - Assume API is available
```

### **3. Use New Transcript System**
```python
# ✅ DO - Use v2 system
from helpers.podcast_transcript_lookup_v2 import PodcastTranscriptLookupV2

# ❌ DON'T - Use old system
from helpers.podcast_transcript_lookup import PodcastTranscriptLookup
```

---

## 🔧 **Setup and Configuration**

### **1. Initialize 1Password Integration**
```bash
python3 scripts/setup_1password_integration.py
```

### **2. Disable All Expensive Services**
```bash
python3 -c "
from helpers.api_manager import api_manager
api_manager.disable_all_expensive_services()
"
```

### **3. Create Authorization Files (When Needed)**
```bash
# Enable Google Search for testing
echo "Testing transcript search" > config/google_search_enabled

# Enable OpenAI for specific task
echo "Content summarization experiment" > config/openai_enabled
```

### **4. Set Up Monitoring**
```bash
# Add cron job for permission checking
echo "0 */6 * * * cd /home/ubuntu/dev/atlas && python3 scripts/check_api_permissions.py >> logs/api_permissions.log 2>&1" | crontab -
```

---

## 🚨 **Emergency Procedures**

### **Immediately Disable All Expensive APIs**
```bash
python3 -c "
from helpers.api_manager import api_manager
api_manager.disable_all_expensive_services()
api_manager._clear_permission_cache()
print('🚨 All expensive APIs disabled immediately!')
"
```

### **Check for Unauthorized Usage**
```bash
python3 scripts/check_api_permissions.py
```

### **Clear All Caches**
```bash
python3 -c "
from helpers.api_manager import api_manager
api_manager._clear_permission_cache()
print('🧹 All permission caches cleared!')
"
```

---

## ✅ **Verification**

### **Test That APIs Are Properly Controlled**
```bash
python3 -c "
# Test 1: Check Google Search is disabled
from helpers.api_manager import api_manager
status = api_manager.check_service_permission('google_search')
print(f'Google Search status: {status.value}')

# Test 2: Try using transcript lookup without Google
from helpers.podcast_transcript_lookup_v2 import PodcastTranscriptLookupV2
lookup = PodcastTranscriptLookupV2()
result = lookup.lookup_transcript('Accidental Tech Podcast', '657: Ears Are Weird')
print(f'Transcript lookup success: {result.success}')
print(f'Source: {result.source}')  # Should be 'atp_scraper', not 'google_search'
"
```

### **Expected Results**
- Google Search status: `disabled`
- Transcript lookup success: `True`
- Source: `atp_scraper` (direct scraper, not Google fallback)

---

## 🎉 **SUCCESS!**

**Problem Solved**: Atlas now has a **single point of control** for all API usage with:
- ✅ **No unauthorized API charges**
- ✅ **Immediate revocation capability**
- ✅ **Centralized permission management**
- ✅ **1Password integration for security**
- ✅ **Comprehensive audit trail**

**Bottom Line**: You now have complete control over API usage with no more surprise charges or cached credentials!

---
**Last Updated**: 2025-09-28
**Status**: ✅ PRODUCTION READY