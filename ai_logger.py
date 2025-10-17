#!/usr/bin/env python3
"""
AI Logger - Real-time comprehensive logging for AI analysis and training
Single log file that captures everything: system events, decisions, performance, errors, patterns
"""

import json
import threading
import time
import psutil
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from contextlib import contextmanager

@dataclass
class AILogEvent:
    """Structured AI log event"""
    timestamp: str
    event_type: str
    category: str
    source: str
    details: Dict[str, Any]
    system_metrics: Optional[Dict[str, Any]] = None
    user_interaction: Optional[Dict[str, Any]] = None
    ai_analysis: Optional[Dict[str, Any]] = None

class AILogger:
    """Real-time AI logger that captures everything for analysis"""

    def __init__(self, log_file: str = "ai_events.log", max_file_size_mb: int = 100):
        self.log_file = log_file
        self.max_file_size = max_file_size_mb * 1024 * 1024  # Convert to bytes
        self.lock = threading.Lock()
        self.session_start = datetime.now()

        # Event categories for organization
        self.categories = {
            'system': 'System operations and performance',
            'processing': 'Content processing and pipeline',
            'database': 'Database operations and sync',
            'user': 'User interactions and commands',
            'error': 'Errors and failures',
            'performance': 'Performance metrics and optimization',
            'ai': 'AI decisions and analysis',
            'security': 'Security events and access',
            'network': 'Network operations and connectivity'
        }

        # Event types for detailed tracking
        self.event_types = {
            'start': 'Process/service started',
            'stop': 'Process/service stopped',
            'decision': 'AI/algorithm decision point',
            'action': 'System action performed',
            'result': 'Result of an operation',
            'error': 'Error or exception',
            'warning': 'Warning or potential issue',
            'info': 'Informational event',
            'debug': 'Debug information',
            'metric': 'Performance metric',
            'pattern': 'Pattern detected',
            'anomaly': 'Anomaly detected',
            'optimization': 'Optimization applied'
        }

        # Ensure log directory exists
        os.makedirs(os.path.dirname(log_file) if os.path.dirname(log_file) else '.', exist_ok=True)

        # Start system metrics thread
        self.running = True
        self.metrics_thread = threading.Thread(target=self._metrics_collector, daemon=True)
        self.metrics_thread.start()

    def _get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        try:
            return {
                'cpu_percent': psutil.cpu_percent(),
                'memory_percent': psutil.virtual_memory().percent,
                'memory_used': psutil.virtual_memory().used,
                'disk_usage': psutil.disk_usage('/').percent,
                'disk_free': psutil.disk_usage('/').free,
                'network_sent': psutil.net_io_counters().bytes_sent,
                'network_recv': psutil.net_io_counters().bytes_recv,
                'process_count': len(psutil.pids()),
                'load_avg': os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0]
            }
        except:
            return {}

    def _metrics_collector(self):
        """Background thread for collecting system metrics"""
        while self.running:
            try:
                # Log system metrics every 30 seconds
                self.log_event(
                    event_type='metric',
                    category='system',
                    source='system_monitor',
                    details={'interval': '30s'},
                    system_metrics=self._get_system_metrics()
                )
                time.sleep(30)
            except:
                time.sleep(60)  # Wait longer if there's an error

    def _rotate_log_if_needed(self):
        """Rotate log file if it gets too large"""
        try:
            if os.path.exists(self.log_file):
                file_size = os.path.getsize(self.log_file)
                if file_size > self.max_file_size:
                    # Create backup
                    backup_file = f"{self.log_file}.{int(time.time())}.backup"
                    os.rename(self.log_file, backup_file)

                    # Write summary of backup file
                    with open(f"{backup_file}.summary", 'w') as f:
                        f.write(f"AI Log Backup Summary\n")
                        f.write(f"Created: {datetime.now().isoformat()}\n")
                        f.write(f"Size: {file_size / (1024*1024):.2f} MB\n")
                        f.write(f"Session: {self.session_start.isoformat()} - {datetime.now().isoformat()}\n")
        except Exception as e:
            print(f"Warning: Log rotation failed: {e}")

    def _format_event(self, event: AILogEvent) -> str:
        """Format event as JSON string"""
        event_dict = asdict(event)
        return json.dumps(event_dict, separators=(',', ':'), ensure_ascii=False)

    def log_event(self, event_type: str, category: str, source: str, details: Dict[str, Any],
                  system_metrics: Optional[Dict[str, Any]] = None,
                  user_interaction: Optional[Dict[str, Any]] = None,
                  ai_analysis: Optional[Dict[str, Any]] = None):
        """Log an AI event"""

        # Validate inputs
        if category not in self.categories:
            print(f"Warning: Unknown category '{category}'", file=os.sys.stderr)
            category = 'system'

        if event_type not in self.event_types:
            print(f"Warning: Unknown event_type '{event_type}'", file=os.sys.stderr)
            event_type = 'info'

        # Create event
        event = AILogEvent(
            timestamp=datetime.now().isoformat(),
            event_type=event_type,
            category=category,
            source=source,
            details=details,
            system_metrics=system_metrics or self._get_system_metrics(),
            user_interaction=user_interaction,
            ai_analysis=ai_analysis
        )

        # Format and write
        event_line = self._format_event(event)

        with self.lock:
            try:
                # Check file size and rotate if needed
                self._rotate_log_if_needed()

                # Write to file
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(event_line + '\n')
                    f.flush()  # Ensure immediate write for real-time analysis

            except Exception as e:
                print(f"Error writing to AI log: {e}", file=os.sys.stderr)

    # Convenience methods for common events
    def system_start(self, service: str, version: str = None, config: Dict[str, Any] = None):
        """Log system service start"""
        self.log_event(
            event_type='start',
            category='system',
            source=service,
            details={
                'action': 'service_start',
                'service': service,
                'version': version,
                'config': config or {}
            }
        )

    def system_stop(self, service: str, reason: str = None, uptime: float = None):
        """Log system service stop"""
        self.log_event(
            event_type='stop',
            category='system',
            source=service,
            details={
                'action': 'service_stop',
                'service': service,
                'reason': reason,
                'uptime_seconds': uptime
            }
        )

    def processing_start(self, item_id: str, item_type: str, source: str):
        """Log processing start"""
        self.log_event(
            event_type='action',
            category='processing',
            source='processing_pipeline',
            details={
                'action': 'processing_start',
                'item_id': item_id,
                'item_type': item_type,
                'source': source
            }
        )

    def processing_complete(self, item_id: str, result: Dict[str, Any], processing_time: float):
        """Log processing completion"""
        self.log_event(
            event_type='result',
            category='processing',
            source='processing_pipeline',
            details={
                'action': 'processing_complete',
                'item_id': item_id,
                'result': result,
                'processing_time_seconds': processing_time
            }
        )

    def ai_decision(self, decision_point: str, options: List[str], chosen: str,
                    confidence: float, reasoning: str):
        """Log AI decision point"""
        self.log_event(
            event_type='decision',
            category='ai',
            source='ai_engine',
            details={
                'decision_point': decision_point,
                'options': options,
                'chosen': chosen,
                'confidence': confidence,
                'reasoning': reasoning
            }
        )

    def error_event(self, error: str, source: str, context: Dict[str, Any] = None,
                    severity: str = 'error'):
        """Log error event"""
        self.log_event(
            event_type='error',
            category='error',
            source=source,
            details={
                'error': error,
                'context': context or {},
                'severity': severity
            }
        )

    def pattern_detected(self, pattern_type: str, pattern_data: Dict[str, Any],
                         confidence: float, impact: str):
        """Log pattern detection"""
        self.log_event(
            event_type='pattern',
            category='ai',
            source='pattern_detector',
            details={
                'pattern_type': pattern_type,
                'pattern_data': pattern_data,
                'confidence': confidence,
                'impact': impact
            }
        )

    def performance_metric(self, metric_name: str, value: float, unit: str,
                           context: Dict[str, Any] = None):
        """Log performance metric"""
        self.log_event(
            event_type='metric',
            category='performance',
            source='performance_monitor',
            details={
                'metric_name': metric_name,
                'value': value,
                'unit': unit,
                'context': context or {}
            }
        )

    def user_interaction(self, action: str, details: Dict[str, Any], user_id: str = None):
        """Log user interaction"""
        self.log_event(
            event_type='action',
            category='user',
            source='user_interface',
            details={
                'action': action,
                'details': details,
                'user_id': user_id or 'anonymous'
            },
            user_interaction={
                'timestamp': datetime.now().isoformat(),
                'action': action,
                'user_id': user_id or 'anonymous'
            }
        )

    def optimization_applied(self, optimization_type: str, before: float, after: float,
                           improvement: float, details: Dict[str, Any]):
        """Log optimization applied"""
        self.log_event(
            event_type='optimization',
            category='performance',
            source='optimization_engine',
            details={
                'optimization_type': optimization_type,
                'before_value': before,
                'after_value': after,
                'improvement_percent': improvement,
                'details': details
            }
        )

    @contextmanager
    def measure_operation(self, operation_name: str, category: str = 'performance'):
        """Context manager to measure and log operation duration"""
        start_time = time.time()
        start_metrics = self._get_system_metrics()

        try:
            yield
        finally:
            end_time = time.time()
            end_metrics = self._get_system_metrics()

            duration = end_time - start_time

            # Calculate resource usage during operation
            cpu_diff = end_metrics.get('cpu_percent', 0) - start_metrics.get('cpu_percent', 0)
            memory_diff = end_metrics.get('memory_used', 0) - start_metrics.get('memory_used', 0)

            self.log_event(
                event_type='metric',
                category=category,
                source='operation_monitor',
                details={
                    'operation': operation_name,
                    'duration_seconds': duration,
                    'cpu_change_percent': cpu_diff,
                    'memory_change_bytes': memory_diff,
                    'start_metrics': start_metrics,
                    'end_metrics': end_metrics
                }
            )

    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of current session"""
        return {
            'session_start': self.session_start.isoformat(),
            'session_duration': (datetime.now() - self.session_start).total_seconds(),
            'log_file': self.log_file,
            'max_file_size_mb': self.max_file_size / (1024 * 1024),
            'categories': self.categories,
            'event_types': self.event_types
        }

    def shutdown(self):
        """Shutdown the AI logger"""
        self.running = False
        if self.metrics_thread.is_alive():
            self.metrics_thread.join(timeout=5)

# Global AI logger instance
_ai_logger = None

def get_ai_logger(log_file: str = "ai_events.log") -> AILogger:
    """Get or create the global AI logger instance"""
    global _ai_logger
    if _ai_logger is None or _ai_logger.log_file != log_file:
        _ai_logger = AILogger(log_file)
    return _ai_logger

# Convenience functions for direct use
def log_system_start(service: str, version: str = None, config: Dict[str, Any] = None):
    """Log system service start using global logger"""
    get_ai_logger().system_start(service, version, config)

def log_processing_start(item_id: str, item_type: str, source: str):
    """Log processing start using global logger"""
    get_ai_logger().processing_start(item_id, item_type, source)

def log_processing_complete(item_id: str, result: Dict[str, Any], processing_time: float):
    """Log processing completion using global logger"""
    get_ai_logger().processing_complete(item_id, result, processing_time)

def log_error(error: str, source: str, context: Dict[str, Any] = None):
    """Log error using global logger"""
    get_ai_logger().error_event(error, source, context)

@contextmanager
def measure_operation(operation_name: str, category: str = 'performance'):
    """Context manager to measure operation using global logger"""
    with get_ai_logger().measure_operation(operation_name, category):
        yield

def main():
    """Test the AI logger"""
    print("🤖 Testing AI Logger")
    print("=" * 40)

    logger = get_ai_logger("test_ai_events.log")

    # Test various event types
    logger.system_start("test_service", "1.0.0", {"mode": "test"})
    logger.processing_start("test_item_001", "podcast", "test_source")
    logger.ai_decision("route_selection", ["fast", "accurate"], "accurate", 0.85, "Quality prioritized")
    logger.performance_metric("processing_time", 2.5, "seconds", {"item": "test_item_001"})
    logger.pattern_detected("retry_pattern", {"count": 3, "interval": 60}, 0.9, "High retry rate detected")

    # Test context manager
    with logger.measure_operation("test_operation"):
        time.sleep(0.1)

    logger.system_stop("test_service", "test_complete", 10.5)

    print("✅ AI logger test completed")

if __name__ == "__main__":
    main()