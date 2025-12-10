# Podcast Transcript Sources - Research Results

## Summary
Searched 40+ podcasts for FREE transcript sources. Results categorized by crawlability.

**Current Status (2025-12-06):** 1,260+ transcripts collected (~152MB)

---

## CRAWL STATUS

| Podcast | Transcripts | Size | Status |
|---------|------------|------|--------|
| Accidental Tech Podcast | 677 | 110MB | ✅ COMPLETE |
| Conversations with Tyler | 273 | 17MB | ✅ COMPLETE |
| Lex Fridman Podcast | 103 | 19MB | ✅ COMPLETE |
| EconTalk | 48 | ~1MB | ✅ COMPLETE (archive page) |
| This American Life | 51 | ~200KB | ✅ COMPLETE |
| Darknet Diaries | 30 | ~140KB | ✅ COMPLETE |
| Ologies | 27 | ~140KB | ✅ COMPLETE |
| Hidden Brain | 21 | ~860KB | ✅ COMPLETE |
| **Dwarkesh Podcast** | 21+ | ~2MB | 🔄 IN PROGRESS (headless browser) |
| Macro Voices | 10 | ~230KB | ✅ COMPLETE |
| Acquired | 5 | ~480KB | ✅ PARTIAL |

---

## TIER 1: OFFICIAL DEDICATED TRANSCRIPT ARCHIVES (Best for Bulk Crawling)

These have dedicated transcript pages that can be bulk crawled:

| Podcast | Source URL | Notes |
|---------|-----------|-------|
| Accidental Tech Podcast | https://catatp.fm/episodes/ | ✅ DONE - 677 transcripts crawled |
| Conversations with Tyler | https://conversationswithtyler.com/episodes/ | ✅ DONE - 273 transcripts crawled |
| Lex Fridman Podcast | https://lexfridman.com/podcast/ | ✅ DONE - 103 transcripts crawled |
| EconTalk | https://www.econlib.org/econtalk-archives-by-date/ | ✅ DONE - 48 transcripts (archive page) |
| Dwarkesh Podcast | https://www.dwarkesh.com/podcast/archive | ⚠️ JavaScript/Substack - needs headless browser |
| This American Life | https://www.thisamericanlife.org/archive | ✅ DONE - 51 transcripts crawled |
| Freakonomics Radio | https://freakonomics.com/series/freakonomics-radio/ | ❌ 403 Forbidden - blocks crawlers |
| People I (Mostly) Admire | https://freakonomics.com/series/people-i-mostly-admire/ | Part of Freakonomics network |
| Tim Ferriss Show | https://tim.blog/transcripts | ⚠️ JavaScript rendered - needs headless browser |
| Sean Carroll Mindscape | https://www.preposterousuniverse.com/podcast-archives/ | ⚠️ JavaScript rendered |
| Darknet Diaries | https://darknetdiaries.com/episode/ | ✅ DONE - 30 transcripts crawled |
| Criminal | https://thisiscriminal.com/ | Transcripts on official site |
| Ologies | https://www.alieward.com/ologies | ✅ DONE - 27 transcripts crawled |
| Macro Voices | https://www.macrovoices.com/podcast-transcripts | ✅ DONE - 10 transcripts crawled |
| Huberman Lab | https://www.hubermantranscripts.com/ | ❌ SITE TAKEN DOWN (RIP 2022-2024) |
| Hidden Brain | https://www.hiddenbrain.org/ | ✅ DONE - 21 transcripts crawled |

---

## TIER 2: NPR NETWORK (Consistent Transcript Pattern)

NPR podcasts have transcripts at: `npr.org/transcripts/{episode_id}`

