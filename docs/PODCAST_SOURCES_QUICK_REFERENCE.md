# Podcast Transcript Sources - Quick Reference

## Free Third-Party Aggregators (Primary Sources)

### 1. PodScripts.co
- **URL**: https://podscripts.co
- **Coverage**: 559,673+ episodes across 300+ podcasts
- **Method**: Static HTML scraping
- **Access**: Free, no authentication
- **Featured Podcasts**: 
  - All-In Podcast
  - Modern Wisdom
  - The Tim Ferriss Show
  - Jordan Peterson Podcast
  - Armchair Expert
  - Joe Rogan Experience (2,000+ episodes)
  - Huberman Lab
  - Stuff You Should Know
  - Knowledge Fight
  - Decoding the Gurus
  - + 20+ more

**Implementation**: Visit `podscripts.co/podcasts/{podcast-slug}` → Parse HTML → Extract transcripts from episode pages

---

### 2. TranscriptForest.com
- **URL**: https://www.transcriptforest.com
- **Coverage**: 73+ podcasts with full transcripts
- **Method**: Static HTML scraping
- **Access**: Free, no authentication
- **Featured Podcasts**:
  - Lex Fridman Podcast
  - Huberman Lab
  - My First Million
  - All-In Podcast
  - Making Sense with Sam Harris
  - Freakonomics
  - How I Built This
  - Masters of Scale
  - The Ezra Klein Show
  - The Tim Ferriss Show
  - This American Life
  - + 20+ more

**Implementation**: Visit `transcriptforest.com/en/channel/{podcast-slug}` → Parse HTML → Extract transcripts

---

### 3. HappyScribe Public Library
- **URL**: https://www.happyscribe.com/public/
- **Coverage**: 15+ podcasts with transcripts
- **Method**: Static HTML/JSON scraping
- **Access**: Free public library (⚠️ may have access restrictions)
- **Featured Podcasts**:
  - The Daily (1,200+ episodes)
  - Making Sense with Sam Harris
  - All-In Podcast
  - The Prof G Pod
  - Pivot
  - TED Radio Hour
  - This American Life
  - + 8+ more

**Implementation**: Visit `podcasts.happyscribe.com/{podcast-slug}` → Handle access restrictions → Parse transcripts

---

### 4. Metacast
- **URL**: https://metacast.app
- **Coverage**: Searchable transcripts for 100+ podcasts
- **Method**: HTML/JSON parsing
- **Access**: Free with search capabilities
- **Features**: Transcripts, summaries, chapters, keyword search

---

### 5. Tapesearch
- **URL**: https://www.tapesearch.com
- **Coverage**: 3 million+ transcripts (largest open database)
- **Method**: Full-text search with timestamp jumping
- **Access**: Free
- **Features**: Search any podcast conversation, instant transcript access

---

## Official Podcast Websites (High Priority)

### Complete Transcript Coverage (95%+)

| Podcast | URL | Episodes | Method | Access |
|---------|-----|----------|--------|--------|
| ATP | https://atp.fm | 700+ | Static HTML | Free |
| Conversations with Tyler | https://conversationswithtyler.com | 250+ | Static HTML | Free |
| Lex Fridman | https://lexfridman.com/transcripts | 500+ | Static HTML | Free |
| EconTalk | https://econtalk.org | 900+ | Static HTML | Free |
| Dwarkesh Podcast | https://www.dwarkesh.com/podcast | 150+ | Official Archive | Free |
| Masters of Scale | https://mastersofscale.com/episodes | 300+ | Official Website | Free |
| Huberman Lab | https://www.hubermanlab.com | 200+ | Official Website | Free |

---

## NPR Network (Standardized Pattern)

**URL Pattern**: `https://www.npr.org/transcripts/{episode-id}`

### Podcasts Following NPR Pattern:
- 99% Invisible (500+ episodes)
- Planet Money (700+ episodes)
- Radiolab (300+ episodes)
- Hidden Brain (200+ episodes)
- Throughline (150+ episodes)
- TED Radio Hour (200+ episodes)
- Fresh Air (400+ episodes)

**Implementation**: 
1. Fetch RSS feed
2. Extract episode ID from URL
3. Construct transcript URL: `npr.org/transcripts/{episode-id}`
4. Scrape transcript page

---

## New York Times Podcasts

| Podcast | Episodes | Official URL | Free Access | Fallback Sources |
|---------|----------|--------------|-------------|------------------|
| The Daily | 1,200+ | nytimes.com/thedaily | Subscription required* | HappyScribe, TranscriptForest, Metacast |
| The Ezra Klein Show | 600+ | nytimes.com/ezra-klein-podcast | Subscription required* | HappyScribe, TranscriptForest |
| Hard Fork | 300+ | nytimes.com/podcasts | Subscription required* | Metacast, PodScribe |

*User has NYT password available per requirements

---

## Podcast-by-Episode Counts

### Large Collections (500+ episodes each)
- Joe Rogan Experience: 2,000+
- This American Life: 700+
- Armchair Expert: 700+
- EconTalk: 900+
- Stuff You Should Know: 800+
- Tim Ferriss Show: 600+
- Jordan Peterson Podcast: 600+
- The Ezra Klein Show: 600+
- This Week in Startups: 600+
- Planet Money: 700+
- Modern Wisdom: 500+
- Lex Fridman Podcast: 500+
- Huberman Lab: 200+

### Medium Collections (200-499 episodes)
- All-In Podcast: 400+
- My First Million: 400+
- Knowledge Fight: 400+
- Freakonomics: 400+
- How I Built This: 300+
- Making Sense with Sam Harris: 300+
- Rotten Mango: 300+
- Odd Lots: 300+
- The Vergecast: 500+
- + 15+ more

