"""Resource management and limits for high-performance Cloudflare bypass operations.

Provides comprehensive resource monitoring, memory management, CPU throttling,
and system resource limits to ensure stable operation under high load.
"""

import asyncio
import psutil
import time
import threading
import weakref
from typing import Dict, List, Optional, Any, Callable, Union, NamedTuple
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import logging
import gc


class ResourceType(Enum):
    """Types of system resources."""
    MEMORY = "memory"
    CPU = "cpu"
    NETWORK = "network"
    DISK = "disk"
    HANDLES = "handles"
    THREADS = "threads"


class LimitAction(Enum):
    """Actions to take when limits are exceeded."""
    WARN = "warn"
    THROTTLE = "throttle"
    PAUSE = "pause"
    TERMINATE = "terminate"


class ResourceStatus(NamedTuple):
    """Resource status information."""
    current_usage: float
    limit: float
    percentage: float
    status: str
    last_check: float


@dataclass
class ResourceLimit:
    """Resource limit configuration."""
    resource_type: ResourceType
    soft_limit: float
    hard_limit: float
    action: LimitAction = LimitAction.THROTTLE
    check_interval: float = 1.0
    enabled: bool = True


@dataclass
class MemoryStats:
    """Memory usage statistics."""
    total_mb: float = 0.0
    available_mb: float = 0.0
    used_mb: float = 0.0
    percent_used: float = 0.0
    process_memory_mb: float = 0.0
    process_percent: float = 0.0


@dataclass
class CPUStats:
    """CPU usage statistics."""
    total_percent: float = 0.0
    process_percent: float = 0.0
    core_count: int = 0
    load_average: List[float] = field(default_factory=list)


@dataclass
class NetworkStats:
    """Network usage statistics."""
    bytes_sent: int = 0
    bytes_recv: int = 0
    packets_sent: int = 0
    packets_recv: int = 0
    connections: int = 0


@dataclass
class SystemResources:
    """Complete system resource information."""
    memory: MemoryStats = field(default_factory=MemoryStats)
    cpu: CPUStats = field(default_factory=CPUStats)
    network: NetworkStats = field(default_factory=NetworkStats)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "memory": {
                "total_mb": self.memory.total_mb,
                "available_mb": self.memory.available_mb,
                "used_mb": self.memory.used_mb,
                "percent_used": self.memory.percent_used,
                "process_memory_mb": self.memory.process_memory_mb,
                "process_percent": self.memory.process_percent,
            },
            "cpu": {
                "total_percent": self.cpu.total_percent,
                "process_percent": self.cpu.process_percent,
                "core_count": self.cpu.core_count,
                "load_average": self.cpu.load_average,
            },
            "network": {
                "bytes_sent": self.network.bytes_sent,
                "bytes_recv": self.network.bytes_recv,
                "packets_sent": self.network.packets_sent,
                "packets_recv": self.network.packets_recv,
                "connections": self.network.connections,
            },
            "timestamp": self.timestamp,
        }


