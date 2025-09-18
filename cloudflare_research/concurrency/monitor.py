"""Performance monitoring and metrics collection.

Provides comprehensive performance monitoring, metrics collection,
and alerting for high-volume Cloudflare bypass operations.
"""

import asyncio
import time
import psutil
import threading
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass, field
from collections import deque, defaultdict
from enum import Enum
import json
import logging


class MetricType(Enum):
    """Types of metrics to collect."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class MetricData:
    """Individual metric data point."""
    name: str
    value: Union[int, float]
    metric_type: MetricType
    timestamp: float = field(default_factory=time.time)
    tags: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "value": self.value,
            "type": self.metric_type.value,
            "timestamp": self.timestamp,
            "tags": self.tags
        }


@dataclass
class SystemMetrics:
    """System resource metrics."""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_used_mb: float = 0.0
    memory_available_mb: float = 0.0
    disk_io_read_mb: float = 0.0
    disk_io_write_mb: float = 0.0
    network_bytes_sent: int = 0
    network_bytes_recv: int = 0
    active_threads: int = 0
    active_coroutines: int = 0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "memory_used_mb": self.memory_used_mb,
            "memory_available_mb": self.memory_available_mb,
            "disk_io_read_mb": self.disk_io_read_mb,
            "disk_io_write_mb": self.disk_io_write_mb,
            "network_bytes_sent": self.network_bytes_sent,
            "network_bytes_recv": self.network_bytes_recv,
            "active_threads": self.active_threads,
            "active_coroutines": self.active_coroutines,
            "timestamp": self.timestamp
        }


@dataclass
class PerformanceMetrics:
    """Application performance metrics."""
    requests_per_second: float = 0.0
    avg_response_time: float = 0.0
    success_rate: float = 0.0
    error_rate: float = 0.0
    active_connections: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    challenges_encountered: int = 0
    challenges_solved: int = 0
    rate_limit_hits: int = 0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "requests_per_second": self.requests_per_second,
            "avg_response_time": self.avg_response_time,
            "success_rate": self.success_rate,
            "error_rate": self.error_rate,
            "active_connections": self.active_connections,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "challenges_encountered": self.challenges_encountered,
            "challenges_solved": self.challenges_solved,
            "rate_limit_hits": self.rate_limit_hits,
            "timestamp": self.timestamp
        }


@dataclass
class Alert:
    """Performance alert."""
    level: AlertLevel
    message: str
    metric_name: str
    current_value: Union[int, float]
    threshold: Union[int, float]
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "level": self.level.value,
            "message": self.message,
            "metric_name": self.metric_name,
            "current_value": self.current_value,
            "threshold": self.threshold,
            "timestamp": self.timestamp
        }


class MetricsCollector:
    """Collects and aggregates various metrics."""

    def __init__(self, max_history: int = 10000):
        self.max_history = max_history

        # Metric storage
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._timers: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))

        # History
        self._metric_history: deque = deque(maxlen=max_history)

        # Lock for thread safety
        self._lock = threading.Lock()

    def increment_counter(self, name: str, value: int = 1, tags: Dict[str, str] = None) -> None:
        """Increment a counter metric."""
        with self._lock:
            self._counters[name] += value
            self._record_metric(MetricData(name, self._counters[name], MetricType.COUNTER, tags=tags or {}))

    def set_gauge(self, name: str, value: float, tags: Dict[str, str] = None) -> None:
        """Set a gauge metric value."""
        with self._lock:
            self._gauges[name] = value
            self._record_metric(MetricData(name, value, MetricType.GAUGE, tags=tags or {}))

    def record_histogram(self, name: str, value: float, tags: Dict[str, str] = None) -> None:
        """Record a histogram value."""
        with self._lock:
            self._histograms[name].append(value)
            self._record_metric(MetricData(name, value, MetricType.HISTOGRAM, tags=tags or {}))

    def record_timer(self, name: str, duration: float, tags: Dict[str, str] = None) -> None:
        """Record a timer duration."""
        with self._lock:
            self._timers[name].append(duration)
            self._record_metric(MetricData(name, duration, MetricType.TIMER, tags=tags or {}))

    def _record_metric(self, metric: MetricData) -> None:
        """Record metric in history."""
        self._metric_history.append(metric)

    def get_counter(self, name: str) -> int:
        """Get counter value."""
        return self._counters.get(name, 0)

    def get_gauge(self, name: str) -> float:
        """Get gauge value."""
        return self._gauges.get(name, 0.0)

    def get_histogram_stats(self, name: str) -> Dict[str, float]:
        """Get histogram statistics."""
        if name not in self._histograms or not self._histograms[name]:
            return {"count": 0, "min": 0, "max": 0, "avg": 0, "p50": 0, "p95": 0, "p99": 0}

        values = sorted(self._histograms[name])
        count = len(values)

        return {
            "count": count,
            "min": values[0],
            "max": values[-1],
            "avg": sum(values) / count,
            "p50": values[int(count * 0.5)],
            "p95": values[int(count * 0.95)],
            "p99": values[int(count * 0.99)]
        }

    def get_timer_stats(self, name: str) -> Dict[str, float]:
        """Get timer statistics."""
        return self.get_histogram_stats(name)  # Same calculation

    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all current metrics."""
        with self._lock:
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {name: self.get_histogram_stats(name) for name in self._histograms},
                "timers": {name: self.get_timer_stats(name) for name in self._timers}
            }

    def reset_metrics(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._timers.clear()
            self._metric_history.clear()


class SystemMonitor:
    """Monitors system resources."""

    def __init__(self):
        self.process = psutil.Process()
        self._last_disk_io = None
        self._last_network_io = None

    def get_system_metrics(self) -> SystemMetrics:
        """Get current system metrics."""
        # CPU and memory
        cpu_percent = psutil.cpu_percent(interval=None)
        memory = psutil.virtual_memory()

        # Process-specific memory
        process_memory = self.process.memory_info()

        # Disk I/O
        disk_io = psutil.disk_io_counters()
        disk_read_mb = 0.0
        disk_write_mb = 0.0

        if self._last_disk_io and disk_io:
            read_bytes = disk_io.read_bytes - self._last_disk_io.read_bytes
            write_bytes = disk_io.write_bytes - self._last_disk_io.write_bytes
            disk_read_mb = read_bytes / (1024 * 1024)
            disk_write_mb = write_bytes / (1024 * 1024)

        self._last_disk_io = disk_io

        # Network I/O
        network_io = psutil.net_io_counters()
        net_sent = network_io.bytes_sent if network_io else 0
        net_recv = network_io.bytes_recv if network_io else 0

        # Thread count
        active_threads = threading.active_count()

        # Coroutine count (approximation)
        try:
            active_coroutines = len([task for task in asyncio.all_tasks() if not task.done()])
        except RuntimeError:
            active_coroutines = 0

        return SystemMetrics(
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_used_mb=process_memory.rss / (1024 * 1024),
            memory_available_mb=memory.available / (1024 * 1024),
            disk_io_read_mb=disk_read_mb,
            disk_io_write_mb=disk_write_mb,
            network_bytes_sent=net_sent,
            network_bytes_recv=net_recv,
            active_threads=active_threads,
            active_coroutines=active_coroutines
        )


class PerformanceMonitor:
    """Monitors application performance metrics."""

    def __init__(self, window_size: int = 60):
        self.window_size = window_size  # seconds
        self.request_times: deque = deque()
        self.request_results: deque = deque()
        self.challenge_events: deque = deque()
        self.rate_limit_events: deque = deque()

        # Current state
        self.active_connections = 0
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0

    def record_request(self, duration: float, success: bool) -> None:
        """Record a request completion."""
        now = time.time()
        self.request_times.append((now, duration))
        self.request_results.append((now, success))

        self.total_requests += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1

        self._cleanup_old_data(now)

    def record_challenge(self, challenge_type: str, solved: bool) -> None:
        """Record a challenge encounter."""
        now = time.time()
        self.challenge_events.append((now, challenge_type, solved))
        self._cleanup_old_data(now)

    def record_rate_limit(self) -> None:
        """Record a rate limit hit."""
        now = time.time()
        self.rate_limit_events.append(now)
        self._cleanup_old_data(now)

    def set_active_connections(self, count: int) -> None:
        """Set current active connection count."""
        self.active_connections = count

    def _cleanup_old_data(self, current_time: float) -> None:
        """Remove data older than window size."""
        cutoff_time = current_time - self.window_size

        # Clean request times
        while self.request_times and self.request_times[0][0] < cutoff_time:
            self.request_times.popleft()

        # Clean request results
        while self.request_results and self.request_results[0][0] < cutoff_time:
            self.request_results.popleft()

        # Clean challenge events
        while self.challenge_events and self.challenge_events[0][0] < cutoff_time:
            self.challenge_events.popleft()

        # Clean rate limit events
        while self.rate_limit_events and self.rate_limit_events[0] < cutoff_time:
            self.rate_limit_events.popleft()

    def get_performance_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics."""
        now = time.time()
        self._cleanup_old_data(now)

        # Calculate requests per second
        recent_requests = len(self.request_times)
        requests_per_second = recent_requests / self.window_size if self.window_size > 0 else 0

        # Calculate average response time
        if self.request_times:
            avg_response_time = sum(duration for _, duration in self.request_times) / len(self.request_times)
        else:
            avg_response_time = 0.0

        # Calculate success/error rates
        if self.request_results:
            successful = sum(1 for _, success in self.request_results if success)
            success_rate = successful / len(self.request_results)
            error_rate = 1.0 - success_rate
        else:
            success_rate = 0.0
            error_rate = 0.0

        # Challenge statistics
        challenges_encountered = len(self.challenge_events)
        challenges_solved = sum(1 for _, _, solved in self.challenge_events if solved)

        # Rate limit hits
        rate_limit_hits = len(self.rate_limit_events)

        return PerformanceMetrics(
            requests_per_second=requests_per_second,
            avg_response_time=avg_response_time,
            success_rate=success_rate,
            error_rate=error_rate,
            active_connections=self.active_connections,
            total_requests=self.total_requests,
            successful_requests=self.successful_requests,
            failed_requests=self.failed_requests,
            challenges_encountered=challenges_encountered,
            challenges_solved=challenges_solved,
            rate_limit_hits=rate_limit_hits
        )


class AlertManager:
    """Manages performance alerts and notifications."""

    def __init__(self):
        self.alert_rules: List[Dict[str, Any]] = []
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_callbacks: List[Callable[[Alert], None]] = []

    def add_alert_rule(self, metric_name: str, threshold: Union[int, float],
                      operator: str = "gt", level: AlertLevel = AlertLevel.WARNING,
                      message_template: str = None) -> None:
        """Add an alert rule."""
        if message_template is None:
            message_template = f"{metric_name} is {operator} {threshold}"

        self.alert_rules.append({
            "metric_name": metric_name,
            "threshold": threshold,
            "operator": operator,
            "level": level,
            "message_template": message_template
        })

    def check_alerts(self, metrics: Dict[str, Any]) -> List[Alert]:
        """Check metrics against alert rules."""
        triggered_alerts = []

        for rule in self.alert_rules:
            metric_name = rule["metric_name"]
            threshold = rule["threshold"]
            operator = rule["operator"]
            level = rule["level"]

            # Get metric value
            current_value = self._get_metric_value(metrics, metric_name)
            if current_value is None:
                continue

            # Check condition
            triggered = False
            if operator == "gt" and current_value > threshold:
                triggered = True
            elif operator == "lt" and current_value < threshold:
                triggered = True
            elif operator == "eq" and current_value == threshold:
                triggered = True
            elif operator == "gte" and current_value >= threshold:
                triggered = True
            elif operator == "lte" and current_value <= threshold:
                triggered = True

            if triggered:
                alert_key = f"{metric_name}_{operator}_{threshold}"

                # Create alert if not already active
                if alert_key not in self.active_alerts:
                    message = rule["message_template"].format(
                        metric_name=metric_name,
                        current_value=current_value,
                        threshold=threshold
                    )

                    alert = Alert(
                        level=level,
                        message=message,
                        metric_name=metric_name,
                        current_value=current_value,
                        threshold=threshold
                    )

                    self.active_alerts[alert_key] = alert
                    triggered_alerts.append(alert)

                    # Notify callbacks
                    for callback in self.alert_callbacks:
                        try:
                            callback(alert)
                        except Exception:
                            pass
            else:
                # Remove alert if condition no longer met
                alert_key = f"{metric_name}_{operator}_{threshold}"
                if alert_key in self.active_alerts:
                    del self.active_alerts[alert_key]

        return triggered_alerts

    def _get_metric_value(self, metrics: Dict[str, Any], metric_path: str) -> Optional[Union[int, float]]:
        """Get nested metric value by path."""
        parts = metric_path.split(".")
        current = metrics

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None

        return current if isinstance(current, (int, float)) else None

    def add_alert_callback(self, callback: Callable[[Alert], None]) -> None:
        """Add callback for alert notifications."""
        self.alert_callbacks.append(callback)

    def get_active_alerts(self) -> List[Alert]:
        """Get currently active alerts."""
        return list(self.active_alerts.values())


class ComprehensiveMonitor:
    """Comprehensive monitoring system combining all monitoring components."""

    def __init__(self, metrics_collector: MetricsCollector = None,
                 system_monitor: SystemMonitor = None,
                 performance_monitor: PerformanceMonitor = None,
                 alert_manager: AlertManager = None):

        self.metrics = metrics_collector or MetricsCollector()
        self.system = system_monitor or SystemMonitor()
        self.performance = performance_monitor or PerformanceMonitor()
        self.alerts = alert_manager or AlertManager()

        # Monitoring control
        self._monitoring_task: Optional[asyncio.Task] = None
        self._monitoring_interval = 1.0
        self._running = False

        # Setup default alerts
        self._setup_default_alerts()

    def _setup_default_alerts(self) -> None:
        """Setup default performance alerts."""
        self.alerts.add_alert_rule("system.cpu_percent", 80.0, "gt", AlertLevel.WARNING)
        self.alerts.add_alert_rule("system.memory_percent", 85.0, "gt", AlertLevel.WARNING)
        self.alerts.add_alert_rule("performance.error_rate", 0.1, "gt", AlertLevel.WARNING)
        self.alerts.add_alert_rule("performance.avg_response_time", 10.0, "gt", AlertLevel.WARNING)

    async def start_monitoring(self, interval: float = 1.0) -> None:
        """Start continuous monitoring."""
        if self._running:
            return

        self._monitoring_interval = interval
        self._running = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())

    async def stop_monitoring(self) -> None:
        """Stop continuous monitoring."""
        self._running = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self._running:
            try:
                # Collect all metrics
                system_metrics = self.system.get_system_metrics()
                performance_metrics = self.performance.get_performance_metrics()
                app_metrics = self.metrics.get_all_metrics()

                # Update gauge metrics
                for key, value in system_metrics.to_dict().items():
                    if isinstance(value, (int, float)):
                        self.metrics.set_gauge(f"system.{key}", value)

                for key, value in performance_metrics.to_dict().items():
                    if isinstance(value, (int, float)):
                        self.metrics.set_gauge(f"performance.{key}", value)

                # Check alerts
                all_metrics = {
                    "system": system_metrics.to_dict(),
                    "performance": performance_metrics.to_dict(),
                    "application": app_metrics
                }

                self.alerts.check_alerts(all_metrics)

                await asyncio.sleep(self._monitoring_interval)

            except asyncio.CancelledError:
                break
            except Exception:
                # Continue monitoring even if there's an error
                await asyncio.sleep(self._monitoring_interval)

    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get all monitoring statistics."""
        return {
            "system": self.system.get_system_metrics().to_dict(),
            "performance": self.performance.get_performance_metrics().to_dict(),
            "application": self.metrics.get_all_metrics(),
            "alerts": [alert.to_dict() for alert in self.alerts.get_active_alerts()],
            "monitoring_status": {
                "running": self._running,
                "interval": self._monitoring_interval
            }
        }


# Utility functions
def create_monitor(enable_alerts: bool = True) -> ComprehensiveMonitor:
    """Create a comprehensive monitor instance."""
    monitor = ComprehensiveMonitor()

    if enable_alerts:
        # Add logging callback for alerts
        def log_alert(alert: Alert):
            level_map = {
                AlertLevel.INFO: logging.INFO,
                AlertLevel.WARNING: logging.WARNING,
                AlertLevel.CRITICAL: logging.CRITICAL
            }
            logging.log(level_map[alert.level], f"Alert: {alert.message}")

        monitor.alerts.add_alert_callback(log_alert)

    return monitor


def create_metrics_collector() -> MetricsCollector:
    """Create a metrics collector instance."""
    return MetricsCollector()


def create_performance_monitor() -> PerformanceMonitor:
    """Create a performance monitor instance."""
    return PerformanceMonitor()