#!/usr/bin/env python3
"""
Compliance and safety check script for Atlas.
Run this periodically to ensure continued safe operation.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from helpers.config import load_config
from helpers.safety_monitor import SafetyMonitor


def main():
    """Run comprehensive compliance check."""
    config = load_config()
    monitor = SafetyMonitor(config)

    print("🔍 Running Atlas Compliance Check...")
    print("=" * 50)

    # Generate safety report
    report = monitor.generate_safety_report()

    # Display results
    if report["potential_issues"]:
        print("\n⚠️  Potential Issues Found:")
        for issue in report["potential_issues"]:
            print(f"   • {issue}")
    else:
        print("\n✅ No major compliance issues detected")

    print("\n📋 Recommendations:")
    for rec in report["recommendations"]:
        print(f"   • {rec}")

    # Save report
    report_path = os.path.join(
        config.get("data_directory", "output"), "compliance_report.json"
    )
    report["timestamp"] = datetime.now().isoformat()

    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n📄 Full report saved to: {report_path}")


if __name__ == "__main__":
    main()
