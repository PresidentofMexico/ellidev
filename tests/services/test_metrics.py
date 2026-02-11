"""
Tests for services/metrics.py

Tests the performance metrics collection service including
query times, API calls, RAG searches, and error tracking.
"""

import pytest
import time
from services.metrics import MetricsCollector, get_metrics


@pytest.fixture
def metrics_collector():
    """Create fresh metrics collector for each test"""
    collector = MetricsCollector(window_minutes=60)
    collector.reset()
    return collector


class TestMetricsCollector:
    """Tests for MetricsCollector class"""

    def test_initialization(self, metrics_collector):
        """Test metrics collector initializes correctly"""
        assert metrics_collector.enabled is True
        assert metrics_collector.window_minutes == 60

    def test_initialization_disabled(self, monkeypatch):
        """Test metrics can be disabled"""
        monkeypatch.setenv("ENABLE_METRICS", "false")
        collector = MetricsCollector()

        assert collector.enabled is False

    def test_record_query_time(self, metrics_collector):
        """Test recording query times"""
        metrics_collector.record_query_time(250.5)
        metrics_collector.record_query_time(180.3)
        metrics_collector.record_query_time(420.8)

        stats = metrics_collector.get_query_time_stats()

        assert stats["count"] == 3
        assert stats["min_ms"] == 180.3
        assert stats["max_ms"] == 420.8
        assert 250.0 < stats["avg_ms"] < 300.0

    def test_query_time_percentiles(self, metrics_collector):
        """Test query time percentile calculations"""
        # Add 100 query times
        for i in range(100):
            metrics_collector.record_query_time(float(i))

        stats = metrics_collector.get_query_time_stats()

        assert stats["count"] == 100
        assert 45 < stats["p50_ms"] < 55  # Median around 50
        assert 90 < stats["p95_ms"] < 100  # 95th percentile around 95
        assert 95 < stats["p99_ms"] < 100  # 99th percentile around 99

    def test_record_api_call(self, metrics_collector):
        """Test recording API calls"""
        metrics_collector.record_api_call("salesforce", "search_opportunities", 156.8, True)
        metrics_collector.record_api_call("salesforce", "update_opportunity", 178.4, True)
        metrics_collector.record_api_call("salesforce", "search_opportunities", 145.2, False)

        stats = metrics_collector.get_api_call_stats("salesforce")

        assert stats["total_calls"] == 3
        assert stats["successful_calls"] == 2
        assert stats["failed_calls"] == 1
        assert stats["success_rate"] == pytest.approx(0.667, rel=0.01)

    def test_api_call_stats_by_method(self, metrics_collector):
        """Test API call stats broken down by method"""
        metrics_collector.record_api_call("salesforce", "search", 100.0, True)
        metrics_collector.record_api_call("salesforce", "search", 150.0, True)
        metrics_collector.record_api_call("salesforce", "update", 200.0, True)

        stats = metrics_collector.get_api_call_stats("salesforce")

        assert "by_method" in stats
        assert stats["by_method"]["search"]["count"] == 2
        assert stats["by_method"]["update"]["count"] == 1
        assert stats["by_method"]["search"]["avg_duration_ms"] == 125.0

    def test_record_rag_search(self, metrics_collector):
        """Test recording RAG searches"""
        metrics_collector.record_rag_search(187.5, 3)
        metrics_collector.record_rag_search(245.3, 2)
        metrics_collector.record_rag_search(156.8, 4)

        stats = metrics_collector.get_rag_search_stats()

        assert stats["total_searches"] == 3
        assert 150 < stats["avg_duration_ms"] < 250
        assert stats["avg_sources_found"] == 3.0
        assert stats["min_sources_found"] == 2
        assert stats["max_sources_found"] == 4

    def test_record_error(self, metrics_collector):
        """Test recording errors"""
        metrics_collector.record_error("salesforce", "ConnectionError")
        metrics_collector.record_error("salesforce", "TimeoutError")
        metrics_collector.record_error("ai", "ConnectionError")
        metrics_collector.record_error("rag", "ValueError")

        stats = metrics_collector.get_error_stats()

        assert stats["total_errors"] == 4
        assert stats["by_component"]["salesforce"] == 2
        assert stats["by_component"]["ai"] == 1
        assert stats["by_type"]["ConnectionError"] == 2
        assert stats["by_type"]["TimeoutError"] == 1

    def test_record_cache_hit_miss(self, metrics_collector):
        """Test recording cache hits and misses"""
        metrics_collector.record_cache_hit("vector_search")
        metrics_collector.record_cache_hit("vector_search")
        metrics_collector.record_cache_miss("vector_search")
        metrics_collector.record_cache_hit("api_response")

        stats = metrics_collector.get_cache_stats()

        assert stats["vector_search"]["hits"] == 2
        assert stats["vector_search"]["misses"] == 1
        assert stats["vector_search"]["hit_rate"] == pytest.approx(0.667, rel=0.01)
        assert stats["api_response"]["hits"] == 1
        assert stats["api_response"]["misses"] == 0
        assert stats["api_response"]["hit_rate"] == 1.0

    def test_get_all_stats(self, metrics_collector):
        """Test retrieving all metrics at once"""
        # Record various metrics
        metrics_collector.record_query_time(250.0)
        metrics_collector.record_api_call("salesforce", "search", 150.0, True)
        metrics_collector.record_rag_search(200.0, 3)
        metrics_collector.record_error("ai", "ConnectionError")

        stats = metrics_collector.get_all_stats()

        assert stats["enabled"] is True
        assert "query_times" in stats
        assert "api_calls" in stats
        assert "rag_searches" in stats
        assert "errors" in stats
        assert "timestamp" in stats

    def test_metrics_disabled_returns_empty(self, monkeypatch):
        """Test that disabled metrics return empty stats"""
        monkeypatch.setenv("ENABLE_METRICS", "false")
        collector = MetricsCollector()

        stats = collector.get_all_stats()

        assert stats["enabled"] is False
        assert "query_times" not in stats

    def test_reset_clears_all_metrics(self, metrics_collector):
        """Test that reset clears all metrics"""
        # Add some metrics
        metrics_collector.record_query_time(250.0)
        metrics_collector.record_api_call("salesforce", "search", 150.0, True)
        metrics_collector.record_error("ai", "Error")

        # Reset
        metrics_collector.reset()

        # Check all cleared
        assert metrics_collector.get_query_time_stats() == {}
        assert metrics_collector.get_rag_search_stats() == {}
        assert metrics_collector.get_error_stats() == {}

    def test_time_window_cleanup(self, metrics_collector):
        """Test that old metrics are cleaned up based on time window"""
        from datetime import datetime, timedelta
        from collections import deque

        # Create metrics with old timestamps (more than window_minutes ago)
        old_time = datetime.utcnow() - timedelta(minutes=metrics_collector.window_minutes + 10)

        # Manually add old metric
        metrics_collector._query_times.append((old_time, 100.0))

        # Add new metric
        metrics_collector.record_query_time(200.0)

        # Trigger cleanup
        metrics_collector._cleanup_old_metrics()

        # Check that old metric was removed
        stats = metrics_collector.get_query_time_stats()
        assert stats["count"] == 1  # Only new metric

    def test_empty_metrics_return_empty_stats(self, metrics_collector):
        """Test that empty metrics return empty dictionaries"""
        assert metrics_collector.get_query_time_stats() == {}
        assert metrics_collector.get_api_call_stats() == {}
        assert metrics_collector.get_rag_search_stats() == {}
        assert metrics_collector.get_error_stats() == {}

    def test_percentile_calculation_edge_cases(self, metrics_collector):
        """Test percentile calculation with edge cases"""
        # Single value
        metrics_collector.record_query_time(100.0)
        stats = metrics_collector.get_query_time_stats()
        assert stats["p50_ms"] == 100.0
        assert stats["p95_ms"] == 100.0
        assert stats["p99_ms"] == 100.0

    def test_api_call_stats_without_service_filter(self, metrics_collector):
        """Test API call stats without service filter returns all services"""
        metrics_collector.record_api_call("salesforce", "search", 100.0, True)
        metrics_collector.record_api_call("snowflake", "query", 200.0, True)

        stats = metrics_collector.get_api_call_stats()  # No service filter

        assert stats["total_calls"] == 2

    def test_api_call_stats_with_nonexistent_service(self, metrics_collector):
        """Test API call stats for service with no calls"""
        metrics_collector.record_api_call("salesforce", "search", 100.0, True)

        stats = metrics_collector.get_api_call_stats("nonexistent_service")

        assert stats == {}


