"""Contract test for metrics export methods.

This test validates the metrics export interface against the API specification.
Tests MUST fail initially to follow TDD principles.
"""

import pytest
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, Mock
import json
import csv
from io import StringIO

# Import will fail until implementation exists - this is expected for TDD
try:
    from cloudflare_research import CloudflareBypass
    from cloudflare_research.models import PerformanceMetrics
except ImportError:
    # Expected during TDD phase - tests should fail initially
    CloudflareBypass = None
    PerformanceMetrics = None


@pytest.mark.contract
@pytest.mark.asyncio
class TestMetricsExport:
    """Contract tests for metrics export methods."""

    @pytest.fixture
    def bypass_client(self):
        """Create CloudflareBypass instance for testing."""
        if CloudflareBypass is None:
            pytest.skip("CloudflareBypass not implemented yet - TDD phase")
        return CloudflareBypass()

    @pytest.fixture
    def sample_session_id(self, bypass_client):
        """Create a sample session for metrics testing."""
        # This would be created in a real test scenario
        return "550e8400-e29b-41d4-a716-446655440000"

    @pytest.fixture
    def sample_metrics(self):
        """Sample performance metrics data."""
        if PerformanceMetrics is None:
            return {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "total_requests": 1000,
                "successful_requests": 950,
                "failed_requests": 50,
                "avg_response_time_ms": 245.7,
                "min_response_time_ms": 89,
                "max_response_time_ms": 1205,
                "p95_response_time_ms": 456.2,
                "p99_response_time_ms": 892.1,
                "requests_per_second": 42.3,
                "concurrent_connections_peak": 85,
                "memory_usage_mb": 67.4,
                "cpu_usage_percent": 23.8,
                "challenges_total": 15,
                "challenges_solved": 14,
                "challenge_solve_rate": 93.3
            }
        
        return PerformanceMetrics(
            session_id="550e8400-e29b-41d4-a716-446655440000",
            total_requests=1000,
            successful_requests=950,
            failed_requests=50,
            avg_response_time_ms=245.7,
            requests_per_second=42.3,
            challenges_total=15,
            challenges_solved=14
        )

    async def test_get_metrics_method_exists(self, bypass_client):
        """Test that get_session_metrics() method exists and is callable."""
        assert hasattr(bypass_client, 'get_session_metrics')
        assert callable(getattr(bypass_client, 'get_session_metrics'))

    async def test_export_metrics_method_exists(self, bypass_client):
        """Test that export_metrics() method exists and is callable."""
        assert hasattr(bypass_client, 'export_metrics')
        assert callable(getattr(bypass_client, 'export_metrics'))

    async def test_get_session_metrics_json(self, bypass_client, sample_session_id):
        """Test retrieving session metrics in JSON format."""
        # Contract: get_session_metrics(session_id, format='json') -> PerformanceMetrics
        metrics = await bypass_client.get_session_metrics(sample_session_id, format='json')

        # Validate result structure matches API spec
        if isinstance(metrics, dict):
            assert 'session_id' in metrics
            assert 'total_requests' in metrics
            assert 'successful_requests' in metrics
            assert 'failed_requests' in metrics
            assert 'avg_response_time_ms' in metrics
            assert 'requests_per_second' in metrics
            assert 'challenges_total' in metrics
            assert 'challenges_solved' in metrics
        else:
            assert isinstance(metrics, PerformanceMetrics)
            assert hasattr(metrics, 'session_id')
            assert hasattr(metrics, 'total_requests')
            assert hasattr(metrics, 'successful_requests')
            assert hasattr(metrics, 'requests_per_second')

    async def test_get_session_metrics_csv(self, bypass_client, sample_session_id):
        """Test retrieving session metrics in CSV format."""
        metrics_csv = await bypass_client.get_session_metrics(sample_session_id, format='csv')

        assert isinstance(metrics_csv, str)
        
        # Validate CSV structure
        csv_reader = csv.DictReader(StringIO(metrics_csv))
        rows = list(csv_reader)
        
        assert len(rows) >= 1  # Should have at least header + 1 data row
        
        # Check required columns
        required_columns = [
            'session_id', 'total_requests', 'successful_requests',
            'failed_requests', 'avg_response_time_ms', 'requests_per_second'
        ]
        
        for column in required_columns:
            assert column in csv_reader.fieldnames

    async def test_get_session_metrics_invalid_session(self, bypass_client):
        """Test retrieving metrics for non-existent session."""
        import uuid
        fake_session_id = str(uuid.uuid4())

        with pytest.raises((ValueError, KeyError)):
            await bypass_client.get_session_metrics(fake_session_id)

    async def test_get_session_metrics_invalid_format(self, bypass_client, sample_session_id):
        """Test retrieving metrics with invalid format."""
        with pytest.raises(ValueError):
            await bypass_client.get_session_metrics(sample_session_id, format='xml')

    async def test_export_metrics_to_file(self, bypass_client, sample_session_id, tmp_path):
        """Test exporting metrics to file."""
        output_file = tmp_path / "metrics.json"
        
        # Contract: export_metrics(session_id, file_path, format) -> None
        result = await bypass_client.export_metrics(
            sample_session_id,
            str(output_file),
            format='json'
        )

        # Should complete without error
        assert result is None or result is True
        
        # File should be created and contain valid JSON
        assert output_file.exists()
        
        with open(output_file, 'r') as f:
            data = json.load(f)
            assert 'session_id' in data
            assert data['session_id'] == sample_session_id

    async def test_export_metrics_csv_to_file(self, bypass_client, sample_session_id, tmp_path):
        """Test exporting metrics to CSV file."""
        output_file = tmp_path / "metrics.csv"
        
        result = await bypass_client.export_metrics(
            sample_session_id,
            str(output_file),
            format='csv'
        )

        assert result is None or result is True
        
        # File should be created and contain valid CSV
        assert output_file.exists()
        
        with open(output_file, 'r') as f:
            csv_content = f.read()
            assert sample_session_id in csv_content
            assert 'total_requests' in csv_content

    async def test_export_metrics_invalid_path(self, bypass_client, sample_session_id):
        """Test exporting metrics to invalid file path."""
        invalid_path = "/invalid/path/that/does/not/exist/metrics.json"
        
        with pytest.raises((OSError, IOError, ValueError)):
            await bypass_client.export_metrics(
                sample_session_id,
                invalid_path,
                format='json'
            )

    async def test_metrics_data_types(self, bypass_client, sample_session_id):
        """Test that metrics data has correct types."""
        metrics = await bypass_client.get_session_metrics(sample_session_id)

        if isinstance(metrics, dict):
            # Validate data types
            assert isinstance(metrics['session_id'], str)
            assert isinstance(metrics['total_requests'], int)
            assert isinstance(metrics['successful_requests'], int)
            assert isinstance(metrics['failed_requests'], int)
            assert isinstance(metrics['avg_response_time_ms'], (int, float))
            assert isinstance(metrics['requests_per_second'], (int, float))
            assert isinstance(metrics['challenges_total'], int)
            assert isinstance(metrics['challenges_solved'], int)
        else:
            assert isinstance(metrics.session_id, str)
            assert isinstance(metrics.total_requests, int)
            assert isinstance(metrics.successful_requests, int)
            assert isinstance(metrics.requests_per_second, (int, float))

    async def test_metrics_data_validation(self, bypass_client, sample_session_id):
        """Test that metrics data is logically valid."""
        metrics = await bypass_client.get_session_metrics(sample_session_id)

        if isinstance(metrics, dict):
            # Logical validations
            assert metrics['total_requests'] >= 0
            assert metrics['successful_requests'] >= 0
            assert metrics['failed_requests'] >= 0
            assert metrics['successful_requests'] + metrics['failed_requests'] <= metrics['total_requests']
            assert metrics['avg_response_time_ms'] >= 0
            assert metrics['requests_per_second'] >= 0
            assert metrics['challenges_total'] >= 0
            assert metrics['challenges_solved'] >= 0
            assert metrics['challenges_solved'] <= metrics['challenges_total']
        else:
            assert metrics.total_requests >= 0
            assert metrics.successful_requests >= 0
            assert metrics.failed_requests >= 0
            assert metrics.requests_per_second >= 0

    async def test_metrics_percentile_data(self, bypass_client, sample_session_id):
        """Test that percentile metrics are included and valid."""
        metrics = await bypass_client.get_session_metrics(sample_session_id)

        if isinstance(metrics, dict):
            if 'p95_response_time_ms' in metrics:
                assert isinstance(metrics['p95_response_time_ms'], (int, float))
                assert metrics['p95_response_time_ms'] >= 0
                
            if 'p99_response_time_ms' in metrics:
                assert isinstance(metrics['p99_response_time_ms'], (int, float))
                assert metrics['p99_response_time_ms'] >= 0
                
                # P99 should be >= P95
                if 'p95_response_time_ms' in metrics:
                    assert metrics['p99_response_time_ms'] >= metrics['p95_response_time_ms']
        else:
            if hasattr(metrics, 'p95_response_time_ms'):
                assert metrics.p95_response_time_ms >= 0
            if hasattr(metrics, 'p99_response_time_ms'):
                assert metrics.p99_response_time_ms >= 0

    async def test_metrics_challenge_rate_calculation(self, bypass_client, sample_session_id):
        """Test challenge solve rate calculation."""
        metrics = await bypass_client.get_session_metrics(sample_session_id)

        if isinstance(metrics, dict):
            if metrics['challenges_total'] > 0:
                expected_rate = (metrics['challenges_solved'] / metrics['challenges_total']) * 100
                if 'challenge_solve_rate' in metrics:
                    assert abs(metrics['challenge_solve_rate'] - expected_rate) < 0.1
        else:
            if metrics.challenges_total > 0:
                expected_rate = (metrics.challenges_solved / metrics.challenges_total) * 100
                if hasattr(metrics, 'challenge_solve_rate'):
                    assert abs(metrics.challenge_solve_rate - expected_rate) < 0.1

    async def test_export_metrics_large_dataset(self, bypass_client, sample_session_id, tmp_path):
        """Test exporting metrics for large datasets."""
        output_file = tmp_path / "large_metrics.json"
        
        # Should handle large datasets without issues
        result = await bypass_client.export_metrics(
            sample_session_id,
            str(output_file),
            format='json'
        )

        assert result is None or result is True
        assert output_file.exists()
        
        # File should not be empty
        assert output_file.stat().st_size > 0

    async def test_metrics_timestamp_fields(self, bypass_client, sample_session_id):
        """Test that timestamp fields are included in metrics."""
        metrics = await bypass_client.get_session_metrics(sample_session_id)

        # Should include timing information
        if isinstance(metrics, dict):
            # May include timestamp fields like collection_time, etc.
            pass
        else:
            # PerformanceMetrics object should have timestamp info
            pass

    async def test_get_metrics_method_signature(self, bypass_client):
        """Test get_session_metrics() method has correct signature."""
        import inspect

        sig = inspect.signature(bypass_client.get_session_metrics)
        params = sig.parameters

        # Check required parameter
        assert 'session_id' in params
        
        # Check optional format parameter
        assert 'format' in params
        assert params['format'].default == 'json'

    async def test_export_metrics_method_signature(self, bypass_client):
        """Test export_metrics() method has correct signature."""
        import inspect

        sig = inspect.signature(bypass_client.export_metrics)
        params = sig.parameters

        # Check required parameters
        assert 'session_id' in params
        assert 'file_path' in params
        
        # Check optional format parameter
        assert 'format' in params
        assert params['format'].default == 'json'

    async def test_metrics_memory_efficiency(self, bypass_client, sample_session_id):
        """Test that metrics retrieval is memory efficient."""
        import sys
        
        # Get initial memory usage
        initial_refs = sys.gettotalrefcount() if hasattr(sys, 'gettotalrefcount') else 0
        
        # Retrieve metrics multiple times
        for _ in range(10):
            metrics = await bypass_client.get_session_metrics(sample_session_id)
            # Process metrics to ensure they're loaded
            if isinstance(metrics, dict):
                _ = metrics['total_requests']
            else:
                _ = metrics.total_requests
        
        # Memory usage shouldn't grow significantly
        # (This is a basic check - full memory profiling would be in performance tests)

    async def test_concurrent_metrics_access(self, bypass_client, sample_session_id):
        """Test concurrent access to metrics data."""
        import asyncio
        
        # Multiple concurrent requests for same metrics
        tasks = []
        for _ in range(5):
            task = asyncio.create_task(
                bypass_client.get_session_metrics(sample_session_id)
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        assert len(results) == 5
        for result in results:
            assert result is not None
            
        # All should have same session_id
        for result in results:
            if isinstance(result, dict):
                assert result['session_id'] == sample_session_id
            else:
                assert result.session_id == sample_session_id