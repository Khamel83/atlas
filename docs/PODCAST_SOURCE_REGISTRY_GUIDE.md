# Podcast Sources Registry Guide

## 🚀 Overview

The new **Podcast Sources Registry** replaces hardcoded podcast detection logic with a flexible, configurable system that makes it easy to add new transcript sources.

## 📋 What This Solves

### OLD Problems (Fixed)
- ❌ Hardcoded podcast names in `_is_atp_episode()`, `_is_tal_episode()`, etc.
- ❌ Difficult to add new podcast sources
- ❌ No source performance tracking
- ❌ Manual priority management
- ❌ No centralized configuration

### NEW Solutions
- ✅ **Centralized Registry**: All sources in `config/podcast_sources.json`
- ✅ **Easy Addition**: Add new sources without code changes
- ✅ **Performance Tracking**: Automatic success rate monitoring
- ✅ **Priority Management**: Configurable priority system
- ✅ **Pattern Matching**: Flexible URL and title pattern matching

## 🏗️ System Architecture

### Core Components

1. **`helpers/podcast_source_registry.py`** - Main registry system
2. **`helpers/enhanced_transcript_lookup.py`** - Enhanced lookup using registry
3. **`config/podcast_sources.json`** - Source configurations

### Source Configuration Format

```json
{
  "name": "atp",
  "display_name": "Accidental Tech Podcast",
  "description": "ATP episodes from catatp.fm",
  "url_patterns": ["atp\\.fm", "accidental.*tech", "atp"],
  "title_patterns": ["\\d+:", "Episode \\d+", "ATP \\d+"],
  "scraper_class": "helpers.atp_transcript_scraper.ATPTranscriptScraper",
  "enabled": true,
  "priority": 100,
  "requires_auth": false,
  "success_rate": 0.85
}
```

## 🔄 Migration Guide

### For Developers

#### OLD Way (Hardcoded)
```python
# PROBLEM: Hardcoded logic
def _is_atp_episode(self, podcast_name: str, episode_title: str) -> bool:
    atp_indicators = ['accidental tech podcast', 'atp.fm', 'atp']
    combined_text = f"{podcast_name} {episode_title}".lower()
    return any(indicator in combined_text for indicator in atp_indicators)
```

#### NEW Way (Registry-based)
```python
# SOLUTION: Use registry
from helpers.podcast_source_registry import podcast_source_registry

source = podcast_source_registry.identify_source(podcast_name, episode_title, episode_url)
if source:
    result = podcast_source_registry.get_transcript(podcast_name, episode_title, episode_url)
```

#### Using Enhanced Lookup
```python
# RECOMMENDED: Use enhanced lookup system
from helpers.enhanced_transcript_lookup import EnhancedTranscriptLookup

lookup = EnhancedTranscriptLookup()
result = lookup.lookup_transcript(podcast_name, episode_title, episode_url)
```

### For Existing Code

#### Replace Hardcoded Checks
```python
# OLD
if self._is_atp_episode(podcast_name, episode_title):
    return self._get_atp_transcript(podcast_name, episode_title, episode_url)
elif self._is_tal_episode(podcast_name, episode_title):
    return self._get_tal_transcript(podcast_name, episode_title, episode_url)

# NEW
source = podcast_source_registry.identify_source(podcast_name, episode_title, episode_url)
if source:
    return podcast_source_registry.get_transcript(podcast_name, episode_title, episode_url)
```

## 📊 Managing Sources

### Add New Source
```python
from helpers.podcast_source_registry import PodcastSourceConfig, podcast_source_registry

new_source = PodcastSourceConfig(
    name="huberman",
    display_name="Huberman Lab",
    description="Science podcast with occasional transcripts",
    url_patterns=["hubermanlab\\.com"],
    title_patterns=["Episode \\d+", "Dr\\. Andrew Huberman"],
    scraper_class="helpers.huberman_scraper.HubermanScraper",
    enabled=True,
    priority=70,
    success_rate=0.30
)

podcast_source_registry.add_source(new_source)
```

### Enable/Disable Source
```python
# Enable source
podcast_source_registry.enable_source("huberman")

# Disable source
podcast_source_registry.disable_source("huberman")
```

### Check Source Performance
```python
stats = podcast_source_registry.get_source_stats()
for source_name, stat in stats.items():
    print(f"{stat['display_name']}: {stat['success_rate']:.1%}")
```

## 🧪 Testing Sources

### Test Individual Source
```python
from helpers.podcast_source_registry import podcast_source_registry

# Test specific source
result = podcast_source_registry.test_source(
    "atp",
    "Accidental Tech Podcast",
    "657: Ears Are Weird",
    "https://atp.fm/657"
)

print(f"Success: {result.success}")
print(f"Transcript length: {len(result.transcript)}")
```

