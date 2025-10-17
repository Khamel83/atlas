#!/usr/bin/env python3
"""
Universal Podcast Transcript Discoverer

Automatically discovers existing transcripts across your 160+ podcasts without manual searching.
Uses multiple strategies to find professional transcripts that already exist.

Common transcript sources:
- Podcast websites with transcript pages
- Third-party transcript sites (like catatp.fm for ATP)
- RSS feeds with transcript links
- Automated transcript services
- Community transcript projects
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Set
import time
from urllib.parse import urljoin, urlparse
import logging
from xml.etree import ElementTree as ET

logger = logging.getLogger(__name__)

class UniversalTranscriptDiscoverer:
    """Discover transcripts across multiple podcast sources"""

    def __init__(self, atlas_root: Path):
        self.atlas_root = atlas_root
        self.podcasts_dir = atlas_root / "output" / "podcasts"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

        # Known transcript hosting patterns
        self.transcript_sites = {
            "otter.ai": r"otter\.ai",
            "rev.com": r"rev\.com",
            "trint.com": r"trint\.com",
            "sonix.ai": r"sonix\.ai",
            "transcript.com": r"transcript\.com",
            "transcripts.fm": r"transcripts\.fm",
            "podscribe.ai": r"podscribe\.ai"
        }

        # Known podcast networks with transcript infrastructure
        self.transcript_networks = {
            "gimlet": ["gimletmedia.com", "spotify.com/show"],
            "npr": ["npr.org", "nprone.org"],
            "this_american_life": ["thisamericanlife.org"],
            "radiolab": ["radiolab.org", "wnycstudios.org"],
            "99pi": ["99percentinvisible.org"],
            "freakonomics": ["freakonomics.com"],
            "planet_money": ["npr.org/sections/money"],
            "ringer": ["theringer.com"],
            "vox": ["voxmedia.com", "vox.com"],
            "slate": ["slate.com"],
            "stratechery": ["stratechery.com"],
            "a16z": ["a16z.com"],
            "ycombinator": ["blog.ycombinator.com"]
        }

    def load_opml_podcasts(self) -> List[Dict]:
        """Load podcast list from OPML file"""
        opml_file = self.atlas_root / "inputs" / "podcasts.opml"
        podcasts = []

        try:
            with open(opml_file, 'r', encoding='utf-8') as f:
                content = f.read()

            root = ET.fromstring(content)

            for outline in root.findall('.//outline[@type="rss"]'):
                podcast = {
                    "title": outline.get('text', ''),
                    "rss_url": outline.get('xmlUrl', ''),
                    "website": outline.get('htmlUrl', ''),
                    "apple_id": outline.get('applePodcastsID', '')
                }

                if podcast["rss_url"]:
                    podcasts.append(podcast)

            logger.info(f"Loaded {len(podcasts)} podcasts from OPML")
            return podcasts

        except Exception as e:
            logger.error(f"Failed to load OPML: {e}")
            return []

    def analyze_rss_for_transcripts(self, rss_url: str) -> Dict:
        """Check RSS feed for transcript links"""
        try:
            response = self.session.get(rss_url, timeout=30)
            response.raise_for_status()

            # Parse RSS/XML
            root = ET.fromstring(response.content)

            transcript_indicators = {
                "has_transcript_tags": False,
                "has_transcript_links": False,
                "transcript_urls": [],
                "transcript_elements": [],
                "sample_episodes": []
            }

            # Look for transcript-related elements
            for item in root.findall('.//item')[:5]:  # Check first 5 episodes
                episode_data = {
                    "title": "",
                    "link": "",
                    "description": "",
                    "transcript_links": []
                }

                # Extract basic episode info
                title_elem = item.find('title')
                if title_elem is not None:
                    episode_data["title"] = title_elem.text or ""

                link_elem = item.find('link')
                if link_elem is not None:
                    episode_data["link"] = link_elem.text or ""

                desc_elem = item.find('description')
                if desc_elem is not None:
                    episode_data["description"] = desc_elem.text or ""

                # Look for transcript-specific elements
                for elem in item:
                    if 'transcript' in elem.tag.lower():
                        transcript_indicators["has_transcript_tags"] = True
                        transcript_indicators["transcript_elements"].append(elem.tag)

                        if elem.text:
                            transcript_indicators["transcript_urls"].append(elem.text)

                # Look for transcript URLs in description or links
                text_to_search = f"{episode_data['description']} {episode_data['link']}"
                transcript_urls = re.findall(r'https?://[^\s<>"]+transcript[^\s<>"]*', text_to_search, re.IGNORECASE)

                if transcript_urls:
                    transcript_indicators["has_transcript_links"] = True
                    episode_data["transcript_links"] = transcript_urls
                    transcript_indicators["transcript_urls"].extend(transcript_urls)

                transcript_indicators["sample_episodes"].append(episode_data)

            return transcript_indicators

        except Exception as e:
            logger.warning(f"Failed to analyze RSS {rss_url}: {e}")
            return {"error": str(e)}

    def detect_transcript_hosting_service(self, podcast: Dict) -> Optional[str]:
        """Detect if podcast uses known transcript hosting service"""

        # Check website URL for known services
        website = podcast.get("website", "")
        rss_url = podcast.get("rss_url", "")

        combined_urls = f"{website} {rss_url}"

        for service, pattern in self.transcript_sites.items():
            if re.search(pattern, combined_urls, re.IGNORECASE):
                return service

        # Check for known networks
        for network, domains in self.transcript_networks.items():
            for domain in domains:
                if domain in combined_urls:
                    return f"network_{network}"

        return None

    def probe_website_for_transcripts(self, podcast: Dict) -> Dict:
        """Probe podcast website for transcript availability"""
        website = podcast.get("website", "")

        if not website:
            return {"status": "no_website"}

        try:
            # Get main podcast page
            response = self.session.get(website, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            findings = {
                "has_transcript_links": False,
                "transcript_pages": [],
                "transcript_mentions": 0,
                "search_functionality": False
            }

            # Look for transcript-related links
            transcript_links = soup.find_all('a', href=re.compile(r'transcript', re.IGNORECASE))
            if transcript_links:
                findings["has_transcript_links"] = True
                findings["transcript_pages"] = [urljoin(website, link.get('href', '')) for link in transcript_links[:5]]

            # Count transcript mentions
            page_text = soup.get_text().lower()
            findings["transcript_mentions"] = len(re.findall(r'transcript', page_text))

            # Look for search functionality (indicates organized content)
            search_elements = soup.find_all(['input', 'form'], attrs={'type': 'search'}) + \
                            soup.find_all(attrs={'class': re.compile(r'search', re.IGNORECASE)})
            findings["search_functionality"] = len(search_elements) > 0

            return findings

        except Exception as e:
            logger.warning(f"Failed to probe website {website}: {e}")
            return {"status": "error", "error": str(e)}

    def discover_podcast_transcripts(self, podcast: Dict) -> Dict:
        """Comprehensive transcript discovery for a single podcast"""

        result = {
            "podcast": podcast["title"],
            "rss_url": podcast["rss_url"],
            "website": podcast.get("website", ""),
            "transcript_likelihood": "unknown",
            "transcript_sources": [],
            "hosting_service": None,
            "rss_analysis": {},
            "website_analysis": {},
            "recommended_action": "unknown"
        }

        # Detect hosting service
        hosting_service = self.detect_transcript_hosting_service(podcast)
        if hosting_service:
            result["hosting_service"] = hosting_service
            result["transcript_likelihood"] = "high"
            result["transcript_sources"].append(f"hosted_on_{hosting_service}")

        # Analyze RSS feed
        logger.info(f"Analyzing RSS for {podcast['title']}")
        rss_analysis = self.analyze_rss_for_transcripts(podcast["rss_url"])
        result["rss_analysis"] = rss_analysis

        if rss_analysis.get("has_transcript_tags") or rss_analysis.get("has_transcript_links"):
            result["transcript_likelihood"] = "high"
            result["transcript_sources"].append("rss_feed")

        # Probe website if available
        if podcast.get("website"):
            logger.info(f"Probing website for {podcast['title']}")
            website_analysis = self.probe_website_for_transcripts(podcast)
            result["website_analysis"] = website_analysis

            if website_analysis.get("has_transcript_links") or website_analysis.get("transcript_mentions", 0) > 3:
                result["transcript_likelihood"] = "medium"
                result["transcript_sources"].append("website")

        # Determine recommended action
        if result["transcript_likelihood"] == "high":
            result["recommended_action"] = "build_custom_scraper"
        elif result["transcript_likelihood"] == "medium":
            result["recommended_action"] = "investigate_manually"
        elif result["hosting_service"]:
            result["recommended_action"] = "use_hosting_api"
        else:
            result["recommended_action"] = "use_audio_transcription"

        return result

    def discover_all_transcripts(self, limit: Optional[int] = None) -> Dict:
        """Discover transcripts across all podcasts in OPML"""

        podcasts = self.load_opml_podcasts()
        if limit:
            podcasts = podcasts[:limit]

        results = {
            "total_podcasts": len(podcasts),
            "high_likelihood": [],
            "medium_likelihood": [],
            "low_likelihood": [],
            "hosting_services": {},
            "transcript_sources": {},
            "recommendations": {}
        }

        for i, podcast in enumerate(podcasts, 1):
            logger.info(f"Processing {i}/{len(podcasts)}: {podcast['title']}")

            try:
                discovery_result = self.discover_podcast_transcripts(podcast)

                # Categorize by likelihood
                likelihood = discovery_result["transcript_likelihood"]
                if likelihood == "high":
                    results["high_likelihood"].append(discovery_result)
                elif likelihood == "medium":
                    results["medium_likelihood"].append(discovery_result)
                else:
                    results["low_likelihood"].append(discovery_result)

                # Track hosting services
                hosting = discovery_result.get("hosting_service")
                if hosting:
                    if hosting not in results["hosting_services"]:
                        results["hosting_services"][hosting] = []
                    results["hosting_services"][hosting].append(podcast["title"])

                # Track transcript sources
                for source in discovery_result.get("transcript_sources", []):
                    if source not in results["transcript_sources"]:
                        results["transcript_sources"][source] = 0
                    results["transcript_sources"][source] += 1

                # Track recommendations
                action = discovery_result.get("recommended_action", "unknown")
                if action not in results["recommendations"]:
                    results["recommendations"][action] = []
                results["recommendations"][action].append(podcast["title"])

                # Rate limiting
                time.sleep(1)

            except Exception as e:
                logger.error(f"Error processing {podcast['title']}: {e}")
                results["low_likelihood"].append({
                    "podcast": podcast["title"],
                    "error": str(e),
                    "recommended_action": "manual_investigation"
                })

        return results


def main():
    """Run transcript discovery on all podcasts"""
    atlas_root = Path("/home/ubuntu/dev/atlas")
    discoverer = UniversalTranscriptDiscoverer(atlas_root)

    print("🔍 Universal Podcast Transcript Discovery")
    print("📊 Analyzing all 160+ podcasts from your OPML for existing transcripts...")

    # Start with a sample to test the system
    results = discoverer.discover_all_transcripts(limit=10)

    print(f"\n📊 Discovery Results (sample of 10):")
    print(f"   High likelihood: {len(results['high_likelihood'])} podcasts")
    print(f"   Medium likelihood: {len(results['medium_likelihood'])} podcasts")
    print(f"   Low likelihood: {len(results['low_likelihood'])} podcasts")

    print(f"\n🏢 Hosting Services Found:")
    for service, podcasts in results['hosting_services'].items():
        print(f"   {service}: {len(podcasts)} podcasts")

    print(f"\n🎯 Recommended Actions:")
    for action, podcasts in results['recommendations'].items():
        print(f"   {action}: {len(podcasts)} podcasts")

    if results['high_likelihood']:
        print(f"\n✅ High-likelihood transcript sources:")
        for podcast in results['high_likelihood'][:3]:
            print(f"   - {podcast['podcast']}: {', '.join(podcast['transcript_sources'])}")


if __name__ == "__main__":
    main()