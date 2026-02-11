"""
Performance metrics collection service for Elli application.

Tracks response times, API calls, cache hits, and error rates to help
identify performance bottlenecks and system health issues.

Phase 7.1: Structured Logging Framework
"""

import os
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque
import statistics


class MetricsCollector:
    """
    Collects and aggregates performance metrics.

    Features:
    - Response time tracking (p50, p95, p99)
    - API call latency monitoring
    - Error rate tracking by component
    - Cache hit rate tracking (for future caching)
    - In-memory windowed metrics (last N minutes)
    """

    def __init__(self, window_minutes: int = 60):
        """
        Initialize metrics collector.

        Args:
            window_minutes: Rolling window size in minutes for metrics aggregation
        """
        self.enabled = os.getenv("ENABLE_METRICS", "true").lower() == "true"
        self.window_minutes = window_minutes

        # Metric storage (in-memory, time-windowed)
        self._query_times: deque = deque()  # (timestamp, duration_ms)
        self._api_calls: deque = deque()  # (timestamp, service, method, duration_ms, success)
        self._rag_searches: deque = deque()  # (timestamp, duration_ms, sources_found)
        self._errors: deque = deque()  # (timestamp, component, error_type)
        self._cache_hits: Dict[str, int] = defaultdict(int)
        self._cache_misses: Dict[str, int] = defaultdict(int)

    def _cleanup_old_metrics(self):
        """Remove metrics older than window_minutes"""
        if not self.enabled:
            return

        cutoff = datetime.utcnow() - timedelta(minutes=self.window_minutes)

        # Clean up query times
        while self._query_times and self._query_times[0][0] < cutoff:
            self._query_times.popleft()

        # Clean up API calls
        while self._api_calls and self._api_calls[0][0] < cutoff:
            self._api_calls.popleft()

        # Clean up RAG searches
        while self._rag_searches and self._rag_searches[0][0] < cutoff:
            self._rag_searches.popleft()

        # Clean up errors
        while self._errors and self._errors[0][0] < cutoff:
            self._errors.popleft()

    def record_query_time(self, duration_ms: float):
        """
        Record query response time.

        Args:
            duration_ms: Query duration in milliseconds
        """
        if not self.enabled:
            return

        self._query_times.append((datetime.utcnow(), duration_ms))
        self._cleanup_old_metrics()

    def record_api_call(
        self,
        service: str,
        method: str,
        duration_ms: float,
        success: bool
    ):
        """
        Record API call metrics.

        Args:
            service: Service name (salesforce, snowflake, slack)
            method: Method/endpoint called
            duration_ms: Call duration in milliseconds
            success: Whether call succeeded
        """
        if not self.enabled:
            return

        self._api_calls.append((
            datetime.utcnow(),
            service,
            method,
            duration_ms,
            success
        ))
        self._cleanup_old_metrics()

    def record_rag_search(self, duration_ms: float, sources_found: int):
        """
        Record RAG search metrics.

        Args:
            duration_ms: Search duration in milliseconds
            sources_found: Number of sources retrieved
        """
        if not self.enabled:
            return

        self._rag_searches.append((
            datetime.utcnow(),
            duration_ms,
            sources_found
        ))
        self._cleanup_old_metrics()

    def record_error(self, component: str, error_type: str):
        """
        Record error occurrence.

        Args:
            component: Component where error occurred (rag, salesforce, ai, etc.)
            error_type: Type of error (Exception class name)
        """
        if not self.enabled:
            return

        self._errors.append((
            datetime.utcnow(),
            component,
            error_type
        ))
        self._cleanup_old_metrics()

    def record_cache_hit(self, cache_name: str):
        """
        Record cache hit.

        Args:
            cache_name: Name of cache (for future use)
        """
        if not self.enabled:
            return

        self._cache_hits[cache_name] += 1

    def record_cache_miss(self, cache_name: str):
        """
        Record cache miss.

        Args:
            cache_name: Name of cache (for future use)
        """
        if not self.enabled:
            return

        self._cache_misses[cache_name] += 1

    def get_query_time_stats(self) -> Dict[str, float]:
        """
        Get query time statistics.

        Returns:
            Dict with p50, p95, p99, avg, min, max, count
        """
        if not self.enabled or not self._query_times:
            return {}

        times = [t[1] for t in self._query_times]

        return {
            "count": len(times),
            "avg_ms": statistics.mean(times),
            "min_ms": min(times),
            "max_ms": max(times),
            "p50_ms": statistics.median(times),
            "p95_ms": self._percentile(times, 0.95),
            "p99_ms": self._percentile(times, 0.99),
        }

    def get_api_call_stats(self, service: Optional[str] = None) -> Dict[str, any]:
        """
        Get API call statistics.

        Args:
            service: Optional service filter

        Returns:
            Dict with call counts, success rate, latency stats
        """
        if not self.enabled or not self._api_calls:
            return {}

        # Filter by service if specified
        calls = [c for c in self._api_calls if service is None or c[1] == service]

        if not calls:
            return {}

        total_calls = len(calls)
        successful_calls = sum(1 for c in calls if c[4])
        durations = [c[3] for c in calls]

        stats = {
            "total_calls": total_calls,
            "successful_calls": successful_calls,
            "failed_calls": total_calls - successful_calls,
            "success_rate": successful_calls / total_calls if total_calls > 0 else 0,
            "avg_duration_ms": statistics.mean(durations) if durations else 0,
            "p95_duration_ms": self._percentile(durations, 0.95) if durations else 0,
        }

        # Break down by method
        method_stats = defaultdict(lambda: {"count": 0, "success": 0, "durations": []})
        for call in calls:
            method = call[2]
            method_stats[method]["count"] += 1
            if call[4]:
                method_stats[method]["success"] += 1
            method_stats[method]["durations"].append(call[3])

        stats["by_method"] = {
            method: {
                "count": data["count"],
                "success_rate": data["success"] / data["count"],
                "avg_duration_ms": statistics.mean(data["durations"])
            }
            for method, data in method_stats.items()
        }

        return stats

    def get_rag_search_stats(self) -> Dict[str, float]:
        """
        Get RAG search statistics.

        Returns:
            Dict with search counts, latency, and sources found
        """
        if not self.enabled or not self._rag_searches:
            return {}

        durations = [s[1] for s in self._rag_searches]
        sources = [s[2] for s in self._rag_searches]

        return {
            "total_searches": len(self._rag_searches),
            "avg_duration_ms": statistics.mean(durations),
            "p95_duration_ms": self._percentile(durations, 0.95),
            "avg_sources_found": statistics.mean(sources),
            "min_sources_found": min(sources),
            "max_sources_found": max(sources),
        }

    def get_error_stats(self) -> Dict[str, any]:
        """
        Get error statistics.

        Returns:
            Dict with error counts by component and type
        """
        if not self.enabled or not self._errors:
            return {}

        total_errors = len(self._errors)

        # Group by component
        by_component = defaultdict(int)
        for error in self._errors:
            by_component[error[1]] += 1

        # Group by error type
        by_type = defaultdict(int)
        for error in self._errors:
            by_type[error[2]] += 1

        return {
            "total_errors": total_errors,
            "by_component": dict(by_component),
            "by_type": dict(by_type),
        }

    def get_cache_stats(self) -> Dict[str, any]:
        """
        Get cache statistics.

        Returns:
            Dict with hit rates by cache name
        """
        if not self.enabled:
            return {}

        all_caches = set(self._cache_hits.keys()) | set(self._cache_misses.keys())

        return {
            cache: {
                "hits": self._cache_hits[cache],
                "misses": self._cache_misses[cache],
                "hit_rate": (
                    self._cache_hits[cache] /
                    (self._cache_hits[cache] + self._cache_misses[cache])
                    if (self._cache_hits[cache] + self._cache_misses[cache]) > 0
                    else 0
                )
            }
            for cache in all_caches
        }

    def get_all_stats(self) -> Dict[str, any]:
        """
        Get all metrics in one call.

        Returns:
            Dict with all metrics organized by category
        """
        if not self.enabled:
            return {"enabled": False}

        self._cleanup_old_metrics()

        return {
            "enabled": True,
            "window_minutes": self.window_minutes,
            "timestamp": datetime.utcnow().isoformat(),
            "query_times": self.get_query_time_stats(),
            "api_calls": {
                "all": self.get_api_call_stats(),
                "salesforce": self.get_api_call_stats("salesforce"),
                "snowflake": self.get_api_call_stats("snowflake"),
            },
            "rag_searches": self.get_rag_search_stats(),
            "errors": self.get_error_stats(),
            "cache": self.get_cache_stats(),
        }

    def _percentile(self, data: List[float], percentile: float) -> float:
        """
        Calculate percentile value.

        Args:
            data: List of values
            percentile: Percentile (0.0 to 1.0)

        Returns:
            Percentile value
        """
        if not data:
            return 0.0

        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile)
        return sorted_data[min(index, len(sorted_data) - 1)]

    def reset(self):
        """Reset all metrics (useful for testing)"""
        self._query_times.clear()
        self._api_calls.clear()
        self._rag_searches.clear()
        self._errors.clear()
        self._cache_hits.clear()
        self._cache_misses.clear()


# Singleton instance
_metrics_instance: Optional[MetricsCollector] = None


def get_metrics() -> MetricsCollector:
    """
    Get singleton metrics collector instance.

    Returns:
        MetricsCollector: Singleton metrics instance
    """
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = MetricsCollector()
    return _metrics_instance


# Convenience exports
metrics = get_metrics()
