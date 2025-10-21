# Atlas v2 Deployment Plan: Safe Migration to atlas.khamel.com

## 🎯 **Deployment Goals**

1. **Atlas v2 accessible at `atlas.khamel.com/v2`**
2. **Atlas v1 stays running at `atlas.khamel.com` (unchanged)**
3. **All content preserved and migrated**
4. **Zero downtime for existing services**
5. **Step-by-step hand-holding through deployment**

## 🗺️ **Deployment Strategy**

### **Phase 1: OCI Setup (Safe Sandbox)**
- Deploy Atlas v2 to OCI Always-Free
- Test everything on clean environment
- Verify data migration works perfectly

### **Phase 2: Domain Integration**
- Point `atlas.khamel.com/v2` to OCI instance
- Atlas v1 continues at `atlas.khamel.com`
- Both systems run in parallel

### **Phase 3: Content Migration & Validation**
- Migrate all 25,831 content items to v2
- Validate every piece of content
- Compare v1 vs v2 to ensure nothing lost

### **Phase 4: Gradual Transition (When Ready)**
- Users can access both versions
- Eventually switch primary to v2
- Keep v1 as backup until confident

## 📋 **Step-by-Step Deployment Guide**

### **STEP 1: Get OCI Always-Free Account Ready**

**1.1 Verify OCI Account**
```bash
# Login to Oracle Cloud Console
https://cloud.oracle.com/

# Verify you have Always-Free tier
# Look for: "Always Free Eligible" resources
```

**1.2 Create VM Instance**
```bash
# In OCI Console:
# 1. Go to "Compute" > "Instances"
# 2. Click "Create Instance"
# 3. Choose:
#    - Name: atlas-v2-production
#    - Image: Ubuntu 22.04 (Always Free Eligible)
#    - Shape: VM.Standard.A1.Flex (ARM)
#    - OCPUs: 4 (max for free tier)
#    - Memory: 24GB (max for free tier)
#    - Boot Volume: 200GB (free tier)
# 4. Add your SSH key
# 5. Create
```

**1.3 Configure Security**
```bash
# In OCI Console > Networking > Security Lists
# Add Ingress Rules:
# Port 22 (SSH): 0.0.0.0/0
# Port 80 (HTTP): 0.0.0.0/0
# Port 443 (HTTPS): 0.0.0.0/0
# Port 8000 (Atlas v2): 0.0.0.0/0
```

### **STEP 2: Deploy Atlas v2 to OCI**

**2.1 SSH to OCI Instance**
```bash
# Get public IP from OCI console
ssh -i ~/.ssh/your-oci-key ubuntu@<OCI-PUBLIC-IP>
```

**2.2 Install Dependencies**
```bash
# On OCI instance:
sudo apt update && sudo apt upgrade -y
sudo apt install -y docker.io docker-compose git curl

# Add user to docker group
sudo usermod -aG docker ubuntu
newgrp docker

# Verify Docker works
docker --version
```

**2.3 Deploy Atlas v2**
```bash
# Clone Atlas v2 (you'll need to push to GitHub first)
git clone https://github.com/Khamel83/Atlas.git
cd Atlas/atlas_v2

# Set environment variables
echo "WEBHOOK_SECRET_TOKEN=$(openssl rand -hex 32)" > .env
echo "HOST=0.0.0.0" >> .env
echo "PORT=8000" >> .env

# Build and start
docker-compose up -d

# Verify running
docker logs atlas-v2
curl http://localhost:8000/health
```

### **STEP 3: Configure Domain Routing**

**3.1 Point Subdomain to OCI**
```bash
# In your DNS provider (wherever khamel.com is hosted):
# Add A record:
# Name: v2.atlas
# Value: <OCI-PUBLIC-IP>
# TTL: 300

# Or add subdirectory routing:
# Name: atlas-v2
# Value: <OCI-PUBLIC-IP>
```

**3.2 Setup Reverse Proxy (if needed)**

If `atlas.khamel.com` is currently running on a different server, you'll need to route `/v2` to OCI:

```nginx
# On current atlas.khamel.com server (if using nginx):
# Add to nginx config:

location /v2/ {
    proxy_pass http://<OCI-PUBLIC-IP>:8000/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

# Reload nginx:
sudo nginx -t && sudo nginx -s reload
```

### **STEP 4: Data Migration (Critical)**

**4.1 Backup Current Data**
```bash
# On current Atlas server:
cd /home/ubuntu/dev/atlas

# Create comprehensive backup
mkdir atlas_v1_backup_$(date +%Y%m%d)
cp -r data/ atlas_v1_backup_$(date +%Y%m%d)/
cp -r output/ atlas_v1_backup_$(date +%Y%m%d)/

# Verify backup size
du -sh atlas_v1_backup_*
```

**4.2 Export Data for Migration**
```bash
# Run our migration script (locally first to test):
python3 atlas_v2_migration.py

# This creates:
# - atlas_v2_migration/main_content_export.json (25,831 items)
# - atlas_v2_migration/episode_queue_export.json (5,337 items)
# - atlas_v2_migration/podcast_episodes_export.json (16,936 items)
```

