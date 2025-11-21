#!/usr/bin/env python3
"""
Atlas Quality Rescue System
Automated recovery for Tier 3 content using multiple sources
"""

import json
import sqlite3
import requests
import time
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import urllib.parse
from urllib.robotparser import RobotFileParser

class AtlasQualityRescue:
    def __init__(self, db_path="podcast_processing.db"):
        self.db_path = db_path
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; Atlas-Content-Rescue/1.0)'
        })
        self.rescue_log = []

    def get_tier_3_files(self) -> List[Dict]:
        """Get Tier 3 files that need rescue"""
        try:
            with open("quality_reports/tier_3_rescue_queue.json", 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print("❌ No Tier 3 rescue queue found. Run atlas_content_validator.py first")
            return []

    def extract_original_url(self, filename: str, content: str = None) -> Optional[str]:
        """Extract original URL from filename or content"""
        # Try to extract from filename first
        if filename.startswith("content_") and filename.endswith(".md"):
            content_hash = filename[8:-3]  # Remove 'content_' and '.md'

            # Try to find original URL from database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT source_url FROM atlas_queue
                WHERE content_hash = ? OR filename = ?
                LIMIT 1
            """, (content_hash, filename))

            result = cursor.fetchone()
            conn.close()

            if result and result[0]:
                return result[0]

        # Try to extract URL from content if provided
        if content:
            # Look for URLs in content
            url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
            urls = re.findall(url_pattern, content)
            if urls:
                return urls[0]

        return None

    def try_wayback_machine(self, url: str) -> Optional[str]:
        """Try to fetch content from Wayback Machine"""
        try:
            # Wayback Machine CDX API
            cdx_url = f"http://web.archive.org/cdx/search/cdx"
            params = {
                'url': url,
                'output': 'json',
                'filter': 'statuscode:200',
                'filter': 'mimetype:text/html',
                'limit': 5,
                'sort': 'reverse'
            }

            response = self.session.get(cdx_url, params=params, timeout=10)
            if response.status_code != 200:
                return None

            data = response.json()
            if len(data) < 2:
                return None

            # Get the most recent snapshot
            snapshot = data[1]  # Skip header row
            timestamp = snapshot[1]

            # Construct Wayback URL
            wayback_url = f"http://web.archive.org/web/{timestamp}/{url}"

            # Fetch the content
            response = self.session.get(wayback_url, timeout=15)
            if response.status_code == 200 and len(response.text) > 1000:
                return response.text

        except Exception as e:
            print(f"    ❌ Wayback Machine error: {e}")

        return None

    def try_google_cache(self, url: str) -> Optional[str]:
        """Try to fetch content from Google Cache"""
        try:
            # Google cache URL
            cache_url = f"https://webcache.googleusercontent.com/search?q=cache:{url}"

            response = self.session.get(cache_url, timeout=10)
            if response.status_code == 200:
                # Check if we got actual cached content
                if "cached" in response.text.lower() and len(response.text) > 1000:
                    return response.text

        except Exception as e:
            print(f"    ❌ Google Cache error: {e}")

        return None

    def try_alternative_domains(self, url: str) -> List[Tuple[str, str]]:
        """Try to find alternative domains with same content"""
        alternatives = []

        # Parse original URL
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc
        path = parsed.path

        # Common alternative patterns
        alternative_patterns = [
            # Add/remove www
            lambda d: d.replace("www.", "") if "www." in d else f"www.{d}",

            # HTTPS/HTTP swap
            lambda d: d.replace("https://", "http://") if d.startswith("https://") else d.replace("http://", "https://"),

            # Common domain variations
            lambda d: d.replace(".com", ".org") if ".com" in d else d,
            lambda d: d.replace(".org", ".net") if ".org" in d else d,
        ]

        for pattern in alternative_patterns:
            try:
                alt_domain = pattern(domain)
                if alt_domain != domain:
                    alt_url = url.replace(domain, alt_domain)

                    response = self.session.get(alt_url, timeout=8)
                    if response.status_code == 200 and len(response.text) > 1000:
                        alternatives.append((alt_url, response.text))

            except Exception:
                continue

        return alternatives

    def extract_article_content(self, html_content: str) -> str:
        """Extract clean article content from HTML"""
        # Simple content extraction (can be enhanced)
        content = html_content

        # Remove script/style tags
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL | re.IGNORECASE)

        # Remove common boilerplate
        boilerplate_patterns = [
            r'<nav[^>]*>.*?</nav>',
            r'<header[^>]*>.*?</header>',
            r'<footer[^>]*>.*?</footer>',
            r'<aside[^>]*>.*?</aside>',
            r'Navigation:',
            r'Menu:',
            r'Share this:',
            r'Related articles:',
            r'Comments:',
            r'Cookie policy',
            r'Privacy policy',
            r'Terms of service'
        ]

        for pattern in boilerplate_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)

        # Extract paragraphs
        paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', content, flags=re.DOTALL | re.IGNORECASE)

        if paragraphs:
            # Clean HTML tags from paragraphs
            clean_paragraphs = []
            for p in paragraphs:
                clean_p = re.sub(r'<[^>]+>', '', p).strip()
                if len(clean_p) > 50:  # Filter out very short paragraphs
                    clean_paragraphs.append(clean_p)

            if clean_paragraphs:
                return '\n\n'.join(clean_paragraphs)

        # Fallback: remove all HTML tags
        content = re.sub(r'<[^>]+>', '\n', content)

        # Clean up whitespace
        content = re.sub(r'\n\s*\n', '\n\n', content)
        content = content.strip()

        return content

    def create_rescued_markdown(self, original_path: str, content: str, source: str, original_url: str) -> str:
        """Create rescued markdown file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"rescued_{timestamp}_{Path(original_path).name}"

        # Create rescued content directory
        rescued_dir = Path("content/rescued")
        rescued_dir.mkdir(exist_ok=True)

        rescued_path = rescued_dir / filename

        # Create rescued markdown with metadata
        header = f"""---
rescued_at: {datetime.now().isoformat()}
original_file: {original_path}
rescue_source: {source}
original_url: {original_url}
rescue_method: automated
---

"""

        full_content = header + content

        with open(rescued_path, 'w', encoding='utf-8') as f:
            f.write(full_content)

        return str(rescued_path)

    def rescue_single_file(self, file_info: Dict) -> Dict:
        """Attempt to rescue a single Tier 3 file"""
        filename = file_info["filename"]
        file_path = file_info["file_path"]
        score = file_info["details"]["final_score"]

        rescue_result = {
            "filename": filename,
            "original_score": score,
            "rescue_attempts": [],
            "rescued": False,
            "rescued_path": None,
            "new_score": None,
            "rescue_time": datetime.now().isoformat()
        }

        print(f"🚨 Rescuing: {filename} (Score: {score})")

        # Read original file to extract URL
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
        except Exception as e:
            rescue_result["error"] = f"Cannot read original file: {e}"
            return rescue_result

        # Extract original URL
        original_url = self.extract_original_url(filename, original_content)
        if not original_url:
            rescue_result["error"] = "Cannot extract original URL"
            return rescue_result

        print(f"  📎 Original URL: {original_url}")

        # Attempt 1: Wayback Machine
        print(f"  🕐 Trying Wayback Machine...")
        wayback_content = self.try_wayback_machine(original_url)
        if wayback_content:
            article_content = self.extract_article_content(wayback_content)
            if len(article_content) > 500:
                rescued_path = self.create_rescued_markdown(file_path, article_content, "wayback_machine", original_url)
                rescue_result["rescue_attempts"].append("wayback_machine_success")
                rescue_result["rescued"] = True
                rescue_result["rescued_path"] = rescued_path
                print(f"    ✅ Rescued via Wayback Machine!")
                return rescue_result
            else:
                rescue_result["rescue_attempts"].append("wayback_machine_no_content")
        else:
            rescue_result["rescue_attempts"].append("wayback_machine_failed")

        # Attempt 2: Google Cache
        print(f"  🔍 Trying Google Cache...")
        cache_content = self.try_google_cache(original_url)
        if cache_content:
            article_content = self.extract_article_content(cache_content)
            if len(article_content) > 500:
                rescued_path = self.create_rescued_markdown(file_path, article_content, "google_cache", original_url)
                rescue_result["rescue_attempts"].append("google_cache_success")
                rescue_result["rescued"] = True
                rescue_result["rescued_path"] = rescued_path
                print(f"    ✅ Rescued via Google Cache!")
                return rescue_result
            else:
                rescue_result["rescue_attempts"].append("google_cache_no_content")
        else:
            rescue_result["rescue_attempts"].append("google_cache_failed")

        # Attempt 3: Alternative Domains
        print(f"  🔄 Trying Alternative Domains...")
        alternatives = self.try_alternative_domains(original_url)
        for alt_url, alt_content in alternatives[:3]:  # Try max 3 alternatives
            article_content = self.extract_article_content(alt_content)
            if len(article_content) > 500:
                rescued_path = self.create_rescued_markdown(file_path, article_content, f"alternative_domain_{alt_url}", original_url)
                rescue_result["rescue_attempts"].append(f"alternative_success_{alt_url}")
                rescue_result["rescued"] = True
                rescue_result["rescued_path"] = rescued_path
                print(f"    ✅ Rescued via Alternative Domain: {alt_url}")
                return rescue_result

        rescue_result["rescue_attempts"].append("alternatives_failed")
        rescue_result["error"] = "All rescue methods failed"

        print(f"    ❌ All rescue methods failed")
        return rescue_result

    def update_rescue_status(self, rescue_result: Dict):
        """Update database with rescue status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE content_quality SET
                needs_rescue = FALSE,
                rescued = TRUE,
                rescued_path = ?,
                rescue_details = ?,
                rescue_time = ?
            WHERE filename = ?
        """, (
            rescue_result.get("rescued_path"),
            json.dumps(rescue_result),
            rescue_result["rescue_time"],
            rescue_result["filename"]
        ))

        conn.commit()
        conn.close()

    def run_rescue_batch(self, max_files: int = None) -> Dict:
        """Run rescue process on Tier 3 files"""
        tier_3_files = self.get_tier_3_files()

        if max_files:
            tier_3_files = tier_3_files[:max_files]

        print(f"🚨 Atlas Quality Rescue System")
        print(f"📁 Processing {len(tier_3_files)} Tier 3 files...")

        results = {
            "total_files": len(tier_3_files),
            "rescued_count": 0,
            "failed_count": 0,
            "rescue_results": []
        }

        for i, file_info in enumerate(tier_3_files):
            print(f"\n📄 [{i+1}/{len(tier_3_files)}] Processing {file_info['filename']}")

            rescue_result = self.rescue_single_file(file_info)
            results["rescue_results"].append(rescue_result)

            if rescue_result["rescued"]:
                results["rescued_count"] += 1
                self.update_rescue_status(rescue_result)
            else:
                results["failed_count"] += 1

            # Rate limiting
            time.sleep(2)

            if (i + 1) % 10 == 0:
                print(f"\n📊 Progress: {i+1}/{len(tier_3_files)} files")
                print(f"   Rescued: {results['rescued_count']}")
                print(f"   Failed: {results['failed_count']}")

        # Save rescue report
        self.save_rescue_report(results)

        return results

    def save_rescue_report(self, results: Dict):
        """Save rescue operation report"""
        report_dir = Path("quality_reports")
        report_dir.mkdir(exist_ok=True)

        rescue_report = {
            "rescue_time": datetime.now().isoformat(),
            "summary": {
                "total_files": results["total_files"],
                "rescued_count": results["rescued_count"],
                "failed_count": results["failed_count"],
                "success_rate": results["rescued_count"] / results["total_files"] * 100 if results["total_files"] > 0 else 0
            },
            "detailed_results": results["rescue_results"]
        }

        with open(report_dir / f"rescue_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", 'w') as f:
            json.dump(rescue_report, f, indent=2)

        print(f"\n📄 Rescue report saved to {report_dir}")

    def print_summary(self, results: Dict):
        """Print rescue operation summary"""
        success_rate = results["rescued_count"] / results["total_files"] * 100 if results["total_files"] > 0 else 0

        print(f"\n🎯 Atlas Quality Rescue Summary")
        print(f"📁 Total Files Processed: {results['total_files']}")
        print(f"✅ Successfully Rescued: {results['rescued_count']}")
        print(f"❌ Rescue Failed: {results['failed_count']}")
        print(f"📈 Success Rate: {success_rate:.1f}%")

        if results["rescued_count"] > 0:
            print(f"\n🎉 Rescued files saved to: content/rescued/")
            print(f"📄 Detailed report: quality_reports/rescue_report_*.json")

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Atlas Quality Rescue System')
    parser.add_argument('--max-files', type=int, help='Maximum files to process')
    parser.add_argument('--run-validation', action='store_true', help='Run content validation first')

    args = parser.parse_args()

    # Run validation if requested
    if args.run_validation:
        print("🔍 Running content validation first...")
        from atlas_content_validator import AtlasContentValidator
        validator = AtlasContentValidator()
        results = validator.scan_all_markdown_files()
        validator.save_quality_report(results)
        print("✅ Validation complete")

    # Run rescue
    rescuer = AtlasQualityRescue()
    results = rescuer.run_rescue_batch(max_files=args.max_files)
    rescuer.print_summary(results)

if __name__ == "__main__":
    main()