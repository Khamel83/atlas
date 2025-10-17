#!/usr/bin/env python3
"""
Atlas Completion Analysis - Terminal states and completion criteria
"""

import json
import sys
from pathlib import Path
from collections import Counter, defaultdict


def analyze_completion_status():
    """Analyze terminal states and completion criteria"""

    print("🎯 Atlas Completion Analysis")
    print("=" * 50)

    # Articles analysis
    articles_dir = Path("output/articles/metadata/")
    if articles_dir.exists():
        analyze_articles(articles_dir)

    # Podcasts analysis
    podcasts_dir = Path("output/podcasts/")
    if podcasts_dir.exists():
        analyze_podcasts(podcasts_dir)

    # Overall completion assessment
    analyze_overall_completion()


def analyze_articles(articles_dir):
    """Analyze article processing completion"""
    print("\n📰 ARTICLES STATUS:")

    metadata_files = list(articles_dir.glob("*.json"))
    total_articles = len(metadata_files)

    if total_articles == 0:
        print("   No articles found")
        return

    # Count by status
    status_counts = Counter()
    error_types = Counter()
    terminal_failures = []

    for file_path in metadata_files:
        try:
            with open(file_path, "r") as f:
                metadata = json.load(f)
                status = metadata.get("status", "unknown")
                status_counts[status] += 1

                if status == "error":
                    error_msg = metadata.get("error", "unknown error")
                    error_types[error_msg] += 1

                    # Check for terminal failures
                    terminal_errors = [
                        "No archived snapshots found",
                        "404",
                        "Access denied",
                        "Paywall blocked",
                        "Site permanently unavailable",
                    ]

                    if any(term in error_msg for term in terminal_errors):
                        terminal_failures.append(
                            {
                                "uid": metadata.get("uid"),
                                "source": metadata.get("source"),
                                "error": error_msg,
                            }
                        )

        except Exception as e:
            print(f"   Error reading {file_path}: {e}")

    # Results
    success_rate = (status_counts["success"] / total_articles) * 100
    print(f"   Total articles: {total_articles:,}")
    print(f"   ✅ Successful: {status_counts['success']:,} ({success_rate:.1f}%)")
    print(f"   ❌ Failed: {status_counts['error']:,}")
    print(
        f"   ⏳ Other: {total_articles - status_counts['success'] - status_counts['error']:,}"
    )

    print(f"\n📊 Top Error Types:")
    for error, count in error_types.most_common(5):
        print(f"   {error}: {count:,} articles")

    print(f"\n🚫 Terminal Failures: {len(terminal_failures):,}")
    if len(terminal_failures) > 0:
        print("   These are likely permanently unrecoverable:")
        for failure in terminal_failures[:5]:  # Show first 5
            print(f"   • {failure['error']}")
        if len(terminal_failures) > 5:
            print(f"   ... and {len(terminal_failures) - 5} more")


def analyze_podcasts(podcasts_dir):
    """Analyze podcast processing completion"""
    print("\n🎙️ PODCASTS STATUS:")

    # Count processed podcasts
    processed_podcasts = list(podcasts_dir.glob("*.json"))
    transcript_files = list(podcasts_dir.glob("*/transcript.txt"))

    print(f"   Total podcast entries: {len(processed_podcasts):,}")
    print(f"   With transcripts: {len(transcript_files):,}")

    if len(processed_podcasts) > 0:
        transcript_rate = (len(transcript_files) / len(processed_podcasts)) * 100
        print(f"   Transcript success rate: {transcript_rate:.1f}%")


def analyze_overall_completion():
    """Analyze overall completion and terminal states"""
    print("\n🎯 COMPLETION ASSESSMENT:")

    # Check remaining inputs
    inputs_dir = Path("inputs/")
    remaining_files = 0

    if inputs_dir.exists():
        for pattern in ["*.txt", "*.csv", "Docs/*.html"]:
            remaining_files += len(list(inputs_dir.glob(pattern)))

    print(f"   📁 Remaining input files: {remaining_files:,}")

    # Completion criteria
    print(f"\n✅ COMPLETION CRITERIA:")

    # Calculate theoretical vs practical completion
    articles_dir = Path("output/articles/metadata/")
    if articles_dir.exists():
        metadata_files = list(articles_dir.glob("*.json"))
        total_processed = len(metadata_files)

        terminal_count = 0
        retryable_count = 0

        for file_path in metadata_files:
            try:
                with open(file_path, "r") as f:
                    metadata = json.load(f)
                    if metadata.get("status") == "error":
                        error_msg = metadata.get("error", "")

                        # Terminal errors (no point retrying)
                        terminal_errors = [
                            "No archived snapshots found",
                            "404",
                            "permanently unavailable",
                            "does not exist",
                        ]

                        if any(term in error_msg.lower() for term in terminal_errors):
                            terminal_count += 1
                        else:
                            retryable_count += 1

            except Exception:
                continue

        success_count = 0
        for file_path in metadata_files:
            try:
                with open(file_path, "r") as f:
                    metadata = json.load(f)
                    if metadata.get("status") == "success":
                        success_count += 1
            except Exception:
                continue

        theoretical_max = total_processed - terminal_count
        if theoretical_max > 0:
            practical_completion = (success_count / theoretical_max) * 100
            print(
                f"   📊 Current success rate: {(success_count/total_processed)*100:.1f}% of all content"
            )
            print(
                f"   🎯 Practical completion: {practical_completion:.1f}% of recoverable content"
            )
            print(f"   🚫 Terminal failures: {terminal_count:,} (permanently lost)")
            print(
                f"   🔄 Retryable failures: {retryable_count:,} (could recover with new methods)"
            )

            if practical_completion > 95:
                print(f"   ✅ RECOMMENDATION: Near-complete! Focus on new content.")
            elif practical_completion > 80:
                print(
                    f"   ⚡ RECOMMENDATION: Good progress. Consider enhanced recovery for retryable failures."
                )
            else:
                print(
                    f"   🔧 RECOMMENDATION: Continue processing. Significant room for improvement."
                )

    # Time to completion estimate
    if remaining_files > 0:
        print(f"\n⏱️ TIME TO COMPLETION:")
        print(f"   At current rate: {remaining_files} files remaining")
        print(f"   Estimated time: Continue background processing")


def show_terminal_failures(limit=20):
    """Show terminal failures that should be excluded from retry"""
    print(f"\n🚫 TERMINAL FAILURES (first {limit}):")
    print("   These should be excluded from future processing:")

    articles_dir = Path("output/articles/metadata/")
    if not articles_dir.exists():
        print("   No metadata directory found")
        return

    terminal_failures = []
    for file_path in articles_dir.glob("*.json"):
        try:
            with open(file_path, "r") as f:
                metadata = json.load(f)
                if metadata.get("status") == "error":
                    error_msg = metadata.get("error", "")

                    terminal_errors = [
                        "No archived snapshots found",
                        "404",
                        "permanently unavailable",
                        "does not exist",
                    ]

                    if any(term in error_msg.lower() for term in terminal_errors):
                        terminal_failures.append(
                            {
                                "source": metadata.get("source"),
                                "error": error_msg,
                                "uid": metadata.get("uid"),
                            }
                        )
        except Exception:
            continue

    for i, failure in enumerate(terminal_failures[:limit]):
        print(f"   {i+1:2d}. {failure['error']}")
        print(f"       {failure['source'][:80]}...")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--terminal":
        show_terminal_failures()
    else:
        analyze_completion_status()
