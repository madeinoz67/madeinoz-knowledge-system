"""
Session Metrics - Aggregated Caching Statistics

Feature: 006-gemini-prompt-caching
Purpose: Track session-level cache performance across multiple requests
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any


@dataclass
class SessionMetrics:
    """
    Aggregated caching statistics across all requests in a session.

    Enables session-level cost analysis and hit rate tracking for monitoring
    overall caching effectiveness.
    """

    total_requests: int = 0
    """Count of all Gemini API requests in this session"""

    cache_hits: int = 0
    """Count of requests with cache_hit=true"""

    cache_misses: int = 0
    """Count of requests with cache_hit=false"""

    total_cached_tokens: int = 0
    """Sum of cached_tokens across all requests"""

    total_prompt_tokens: int = 0
    """Sum of prompt_tokens across all requests"""

    total_completion_tokens: int = 0
    """Sum of completion_tokens across all requests"""

    total_cost_without_cache: float = 0.0
    """Sum of hypothetical costs (USD)"""

    total_actual_cost: float = 0.0
    """Sum of actual costs (USD)"""

    total_cost_saved: float = 0.0
    """Cumulative savings (USD)"""

    session_start: datetime = field(default_factory=datetime.now)
    """When the session began (auto-initialized)"""

    last_request: datetime = field(default_factory=datetime.now)
    """Most recent request timestamp"""

    @property
    def cache_hit_rate(self) -> float:
        """
        Calculate cache hit rate as percentage.

        Returns:
            Hit rate (0.0 to 100.0), or 0.0 if no requests
        """
        if self.total_requests == 0:
            return 0.0
        return (self.cache_hits / self.total_requests) * 100

    @property
    def overall_savings_percent(self) -> float:
        """
        Calculate overall cost savings percentage.

        Returns:
            Savings percentage (0.0 to 100.0), or 0.0 if no cost
        """
        if self.total_cost_without_cache == 0:
            return 0.0
        return (self.total_cost_saved / self.total_cost_without_cache) * 100

    @property
    def average_cached_tokens_per_request(self) -> float:
        """
        Calculate average cached tokens per request.

        Returns:
            Average cached tokens, or 0.0 if no requests
        """
        if self.total_requests == 0:
            return 0.0
        return self.total_cached_tokens / self.total_requests

    @property
    def session_duration(self) -> float:
        """
        Calculate session duration in seconds.

        Returns:
            Duration in seconds since session start
        """
        return (self.last_request - self.session_start).total_seconds()

    def record_request(self, cache_metrics: "CacheMetrics") -> None:
        """
        Update session metrics with data from a single request.

        Args:
            cache_metrics: CacheMetrics from a completed API request
        """
        self.total_requests += 1

        if cache_metrics.cache_hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1

        self.total_cached_tokens += cache_metrics.cached_tokens
        self.total_prompt_tokens += cache_metrics.prompt_tokens
        self.total_completion_tokens += cache_metrics.completion_tokens
        self.total_cost_without_cache += cache_metrics.cost_without_cache
        self.total_actual_cost += cache_metrics.actual_cost
        self.total_cost_saved += cache_metrics.cost_saved

        self.last_request = datetime.now()

    def get_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive session statistics as dictionary.

        Returns:
            Dictionary with all session metrics including computed properties
        """
        return {
            "total_requests": self.total_requests,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "total_cached_tokens": self.total_cached_tokens,
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_cost_without_cache": round(self.total_cost_without_cache, 8),
            "total_actual_cost": round(self.total_actual_cost, 8),
            "total_cost_saved": round(self.total_cost_saved, 8),
            "session_start": self.session_start.isoformat(),
            "last_request": self.last_request.isoformat(),
            "cache_hit_rate": round(self.cache_hit_rate, 2),
            "overall_savings_percent": round(self.overall_savings_percent, 2),
            "average_cached_tokens_per_request": round(self.average_cached_tokens_per_request, 2),
            "session_duration_seconds": round(self.session_duration, 2)
        }