### Test Enhanced Lookup
```python
from helpers.enhanced_transcript_lookup import test_enhanced_lookup
test_enhanced_lookup()
```

## 📈 Performance Monitoring

### Automatic Performance Tracking
The system automatically tracks:
- **Success Rate**: Percentage of successful extractions
- **Priority Adjustments**: Automatic priority based on performance
- **Confidence Scores**: Source confidence for each extraction

### Manual Performance Optimization
```python
# Optimize source priorities based on performance
lookup = EnhancedTranscriptLookup()
lookup.optimize_source_performance()
```

## 🛠️ CLI Interface

### List All Sources
```bash
python3 helpers/podcast_source_registry.py --list
```

### Show Statistics
```bash
python3 helpers/podcast_source_registry.py --stats
```

### Enable/Disable Source
```bash
# Enable
python3 helpers/podcast_source_registry.py --enable huberman

# Disable
python3 helpers/podcast_source_registry.py --disable huberman
```

### Test Source
```bash
python3 helpers/podcast_source_registry.py --test atp
```

## 🔧 Configuration Management

### Manual Configuration Edit
```bash
# Edit source configuration
nano config/podcast_sources.json

# Reload registry
python3 -c "
from helpers.podcast_source_registry import podcast_source_registry
podcast_source_registry._load_sources()
"
```

### Configuration Backup
```bash
# Backup current configuration
cp config/podcast_sources.json config/podcast_sources.json.backup

# Restore from backup
cp config/podcast_sources.json.backup config/podcast_sources.json
```

## 🚨 Troubleshooting

### Source Not Identified
**Problem**: Podcast not being recognized by registry
**Solution**:
```python
# Check patterns
source = podcast_source_registry.identify_source(podcast_name, episode_title, episode_url)
if not source:
    print("Try adding more patterns to the source configuration")
```

### Scraper Class Not Found
**Problem**: `ModuleNotFoundError` when trying to load scraper
**Solution**: Check scraper class name in configuration
```python
# Verify scraper exists
try:
    module = __import__("helpers.atp_transcript_scraper", fromlist=["ATPTranscriptScraper"])
    scraper_class = getattr(module, "ATPTranscriptScraper")
    print("✅ Scraper class found")
except Exception as e:
    print(f"❌ Scraper class not found: {e}")
```

### Low Success Rate
**Problem**: Source has low success rate
**Solution**:
```python
# Check and adjust patterns
stats = podcast_source_registry.get_source_stats()
print(f"Current success rate: {stats['atp']['success_rate']:.1%}")

# Consider disabling low-performing sources
if stats['atp']['success_rate'] < 0.2:
    podcast_source_registry.disable_source('atp')
```

## 📋 Best Practices

### 1. Use Enhanced Lookup System
```python
# ✅ RECOMMENDED
from helpers.enhanced_transcript_lookup import EnhancedTranscriptLookup
lookup = EnhancedTranscriptLookup()
result = lookup.lookup_transcript(podcast_name, episode_title, episode_url)

# ❌ AVOID - Old hardcoded system
from helpers.podcast_transcript_lookup import PodcastTranscriptLookup
lookup = PodcastTranscriptLookup()
result = lookup.lookup_transcript(podcast_name, episode_title, episode_url)
```

### 2. Add Multiple Patterns
```python
# Good - multiple matching strategies
url_patterns = ["atp\\.fm", "accidental.*tech", "atp"]
title_patterns = ["\\d+:", "Episode \\d+", "ATP \\d+"]
```

### 3. Monitor Performance
```python
# Regular performance checks
stats = lookup.get_source_statistics()
for source_name, stat in stats["registry_stats"].items():
    if stat["success_rate"] < 0.3:
        print(f"⚠️  {source_name} has low success rate: {stat['success_rate']:.1%}")
```

### 4. Use Appropriate Priorities
```python
# High priority (100-90): Reliable sources with good transcripts
# Medium priority (80-70): Sources with occasional transcripts
# Low priority (60-50): Experimental or unreliable sources
```

## 🎯 Current Sources

| Source | Priority | Success Rate | Status |
|--------|----------|--------------|--------|
| Accidental Tech Podcast | 100 | 86.5% | ✅ Enabled |
| This American Life | 90 | 67.5% | ✅ Enabled |
| 99% Invisible | 80 | 70.0% | ✅ Enabled |
| Huberman Lab | 70 | 30.0% | 🚫 Disabled |
| Lex Fridman Podcast | 60 | 25.0% | 🚫 Disabled |

---

**Next Steps**:
1. ✅ Registry system deployed
2. ✅ Enhanced lookup system ready
3. 🔄 Gradually migrate existing code to use new system
4. 📊 Monitor source performance and optimize configurations

**Status**: ✅ PRODUCTION READY