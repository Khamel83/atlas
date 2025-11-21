# PODEMOS System Integration Documentation

## Overview

The PODEMOS Personal Podcast Feed System is now fully integrated with the Atlas infrastructure, providing:

- **Real-time Feed Monitoring**: 1-2 minute polling of 191 podcast feeds
- **Ultra-Fast Processing**: 19-minute target from episode release to clean feed
- **Private RSS Hosting**: Authenticated access to ad-free feeds on Oracle OCI
- **Atlas Integration**: Shared processing queue and resource management

## System Architecture

```
┌─────────────────────┐    ┌──────────────────────┐    ┌─────────────────────┐
│   Feed Monitor      │────│   Atlas Processing  │────│   RSS Feed Server   │
│   (podemos_feed_    │    │   Queue (shared)     │    │   (Oracle OCI)      │
│    monitor.py)      │    │                      │    │                      │
└─────────────────────┘    └──────────────────────┘    └─────────────────────┘
           │                           │                           │
           │                           │                           │
           ▼                           ▼                           ▼
┌─────────────────────┐    ┌──────────────────────┐    ┌─────────────────────┐
│  OPML Import        │    │  Mac Mini            │    │  Private Feeds      │
│  (191 feeds)        │    │  Transcription       │    │  (Authenticated)    │
└─────────────────────┘    └──────────────────────┘    └─────────────────────┘
```

## Key Components

### 1. Feed Monitoring (`podemos_feed_monitor.py`)
- **OPML Import**: Loads 191 podcast feeds from Overcast export
- **Real-time Polling**: 1-2 minute intervals for new episodes
- **Immediate Triggering**: Downloads detected within seconds
- **Atlas Queue Integration**: Episodes added to shared processing queue

### 2. Ultra-Fast Processing (`podemos_ultra_fast_processor.py`)
- **whisper.cpp Integration**: Fast transcription (~7 minutes)
- **Multi-Method Ad Detection**: Keywords, silence, timing patterns
- **FFmpeg Audio Cutting**: Removes detected ad segments
- **Target Performance**: 2:01AM release → 2:20AM clean episode

### 3. Private RSS Server (`podemos_rss_server.py`)
- **RSS Generation**: Standards-compliant podcast feeds
- **Authentication System**: Secure token-based access
- **Oracle OCI Hosting**: Scalable cloud deployment
- **Podcast App Compatible**: Works with Overcast, Pocket Casts, etc.

### 4. Atlas Integration (`podemos_atlas_integration.py`)
- **Shared Processing Queue**: Prevents resource conflicts
- **Database Integration**: Clean episodes saved to Atlas
- **Mac Mini Coordination**: Shared transcription resources
- **Unified Monitoring**: Integrated logging and metrics

## Configuration Files

### Core Configuration (`config/podemos_atlas_config.json`)
```json
{
  "integration": {
    "enabled": true,
    "atlas_database_path": "data/atlas.db",
    "processing_queue_shared": true,
    "mac_mini_coordination": true
  },
  "queue_configuration": {
    "podcast_episode_priority": "high",
    "max_concurrent_transcriptions": 2,
    "processing_timeout_minutes": 30
  }
}
```

### Feed Configuration (`config/podemos_feeds.json`)
```json
{
  "feeds": {
    "acquired": {
      "display_name": "Acquired (Ad-Free)",
      "priority": "high",
      "enabled": true
    }
  }
}
```

### Mac Mini Integration (`config/mac_mini.json`)
```json
{
  "enabled": true,
  "host": "mac-mini.local",
  "concurrent_jobs": 2,
  "timeout_minutes": 30,
  "transcription_model": "large-v3"
}
```

## Usage Guide

### 1. Start Real-Time Monitoring
```bash
# Start feed monitoring (runs continuously)
python3 podemos_feed_monitor.py --start-monitoring

# Import OPML feeds
python3 podemos_feed_monitor.py --import-opml inputs/podcasts.opml

# Check status
python3 podemos_feed_monitor.py --status
```

### 2. Process Episodes
```bash
# Process queued episodes with Atlas integration
python3 podemos_atlas_integration.py --process-queue 10

# Check integration status
python3 podemos_atlas_integration.py --status

# Test integration
python3 podemos_atlas_integration.py --test-integration
```

### 3. Deploy RSS Server
```bash
# Create deployment configuration
python3 podemos_rss_server.py --create-deployment-config

# Deploy to Oracle OCI
bash scripts/deploy_oracle_oci.sh

# Generate access token
python3 podemos_rss_server.py --generate-token "acquired" "your_name"
```

## Performance Targets