| Podcast | Archive URL | Notes |
|---------|------------|-------|
| Planet Money | https://www.npr.org/series/94427042/planet-money/archive | NPR transcript pattern |
| Radiolab | https://www.radiolab.org/ | Pattern: /podcast/{name}/transcript |
| Hidden Brain | https://www.hiddenbrain.org/ + NPR archive | Official + NPR transcripts |
| Throughline | https://www.npr.org/programs/ted-radio-hour/archive | NPR transcript pattern |
| TED Radio Hour | https://www.npr.org/programs/ted-radio-hour/archive | NPR transcript pattern |
| How I Built This | https://www.npr.org/series/490248027/how-i-built-this | Some NPR transcripts |
| The Indicator | NPR pattern | Part of Planet Money network |
| NPR Politics Podcast | NPR pattern | Standard NPR transcripts |

---

## TIER 3: VOX MEDIA NETWORK

| Podcast | Source URL | Notes |
|---------|-----------|-------|
| Today, Explained | https://vox.com/today-explained-podcast | Official transcripts |
| The Weeds | https://www.podgist.com/the-weeds/index.html | Third-party archive |
| Decoder | https://theverge.com | Full transcripts on The Verge |
| The Vergecast | Third-party transcripts | Happy Scribe, Podscripts |
| Land of the Giants | Vox pattern | Check Vox.com |

---

## TIER 4: SUBSCRIPTION/PAYWALLED (Stratechery Network)

| Podcast | Source URL | Notes |
|---------|-----------|-------|
| Sharp Tech | https://sharptech.fm/member | Stratechery Plus ($15/mo) |
| Sharp China | Stratechery Plus | Paywalled |
| Dithering | Stratechery Plus | Paywalled |
| Greatest Of All Talk | Stratechery Plus | Paywalled |
| Asianometry | Stratechery Plus | Scripts for paid subscribers |
| Stratechery | stratechery.com | Paid subscription required |
| Exponent | https://exponent.fm/ | Free episodes available |

---

## TIER 5: THIRD-PARTY AGGREGATORS (Free, AI-Generated)

These sites have transcripts but may require crawling multiple sources:

| Aggregator | URL | Coverage |
|------------|-----|----------|
| Podscripts.co | https://podscripts.co/ | No Such Thing As A Fish (642 eps), many others |
| Happy Scribe | https://www.happyscribe.com/public/ | Prof G (507 eps), SYSK, many podcasts |
| Transcript Forest | https://www.transcriptforest.com/ | Reply All, Invest Like the Best, a16z |
| Podgist | https://www.podgist.com/ | The Weeds, Sean Carroll |
| Tapesearch | https://www.tapesearch.com/ | Bloomberg Surveillance, searchable |
| Metacast | https://metacast.app/ | Cortex, No Such Thing As A Fish |
| Listen Notes | https://www.listennotes.com/ | Search + transcripts for many |
| Internet Archive | https://archive.org/ | Reply All full archive, Hello Internet |

---

## TIER 6: SPECIFIC FINDINGS BY PODCAST

### From the 73 Podcast List:

| Podcast | Best Free Source | Crawlable? |
|---------|-----------------|------------|
| 99% Invisible | Pattern: 99percentinvisible.org/transcript | ✅ |
| Acquired | acquired.fm/episodes (some have transcripts) | Partial |
| Against the Rules | podscribe.app (third-party) | Third-party |
| Cortex | metacast.app transcripts | Third-party |
| Ezra Klein Show | NYT subscriber only | ❌ Paywall |
| Hard Fork | Third-party only | Third-party |
| Odd Lots | bloomberg.com/oddlots (some official) | Partial |
| Pivot | podscripts.co (721 episodes) | Third-party |
| Political Gabfest | Slate transcripts (check Slate.com) | Check official |
| Revisionist History | simonsaysai.com/blog (fan transcripts S1-4) | Third-party |
| Sam Harris Making Sense | samharris.org/blog?category=podcast_transcript | Official |
| The Daily | nytimes.com/thedaily + third-party | Partial/Paywall |
| All-In Podcast | No official archive found | Third-party only |
| Prof G | transcriptforest.com, happyscribe.com | Third-party |
| Invest Like the Best | joincolossus.com/episodes (official) | Check official |
| a16z Podcast | transcriptforest.com/en/channel/a16z-podcast | Third-party |
| Hardcore History | happyscribe.com, archive.org | Third-party |
| Stuff You Should Know | iheart auto-transcripts, happyscribe | Third-party |
| Hello Internet | podpedia.org/wiki/Portal:HelloInternet | Fan wiki |
| Omnibus | metacast.app | Third-party |

