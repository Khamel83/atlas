# Atlas Complete Data Archive - Import Guide

**Archive Location:** `/Users/khamel83/Desktop/data for atlas/`

## 📁 What's Included

**Complete Atlas System Data:**
- `home/ubuntu/dev/atlas/` - Main Atlas directory (1.9GB)
- `home/ubuntu/dev/atlas-clean/` - Atlas with episode data (2.2GB)
- `home/ubuntu/dev/oos/` - Operational data
- **Total:** 5GB+ uncompressed data

## 🎯 Key Data Files

**Primary Database (2,373 episodes):**
```
home/ubuntu/dev/atlas-clean/data/databases/atlas_content_before_reorg.db
```

**Environment Configuration:**
```
home/ubuntu/dev/atlas/.env
```

**Podcast Configurations:**
```
home/ubuntu/dev/atlas/config/podcast_sources.json
home/ubuntu/dev/atlas/config/podcasts_prioritized.csv
```

**Content Exports:**
```
home/ubuntu/dev/atlas/tools/backup/ (38MB of processed content)
Multiple JSON exports and Instapaper reports
```

## 🚀 Import Instructions

**To migrate to new Atlas system:**

1. **Copy database files:**
   ```bash
   cp home/ubuntu/dev/atlas-clean/data/databases/atlas_content_before_reorg.db /path/to/new/atlas/podcast_processing.db
   ```

2. **Copy environment config:**
   ```bash
   cp home/ubuntu/dev/atlas/.env /path/to/new/atlas/
   ```

3. **Copy configurations:**
   ```bash
   cp -r home/ubuntu/dev/atlas/config/* /path/to/new/atlas/config/
   ```

4. **Copy content exports:**
   ```bash
   cp -r home/ubuntu/dev/atlas/tools/backup/ /path/to/new/atlas/tools/
   ```

## 📊 Data Summary

- **Episodes:** 2,373 records in main database
- **Content:** 38MB of processed content exports
- **Configurations:** Complete podcast sources and RSS feeds
- **Processing logs:** Full history of Atlas operations

## ⚠️ Important Notes

- This is a **complete data snapshot** - all Atlas content preserved
- Database contains episode metadata and processing results
- Content files are in markdown/JSON format in tools/backup/
- Environment file contains API keys and configurations
- Multiple backup databases provide redundancy

**Archive Status:** ✅ Complete and ready for import
**Last Updated:** November 27, 2025
**Archive Size:** 245MB compressed (~5GB uncompressed)

## 🎯 Quick Reference

**Your complete Atlas data is now at:**
```
/Users/khamel83/Desktop/data for atlas/
```

**Main database with episodes:** `home/ubuntu/dev/atlas-clean/data/databases/atlas_content_before_reorg.db` (14MB, 2,373 episodes)

**All configurations:** `home/ubuntu/dev/atlas/config/`

**Content exports:** `home/ubuntu/dev/atlas/tools/backup/` (38MB)

Ready for import into any new Atlas installation!