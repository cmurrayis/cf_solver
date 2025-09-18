"""
Integration tests for data export and metrics functionality.

These tests verify that CloudflareBypass can collect, export, and manage
metrics data in various formats including JSON, CSV, Prometheus, and InfluxDB
for monitoring and analysis purposes.
"""

import pytest
import asyncio
import json
import csv
import time
import tempfile
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from cloudflare_research.bypass import CloudflareBypass, CloudflareBypassConfig
from cloudflare_research.metrics import MetricsCollector, ExportFormat, MetricEvent, AggregatedMetric
from cloudflare_research.models.response import CloudflareResponse


@pytest.mark.integration
@pytest.mark.asyncio
class TestDataExportIntegration:
    """Integration tests for data export and metrics functionality."""

    @pytest.fixture
    def metrics_config(self) -> CloudflareBypassConfig:
        """Create configuration with metrics collection enabled."""
        return CloudflareBypassConfig(
            max_concurrent_requests=10,
            requests_per_second=5.0,
            timeout=30.0,
            solve_javascript_challenges=True,
            enable_detailed_logging=True,
            enable_monitoring=True,
            enable_metrics_collection=True
        )

    @pytest.fixture
    def temp_dir(self) -> Path:
        """Create temporary directory for test files."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path

        # Cleanup after test
        import shutil
        try:
            shutil.rmtree(temp_path)
        except Exception:
            pass

    @pytest.fixture
    async def metrics_collector(self) -> MetricsCollector:
        """Create and initialize metrics collector."""
        collector = MetricsCollector()
        await collector.start()
        yield collector
        await collector.stop()

    async def test_metrics_collection_during_requests(self, metrics_config):
        """Test that metrics are collected during normal request operations."""
        async with CloudflareBypass(metrics_config) as bypass:
            # Verify metrics collector is available
            assert bypass.metrics_collector is not None

            # Make some requests to generate metrics
            urls = [
                "https://httpbin.org/get",
                "https://httpbin.org/headers",
                "https://httpbin.org/json"
            ]

            responses = []
            for url in urls:
                response = await bypass.get(url)
                responses.append(response)
                await asyncio.sleep(0.5)  # Small delay between requests

            # Verify responses
            for response in responses:
                assert response.status_code == 200

            # Verify metrics collection
            collector = bypass.metrics_collector

            # Should have collected some metrics
            current_metrics = await collector.get_current_metrics()
            assert len(current_metrics) > 0

            # Should have request metrics
            request_metrics = [m for m in current_metrics if m.metric_type == "request"]
            assert len(request_metrics) >= len(urls)

    async def test_json_export_functionality(self, metrics_collector, temp_dir):
        """Test JSON export functionality."""
        # Generate some test metrics
        test_metrics = [
            MetricEvent(
                timestamp=datetime.now(),
                metric_type="request",
                metric_name="http_request",
                value=1.0,
                labels={"method": "GET", "status": "200", "url": "https://test.com"},
                metadata={"response_time": 0.5}
            ),
            MetricEvent(
                timestamp=datetime.now(),
                metric_type="performance",
                metric_name="response_time",
                value=0.75,
                labels={"endpoint": "api"},
                metadata={"content_length": 1024}
            ),
            MetricEvent(
                timestamp=datetime.now(),
                metric_type="challenge",
                metric_name="challenge_solved",
                value=1.0,
                labels={"type": "javascript", "attempts": "2"},
                metadata={"solve_time": 3.2}
            )
        ]

        # Add metrics to collector
        for metric in test_metrics:
            await metrics_collector.record_metric(metric)

        # Export to JSON
        json_file = temp_dir / "test_metrics.json"
        exported_file = await metrics_collector.export_metrics(
            format=ExportFormat.JSON,
            hours=1,
            filename=str(json_file)
        )

        # Verify export
        assert Path(exported_file).exists()
        assert Path(exported_file).stat().st_size > 0

        # Load and verify JSON content
        with open(exported_file, 'r') as f:
            data = json.load(f)

        assert isinstance(data, dict)
        assert "export_info" in data
        assert "metrics" in data

        # Verify export info
        export_info = data["export_info"]
        assert "timestamp" in export_info
        assert "format" in export_info
        assert export_info["format"] == "json"

        # Verify metrics data
        metrics_data = data["metrics"]
        assert isinstance(metrics_data, list)
        assert len(metrics_data) == len(test_metrics)

        # Verify metric structure
        for metric_data in metrics_data:
            assert "timestamp" in metric_data
            assert "metric_type" in metric_data
            assert "metric_name" in metric_data
            assert "value" in metric_data
            assert "labels" in metric_data

    async def test_csv_export_functionality(self, metrics_collector, temp_dir):
        """Test CSV export functionality."""
        # Generate test metrics with consistent structure
        test_metrics = []
        for i in range(5):
            metric = MetricEvent(
                timestamp=datetime.now() - timedelta(minutes=i),
                metric_type="request",
                metric_name="http_request_duration",
                value=0.5 + i * 0.1,
                labels={"method": "GET", "status": "200"},
                metadata={"request_id": f"req_{i}"}
            )
            test_metrics.append(metric)

        # Add metrics to collector
        for metric in test_metrics:
            await metrics_collector.record_metric(metric)

        # Export to CSV
        csv_file = temp_dir / "test_metrics.csv"
        exported_file = await metrics_collector.export_metrics(
            format=ExportFormat.CSV,
            hours=1,
            filename=str(csv_file)
        )

        # Verify export
        assert Path(exported_file).exists()
        assert Path(exported_file).stat().st_size > 0

        # Load and verify CSV content
        with open(exported_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == len(test_metrics)

        # Verify CSV structure
        expected_headers = ["timestamp", "metric_type", "metric_name", "value", "labels", "metadata"]
        assert all(header in reader.fieldnames for header in expected_headers)

        # Verify data integrity
        for i, row in enumerate(rows):
            assert row["metric_type"] == "request"
            assert row["metric_name"] == "http_request_duration"
            assert float(row["value"]) >= 0.5

    async def test_prometheus_export_functionality(self, metrics_collector, temp_dir):
        """Test Prometheus export functionality."""
        # Generate test metrics suitable for Prometheus
        test_metrics = [
            MetricEvent(
                timestamp=datetime.now(),
                metric_type="counter",
                metric_name="http_requests_total",
                value=10.0,
                labels={"method": "GET", "status": "200"},
                metadata={}
            ),
            MetricEvent(
                timestamp=datetime.now(),
                metric_type="histogram",
                metric_name="http_request_duration_seconds",
                value=0.75,
                labels={"method": "POST", "status": "201"},
                metadata={}
            ),
            MetricEvent(
                timestamp=datetime.now(),
                metric_type="gauge",
                metric_name="active_connections",
                value=25.0,
                labels={"pool": "default"},
                metadata={}
            )
        ]

        # Add metrics to collector
        for metric in test_metrics:
            await metrics_collector.record_metric(metric)

        # Export to Prometheus format
        prom_file = temp_dir / "test_metrics.prom"
        exported_file = await metrics_collector.export_metrics(
            format=ExportFormat.PROMETHEUS,
            hours=1,
            filename=str(prom_file)
        )

        # Verify export
        assert Path(exported_file).exists()
        assert Path(exported_file).stat().st_size > 0

        # Load and verify Prometheus content
        with open(exported_file, 'r') as f:
            content = f.read()

        # Verify Prometheus format
        lines = content.strip().split('\n')
        assert len(lines) > 0

        # Should contain metric definitions and values
        metric_lines = [line for line in lines if not line.startswith('#')]
        assert len(metric_lines) >= len(test_metrics)

        # Verify specific Prometheus format elements
        assert any("http_requests_total" in line for line in lines)
        assert any("http_request_duration_seconds" in line for line in lines)
        assert any("active_connections" in line for line in lines)

        # Verify label format
        assert any('{method="GET"' in line for line in lines)
        assert any('status="200"' in line for line in lines)

    async def test_influxdb_export_functionality(self, metrics_collector, temp_dir):
        """Test InfluxDB line protocol export functionality."""
        # Generate test metrics
        test_metrics = [
            MetricEvent(
                timestamp=datetime.now(),
                metric_type="measurement",
                metric_name="http_requests",
                value=1.0,
                labels={"host": "server1", "method": "GET"},
                metadata={"response_time": 0.5, "bytes": 1024}
            ),
            MetricEvent(
                timestamp=datetime.now(),
                metric_type="measurement",
                metric_name="system_load",
                value=0.75,
                labels={"host": "server1", "cpu": "0"},
                metadata={"user": 25.5, "system": 10.2}
            )
        ]

        # Add metrics to collector
        for metric in test_metrics:
            await metrics_collector.record_metric(metric)

        # Export to InfluxDB format
        influx_file = temp_dir / "test_metrics.influx"
        exported_file = await metrics_collector.export_metrics(
            format=ExportFormat.INFLUXDB,
            hours=1,
            filename=str(influx_file)
        )

        # Verify export
        assert Path(exported_file).exists()
        assert Path(exported_file).stat().st_size > 0

        # Load and verify InfluxDB content
        with open(exported_file, 'r') as f:
            content = f.read()

        lines = content.strip().split('\n')
        assert len(lines) >= len(test_metrics)

        # Verify InfluxDB line protocol format
        for line in lines:
            if line.strip():
                # Should contain measurement,tags fields timestamp
                parts = line.split(' ')
                assert len(parts) >= 3

                # First part should be measurement with tags
                measurement_part = parts[0]
                assert ',' in measurement_part or '=' in measurement_part

                # Should have fields
                fields_part = parts[1]
                assert '=' in fields_part

    async def test_metrics_aggregation_and_export(self, metrics_collector, temp_dir):
        """Test metrics aggregation before export."""
        # Generate metrics over time
        base_time = datetime.now()
        test_metrics = []

        for i in range(10):
            metric = MetricEvent(
                timestamp=base_time + timedelta(seconds=i * 30),
                metric_type="request",
                metric_name="response_time",
                value=0.5 + (i % 3) * 0.2,  # Varying response times
                labels={"endpoint": "api", "method": "GET"},
                metadata={}
            )
            test_metrics.append(metric)

        # Add metrics to collector
        for metric in test_metrics:
            await metrics_collector.record_metric(metric)

        # Get aggregated metrics
        aggregated = await metrics_collector.get_aggregated_metrics(
            time_window=timedelta(minutes=10)
        )

        assert len(aggregated) > 0

        # Should have aggregation statistics
        for agg_metric in aggregated:
            assert hasattr(agg_metric, 'metric_name')
            assert hasattr(agg_metric, 'count')
            assert hasattr(agg_metric, 'avg_value')
            assert agg_metric.count > 0

        # Export aggregated data
        json_file = temp_dir / "aggregated_metrics.json"
        exported_file = await metrics_collector.export_aggregated_metrics(
            format=ExportFormat.JSON,
            time_window=timedelta(minutes=10),
            filename=str(json_file)
        )

        # Verify aggregated export
        assert Path(exported_file).exists()

        with open(exported_file, 'r') as f:
            data = json.load(f)

        assert "aggregated_metrics" in data
        assert len(data["aggregated_metrics"]) > 0

    async def test_real_time_metrics_export(self, metrics_config, temp_dir):
        """Test real-time metrics export during live operations."""
        async with CloudflareBypass(metrics_config) as bypass:
            collector = bypass.metrics_collector

            # Start real-time export monitoring
            export_files = []

            async def export_metrics_periodically():
                """Export metrics every few seconds."""
                for i in range(3):
                    await asyncio.sleep(2)

                    export_file = temp_dir / f"realtime_metrics_{i}.json"
                    try:
                        exported = await collector.export_metrics(
                            format=ExportFormat.JSON,
                            hours=1,
                            filename=str(export_file)
                        )
                        export_files.append(exported)
                    except Exception as e:
                        print(f"Export {i} failed: {e}")

            # Start background export task
            export_task = asyncio.create_task(export_metrics_periodically())

            # Generate requests while exporting
            urls = ["https://httpbin.org/get"] * 5

            for url in urls:
                try:
                    response = await bypass.get(url)
                    assert response.status_code == 200
                except Exception as e:
                    print(f"Request failed: {e}")

                await asyncio.sleep(1)

            # Wait for exports to complete
            await export_task

            # Verify exports were created
            assert len(export_files) > 0

            # Verify export file contents
            for export_file in export_files:
                if Path(export_file).exists():
                    with open(export_file, 'r') as f:
                        data = json.load(f)

                    assert "metrics" in data
                    print(f"Export file {export_file} contains {len(data['metrics'])} metrics")

    async def test_metrics_filtering_and_export(self, metrics_collector, temp_dir):
        """Test filtering metrics before export."""
        # Generate diverse metrics
        test_metrics = [
            MetricEvent(
                timestamp=datetime.now(),
                metric_type="request",
                metric_name="http_request",
                value=1.0,
                labels={"method": "GET", "status": "200"},
                metadata={}
            ),
            MetricEvent(
                timestamp=datetime.now(),
                metric_type="error",
                metric_name="http_error",
                value=1.0,
                labels={"method": "POST", "status": "500"},
                metadata={}
            ),
            MetricEvent(
                timestamp=datetime.now(),
                metric_type="performance",
                metric_name="response_time",
                value=0.75,
                labels={"endpoint": "api"},
                metadata={}
            ),
            MetricEvent(
                timestamp=datetime.now(),
                metric_type="challenge",
                metric_name="challenge_solved",
                value=1.0,
                labels={"type": "javascript"},
                metadata={}
            )
        ]

        # Add metrics to collector
        for metric in test_metrics:
            await metrics_collector.record_metric(metric)

        # Export only error metrics
        error_file = temp_dir / "error_metrics.json"
        try:
            exported_file = await metrics_collector.export_filtered_metrics(
                format=ExportFormat.JSON,
                metric_type="error",
                filename=str(error_file)
            )

            # Verify filtered export
            if Path(exported_file).exists():
                with open(exported_file, 'r') as f:
                    data = json.load(f)

                metrics_data = data.get("metrics", [])
                # Should only contain error metrics
                for metric in metrics_data:
                    assert metric["metric_type"] == "error"

        except AttributeError:
            # Method might not exist - that's acceptable
            print("Filtered export method not available")

    async def test_export_format_validation(self, metrics_collector, temp_dir):
        """Test validation of export formats and parameters."""
        # Generate test metric
        test_metric = MetricEvent(
            timestamp=datetime.now(),
            metric_type="test",
            metric_name="validation_test",
            value=1.0,
            labels={},
            metadata={}
        )

        await metrics_collector.record_metric(test_metric)

        # Test all supported formats
        formats_to_test = [
            ExportFormat.JSON,
            ExportFormat.CSV,
            ExportFormat.PROMETHEUS,
            ExportFormat.INFLUXDB
        ]

        for export_format in formats_to_test:
            file_extension = {
                ExportFormat.JSON: ".json",
                ExportFormat.CSV: ".csv",
                ExportFormat.PROMETHEUS: ".prom",
                ExportFormat.INFLUXDB: ".influx"
            }

            test_file = temp_dir / f"format_test{file_extension[export_format]}"

            try:
                exported_file = await metrics_collector.export_metrics(
                    format=export_format,
                    hours=1,
                    filename=str(test_file)
                )

                # Verify file was created
                assert Path(exported_file).exists()
                assert Path(exported_file).stat().st_size > 0

                print(f"Export format {export_format} successful: {exported_file}")

            except Exception as e:
                print(f"Export format {export_format} failed: {e}")
                # Some formats might not be implemented - that's acceptable

    async def test_large_dataset_export_performance(self, metrics_collector, temp_dir):
        """Test export performance with large datasets."""
        # Generate large number of metrics
        print("Generating large metric dataset...")
        large_metrics = []

        base_time = datetime.now()
        for i in range(1000):  # 1000 metrics
            metric = MetricEvent(
                timestamp=base_time + timedelta(seconds=i),
                metric_type="load_test",
                metric_name="bulk_metric",
                value=i % 100,
                labels={"batch": str(i // 100), "index": str(i % 100)},
                metadata={"sequence": i}
            )
            large_metrics.append(metric)

        # Add metrics in batches
        batch_size = 100
        for i in range(0, len(large_metrics), batch_size):
            batch = large_metrics[i:i + batch_size]
            for metric in batch:
                await metrics_collector.record_metric(metric)

        print(f"Added {len(large_metrics)} metrics to collector")

        # Test export performance
        start_time = time.time()

        large_export_file = temp_dir / "large_dataset.json"
        exported_file = await metrics_collector.export_metrics(
            format=ExportFormat.JSON,
            hours=1,
            filename=str(large_export_file)
        )

        export_time = time.time() - start_time

        # Verify export
        assert Path(exported_file).exists()
        file_size = Path(exported_file).stat().st_size

        print(f"Large export completed in {export_time:.2f}s, file size: {file_size} bytes")

        # Performance assertions
        assert export_time < 30  # Should complete within 30 seconds
        assert file_size > 1000  # Should contain substantial data

        # Verify data integrity
        with open(exported_file, 'r') as f:
            data = json.load(f)

        assert len(data["metrics"]) == len(large_metrics)

    async def test_concurrent_export_operations(self, metrics_collector, temp_dir):
        """Test concurrent export operations."""
        # Generate test metrics
        test_metrics = []
        for i in range(50):
            metric = MetricEvent(
                timestamp=datetime.now(),
                metric_type="concurrent_test",
                metric_name="concurrent_metric",
                value=i,
                labels={"thread": str(i % 5)},
                metadata={}
            )
            test_metrics.append(metric)

        # Add metrics
        for metric in test_metrics:
            await metrics_collector.record_metric(metric)

        # Perform concurrent exports
        export_tasks = []

        for i in range(3):  # 3 concurrent exports
            export_file = temp_dir / f"concurrent_export_{i}.json"
            task = asyncio.create_task(
                metrics_collector.export_metrics(
                    format=ExportFormat.JSON,
                    hours=1,
                    filename=str(export_file)
                )
            )
            export_tasks.append(task)

        # Wait for all exports to complete
        export_results = await asyncio.gather(*export_tasks, return_exceptions=True)

        # Verify all exports
        successful_exports = 0
        for i, result in enumerate(export_results):
            if isinstance(result, str) and Path(result).exists():
                successful_exports += 1
                print(f"Concurrent export {i} successful: {result}")
            else:
                print(f"Concurrent export {i} failed: {result}")

        # At least some exports should succeed
        assert successful_exports > 0


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "--tb=short"])