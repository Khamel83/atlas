# Transcript Resolution Framework

## The Problem

2,368 episodes need transcripts. Each needs a **deterministic path** to completion.

## Core Principle

**Every podcast must have exactly one assigned pathway:**

| Pathway | Automation | Quality | Speed |
|---------|------------|---------|-------|
| WEBSITE | Full | Best | Fast |
| NETWORK | Full | Official | Fast |
| PODSCRIPTS | Full | Good (AI) | Fast |
| YOUTUBE | Full (VPN) | OK | Medium |
| WHISPER | Semi-auto | Variable | Slow |

## Resolution Algorithm

```python
def resolve_pathway(podcast):
    # 1. Already assigned?
    if podcast.has_local_episodes():
        return WHISPER  # Paywalled, already decided

    # 2. Check known sources (highest quality first)
    if podcast.slug in WEBSITE_DIRECT:
        return WEBSITE

    if podcast.rss_domain in ['npr.org', 'prx.org', 'slate.com', 'wnyc.org']:
        return NETWORK

    if podcast.slug in NYT_SHOWS:
        return NYT

    # 3. Check podscripts.co (covers most shows)
    if podscripts_has_podcast(podcast.slug):
        return PODSCRIPTS

    # 4. Check YouTube
    if podcast_has_youtube(podcast.slug):
        return YOUTUBE

    # 5. Fallback
    return WHISPER
```

---

## Current Status by Pathway

### Tier 1: Already Working (just need to run)

| Podcast | Pending | Pathway | Action |
|---------|---------|---------|--------|
| stratechery | 249 | WEBSITE | Run fetch --limit 50 |
| planet-money | 100 | NETWORK | Run fetch (auto) |
| hard-fork | 151 | NYT | Run fetch (auto) |
| acquired | 184 | PODSCRIPTS | Verify, run fetch |
| acq2-by-acquired | 111 | PODSCRIPTS | Verify, run fetch |
| conversations-with-tyler | 274 | WEBSITE | Needs selector config |

### Tier 2: Need Podscripts Verification

These likely work with podscripts, need to verify:

| Podcast | Pending | RSS Source | Check |
|---------|---------|------------|-------|
| the-rewatchables | 100 | Megaphone | `curl podscripts.co/show/the-rewatchables` |
| revisionist-history | 100 | Unknown | `curl podscripts.co/show/revisionist-history` |
| land-of-the-giants | 71 | Megaphone | `curl podscripts.co/show/land-of-the-giants` |
| the-knowledge-project | 99 | Megaphone | `curl podscripts.co/show/the-knowledge-project` |
| econtalk | 20 | Simplecast | `curl podscripts.co/show/econtalk` |

### Tier 3: Confirmed Whisper Path

These require local transcription (paywalled or no source):

| Podcast | Pending | Reason |
|---------|---------|--------|
| dithering | 97 | Paywalled (Daring Fireball) |
| asianometry | 90 | Paywalled (Substack) |
| against-the-rules | 47 | No online source |
| hyperfixed | 33 | Ringer network (no transcripts) |

---

## Implementation: The Pathway Database

Add `pathway` column to podcasts table:

```sql
ALTER TABLE podcasts ADD COLUMN pathway TEXT DEFAULT 'unknown';

-- Values: 'website', 'network', 'nyt', 'podscripts', 'youtube', 'whisper', 'unknown'
```

### Update Script

```python
# scripts/assign_pathways.py

WEBSITE_DIRECT = {
    'stratechery', 'acquired', 'lex-fridman-podcast',
    'conversations-with-tyler'
}

NETWORK = {
    'planet-money', 'the-indicator', 'code-switch', 'throughline',
    'fresh-air', 'hidden-brain', 'ted-radio-hour', 'embedded',
    'how-i-built-this', 'the-npr-politics-podcast'
}

NYT = {'hard-fork', 'the-ezra-klein-show'}

# For unknown, check podscripts.co API
def check_podscripts(slug):
    resp = requests.get(f'https://podscripts.co/show/{slug}')
    return resp.status_code == 200

# Assign pathways
for podcast in get_unknown_podcasts():
    if podcast.slug in WEBSITE_DIRECT:
        set_pathway(podcast, 'website')
    elif podcast.slug in NETWORK:
        set_pathway(podcast, 'network')
    elif podcast.slug in NYT:
        set_pathway(podcast, 'nyt')
    elif check_podscripts(podcast.slug):
        set_pathway(podcast, 'podscripts')
    elif has_local_episodes(podcast):
        set_pathway(podcast, 'whisper')
    else:
        set_pathway(podcast, 'whisper')  # Default fallback
```

---

## Monitoring Dashboard

### Status by Pathway

```bash
# Quick status
sqlite3 data/podcasts/atlas_podcasts.db "
SELECT
    COALESCE(pathway, 'unknown') as path,
    COUNT(DISTINCT podcast_id) as podcasts,
    SUM(CASE WHEN transcript_status='fetched' THEN 1 ELSE 0 END) as done,
    SUM(CASE WHEN transcript_status='unknown' THEN 1 ELSE 0 END) as pending
FROM episodes e
JOIN podcasts p ON e.podcast_id = p.id
GROUP BY pathway"
```

### Expected Output

```
path       | podcasts | done  | pending
-----------+----------+-------+---------
website    |        4 |   350 |     700
network    |       12 | 2,400 |     100
nyt        |        2 |    30 |     160
podscripts |       30 | 1,500 |     500
whisper    |       24 |   250 |     700
unknown    |      120 |    50 |     150
```

---

## Weekly Workflow

### Monday: Check Progress
```bash
./venv/bin/python scripts/atlas_status.py --podcasts
```

### If podcasts stuck:
1. Check pathway assignment
2. Verify source still works
3. Re-assign if needed

### Friday: Review Whisper Queue
```bash
ls data/whisper_queue/audio/ | wc -l      # Pending download
ls data/whisper_queue/transcripts/ | wc -l # Pending import
```

---

## Success Criteria

| Metric | Target | Current |
|--------|--------|---------|
| Pathway assigned | 100% | ~70% |
| Automated path coverage | 85% | ~80% |
| Weekly completion rate | 500 eps | ~200 |
| Time to 100% | 4 weeks | TBD |

---

## Next Actions

1. **Create `scripts/assign_pathways.py`** - One-time pathway assignment
2. **Add pathway column** - Schema migration
3. **Verify podscripts coverage** - Bulk check for unknown podcasts
4. **Update `atlas_status.py`** - Show status by pathway
5. **Document in CLAUDE.md** - Pathway resolution rules