class ResourceMonitor:
    """Monitors system resources and enforces limits."""

    def __init__(self):
        self._limits: Dict[ResourceType, ResourceLimit] = {}
        self._status: Dict[ResourceType, ResourceStatus] = {}
        self._history: deque = deque(maxlen=100)

        # Process handle
        self._process = psutil.Process()

        # Monitoring state
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

        # Callbacks
        self._limit_exceeded_callbacks: List[Callable] = []
        self._resource_update_callbacks: List[Callable] = []

        # Throttling state
        self._throttling = False
        self._throttle_factor = 1.0

        # Setup default limits
        self._setup_default_limits()

    def _setup_default_limits(self) -> None:
        """Setup default resource limits."""

        # Memory limits (in MB)
        total_memory_mb = psutil.virtual_memory().total / (1024 * 1024)
        self.set_limit(
            ResourceType.MEMORY,
            soft_limit=total_memory_mb * 0.8,  # 80% of total
            hard_limit=total_memory_mb * 0.9,  # 90% of total
            action=LimitAction.THROTTLE
        )

        # CPU limits (percentage)
        self.set_limit(
            ResourceType.CPU,
            soft_limit=80.0,  # 80% CPU usage
            hard_limit=95.0,  # 95% CPU usage
            action=LimitAction.THROTTLE
        )

        # Network connection limits
        self.set_limit(
            ResourceType.NETWORK,
            soft_limit=1000,  # 1000 connections
            hard_limit=2000,  # 2000 connections
            action=LimitAction.PAUSE
        )

    def set_limit(self,
                  resource_type: ResourceType,
                  soft_limit: float,
                  hard_limit: float,
                  action: LimitAction = LimitAction.THROTTLE,
                  check_interval: float = 1.0) -> None:
        """Set a resource limit."""

        limit = ResourceLimit(
            resource_type=resource_type,
            soft_limit=soft_limit,
            hard_limit=hard_limit,
            action=action,
            check_interval=check_interval
        )

        self._limits[resource_type] = limit

    def remove_limit(self, resource_type: ResourceType) -> None:
        """Remove a resource limit."""
        if resource_type in self._limits:
            del self._limits[resource_type]
        if resource_type in self._status:
            del self._status[resource_type]

    async def start_monitoring(self) -> None:
        """Start resource monitoring."""
        if self._monitoring:
            return

        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())

    async def stop_monitoring(self) -> None:
        """Stop resource monitoring."""
        self._monitoring = False

        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

    async def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self._monitoring:
            try:
                await self._check_resources()
                await asyncio.sleep(0.5)  # Check every 500ms
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"Error in resource monitoring: {e}")
                await asyncio.sleep(1.0)

    async def _check_resources(self) -> None:
        """Check all monitored resources."""
        async with self._lock:
            current_resources = self._get_current_resources()
            self._history.append(current_resources)

            # Check each configured limit
            for resource_type, limit in self._limits.items():
                if not limit.enabled:
                    continue

                current_usage = self._get_resource_usage(current_resources, resource_type)
                await self._check_limit(resource_type, limit, current_usage)

            # Trigger update callbacks
            for callback in self._resource_update_callbacks:
                try:
                    await callback(current_resources)
                except Exception:
                    pass

    def _get_current_resources(self) -> SystemResources:
        """Get current system resource usage."""

        # Memory stats
        memory = psutil.virtual_memory()
        process_memory = self._process.memory_info()

        memory_stats = MemoryStats(
            total_mb=memory.total / (1024 * 1024),
            available_mb=memory.available / (1024 * 1024),
            used_mb=memory.used / (1024 * 1024),
            percent_used=memory.percent,
            process_memory_mb=process_memory.rss / (1024 * 1024),
            process_percent=self._process.memory_percent()
        )

        # CPU stats
        cpu_stats = CPUStats(
            total_percent=psutil.cpu_percent(),
            process_percent=self._process.cpu_percent(),
            core_count=psutil.cpu_count(),
            load_average=list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else []
        )

        # Network stats
        try:
            net_io = psutil.net_io_counters()
            connections = len(self._process.connections())

            network_stats = NetworkStats(
                bytes_sent=net_io.bytes_sent,
                bytes_recv=net_io.bytes_recv,
                packets_sent=net_io.packets_sent,
                packets_recv=net_io.packets_recv,
                connections=connections
            )
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            network_stats = NetworkStats()

        return SystemResources(
            memory=memory_stats,
            cpu=cpu_stats,
            network=network_stats
        )

    def _get_resource_usage(self, resources: SystemResources, resource_type: ResourceType) -> float:
        """Get current usage for a specific resource type."""

        if resource_type == ResourceType.MEMORY:
            return resources.memory.process_memory_mb
        elif resource_type == ResourceType.CPU:
            return resources.cpu.process_percent
        elif resource_type == ResourceType.NETWORK:
            return resources.network.connections
        else:
            return 0.0

    async def _check_limit(self, resource_type: ResourceType, limit: ResourceLimit, current_usage: float) -> None:
        """Check if a resource limit is exceeded."""

        now = time.time()

        # Determine status
        if current_usage >= limit.hard_limit:
            status = "hard_limit_exceeded"
            percentage = (current_usage / limit.hard_limit) * 100
            await self._handle_limit_exceeded(resource_type, limit, current_usage, True)
        elif current_usage >= limit.soft_limit:
            status = "soft_limit_exceeded"
            percentage = (current_usage / limit.soft_limit) * 100
            await self._handle_limit_exceeded(resource_type, limit, current_usage, False)
        else:
            status = "normal"
            percentage = (current_usage / limit.soft_limit) * 100
            await self._handle_limit_normal(resource_type)

        # Update status
        self._status[resource_type] = ResourceStatus(
            current_usage=current_usage,
            limit=limit.hard_limit,
            percentage=percentage,
            status=status,
            last_check=now
        )

    async def _handle_limit_exceeded(self, resource_type: ResourceType, limit: ResourceLimit,
                                   current_usage: float, is_hard_limit: bool) -> None:
        """Handle resource limit exceeded."""

        # Take action based on limit configuration
        if limit.action == LimitAction.WARN:
            logging.warning(f"Resource limit exceeded: {resource_type.value} = {current_usage}")

        elif limit.action == LimitAction.THROTTLE:
            await self._apply_throttling(resource_type, current_usage, limit)

        elif limit.action == LimitAction.PAUSE:
            await self._apply_pause(resource_type)

        elif limit.action == LimitAction.TERMINATE:
            if is_hard_limit:
                logging.critical(f"Hard limit exceeded for {resource_type.value}, terminating")
                # Could implement graceful shutdown here

        # Trigger callbacks
        for callback in self._limit_exceeded_callbacks:
            try:
                await callback(resource_type, current_usage, limit, is_hard_limit)
            except Exception:
                pass

    async def _handle_limit_normal(self, resource_type: ResourceType) -> None:
        """Handle resource returning to normal levels."""
        if self._throttling:
            # Gradually reduce throttling
            self._throttle_factor = min(1.0, self._throttle_factor + 0.1)
            if self._throttle_factor >= 1.0:
                self._throttling = False

    async def _apply_throttling(self, resource_type: ResourceType, current_usage: float, limit: ResourceLimit) -> None:
        """Apply throttling based on resource usage."""

        if not self._throttling:
            self._throttling = True

        # Calculate throttle factor based on how much over limit we are
        overage = (current_usage - limit.soft_limit) / (limit.hard_limit - limit.soft_limit)
        self._throttle_factor = max(0.1, 1.0 - overage)

        # Apply delay based on throttle factor
        delay = (1.0 - self._throttle_factor) * 0.1  # Up to 100ms delay
        if delay > 0:
            await asyncio.sleep(delay)

    async def _apply_pause(self, resource_type: ResourceType) -> None:
        """Apply pause for resource recovery."""
        logging.warning(f"Pausing operations due to {resource_type.value} limit")
        await asyncio.sleep(1.0)  # Pause for 1 second

    def get_resource_status(self, resource_type: ResourceType) -> Optional[ResourceStatus]:
        """Get current status for a specific resource."""
        return self._status.get(resource_type)

    def get_all_resource_status(self) -> Dict[ResourceType, ResourceStatus]:
        """Get status for all monitored resources."""
        return self._status.copy()

    def get_current_resources(self) -> SystemResources:
        """Get current system resources (public method)."""
        return self._get_current_resources()

    def get_resource_history(self, count: int = 100) -> List[SystemResources]:
        """Get resource usage history."""
        return list(self._history)[-count:]

    def is_throttling(self) -> bool:
        """Check if currently throttling."""
        return self._throttling

    def get_throttle_factor(self) -> float:
        """Get current throttle factor (0.0 to 1.0)."""
        return self._throttle_factor

    def force_garbage_collection(self) -> Dict[str, int]:
        """Force garbage collection and return stats."""
        before_counts = [len(gc.get_objects())]

        # Run garbage collection
        collected = []
        for generation in range(3):
            collected.append(gc.collect(generation))

        after_counts = [len(gc.get_objects())]

        return {
            "objects_before": before_counts[0],
            "objects_after": after_counts[0],
            "objects_freed": before_counts[0] - after_counts[0],
            "collected_gen0": collected[0],
            "collected_gen1": collected[1],
            "collected_gen2": collected[2],
        }

    def optimize_memory(self) -> Dict[str, Any]:
        """Optimize memory usage."""
        stats = {}

        # Force garbage collection
        gc_stats = self.force_garbage_collection()
        stats["garbage_collection"] = gc_stats

        # Get memory stats before and after
        before_memory = self._process.memory_info().rss / (1024 * 1024)

        # Additional cleanup could go here

        after_memory = self._process.memory_info().rss / (1024 * 1024)

        stats["memory_mb_before"] = before_memory
        stats["memory_mb_after"] = after_memory
        stats["memory_freed_mb"] = before_memory - after_memory

        return stats

    def add_limit_exceeded_callback(self, callback: Callable) -> None:
        """Add callback for limit exceeded events."""
        self._limit_exceeded_callbacks.append(callback)

    def add_resource_update_callback(self, callback: Callable) -> None:
        """Add callback for resource updates."""
        self._resource_update_callbacks.append(callback)

    def get_memory_breakdown(self) -> Dict[str, float]:
        """Get detailed memory breakdown."""
        try:
            memory_info = self._process.memory_full_info()
            return {
                "rss_mb": memory_info.rss / (1024 * 1024),
                "vms_mb": memory_info.vms / (1024 * 1024),
                "shared_mb": getattr(memory_info, 'shared', 0) / (1024 * 1024),
                "text_mb": getattr(memory_info, 'text', 0) / (1024 * 1024),
                "data_mb": getattr(memory_info, 'data', 0) / (1024 * 1024),
            }
        except (psutil.AccessDenied, AttributeError):
            memory_info = self._process.memory_info()
            return {
                "rss_mb": memory_info.rss / (1024 * 1024),
                "vms_mb": memory_info.vms / (1024 * 1024),
            }


