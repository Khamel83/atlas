#!/usr/bin/env python3
"""
Database Audit Tool for Atlas - Phase 3.1
Identifies database bloat, duplicates, and optimization opportunities
"""

import sqlite3
import os
import sys
from pathlib import Path
import json
from datetime import datetime

class AtlasDatabaseAuditor:
    def __init__(self, base_path="/home/ubuntu/dev/atlas"):
        self.base_path = Path(base_path)
        self.databases = {}
        self.audit_results = {}

    def find_databases(self):
        """Find all SQLite databases in the Atlas directory"""
        print("🔍 Finding all database files...")

        # Known database locations
        db_patterns = [
            "*.db",
            "**/*.db"
        ]

        found_dbs = []
        for pattern in db_patterns:
            found_dbs.extend(list(self.base_path.glob(pattern)))

        # Remove duplicates and sort
        unique_dbs = sorted(set(found_dbs))

        for db_path in unique_dbs:
            if db_path.exists() and db_path.stat().st_size > 0:
                self.databases[db_path.name] = str(db_path)

        print(f"📊 Found {len(self.databases)} database files")
        return self.databases

    def analyze_database(self, db_path):
        """Analyze a single database for size, tables, and content quality"""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            analysis = {
                'path': db_path,
                'size_mb': Path(db_path).stat().st_size / (1024 * 1024),
                'tables': {},
                'total_records': 0,
                'quality_issues': []
            }

            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()

            for (table_name,) in tables:
                try:
                    # Count records
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = cursor.fetchone()[0]
                    analysis['total_records'] += count

                    # Get table schema
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns = cursor.fetchall()

                    # Sample some data for quality assessment
                    cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
                    sample_data = cursor.fetchall()

                    # Check for potential junk data
                    junk_indicators = self.assess_data_quality(table_name, sample_data, cursor)

                    analysis['tables'][table_name] = {
                        'records': count,
                        'columns': len(columns),
                        'column_names': [col[1] for col in columns],
                        'sample_data': len(sample_data),
                        'quality_issues': junk_indicators
                    }

                    if junk_indicators:
                        analysis['quality_issues'].extend(junk_indicators)

                except Exception as e:
                    analysis['tables'][table_name] = {'error': str(e)}

            conn.close()
            return analysis

        except Exception as e:
            return {'path': db_path, 'error': str(e)}

    def assess_data_quality(self, table_name, sample_data, cursor):
        """Assess data quality and identify potential junk entries"""
        issues = []

        try:
            # Check for suspiciously short content
            if 'content' in [desc[0] for desc in cursor.description]:
                content_idx = [desc[0] for desc in cursor.description].index('content')
                short_content = [row for row in sample_data if row[content_idx] and len(str(row[content_idx])) < 100]
                if len(short_content) > len(sample_data) * 0.5:
                    issues.append(f"High percentage of very short content in {table_name}")

            # Check for HTML interface junk (Instapaper issue)
            if sample_data:
                for row in sample_data:
                    row_str = ' '.join([str(cell) for cell in row if cell])
                    if any(indicator in row_str.lower() for indicator in [
                        'instapaper', 'loading', 'javascript', 'cookie', 'login',
                        'interface', 'navigation', 'menu', 'header', 'footer'
                    ]):
                        issues.append(f"Potential interface HTML junk detected in {table_name}")
                        break

            # Check for duplicates
            if len(sample_data) != len(set(sample_data)):
                issues.append(f"Duplicate records detected in {table_name}")

        except Exception as e:
            issues.append(f"Quality assessment failed for {table_name}: {e}")

        return issues

    def estimate_junk_entries(self, db_path):
        """Estimate how many entries are likely junk based on patterns"""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            junk_estimates = {}

            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()

            for (table_name,) in tables:
                total_count = 0
                junk_count = 0

                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    total_count = cursor.fetchone()[0]

                    # Check for content-based junk indicators
                    if 'content' in [desc[1] for desc in cursor.execute(f"PRAGMA table_info({table_name})").fetchall()]:
                        # Very short content (likely interface elements)
                        cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE LENGTH(content) < 200")
                        short_content = cursor.fetchone()[0]

                        # Content with interface keywords
                        interface_keywords = ['instapaper', 'javascript', 'loading', 'cookie policy', 'navigation']
                        for keyword in interface_keywords:
                            cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE content LIKE '%{keyword}%'")
                            junk_count += cursor.fetchone()[0]

                        junk_count += short_content

                    # Remove double counting
                    junk_count = min(junk_count, total_count)

                    junk_estimates[table_name] = {
                        'total': total_count,
                        'estimated_junk': junk_count,
                        'estimated_legitimate': total_count - junk_count
                    }

                except Exception as e:
                    junk_estimates[table_name] = {'error': str(e)}

            conn.close()
            return junk_estimates

        except Exception as e:
            return {'error': str(e)}

    def run_full_audit(self):
        """Run comprehensive audit of all databases"""
        print("🚀 Starting Atlas Database Audit...")

        # Find all databases
        self.find_databases()

        # Analyze each database
        for db_name, db_path in self.databases.items():
            print(f"\n📊 Analyzing {db_name}...")

            analysis = self.analyze_database(db_path)
            junk_estimates = self.estimate_junk_entries(db_path)

            self.audit_results[db_name] = {
                'analysis': analysis,
                'junk_estimates': junk_estimates,
                'timestamp': datetime.now().isoformat()
            }

        return self.audit_results

    def generate_report(self):
        """Generate comprehensive audit report"""
        report = {
            'audit_timestamp': datetime.now().isoformat(),
            'summary': {
                'total_databases': len(self.databases),
                'total_size_mb': 0,
                'total_records': 0,
                'estimated_junk_records': 0,
                'databases_with_issues': 0
            },
            'databases': self.audit_results,
            'recommendations': []
        }

        # Calculate summary statistics
        for db_name, results in self.audit_results.items():
            analysis = results.get('analysis', {})
            if 'size_mb' in analysis:
                report['summary']['total_size_mb'] += analysis['size_mb']
                report['summary']['total_records'] += analysis.get('total_records', 0)

            if analysis.get('quality_issues'):
                report['summary']['databases_with_issues'] += 1

            # Sum up junk estimates
            junk_estimates = results.get('junk_estimates', {})
            for table_estimates in junk_estimates.values():
                if isinstance(table_estimates, dict) and 'estimated_junk' in table_estimates:
                    report['summary']['estimated_junk_records'] += table_estimates['estimated_junk']

        # Generate recommendations
        if report['summary']['estimated_junk_records'] > 1000:
            report['recommendations'].append("High volume of junk entries detected - database cleanup recommended")

        if report['summary']['total_size_mb'] > 100:
            report['recommendations'].append("Large database size - consider archiving old data")

        if report['summary']['databases_with_issues'] > 2:
            report['recommendations'].append("Multiple databases have quality issues - systematic cleanup needed")

        return report

