"""Metrics collection and export for CloudflareBypass operations.

Provides comprehensive metrics collection, aggregation, and export capabilities
for performance monitoring, analysis, and reporting of bypass operations.
"""

import asyncio
import json
import time
import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Callable, NamedTuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict, deque
import logging

# Core models
from .models.performance_metrics import PerformanceMetrics
from .models.challenge_record import ChallengeRecord
from .models.test_session import TestSession
from .models.test_request import TestRequest

# Utilities
from .utils import Timer, generate_request_id, compute_hash


class MetricType(Enum):
    """Types of metrics that can be collected."""
    REQUEST_TIMING = "request_timing"
    CHALLENGE_SOLVING = "challenge_solving"
    BYPASS_SUCCESS = "bypass_success"
    ERROR_RATE = "error_rate"
    CONCURRENCY = "concurrency"
    RESOURCE_USAGE = "resource_usage"
    THROUGHPUT = "throughput"
    LATENCY = "latency"


class ExportFormat(Enum):
    """Export formats for metrics."""
    JSON = "json"
    CSV = "csv"
    PROMETHEUS = "prometheus"
    INFLUXDB = "influxdb"
    CUSTOM = "custom"


@dataclass
class MetricEvent:
    """Individual metric event."""
    timestamp: float
    metric_type: MetricType
    value: Union[float, int, str]
    labels: Dict[str, str] = field(default_factory=dict)
    session_id: Optional[str] = None
    request_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp,
            "metric_type": self.metric_type.value,
            "value": self.value,
            "labels": self.labels,
            "session_id": self.session_id,
            "request_id": self.request_id,
        }


@dataclass
class AggregatedMetric:
    """Aggregated metric over a time period."""
    metric_type: MetricType
    start_time: float
    end_time: float
    count: int = 0
    sum_value: float = 0.0
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    avg_value: float = 0.0
    percentiles: Dict[int, float] = field(default_factory=dict)
    labels: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "metric_type": self.metric_type.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": self.end_time - self.start_time,
            "count": self.count,
            "sum_value": self.sum_value,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "avg_value": self.avg_value,
            "percentiles": self.percentiles,
            "labels": self.labels,
        }


@dataclass
class MetricsConfig:
    """Configuration for metrics collection."""
    enabled: bool = True
    buffer_size: int = 10000
    flush_interval: float = 60.0  # seconds
    aggregation_window: float = 300.0  # 5 minutes
    retention_hours: int = 24
    export_enabled: bool = True
    export_path: str = "./metrics"
    export_formats: List[ExportFormat] = field(default_factory=lambda: [ExportFormat.JSON])
    collect_detailed_timings: bool = True
    collect_challenge_metrics: bool = True
    collect_resource_metrics: bool = True


