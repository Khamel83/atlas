#!/usr/bin/env python3
"""
Performance Baseline Measurement Tool
Establishes baseline metrics before refactoring
"""

import json
import time
import psutil
import os
from datetime import datetime
from pathlib import Path

class PerformanceBaseline:
    def __init__(self):
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'system_info': self.get_system_info(),
            'baselines': {}
        }

    def get_system_info(self):
        return {
            'cpu_count': psutil.cpu_count(),
            'memory_total': psutil.virtual_memory().total,
            'disk_free': psutil.disk_usage('.').free,
            'python_version': os.sys.version
        }

    def measure_file_processing_speed(self):
        """Measure how fast we can process files"""
        start_time = time.time()

        # Count existing processed files
        output_dir = Path('output')
        if output_dir.exists():
            article_files = len(list(output_dir.glob('**/*.json')))
            podcast_files = len(list((output_dir / 'podcasts').glob('*.json')) if (output_dir / 'podcasts').exists() else [])
        else:
            article_files = 0
            podcast_files = 0

        processing_time = time.time() - start_time

        return {
            'articles_count': article_files,
            'podcasts_count': podcast_files,
            'file_scan_time': processing_time,
            'scan_rate': (article_files + podcast_files) / max(processing_time, 0.001)
        }

    def measure_memory_usage(self):
        """Get current memory usage patterns"""
        process = psutil.Process()
        memory_info = process.memory_info()

        return {
            'rss_mb': memory_info.rss / 1024 / 1024,
            'vms_mb': memory_info.vms / 1024 / 1024,
            'percent': process.memory_percent(),
            'system_available_mb': psutil.virtual_memory().available / 1024 / 1024
        }

    def measure_disk_io_performance(self):
        """Basic disk I/O performance check"""
        start_time = time.time()

        # Write test file
        test_file = 'performance_test.tmp'
        test_data = 'x' * 10000  # 10KB test

        with open(test_file, 'w') as f:
            f.write(test_data)

        write_time = time.time() - start_time

        # Read test file
        start_time = time.time()
        with open(test_file, 'r') as f:
            _ = f.read()
        read_time = time.time() - start_time

        # Cleanup
        os.unlink(test_file)

        return {
            'write_time_ms': write_time * 1000,
            'read_time_ms': read_time * 1000,
            'write_rate_mb_s': (10 / 1024) / max(write_time, 0.001),
            'read_rate_mb_s': (10 / 1024) / max(read_time, 0.001)
        }

    def measure_import_performance(self):
        """Measure how long key imports take"""
        import_times = {}

        # Test key module imports
        modules = [
            'helpers.config',
            'helpers.article_fetcher',
            'helpers.podcast_ingestor',
            'helpers.youtube_ingestor',
            'helpers.utils'
        ]

        for module in modules:
            start_time = time.time()
            try:
                __import__(module)
                import_time = time.time() - start_time
                import_times[module] = {
                    'time_ms': import_time * 1000,
                    'success': True
                }
            except Exception as e:
                import_times[module] = {
                    'time_ms': -1,
                    'success': False,
                    'error': str(e)
                }

        return import_times

    def run_full_baseline(self):
        """Run complete baseline measurement suite"""
        print("🔍 Starting performance baseline measurement...")

        print("  📁 Measuring file processing...")
        self.results['baselines']['file_processing'] = self.measure_file_processing_speed()

        print("  💾 Measuring memory usage...")
        self.results['baselines']['memory'] = self.measure_memory_usage()

        print("  💾 Measuring disk I/O...")
        self.results['baselines']['disk_io'] = self.measure_disk_io_performance()

        print("  📦 Measuring import performance...")
        self.results['baselines']['imports'] = self.measure_import_performance()

        return self.results

    def save_baseline(self, filename='performance_baseline.json'):
        """Save baseline results to file"""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"✅ Baseline saved to {filename}")

    def print_summary(self):
        """Print human-readable summary"""
        print("\n📊 PERFORMANCE BASELINE SUMMARY")
        print("=" * 50)

        fp = self.results['baselines']['file_processing']
        print(f"📁 File Processing:")
        print(f"   Articles: {fp['articles_count']}")
        print(f"   Podcasts: {fp['podcasts_count']} (includes duplicates)")
        print(f"   Scan Rate: {fp['scan_rate']:.1f} files/sec")

        mem = self.results['baselines']['memory']
        print(f"💾 Memory Usage:")
        print(f"   RSS: {mem['rss_mb']:.1f} MB")
        print(f"   Percent: {mem['percent']:.1f}%")
        print(f"   Available: {mem['system_available_mb']:.1f} MB")

        disk = self.results['baselines']['disk_io']
        print(f"💽 Disk I/O:")
        print(f"   Write: {disk['write_rate_mb_s']:.1f} MB/s")
        print(f"   Read: {disk['read_rate_mb_s']:.1f} MB/s")

        imports = self.results['baselines']['imports']
        working_imports = sum(1 for i in imports.values() if i['success'])
        total_imports = len(imports)
        print(f"📦 Imports: {working_imports}/{total_imports} working")

        print("=" * 50)

if __name__ == '__main__':
    baseline = PerformanceBaseline()
    results = baseline.run_full_baseline()
    baseline.print_summary()
    baseline.save_baseline()