class TestGetMetrics:
    """Tests for get_metrics singleton function"""

    def test_get_metrics_singleton(self):
        """Test that get_metrics returns singleton instance"""
        metrics1 = get_metrics()
        metrics2 = get_metrics()

        assert metrics1 is metrics2

    def test_get_metrics_returns_collector(self):
        """Test that get_metrics returns MetricsCollector instance"""
        metrics = get_metrics()

        assert isinstance(metrics, MetricsCollector)


@pytest.mark.integration
class TestMetricsIntegration:
    """Integration tests for metrics collector"""

    def test_realistic_query_flow(self, metrics_collector):
        """Test metrics collection for realistic query flow"""
        # Simulate a RAG search query
        metrics_collector.record_rag_search(187.5, 3)
        metrics_collector.record_api_call("snowflake", "cortex.complete", 423.6, True)
        metrics_collector.record_query_time(650.0)

        # Get all stats
        stats = metrics_collector.get_all_stats()

        assert stats["query_times"]["count"] == 1
        assert stats["rag_searches"]["total_searches"] == 1
        assert stats["api_calls"]["all"]["total_calls"] == 1

    def test_multiple_concurrent_operations(self, metrics_collector):
        """Test metrics for multiple concurrent operations"""
        # Simulate multiple queries and operations
        for i in range(10):
            metrics_collector.record_query_time(200.0 + i * 10)
            metrics_collector.record_api_call("salesforce", "search", 150.0, i % 3 != 0)
            if i % 2 == 0:
                metrics_collector.record_rag_search(180.0, 2 + i % 3)

        stats = metrics_collector.get_all_stats()

        assert stats["query_times"]["count"] == 10
        assert stats["api_calls"]["salesforce"]["total_calls"] == 10
        assert stats["rag_searches"]["total_searches"] == 5

    def test_error_rate_calculation(self, metrics_collector):
        """Test error rate tracking over multiple operations"""
        # Record successful operations
        for i in range(90):
            metrics_collector.record_api_call("salesforce", "search", 150.0, True)

        # Record failures
        for i in range(10):
            metrics_collector.record_api_call("salesforce", "search", 150.0, False)
            metrics_collector.record_error("salesforce", "TimeoutError")

        stats = metrics_collector.get_api_call_stats("salesforce")
        error_stats = metrics_collector.get_error_stats()

        assert stats["total_calls"] == 100
        assert stats["success_rate"] == 0.9
        assert error_stats["total_errors"] == 10