class MetricsCollector:
    """Collects and manages metrics from CloudflareBypass operations."""

    def __init__(self, config: MetricsConfig = None):
        self.config = config or MetricsConfig()

        # Event storage
        self._events: deque = deque(maxlen=self.config.buffer_size)
        self._events_lock = asyncio.Lock()

        # Aggregation storage
        self._aggregated_metrics: Dict[str, List[AggregatedMetric]] = defaultdict(list)
        self._aggregation_lock = asyncio.Lock()

        # Background tasks
        self._running = False
        self._flush_task: Optional[asyncio.Task] = None
        self._aggregation_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None

        # Event handlers
        self._export_handlers: Dict[ExportFormat, Callable] = {
            ExportFormat.JSON: self._export_json,
            ExportFormat.CSV: self._export_csv,
            ExportFormat.PROMETHEUS: self._export_prometheus,
            ExportFormat.INFLUXDB: self._export_influxdb,
        }

        # Performance tracking
        self._last_flush: float = time.time()
        self._last_aggregation: float = time.time()

        # Setup export directory
        if self.config.export_enabled:
            Path(self.config.export_path).mkdir(parents=True, exist_ok=True)

    async def start(self) -> None:
        """Start metrics collection."""
        if self._running or not self.config.enabled:
            return

        self._running = True

        # Start background tasks
        if self.config.flush_interval > 0:
            self._flush_task = asyncio.create_task(self._flush_loop())

        if self.config.aggregation_window > 0:
            self._aggregation_task = asyncio.create_task(self._aggregation_loop())

        if self.config.retention_hours > 0:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        logging.info("Metrics collector started")

    async def stop(self) -> None:
        """Stop metrics collection."""
        self._running = False

        # Cancel background tasks
        tasks = [self._flush_task, self._aggregation_task, self._cleanup_task]
        for task in tasks:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Final flush
        await self._flush_events()
        await self._aggregate_pending_events()

        logging.info("Metrics collector stopped")

    async def record_event(self, metric_type: MetricType, value: Union[float, int, str],
                          labels: Dict[str, str] = None, session_id: str = None,
                          request_id: str = None) -> None:
        """Record a metric event."""
        if not self.config.enabled:
            return

        event = MetricEvent(
            timestamp=time.time(),
            metric_type=metric_type,
            value=value,
            labels=labels or {},
            session_id=session_id,
            request_id=request_id
        )

        async with self._events_lock:
            self._events.append(event)

    async def record_request_timing(self, duration: float, success: bool,
                                  url: str = None, session_id: str = None,
                                  request_id: str = None) -> None:
        """Record request timing metrics."""
        labels = {
            "success": str(success).lower(),
            "url_domain": self._extract_domain(url) if url else "unknown"
        }

        await self.record_event(
            MetricType.REQUEST_TIMING,
            duration,
            labels=labels,
            session_id=session_id,
            request_id=request_id
        )

    async def record_challenge_event(self, challenge_type: str, solve_time: float,
                                   success: bool, session_id: str = None,
                                   request_id: str = None) -> None:
        """Record challenge solving metrics."""
        if not self.config.collect_challenge_metrics:
            return

        labels = {
            "challenge_type": challenge_type,
            "success": str(success).lower()
        }

        await self.record_event(
            MetricType.CHALLENGE_SOLVING,
            solve_time,
            labels=labels,
            session_id=session_id,
            request_id=request_id
        )

    async def record_bypass_result(self, success: bool, attempts: int,
                                 total_time: float, session_id: str = None,
                                 request_id: str = None) -> None:
        """Record bypass attempt results."""
        labels = {
            "success": str(success).lower(),
            "attempts": str(attempts)
        }

        await self.record_event(
            MetricType.BYPASS_SUCCESS,
            total_time,
            labels=labels,
            session_id=session_id,
            request_id=request_id
        )

    async def record_error(self, error_type: str, error_message: str = None,
                         session_id: str = None, request_id: str = None) -> None:
        """Record error events."""
        labels = {
            "error_type": error_type,
            "error_hash": compute_hash(error_message)[:8] if error_message else "unknown"
        }

        await self.record_event(
            MetricType.ERROR_RATE,
            1,  # Count of errors
            labels=labels,
            session_id=session_id,
            request_id=request_id
        )

    async def record_concurrency(self, active_requests: int, pending_requests: int,
                               session_id: str = None) -> None:
        """Record concurrency metrics."""
        await self.record_event(
            MetricType.CONCURRENCY,
            active_requests,
            labels={"metric": "active"},
            session_id=session_id
        )

        await self.record_event(
            MetricType.CONCURRENCY,
            pending_requests,
            labels={"metric": "pending"},
            session_id=session_id
        )

    async def record_throughput(self, requests_per_second: float,
                              session_id: str = None) -> None:
        """Record throughput metrics."""
        await self.record_event(
            MetricType.THROUGHPUT,
            requests_per_second,
            session_id=session_id
        )

    async def get_current_metrics(self) -> Dict[str, Any]:
        """Get current metrics summary."""
        async with self._events_lock:
            recent_events = [e for e in self._events if time.time() - e.timestamp < 300]  # Last 5 minutes

        # Calculate basic statistics
        metrics_by_type = defaultdict(list)
        for event in recent_events:
            if isinstance(event.value, (int, float)):
                metrics_by_type[event.metric_type].append(event.value)

        summary = {}
        for metric_type, values in metrics_by_type.items():
            if values:
                summary[metric_type.value] = {
                    "count": len(values),
                    "avg": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "total": sum(values),
                }

        return {
            "current_metrics": summary,
            "total_events": len(self._events),
            "collection_active": self._running,
            "last_flush": self._last_flush,
            "last_aggregation": self._last_aggregation,
        }

    async def get_aggregated_metrics(self, metric_type: MetricType = None,
                                   hours: int = 1) -> List[AggregatedMetric]:
        """Get aggregated metrics for a specific period."""
        cutoff_time = time.time() - (hours * 3600)

        async with self._aggregation_lock:
            if metric_type:
                metrics = self._aggregated_metrics.get(metric_type.value, [])
            else:
                metrics = []
                for metric_list in self._aggregated_metrics.values():
                    metrics.extend(metric_list)

            # Filter by time
            return [m for m in metrics if m.end_time >= cutoff_time]

    async def export_metrics(self, format: ExportFormat = ExportFormat.JSON,
                           hours: int = 1, filename: str = None) -> str:
        """Export metrics in specified format."""
        if not self.config.export_enabled:
            raise RuntimeError("Export is disabled")

        # Get metrics data
        aggregated = await self.get_aggregated_metrics(hours=hours)

        # Generate filename if not provided
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"metrics_{timestamp}.{format.value}"

        file_path = Path(self.config.export_path) / filename

        # Export using appropriate handler
        handler = self._export_handlers.get(format)
        if handler:
            await handler(aggregated, file_path)
        else:
            raise ValueError(f"Unsupported export format: {format}")

        return str(file_path)

    async def _flush_loop(self) -> None:
        """Background event flushing."""
        while self._running:
            try:
                await asyncio.sleep(self.config.flush_interval)
                await self._flush_events()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"Metrics flush error: {e}")

    async def _flush_events(self) -> None:
        """Flush events to storage."""
        if not self.config.export_enabled:
            return

        async with self._events_lock:
            if not self._events:
                return

            # Export recent events
            recent_events = list(self._events)

        # Create export data
        export_data = {
            "timestamp": datetime.now().isoformat(),
            "event_count": len(recent_events),
            "events": [event.to_dict() for event in recent_events]
        }

        # Write to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"events_{timestamp}.json"
        file_path = Path(self.config.export_path) / filename

        try:
            with open(file_path, 'w') as f:
                json.dump(export_data, f, indent=2)

            self._last_flush = time.time()

        except Exception as e:
            logging.error(f"Failed to flush events: {e}")

    async def _aggregation_loop(self) -> None:
        """Background metrics aggregation."""
        while self._running:
            try:
                await asyncio.sleep(self.config.aggregation_window)
                await self._aggregate_pending_events()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"Metrics aggregation error: {e}")

    async def _aggregate_pending_events(self) -> None:
        """Aggregate recent events into summary metrics."""
        current_time = time.time()
        window_start = current_time - self.config.aggregation_window

        async with self._events_lock:
            events_to_aggregate = [
                e for e in self._events
                if e.timestamp >= window_start and isinstance(e.value, (int, float))
            ]

        if not events_to_aggregate:
            return

        # Group events by metric type and labels
        grouped_events = defaultdict(list)
        for event in events_to_aggregate:
            key = (event.metric_type, tuple(sorted(event.labels.items())))
            grouped_events[key].append(event)

        # Create aggregated metrics
        aggregated = []
        for (metric_type, labels_tuple), events in grouped_events.items():
            values = [e.value for e in events]
            labels = dict(labels_tuple)

            # Calculate percentiles
            sorted_values = sorted(values)
            percentiles = {}
            for p in [50, 90, 95, 99]:
                idx = int((p / 100) * len(sorted_values))
                percentiles[p] = sorted_values[min(idx, len(sorted_values) - 1)]

            aggregated_metric = AggregatedMetric(
                metric_type=metric_type,
                start_time=window_start,
                end_time=current_time,
                count=len(values),
                sum_value=sum(values),
                min_value=min(values),
                max_value=max(values),
                avg_value=sum(values) / len(values),
                percentiles=percentiles,
                labels=labels
            )

            aggregated.append(aggregated_metric)

        # Store aggregated metrics
        async with self._aggregation_lock:
            for metric in aggregated:
                self._aggregated_metrics[metric.metric_type.value].append(metric)

        self._last_aggregation = time.time()

    async def _cleanup_loop(self) -> None:
        """Background cleanup of old metrics."""
        while self._running:
            try:
                await asyncio.sleep(3600)  # Run every hour
                await self._cleanup_old_metrics()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"Metrics cleanup error: {e}")

    async def _cleanup_old_metrics(self) -> None:
        """Clean up old aggregated metrics."""
        cutoff_time = time.time() - (self.config.retention_hours * 3600)

        async with self._aggregation_lock:
            for metric_type in list(self._aggregated_metrics.keys()):
                metrics = self._aggregated_metrics[metric_type]
                self._aggregated_metrics[metric_type] = [
                    m for m in metrics if m.end_time >= cutoff_time
                ]

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc
        except Exception:
            return "unknown"

    # Export handlers
    async def _export_json(self, metrics: List[AggregatedMetric], file_path: Path) -> None:
        """Export metrics as JSON."""
        data = {
            "export_timestamp": datetime.now().isoformat(),
            "metric_count": len(metrics),
            "metrics": [metric.to_dict() for metric in metrics]
        }

        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)

    async def _export_csv(self, metrics: List[AggregatedMetric], file_path: Path) -> None:
        """Export metrics as CSV."""
        if not metrics:
            return

        with open(file_path, 'w', newline='') as f:
            writer = csv.writer(f)

            # Write header
            headers = [
                "metric_type", "start_time", "end_time", "duration_seconds",
                "count", "sum_value", "min_value", "max_value", "avg_value",
                "p50", "p90", "p95", "p99", "labels"
            ]
            writer.writerow(headers)

            # Write data
            for metric in metrics:
                row = [
                    metric.metric_type.value,
                    metric.start_time,
                    metric.end_time,
                    metric.end_time - metric.start_time,
                    metric.count,
                    metric.sum_value,
                    metric.min_value,
                    metric.max_value,
                    metric.avg_value,
                    metric.percentiles.get(50, ""),
                    metric.percentiles.get(90, ""),
                    metric.percentiles.get(95, ""),
                    metric.percentiles.get(99, ""),
                    json.dumps(metric.labels)
                ]
                writer.writerow(row)

    async def _export_prometheus(self, metrics: List[AggregatedMetric], file_path: Path) -> None:
        """Export metrics in Prometheus format."""
        lines = []
        lines.append(f"# HELP cloudflare_bypass_metrics CloudflareBypass metrics")
        lines.append(f"# TYPE cloudflare_bypass_metrics summary")

        for metric in metrics:
            labels_str = ",".join([f'{k}="{v}"' for k, v in metric.labels.items()])
            if labels_str:
                labels_str = "{" + labels_str + "}"

            metric_name = f"cloudflare_bypass_{metric.metric_type.value}"

            lines.append(f'{metric_name}_count{labels_str} {metric.count}')
            lines.append(f'{metric_name}_sum{labels_str} {metric.sum_value}')

            for p, value in metric.percentiles.items():
                quantile_labels = f'{labels_str[:-1]},quantile="{p/100}"}}' if labels_str else f'{{quantile="{p/100}"}}'
                lines.append(f'{metric_name}{quantile_labels} {value}')

        with open(file_path, 'w') as f:
            f.write('\n'.join(lines))

    async def _export_influxdb(self, metrics: List[AggregatedMetric], file_path: Path) -> None:
        """Export metrics in InfluxDB line protocol format."""
        lines = []

        for metric in metrics:
            measurement = f"cloudflare_bypass_{metric.metric_type.value}"

            # Tags (labels)
            tags = ",".join([f"{k}={v}" for k, v in metric.labels.items()])
            if tags:
                measurement += f",{tags}"

            # Fields
            fields = [
                f"count={metric.count}",
                f"sum={metric.sum_value}",
                f"min={metric.min_value}",
                f"max={metric.max_value}",
                f"avg={metric.avg_value}",
            ]

            for p, value in metric.percentiles.items():
                fields.append(f"p{p}={value}")

            fields_str = ",".join(fields)

            # Timestamp (nanoseconds)
            timestamp = int(metric.end_time * 1_000_000_000)

            line = f"{measurement} {fields_str} {timestamp}"
            lines.append(line)

        with open(file_path, 'w') as f:
            f.write('\n'.join(lines))