def main():
    """Main function to run database audit"""
    auditor = AtlasDatabaseAuditor()

    print("🎯 Atlas Database Audit - Phase 3.1")
    print("=" * 50)

    # Run full audit
    results = auditor.run_full_audit()

    # Generate report
    report = auditor.generate_report()

    # Save results
    docs_dir = Path("/home/ubuntu/dev/atlas/docs")
    docs_dir.mkdir(exist_ok=True)

    with open(docs_dir / "database_audit.json", 'w') as f:
        json.dump(report, f, indent=2)

    # Print summary
    print("\n" + "=" * 50)
    print("📊 AUDIT SUMMARY")
    print("=" * 50)
    print(f"Total Databases: {report['summary']['total_databases']}")
    print(f"Total Size: {report['summary']['total_size_mb']:.1f} MB")
    print(f"Total Records: {report['summary']['total_records']:,}")
    print(f"Estimated Junk: {report['summary']['estimated_junk_records']:,}")
    print(f"Databases with Issues: {report['summary']['databases_with_issues']}")

    print("\n🎯 RECOMMENDATIONS:")
    for rec in report['recommendations']:
        print(f"• {rec}")

    print(f"\n📄 Full report saved to: {docs_dir / 'database_audit.json'}")

    return report

if __name__ == "__main__":
    main()