#!/usr/bin/env python3
"""
Atlas Content Validator
Automated quality scoring system for markdown content
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Tuple
import sqlite3
from datetime import datetime

class AtlasContentValidator:
    def __init__(self, db_path="podcast_processing.db"):
        self.db_path = db_path
        self.content_dir = Path("content/markdown")
        self.quality_log = []

    def calculate_quality_score(self, content: str, filename: str) -> Tuple[int, Dict]:
        """Calculate quality score (1-10) and return analysis details"""
        score = 0
        details = {
            "char_count": len(content),
            "word_count": len(content.split()),
            "paragraph_count": len([p for p in content.split('\n\n') if p.strip()]),
            "has_title": False,
            "has_proper_structure": False,
            "has_quotes": False,
            "has_subsections": False,
            "readability_score": 0,
            "issues": []
        }

        # Basic content length scoring
        if details["char_count"] > 5000:
            score += 3
        elif details["char_count"] > 2000:
            score += 2
        elif details["char_count"] > 500:
            score += 1
        else:
            details["issues"].append("Content too short")

        # Word count scoring
        if details["word_count"] > 1000:
            score += 2
        elif details["word_count"] > 300:
            score += 1

        # Structure analysis
        lines = content.split('\n')

        # Check for title (first line with # or just text)
        if lines and (lines[0].strip().startswith('#') or len(lines[0].strip()) > 20):
            details["has_title"] = True
            score += 1

        # Check for proper article structure
        if details["paragraph_count"] > 3:
            details["has_proper_structure"] = True
            score += 1

        # Check for quotes or excerpts
        if '"' in content or "'" in content or ">" in content:
            details["has_quotes"] = True
            score += 1

        # Check for subsections
        if any(line.strip().startswith('#') for line in lines[1:]):
            details["has_subsections"] = True
            score += 1

        # Readability check (simple version)
        sentences = [s.strip() for s in content.split('.') if s.strip()]
        if sentences:
            avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
            if 10 <= avg_sentence_length <= 25:  # Good readability range
                details["readability_score"] = 1
                score += 1

        # Penalty flags
        if "404" in content.upper() and "not found" in content.lower():
            score -= 5
            details["issues"].append("404 error page")

        if len(content) < 200:
            score -= 3
            details["issues"].append("Extremely short content")

        if details["word_count"] < 50:
            score -= 2
            details["issues"].append("Very few words")

        # Ensure score is within bounds
        score = max(1, min(10, score))
        details["final_score"] = score

        return score, details

    def scan_all_markdown_files(self) -> Dict:
        """Scan all markdown files and quality score them"""
        results = {
            "total_files": 0,
            "quality_distribution": {i: 0 for i in range(1, 11)},
            "tier_1_files": [],  # 9-10
            "tier_2_files": [],  # 6-8
            "tier_3_files": [],  # 1-5
            "detailed_results": []
        }

        if not self.content_dir.exists():
            print(f"Content directory {self.content_dir} does not exist")
            return results

        md_files = list(self.content_dir.glob("*.md"))
        results["total_files"] = len(md_files)

        print(f"🔍 Scanning {len(md_files)} markdown files for quality...")

        for i, md_file in enumerate(md_files):
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                score, details = self.calculate_quality_score(content, md_file.name)

                file_result = {
                    "filename": md_file.name,
                    "file_path": str(md_file),
                    "score": score,
                    "details": details,
                    "scan_time": datetime.now().isoformat()
                }

                results["detailed_results"].append(file_result)
                results["quality_distribution"][score] += 1

                # Categorize into tiers
                if score >= 9:
                    results["tier_1_files"].append(file_result)
                elif score >= 6:
                    results["tier_2_files"].append(file_result)
                else:
                    results["tier_3_files"].append(file_result)

                if (i + 1) % 100 == 0:
                    print(f"  Processed {i + 1}/{len(md_files)} files...")

            except Exception as e:
                print(f"❌ Error processing {md_file}: {e}")
                continue

        return results

    def save_quality_report(self, results: Dict):
        """Save quality analysis to database and files"""
        # Save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create quality tracking table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS content_quality (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT UNIQUE,
                file_path TEXT,
                quality_score INTEGER,
                quality_tier TEXT,
                char_count INTEGER,
                word_count INTEGER,
                paragraph_count INTEGER,
                issues TEXT,
                details TEXT,
                scan_time TIMESTAMP,
                needs_rescue BOOLEAN DEFAULT FALSE
            )
        """)

        # Clear existing records
        cursor.execute("DELETE FROM content_quality")

        # Insert results
        for file_result in results["detailed_results"]:
            details = file_result["details"]
            score = details["final_score"]

            if score >= 9:
                tier = "tier_1"
            elif score >= 6:
                tier = "tier_2"
            else:
                tier = "tier_3"

            cursor.execute("""
                INSERT INTO content_quality (
                    filename, file_path, quality_score, quality_tier,
                    char_count, word_count, paragraph_count,
                    issues, details, scan_time, needs_rescue
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                file_result["filename"],
                file_result["file_path"],
                score,
                tier,
                details["char_count"],
                details["word_count"],
                details["paragraph_count"],
                json.dumps(details["issues"]),
                json.dumps(details),
                file_result["scan_time"],
                score < 6  # Needs rescue if Tier 3
            ))

        conn.commit()
        conn.close()

        # Save detailed reports
        report_dir = Path("quality_reports")
        report_dir.mkdir(exist_ok=True)

        # Save tier-specific files for rescue processing
        with open(report_dir / "tier_3_rescue_queue.json", 'w') as f:
            json.dump(results["tier_3_files"], f, indent=2)

        with open(report_dir / "quality_summary.json", 'w') as f:
            summary = {
                "scan_time": datetime.now().isoformat(),
                "total_files": results["total_files"],
                "quality_distribution": results["quality_distribution"],
                "tier_counts": {
                    "tier_1": len(results["tier_1_files"]),
                    "tier_2": len(results["tier_2_files"]),
                    "tier_3": len(results["tier_3_files"])
                }
            }
            json.dump(summary, f, indent=2)

    def print_summary(self, results: Dict):
        """Print quality scan summary"""
        print(f"\n📊 Atlas Content Quality Report")
        print(f"📁 Total Files: {results['total_files']}")
        print(f"🏆 Tier 1 (9-10): {len(results['tier_1_files'])} files")
        print(f"✅ Tier 2 (6-8): {len(results['tier_2_files'])} files")
        print(f"⚠️  Tier 3 (1-5): {len(results['tier_3_files'])} files (need rescue)")

        print(f"\n📈 Quality Distribution:")
        for score in range(1, 11):
            count = results["quality_distribution"][score]
            bar = "█" * (count // 10)
            print(f"  {score:2d}: {count:4d} {bar}")

        if results["tier_3_files"]:
            print(f"\n🚨 Tier 3 Rescue Queue Created: {len(results['tier_3_files'])} files")
            print(f"   Ready for atlas_quality_rescue.py processing")

def main():
    validator = AtlasContentValidator()

    print("🔍 Atlas Content Validator Starting...")
    print("📂 Scanning content/markdown/ directory...")

    results = validator.scan_all_markdown_files()

    if results["total_files"] > 0:
        validator.save_quality_report(results)
        validator.print_summary(results)

        print(f"\n✅ Quality analysis complete!")
        print(f"📄 Reports saved to quality_reports/")
        print(f"🗄️  Data saved to {validator.db_path}")

        if results["tier_3_files"]:
            print(f"\n🚨 Ready to run: python3 atlas_quality_rescue.py")
        else:
            print(f"\n🎉 All content passed quality checks!")
    else:
        print("❌ No markdown files found to analyze")

if __name__ == "__main__":
    main()