---

## RECOMMENDED BULK CRAWL PRIORITY

### Phase 1: Already Done ✅
1. ATP (catatp.fm) - 677 transcripts
2. Conversations with Tyler - 273 transcripts

### Phase 2: High-Value Official Archives
3. Lex Fridman - lexfridman.com/category/transcripts/
4. EconTalk - econtalk.org
5. Dwarkesh - dwarkesh.com/podcast/archive
6. This American Life - thisamericanlife.org/archive
7. Freakonomics - freakonomics.com/category/transcripts/
8. Tim Ferriss - tim.blog/transcripts
9. Darknet Diaries - darknetdiaries.com/transcript/
10. Huberman Lab - hubermantranscripts.com

### Phase 3: NPR Network (Similar Pattern)
11. Planet Money
12. Radiolab
13. Hidden Brain
14. Throughline
15. TED Radio Hour

### Phase 4: Third-Party Aggregators
- Crawl podscripts.co for multiple podcasts
- Crawl happyscribe.com/public/ for coverage

---

## SITES TO ADD TO BULK CRAWLER

```python
TRANSCRIPT_SITES = {
    'lexfridman.com': {
        'name': 'Lex Fridman Podcast',
        'index_url': 'https://lexfridman.com/podcast/',
        'transcript_url_pattern': 'https://lexfridman.com/{slug}-transcript/',
        'rate_limit': 1.0,
        'slug': 'lex-fridman-podcast',
    },
    'econtalk.org': {
        'name': 'EconTalk',
        'index_url': 'https://www.econtalk.org/',
        'rate_limit': 1.5,
        'slug': 'econtalk',
    },
    'dwarkesh.com': {
        'name': 'Dwarkesh Podcast',
        'index_url': 'https://www.dwarkesh.com/podcast',
        'rate_limit': 1.0,
        'slug': 'dwarkesh-podcast',
    },
    'freakonomics.com': {
        'name': 'Freakonomics Radio',
        'index_url': 'https://freakonomics.com/series/freakonomics-radio/',
        'rate_limit': 1.5,
        'slug': 'freakonomics-radio',
    },
    'tim.blog': {
        'name': 'Tim Ferriss Show',
        'index_url': 'https://tim.blog/podcast/',
        'rate_limit': 2.0,
        'slug': 'tim-ferriss-show',
    },
    'darknetdiaries.com': {
        'name': 'Darknet Diaries',
        'index_url': 'https://darknetdiaries.com/',
        'transcript_pattern': '/transcript/',
        'rate_limit': 1.0,
        'slug': 'darknet-diaries',
    },
    'hubermantranscripts.com': {
        'name': 'Huberman Lab',
        'index_url': 'https://www.hubermantranscripts.com/',
        'rate_limit': 1.0,
        'slug': 'huberman-lab',
    },
    'preposterousuniverse.com': {
        'name': 'Sean Carroll Mindscape',
        'index_url': 'https://www.preposterousuniverse.com/podcast-archives/',
        'rate_limit': 1.5,
        'slug': 'mindscape',
    },
}
```

---

## NOTES

1. **Third-party services (Happy Scribe, Podscripts, etc.)** use AI transcription - quality varies
2. **NPR podcasts** have most reliable free transcripts via npr.org/transcripts/
3. **Stratechery network** is paywalled but high quality
4. **GitHub repos exist** for Huberman Lab transcripts (prakhar625/huberman-podcasts-transcripts)
5. **Internet Archive** has full podcast archives for Reply All, Hello Internet
6. **Official transcripts** are always higher quality than AI-generated

Generated: 2025-12-06
