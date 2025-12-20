# Link Discovery v1 - Archived 2024-12-20

## Why Archived

The v1 link extractor was too aggressive:
- Extracted ALL URLs from HTML including navigation, sidebars, footers
- 149k links accumulated, most were noise
- 58k approved (quality domains), 68k pending (ambiguous), 13k rejected

## What Was Intended

- Podcast: Extract links from show notes ("here's the article we mentioned")
- Articles: Extract cited/referenced articles from main content only
- One level deep discovery, not recreating the entire internet

## What Needs to Change for v2

1. **Podcast links** - Extract only from RSS `<description>` (show notes), not transcript body
2. **Article links** - Parse HTML properly, extract only from `<article>` or main content area
3. **Context scoring** - Links with context ("read more", "according to", "reported by") score higher
4. **Dedup against existing content** - Don't queue URLs we already have

## Files

- `link_queue.db` - SQLite with 149k extracted links
  - 58,712 approved (NPR, archive.org, PubMed, NYT, Substack, etc.)
  - 68,813 pending (ambiguous domains)
  - 13,133 rejected (CDNs, social, etc.)
  - 8,530 ingested (already sent to URL queue)

## To Resume Later

```bash
# Restore the database
cp data/archive/link_discovery_v1/link_queue.db data/enrich/

# Re-enable the pipeline (after fixing the extractor)
sudo systemctl enable --now atlas-link-pipeline.timer
```

## Related Files

- `modules/links/` - Link extraction and approval code
- `modules/enrich/link_extractor.py` - The extractor that needs redesign
- `config/link_approval_rules.yml` - Whitelist/blacklist (this was working correctly)