**4.3 Transfer Data to OCI**
```bash
# From local machine:
scp -i ~/.ssh/your-oci-key -r atlas_v2_migration/ ubuntu@<OCI-PUBLIC-IP>:/home/ubuntu/

# SSH to OCI and import:
ssh -i ~/.ssh/your-oci-key ubuntu@<OCI-PUBLIC-IP>
cd Atlas/atlas_v2

# Run migration import (you'll need to create this script)
python3 import_migration_data.py
```

### **STEP 5: Verification & Testing**

**5.1 Test Atlas v2 Endpoints**
```bash
# Health check
curl https://atlas.khamel.com/v2/health

# Stats check
curl https://atlas.khamel.com/v2/stats

# Test webhook
curl -X POST https://atlas.khamel.com/v2/webhook/vejla \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-webhook-token" \
  -d '{"type":"test","url":"https://example.com","source":"Test"}'
```

**5.2 Content Verification**
```bash
# Check that all content migrated
curl https://atlas.khamel.com/v2/stats | jq

# Should show:
# - content_by_type with your expected numbers
# - queue_by_status showing migrated items
```

### **STEP 6: Configure Vejla for Production**

**6.1 Update Vejla Webhook URL**
```json
// In Shortcuts app, update webhook URL from:
"http://localhost:8000/webhook/vejla"

// To:
"https://atlas.khamel.com/v2/webhook/vejla"
```

**6.2 Test End-to-End Flow**
```bash
# Send test URL through Vejla
# Verify it appears in Atlas v2
# Check processing logs
```

## 🛡️ **Data Preservation Guarantees**

### **What We're Preserving**
- ✅ **25,831** total content items
- ✅ **13,209** large content pieces (>10K chars)
- ✅ **9,454** podcast transcripts
- ✅ **1,997** email archives
- ✅ **1,754** articles
- ✅ **5,337** episode queue items
- ✅ **33,303** markdown files
- ✅ **102,009** JSON files

### **Migration Validation Checklist**
```bash
# Before migration
sqlite3 /home/ubuntu/dev/atlas/data/atlas.db "SELECT COUNT(*) FROM content WHERE length(content) > 10000"
# Result: Should be 13,209

# After migration
curl https://atlas.khamel.com/v2/stats | jq '.validation_by_status'
# Should show equivalent numbers
```

### **Rollback Plan**
If anything goes wrong:
1. Atlas v1 continues running unchanged
2. OCI v2 instance can be destroyed and rebuilt
3. All original data remains safe
4. No risk to existing system

## 📊 **Monitoring & Maintenance**

### **Health Monitoring**
```bash
# Daily health check (add to cron):
curl -s https://atlas.khamel.com/v2/health | jq '.status'

# Queue monitoring:
curl -s https://atlas.khamel.com/v2/stats | jq '.queue_by_status'
```

### **Log Monitoring**
```bash
# On OCI instance:
docker logs atlas-v2 --tail 100

# Check for errors:
docker logs atlas-v2 | grep ERROR
```

### **Resource Monitoring**
```bash
# Memory usage:
docker stats atlas-v2

# Should stay under 4GB RAM for OCI Always-Free
```

## 🚀 **Go-Live Checklist**

### **Pre-Deployment**
- [ ] OCI instance created and configured
- [ ] DNS records updated
- [ ] SSL certificates configured (Let's Encrypt)
- [ ] Atlas v2 Docker containers running
- [ ] Health checks passing

### **Migration**
- [ ] All data exported from v1
- [ ] Data imported to v2
- [ ] Content counts verified
- [ ] Sample content spot-checked
- [ ] Queue processing tested

### **Integration**
- [ ] Vejla webhook updated to v2 URL
- [ ] Test URL processing end-to-end
- [ ] Webhook authentication working
- [ ] Processing pipeline verified

### **Production**
- [ ] `atlas.khamel.com/v2` accessible
- [ ] `atlas.khamel.com` (v1) still working
- [ ] Monitoring in place
- [ ] Documentation updated

## 💰 **Cost Verification**

### **OCI Always-Free Resources**
- Compute: 4 ARM cores, 24GB RAM
- Storage: 200GB boot volume
- Network: 10TB egress/month
- **Cost: $0.00/month forever**

### **Atlas v2 Usage**
- RAM: ~2-4GB typical
- CPU: <20% average
- Storage: ~50GB for all content
- Network: <1TB/month
- **All within free tier limits ✅**

## 🆘 **Support & Troubleshooting**

### **Common Issues**

**Domain not resolving:**
```bash
# Check DNS propagation:
dig atlas.khamel.com
nslookup v2.atlas.khamel.com
```

**Container not starting:**
```bash
# Check logs:
docker logs atlas-v2
docker-compose logs

# Check resources:
docker stats
```

**Migration issues:**
```bash
# Check source data:
ls -la atlas_v2_migration/

# Check import logs:
docker logs atlas-v2 | grep migration
```

### **Getting Help**
1. Check Docker logs: `docker logs atlas-v2`
2. Verify health endpoint: `curl /health`
3. Check OCI instance resources in console
4. Review migration export files

---

## 🎯 **Next Actions for You**

1. **Create OCI instance** using specifications above
2. **SSH to OCI** and deploy Atlas v2
3. **Run data migration** to preserve all content
4. **Update DNS** to point atlas.khamel.com/v2 to OCI
5. **Test Vejla integration** with new URL

**This plan gives you a safe, step-by-step path to Atlas v2 while keeping v1 running until you're confident everything works perfectly.**