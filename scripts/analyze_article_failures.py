#!/usr/bin/env python3
"""
Task 1.4: Analyze Article Fetching Failures

This script analyzes article fetching failure patterns from various log files
to identify the most common reasons for failure and categorize them.
"""

import json
import re
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Counter
from collections import defaultdict, Counter
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

class ArticleFailureAnalyzer:
    """Analyzes article fetching failures from log files."""

    def __init__(self):
        self.failure_patterns = {
            "paywall": [
                "paywall", "subscription", "premium", "subscribe",
                "login required", "sign up", "member", "access denied"
            ],
            "cloudflare": [
                "cloudflare", "challenge", "checking your browser", "ray id",
                "ddos protection", "security check"
            ],
            "404_not_found": [
                "404", "not found", "page not found", "does not exist"
            ],
            "403_forbidden": [
                "403", "forbidden", "access forbidden", "permission denied"
            ],
            "timeout": [
                "timeout", "timed out", "connection timeout", "read timeout"
            ],
            "rate_limiting": [
                "rate limit", "too many requests", "429", "throttled"
            ],
            "server_error": [
                "500", "502", "503", "504", "internal server error",
                "bad gateway", "service unavailable"
            ],
            "connection_error": [
                "connection refused", "connection error", "network error",
                "dns resolution", "connection reset"
            ],
            "content_issues": [
                "empty content", "no content", "content too short",
                "invalid content", "malformed"
            ],
            "javascript_required": [
                "javascript", "js required", "enable javascript"
            ]
        }

        self.log_files = []
        self.findings = defaultdict(list)
        self.failure_stats = Counter()

    def find_log_files(self) -> List[Path]:
        """Find all relevant log files."""
        log_files = []

        # Common log file locations
        search_paths = [
            "output/articles/ingest.log",
            "output/error_log.jsonl",
            "output/Full_Pipeline.log",
            "output/link_dispatcher.log",
            "logs/",
            "retries/",
            "."
        ]

        for search_path in search_paths:
            path = Path(search_path)
            if path.is_file():
                log_files.append(path)
            elif path.is_dir():
                # Find log files in directory
                for pattern in ["*.log", "*.jsonl", "*retry*", "*error*"]:
                    log_files.extend(path.glob(pattern))

        # Remove duplicates and filter
        unique_files = []
        seen = set()

        for log_file in log_files:
            abs_path = log_file.resolve()
            if abs_path not in seen and abs_path.exists():
                seen.add(abs_path)
                unique_files.append(log_file)

        return unique_files

    def analyze_log_file(self, log_file: Path) -> Dict[str, Any]:
        """Analyze a single log file for failure patterns."""
        print(f"📄 Analyzing: {log_file}")

        results = {
            "file": str(log_file),
            "total_lines": 0,
            "error_lines": 0,
            "patterns_found": defaultdict(list)
        }

        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    results["total_lines"] += 1

                    # Check if line contains error indicators
                    line_lower = line.lower()
                    if any(indicator in line_lower for indicator in
                          ["error", "failed", "exception", "warning", "timeout"]):
                        results["error_lines"] += 1

                        # Check against failure patterns
                        for category, patterns in self.failure_patterns.items():
                            for pattern in patterns:
                                if pattern in line_lower:
                                    results["patterns_found"][category].append({
                                        "line_num": line_num,
                                        "pattern": pattern,
                                        "context": line.strip()[:200]  # Limit context
                                    })
                                    self.failure_stats[category] += 1
                                    break

        except Exception as e:
            print(f"❌ Error reading {log_file}: {e}")
            results["error"] = str(e)

        return results

    def extract_urls_from_logs(self, log_files: List[Path]) -> List[str]:
        """Extract failed URLs from log files."""
        failed_urls = []
        url_pattern = re.compile(r'https?://[^\s<>"\']+')

        for log_file in log_files:
            try:
                content = log_file.read_text(encoding='utf-8', errors='ignore')

                # Look for lines with errors and URLs
                for line in content.split('\n'):
                    line_lower = line.lower()
                    if any(indicator in line_lower for indicator in
                          ["error", "failed", "exception", "timeout"]):
                        urls = url_pattern.findall(line)
                        failed_urls.extend(urls)

            except Exception as e:
                print(f"Error processing {log_file}: {e}")

        return list(set(failed_urls))  # Remove duplicates

    def categorize_url_failures(self, urls: List[str]) -> Dict[str, List[str]]:
        """Categorize URLs by likely failure reason based on domain patterns."""
        categorized = defaultdict(list)

        for url in urls:
            domain = self.extract_domain(url)
            category = self.classify_domain(domain)
            categorized[category].append(url)

        return dict(categorized)

    def extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse
            return urlparse(url).netloc.lower()
        except:
            return "unknown"

    def classify_domain(self, domain: str) -> str:
        """Classify domain by likely issues."""
        known_paywall_sites = [
            "nytimes.com", "wsj.com", "economist.com", "ft.com",
            "washingtonpost.com", "newyorker.com", "atlantic.com"
        ]

        cloudflare_heavy = [
            "medium.com", "substack.com"
        ]

        if any(paywall in domain for paywall in known_paywall_sites):
            return "known_paywall"
        elif any(cf in domain for cf in cloudflare_heavy):
            return "cloudflare_protected"
        elif "news" in domain or "blog" in domain:
            return "news_blog_site"
        else:
            return "other_domain"

    def analyze_failure_trends(self) -> Dict[str, Any]:
        """Analyze trends in failure patterns."""
        total_failures = sum(self.failure_stats.values())

        if total_failures == 0:
            return {"message": "No failure patterns detected"}

        # Calculate percentages
        failure_percentages = {
            category: (count / total_failures) * 100
            for category, count in self.failure_stats.items()
        }

        # Sort by frequency
        sorted_failures = sorted(
            failure_percentages.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return {
            "total_failure_instances": total_failures,
            "top_failure_categories": sorted_failures[:10],
            "detailed_breakdown": dict(failure_percentages)
        }

    def generate_recommendations(self, trends: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on failure analysis."""
        recommendations = []

        if "top_failure_categories" not in trends:
            return ["No specific recommendations - insufficient failure data"]

        top_failures = trends["top_failure_categories"]

        for category, percentage in top_failures[:5]:
            if percentage > 20:  # Significant failure category
                if category == "paywall":
                    recommendations.append(
                        f"🔐 Paywall issues ({percentage:.1f}%): Implement authentication for major news sites or use archive.org fallback"
                    )
                elif category == "cloudflare":
                    recommendations.append(
                        f"☁️ Cloudflare protection ({percentage:.1f}%): Add user-agent rotation and request delays"
                    )
                elif category == "404_not_found":
                    recommendations.append(
                        f"🔍 404 errors ({percentage:.1f}%): Implement URL validation before processing"
                    )
                elif category == "timeout":
                    recommendations.append(
                        f"⏰ Timeout issues ({percentage:.1f}%): Increase timeout values and add retry logic"
                    )
                elif category == "server_error":
                    recommendations.append(
                        f"🔥 Server errors ({percentage:.1f}%): Implement exponential backoff retry strategy"
                    )

        if not recommendations:
            recommendations.append("✅ No major failure categories identified - system appears healthy")

        return recommendations

    def run_analysis(self) -> Dict[str, Any]:
        """Run complete failure analysis."""
        print("🔍 Starting article failure analysis...")

        # Find log files
        self.log_files = self.find_log_files()
        print(f"📁 Found {len(self.log_files)} log files to analyze")

        if not self.log_files:
            return {
                "error": "No log files found for analysis",
                "recommendations": ["Create proper logging for article fetching failures"]
            }

        # Analyze each log file
        file_results = []
        for log_file in self.log_files:
            result = self.analyze_log_file(log_file)
            file_results.append(result)

        # Extract failed URLs
        failed_urls = self.extract_urls_from_logs(self.log_files)
        categorized_urls = self.categorize_url_failures(failed_urls)

        # Analyze trends
        trends = self.analyze_failure_trends()

        # Generate recommendations
        recommendations = self.generate_recommendations(trends)

        # Compile comprehensive report
        report = {
            "analysis_timestamp": datetime.now().isoformat(),
            "log_files_analyzed": len(self.log_files),
            "file_details": file_results,
            "failure_trends": trends,
            "failed_urls": {
                "total_unique": len(failed_urls),
                "by_category": {k: len(v) for k, v in categorized_urls.items()},
                "examples": {k: v[:5] for k, v in categorized_urls.items()}  # First 5 of each
            },
            "recommendations": recommendations
        }

        return report


def main():
    """Main function to run article failure analysis."""
    analyzer = ArticleFailureAnalyzer()

    # Run analysis
    report = analyzer.run_analysis()

    # Save report
    os.makedirs("reports", exist_ok=True)
    report_file = f"reports/article_fetching_failures_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)

    # Generate markdown report
    md_file = report_file.replace('.json', '.md')
    generate_markdown_report(report, md_file)

    # Print summary
    print_summary(report)

    print(f"\n📄 Detailed report saved to: {report_file}")
    print(f"📝 Markdown report saved to: {md_file}")

    return report


def generate_markdown_report(report: Dict[str, Any], output_file: str) -> None:
    """Generate human-readable markdown report."""
    with open(output_file, 'w') as f:
        f.write("# Article Fetching Failures Analysis Report\n\n")
        f.write(f"**Generated:** {report['analysis_timestamp']}\n\n")

        # Summary
        f.write("## 📊 Summary\n\n")
        f.write(f"- **Log files analyzed:** {report['log_files_analyzed']}\n")

        if "failed_urls" in report:
            f.write(f"- **Unique failed URLs:** {report['failed_urls']['total_unique']}\n")

        if "failure_trends" in report and "total_failure_instances" in report["failure_trends"]:
            f.write(f"- **Total failure instances:** {report['failure_trends']['total_failure_instances']}\n")

        # Top failure categories
        if ("failure_trends" in report and
            "top_failure_categories" in report["failure_trends"]):
            f.write("\n## 🔥 Top Failure Categories\n\n")
            for category, percentage in report["failure_trends"]["top_failure_categories"]:
                f.write(f"- **{category.replace('_', ' ').title()}:** {percentage:.1f}%\n")

        # Recommendations
        f.write("\n## 💡 Recommendations\n\n")
        for i, rec in enumerate(report["recommendations"], 1):
            f.write(f"{i}. {rec}\n")

        # Failed URL categories
        if "failed_urls" in report and report["failed_urls"]["examples"]:
            f.write("\n## 🌐 Failed URL Examples by Category\n\n")
            for category, urls in report["failed_urls"]["examples"].items():
                if urls:
                    f.write(f"### {category.replace('_', ' ').title()}\n")
                    for url in urls:
                        f.write(f"- {url}\n")
                    f.write("\n")


def print_summary(report: Dict[str, Any]) -> None:
    """Print human-readable summary."""
    print("\n" + "="*60)
    print("📈 ARTICLE FETCHING FAILURE ANALYSIS")
    print("="*60)

    print(f"📁 Log files analyzed: {report['log_files_analyzed']}")

    if "failed_urls" in report:
        print(f"🔗 Unique failed URLs: {report['failed_urls']['total_unique']}")

    if ("failure_trends" in report and
        "total_failure_instances" in report["failure_trends"]):
        print(f"🔥 Total failure instances: {report['failure_trends']['total_failure_instances']}")

        print("\n🏆 Top Failure Categories:")
        for category, percentage in report["failure_trends"]["top_failure_categories"][:5]:
            print(f"  • {category.replace('_', ' ').title()}: {percentage:.1f}%")

    print("\n💡 Key Recommendations:")
    for i, rec in enumerate(report["recommendations"][:3], 1):
        print(f"  {i}. {rec}")


if __name__ == "__main__":
    main()