---

## Implementation Priority by Ease

### Phase 1: EASY (Official Sites + NPR)
- ATP
- Conversations with Tyler
- Lex Fridman
- EconTalk
- Dwarkesh Podcast
- Masters of Scale
- NPR Network (7 podcasts)

**Expected Episodes**: 3,500+ in ~1 week

---

### Phase 2: EASY-MEDIUM (Aggregators)
- PodScripts.co crawl (15+ podcasts)
- TranscriptForest.com crawl (25+ podcasts)

**Expected Episodes**: 8,000+ in ~1 week

---

### Phase 3: MEDIUM (NYT + Specialty)
- The Daily (HappyScribe fallback)
- The Ezra Klein Show (TranscriptForest)
- Hard Fork (Metacast)
- HappyScribe Library (15 podcasts)
- Remaining research (5-8 podcasts)

**Expected Episodes**: 3,000+ in ~1 week

---

### Phase 4: POLISH & OPTIMIZATION
- Deduplication across sources
- Quality scoring and filtering
- Error handling and retries
- Dashboard and reporting

---

## Key Statistics

```
Total Podcasts to Crawl: 73
Total Episodes (Estimated): 15,000+
Total Transcripts Available: ~14,500 (90% coverage)

Breakdown by Source:
- Official Sites: 1,800 episodes (13%)
- NPR Network: 2,450 episodes (17%)
- PodScripts: 4,000 episodes (28%)
- TranscriptForest: 4,500 episodes (31%)
- NYT/HappyScribe/Other: 1,750 episodes (11%)

Crawl Complexity:
- Easy (30 podcasts): 5-15 min setup each
- Medium (25 podcasts): 30-60 min setup each
- Hard (10-15 podcasts): 1-3 hours setup each
- Impossible (3-5 podcasts): Skip

Total Implementation Time: 160-200 hours
Expected Timeline: 4-5 weeks
Team Size: 1-2 developers
Cost: $0 (all free sources)
```

---

## Access Concerns & Solutions

### Resolved Issues
- ✅ ATP: Direct HTML parsing works
- ✅ Lex Fridman: Official site + PodScripts + TranscriptForest all available
- ✅ EconTalk: Official site with complete transcripts
- ✅ NPR Network: Public transcripts at npr.org/transcripts

### Pending Investigation
- ⚠️ HappyScribe: 403 error in initial test - needs access method research
- ⚠️ Huberman Lab: YouTube fallback available if official source problematic
- ⚠️ Joe Rogan Experience: PodScripts only source, may need proxy if rate limited

### Fallback Options
- **YouTube Transcripts**: Auto-generated captions for most podcasts
- **Secondary Aggregators**: Metacast, Tapesearch, Listen Notes
- **API Fallbacks**: Spotify API, YouTube API (requires keys)

---

## Database Schema (Minimal)

```sql
CREATE TABLE podcasts (
  id INTEGER PRIMARY KEY,
  name TEXT UNIQUE,
  source TEXT,  -- 'official', 'podscripts', 'transcriptforest', etc.
  episodes INTEGER,
  url TEXT,
  enabled BOOLEAN
);

CREATE TABLE transcripts (
  id INTEGER PRIMARY KEY,
  podcast_id INTEGER,
  title TEXT,
  episode_url TEXT,
  transcript_text TEXT,
  source_url TEXT,
  quality_score INTEGER,
  created_at TIMESTAMP,
  FOREIGN KEY(podcast_id) REFERENCES podcasts(id)
);
```

---

## Tools & Libraries Needed

### Core Libraries
```
beautifulsoup4      # HTML parsing
requests            # HTTP requests
feedparser          # RSS parsing
selenium            # Headless browser (if needed)
playwright          # Alternative headless browser
fuzzywuzzy         # Duplicate detection
python-dotenv      # Configuration
```

### Optional Tools
```
yt-dlp             # YouTube fallback
httpx              # Async HTTP
pydantic           # Data validation
sqlalchemy         # ORM
logging            # Built-in
```

---

## Testing Checklist

- [ ] Verify PodScripts.co accessible and scrapeable
- [ ] Verify TranscriptForest.com accessible and scrapeable
- [ ] Test HappyScribe access (resolve 403 error)
- [ ] Test NPR transcript pattern with 99% Invisible
- [ ] Test official site parsing (ATP, Lex, EconTalk)
- [ ] Verify episode counts match estimates
- [ ] Check for rate limiting or robots.txt restrictions
- [ ] Test duplicate detection across sources
- [ ] Validate transcript quality (minimum length, format)

---

## Sources & References

**Official Documentation:**
- [PodScripts.co Podcasts List](https://podscripts.co/podcasts)
- [TranscriptForest.com](https://www.transcriptforest.com)
- [HappyScribe Public Library](https://www.happyscribe.com/public)
- [NPR Transcripts](https://www.npr.org/transcripts/)
- [Dwarkesh Podcast Archive](https://www.dwarkesh.com/podcast/archive)
- [Lex Fridman Transcripts](https://lexfridman.com/category/transcripts/)
- [Huberman Lab Episodes](https://www.hubermanlab.com/all-episodes)

**Aggregator Tools:**
- [Metacast - Podcast Transcripts](https://metacast.app)
- [Tapesearch - Transcript Database](https://www.tapesearch.com)
- [Listen Notes - Podcast Search](https://www.listennotes.com)
- [Podcast Notes](https://podcastnotes.org)

---

**Version:** 1.0  
**Updated:** 2025-12-06  
**Status:** Reference Guide - Ready for Development
