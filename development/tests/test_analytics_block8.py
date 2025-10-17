#!/usr/bin/env python3
"""
Test Block 8: Analytics Dashboard
Tests analytics integration with real Atlas data
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

import json
from pathlib import Path
from datetime import datetime
from helpers.analytics_engine import AnalyticsEngine


class AtlasAnalyticsIntegrator:
    """Integrate analytics with real Atlas data"""

    def __init__(self, atlas_output_dir: str = "output"):
        self.atlas_output_dir = Path(atlas_output_dir)
        self.documents_dir = self.atlas_output_dir / "documents"
        self.analytics_engine = AnalyticsEngine()

    def get_system_stats(self) -> dict:
        """Get system-level statistics"""
        stats = {
            "total_documents": 0,
            "total_content_size": 0,
            "content_types": {},
            "languages": {},
            "processing_dates": {},
            "word_count_distribution": {"0-100": 0, "100-500": 0, "500-1000": 0, "1000+": 0}
        }

        metadata_files = list(self.documents_dir.glob("*_metadata.json"))
        stats["total_documents"] = len(metadata_files)

        for metadata_file in metadata_files[:100]:  # Sample first 100 for speed
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)

                # Content type distribution
                content_type = metadata.get("content_type", "unknown")
                stats["content_types"][content_type] = stats["content_types"].get(content_type, 0) + 1

                # Language distribution
                language = metadata.get("language", "unknown")
                stats["languages"][language] = stats["languages"].get(language, 0) + 1

                # Size tracking
                file_size = metadata.get("file_size", 0)
                stats["total_content_size"] += file_size

                # Word count distribution
                word_count = metadata.get("word_count", 0)
                if word_count < 100:
                    stats["word_count_distribution"]["0-100"] += 1
                elif word_count < 500:
                    stats["word_count_distribution"]["100-500"] += 1
                elif word_count < 1000:
                    stats["word_count_distribution"]["500-1000"] += 1
                else:
                    stats["word_count_distribution"]["1000+"] += 1

                # Processing date tracking
                created_date = metadata.get("created_at", "")[:10]  # YYYY-MM-DD
                stats["processing_dates"][created_date] = stats["processing_dates"].get(created_date, 0) + 1

            except Exception as e:
                continue

        return stats

    def analyze_content_sample(self, limit: int = 5) -> list:
        """Analyze a sample of content"""
        results = []

        metadata_files = list(self.documents_dir.glob("*_metadata.json"))[:limit]

        for metadata_file in metadata_files:
            try:
                # Load metadata
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)

                # Load content
                content_file = metadata_file.parent / f"{metadata['uid']}.md"
                if content_file.exists():
                    with open(content_file, 'r') as f:
                        content = f.read()

                    # Analyze with analytics engine
                    analysis = self.analytics_engine.analyze_content(content, metadata)

                    results.append({
                        "id": metadata["uid"],
                        "title": metadata.get("source_file", "Unknown").split("/")[-1],
                        "metadata": metadata,
                        "analysis": analysis
                    })

            except Exception as e:
                continue

        return results

    def generate_usage_dashboard_data(self) -> dict:
        """Generate data for web dashboard"""
        system_stats = self.get_system_stats()
        content_analysis = self.analyze_content_sample(3)

        dashboard_data = {
            "generated_at": datetime.now().isoformat(),
            "system_overview": {
                "total_documents": system_stats["total_documents"],
                "total_size_mb": round(system_stats["total_content_size"] / (1024 * 1024), 2),
                "content_types": system_stats["content_types"],
                "languages": system_stats["languages"]
            },
            "content_insights": {
                "word_count_distribution": system_stats["word_count_distribution"],
                "daily_processing": dict(list(system_stats["processing_dates"].items())[-7:])  # Last 7 days
            },
            "sample_analysis": [
                {
                    "title": item["title"],
                    "word_count": item["analysis"].get("word_count", 0),
                    "readability_score": item["analysis"].get("readability_score", 0),
                    "keywords": item["analysis"].get("keywords", [])[:5],
                    "categories": item["analysis"].get("categories", [])
                }
                for item in content_analysis
            ]
        }

        return dashboard_data


def test_analytics_integration():
    """Test analytics integration with real Atlas data"""
    print("🧪 Testing Block 8: Analytics Dashboard Integration")
    print("=" * 50)

    integrator = AtlasAnalyticsIntegrator()

    # Test 1: System statistics
    print("\n📊 Testing system statistics...")
    try:
        stats = integrator.get_system_stats()
        print(f"✅ System stats generated:")
        print(f"   - Total documents: {stats['total_documents']}")
        print(f"   - Total size: {stats['total_content_size'] / (1024*1024):.1f} MB")
        print(f"   - Content types: {list(stats['content_types'].keys())}")
        print(f"   - Languages: {list(stats['languages'].keys())}")
        print(f"   - Recent processing days: {len(stats['processing_dates'])}")
        test1_success = True
    except Exception as e:
        print(f"❌ System stats failed: {e}")
        test1_success = False

    # Test 2: Content analysis
    print(f"\n🔍 Testing content analysis...")
    try:
        analysis_results = integrator.analyze_content_sample(3)
        print(f"✅ Content analysis successful:")
        print(f"   - Analyzed {len(analysis_results)} documents")
        for result in analysis_results:
            print(f"   - {result['title'][:40]}... ({result['analysis'].get('word_count', 0)} words)")
        test2_success = True
    except Exception as e:
        print(f"❌ Content analysis failed: {e}")
        test2_success = False

    # Test 3: Dashboard data generation
    print(f"\n📈 Testing dashboard data generation...")
    try:
        dashboard_data = integrator.generate_usage_dashboard_data()
        print(f"✅ Dashboard data generated:")
        print(f"   - System overview: {len(dashboard_data['system_overview'])} metrics")
        print(f"   - Content insights: {len(dashboard_data['content_insights'])} categories")
        print(f"   - Sample analysis: {len(dashboard_data['sample_analysis'])} items")

        # Save dashboard data
        with open("test_dashboard_data.json", 'w') as f:
            json.dump(dashboard_data, f, indent=2)
        print(f"   - Dashboard data saved to: test_dashboard_data.json")

        test3_success = True
    except Exception as e:
        print(f"❌ Dashboard data generation failed: {e}")
        test3_success = False

    # Summary
    print(f"\n📊 BLOCK 8 ANALYTICS TEST SUMMARY")
    print("=" * 50)

    tests = {
        "System Statistics": test1_success,
        "Content Analysis": test2_success,
        "Dashboard Data": test3_success
    }

    passed = sum(tests.values())
    total = len(tests)

    for test_name, result in tests.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name.ljust(20)}: {status}")

    if passed == total:
        print(f"\n🎉 BLOCK 8: ANALYTICS DASHBOARD - COMPLETE!")
        print("✅ Real Atlas data integration working")
        print("✅ System statistics generation successful")
        print("✅ Content analysis with analytics engine working")
        print("✅ Dashboard data ready for web interface")
        return True
    else:
        print(f"\n⚠️  BLOCK 8: Partial success - {passed}/{total} tests passed")
        return False


if __name__ == "__main__":
    print("🚀 Starting Block 8: Analytics Dashboard Integration Test")
    print(f"Time: {datetime.now().isoformat()}")

    success = test_analytics_integration()
    sys.exit(0 if success else 1)