### Real-Time Processing Pipeline
```
2:00:00 AM - Episode released
2:00:30 AM - Feed monitor detects new episode
2:01:00 AM - Download triggered, added to Atlas queue
2:01:30 AM - Mac Mini transcription starts (whisper.cpp tiny)
2:08:30 AM - Transcription complete (~7 minutes)
2:18:00 AM - Ad detection and audio cutting complete
2:19:00 AM - Clean episode uploaded, RSS feed updated
2:20:00 AM - Private feed available in podcast apps
```

**Total Latency: 20 minutes from release to availability**

### Throughput Capacity
- **Feed Monitoring**: 191 feeds polled every 1-2 minutes
- **Concurrent Processing**: 2 episodes simultaneously (Mac Mini)
- **Daily Capacity**: ~144 episodes processed per day
- **Storage**: Clean episodes stored in Atlas database + cloud hosting

## Integration Benefits

### Atlas Infrastructure Reuse
1. **Shared Processing Queue**: No competing parallel processes
2. **Database Integration**: Clean episodes searchable via Atlas
3. **Bulletproof Process Management**: Memory leak prevention
4. **Configuration System**: Unified .env management
5. **Monitoring Integration**: Grafana dashboards and alerts

### Quality Improvements
1. **Consistent Ad Detection**: Multiple detection methods
2. **Quality Validation**: Atlas content quality system
3. **Error Handling**: Automatic retries and fallback processing
4. **Resource Management**: Shared Mac Mini coordination

### User Experience
1. **Private Feeds**: Personal authentication for RSS access
2. **Mobile Integration**: Works with all podcast apps
3. **Real-Time Updates**: Immediate availability of clean episodes
4. **Quality Search**: Episodes indexed in Atlas search system

## Deployment Architecture

### Oracle OCI Components
```
┌─────────────────────────────────────┐
│           Oracle OCI                │
├─────────────────────────────────────┤
│ Container Instance                  │
│ ├── PODEMOS RSS Server              │
│ ├── Authentication Database         │
│ └── Clean Episode Storage           │
│                                     │
│ Security Group                      │
│ ├── HTTP/HTTPS Access (443, 8080)   │
│ └── Rate Limiting                   │
│                                     │
│ Load Balancer (Optional)            │
│ └── SSL Termination                 │
└─────────────────────────────────────┘
```

### Data Flow
```
Atlas Database (Local) ──┐
                        │
                        ├── Processed Episodes
                        │
                        ▼
              Oracle OCI RSS Server ──── Podcast Apps
                        ▲                (Overcast, etc.)
                        │
                        └── Private Authentication
```

## Monitoring and Maintenance

### Health Checks
```bash
# System status
python3 podemos_atlas_integration.py --status

# Feed monitor health
python3 podemos_feed_monitor.py --health-check

# RSS server status
curl https://your-domain.com:8080/status
```

### Log Files
- **Feed Monitoring**: `data/podemos/feed_monitor.log`
- **Processing**: `data/podemos/processing.log`
- **Integration**: Atlas standard logging
- **RSS Server**: Container logs via OCI

### Maintenance Tasks
1. **Queue Cleanup**: Automatic cleanup of completed items
2. **Storage Management**: Rotation of temporary processing files
3. **Token Management**: Cleanup of expired authentication tokens
4. **Feed Updates**: Periodic OPML reimport for new subscriptions

## Future Enhancements

### Planned Features
1. **Semantic Search**: Integration with Atlas semantic indexing
2. **Speaker Identification**: Automatic speaker diarization
3. **Chapter Markers**: Intelligent episode segmentation
4. **Multi-Language**: Support for non-English podcasts
5. **Mobile App**: Dedicated PODEMOS mobile interface

### Scalability Improvements
1. **Multi-Node Processing**: Distributed Mac Mini cluster
2. **CDN Integration**: Global content delivery network
3. **Advanced Analytics**: Episode consumption metrics
4. **ML-Enhanced Ad Detection**: Improved accuracy with training data

---

## Quick Reference

### Start Complete System
```bash
# 1. Start Atlas services
python atlas_service_manager.py start

# 2. Start PODEMOS monitoring
python3 podemos_feed_monitor.py --start-monitoring

# 3. Deploy RSS server
bash scripts/deploy_oracle_oci.sh

# 4. Generate feed tokens
python3 podemos_rss_server.py --generate-token "podcast_name"
```

### Emergency Procedures
- **Stop Processing**: Kill all podcast processing jobs
- **Clear Queue**: Reset Atlas processing queue
- **Restart Monitoring**: Restart feed monitoring service
- **Token Reset**: Regenerate all RSS feed access tokens

The PODEMOS system is now production-ready with full Atlas integration, providing real-time ad-free podcast processing with enterprise-grade infrastructure.