class ResourceManager:
    """High-level resource management coordinator."""

    def __init__(self):
        self.monitor = ResourceMonitor()
        self._auto_optimization = False
        self._optimization_task: Optional[asyncio.Task] = None

    async def start(self, auto_optimize: bool = True) -> None:
        """Start resource management."""
        await self.monitor.start_monitoring()

        if auto_optimize:
            self._auto_optimization = True
            self._optimization_task = asyncio.create_task(self._auto_optimize_loop())

    async def stop(self) -> None:
        """Stop resource management."""
        self._auto_optimization = False

        if self._optimization_task:
            self._optimization_task.cancel()
            try:
                await self._optimization_task
            except asyncio.CancelledError:
                pass

        await self.monitor.stop_monitoring()

    async def _auto_optimize_loop(self) -> None:
        """Auto-optimization loop."""
        while self._auto_optimization:
            try:
                await asyncio.sleep(30.0)  # Check every 30 seconds

                # Check if memory optimization is needed
                memory_status = self.monitor.get_resource_status(ResourceType.MEMORY)
                if memory_status and memory_status.percentage > 70:
                    self.monitor.optimize_memory()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"Error in auto-optimization: {e}")


# Utility functions
def create_resource_monitor() -> ResourceMonitor:
    """Create a new resource monitor."""
    return ResourceMonitor()


