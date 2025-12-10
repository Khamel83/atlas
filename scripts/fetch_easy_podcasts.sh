#!/bin/bash
# Fetch transcripts for podcasts that have reliable non-YouTube sources
# These will process much faster than YouTube-dependent shows

cd /home/khamel83/github/atlas
source venv/bin/activate

# Podcasts with Podscripts (AI transcripts - very reliable)
PODSCRIPTS_SHOWS=(
    "decoder-with-nilay-patel"
    "cortex"
    "all-in-with-chamath-jason-sacks-amp-friedberg"
    "animal-spirits-podcast"
    "heavyweight"
    "a16z-podcast"
    "conan-obrien-needs-a-friend"
    "dwarkesh-podcast"
)

# Podcasts with network transcripts (NPR, Slate, etc)
NETWORK_SHOWS=(
    "hidden-brain"
    "this-american-life"
    "radiolab"
    "planet-money"
    "the-indicator-from-planet-money"
    "npr-politics-podcast"
    "up-first"
    "embedded"
    "invisibilia"
    "code-switch"
    "rough-translation"
    "throughline"
    "fresh-air"
    "ted-radio-hour"
    "how-i-built-this-with-guy-raz"
    "wait-wait-dont-tell-me"
    "pop-culture-happy-hour"
    "its-been-a-minute"
    "bullseye-with-jesse-thorn"
    "political-gabfest"
    "slate-culture"
    "what-next"
    "slow-burn"
    "decoder-ring"
)

# Podcasts with RSS link transcripts (direct links in feed)
RSS_SHOWS=(
    "accidental-tech-podcast"
    "the-talk-show-with-john-gruber"
    "dithering"
    "exponent"
)

echo "=========================================="
echo "PHASE 1: Podscripts shows (fastest)"
echo "=========================================="
for show in "${PODSCRIPTS_SHOWS[@]}"; do
    echo ">>> Processing $show"
    python -m modules.podcasts.cli fetch-transcripts --slug "$show" 2>&1 | tail -5
done

echo ""
echo "=========================================="
echo "PHASE 2: Network transcript shows"
echo "=========================================="
for show in "${NETWORK_SHOWS[@]}"; do
    echo ">>> Processing $show"
    python -m modules.podcasts.cli fetch-transcripts --slug "$show" 2>&1 | tail -5
done

echo ""
echo "=========================================="
echo "PHASE 3: RSS link shows"
echo "=========================================="
for show in "${RSS_SHOWS[@]}"; do
    echo ">>> Processing $show"
    python -m modules.podcasts.cli fetch-transcripts --slug "$show" 2>&1 | tail -5
done

echo ""
echo "=========================================="
echo "Done with easy podcasts!"
echo "=========================================="
python -m modules.podcasts.cli status
