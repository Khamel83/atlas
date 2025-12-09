#!/usr/bin/env python3
"""
Podcast Registry - Master list of 73 podcasts with transcript sources

This is the single source of truth for all podcasts we want to crawl.
Each podcast specifies its available sources in priority order.
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


class CrawlMethod(Enum):
    """Available crawl methods"""
    OFFICIAL_SITE = "official_site"      # Direct from official website
    BULK_CRAWLER = "bulk_crawler"        # Uses bulk_crawler.py
    HEADLESS = "headless"                # Uses headless_crawler.py (JS-rendered)
    PODSCRIPTS = "podscripts"            # podscripts.co aggregator
    TRANSCRIPT_FOREST = "transcript_forest"  # transcriptforest.com
    NPR_PATTERN = "npr_pattern"          # NPR network transcript pattern
    NYT = "nyt"                          # NYT official (requires login)
    YOUTUBE = "youtube"                  # YouTube auto-captions fallback
    SKIP = "skip"                        # No source available


class CrawlStatus(Enum):
    """Status of each podcast"""
    COMPLETE = "complete"      # Done crawling
    IN_PROGRESS = "in_progress"  # Currently being crawled
    READY = "ready"            # Has source, ready to crawl
    NEEDS_RESEARCH = "needs_research"  # Source not yet identified
    PAYWALLED = "paywalled"    # No free source available


@dataclass
class TranscriptSource:
    """A source for podcast transcripts"""
    method: CrawlMethod
    url: str = ""
    slug: str = ""  # Key for crawler configs
    notes: str = ""
    headless_required: bool = False


@dataclass
class Podcast:
    """A podcast in the registry"""
    name: str
    slug: str
    category: str
    estimated_episodes: int
    status: CrawlStatus
    sources: List[TranscriptSource] = field(default_factory=list)
    notes: str = ""

    @property
    def primary_source(self) -> Optional[TranscriptSource]:
        """Get the first/best available source"""
        return self.sources[0] if self.sources else None


# =============================================================================
# MASTER PODCAST REGISTRY - 73 PODCASTS
# =============================================================================

PODCASTS: Dict[str, Podcast] = {

    # =========================================================================
    # CATEGORY A: COMPLETED (4 podcasts)
    # =========================================================================

    "atp": Podcast(
        name="Accidental Tech Podcast",
        slug="accidental-tech-podcast",
        category="completed",
        estimated_episodes=700,
        status=CrawlStatus.COMPLETE,
        sources=[
            TranscriptSource(CrawlMethod.BULK_CRAWLER, slug="catatp.fm"),
        ],
        notes="677 transcripts downloaded"
    ),

    "conversations-with-tyler": Podcast(
        name="Conversations with Tyler",
        slug="conversations-with-tyler",
        category="completed",
        estimated_episodes=273,
        status=CrawlStatus.COMPLETE,
        sources=[
            TranscriptSource(CrawlMethod.BULK_CRAWLER, slug="conversationswithtyler.com"),
        ],
        notes="273 transcripts downloaded"
    ),

    "lex-fridman": Podcast(
        name="Lex Fridman Podcast",
        slug="lex-fridman-podcast",
        category="completed",
        estimated_episodes=500,
        status=CrawlStatus.COMPLETE,
        sources=[
            TranscriptSource(CrawlMethod.BULK_CRAWLER, slug="lexfridman.com"),
            TranscriptSource(CrawlMethod.PODSCRIPTS, slug="lex-fridman-podcast"),
            TranscriptSource(CrawlMethod.TRANSCRIPT_FOREST, slug="lex-fridman"),
        ],
        notes="103 transcripts downloaded"
    ),

    "econtalk": Podcast(
        name="EconTalk",
        slug="econtalk",
        category="completed",
        estimated_episodes=900,
        status=CrawlStatus.COMPLETE,
        sources=[
            TranscriptSource(CrawlMethod.BULK_CRAWLER, slug="econtalk.org"),
        ],
        notes="48 transcripts from archive page"
    ),

    # =========================================================================
    # CATEGORY B: IN PROGRESS (2 podcasts)
    # =========================================================================

    "99pi": Podcast(
        name="99% Invisible",
        slug="99-percent-invisible",
        category="in_progress",
        estimated_episodes=712,
        status=CrawlStatus.IN_PROGRESS,
        sources=[
            TranscriptSource(CrawlMethod.HEADLESS, slug="99percentinvisible.org", headless_required=True),
            TranscriptSource(CrawlMethod.NPR_PATTERN),
        ],
        notes="Crawling via headless browser - 712 episodes discovered"
    ),

    "dwarkesh": Podcast(
        name="Dwarkesh Podcast",
        slug="dwarkesh-podcast",
        category="in_progress",
        estimated_episodes=150,
        status=CrawlStatus.COMPLETE,
        sources=[
            TranscriptSource(CrawlMethod.HEADLESS, slug="dwarkesh.com", headless_required=True),
        ],
        notes="Substack-based, requires headless browser"
    ),

    # =========================================================================
    # CATEGORY C: NPR NETWORK (7 podcasts) - FREE, EASY
    # =========================================================================

    "planet-money": Podcast(
        name="Planet Money",
        slug="planet-money",
        category="npr",
        estimated_episodes=700,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.NPR_PATTERN, url="https://www.npr.org/series/93559517/planet-money"),
        ],
    ),

    "radiolab": Podcast(
        name="Radiolab",
        slug="radiolab",
        category="npr",
        estimated_episodes=300,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.NPR_PATTERN, url="https://radiolab.org/podcast"),
        ],
    ),

    "hidden-brain": Podcast(
        name="Hidden Brain",
        slug="hidden-brain",
        category="npr",
        estimated_episodes=400,
        status=CrawlStatus.COMPLETE,
        sources=[
            TranscriptSource(CrawlMethod.BULK_CRAWLER, slug="hiddenbrain.org"),
            TranscriptSource(CrawlMethod.NPR_PATTERN),
        ],
        notes="21 transcripts downloaded"
    ),

    "throughline": Podcast(
        name="Throughline",
        slug="throughline",
        category="npr",
        estimated_episodes=150,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.NPR_PATTERN, url="https://www.npr.org/podcasts/510333/throughline"),
        ],
    ),

    "ted-radio-hour": Podcast(
        name="TED Radio Hour",
        slug="ted-radio-hour",
        category="npr",
        estimated_episodes=200,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.NPR_PATTERN, url="https://www.npr.org/programs/ted-radio-hour"),
            TranscriptSource(CrawlMethod.TRANSCRIPT_FOREST, slug="ted-radio-hour"),
        ],
    ),

    "fresh-air": Podcast(
        name="Fresh Air",
        slug="fresh-air",
        category="npr",
        estimated_episodes=400,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.NPR_PATTERN, url="https://www.npr.org/programs/fresh-air"),
        ],
    ),

    "how-i-built-this": Podcast(
        name="How I Built This",
        slug="how-i-built-this",
        category="npr",
        estimated_episodes=300,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.NPR_PATTERN, url="https://www.npr.org/podcasts/510313/how-i-built-this"),
            TranscriptSource(CrawlMethod.TRANSCRIPT_FOREST, slug="how-i-built-this"),
        ],
    ),

    # =========================================================================
    # CATEGORY D: NYT PODCASTS (3 podcasts) - User has password
    # =========================================================================

    "the-daily": Podcast(
        name="The Daily",
        slug="the-daily",
        category="nyt",
        estimated_episodes=1200,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.NYT, url="https://www.nytimes.com/column/the-daily"),
            TranscriptSource(CrawlMethod.TRANSCRIPT_FOREST, slug="the-daily"),
        ],
        notes="User has NYT password"
    ),

    "ezra-klein": Podcast(
        name="The Ezra Klein Show",
        slug="ezra-klein-show",
        category="nyt",
        estimated_episodes=600,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.NYT, url="https://www.nytimes.com/column/ezra-klein-podcast"),
            TranscriptSource(CrawlMethod.TRANSCRIPT_FOREST, slug="ezra-klein-show"),
        ],
        notes="User has NYT password"
    ),

    "hard-fork": Podcast(
        name="Hard Fork",
        slug="hard-fork",
        category="nyt",
        estimated_episodes=300,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.PODSCRIPTS, slug="hard-fork"),
            TranscriptSource(CrawlMethod.TRANSCRIPT_FOREST, slug="hard-fork"),
        ],
    ),

    # =========================================================================
    # CATEGORY E: PODSCRIPTS AVAILABLE (15+ podcasts) - FREE
    # =========================================================================

    "all-in": Podcast(
        name="All-In Podcast",
        slug="all-in-podcast",
        category="tech",
        estimated_episodes=400,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.PODSCRIPTS, slug="all-in-with-chamath-jason-sacks-friedberg"),
            TranscriptSource(CrawlMethod.TRANSCRIPT_FOREST, slug="all-in-podcast"),
        ],
    ),

    "pivot": Podcast(
        name="Pivot",
        slug="pivot",
        category="tech",
        estimated_episodes=723,
        status=CrawlStatus.IN_PROGRESS,
        sources=[
            TranscriptSource(CrawlMethod.PODSCRIPTS, slug="pivot"),
        ],
        notes="19 transcripts downloaded from Podscripts (only shows recent 22)"
    ),

    "prof-g": Podcast(
        name="The Prof G Pod",
        slug="prof-g",
        category="tech",
        estimated_episodes=500,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.PODSCRIPTS, slug="the-prof-g-pod-with-scott-galloway"),
        ],
    ),

    "tim-ferriss": Podcast(
        name="The Tim Ferriss Show",
        slug="tim-ferriss-show",
        category="tech",
        estimated_episodes=600,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.PODSCRIPTS, slug="the-tim-ferriss-show"),
            TranscriptSource(CrawlMethod.TRANSCRIPT_FOREST, slug="tim-ferriss-show"),
        ],
    ),

    "huberman-lab": Podcast(
        name="Huberman Lab",
        slug="huberman-lab",
        category="health",
        estimated_episodes=200,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.PODSCRIPTS, slug="huberman-lab"),
            TranscriptSource(CrawlMethod.TRANSCRIPT_FOREST, slug="huberman-lab"),
        ],
        notes="hubermantranscripts.com is down"
    ),

    "modern-wisdom": Podcast(
        name="Modern Wisdom",
        slug="modern-wisdom",
        category="interviews",
        estimated_episodes=500,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.PODSCRIPTS, slug="modern-wisdom"),
            TranscriptSource(CrawlMethod.TRANSCRIPT_FOREST, slug="modern-wisdom"),
        ],
    ),

    "jordan-peterson": Podcast(
        name="The Jordan B Peterson Podcast",
        slug="jordan-peterson",
        category="interviews",
        estimated_episodes=600,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.PODSCRIPTS, slug="the-jordan-b-peterson-podcast"),
            TranscriptSource(CrawlMethod.TRANSCRIPT_FOREST, slug="jordan-peterson"),
        ],
    ),

    "armchair-expert": Podcast(
        name="Armchair Expert",
        slug="armchair-expert",
        category="interviews",
        estimated_episodes=700,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.PODSCRIPTS, slug="armchair-expert-with-dax-shepard"),
        ],
    ),

    "joe-rogan": Podcast(
        name="The Joe Rogan Experience",
        slug="joe-rogan",
        category="interviews",
        estimated_episodes=2000,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.PODSCRIPTS, slug="the-joe-rogan-experience"),
        ],
        notes="Largest podcast - 2000+ episodes"
    ),

    "stuff-you-should-know": Podcast(
        name="Stuff You Should Know",
        slug="stuff-you-should-know",
        category="educational",
        estimated_episodes=800,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.PODSCRIPTS, slug="stuff-you-should-know"),
            TranscriptSource(CrawlMethod.TRANSCRIPT_FOREST, slug="stuff-you-should-know"),
        ],
    ),

    "behind-the-bastards": Podcast(
        name="Behind the Bastards",
        slug="behind-the-bastards",
        category="history",
        estimated_episodes=300,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.PODSCRIPTS, slug="behind-the-bastards"),
        ],
    ),

    "conan-obrien": Podcast(
        name="Conan O'Brien Needs A Friend",
        slug="conan-obrien",
        category="comedy",
        estimated_episodes=200,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.PODSCRIPTS, slug="conan-obrien-needs-a-friend"),
        ],
    ),

    "no-such-thing-as-a-fish": Podcast(
        name="No Such Thing As A Fish",
        slug="no-such-thing-as-a-fish",
        category="comedy",
        estimated_episodes=642,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.PODSCRIPTS, slug="no-such-thing-as-a-fish"),
        ],
    ),

    # =========================================================================
    # CATEGORY F: TRANSCRIPT FOREST AVAILABLE (additional podcasts)
    # =========================================================================

    "my-first-million": Podcast(
        name="My First Million",
        slug="my-first-million",
        category="business",
        estimated_episodes=400,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.TRANSCRIPT_FOREST, slug="my-first-million"),
        ],
    ),

    "making-sense": Podcast(
        name="Making Sense with Sam Harris",
        slug="making-sense",
        category="philosophy",
        estimated_episodes=300,
        status=CrawlStatus.PAYWALLED,
        sources=[
            TranscriptSource(CrawlMethod.TRANSCRIPT_FOREST, slug="making-sense"),
        ],
        notes="Official requires subscription, TranscriptForest may have some"
    ),

    "freakonomics": Podcast(
        name="Freakonomics Radio",
        slug="freakonomics-radio",
        category="economics",
        estimated_episodes=400,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.TRANSCRIPT_FOREST, slug="freakonomics-radio"),
            TranscriptSource(CrawlMethod.BULK_CRAWLER, slug="freakonomics.com"),
        ],
        notes="Official site blocks crawlers (403)"
    ),

    "masters-of-scale": Podcast(
        name="Masters of Scale",
        slug="masters-of-scale",
        category="business",
        estimated_episodes=300,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.TRANSCRIPT_FOREST, slug="masters-of-scale"),
        ],
    ),

    "the-talk-show": Podcast(
        name="The Talk Show with John Gruber",
        slug="the-talk-show",
        category="tech",
        estimated_episodes=400,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.TRANSCRIPT_FOREST, slug="the-talk-show"),
        ],
    ),

    "this-american-life": Podcast(
        name="This American Life",
        slug="this-american-life",
        category="stories",
        estimated_episodes=700,
        status=CrawlStatus.COMPLETE,
        sources=[
            TranscriptSource(CrawlMethod.BULK_CRAWLER, slug="thisamericanlife.org"),
            TranscriptSource(CrawlMethod.TRANSCRIPT_FOREST, slug="this-american-life"),
        ],
        notes="51 transcripts downloaded"
    ),

    "acquired": Podcast(
        name="Acquired",
        slug="acquired",
        category="tech",
        estimated_episodes=200,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.TRANSCRIPT_FOREST, slug="acquired"),
        ],
        notes="5 transcripts from official, more on TranscriptForest"
    ),

    "odd-lots": Podcast(
        name="Odd Lots",
        slug="odd-lots",
        category="finance",
        estimated_episodes=300,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.PODSCRIPTS, slug="oddlots"),
            TranscriptSource(CrawlMethod.TRANSCRIPT_FOREST, slug="odd-lots"),
        ],
    ),

    "the-vergecast": Podcast(
        name="The Vergecast",
        slug="the-vergecast",
        category="tech",
        estimated_episodes=500,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.TRANSCRIPT_FOREST, slug="the-vergecast"),
        ],
    ),

    "this-week-in-startups": Podcast(
        name="This Week in Startups",
        slug="this-week-in-startups",
        category="business",
        estimated_episodes=600,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.TRANSCRIPT_FOREST, slug="this-week-in-startups"),
        ],
    ),

    "naval": Podcast(
        name="Naval",
        slug="naval",
        category="philosophy",
        estimated_episodes=200,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.TRANSCRIPT_FOREST, slug="naval"),
        ],
    ),

    "on-with-kara-swisher": Podcast(
        name="On with Kara Swisher",
        slug="on-with-kara-swisher",
        category="tech",
        estimated_episodes=200,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.TRANSCRIPT_FOREST, slug="on-with-kara-swisher"),
        ],
    ),

    "exponent": Podcast(
        name="Exponent",
        slug="exponent",
        category="tech",
        estimated_episodes=200,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.TRANSCRIPT_FOREST, slug="exponent"),
        ],
        notes="Ben Thompson's free podcast (not Stratechery)"
    ),

    "the-lunar-society": Podcast(
        name="The Lunar Society",
        slug="the-lunar-society",
        category="tech",
        estimated_episodes=100,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.TRANSCRIPT_FOREST, slug="the-lunar-society"),
        ],
        notes="Dwarkesh's other podcast"
    ),

    # =========================================================================
    # CATEGORY G: OFFICIAL SITES (various podcasts)
    # =========================================================================

    "darknet-diaries": Podcast(
        name="Darknet Diaries",
        slug="darknet-diaries",
        category="tech",
        estimated_episodes=200,
        status=CrawlStatus.COMPLETE,
        sources=[
            TranscriptSource(CrawlMethod.BULK_CRAWLER, slug="darknetdiaries.com"),
        ],
        notes="30 transcripts downloaded"
    ),

    "ologies": Podcast(
        name="Ologies",
        slug="ologies",
        category="science",
        estimated_episodes=400,
        status=CrawlStatus.COMPLETE,
        sources=[
            TranscriptSource(CrawlMethod.BULK_CRAWLER, slug="alieward.com"),
        ],
        notes="27 transcripts downloaded"
    ),

    "macro-voices": Podcast(
        name="Macro Voices",
        slug="macro-voices",
        category="finance",
        estimated_episodes=300,
        status=CrawlStatus.COMPLETE,
        sources=[
            TranscriptSource(CrawlMethod.BULK_CRAWLER, slug="macrovoices.com"),
        ],
        notes="10 transcripts downloaded"
    ),

    "revisionist-history": Podcast(
        name="Revisionist History",
        slug="revisionist-history",
        category="history",
        estimated_episodes=150,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.PODSCRIPTS, slug="revisionist-history"),
        ],
    ),

    "cortex": Podcast(
        name="Cortex",
        slug="cortex",
        category="productivity",
        estimated_episodes=150,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.PODSCRIPTS, slug="cortex"),
        ],
    ),

    # =========================================================================
    # CATEGORY H: MORE TECH/BUSINESS PODCASTS
    # =========================================================================

    "invest-like-the-best": Podcast(
        name="Invest Like the Best",
        slug="invest-like-the-best",
        category="finance",
        estimated_episodes=250,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.TRANSCRIPT_FOREST, slug="invest-like-the-best"),
            TranscriptSource(CrawlMethod.HEADLESS, url="https://www.joincolossus.com/episodes", headless_required=True),
        ],
    ),

    "a16z": Podcast(
        name="a16z Podcast",
        slug="a16z-podcast",
        category="tech",
        estimated_episodes=400,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.TRANSCRIPT_FOREST, slug="a16z-podcast"),
        ],
    ),

    "the-knowledge-project": Podcast(
        name="The Knowledge Project",
        slug="the-knowledge-project",
        category="interviews",
        estimated_episodes=200,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.TRANSCRIPT_FOREST, slug="the-knowledge-project"),
        ],
    ),

    "lennys-podcast": Podcast(
        name="Lenny's Podcast",
        slug="lennys-podcast",
        category="product",
        estimated_episodes=300,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.HEADLESS, url="https://www.lennysnewsletter.com/podcast", headless_required=True),
        ],
        notes="Substack-based"
    ),

    "twenty-minute-vc": Podcast(
        name="The Twenty Minute VC",
        slug="twenty-minute-vc",
        category="vc",
        estimated_episodes=500,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.TRANSCRIPT_FOREST, slug="twenty-minute-vc"),
        ],
    ),

    "decoder": Podcast(
        name="Decoder",
        slug="decoder",
        category="tech",
        estimated_episodes=200,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.TRANSCRIPT_FOREST, slug="decoder"),
        ],
        notes="The Verge - official transcripts available"
    ),

    "reply-all": Podcast(
        name="Reply All",
        slug="reply-all",
        category="tech",
        estimated_episodes=200,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.TRANSCRIPT_FOREST, slug="reply-all"),
        ],
        notes="Ended in 2022, archive available"
    ),

    "serial": Podcast(
        name="Serial",
        slug="serial",
        category="stories",
        estimated_episodes=50,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.TRANSCRIPT_FOREST, slug="serial"),
        ],
    ),

    "radiolab-presents-more-perfect": Podcast(
        name="More Perfect",
        slug="more-perfect",
        category="politics",
        estimated_episodes=50,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.NPR_PATTERN),
        ],
    ),

    "slow-burn": Podcast(
        name="Slow Burn",
        slug="slow-burn",
        category="history",
        estimated_episodes=80,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.TRANSCRIPT_FOREST, slug="slow-burn"),
        ],
    ),

    "criminal": Podcast(
        name="Criminal",
        slug="criminal",
        category="stories",
        estimated_episodes=200,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.OFFICIAL_SITE, url="https://thisiscriminal.com/"),
        ],
    ),

    "mbmbam": Podcast(
        name="My Brother, My Brother and Me",
        slug="mbmbam",
        category="comedy",
        estimated_episodes=600,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.TRANSCRIPT_FOREST, slug="mbmbam"),
        ],
    ),

    "omnibus": Podcast(
        name="Omnibus",
        slug="omnibus",
        category="educational",
        estimated_episodes=400,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.PODSCRIPTS, slug="omnibus"),
        ],
    ),

    "hardcore-history": Podcast(
        name="Hardcore History",
        slug="hardcore-history",
        category="history",
        estimated_episodes=70,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.TRANSCRIPT_FOREST, slug="hardcore-history"),
        ],
        notes="Long episodes, some are 4+ hours"
    ),

    # =========================================================================
    # CATEGORY I: PAYWALLED / NO FREE SOURCE (3-5 podcasts)
    # =========================================================================

    "stratechery": Podcast(
        name="Stratechery",
        slug="stratechery",
        category="tech",
        estimated_episodes=200,
        status=CrawlStatus.PAYWALLED,
        sources=[],
        notes="$150/year - user has access but uses magic links"
    ),

    "sharp-tech": Podcast(
        name="Sharp Tech",
        slug="sharp-tech",
        category="tech",
        estimated_episodes=100,
        status=CrawlStatus.PAYWALLED,
        sources=[],
        notes="Stratechery Plus network - $15/mo"
    ),

    "dithering": Podcast(
        name="Dithering",
        slug="dithering",
        category="tech",
        estimated_episodes=150,
        status=CrawlStatus.PAYWALLED,
        sources=[],
        notes="Stratechery Plus network"
    ),

    # =========================================================================
    # ADDITIONAL PODCASTS (to reach 73)
    # =========================================================================

    "sean-carroll-mindscape": Podcast(
        name="Mindscape",
        slug="mindscape",
        category="science",
        estimated_episodes=250,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.TRANSCRIPT_FOREST, slug="mindscape"),
        ],
    ),

    "people-i-mostly-admire": Podcast(
        name="People I (Mostly) Admire",
        slug="people-i-mostly-admire",
        category="interviews",
        estimated_episodes=100,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.TRANSCRIPT_FOREST, slug="people-i-mostly-admire"),
        ],
        notes="Freakonomics network"
    ),

    "the-indicator": Podcast(
        name="The Indicator from Planet Money",
        slug="the-indicator",
        category="economics",
        estimated_episodes=500,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.NPR_PATTERN),
        ],
    ),

    "today-explained": Podcast(
        name="Today, Explained",
        slug="today-explained",
        category="news",
        estimated_episodes=600,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.TRANSCRIPT_FOREST, slug="today-explained"),
        ],
        notes="Vox Media"
    ),

    "the-weeds": Podcast(
        name="The Weeds",
        slug="the-weeds",
        category="politics",
        estimated_episodes=400,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.TRANSCRIPT_FOREST, slug="the-weeds"),
        ],
        notes="Vox Media"
    ),

    "endless-thread": Podcast(
        name="Endless Thread",
        slug="endless-thread",
        category="stories",
        estimated_episodes=200,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.NPR_PATTERN),
        ],
        notes="WBUR + Reddit"
    ),

    "land-of-the-giants": Podcast(
        name="Land of the Giants",
        slug="land-of-the-giants",
        category="tech",
        estimated_episodes=100,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.TRANSCRIPT_FOREST, slug="land-of-the-giants"),
        ],
        notes="Vox Media"
    ),

    "marketplace": Podcast(
        name="Marketplace",
        slug="marketplace",
        category="economics",
        estimated_episodes=2000,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.OFFICIAL_SITE, url="https://www.marketplace.org/"),
        ],
        notes="APM - daily show, huge archive"
    ),

    "the-daily-show-ears-edition": Podcast(
        name="The Daily Show: Ears Edition",
        slug="daily-show-ears",
        category="comedy",
        estimated_episodes=300,
        status=CrawlStatus.NEEDS_RESEARCH,
        sources=[],
    ),

    "hello-internet": Podcast(
        name="Hello Internet",
        slug="hello-internet",
        category="tech",
        estimated_episodes=136,
        status=CrawlStatus.READY,
        sources=[
            TranscriptSource(CrawlMethod.TRANSCRIPT_FOREST, slug="hello-internet"),
        ],
        notes="Ended in 2020, full archive"
    ),
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_podcasts_by_status(status: CrawlStatus) -> List[Podcast]:
    """Get all podcasts with a specific status"""
    return [p for p in PODCASTS.values() if p.status == status]


def get_podcasts_by_category(category: str) -> List[Podcast]:
    """Get all podcasts in a category"""
    return [p for p in PODCASTS.values() if p.category == category]


def get_podcasts_by_method(method: CrawlMethod) -> List[Podcast]:
    """Get all podcasts that can use a specific crawl method"""
    return [
        p for p in PODCASTS.values()
        if any(s.method == method for s in p.sources)
    ]


def get_ready_podcasts() -> List[Podcast]:
    """Get all podcasts ready to crawl"""
    return [p for p in PODCASTS.values() if p.status == CrawlStatus.READY]


def get_podcast_stats() -> Dict[str, Any]:
    """Get summary statistics"""
    total = len(PODCASTS)
    by_status = {}
    for status in CrawlStatus:
        count = len([p for p in PODCASTS.values() if p.status == status])
        by_status[status.value] = count

    total_episodes = sum(p.estimated_episodes for p in PODCASTS.values())

    return {
        "total_podcasts": total,
        "by_status": by_status,
        "estimated_total_episodes": total_episodes,
    }


def print_registry_summary():
    """Print a summary of the registry"""
    stats = get_podcast_stats()

    print("\n" + "=" * 70)
    print("PODCAST TRANSCRIPT REGISTRY - SUMMARY")
    print("=" * 70)
    print(f"\nTotal Podcasts: {stats['total_podcasts']}")
    print(f"Estimated Episodes: {stats['estimated_total_episodes']:,}")
    print("\nBy Status:")
    for status, count in stats['by_status'].items():
        print(f"  {status}: {count}")

    print("\n" + "-" * 70)
    print("READY TO CRAWL:")
    print("-" * 70)
    for p in get_ready_podcasts():
        source = p.primary_source
        method = source.method.value if source else "none"
        print(f"  [{method:20}] {p.name} (~{p.estimated_episodes} eps)")

    print("\n" + "-" * 70)
    print("COMPLETED:")
    print("-" * 70)
    for p in get_podcasts_by_status(CrawlStatus.COMPLETE):
        print(f"  ✓ {p.name} - {p.notes}")

    print("\n" + "-" * 70)
    print("PAYWALLED (No free source):")
    print("-" * 70)
    for p in get_podcasts_by_status(CrawlStatus.PAYWALLED):
        print(f"  ✗ {p.name} - {p.notes}")

    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    print_registry_summary()