def create_resource_manager() -> ResourceManager:
    """Create a new resource manager."""
    return ResourceManager()


def get_system_limits() -> Dict[str, float]:
    """Get recommended system limits based on current hardware."""

    memory = psutil.virtual_memory()
    cpu_count = psutil.cpu_count()

    return {
        "memory_soft_limit_mb": (memory.total / (1024 * 1024)) * 0.7,  # 70%
        "memory_hard_limit_mb": (memory.total / (1024 * 1024)) * 0.85,  # 85%
        "cpu_soft_limit_percent": 70.0,
        "cpu_hard_limit_percent": 90.0,
        "connections_soft_limit": max(1000, cpu_count * 200),
        "connections_hard_limit": max(2000, cpu_count * 400),
    }


async def wait_for_resources(monitor: ResourceMonitor,
                           resource_types: List[ResourceType],
                           max_wait: float = 30.0) -> bool:
    """Wait for resources to become available."""

    start_time = time.time()

    while time.time() - start_time < max_wait:
        all_available = True

        for resource_type in resource_types:
            status = monitor.get_resource_status(resource_type)
            if status and status.status != "normal":
                all_available = False
                break

        if all_available:
            return True

        await asyncio.sleep(0.5)

    return False


def check_system_health() -> Dict[str, Any]:
    """Quick system health check."""

    memory = psutil.virtual_memory()
    cpu_percent = psutil.cpu_percent(interval=1)

    health = {
        "memory_available_gb": memory.available / (1024 * 1024 * 1024),
        "memory_percent_used": memory.percent,
        "cpu_percent": cpu_percent,
        "load_average": list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else [],
        "disk_usage": {},
    }

    # Check disk usage for key partitions
    try:
        for partition in psutil.disk_partitions():
            if partition.fstype:
                usage = psutil.disk_usage(partition.mountpoint)
                health["disk_usage"][partition.mountpoint] = {
                    "total_gb": usage.total / (1024 * 1024 * 1024),
                    "free_gb": usage.free / (1024 * 1024 * 1024),
                    "percent_used": (usage.used / usage.total) * 100
                }
    except (psutil.AccessDenied, OSError):
        pass

    # Overall health score (0-100)
    health_score = 100
    if memory.percent > 90:
        health_score -= 30
    elif memory.percent > 80:
        health_score -= 15

    if cpu_percent > 90:
        health_score -= 30
    elif cpu_percent > 80:
        health_score -= 15

    health["health_score"] = max(0, health_score)
    health["status"] = "healthy" if health_score > 70 else "degraded" if health_score > 40 else "critical"

    return health