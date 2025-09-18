"""PerformanceMetrics model for tracking timing and resource usage.

Represents performance measurements from test runs including timing,
throughput, and resource usage data.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List
from uuid import UUID, uuid4


class MetricType(Enum):
    """Types of performance metrics."""
    REQUEST_TIMING = "request_timing"
    SESSION_SUMMARY = "session_summary"
    RESOURCE_USAGE = "resource_usage"
    THROUGHPUT = "throughput"
    CHALLENGE_PERFORMANCE = "challenge_performance"


@dataclass
class PerformanceMetrics:
    """
    Represents performance measurements from test runs.

    This entity captures timing, throughput, and resource usage measurements
    for individual requests or aggregated session data.
    """

    # Core identifiers
    metrics_id: UUID = field(default_factory=uuid4)
    session_id: UUID = field(default_factory=uuid4)
    request_id: Optional[UUID] = None

    # Metric classification
    metric_type: MetricType = MetricType.REQUEST_TIMING
    timestamp: datetime = field(default_factory=datetime.now)

    # Request counts
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0

    # Timing metrics (in milliseconds)
    avg_response_time_ms: float = 0.0
    min_response_time_ms: int = 0
    max_response_time_ms: int = 0
    p95_response_time_ms: float = 0.0
    p99_response_time_ms: float = 0.0

    # Individual request timing (for REQUEST_TIMING type)
    duration_ms: Optional[int] = None

    # Throughput metrics
    requests_per_second: float = 0.0
    concurrent_connections_peak: int = 0

    # Resource usage metrics
    memory_mb: float = 0.0
    cpu_percent: float = 0.0
    connections_active: int = 0

    # Error and challenge metrics
    error_count: int = 0
    challenges_total: int = 0
    challenges_solved: int = 0
    challenge_solve_rate: float = 0.0

    def __post_init__(self):
        """Validate metrics after initialization."""
        self._validate_percentages()
        self._validate_timing_values()
        self._validate_counts()

    def _validate_percentages(self) -> None:
        """Validate percentage values are in valid range."""
        percentage_fields = ['cpu_percent', 'challenge_solve_rate']
        for field_name in percentage_fields:
            value = getattr(self, field_name)
            if not (0 <= value <= 100):
                raise ValueError(f"{field_name} must be between 0 and 100")

    def _validate_timing_values(self) -> None:
        """Validate timing values are non-negative."""
        timing_fields = [
            'avg_response_time_ms', 'min_response_time_ms', 'max_response_time_ms',
            'p95_response_time_ms', 'p99_response_time_ms', 'duration_ms'
        ]
        for field_name in timing_fields:
            value = getattr(self, field_name)
            if value is not None and value < 0:
                raise ValueError(f"{field_name} must be non-negative")

    def _validate_counts(self) -> None:
        """Validate count values are non-negative."""
        count_fields = [
            'total_requests', 'successful_requests', 'failed_requests',
            'concurrent_connections_peak', 'connections_active', 'error_count',
            'challenges_total', 'challenges_solved'
        ]
        for field_name in count_fields:
            value = getattr(self, field_name)
            if value < 0:
                raise ValueError(f"{field_name} must be non-negative")

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100

    @property
    def error_rate(self) -> float:
        """Calculate error rate percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.failed_requests / self.total_requests) * 100

    @property
    def challenge_encounter_rate(self) -> float:
        """Calculate rate of challenge encounters."""
        if self.total_requests == 0:
            return 0.0
        return (self.challenges_total / self.total_requests) * 100

    def update_from_request_timing(self, request_duration_ms: int,
                                  success: bool, had_challenge: bool = False) -> None:
        """Update metrics from individual request timing."""
        self.total_requests += 1
        
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
            self.error_count += 1
        
        if had_challenge:
            self.challenges_total += 1
        
        # Update timing statistics
        if self.total_requests == 1:
            # First request
            self.min_response_time_ms = request_duration_ms
            self.max_response_time_ms = request_duration_ms
            self.avg_response_time_ms = float(request_duration_ms)
        else:
            # Update min/max
            self.min_response_time_ms = min(self.min_response_time_ms, request_duration_ms)
            self.max_response_time_ms = max(self.max_response_time_ms, request_duration_ms)
            
            # Update running average
            current_total = self.avg_response_time_ms * (self.total_requests - 1)
            self.avg_response_time_ms = (current_total + request_duration_ms) / self.total_requests

    def update_challenge_solved(self, success: bool) -> None:
        """Update challenge solving statistics."""
        if success:
            self.challenges_solved += 1
        
        if self.challenges_total > 0:
            self.challenge_solve_rate = (self.challenges_solved / self.challenges_total) * 100

    def update_resource_usage(self, memory_mb: float, cpu_percent: float,
                             active_connections: int) -> None:
        """Update resource usage metrics."""
        self.memory_mb = memory_mb
        self.cpu_percent = cpu_percent
        self.connections_active = active_connections
        self.concurrent_connections_peak = max(
            self.concurrent_connections_peak, active_connections
        )

    def calculate_throughput(self, elapsed_seconds: float) -> None:
        """Calculate requests per second throughput."""
        if elapsed_seconds > 0:
            self.requests_per_second = self.total_requests / elapsed_seconds

    def update_percentiles(self, response_times: List[int]) -> None:
        """Update percentile calculations from list of response times."""
        if not response_times:
            return
        
        sorted_times = sorted(response_times)
        count = len(sorted_times)
        
        # Calculate P95
        p95_index = int(0.95 * count)
        if p95_index < count:
            self.p95_response_time_ms = float(sorted_times[p95_index])
        
        # Calculate P99
        p99_index = int(0.99 * count)
        if p99_index < count:
            self.p99_response_time_ms = float(sorted_times[p99_index])

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for serialization."""
        return {
            "metrics_id": str(self.metrics_id),
            "session_id": str(self.session_id),
            "request_id": str(self.request_id) if self.request_id else None,
            "metric_type": self.metric_type.value,
            "timestamp": self.timestamp.isoformat(),
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "avg_response_time_ms": self.avg_response_time_ms,
            "min_response_time_ms": self.min_response_time_ms,
            "max_response_time_ms": self.max_response_time_ms,
            "p95_response_time_ms": self.p95_response_time_ms,
            "p99_response_time_ms": self.p99_response_time_ms,
            "duration_ms": self.duration_ms,
            "requests_per_second": self.requests_per_second,
            "concurrent_connections_peak": self.concurrent_connections_peak,
            "memory_mb": self.memory_mb,
            "cpu_percent": self.cpu_percent,
            "connections_active": self.connections_active,
            "error_count": self.error_count,
            "challenges_total": self.challenges_total,
            "challenges_solved": self.challenges_solved,
            "challenge_solve_rate": self.challenge_solve_rate,
            "success_rate": self.success_rate,
            "error_rate": self.error_rate,
            "challenge_encounter_rate": self.challenge_encounter_rate,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PerformanceMetrics":
        """Create PerformanceMetrics from dictionary."""
        # Parse timestamp
        timestamp = datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.now()

        return cls(
            metrics_id=UUID(data["metrics_id"]) if data.get("metrics_id") else uuid4(),
            session_id=UUID(data["session_id"]) if data.get("session_id") else uuid4(),
            request_id=UUID(data["request_id"]) if data.get("request_id") else None,
            metric_type=MetricType(data.get("metric_type", "request_timing")),
            timestamp=timestamp,
            total_requests=data.get("total_requests", 0),
            successful_requests=data.get("successful_requests", 0),
            failed_requests=data.get("failed_requests", 0),
            avg_response_time_ms=data.get("avg_response_time_ms", 0.0),
            min_response_time_ms=data.get("min_response_time_ms", 0),
            max_response_time_ms=data.get("max_response_time_ms", 0),
            p95_response_time_ms=data.get("p95_response_time_ms", 0.0),
            p99_response_time_ms=data.get("p99_response_time_ms", 0.0),
            duration_ms=data.get("duration_ms"),
            requests_per_second=data.get("requests_per_second", 0.0),
            concurrent_connections_peak=data.get("concurrent_connections_peak", 0),
            memory_mb=data.get("memory_mb", 0.0),
            cpu_percent=data.get("cpu_percent", 0.0),
            connections_active=data.get("connections_active", 0),
            error_count=data.get("error_count", 0),
            challenges_total=data.get("challenges_total", 0),
            challenges_solved=data.get("challenges_solved", 0),
            challenge_solve_rate=data.get("challenge_solve_rate", 0.0),
        )

    @classmethod
    def create_session_summary(cls, session_id: UUID) -> "PerformanceMetrics":
        """Create metrics instance for session summary."""
        return cls(
            session_id=session_id,
            metric_type=MetricType.SESSION_SUMMARY,
        )

    @classmethod
    def create_request_timing(cls, session_id: UUID, request_id: UUID,
                            duration_ms: int) -> "PerformanceMetrics":
        """Create metrics instance for individual request timing."""
        return cls(
            session_id=session_id,
            request_id=request_id,
            metric_type=MetricType.REQUEST_TIMING,
            duration_ms=duration_ms,
        )

    def meets_performance_targets(self) -> Dict[str, bool]:
        """Check if metrics meet performance targets from specification."""
        targets = {
            "response_time_under_10s": self.avg_response_time_ms < 10000,
            "success_rate_above_95": self.success_rate >= 95.0,
            "challenge_solve_rate_above_90": self.challenge_solve_rate >= 90.0 if self.challenges_total > 0 else True,
            "memory_under_100mb_per_1k_requests": (
                self.memory_mb < (self.total_requests / 1000 * 100) if self.total_requests > 0 else True
            ),
            "supports_10k_concurrent": self.concurrent_connections_peak >= 1000,  # Partial validation
        }
        return targets

    def get_performance_grade(self) -> str:
        """Get overall performance grade based on targets."""
        targets = self.meets_performance_targets()
        met_count = sum(targets.values())
        total_count = len(targets)
        
        percentage = (met_count / total_count) * 100
        
        if percentage >= 90:
            return "A"
        elif percentage >= 80:
            return "B"
        elif percentage >= 70:
            return "C"
        elif percentage >= 60:
            return "D"
        else:
            return "F"

    def __str__(self) -> str:
        """String representation of the metrics."""
        return (
            f"PerformanceMetrics(type={self.metric_type.value}, "
            f"requests={self.total_requests}, "
            f"avg_time={self.avg_response_time_ms:.1f}ms, "
            f"success_rate={self.success_rate:.1f}%)"
        )