# Utility functions
def create_metrics_collector(config: MetricsConfig = None) -> MetricsCollector:
    """Create a new metrics collector."""
    return MetricsCollector(config)


def create_metrics_config(export_path: str = "./metrics",
                        buffer_size: int = 10000,
                        flush_interval: float = 60.0) -> MetricsConfig:
    """Create metrics configuration."""
    return MetricsConfig(
        export_path=export_path,
        buffer_size=buffer_size,
        flush_interval=flush_interval
    )


async def export_session_metrics(session: TestSession, collector: MetricsCollector,
                                format: ExportFormat = ExportFormat.JSON) -> str:
    """Export metrics for a specific session."""
    # Record session completion metrics
    if session.stats.total_requests > 0:
        await collector.record_throughput(
            session.stats.total_requests / max(session.duration_ms / 1000, 1),
            session_id=str(session.session_id)
        )

    await collector.record_event(
        MetricType.BYPASS_SUCCESS,
        session.stats.success_rate,
        labels={"session_name": session.name},
        session_id=str(session.session_id)
    )

    # Export metrics
    filename = f"session_{session.session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format.value}"
    return await collector.export_metrics(format=format, filename=filename)


# Export public API
__all__ = [
    "MetricType",
    "ExportFormat",
    "MetricEvent",
    "AggregatedMetric",
    "MetricsConfig",
    "MetricsCollector",
    "create_metrics_collector",
    "create_metrics_config",
    "export_session_metrics",
]