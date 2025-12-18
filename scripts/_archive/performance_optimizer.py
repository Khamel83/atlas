#!/usr/bin/env python3
"""
Performance optimization recommendations and analysis
"""

import json
import psutil
import time
import logging
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# Add helpers to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from helpers.resource_manager import ResourceManager, ResourceMetrics

@dataclass
class PerformanceIssue:
    """Container for performance issues"""
    severity: str  # low, medium, high, critical
    category: str  # memory, cpu, disk, network, system
    title: str
    description: str
    recommendation: str
    impact: str
    priority: int  # 1-10

class PerformanceOptimizer:
    """Analyzes system performance and provides optimization recommendations"""

    def __init__(self, config_path: str = "data/performance_config.json"):
        self.config_path = config_path
        self.logger = self._setup_logging()
        self.config = self._load_config()
        self.resource_manager = ResourceManager()

    def _setup_logging(self) -> logging.Logger:
        """Setup logging for performance optimizer"""
        logger = logging.getLogger('performance_optimizer')
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.FileHandler('data/performance_optimizer.log')
            os.makedirs(os.path.dirname('data/performance_optimizer.log'), exist_ok=True)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def _load_config(self) -> Dict:
        """Load performance optimization configuration"""
        default_config = {
            "thresholds": {
                "cpu_high": 80.0,
                "cpu_critical": 95.0,
                "memory_high": 80.0,
                "memory_critical": 95.0,
                "disk_high": 80.0,
                "disk_critical": 95.0,
                "load_high": 2.0,
                "load_critical": 5.0,
                "iowait_high": 20.0,
                "response_time_high": 1000  # ms
            },
            "analysis": {
                "sample_duration": 60,  # seconds
                "history_days": 7,
                "min_samples": 10
            },
            "recommendations": {
                "include_system_tweaks": True,
                "include_application_optimizations": True,
                "include_hardware_recommendations": True
            }
        }

        try:
            if Path(self.config_path).exists():
                with open(self.config_path) as f:
                    config = json.load(f)
                # Merge with defaults
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
            else:
                self._save_config(default_config)
                return default_config
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            return default_config

    def _save_config(self, config: Dict):
        """Save configuration to file"""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving config: {e}")

    def collect_performance_sample(self, duration: int = 60) -> Dict:
        """Collect detailed performance metrics over a period"""
        self.logger.info(f"Collecting performance sample for {duration} seconds...")

        samples = []
        start_time = time.time()
        sample_interval = 5  # seconds

        while (time.time() - start_time) < duration:
            try:
                # CPU metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                cpu_times = psutil.cpu_times_percent()
                load_avg = os.getloadavg()

                # Memory metrics
                memory = psutil.virtual_memory()
                swap = psutil.swap_memory()

                # Disk metrics
                disk_usage = psutil.disk_usage('/')
                disk_io = psutil.disk_io_counters()

                # Network metrics (if available)
                try:
                    network_io = psutil.net_io_counters()
                except:
                    network_io = None

                # Process metrics
                try:
                    process_count = len(psutil.pids())
                    processes_by_memory = sorted(
                        [p.info for p in psutil.process_iter(['pid', 'memory_percent', 'name'])],
                        key=lambda x: x.get('memory_percent', 0),
                        reverse=True
                    )[:5]  # Top 5 by memory

                    processes_by_cpu = sorted(
                        [p.info for p in psutil.process_iter(['pid', 'cpu_percent', 'name'])],
                        key=lambda x: x.get('cpu_percent', 0),
                        reverse=True
                    )[:5]  # Top 5 by CPU
                except:
                    process_count = 0
                    processes_by_memory = []
                    processes_by_cpu = []

                sample = {
                    'timestamp': datetime.now().isoformat(),
                    'cpu': {
                        'percent': cpu_percent,
                        'user': cpu_times.user,
                        'system': cpu_times.system,
                        'idle': cpu_times.idle,
                        'iowait': getattr(cpu_times, 'iowait', 0),
                        'load_avg': load_avg
                    },
                    'memory': {
                        'percent': memory.percent,
                        'available': memory.available,
                        'used': memory.used,
                        'total': memory.total,
                        'swap_percent': swap.percent,
                        'swap_used': swap.used
                    },
                    'disk': {
                        'percent': (disk_usage.used / disk_usage.total) * 100,
                        'total': disk_usage.total,
                        'used': disk_usage.used,
                        'free': disk_usage.free
                    },
                    'processes': {
                        'count': process_count,
                        'top_memory': processes_by_memory,
                        'top_cpu': processes_by_cpu
                    }
                }

                if disk_io:
                    sample['disk_io'] = {
                        'read_bytes': disk_io.read_bytes,
                        'write_bytes': disk_io.write_bytes,
                        'read_count': disk_io.read_count,
                        'write_count': disk_io.write_count
                    }

                if network_io:
                    sample['network'] = {
                        'bytes_sent': network_io.bytes_sent,
                        'bytes_recv': network_io.bytes_recv,
                        'packets_sent': network_io.packets_sent,
                        'packets_recv': network_io.packets_recv
                    }

                samples.append(sample)
                time.sleep(sample_interval)

            except Exception as e:
                self.logger.error(f"Error collecting sample: {e}")
                continue

        return {
            'duration': duration,
            'sample_count': len(samples),
            'samples': samples,
            'analysis_timestamp': datetime.now().isoformat()
        }

    def analyze_performance_trends(self, sample_data: Dict) -> Dict:
        """Analyze performance trends from sample data"""
        if not sample_data.get('samples'):
            return {'error': 'No sample data available'}

        samples = sample_data['samples']
        analysis = {
            'cpu_analysis': self._analyze_cpu_trends(samples),
            'memory_analysis': self._analyze_memory_trends(samples),
            'disk_analysis': self._analyze_disk_trends(samples),
            'process_analysis': self._analyze_process_trends(samples)
        }

        return analysis

    def _analyze_cpu_trends(self, samples: List[Dict]) -> Dict:
        """Analyze CPU performance trends"""
        cpu_data = [s['cpu'] for s in samples if 'cpu' in s]
        if not cpu_data:
            return {'error': 'No CPU data available'}

        cpu_percents = [d['percent'] for d in cpu_data]
        load_avgs = [d['load_avg'][0] for d in cpu_data]  # 1-minute load
        iowait_values = [d.get('iowait', 0) for d in cpu_data]

        analysis = {
            'cpu_utilization': {
                'average': sum(cpu_percents) / len(cpu_percents),
                'max': max(cpu_percents),
                'min': min(cpu_percents),
                'variance': self._calculate_variance(cpu_percents)
            },
            'load_average': {
                'average': sum(load_avgs) / len(load_avgs),
                'max': max(load_avgs),
                'min': min(load_avgs)
            },
            'iowait': {
                'average': sum(iowait_values) / len(iowait_values),
                'max': max(iowait_values)
            }
        }

        # Detect patterns
        analysis['patterns'] = []

        if analysis['cpu_utilization']['average'] > self.config['thresholds']['cpu_high']:
            analysis['patterns'].append('high_cpu_utilization')

        if analysis['load_average']['average'] > self.config['thresholds']['load_high']:
            analysis['patterns'].append('high_load_average')

        if analysis['iowait']['average'] > self.config['thresholds']['iowait_high']:
            analysis['patterns'].append('high_iowait')

        if analysis['cpu_utilization']['variance'] > 500:  # High variance
            analysis['patterns'].append('cpu_usage_spikes')

        return analysis

    def _analyze_memory_trends(self, samples: List[Dict]) -> Dict:
        """Analyze memory performance trends"""
        memory_data = [s['memory'] for s in samples if 'memory' in s]
        if not memory_data:
            return {'error': 'No memory data available'}

        mem_percents = [d['percent'] for d in memory_data]
        swap_percents = [d['swap_percent'] for d in memory_data]

        analysis = {
            'memory_utilization': {
                'average': sum(mem_percents) / len(mem_percents),
                'max': max(mem_percents),
                'min': min(mem_percents),
                'trend': self._calculate_trend(mem_percents)
            },
            'swap_usage': {
                'average': sum(swap_percents) / len(swap_percents),
                'max': max(swap_percents)
            }
        }

        # Detect patterns
        analysis['patterns'] = []

        if analysis['memory_utilization']['average'] > self.config['thresholds']['memory_high']:
            analysis['patterns'].append('high_memory_usage')

        if analysis['swap_usage']['average'] > 10:  # More than 10% swap usage
            analysis['patterns'].append('swap_usage')

        if analysis['memory_utilization']['trend'] > 0.5:  # Increasing trend
            analysis['patterns'].append('memory_leak_potential')

        return analysis

    def _analyze_disk_trends(self, samples: List[Dict]) -> Dict:
        """Analyze disk performance trends"""
        disk_data = [s['disk'] for s in samples if 'disk' in s]
        if not disk_data:
            return {'error': 'No disk data available'}

        disk_percents = [d['percent'] for d in disk_data]

        analysis = {
            'disk_utilization': {
                'average': sum(disk_percents) / len(disk_percents),
                'max': max(disk_percents),
                'min': min(disk_percents)
            }
        }

        # Analyze disk I/O if available
        disk_io_data = [s.get('disk_io') for s in samples if s.get('disk_io')]
        if disk_io_data and len(disk_io_data) > 1:
            read_rates = []
            write_rates = []

            for i in range(1, len(disk_io_data)):
                time_diff = 5  # seconds between samples
                read_diff = disk_io_data[i]['read_bytes'] - disk_io_data[i-1]['read_bytes']
                write_diff = disk_io_data[i]['write_bytes'] - disk_io_data[i-1]['write_bytes']

                read_rates.append(read_diff / time_diff)
                write_rates.append(write_diff / time_diff)

            if read_rates:
                analysis['disk_io'] = {
                    'read_rate_avg': sum(read_rates) / len(read_rates),
                    'write_rate_avg': sum(write_rates) / len(write_rates),
                    'read_rate_max': max(read_rates),
                    'write_rate_max': max(write_rates)
                }

        # Detect patterns
        analysis['patterns'] = []

        if analysis['disk_utilization']['average'] > self.config['thresholds']['disk_high']:
            analysis['patterns'].append('high_disk_usage')

        return analysis

    def _analyze_process_trends(self, samples: List[Dict]) -> Dict:
        """Analyze process-related trends"""
        process_data = [s.get('processes', {}) for s in samples]
        process_counts = [d.get('count', 0) for d in process_data if d.get('count')]

        if not process_counts:
            return {'error': 'No process data available'}

        analysis = {
            'process_count': {
                'average': sum(process_counts) / len(process_counts),
                'max': max(process_counts),
                'min': min(process_counts)
            }
        }

        # Analyze top processes
        all_memory_processes = []
        all_cpu_processes = []

        for data in process_data:
            if data.get('top_memory'):
                all_memory_processes.extend(data['top_memory'])
            if data.get('top_cpu'):
                all_cpu_processes.extend(data['top_cpu'])

        # Find most frequent memory consumers
        memory_consumers = {}
        for proc in all_memory_processes:
            if proc and proc.get('name'):
                name = proc['name']
                if name not in memory_consumers:
                    memory_consumers[name] = []
                if proc.get('memory_percent'):
                    memory_consumers[name].append(proc['memory_percent'])

        # Find most frequent CPU consumers
        cpu_consumers = {}
        for proc in all_cpu_processes:
            if proc and proc.get('name'):
                name = proc['name']
                if name not in cpu_consumers:
                    cpu_consumers[name] = []
                if proc.get('cpu_percent'):
                    cpu_consumers[name].append(proc['cpu_percent'])

        analysis['top_memory_consumers'] = {
            name: {
                'average': sum(values) / len(values),
                'max': max(values),
                'samples': len(values)
            }
            for name, values in memory_consumers.items()
            if len(values) >= 3  # At least 3 samples
        }

        analysis['top_cpu_consumers'] = {
            name: {
                'average': sum(values) / len(values),
                'max': max(values),
                'samples': len(values)
            }
            for name, values in cpu_consumers.items()
            if len(values) >= 3  # At least 3 samples
        }

        return analysis

    def _calculate_variance(self, values: List[float]) -> float:
        """Calculate variance of values"""
        if len(values) < 2:
            return 0

        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance

    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend direction (-1 to 1, where 1 is increasing)"""
        if len(values) < 2:
            return 0

        # Simple linear trend calculation
        n = len(values)
        sum_x = sum(range(n))
        sum_y = sum(values)
        sum_xy = sum(i * values[i] for i in range(n))
        sum_x_squared = sum(i ** 2 for i in range(n))

        # Linear regression slope
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x_squared - sum_x ** 2)

        # Normalize to -1 to 1 range
        max_possible_slope = max(values) - min(values) if max(values) != min(values) else 1
        normalized_slope = slope / max_possible_slope if max_possible_slope != 0 else 0

        return max(-1, min(1, normalized_slope))

    def generate_performance_issues(self, analysis: Dict) -> List[PerformanceIssue]:
        """Generate performance issues from analysis"""
        issues = []

        # CPU issues
        cpu_analysis = analysis.get('cpu_analysis', {})
        if 'high_cpu_utilization' in cpu_analysis.get('patterns', []):
            cpu_avg = cpu_analysis.get('cpu_utilization', {}).get('average', 0)
            severity = 'critical' if cpu_avg > 95 else 'high'

            issues.append(PerformanceIssue(
                severity=severity,
                category='cpu',
                title='High CPU Utilization',
                description=f'Average CPU usage is {cpu_avg:.1f}%, which exceeds recommended thresholds.',
                recommendation='Consider optimizing CPU-intensive processes, adding more CPU cores, or implementing load balancing.',
                impact='System responsiveness and throughput may be significantly reduced.',
                priority=9 if severity == 'critical' else 7
            ))

        if 'high_load_average' in cpu_analysis.get('patterns', []):
            load_avg = cpu_analysis.get('load_average', {}).get('average', 0)

            issues.append(PerformanceIssue(
                severity='high',
                category='cpu',
                title='High System Load',
                description=f'System load average is {load_avg:.2f}, indicating possible CPU contention.',
                recommendation='Investigate process scheduling, reduce concurrent processes, or upgrade CPU.',
                impact='Increased response times and potential system instability.',
                priority=8
            ))

        if 'high_iowait' in cpu_analysis.get('patterns', []):
            iowait_avg = cpu_analysis.get('iowait', {}).get('average', 0)

            issues.append(PerformanceIssue(
                severity='medium',
                category='disk',
                title='High I/O Wait Time',
                description=f'Average I/O wait time is {iowait_avg:.1f}%, indicating disk bottlenecks.',
                recommendation='Consider upgrading to faster storage (SSD), optimizing disk access patterns, or adding more storage.',
                impact='Application performance may be limited by disk speed.',
                priority=6
            ))

        # Memory issues
        memory_analysis = analysis.get('memory_analysis', {})
        if 'high_memory_usage' in memory_analysis.get('patterns', []):
            mem_avg = memory_analysis.get('memory_utilization', {}).get('average', 0)
            severity = 'critical' if mem_avg > 95 else 'high'

            issues.append(PerformanceIssue(
                severity=severity,
                category='memory',
                title='High Memory Usage',
                description=f'Average memory usage is {mem_avg:.1f}%, approaching system limits.',
                recommendation='Optimize memory usage in applications, add more RAM, or implement memory caching strategies.',
                impact='Risk of system instability, swap usage, and performance degradation.',
                priority=9 if severity == 'critical' else 8
            ))

        if 'swap_usage' in memory_analysis.get('patterns', []):
            swap_avg = memory_analysis.get('swap_usage', {}).get('average', 0)

            issues.append(PerformanceIssue(
                severity='medium',
                category='memory',
                title='Swap Usage Detected',
                description=f'System is using {swap_avg:.1f}% swap space, indicating memory pressure.',
                recommendation='Increase physical RAM or optimize application memory usage to reduce swap dependency.',
                impact='Significantly reduced performance due to disk-based virtual memory.',
                priority=7
            ))

        if 'memory_leak_potential' in memory_analysis.get('patterns', []):
            issues.append(PerformanceIssue(
                severity='medium',
                category='memory',
                title='Potential Memory Leak',
                description='Memory usage shows an increasing trend over time.',
                recommendation='Investigate applications for memory leaks, implement proper memory management.',
                impact='Eventually leads to system instability and crashes.',
                priority=6
            ))

        # Disk issues
        disk_analysis = analysis.get('disk_analysis', {})
        if 'high_disk_usage' in disk_analysis.get('patterns', []):
            disk_avg = disk_analysis.get('disk_utilization', {}).get('average', 0)
            severity = 'critical' if disk_avg > 95 else 'high'

            issues.append(PerformanceIssue(
                severity=severity,
                category='disk',
                title='High Disk Usage',
                description=f'Disk usage is {disk_avg:.1f}%, approaching capacity limits.',
                recommendation='Clean up unnecessary files, implement log rotation, or add more storage capacity.',
                impact='Risk of application failures and inability to write new data.',
                priority=8 if severity == 'critical' else 6
            ))

        # Process issues
        process_analysis = analysis.get('process_analysis', {})
        top_memory = process_analysis.get('top_memory_consumers', {})
        for process_name, stats in top_memory.items():
            if stats['average'] > 20:  # More than 20% memory usage
                issues.append(PerformanceIssue(
                    severity='medium',
                    category='process',
                    title=f'High Memory Usage: {process_name}',
                    description=f'Process {process_name} uses {stats["average"]:.1f}% memory on average.',
                    recommendation=f'Optimize {process_name} memory usage or consider process limits.',
                    impact='Reduces available memory for other applications.',
                    priority=5
                ))

        return sorted(issues, key=lambda x: x.priority, reverse=True)

    def generate_optimization_recommendations(self, issues: List[PerformanceIssue]) -> Dict:
        """Generate comprehensive optimization recommendations"""
        recommendations = {
            'immediate_actions': [],
            'system_optimizations': [],
            'application_optimizations': [],
            'hardware_recommendations': [],
            'monitoring_improvements': []
        }

        # Categorize recommendations by issue type
        for issue in issues:
            if issue.severity in ['critical', 'high']:
                recommendations['immediate_actions'].append({
                    'title': issue.title,
                    'action': issue.recommendation,
                    'priority': issue.priority
                })

        # System optimizations based on patterns
        issue_categories = [issue.category for issue in issues]

        if 'cpu' in issue_categories:
            recommendations['system_optimizations'].extend([
                'Consider tuning CPU governor settings for performance',
                'Implement CPU affinity for critical processes',
                'Review and optimize cron jobs and background tasks'
            ])

        if 'memory' in issue_categories:
            recommendations['system_optimizations'].extend([
                'Tune kernel memory management parameters',
                'Implement memory limits for containers/processes',
                'Configure appropriate swap settings'
            ])

        if 'disk' in issue_categories:
            recommendations['system_optimizations'].extend([
                'Implement log rotation and cleanup policies',
                'Optimize filesystem mount options',
                'Consider using compression for archived data'
            ])

        # Hardware recommendations
        critical_issues = [i for i in issues if i.severity == 'critical']
        if any(i.category == 'cpu' for i in critical_issues):
            recommendations['hardware_recommendations'].append('Upgrade CPU or add more cores')

        if any(i.category == 'memory' for i in critical_issues):
            recommendations['hardware_recommendations'].append('Add more RAM')

        if any(i.category == 'disk' for i in critical_issues):
            recommendations['hardware_recommendations'].extend([
                'Upgrade to SSD storage',
                'Add additional storage capacity'
            ])

        # Monitoring improvements
        recommendations['monitoring_improvements'].extend([
            'Implement continuous performance monitoring',
            'Set up alerting for resource thresholds',
            'Create performance dashboards',
            'Implement application performance monitoring (APM)'
        ])

        return recommendations

    def run_performance_analysis(self, duration: int = 60) -> Dict:
        """Run complete performance analysis"""
        start_time = datetime.now()

        self.logger.info("Starting comprehensive performance analysis...")

        # Collect performance sample
        sample_data = self.collect_performance_sample(duration)

        # Analyze trends
        analysis = self.analyze_performance_trends(sample_data)

        # Generate performance issues
        issues = self.generate_performance_issues(analysis)

        # Generate recommendations
        recommendations = self.generate_optimization_recommendations(issues)

        # Compile final report
        report = {
            'timestamp': start_time.isoformat(),
            'duration': duration,
            'sample_count': sample_data.get('sample_count', 0),
            'analysis': analysis,
            'issues': [
                {
                    'severity': issue.severity,
                    'category': issue.category,
                    'title': issue.title,
                    'description': issue.description,
                    'recommendation': issue.recommendation,
                    'impact': issue.impact,
                    'priority': issue.priority
                }
                for issue in issues
            ],
            'recommendations': recommendations,
            'summary': {
                'total_issues': len(issues),
                'critical_issues': len([i for i in issues if i.severity == 'critical']),
                'high_issues': len([i for i in issues if i.severity == 'high']),
                'medium_issues': len([i for i in issues if i.severity == 'medium']),
                'low_issues': len([i for i in issues if i.severity == 'low'])
            }
        }

        # Save report
        self._save_performance_report(report)

        self.logger.info(f"Performance analysis complete: {len(issues)} issues found")

        return report

    def _save_performance_report(self, report: Dict):
        """Save performance report to file"""
        try:
            reports_dir = "data/performance_reports"
            os.makedirs(reports_dir, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = f"{reports_dir}/performance_report_{timestamp}.json"

            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)

            self.logger.info(f"Performance report saved to {report_file}")

        except Exception as e:
            self.logger.error(f"Error saving performance report: {e}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Performance Optimizer")
    parser.add_argument("--duration", type=int, default=60,
                       help="Analysis duration in seconds")
    parser.add_argument("--quick", action="store_true",
                       help="Quick analysis (30 seconds)")
    parser.add_argument("--config", default="data/performance_config.json",
                       help="Configuration file path")

    args = parser.parse_args()

    duration = 30 if args.quick else args.duration

    optimizer = PerformanceOptimizer(args.config)
    report = optimizer.run_performance_analysis(duration)

    print(json.dumps(report, indent=2))